# app.py
import json, io, itertools, joblib, numpy as np, pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "cloud-safe-key-please-change"

# ------------------ CONFIG ------------------
# Local uploaded dataset path (this is the path you uploaded earlier)
LOCAL_UPLOADED_CSV = "/mnt/data/5c838a7d-4918-4ab5-849e-1785165c5052.csv"

# For repo/deploy use these defaults (recommended copy your CSV to data/processed.csv)
MODEL_PATH = "models/ddi_model.pkl"
VECT_PATH = "models/tfidf.pkl"
DATA_PATH = "data/processed.csv"   # replace with LOCAL_UPLOADED_CSV if testing locally
DOSING_BASELINE_PATH = "data/dosing_baseline.json"

# Choose which dataset path to use:
# If the local uploaded path exists, we will prefer it (useful for local testing here).
import os
if os.path.exists(LOCAL_UPLOADED_CSV):
    DATA_PATH_ACTIVE = LOCAL_UPLOADED_CSV
else:
    DATA_PATH_ACTIVE = DATA_PATH

# ------------------ LOAD MODEL & DATA ------------------
# NOTE: ensure models/ contains ddi_model.pkl and tfidf.pkl (trained earlier).
model = joblib.load(MODEL_PATH)
tfidf = joblib.load(VECT_PATH)

df = pd.read_csv(DATA_PATH_ACTIVE)
df.columns = [c.strip() for c in df.columns]

# dosing baseline JSON
with open(DOSING_BASELINE_PATH, "r", encoding="utf-8") as fh:
    dosing_baseline = json.load(fh)

# ------------------ HELPERS ------------------
def key_pair(a, b):
    a, b = str(a).strip().lower(), str(b).strip().lower()
    return "||".join(sorted([a, b]))

interaction_map = {}
# expect df columns: drug1, drug2, label (as in your uploaded CSV)
for _, r in df.iterrows():
    k = key_pair(r.get("drug1", ""), r.get("drug2", ""))
    interaction_map[k] = ""  # no textual description in this dataset

unique_drugs = sorted(list(set(df["drug1"].astype(str)).union(set(df["drug2"].astype(str)))))

# Unit conversion helper (returns mg or None)
def convert_to_mg(value, unit):
    if value is None:
        return None
    unit = (unit or "").strip().lower()
    try:
        val = float(value)
    except Exception:
        return None
    if unit in ["mg", "milligram", "milligrams"]:
        return val
    if unit in ["g", "gram", "grams"]:
        return val * 1000.0
    if unit in ["mcg", "µg", "microgram", "micrograms"]:
        return val / 1000.0
    if unit in ["ml", "mL"]:
        # cannot reliably convert mL -> mg without concentration; return None
        return None
    if unit in ["iu"]:
        # IU conversion depends on substance; skip
        return None
    return None

def evaluate_dose(drug_name, dose_value, dose_unit, freq_per_day, route, is_pediatric=False, age=None, weight_kg=None):
    d = {
        "drug": drug_name,
        "dose_value": dose_value,
        "unit": dose_unit,
        "freq_per_day": freq_per_day,
        "route": route,
        "baseline_found": False,
        "status": "unknown",
        "percent_above": 0.0,
        "comment": ""
    }
    key = drug_name.strip().lower()
    if key not in dosing_baseline:
        d["comment"] = "No baseline dosing info available"
        return d
    d["baseline_found"] = True
    baseline = dosing_baseline[key]

    # convert per-dose to mg where possible
    dose_mg = convert_to_mg(dose_value, dose_unit)
    if dose_mg is None:
        d["comment"] = "Unsupported or non-convertible unit for automated check"
        return d

    # adult per-dose check
    adult = baseline.get("adult", {})
    if adult and not is_pediatric:
        min_mg = adult.get("min_mg_per_dose")
        max_mg = adult.get("max_mg_per_dose")
        if min_mg is None or max_mg is None:
            d["comment"] = "Incomplete adult baseline"
        else:
            if dose_mg < min_mg:
                d["status"] = "below"
                d["comment"] = f"Below typical adult per-dose range ({min_mg}-{max_mg} mg)"
            elif dose_mg > max_mg:
                d["status"] = "above"
                d["percent_above"] = ((dose_mg - max_mg) / max_mg) * 100.0
                d["comment"] = f"Above typical adult per-dose max ({max_mg} mg) by {d['percent_above']:.1f}%"
            else:
                d["status"] = "within"
                d["comment"] = f"Within typical adult per-dose range ({min_mg}-{max_mg} mg)"

    # pediatric mg/kg/day check if requested
    if is_pediatric and weight_kg is not None:
        ped = baseline.get("pediatric_mg_per_kg_per_day")
        if ped:
            mg_per_kg_day = (dose_mg * (freq_per_day or 1.0)) / float(weight_kg)
            d["pediatric_mg_per_kg_day"] = mg_per_kg_day
            if mg_per_kg_day < ped["min"]:
                d["status"] = "below"
                d["comment"] = f"Below pediatric guidance ({ped['min']} mg/kg/day)"
            elif mg_per_kg_day > ped["max"]:
                d["status"] = "above"
                d["percent_above"] = ((mg_per_kg_day - ped["max"]) / ped["max"]) * 100.0
                d["comment"] = f"Above pediatric guidance ({ped['max']} mg/kg/day) by {d['percent_above']:.1f}%"
            else:
                d["status"] = "within"
                d["comment"] = f"Within pediatric range ({ped['min']}-{ped['max']} mg/kg/day)"
    return d

# ------------------ ROUTES ------------------
@app.route("/")
def index():
    # pass drug list for autocomplete and baseline hits
    baseline_keys = list(dosing_baseline.keys())
    combined = sorted(list(set(unique_drugs + baseline_keys)))
    return render_template("index.html", drugs=combined)

@app.route("/autocomplete")
def autocomplete():
    q = request.args.get("q","").lower()
    res = [d for d in unique_drugs if q in d.lower()]
    return jsonify(res[:30])

@app.route("/predict", methods=["POST"])
def predict():
    payload = request.json or {}
    drugs_in = payload.get("drugs", [])
    is_pediatric = bool(payload.get("is_pediatric", False))
    age = payload.get("age", None)
    weight_kg = payload.get("weight_kg", None)

    # validate pediatric requires weight per your choice
    if is_pediatric and (weight_kg is None or weight_kg == 0):
        return jsonify({"error":"Pediatric mode requires patient weight (kg)."}), 400

    # normalize inputs
    cleaned = []
    for item in drugs_in:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        dose = item.get("dose") or 0
        unit = item.get("unit") or "mg"
        freq = item.get("freq") or 1
        route = item.get("route") or "oral"
        try:
            dosef = float(dose)
        except:
            dosef = 0.0
        try:
            freqf = float(freq)
        except:
            freqf = 1.0
        cleaned.append({"name": name, "dose": dosef, "unit": unit, "freq": freqf, "route": route})

    if len(cleaned) < 2:
        return jsonify({"error":"Enter at least two drugs with names and dose info."}), 400

    # evaluate doses
    dose_evals = {}
    for c in cleaned:
        ev = evaluate_dose(c['name'], c['dose'], c['unit'], c['freq'], c['route'],
                           is_pediatric=is_pediatric, age=age, weight_kg=weight_kg)
        dose_evals[c['name'].strip().lower()] = ev

    # pairwise predictions with dosage escalation
    pairs = []
    for a, b in itertools.combinations(cleaned, 2):
        name_a, name_b = a['name'], b['name']
        k = key_pair(name_a, name_b)
        if k in interaction_map:
            prob = 1.0; label = 1; found = True
        else:
            txt = f"Interaction between {name_a} and {name_b}"
            prob = float(model.predict_proba(tfidf.transform([txt]))[0][1])
            label = int(prob > 0.5); found = False

        ev_a = dose_evals.get(name_a.strip().lower(), {})
        ev_b = dose_evals.get(name_b.strip().lower(), {})
        escalation = 0.0
        for ev in (ev_a, ev_b):
            if ev.get("status") == "above":
                pct = min(ev.get("percent_above", 0.0), 200.0) / 200.0
                escalation += 0.12 + 0.38 * pct
        if is_pediatric and (ev_a.get("status")=="above" or ev_b.get("status")=="above"):
            escalation = max(escalation, 0.25)
        prob_adj = min(1.0, prob + escalation)
        label_adj = int(prob_adj > 0.5)

        # determine final risk level for this pair
        if prob_adj >= 0.85:
            risk = "High"
        elif prob_adj >= 0.5:
            risk = "Moderate"
        else:
            risk = "Low"

        pairs.append({
            "drug1": name_a, "drug2": name_b,
            "found": found,
            "prob": prob,
            "prob_adj": prob_adj,
            "label": label_adj,
            "risk": risk,
            "dose_eval_a": ev_a,
            "dose_eval_b": ev_b
        })

    # summary using adjusted probabilities
    total_pairs = len(pairs)
    risky_count = sum(1 for p in pairs if p["label"]==1)
    pct_risky = risky_count/total_pairs if total_pairs>0 else 0.0
    avg_conf = float(np.mean([p["prob_adj"] for p in pairs])) if pairs else 0.0
    combined_score = 0.6 * pct_risky + 0.4 * avg_conf
    if combined_score >= 0.7:
        level = "High"; color = "high"
    elif combined_score >= 0.4:
        level = "Moderate"; color = "moderate"
    else:
        level = "Low"; color = "low"

    summary = {
        "total_pairs": total_pairs,
        "risky_pairs": risky_count,
        "pct_risky": pct_risky,
        "avg_confidence": avg_conf,
        "combined_score": combined_score,
        "level": level,
        "color": color
    }

    # save history in session only
    history = session.get("history", [])
    history.insert(0, {"timestamp": datetime.utcnow().isoformat(), "drugs": [d["name"] for d in cleaned], "summary": summary})
    session["history"] = history[:50]

    return jsonify({"pairs": pairs, "summary": summary})

# history endpoint
@app.route("/history")
def history():
    return jsonify(session.get("history", []))

# csv export
@app.route("/export_csv", methods=["POST"])
def export_csv():
    pairs = request.json.get("pairs", [])
    df_out = pd.DataFrame(pairs)
    buf = io.StringIO()
    df_out.to_csv(buf, index=False)
    return send_file(io.BytesIO(buf.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="ddi_results.csv")

# pdf export
@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    body = request.json or {}
    pairs = body.get("pairs", [])
    summary = body.get("summary", {})
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(40, 780, "Drug Interaction Report")
    c.drawString(40, 760, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    y = 740
    c.drawString(40, y, f"Summary: Level={summary.get('level')} Combined Score={summary.get('combined_score'):.3f}")
    y -= 20
    for p in pairs:
        if y < 80:
            c.showPage(); y = 740
        line = f"{p['drug1']} + {p['drug2']} | prob_adj: {p['prob_adj']:.3f} | risk: {p['risk']}"
        c.drawString(40, y, line); y -= 14
        # include dose evals if present
        a_eval = p.get("dose_eval_a", {})
        b_eval = p.get("dose_eval_b", {})
        c.drawString(60, y, f"A: {a_eval.get('comment','')}" if a_eval else ""); y -= 12
        c.drawString(60, y, f"B: {b_eval.get('comment','')}" if b_eval else ""); y -= 14
    c.save()
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="ddi_report.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

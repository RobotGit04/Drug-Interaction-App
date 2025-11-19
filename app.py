from flask import Flask, render_template, request, jsonify, send_file
import itertools
import json
import pandas as pd
import joblib
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# -------------------------
# Load model + vectorizer
# -------------------------
model = joblib.load("models/ddi_model.pkl")
tfidf = joblib.load("models/tfidf.pkl")

# -------------------------
# Load interaction dataset
# -------------------------
df = pd.read_csv("data/processed.csv")

def key_pair(a, b):
    return tuple(sorted([a.strip().lower(), b.strip().lower()]))

interaction_map = {key_pair(r["drug1"], r["drug2"]): r["label"] for _, r in df.iterrows()}

# -------------------------
# Load baseline dose information
# -------------------------
try:
    with open("data/dosing_baseline.json", "r") as f:
        dosing_baseline = json.load(f)
except:
    dosing_baseline = {}

# -------------------------
# Evaluate dosage (informational only)
# -------------------------
def evaluate_dose(name, dose, freq, weight_kg=None):
    name_l = name.strip().lower()
    d = dosing_baseline.get(name_l)
    if not d:
        return {"status":"unknown", "comment":"No baseline dosing info available"}

    try:
        dose = float(dose)
    except:
        return {"status":"unknown", "comment":"Dose not interpretable"}

    freq = float(freq) if freq else 1
    total = dose * freq

    # Adult reference
    if "adult" in d:
        amin = d["adult"].get("min_mg_per_dose", 0)
        amax = d["adult"].get("max_mg_per_dose", 999999)

        if dose > amax:
            pct = ((dose - amax) / max(amax, 1)) * 100
            return {"status":"above", "percent_above":pct,
                    "comment":f"Above typical adult per-dose max ({amax} mg). ~{pct:.1f}% higher."}
        elif dose < amin:
            return {"status":"below", "comment":f"Below typical adult per-dose minimum ({amin} mg)."}
        else:
            return {"status":"within", "comment":"Within typical adult per-dose range."}

    return {"status":"unknown", "comment":"No baseline dose info available"}

# -------------------------
# Predict route
# -------------------------
@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    drugs = data["drugs"]
    is_pediatric = data["is_pediatric"]
    weight_kg = data.get("weight_kg")

    cleaned = [d for d in drugs if d["name"].strip()]
    if len(cleaned) < 2:
        return jsonify({"error":"At least two drugs required"}), 400

    # precompute dose evaluations
    dose_evals = {}
    for d in cleaned:
        dose = d.get("dose", 0)
        freq = d.get("freq", 1)
        dose_evals[d["name"].strip().lower()] = evaluate_dose(d["name"], dose, freq, weight_kg)

    pairs = []
    for a, b in itertools.combinations(cleaned, 2):
        name_a = a["name"]
        name_b = b["name"]
        k = key_pair(name_a, name_b)

        if k in interaction_map:
            prob = 1.0
            label = 1
            found = True
        else:
            txt = f"Interaction between {name_a} and {name_b}"
            prob = float(model.predict_proba(tfidf.transform([txt]))[0][1])
            label = int(prob > 0.5)
            found = False

        ev_a = dose_evals.get(name_a.strip().lower(), {})
        ev_b = dose_evals.get(name_b.strip().lower(), {})

        # dosage escalation
        escalation = 0.0
        for ev in (ev_a, ev_b):
            if ev.get("status") == "above":
                pct = min(ev.get("percent_above", 0.0), 200) / 200
                escalation += 0.12 + 0.38 * pct

        if is_pediatric and (
            ev_a.get("status")=="above" or ev_b.get("status")=="above"
        ):
            escalation = max(escalation, 0.25)

        prob_adj = min(1.0, prob + escalation)

        # risk level
        if prob_adj >= 0.85:
            risk = "High"
        elif prob_adj >= 0.5:
            risk = "Moderate"
        else:
            risk = "Low"

        # ---------  EFFECTS (Option A) ----------
        effects = []
        if risk == "High":
            effects = [
                "This combination may lead to stronger combined drug effects.",
                "The body may process one or both drugs differently when used together.",
                "Increased likelihood of experiencing general side effects."
            ]
        elif risk == "Moderate":
            effects = [
                "Possible additive drug effects.",
                "Drug levels or activity may be altered when taken together."
            ]

        pairs.append({
            "drug1": name_a,
            "drug2": name_b,
            "found": found,
            "prob": prob,
            "prob_adj": prob_adj,
            "label": label,
            "risk": risk,
            "effects": effects,
            "dose_eval_a": ev_a,
            "dose_eval_b": ev_b
        })

    risky = sum(1 for p in pairs if p["risk"] in ["High","Moderate"])
    summary_level = (
        "High" if any(p["risk"]=="High" for p in pairs)
        else "Moderate" if any(p["risk"]=="Moderate" for p in pairs)
        else "Low"
    )
    combined_score = max(p["prob_adj"] for p in pairs)

    summary = {
        "level": summary_level,
        "risky_pairs": risky,
        "total_pairs": len(pairs),
        "combined_score": combined_score
    }

    return jsonify({"pairs":pairs, "summary":summary})


# -------------------------
# Home
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -------------------------
# Export CSV
# -------------------------
@app.route("/export_csv", methods=["POST"])
def export_csv():
    rows = request.json["pairs"]
    df = pd.DataFrame(rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="ddi_results.csv"
    )

# -------------------------
# Export PDF
# -------------------------
@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    data = request.json
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)

    y = 750
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y, "DDI Report")
    y -= 30

    p.setFont("Helvetica", 10)
    for pair in data["pairs"]:
        line = f"{pair['drug1']} + {pair['drug2']} → {pair['risk']} ({pair['prob_adj']*100:.1f}%)"
        p.drawString(30, y, line)
        y -= 15
        if y < 40:
            p.showPage(); y = 750

    p.save()
    buf.seek(0)
    return send_file(
        buf, mimetype="application/pdf", as_attachment=True, download_name="ddi_report.pdf"
    )


if __name__ == "__main__":
    app.run(debug=True, port=10000)

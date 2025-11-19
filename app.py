import pandas as pd
import itertools
import joblib
import numpy as np
from flask import Flask, render_template, request, jsonify, session, send_file
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

import os
print("FILES:", os.listdir(), "MODELS:", os.listdir("models"), "DATA:", os.listdir("data"))

app = Flask(__name__)
app.secret_key = "cloud-safe-key"

# -------------------------
# FILE PATHS
# -------------------------
MODEL_PATH = "models/ddi_model.pkl"
VECT_PATH = "models/tfidf.pkl"
DATA_PATH = "data/processed.csv"   # Your dataset

# -------------------------
# LOAD MODEL + DATA
# -------------------------
model = joblib.load(MODEL_PATH)
tfidf = joblib.load(VECT_PATH)
df = pd.read_csv(DATA_PATH)

df.columns = [c.strip() for c in df.columns]

# Confirm actual columns
# Expected dataset columns:
#   drug1, drug2, label

# -------------------------
# NORMALIZE PAIRS FOR LOOKUP
# -------------------------
def key_pair(a, b):
    a, b = a.strip().lower(), b.strip().lower()
    return "||".join(sorted([a, b]))

# Build interaction map (NO DESCRIPTIONS in your dataset)
interaction_map = {}
for _, row in df.iterrows():
    k = key_pair(str(row["drug1"]), str(row["drug2"]))
    interaction_map[k] = ""      # no descriptions available

# Unique drug list (for autocomplete)
unique_drugs = sorted(
    list(set(df["drug1"].astype(str)).union(set(df["drug2"].astype(str))))
)

# -------------------------
# HOME PAGE
# -------------------------
@app.route("/")
def index():
    return render_template("index.html", drugs=unique_drugs)

# -------------------------
# MULTI-DRUG PREDICTION
# -------------------------
@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    drugs = [d.strip() for d in data["drugs"] if d.strip()]

    if len(drugs) < 2:
        return jsonify({"error": "Please enter at least two drugs."}), 400

    results = []

    for a, b in itertools.combinations(drugs, 2):
        k = key_pair(a, b)

        # Check if pair exists in dataset
        if k in interaction_map:
            prob = 1.0
            label = 1
            desc = ""
            found = True
        else:
            # ML Prediction
            found = False
            desc = ""
            text = f"Interaction between {a} and {b}"
            vector = tfidf.transform([text])
            prob = float(model.predict_proba(vector)[0][1])
            label = int(prob > 0.5)

        results.append({
            "drug1": a,
            "drug2": b,
            "prob": prob,
            "label": label,
            "found": found,
            "description": desc
        })

    # -------------------------
    # RISK CALCULATION
    # -------------------------
    risky = sum(r["label"] == 1 for r in results)
    total = len(results)

    pct_risky = risky / total
    avg_conf = np.mean([r["prob"] for r in results])
    combined = 0.6 * pct_risky + 0.4 * avg_conf

    if combined >= 0.7:
        level, color = "High", "high"
    elif combined >= 0.4:
        level, color = "Moderate", "moderate"
    else:
        level, color = "Low", "low"

    summary = {
        "total_pairs": total,
        "risky_pairs": risky,
        "pct_risky": pct_risky,
        "avg_confidence": avg_conf,
        "combined_score": combined,
        "level": level,
        "color": color
    }

    # Save to session history
    history = session.get("history", [])
    history.insert(0, {"drugs": drugs, "summary": summary})
    session["history"] = history[:20]

    return jsonify({"pairs": results, "summary": summary})


# -------------------------
# HISTORY
# -------------------------
@app.route("/history")
def history():
    return jsonify(session.get("history", []))


# -------------------------
# EXPORT CSV
# -------------------------
@app.route("/export_csv", methods=["POST"])
def export_csv():
    data = request.json["pairs"]
    df_out = pd.DataFrame(data)
    buffer = io.StringIO()
    df_out.to_csv(buffer, index=False)

    return send_file(
        io.BytesIO(buffer.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="interaction_results.csv"
    )


# -------------------------
# EXPORT PDF
# -------------------------
@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    data = request.json
    summary = data["summary"]
    pairs = data["pairs"]

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    c.drawString(50, 750, "Drug Interaction Report")
    c.drawString(50, 730, f"Generated: {datetime.now()}")

    y = 700
    for k, v in summary.items():
        c.drawString(50, y, f"{k}: {v}")
        y -= 20

    y -= 20
    c.drawString(50, y, "Pair Details:")
    y -= 20

    for p in pairs:
        line = f"{p['drug1']} + {p['drug2']}  →  Prob: {p['prob']:.2f}"
        c.drawString(50, y, line)
        y -= 15
        if y < 80:
            c.showPage()
            y = 750

    c.save()
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="interaction_report.pdf"
    )


# -------------------------
# RENDER START
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

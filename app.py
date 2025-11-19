import pandas as pd
import itertools
import joblib
import numpy as np
from flask import Flask, render_template, request, jsonify, session, send_file
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cloud-safe-key"

# File paths
MODEL_PATH = "models/ddi_model.pkl"
VECT_PATH = "models/tfidf.pkl"
DATA_PATH = "data/processed.csv"

# Load trained model
model = joblib.load(MODEL_PATH)
tfidf = joblib.load(VECT_PATH)
df = pd.read_csv(DATA_PATH)

# Preprocess dataset
df.columns = [c.strip() for c in df.columns]

# Normalize drug pairs for lookup
def key_pair(a, b):
    a, b = a.strip().lower(), b.strip().lower()
    return "||".join(sorted([a, b]))

interaction_map = {}
for i, row in df.iterrows():
    k = key_pair(str(row["Drug 1"]), str(row["Drug 2"]))
    interaction_map[k] = row.get("Interaction Description", "")

# Unique drug list
unique_drugs = sorted(
    list(set(df["Drug 1"].astype(str)).union(set(df["Drug 2"].astype(str))))
)

# Home page
@app.route("/")
def index():
    return render_template("index.html", drugs=unique_drugs)

# Multi-drug prediction API
@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    drugs = [d.strip() for d in data["drugs"] if d.strip()]

    if len(drugs) < 2:
        return jsonify({"error": "Enter at least 2 drugs"}), 400

    results = []
    for a, b in itertools.combinations(drugs, 2):
        k = key_pair(a, b)
        
        # Check if pair in dataset
        if k in interaction_map:
            prob = 1.0
            label = 1
            desc = interaction_map[k]
            found = True
        else:
            found = False
            desc = ""
            text = f"Interaction between {a} and {b}"
            prob = float(model.predict_proba(tfidf.transform([text]))[0][1])
            label = int(prob > 0.5)

        results.append({
            "drug1": a,
            "drug2": b,
            "prob": prob,
            "label": label,
            "found": found,
            "description": desc
        })

    # Compute risk
    risky = sum(r["label"] == 1 for r in results)
    total = len(results)

    pct_risky = risky / total
    avg_conf = np.mean([r["prob"] for r in results])
    combined = 0.6 * pct_risky + 0.4 * avg_conf

    if combined >= 0.7:
        level, color = "High", "red"
    elif combined >= 0.4:
        level, color = "Moderate", "orange"
    else:
        level, color = "Low", "green"

    summary = {
        "total_pairs": total,
        "risky_pairs": risky,
        "pct_risky": pct_risky,
        "avg_confidence": avg_conf,
        "combined_score": combined,
        "level": level,
        "color": color
    }

    # Update session history
    history = session.get("history", [])
    history.insert(0, {"drugs": drugs, "summary": summary})
    session["history"] = history[:20]

    return jsonify({"pairs": results, "summary": summary})

@app.route("/history")
def history():
    return jsonify(session.get("history", []))

# CSV export
@app.route("/export_csv", methods=["POST"])
def export_csv():
    data = request.json["pairs"]
    df_out = pd.DataFrame(data)
    buf = io.StringIO()
    df_out.to_csv(buf, index=False)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="results.csv"
    )

# PDF export
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
        line = f"{p['drug1']} + {p['drug2']} → Prob: {p['prob']:.2f}"
        c.drawString(50, y, line)
        y -= 15
        if y < 100:
            c.showPage()
            y = 750

    c.save()
    buffer.seek(0)

    return send_file(buffer, mimetype="application/pdf",
                     as_attachment=True, download_name="results.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

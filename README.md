<p align="center">
  <h2>Drug Interaction Predictor</h2>
  <p>
    A minimalistic, dosage-aware, machine-learning web application that predicts
    drug–drug interaction risk and displays safe, general informational effects.
  </p>
</p>

---

## 🚀 Features

- Multi-drug interaction prediction (2 or more drugs)
- ML-based classification using TF-IDF + Random Forest
- Combination of:
  - Dataset lookup  
  - Probability prediction  
  - Dose-based risk escalation  
- Clean, centered minimal UI
- Column-heading layout for clarity
- Informational “General Interaction Effects” for Moderate/High risk pairs
- Adult and pediatric dosage evaluation (informational only)
- Export results to CSV & PDF
- Fully cloud-deployed on Render (Flask + Gunicorn)

---

## 🧠 How It Works

### 1. User Input
You can enter:
- Drug name  
- Dose  
- Units (mg, g, mcg, mL, IU)  
- Frequency per day  
- Route of administration  

Pediatric mode allows:
- Weight (kg)
- Age (optional)

### 2. Backend Processing  
For each pair of drugs:
1. **Dataset matching** — checks if interaction is directly known.  
2. **Machine learning prediction** — TF-IDF text → Random Forest → probability.  
3. **Dosage awareness**  
   - If dose exceeds general adult ranges → risk escalates.  
   - Pediatric mg/kg calculations for informational comparison.

### 3. Interaction Effects (Updated)
For Moderate/High risk pairs, the app shows general, safe, non-medical effects:

#### **High Risk**
- Stronger combined drug effects  
- Body may process drugs differently  
- Increased likelihood of experiencing general side effects  

#### **Moderate Risk**
- Possible additive drug effects  
- Altered drug levels or activity  

🛈 These are **informational only** and **not** clinical recommendations.

### 4. Final Output
Displayed per pair:
- Risk Level (Low / Moderate / High)
- ML probability (raw and adjusted)
- Dataset match (Yes/No)
- Dose evaluation for each drug
- General interaction effects (if any)

---

## 📦 Project Structure

Drug-Interaction-App/
│
├── app.py                     # Flask backend (API, prediction, PDF/CSV export)
├── Procfile                   # Render deployment command
├── requirements.txt           # Python package dependencies
│
├── models/
│   ├── ddi_model.pkl          # Trained Random Forest model
│   └── tfidf.pkl              # TF-IDF vectorizer
│
├── data/
│   ├── processed.csv          # Cleaned interaction dataset
│   └── dosing_baseline.json   # Informational dosage baseline (no duplicates)
│
├── templates/
│   └── index.html             # Web interface (Bootstrap minimalist UI)
│
└── static/
    ├── style.css              # Centered, clean styling
    └── script.js              # UI logic, card builder, result rendering

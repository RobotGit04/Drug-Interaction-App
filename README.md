<p align="center">
  <h2>Drug Interaction Predictor</h2>
  <p>A minimalistic, centered web application for predicting drug–drug interaction risks using Machine Learning and dosage-aware evaluation.</p>
</p>

---

## 🚀 Features

- Multi-drug interaction prediction  
- Dosage-aware evaluation (adult + pediatric mg/kg/day)  
- ML-adjusted risk scoring  
- Minimalistic centered UI  
- Card-based drug entry system  
- CSV & PDF export  
- Cloud deployment using Flask + Render  

---

## 🧠 How It Works

1. User enters two or more drugs  
2. For each drug, the system accepts:
   - Dose
   - Unit (mg, g, mcg, mL, IU)
   - Frequency per day
   - Route of administration  
3. Pediatric mode (optional):
   - Requires weight input  
   - Performs mg/kg/day dosage evaluation  
4. ML model computes interaction probability  
5. Dosage rules adjust risk level  
6. Final output shows:
   - Low / Moderate / High risk  
   - Per-drug dosage evaluation  
   - Per-pair ML confidence  

---

## 📦 Project Structure


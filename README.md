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
- Card-based drug entry  
- Export results to CSV and PDF  
- Cloud deployment with Flask & Render  

---

## 🧠 How It Works

1. User enters two or more drugs  
2. For each drug, the user provides:
   - Dose
   - Unit (mg, g, mL, mcg, IU)
   - Frequency per day
   - Route of administration
3. Pediatric mode enables mg/kg/day dosage checking  
4. ML model predicts interaction probability  
5. Dosage rules escalate or reduce risk  
6. Final risk displayed:
   - Low
   - Moderate
   - High

---

## 📦 Project Structure


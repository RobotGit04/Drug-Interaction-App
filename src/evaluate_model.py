import pandas as pd
import joblib
from sklearn.metrics import confusion_matrix, roc_curve, auc
import matplotlib.pyplot as plt
import numpy as np

print("Loading model and vectorizer...")
model = joblib.load("models/ddi_model.pkl")
tfidf = joblib.load("models/tfidf.pkl")

df = pd.read_csv("data/processed.csv")

X_text = df["description"].fillna("")
y = df["label"]

X = tfidf.transform(X_text)
y_proba = model.predict_proba(X)[:, 1]
y_pred = model.predict(X)

# Confusion Matrix
cm = confusion_matrix(y, y_pred)
print("Confusion Matrix:")
print(cm)

plt.figure(figsize=(6, 6))
plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
plt.title("Confusion Matrix")
plt.colorbar()
plt.xlabel("Predicted")
plt.ylabel("True")
plt.savefig("models/confusion_matrix.png", dpi=300)
plt.close()

# ROC Curve
fpr, tpr, _ = roc_curve(y, y_proba)
roc_auc = auc(fpr, tpr)

plt.figure(figsize=(6, 6))
plt.plot(fpr, tpr, label=f"AUC = {roc_auc:.3f}")
plt.plot([0, 1], [0, 1], linestyle="--")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve")
plt.legend(loc="lower right")
plt.savefig("models/roc_curve.png", dpi=300)
plt.close()

print("Plots saved in models/ folder!")

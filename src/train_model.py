import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, mean_squared_error, r2_score
from imblearn.under_sampling import RandomUnderSampler
import joblib

print("Loading processed dataset...")
df = pd.read_csv("data/processed.csv")

X_text = df["description"].fillna("")  # text or empty
y = df["label"]

print("Vectorizing text with TF-IDF...")
tfidf = TfidfVectorizer(max_features=5000)
X = tfidf.fit_transform(X_text)

print("Splitting train and test...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print("Balancing classes with UNDERSAMPLING...")
rus = RandomUnderSampler(random_state=42)
X_train_res, y_train_res = rus.fit_resample(X_train, y_train)

print("Training RandomForest (n_estimators=300)...")
model = RandomForestClassifier(n_estimators=300, random_state=42)
model.fit(X_train_res, y_train_res)

print("Making predictions...")
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print("\n=== CLASSIFICATION REPORT ===")
print(classification_report(y_test, y_pred))

print("ROC-AUC:", roc_auc_score(y_test, y_proba))

mse = mean_squared_error(y_test, y_proba)
rmse = mse ** 0.5
r2 = r2_score(y_test, y_proba)

print("\nRegression-style metrics:")
print("MSE:", mse)
print("RMSE:", rmse)
print("R²:", r2)

print("Saving model and vectorizer...")
joblib.dump(model, "models/ddi_model.pkl")
joblib.dump(tfidf, "models/tfidf.pkl")

print("Training complete! Model saved.")

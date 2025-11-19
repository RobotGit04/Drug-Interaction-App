import joblib

# Load model and tfidf
model = joblib.load("models/ddi_model.pkl")
tfidf = joblib.load("models/tfidf.pkl")

def predict_interaction(drug1, drug2):
    # Create input text for TF-IDF
    text = f"Interaction between {drug1} and {drug2}"
    X = tfidf.transform([text])
    
    # Make predictions
    proba = model.predict_proba(X)[0][1]
    prediction = "YES (interaction likely)" if proba > 0.5 else "NO (interaction unlikely)"
    
    return prediction, round(proba * 100, 2)

# ----- USER INPUT -----
if __name__ == "__main__":
    d1 = input("Enter drug 1: ")
    d2 = input("Enter drug 2: ")

    result, confidence = predict_interaction(d1, d2)
    print("\nPREDICTION RESULT")
    print("--------------------")
    print(f"Interaction: {result}")
    print(f"Confidence: {confidence}%")

import pandas as pd
import numpy as np
import random
from itertools import product

# Load dataset
df = pd.read_csv("data/drug_drug_interactions.csv")
df.columns = ["drug1", "drug2", "description"]

# POSITIVE CLASS
df_pos = df.copy()
df_pos["label"] = 1

# Unique drug list
unique_drugs = list(set(df["drug1"]).union(set(df["drug2"])))

# Generate ALL possible pairs (cartesian product)
all_pairs = pd.DataFrame(list(product(unique_drugs, unique_drugs)), columns=["drug1", "drug2"])

# Remove self-pairs (Drug, Drug)
all_pairs = all_pairs[all_pairs["drug1"] != all_pairs["drug2"]]

# Mark positive pairs
df_pos_pairs = df_pos[["drug1", "drug2"]].drop_duplicates()
df_pos_pairs["pos"] = 1

# Merge to find negatives
merged = all_pairs.merge(df_pos_pairs, on=["drug1", "drug2"], how="left")
df_neg = merged[merged["pos"].isna()].copy()

# Randomly sample NEGATIVES = same count as positives
df_neg = df_neg.sample(n=len(df_pos), random_state=42)

# Add empty description + label 0
df_neg["description"] = ""
df_neg["label"] = 0

# Final dataset
df_final = pd.concat([df_pos, df_neg], ignore_index=True)

df_final.to_csv("data/processed.csv", index=False)

print("Dataset Ready!")
print(df_final["label"].value_counts())

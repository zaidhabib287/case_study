"""
Train a tiny baseline eligibility model on synthetic data.
Saves: /app/models/baseline.joblib
Features (order-sensitive!):
  [age, income, obligations_ratio, dependents, doc_count, avg_text_len]
"""
from __future__ import annotations
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import joblib
import os
rng = np.random.default_rng(42)

N = 3000

# synthetic features
age = rng.integers(18, 64, size=N)
income = rng.normal(5500, 1800, size=N).clip(min=0)
obl = rng.uniform(0, 0.8, size=N)                  # obligations ratio
deps = rng.integers(0, 4, size=N)                  # dependents
doc_count = rng.integers(0, 4, size=N)
avg_txt = rng.normal(1200, 500, size=N).clip(min=0)

X = np.vstack([age, income, obl, deps, doc_count, avg_txt]).T

# heuristic ground-truth for y (approval likelihood)
logit = (
    -4.0
    + 0.02 * (age - 18)
    + 0.0006 * income
    - 1.8 * obl
    - 0.25 * deps
    + 0.20 * doc_count
    + 0.0002 * avg_txt
)
p = 1 / (1 + np.exp(-logit))
y = (rng.uniform(0, 1, size=N) < p).astype(int)

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression(max_iter=1000))
])
pipe.fit(X, y)

os.makedirs("/app/models", exist_ok=True)
joblib.dump(pipe, "/app/models/baseline.joblib")
print("Saved model -> /app/models/baseline.joblib")

"""
Train a car selling-price prediction model from data/car_sales.json.

Usage:
    python train_model.py
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "car_sales.json"
MODEL_PATH = ROOT / "model" / "car_price_model.joblib"

NUMERIC_FEATURES = ["year", "km_driven"]
CATEGORICAL_FEATURES = ["brand", "fuel", "seller_type", "transmission", "owner"]
TARGET = "selling_price"


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    df = df.dropna(subset=NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET])
    return df


def build_pipeline():
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    model = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def main():
    df = load_data()
    print(f"Loaded {len(df)} records from {DATA_PATH}")

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    print(f"Test MAE:  {mae:,.0f}")
    print(f"Test R^2:  {r2:.4f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()

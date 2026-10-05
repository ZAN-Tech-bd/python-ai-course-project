"""
Interactive terminal tool to predict a used car's selling price.

Usage:
    python predict.py
"""

import json
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "model" / "car_price_model.joblib"
DATA_PATH = ROOT / "data" / "car_sales.json"


def load_known_values():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    brands = sorted({r["brand"] for r in records})
    fuels = sorted({r["fuel"] for r in records})
    seller_types = sorted({r["seller_type"] for r in records})
    transmissions = sorted({r["transmission"] for r in records})
    owners = sorted({r["owner"] for r in records})
    return brands, fuels, seller_types, transmissions, owners


def ask(prompt, choices=None, cast=str):
    while True:
        if choices:
            print(f"  options: {', '.join(choices)}")
        raw = input(f"{prompt}: ").strip()
        if choices and raw not in choices:
            print(f"  '{raw}' not recognized, please pick from the list above.")
            continue
        try:
            return cast(raw)
        except ValueError:
            print("  Invalid value, try again.")


def main():
    if not MODEL_PATH.exists():
        print("No trained model found. Run `python train_model.py` first.")
        return

    pipeline = joblib.load(MODEL_PATH)
    brands, fuels, seller_types, transmissions, owners = load_known_values()

    print("=== Car Sales Price Predictor ===")
    brand = ask("Brand", choices=brands)
    year = ask("Manufacture year (e.g. 2018)", cast=int)
    km_driven = ask("Kilometers driven (e.g. 40000)", cast=int)
    fuel = ask("Fuel type", choices=fuels)
    seller_type = ask("Seller type", choices=seller_types)
    transmission = ask("Transmission", choices=transmissions)
    owner = ask("Owner history", choices=owners)

    row = pd.DataFrame([{
        "brand": brand,
        "year": year,
        "km_driven": km_driven,
        "fuel": fuel,
        "seller_type": seller_type,
        "transmission": transmission,
        "owner": owner,
    }])

    prediction = pipeline.predict(row)[0]
    print(f"\nPredicted selling price: Rs {prediction:,.0f}")


if __name__ == "__main__":
    main()

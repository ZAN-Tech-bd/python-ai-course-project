"""
Add a car sale record to data/car_sales.json from the terminal.

Usage:
    python add_data.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "car_sales.json"


def load_records():
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_records(records):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def main():
    records = load_records()
    print(f"Current dataset has {len(records)} records.\n")

    name = input("Car name (e.g. 'Maruti Swift VDI'): ").strip()
    brand = name.split(" ")[0] if name else input("Brand: ").strip()
    year = int(input("Year: ").strip())
    selling_price = float(input("Selling price (Rs): ").strip())
    km_driven = int(input("Km driven: ").strip())
    fuel = input("Fuel (Petrol/Diesel/CNG/LPG/Electric): ").strip()
    seller_type = input("Seller type (Individual/Dealer/Trustmark Dealer): ").strip()
    transmission = input("Transmission (Manual/Automatic): ").strip()
    owner = input("Owner (First Owner/Second Owner/...): ").strip()

    records.append({
        "name": name,
        "brand": brand,
        "year": year,
        "selling_price": selling_price,
        "km_driven": km_driven,
        "fuel": fuel,
        "seller_type": seller_type,
        "transmission": transmission,
        "owner": owner,
    })

    save_records(records)
    print(f"\nSaved. Dataset now has {len(records)} records.")
    print("Run `python train_model.py` to retrain with the new data.")


if __name__ == "__main__":
    main()

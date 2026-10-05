"""
Convert a CarDekho-style CSV (name,year,selling_price,km_driven,fuel,
seller_type,transmission,owner) into records appended to data/car_sales.json.

Usage:
    python scripts/csv_to_json.py path/to/file.csv
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "data" / "car_sales.json"


def load_existing():
    if JSON_PATH.exists():
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def csv_to_records(csv_path):
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                records.append({
                    "name": row["name"].strip(),
                    "brand": row["name"].strip().split(" ")[0],
                    "year": int(row["year"]),
                    "selling_price": float(row["selling_price"]),
                    "km_driven": int(row["km_driven"]),
                    "fuel": row["fuel"].strip(),
                    "seller_type": row["seller_type"].strip(),
                    "transmission": row["transmission"].strip(),
                    "owner": row["owner"].strip(),
                })
            except (KeyError, ValueError):
                continue
    return records


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/csv_to_json.py path/to/file.csv")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        sys.exit(1)

    existing = load_existing()
    existing_keys = {
        (r["name"], r["year"], r["km_driven"], r["selling_price"]) for r in existing
    }

    new_records = csv_to_records(csv_path)
    added = 0
    for r in new_records:
        key = (r["name"], r["year"], r["km_driven"], r["selling_price"])
        if key not in existing_keys:
            existing.append(r)
            existing_keys.add(key)
            added += 1

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    print(f"Added {added} new records (skipped {len(new_records) - added} duplicates).")
    print(f"Total records in {JSON_PATH}: {len(existing)}")


if __name__ == "__main__":
    main()

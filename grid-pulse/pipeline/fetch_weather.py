"""Download hourly weather per city from Open-Meteo, at fixed UTC+10 to match NEM market time.

Weather data by Open-Meteo.com (https://open-meteo.com/), CC BY 4.0.
Region figures are weighted city averages. The weights are rounded approximations of population share.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path

import requests

POINTS = {
    "NSW1": [("Sydney", -33.87, 151.21, 0.8), ("Newcastle", -32.93, 151.78, 0.1), ("Wollongong", -34.42, 150.89, 0.1)],
    "QLD1": [("Brisbane", -27.47, 153.03, 0.7), ("Gold Coast", -28.02, 153.40, 0.2), ("Townsville", -19.26, 146.82, 0.1)],
    "SA1": [("Adelaide", -34.93, 138.60, 1.0)],
    "TAS1": [("Hobart", -42.88, 147.33, 0.6), ("Launceston", -41.43, 147.14, 0.4)],
    "VIC1": [("Melbourne", -37.81, 144.96, 0.9), ("Geelong", -38.15, 144.36, 0.1)],
}
URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch(start: str, end: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for region, cities in POINTS.items():
        for name, lat, lon, weight in cities:
            path = out / f"{region}_{name.replace(' ', '_')}.json"
            if path.exists():
                continue
            r = requests.get(URL, timeout=120, params={
                "latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
                "hourly": "temperature_2m,shortwave_radiation", "timezone": "Australia/Brisbane",
            })
            r.raise_for_status()
            body = r.json()
            if body.get("utc_offset_seconds") != 36000:
                raise ValueError(f"Expected UTC+10 for {name}, got {body.get('utc_offset_seconds')}")
            path.write_text(json.dumps({"region": region, "city": name, "weight": weight, "hourly": body["hourly"]}))
            time.sleep(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2019-01-01")
    p.add_argument("--end", default="2026-10-31")
    p.add_argument("--out", default="data/raw/weather", type=Path)
    a = p.parse_args()
    dt.date.fromisoformat(a.start)
    fetch(a.start, a.end, a.out)
    print("ok", len(list(a.out.glob('*.json'))))

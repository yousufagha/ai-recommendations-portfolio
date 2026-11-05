"""List every public data file with a direct link, so people and crawlers can find and fetch the data."""
from __future__ import annotations

import json
from pathlib import Path

RAW = "https://raw.githubusercontent.com/yousufagha/ai-recommendations-portfolio/main/"
DUBAI_LICENCE = "https://data.dubai/documents/d/guest/open-data-license-english-5-pdf"
DATASETS = [
    {"name": "Dubai real estate transactions", "publisher": "Dubai Land Department, via Data.Dubai", "source": "https://data.dubai/en/l/470061",
     "licence": DUBAI_LICENCE, "folder": "dubai-property/data/raw/transactions", "pattern": "*.csv.gz", "manifest": True},
    {"name": "Dubai rent contracts", "publisher": "Dubai Land Department, via Data.Dubai", "source": "https://data.dubai/en/l/468586",
     "licence": DUBAI_LICENCE, "folder": "dubai-property/data/raw/rents", "pattern": "*.csv.gz", "manifest": True},
    {"name": "Dubai residential sale price index", "publisher": "Dubai Land Department, via Data.Dubai", "source": "https://data.dubai/en/l/468732",
     "licence": DUBAI_LICENCE, "folder": "dubai-property/data/raw/price_index", "pattern": "*.csv", "manifest": False},
    {"name": "Australian electricity prices and demand", "publisher": "Australian Energy Market Operator", "source": "https://www.aemo.com.au/",
     "licence": "https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions", "folder": "grid-pulse/data/raw/aemo", "pattern": "*.csv", "manifest": False},
    {"name": "Australian city weather", "publisher": "Open-Meteo.com", "source": "https://open-meteo.com/",
     "licence": "https://open-meteo.com/en/licence", "folder": "grid-pulse/data/raw/weather", "pattern": "*.json", "manifest": False},
]


def build(root: Path) -> dict:
    out = []
    for d in DATASETS:
        folder = root / d["folder"]
        rows = {}
        if d["manifest"]:
            rows = {f["file"]: f["rows"] for f in json.loads((folder / "manifest.json").read_text())["files"]}
        files = []
        for path in sorted(folder.glob(d["pattern"])):
            entry = {"file": path.name, "url": RAW + f"{d['folder']}/{path.name}", "bytes": path.stat().st_size}
            if path.name in rows:
                entry["rows"] = rows[path.name]
            files.append(entry)
        info = {k: d[k] for k in ("name", "publisher", "source", "licence")}
        if rows:
            info["rows"] = sum(rows.values())
        out.append({**info, "files": files})
    return {"terms": "https://github.com/yousufagha/ai-recommendations-portfolio/blob/main/DATA.md", "datasets": out}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    catalog = build(root)
    (root / "docs" / "data-catalog.json").write_text(json.dumps(catalog, indent=1, ensure_ascii=False) + "\n")
    print(sum(len(d["files"]) for d in catalog["datasets"]), "files listed")

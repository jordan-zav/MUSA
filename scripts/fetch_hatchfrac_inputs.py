"""Use the documented-by-client public Mendeley file/folder API."""
import json
from pathlib import Path
import re

import requests

from fetch_extended_benchmarks import ROOT, META, download, extract


def api(suffix):
    url = "https://data.mendeley.com/public-api/datasets/zhs97tsdry/" + suffix
    response = requests.get(url, headers={"Accept": "application/vnd.mendeley-public-dataset.1+json"}, timeout=(10, 30))
    response.raise_for_status()
    return response.json()


def main():
    folders = api("folders/1")
    (META / "hatchfrac_folder_tree.json").write_text(json.dumps(folders, indent=2), encoding="utf-8")
    print("FOLDERS", str(folders)[:2000], flush=True)
    ids = ["root"] + [r["id"] for r in folders]
    files = []
    for identity in ids:
        rows = api(f"files?folder_id={identity}&version=1&$start=0&$limit=1000")
        if not isinstance(rows, list):
            raise ValueError("Expected file list")
        files.extend(rows)
    (META / "hatchfrac_all_files.json").write_text(json.dumps(files, indent=2), encoding="utf-8")
    records = []
    folder_rows = {r["id"]: r for r in folders}
    def folder_path(identity):
        row = folder_rows.get(identity)
        if row is None:
            return "root"
        return str(Path(folder_path(row["parent_id"])) / row["name"]) if row.get("parent_id") else row["name"]
    for file in files:
        name = file.get("filename", "")
        details = file.get("content_details", {})
        size = details.get("size", 0)
        parent = folder_path(file.get("folder_id"))
        print("FILE", parent, name, size, flush=True)
        if not parent.startswith("2DFractureNetworks"):
            continue  # MUSA analyzes planar traces; do not project 3D polygons silently
        if size > 100_000_000:
            continue
        if not name.lower().endswith((".zip", ".txt", ".mat", ".m", ".csv")) and name not in ("Output.cpp", "Input.cpp", "Boundary.cpp", "DifferentDistribution.cpp"):
            continue
        safe_name = Path(name).name
        record = download(details["download_url"], ROOT / "hatchfrac/original" / parent / safe_name, size=size)
        if safe_name.lower().endswith(".zip"):
            record["extracted"] = extract(Path(record["path"]), Path(record["path"]).with_suffix(""))
        records.append(record)
    if records:
        (ROOT / "hatchfrac/provenance.json").write_text(json.dumps(dict(doi="10.17632/zhs97tsdry.1", license="CC BY 4.0 in Mendeley metadata", files=records), indent=2), encoding="utf-8")
    # Author repository helper identifies which sample maps its own tests use.
    tree = json.loads((META / "fracpaq_tree.json").read_text())
    for name in ("testmaps.m", "FracPaQ User Guide v2.8.pdf"):
        from urllib.parse import quote
        url = "https://raw.githubusercontent.com/DaveHealy-github/FracPaQ/" + tree["sha"] + "/" + quote(name)
        record = download(url, ROOT / "fracpaq/original" / name)
        if name.endswith(".pdf"):
            import pymupdf
            with pymupdf.open(record["path"]) as pdf:
                pages = []
                for index, page in enumerate(pdf):
                    text = page.get_text()
                    if re.search("Hornelen|map1|map7|Odling", text, re.I):
                        pages.append(dict(page=index+1, text=text))
                (META / "fracpaq_hornelen_evidence.json").write_text(json.dumps(pages, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

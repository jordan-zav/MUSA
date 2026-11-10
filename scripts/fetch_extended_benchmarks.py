"""Download verified public inputs; data remain external to the plugin/repo."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import quote
import zipfile

import requests

ROOT = Path(os.environ.get("MUSA_BENCHMARK_DATA", Path(__file__).resolve().parents[1] / "data/benchmarks"))
META = ROOT / "extended_metadata"


def download(url, path, md5=None, size=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if size is not None and path.stat().st_size != size:
            raise ValueError(f"Existing size mismatch: {path}")
    else:
        partial = path.with_name(path.name + ".partial_" + str(time.time_ns()))
        with requests.get(url, stream=True, timeout=(15, 60)) as response:
            response.raise_for_status()
            with partial.open("xb") as stream:
                for block in response.iter_content(1024 * 1024):
                    stream.write(block)
        if size is not None and partial.stat().st_size != size:
            raise ValueError(f"Downloaded size mismatch; partial preserved: {partial}")
        partial.rename(path)
    digest, secure = hashlib.md5(usedforsecurity=False), hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            secure.update(block)
    if md5 and digest.hexdigest() != md5:
        raise ValueError(f"Checksum mismatch; preserved for inspection: {path}")
    return dict(url=url, path=str(path), bytes=path.stat().st_size, md5=digest.hexdigest(), sha256=secure.hexdigest())


def extract(archive, folder, masks_only=False):
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    with zipfile.ZipFile(archive) as stream:
        for entry in stream.infolist():
            if entry.is_dir():
                continue
            name = entry.filename.replace("\\", "/")
            if masks_only and not any(term in name.lower().split("/") for term in ("gt", "masks", "mask")):
                continue
            target = folder / name
            if not target.resolve().is_relative_to(folder.resolve()):
                raise ValueError("Unsafe archive path")
            if entry.file_size > 200_000_000:
                raise ValueError("Inspect unusually large individual file before extraction")
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                with stream.open(entry) as source, target.open("xb") as dest:
                    while block := source.read(1024 * 1024):
                        dest.write(block)
            paths.append(str(target.relative_to(folder)))
    return paths


def zenodo(name):
    record = json.loads((META / (name + ".json")).read_text())
    folder = ROOT / name
    file = record["files"][0]
    path = folder / Path(file["key"]).name
    result = download(file["links"]["self"], path, file["checksum"].split(":")[-1], file["size"])
    files = extract(path, folder / "original", masks_only=name == "fraxet")
    result.update(source=name, doi=record["doi"], license=record["metadata"].get("license"),
                  extracted_files=files, status="verified", author_archive=True)
    (folder / "provenance.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(name, "VERIFIED", result["bytes"], "extracted", len(files), flush=True)
    return result


def fracpaq():
    tree = json.loads((META / "fracpaq_tree.json").read_text())
    commit = tree["sha"]
    names = [r["path"] for r in tree["tree"] if r["type"] == "blob" and
             (r["path"].lower().startswith("map") or r["path"] in ("LICENSE", "README.md", "FracPaQ2D.m")
              or "read" in r["path"].lower())]
    records = []
    for name in names:
        url = "https://raw.githubusercontent.com/DaveHealy-github/FracPaQ/" + commit + "/" + quote(name)
        records.append(download(url, ROOT / "fracpaq/original" / name))
    result = dict(source="fracpaq", commit=commit, files=records, status="verified")
    (ROOT / "fracpaq/provenance.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("fracpaq VERIFIED", len(records), flush=True)
    return result


def inspect_hatchfrac():
    page = (META / "hatchfrac_page.html").read_text(encoding="utf-8")
    # Server state is data only. Never eval/execute scripts from author pages.
    snippets = []
    for token in ("download_url", "downloadUrl", "files", "api", "INITIAL_STATE"):
        matches = list(re.finditer(token, page))
        snippets += [page[max(0, m.start()-100):m.start()+350] for m in matches[:6]]
    (META / "hatchfrac_links.txt").write_text("\n".join(snippets), encoding="utf-8")
    return dict(source="hatchfrac", status="metadata_inspected", snippets=snippets[:8])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--large", action="store_true", help="Include the 2.6 GB FraXet original archive; extract masks only")
    args = parser.parse_args()
    functions = [lambda: zenodo("aland_zenodo"), lambda: zenodo("loviisa"), fracpaq, inspect_hatchfrac]
    if args.large:
        functions.append(lambda: zenodo("fraxet"))
    results = []
    def run(function):
        try:
            return function()
        except Exception as error:
            print(type(error).__name__, str(error), flush=True)
            return dict(status="failed", error=type(error).__name__ + ": " + str(error))
    with ThreadPoolExecutor(max_workers=3) as pool:
        for record in pool.map(run, functions):
            results.append(record)
    (ROOT / "extended_downloads.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

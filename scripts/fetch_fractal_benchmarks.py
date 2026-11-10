"""Fetch public author datasets, retaining provenance outside the code repository."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile

import requests


def md5(data):
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def fetch_archive(url, destination, expected_md5=None):
    if destination.exists():
        data = destination.read_bytes()
        if zipfile.is_zipfile(destination) and (expected_md5 is None or md5(data) == expected_md5):
            return data
        raise ValueError(f"Existing archive is not verified; preserve it and choose another destination: {destination}")
    attempts = []
    for index in range(3):
        candidate = url if index == 0 else url + ("&" if "?" in url else "?") + "musa_download=" + str(time.time_ns())
        try:
            response = requests.get(candidate, timeout=(15, 60))
            data = response.content
            attempts.append({"status": response.status_code, "bytes": len(data)})
            if response.ok and data[:2] == b"PK" and (expected_md5 is None or md5(data) == expected_md5):
                destination.write_bytes(data)
                (destination.parent / "download_attempts.json").write_text(json.dumps(attempts, indent=2), encoding="utf-8")
                return data
        except requests.RequestException as error:
            attempts.append({"error_type": type(error).__name__})
    (destination.parent / "download_attempts.json").write_text(json.dumps(attempts, indent=2), encoding="utf-8")
    raise RuntimeError(f"Could not download and verify {url}: {attempts}")


def extract_verified(archive, target):
    if target.exists():
        return
    with zipfile.ZipFile(archive) as stream:
        total = sum(info.file_size for info in stream.infolist())
        if total > 250_000_000:
            raise ValueError("Inspect archive size before extracting more than 250 MB.")
        root = target.resolve()
        for name in stream.namelist():
            path = (root / name).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Archive path escapes its destination.")
        assert stream.testzip() is None
        stream.extractall(target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("MUSA_BENCHMARK_DATA", Path(__file__).resolve().parents[1] / "data/benchmarks")))
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    # Fetch independent sources first so a 4TU outage does not prevent the
    # author-provided deterministic controls from being prepared.
    sahu = args.root / "sahu_roy_2020"
    sahu.mkdir(exist_ok=True)
    url = "https://adgeo.copernicus.org/articles/54/149/2020/adgeo-54-149-2020-supplement.zip"
    sahu_data = fetch_archive(url, sahu / "supplement.zip")
    extract_verified(sahu / "supplement.zip", sahu / "original")
    print("Sahu/Roy:", len(sahu_data), "bytes; original supplement extracted", flush=True)
    manifest = {
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "sahu_roy": {"doi": "10.5194/adgeo-54-149-2020", "supplement_url": url,
                     "article_license": "CC BY 4.0", "sha256": hashlib.sha256(sahu_data).hexdigest(),
                     "status": "verified"},
        "zhu": {"doi": "10.4121/14464893", "status": "pending"},
        "scope": "local research validation; no datasets included in the plugin ZIP",
    }
    (args.root / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    zhu = args.root / "zhu_2022_v2"
    zhu.mkdir(exist_ok=True)
    metadata = requests.get("https://api.figshare.com/v2/articles/14464893", timeout=30)
    metadata.raise_for_status()
    record = metadata.json()
    (zhu / "metadata_figshare.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    file = next(item for item in record["files"] if item["name"] == "DataShare.zip")
    try:
        data = fetch_archive(file["download_url"], zhu / file["name"], file["computed_md5"])
    except RuntimeError:
        manifest["zhu"] = {"doi": "10.4121/14464893", "version": record["version"],
                           "license": record["license"], "status": "download_failed_not_analyzed",
                           "attempts": str(zhu / "download_attempts.json")}
        (args.root / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        raise
    extract_verified(zhu / file["name"], zhu / "original")
    print("Zhu:", len(data), "bytes; checksum verified; license:", record["license"], flush=True)
    manifest = {
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "zhu": {"doi": "10.4121/14464893", "version": record["version"], "license": record["license"],
                "md5": file["computed_md5"], "sha256": hashlib.sha256((zhu / file["name"]).read_bytes()).hexdigest()},
        "sahu_roy": {"doi": "10.5194/adgeo-54-149-2020", "supplement_url": url,
                     "article_license": "CC BY 4.0", "sha256": hashlib.sha256(sahu_data).hexdigest()},
        "scope": "local research validation; no datasets included in the plugin ZIP",
    }
    (args.root / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for dataset in (zhu, sahu):
        print(dataset.name, [str(p.relative_to(dataset)) for p in (dataset / "original").rglob("*") if p.is_file()][:15])


if __name__ == "__main__":
    main()

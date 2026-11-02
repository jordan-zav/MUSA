"""Resolve author API links and inspect physical input formats, read-only."""
import json
from urllib.parse import quote

import geopandas as gpd
import requests

from fetch_extended_benchmarks import ROOT, META, download


def get(name, url):
    response = requests.get(url, timeout=(10, 25))
    path = META / (name + ".json")
    try:
        record = response.json()
    except ValueError:
        record = {"status": response.status_code, "body": response.text[:250]}
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(name, response.status_code, str(record)[:1200], flush=True)
    return record


def main():
    item = json.loads((META / "bristol_pid.json").read_text())
    bundles = get("bristol_bundles", item["_links"]["bundles"]["href"])
    for bundle in bundles.get("_embedded", {}).get("bundles", []):
        if bundle["name"] != "ORIGINAL":
            continue
        files = get("bristol_bitstreams", bundle["_links"]["bitstreams"]["href"])
        for file in files.get("_embedded", {}).get("bitstreams", []):
            if file["name"].lower().endswith((".mat", ".txt", ".pdf")):
                record = download(file["_links"]["content"]["href"], ROOT / "bristol/original" / file["name"],
                                  file.get("checkSum", {}).get("value"), file.get("sizeBytes"))
                (ROOT / "bristol/provenance.json").write_text(json.dumps(dict(source="bristol", doi="10.13020/ah7v-6n67", license="CC0-1.0", file=record), indent=2), encoding="utf-8")
                print("BRISTOL DOWNLOADED", record, flush=True)
    for kind in ("files", "folders"):
        get("hatchfrac_" + kind + "_all", f"https://data.mendeley.com/public-api/datasets/zhs97tsdry/{kind}?version=1")
    get("geocrack_datacite", "https://api.datacite.org/dois/10.7910/DVN/E4OXHQ")
    url = "https://zenodo.org/records/17069947/files/" + quote("FraXet_v0.1.zip")
    with requests.get(url, headers={"Range": "bytes=0-127"}, stream=True, timeout=(10, 20)) as response:
        data = next(response.iter_content(128), b"")
        print("FRAXET RANGE", response.status_code, response.headers.get("Content-Range"), len(data), data[:8], flush=True)
        (META / "fraxet_range.json").write_text(json.dumps(dict(url=url, status=response.status_code, content_range=response.headers.get("Content-Range"), first_bytes=data[:8].hex()), indent=2), encoding="utf-8")
    for source in ("aland_zenodo", "loviisa"):
        files = list((ROOT / source / "original").rglob("*.geojson")) + list((ROOT / source / "original").rglob("*.shp"))
        details = []
        for path in files:
            frame = gpd.read_file(path)
            details.append(dict(path=str(path), rows=len(frame), crs=str(frame.crs), types=frame.geom_type.value_counts().to_dict(),
                                bounds=frame.total_bounds.tolist(), columns=list(frame.columns)))
        (META / (source + "_layers.json")).write_text(json.dumps(details, indent=2), encoding="utf-8")
        print(source, "LAYERS", len(details), flush=True)


if __name__ == "__main__":
    main()

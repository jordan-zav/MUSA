"""Archive public source metadata without executing downloaded author code."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path("D:/DevResources/Shared/MUSA-benchmarks/extended_metadata")
SOURCES = {
    "geocrack_dataverse": "https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/E4OXHQ",
    "hatchfrac_files": "https://data.mendeley.com/public-api/datasets/zhs97tsdry/files?folder_id=root&version=1",
    "hatchfrac_files2": "https://data.mendeley.com/public-api/datasets/zhs97tsdry/versions/1/files",
    "bristol_pid": "https://conservancy.umn.edu/server/api/pid/find?id=11299/202350",
    "aland_tree": "https://api.github.com/repos/nialov/multi-scale-fracture-networks-aland-islands-2022/git/trees/master?recursive=1",
    "aland_zenodo": "https://zenodo.org/api/records/7919843",
    "fracpaq_tree": "https://api.github.com/repos/DaveHealy-github/FracPaQ/git/trees/master?recursive=1",
    "geocrack_tree": "https://api.github.com/repos/YaqoobAnsari/GeoCrack-A-High-Resolution-Dataset-of-Fracture-Edges-in-Geological-Outcrops/git/trees/main?recursive=1",
    "geocrack_page": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11615390/",
    "fraxet": "https://zenodo.org/api/records/17069947",
    "hatchfrac": "https://data.mendeley.com/public-api/datasets/zhs97tsdry/versions/1",
    "hatchfrac_page": "https://data.mendeley.com/datasets/zhs97tsdry/1",
    "bristol_doi": "https://api.datacite.org/dois/10.13020/ah7v-6n67",
    "bristol_page": "https://conservancy.umn.edu/handle/11299/202350",
    "loviisa": "https://zenodo.org/api/records/7077846",
}


def fetch(item):
    name, url = item
    result = dict(source=name, url=url, accessed_utc=datetime.now(timezone.utc).isoformat())
    try:
        response = requests.get(url, timeout=(15, 45))
        suffix = ".json" if "json" in response.headers.get("content-type", "") else ".html"
        path = ROOT / (name + suffix)
        path.write_bytes(response.content)
        result.update(status=response.status_code, bytes=len(response.content), path=str(path),
                      sha256=hashlib.sha256(response.content).hexdigest())
        if response.ok and suffix == ".json":
            record = response.json()
            if "tree" in record:
                interesting = [r for r in record["tree"] if any(v in r["path"].lower() for v in
                    (".gpkg", ".shp", ".mat", ".txt", ".csv", "license", "readme", ".zip"))]
                result["interesting"] = [dict(path=r["path"], size=r.get("size")) for r in interesting][:180]
            else:
                result["keys"] = list(record)[:20]
                if "files" in record:
                    result["files"] = record["files"]
                if "metadata" in record:
                    result["metadata"] = record["metadata"]
    except requests.RequestException as error:
        result["error"] = str(error)
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return result


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, SOURCES.items()))
    (ROOT / "inventory.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

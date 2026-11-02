"""Deterministically select FraXet test masks using standard HTTP Range reads.

The public server explicitly supports ranges. Each selected ZIP member is CRC
verified; this does not claim verification of the complete 2.6 GB archive MD5.
"""
import io
import json
from pathlib import Path
import re
import time
import zipfile

import requests

from fetch_extended_benchmarks import ROOT, META, download


class RangeReader(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.position = url, size, 0
        self.session = requests.Session()
        self.transferred = 0
        self.cache = {}
        self.last_request = 0.

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if target < 0:
            raise ValueError("Negative seek")
        self.position = target
        return target

    def read(self, size=-1):
        size = self.size - self.position if size < 0 else min(size, self.size - self.position)
        if size <= 0:
            return b""
        start, end = self.position, self.position + size - 1
        if size > 15_000_000:
            raise ValueError("Unexpected large range; inspect archive structure first")
        block_size = 4 * 1024 * 1024
        first, last = start // block_size, end // block_size
        blocks = []
        for block in range(first, last + 1):
            if block not in self.cache:
                lower, upper = block * block_size, min((block + 1) * block_size, self.size) - 1
                time.sleep(max(0., 1.1 - (time.monotonic() - self.last_request)))
                for attempt in range(3):
                    response = self.session.get(self.url, headers={"Range": f"bytes={lower}-{upper}"}, timeout=(10, 25))
                    self.last_request = time.monotonic()
                    if response.status_code != 429:
                        break
                    pause = min(60., max(30., float(response.headers.get("Retry-After", 60))))
                    print("RATE LIMIT: respecting backoff", pause, flush=True)
                    time.sleep(pause)
                response.raise_for_status()
                if response.status_code != 206 or response.headers.get("Content-Range") != f"bytes {lower}-{upper}/{self.size}":
                    raise ValueError("Server did not honor the exact requested range")
                if len(response.content) != upper - lower + 1:
                    raise ValueError("Truncated range")
                self.cache[block] = response.content
                self.transferred += len(response.content)
            blocks.append(self.cache[block])
        data = b"".join(blocks)[start - first * block_size:start - first * block_size + size]
        self.position += size
        return data


def main():
    record = json.loads((META / "fraxet.json").read_text())
    file = record["files"][0]
    url = "https://zenodo.org/records/17069947/files/FraXet_v0.1.zip"
    reader = RangeReader(url, file["size"])
    folder = ROOT / "fraxet_selected"
    folder.mkdir(exist_ok=True)
    with zipfile.ZipFile(reader) as archive:
        names = archive.namelist()
        (folder / "archive_members.json").write_text(json.dumps(names, indent=2), encoding="utf-8")
        candidates = [n for n in names if "__MACOSX/" not in n and not Path(n).name.startswith("._")
                      and "/test/" in n.lower() and "/gt/" in n.lower()
                      and n.lower().endswith((".png", ".tif", ".tiff"))]
        if not candidates:
            print("INSPECT DIRECTORY NAMES", names[:45], flush=True)
            return
        families = {}
        for name in sorted(candidates):
            prefix = name.lower().split("/test/")[0]
            families.setdefault(prefix, []).append(name)
        chosen = [name for family in sorted(families) for name in families[family][:8]]
        records = []
        import hashlib
        for index, name in enumerate(chosen):
            path = folder / "original" / name
            if not path.resolve().is_relative_to((folder / "original").resolve()):
                raise ValueError("Unsafe archive member")
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(archive.read(name))
            data = path.read_bytes()
            import binascii
            assert binascii.crc32(data) == archive.getinfo(name).CRC
            records.append(dict(member=name, path=str(path), sha256=hashlib.sha256(data).hexdigest(), crc32=archive.getinfo(name).CRC))
            print("MASK", index + 1, len(chosen), name, flush=True)
        provenance = dict(doi=record["doi"], license=record["metadata"]["license"], url=url,
                          selection="first eight sorted test/gt mask members per source family; before analysis",
                          families={k: len(v) for k, v in families.items()}, files=records,
                          integrity="selected original member CRC32 and local SHA256; complete archive MD5 not verified",
                          transferred_bytes=reader.transferred)
        (folder / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
        print("SELECTED COMPLETE", len(records), "transferred", reader.transferred, flush=True)


def hatchfrac_links():
    page = (META / "hatchfrac_page.html").read_text(encoding="utf-8")
    sources = re.findall(r'<script[^>]+src="([^"]+)"', page)
    print("HATCHFRAC SCRIPTS", sources, flush=True)
    for index, url in enumerate(sources):
        if ("mendeley" in url or url.startswith("/") and not url.startswith("//")) and "newrelic" not in url and "onetrust" not in url:
            url = "https://data.mendeley.com" + url if url.startswith("/") else url
            path = META / f"hatchfrac_client_{index}.js"
            download(url, path)
            script = path.read_text(encoding="utf-8")
            matches = list(re.finditer("folder_id|public-api|/folders", script))
            snippets = [script[max(0, m.start()-180):m.start()+250] for m in matches]
            (META / f"hatchfrac_client_{index}_links.txt").write_text("\n".join(snippets), encoding="utf-8")
            print("CLIENT", index, "matches", len(snippets), flush=True)


if __name__ == "__main__":
    import sys
    hatchfrac_links() if "--hatchfrac" in sys.argv else main()

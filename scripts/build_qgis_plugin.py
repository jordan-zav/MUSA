"""Build an installable plugin with a private copy of the shared Python core."""

import argparse
import configparser
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


def build_plugin(repo, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    metadata = configparser.ConfigParser()
    metadata.read(repo / "qgis_plugin/metadata.txt", encoding="utf-8")
    version = metadata["general"]["version"]
    files = []
    for folder, archive_root, extensions in (
        (repo / "qgis_plugin", "musa_qgis", {".py", ".txt", ".md"}),
        (repo / "src/musa", "musa_qgis/_core/musa", {".py", ".png", ".qml"}),
    ):
        for source in sorted(folder.rglob("*")):
            if not source.is_file() or source.suffix.lower() not in extensions or "__pycache__" in source.parts:
                continue
            if not source.resolve().is_relative_to(repo):
                raise ValueError(f"File outside repository: {source}")
            if source.name == "interface.py":
                continue  # Tk desktop UI is legacy; it does not ship inside QGIS.
            files.append((source, archive_root + "/" + source.relative_to(folder).as_posix()))
    for source, name in ((repo / "LICENSE", "LICENSE"), (repo / "docs/QGIS.md", "QGIS.md")):
        files.append((source, "musa_qgis/" + name))
    manifest = {"version": version, "files": {}}
    output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = output / f"musa_qgis_{version}_{timestamp}.zip"
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("musa_qgis/_core/__init__.py", "")
        for source, name in files:
            data = source.read_bytes()
            archive.writestr(name, data)
            manifest["files"][name] = hashlib.sha256(data).hexdigest()
        archive.writestr("musa_qgis/build_manifest.json", json.dumps(manifest, indent=2))
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "dist/qgis")
    args = parser.parse_args()
    print(build_plugin(Path(__file__).resolve().parents[1], args.output))

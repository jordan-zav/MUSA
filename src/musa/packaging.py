from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


def package_run_output(
    output_dir: str | Path,
    run_name: str | None = None,
    run_config: dict[str, Any] | None = None,
    execution_log: str = "",
) -> dict[str, str]:
    out_dir = Path(output_dir)
    if not out_dir.is_dir():
        raise FileNotFoundError(f"No existe el directorio de salida: {out_dir}")

    safe_name = _safe_run_name(run_name or f"MUSA_Run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    zip_path = out_dir / f"{safe_name}.zip"
    if zip_path.exists():
        zip_path.unlink()

    readme = _build_readme(safe_name)
    config_json = json.dumps(_json_safe(run_config or {}), indent=2, sort_keys=True, ensure_ascii=False)
    manifest: list[dict[str, str]] = []

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _write_text(zf, safe_name, "README.txt", readme)
        _write_text(zf, safe_name, "metadata/run_config.json", config_json + "\n")
        _write_text(zf, safe_name, "logs/execution_log.txt", execution_log)
        for file_path in sorted(p for p in out_dir.iterdir() if p.is_file() and p.name != zip_path.name):
            category = _category_for_file(file_path.name)
            arcname = f"{safe_name}/{category}/{file_path.name}"
            zf.write(file_path, arcname)
            manifest.append({"file": file_path.name, "category": category, "archive_path": arcname})
        _write_text(
            zf,
            safe_name,
            "metadata/manifest.json",
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        )

    return {"zip_path": str(zip_path), "run_name": safe_name}


def _safe_run_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    return cleaned.strip("._-") or f"MUSA_Run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _write_text(zf: zipfile.ZipFile, root: str, relative_path: str, text: str) -> None:
    zf.writestr(f"{root}/{relative_path}", text.encode("utf-8"))


def _category_for_file(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".svg")):
        return "figures"
    if lower.endswith((".gpkg", ".shp", ".shx", ".dbf", ".prj", ".cpg", ".geojson")):
        return "gis"
    if lower in {"analysis_report.csv", "analysis_scale_diagnostics.csv", "spectrum_fit_summary.csv"}:
        return "analysis"
    if "diagnostic" in lower or "sensitivity" in lower:
        return "diagnostics"
    if lower.endswith(".csv") and ("mother" in lower or "structural" in lower or "network" in lower):
        return "mother_cells"
    if lower.endswith(".csv"):
        return "tables"
    if lower.endswith((".txt", ".json", ".md")):
        return "metadata"
    return "misc"


def _build_readme(run_name: str) -> str:
    return (
        f"{run_name}\n\n"
        "MUSA output package\n\n"
        "analysis: global multifractal reports and spectrum diagnostics.\n"
        "mother_cells: mother-cell CSV outputs for local multifractal, monofractal, structural and network metrics.\n"
        "gis: GIS-ready vector outputs such as GeoPackage layers.\n"
        "figures: exported PNG figures.\n"
        "diagnostics: scale diagnostics, zeta sensitivity and uncertainty outputs.\n"
        "metadata: run configuration and file manifest.\n"
        "logs: execution log copied from the GUI session.\n\n"
        "Interpretation note: zeta is a local reliability weight, not a physical fractal dimension.\n"
    )

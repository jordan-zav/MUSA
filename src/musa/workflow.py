"""Host-independent run configuration and execution, using the existing core."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from threading import Lock

import numpy as np

from .control import AnalysisCancelled, check_cancelled
from .core import MUSA

_RUN_LOCK = Lock()  # Matplotlib and GIS writers must not run concurrently here.


@dataclass(frozen=True)
class RunConfig:
    mother_cell_m: float = 4000.0
    divisors: tuple = (2, 4, 6, 8, 16)
    q_min: float = -4.0
    q_max: float = 4.0
    q_step: float = 1.0
    threshold_m: float = 0.01
    min_r2: float = 0.9
    local: bool = True
    structural: bool = True
    network: bool = False
    plots: bool = True
    gis: bool = True
    bootstrap_iterations: int = 0
    local_bootstrap_iterations: int = 0
    bootstrap_ci: float = 0.95
    seed: int = 42
    negative_q_floor_fraction: float = 0.0
    reliable_min_zeta: float = 0.15
    zeta_exponents: tuple = (1.0, 1.0, 1.0, 1.0)
    zeta_scale_floor: float = 0.25
    zeta_sensitivity: bool = False
    moving: bool = False
    window_sizes_m: tuple = (2000.0, 4000.0, 8000.0)
    window_step_m: float = 1000.0
    moving_divisors: tuple = (2, 4, 8, 16)
    origin_ensemble: bool = False
    proximity_radii_m: tuple = ()

    def validate(self):
        values = (
            self.mother_cell_m,
            self.q_min,
            self.q_max,
            self.q_step,
            self.threshold_m,
            self.min_r2,
            self.bootstrap_ci,
            self.negative_q_floor_fraction,
            self.reliable_min_zeta,
            self.zeta_scale_floor,
        )
        if not np.isfinite(values).all():
            raise ValueError("Parameters must be finite.")
        if self.mother_cell_m <= 0 or self.threshold_m < 0 or not 0 <= self.min_r2 < 1:
            raise ValueError("Use positive mother size, nonnegative length threshold and R2 in [0,1).")
        if not -100 <= self.q_min <= self.q_max <= 100 or self.q_step <= 0:
            raise ValueError("Use -100 <= q min <= q max <= 100 and a positive q step.")
        if (self.q_max - self.q_min) / self.q_step > 400:
            raise ValueError("Use at most 401 q values.")
        div = np.asarray(self.divisors, dtype=float)
        if (
            div.ndim != 1
            or len(div) < 4
            or not np.isfinite(div).all()
            or (div < 2).any()
            or (div != np.floor(div)).any()
            or len(set(div)) != len(div)
        ):
            raise ValueError("Use at least four distinct integer divisors >= 2.")
        if any(
            type(v) is not int or not 0 <= v <= 10000
            for v in (self.bootstrap_iterations, self.local_bootstrap_iterations)
        ):
            raise ValueError("Bootstrap iterations must be integers from 0 to 10000.")
        if type(self.seed) is not int or self.seed < 0 or not 0 < self.bootstrap_ci < 1:
            raise ValueError("Use a nonnegative integer seed and confidence in (0,1).")
        MUSA._normalize_zeta_exponents(self.zeta_exponents)
        if (
            self.negative_q_floor_fraction < 0
            or not 0 <= self.reliable_min_zeta <= 1
            or not 0 <= self.zeta_scale_floor <= 1
        ):
            raise ValueError("Invalid negative-q floor or zeta configuration.")
        if self.moving:
            for values in (self.window_sizes_m, self.moving_divisors):
                if not len(values) or not np.isfinite(values).all() or min(values) <= 0:
                    raise ValueError("Window sizes and divisors must be positive and finite.")
            if len(set(self.moving_divisors)) < 4 or any(v < 2 or int(v) != v for v in self.moving_divisors):
                raise ValueError("Moving windows require four distinct integer divisors >= 2.")
            if not np.isfinite(self.window_step_m) or self.window_step_m <= 0:
                raise ValueError("Window spacing must be positive and finite.")
            if self.proximity_radii_m and (
                not np.isfinite(self.proximity_radii_m).all() or min(self.proximity_radii_m) <= 0
            ):
                raise ValueError("Proximity radii must be positive and finite.")
        for name in ("local", "structural", "network", "plots", "gis", "zeta_sensitivity", "moving", "origin_ensemble"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean.")
        return self

    def q_values(self):
        self.validate()
        count = int(np.floor((self.q_max - self.q_min) / self.q_step + 1e-10)) + 1
        return self.q_min + np.arange(count) * self.q_step

    def recipe(self):
        self.validate()
        return json.loads(json.dumps({"format": "musa-analysis", "version": 1, "parameters": asdict(self)}))

    @classmethod
    def from_recipe(cls, recipe):
        if recipe.get("format") != "musa-analysis" or recipe.get("version") != 1:
            raise ValueError("Expected a musa-analysis version 1 recipe.")
        return cls(**recipe["parameters"]).validate()


def execute_analysis(
    analyzer, config, output_dir, *, source_info=None, cancelled=None, progress=None, gis_exporter=None
):
    """Reserve a NEW output folder; retain partial results on failure/cancel.

    Cancellation is cooperative between scales, mother cells and workflow stages.
    Existing outputs are never overwritten. The manifest records file hashes.
    """
    config.validate()
    check_cancelled(cancelled)
    out = Path(output_dir)
    from . import __version__

    manifest = {
        "format": "musa-run",
        "version": 1,
        "software_version": __version__,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "recipe": config.recipe(),
        "source": source_info or {},
        "outputs": {},
        "files": {},
    }
    if not _RUN_LOCK.acquire(blocking=False):
        raise RuntimeError("Another MUSA analysis is running. Wait for it to finish.")
    reserved = False

    def stage(percent, message):
        check_cancelled(cancelled)
        if progress:
            progress(percent, message)

    try:
        out.mkdir(parents=True, exist_ok=False)
        reserved = True
        (out / "recipe.json").write_text(json.dumps(config.recipe(), indent=2), encoding="utf-8")
        (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        analyzer.q_values = config.q_values()
        scales = MUSA.resolutions_from_mother_cell(config.mother_cell_m, config.divisors, include_mother=True)
        stage(5, "Computing global multifractal spectra")
        result = analyzer.run_analysis(
            resolutions_m=scales,
            cell_length_threshold_m=config.threshold_m,
            min_r2=config.min_r2,
            bootstrap_iterations=config.bootstrap_iterations,
            bootstrap_ci=config.bootstrap_ci,
            bootstrap_seed=config.seed,
            negative_q_floor_fraction=config.negative_q_floor_fraction,
            cancelled=cancelled,
        )
        outputs = manifest["outputs"]
        outputs["analysis_report"] = MUSA.export_analysis_report(out, result)
        outputs["scale_diagnostics"] = MUSA.export_analysis_scale_diagnostics(out, result)
        from .spectrum import write_spectrum_fit_summary

        outputs["spectrum_fit"] = write_spectrum_fit_summary(out, result)
        if config.local:
            stage(25, "Computing mother cells and numerical reliability")
            outputs.update(
                analyzer.export_cell_outputs(
                    out,
                    scales,
                    cell_length_threshold_m=config.threshold_m,
                    q_values=analyzer.q_values,
                    reliable_min_zeta=config.reliable_min_zeta,
                    reliable_min_r2=config.min_r2,
                    local_bootstrap_iterations=config.local_bootstrap_iterations,
                    local_bootstrap_ci=config.bootstrap_ci,
                    local_bootstrap_seed=config.seed,
                    negative_q_floor_fraction=config.negative_q_floor_fraction,
                    zeta_exponents=config.zeta_exponents,
                    zeta_scale_floor=config.zeta_scale_floor,
                    export_zeta_sensitivity=config.zeta_sensitivity,
                    export_structural_stats=config.structural,
                    export_network_stats=config.network,
                    export_gis_package=False,
                    cancelled=cancelled,
                )
            )
        elif config.structural or config.network:
            stage(35, "Computing structural statistics")
            if config.structural:
                from .structural import compute_lineament_mother_structural_stats

                rows = compute_lineament_mother_structural_stats(
                    analyzer._line_geometries, analyzer._boundary_geom, config.mother_cell_m, origin=analyzer._origin
                )
                target = out / "lineament_mother_structural_stats.csv"
                MUSA._write_rows_csv(target, rows)
                outputs["structural_stats"] = str(target)
            if config.network:
                from .network import compute_lineament_network_stats

                rows = [compute_lineament_network_stats(analyzer._line_geometries, analyzer._boundary_geom)]
                target = out / "lineament_network_stats.csv"
                MUSA._write_rows_csv(target, rows)
                outputs["network_stats"] = str(target)
        if config.gis and (config.local or config.structural):
            stage(55, "Exporting spatial layers")
            if gis_exporter:
                outputs.update(gis_exporter(out, analyzer._active_crs, config))
            elif config.local:
                from .geomatics import export_mother_geopackage

                outputs["mother_geopackage"] = export_mother_geopackage(
                    out, analyzer._active_crs, reliable_min_zeta=config.reliable_min_zeta, reliable_min_r2=config.min_r2
                )["geopackage"]
        if config.moving:
            stage(65, "Computing experimental moving windows and topology")
            from .moving import ENSEMBLE_OFFSETS, export_moving_windows

            # CRS decoding only: coordinate transforms have already been done by the host.
            from pyproj import CRS

            analyzer._active_crs = CRS.from_user_input(analyzer._active_crs)
            outputs.update(
                export_moving_windows(
                    analyzer,
                    out,
                    config.window_sizes_m,
                    config.window_step_m,
                    q_values=analyzer.q_values,
                    divisors=config.moving_divisors,
                    origin_offsets=ENSEMBLE_OFFSETS if config.origin_ensemble else None,
                    proximity_radii_m=config.proximity_radii_m or None,
                    export_gis=config.gis,
                    min_r2=config.min_r2,
                    reliable_min_zeta=config.reliable_min_zeta,
                    zeta_exponents=config.zeta_exponents,
                    zeta_scale_floor=config.zeta_scale_floor,
                    progress=lambda message: stage(65, message),
                )
            )
        if config.plots:
            stage(85, "Rendering spectrum and reliability figures")
            from .plotting import export_analysis_plots, export_mother_plots

            outputs.update(export_analysis_plots(out, result))
            if config.local:
                outputs.update(export_mother_plots(out, result))
        stage(98, "Writing reproducibility manifest")
        manifest.update(status="complete", accepted_q=result.accepted_count, rejected_q=result.rejected_count)
    except AnalysisCancelled as exc:
        manifest.update(status="cancelled", error=str(exc))
        raise
    except Exception as exc:
        manifest.update(status="failed", error=str(exc))
        raise
    finally:
        try:
            if reserved:
                manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
                for file in sorted(out.rglob("*")):
                    if file.is_file() and file.name != "run_manifest.json":
                        manifest["files"][file.relative_to(out).as_posix()] = hashlib.sha256(
                            file.read_bytes()
                        ).hexdigest()
                (out / "run_manifest.json").write_text(
                    json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8"
                )
        finally:
            _RUN_LOCK.release()
    if progress:
        progress(100, "Analysis complete")
    return manifest

"""Run with QGIS Python, not pytest; real runtime, isolated profile, bundled core."""

# ruff: noqa: E402
import argparse
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import zipfile

faulthandler.enable()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("bundle", type=Path)
args = parser.parse_args()
session = Path(os.environ["DEVRESOURCES_SESSION"]) / "qgis_smoke"
session.mkdir()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = str(session / "profile")
os.environ["QGIS_AUTH_DB_DIR_PATH"] = str(session / "profile/auth")
with zipfile.ZipFile(args.bundle) as archive:
    assert all(name.startswith("musa_qgis/") and ".." not in Path(name).parts for name in archive.namelist())
    assert not any("interface.py" in name or "data/" in name for name in archive.namelist())
    archive.extractall(session / "plugins")
build = json.loads((session / "plugins/musa_qgis/build_manifest.json").read_text())
for name, digest in build["files"].items():
    assert hashlib.sha256((session / "plugins" / name).read_bytes()).hexdigest() == digest
sys.path.insert(0, str(session / "plugins"))

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsPointXY,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase
from qgis.PyQt.QtWidgets import QMainWindow
from qgis.gui import QgsMapCanvas
from osgeo import ogr
import numpy as np

app = QgsApplication([], True)
app.initQgis()
font = Path("C:/Windows/Fonts/arial.ttf")
if font.is_file():
    QFontDatabase.addApplicationFont(str(font))
    app.setFont(QFont("Arial", 10))
sys.path.insert(0, str(Path(QgsApplication.prefixPath()) / "python/plugins"))
from processing.core.Processing import Processing

Processing.initialize()
import processing
from musa_qgis import classFactory
from musa_qgis.inputs import make_analyzer, snapshot_sources, validate_metric_crs
from musa_qgis.runtime import core

MUSA, RunConfig, execute = core()
project = QgsProject.instance()
crs = QgsCoordinateReferenceSystem("EPSG:32718")
project.setCrs(crs)
lines = QgsVectorLayer("LineString?crs=EPSG:32718", "Synthetic lineaments", "memory")
boundary = QgsVectorLayer("Polygon?crs=EPSG:32718", "Synthetic boundary", "memory")
rng = np.random.default_rng(42)
features = []
for i in range(32):
    feature = QgsFeature(lines.fields())
    if i % 2:
        y = 8600000 + rng.uniform(30, 3970)
        geometry = QgsGeometry.fromPolylineXY([QgsPointXY(400000, y), QgsPointXY(404000, y + rng.uniform(-100, 100))])
    else:
        x = 400000 + rng.uniform(30, 3970)
        geometry = QgsGeometry.fromPolylineXY([QgsPointXY(x, 8600000), QgsPointXY(x + rng.uniform(-100, 100), 8604000)])
    feature.setGeometry(geometry)
    features.append(feature)
lines.dataProvider().addFeatures(features)
lines.updateExtents()
feature = QgsFeature(boundary.fields())
feature.setGeometry(
    QgsGeometry.fromWkt("POLYGON((400000 8600000,404000 8600000,404000 8604000,400000 8604000,400000 8600000))")
)
boundary.dataProvider().addFeatures([feature])
boundary.updateExtents()
project.addMapLayers([boundary, lines])
boundary.renderer().setSymbol(
    QgsFillSymbol.createSimple({"color": "233,239,233,255", "outline_color": "#61746b", "outline_width": "0.4"})
)
lines.renderer().setSymbol(QgsLineSymbol.createSimple({"line_color": "#244e68", "line_width": "0.4"}))
snapshot = snapshot_sources(lines, boundary, crs)
config = RunConfig(mother_cell_m=2000, divisors=(2, 4, 8, 16), q_min=-2, q_max=2, min_r2=0.1)


class Interface:
    def __init__(self):
        self.window = QMainWindow()
        self.window.resize(1500, 1040)
        self.window.setWindowTitle("QGIS — MUSA Workbench | Synthetic demonstration")
        self.canvas = QgsMapCanvas(self.window)
        self.canvas.setCanvasColor(QColor("#f4f6f7"))
        self.window.setCentralWidget(self.canvas)
        self.menu = self.window.menuBar().addMenu("Vector")
        self.toolbar = self.window.addToolBar("MUSA")

    def mainWindow(self):
        return self.window

    def activeLayer(self):
        return lines

    def addPluginToVectorMenu(self, _name, action):
        self.menu.addAction(action)

    def removePluginVectorMenu(self, _name, action):
        self.menu.removeAction(action)

    def addToolBarIcon(self, action):
        self.toolbar.addAction(action)

    def removeToolBarIcon(self, action):
        self.toolbar.removeAction(action)

    def addDockWidget(self, area, dock):
        self.window.addDockWidget(area, dock)

    def removeDockWidget(self, dock):
        self.window.removeDockWidget(dock)


def wait_until(predicate, seconds=120):
    limit = time.monotonic() + seconds
    while time.monotonic() < limit:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for QGIS task")


plugin = classFactory(None)
plugin.initProcessing()
assert sorted(a.id() for a in plugin.provider.algorithms()) == ["musa:analyze", "musa:run_recipe", "musa:scaling_support"]
context, feedback = QgsProcessingContext(), QgsProcessingFeedback()
context.setProject(project)
params = {
    "LINES": lines,
    "BOUNDARY": boundary,
    "CRS": crs,
    "MOTHER": 2000,
    "DIVISORS": "2,4,8,16",
    "Q_MIN": -2,
    "Q_MAX": 2,
    "Q_STEP": 1,
    "MIN_R2": 0.1,
    "LOCAL": True,
    "STRUCTURAL": True,
    "NETWORK": False,
    "PLOTS": False,
    "OUTPUT": str(session / "processing"),
}
result = processing.run("musa:analyze", params, context=context, feedback=feedback)
manifest = json.loads(Path(result["MANIFEST"]).read_text())
assert manifest["status"] == "complete"
scaling_params = {"LINES": lines, "BOUNDARY": boundary, "CRS": crs,
                  "SCALES": "2,4,6,10,16,25,40,63,100,160,250,400", "RESOLUTION": 1,
                  "Q_MIN": 0, "Q_MAX": 2, "Q_STEP": 1, "NULL_REPLICATES": 0, "SEED": 42,
                  "OUTPUT": str(session / "scaling_processing")}
scaling_result = processing.run("musa:scaling_support", scaling_params, context=context, feedback=feedback)
scaling_report = json.loads(Path(scaling_result["REPORT"]).read_text())
assert len(scaling_report["supports"][0]["q_results"]) == 3
assert (session / "scaling_processing/scaling_support.csv").exists()
assert json.loads((session / "scaling_processing/run_manifest.json").read_text())["status"] == "complete"
assert (session / "scaling_processing/spectrum_curves.sqlite").is_file()
assert all("observables" in row for row in scaling_report["supports"][0]["q_results"])
try:
    processing.run("musa:scaling_support", scaling_params, context=context, feedback=feedback)
except Exception:
    pass
else:
    raise AssertionError("Scaling Processing overwrote an existing output folder")
print("PASS independent Renyi scaling Processing, all q retained and output collision protection", flush=True)
for relative, digest in manifest["files"].items():
    assert hashlib.sha256((session / "processing" / relative).read_bytes()).hexdigest() == digest
ds = ogr.Open(str(session / "processing/musa_mother_cells.gpkg"))
layer = ds.GetLayerByName("mother_multifractal_display")
assert layer.GetFeatureCount() == 4
assert layer.GetSpatialRef().GetAuthorityCode(None) == "32718"
ds = None
reference = make_analyzer(snapshot, config).run_analysis(resolutions_m=[2000, 1000, 500, 250, 125], min_r2=0.1)
import csv

with (session / "processing/analysis_report.csv").open(newline="") as file:
    rows = [row for row in csv.DictReader(file) if row["row_type"] == "detail" and row["status"] == "accepted"]
assert manifest["accepted_q"] == reference.accepted_count
assert len(rows) == reference.accepted_count
for field in ("q", "dq", "alpha", "f_alpha"):
    np.testing.assert_allclose([float(row[field]) for row in rows], getattr(reference, field), atol=1e-12)
print("PASS bundle, Processing, native GeoPackage, shared numerical core", flush=True)

# Different source CRS, selected features and unsaved edits are captured on main thread.
geographic = QgsVectorLayer("Polygon?crs=EPSG:4326", "Geographic boundary", "memory")
g = QgsGeometry(feature.geometry())
g.transform(QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem("EPSG:4326"), project.transformContext()))
f = QgsFeature()
f.setGeometry(g)
geographic.dataProvider().addFeatures([f])
lines.selectByIds([next(lines.getFeatures()).id()])
selected = snapshot_sources(lines, geographic, crs, selected_only=True)
assert len(selected["lines"]) == 1
assert make_analyzer(selected, config)._boundary_geom.area > 15_999_999
lines.removeSelection()
for invalid in ("EPSG:4326", "EPSG:2263"):
    try:
        validate_metric_crs(QgsCoordinateReferenceSystem(invalid))
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid units accepted")
print("PASS selection and geographic reprojection; geographic/feet analysis CRS rejected", flush=True)

recipe = session / "recipe.json"
recipe.write_text(json.dumps(config.recipe()), encoding="utf-8")
recipe_output = session / "recipe_run"
processing.run(
    "musa:run_recipe",
    {"LINES": lines, "BOUNDARY": boundary, "CRS": crs, "RECIPE": str(recipe), "OUTPUT": str(recipe_output)},
    context=context,
)
assert json.loads((recipe_output / "run_manifest.json").read_text())["status"] == "complete"
try:
    processing.run("musa:analyze", params, context=context)
except Exception:
    pass
else:
    raise AssertionError("Existing output overwritten")
plugin.unload()

iface = Interface()
plugin = classFactory(iface)
plugin.initGui()
plugin.initGui()
assert len(plugin.actions) == 2
plugin.show_workbench()
dock = plugin.dock
dock.lines.setLayer(lines)
dock.boundary.setLayer(boundary)
dock.crs.setCrs(crs)
dock.output_root.setText(str(session))
dock.apply_config(config)
assert dock.config().recipe() == json.loads(json.dumps(config.recipe()))
iface.window.resizeDocks([dock], [600], Qt.Horizontal)
iface.window.show()
dock.start_run()
wait_until(lambda: dock.task is None)
assert dock.status.text() == "Analysis complete", dock.log.toPlainText()
assert dock.last_output and len(list(dock.last_output.glob("*.png"))) > 0
assert len(project.mapLayers()) > 2
print("PASS workbench background task and layer/figure loading", flush=True)
# A second task exercises CRS/thread context reuse with a geographic boundary.
second = session / "second_task"
dock.start_snapshot(snapshot_sources(lines, geographic, crs), config, second)
wait_until(lambda: dock.task is None)
assert (second / "run_manifest.json").is_file()
assert json.loads((second / "run_manifest.json").read_text())["status"] == "complete"
print("PASS successive tasks with reprojected source", flush=True)

images = Path(__file__).resolve().parents[1] / "docs/images"
images.mkdir(exist_ok=True)
iface.canvas.setLayers([lines, boundary])
iface.canvas.setDestinationCrs(crs)
iface.canvas.setExtent(boundary.extent())
iface.canvas.refresh()
iface.canvas.waitWhileRendering()
dock.tabs.setCurrentIndex(0)
app.processEvents()
time.sleep(0.2)
app.processEvents()
assert iface.window.grab().save(str(images / "qgis_musa_workbench.png"))
dock.tabs.setCurrentWidget(dock.results_page)
display = next(layer for layer in project.mapLayers().values() if layer.name() == "Mother Multifractal Display")
iface.canvas.setLayers([lines, display, boundary])
iface.canvas.refresh()
iface.canvas.waitWhileRendering()
app.processEvents()
assert iface.window.grab().save(str(images / "qgis_musa_results.png"))

# Exercise optional GeoPandas outputs in the same background-task environment.
small = QgsVectorLayer("LineString?crs=EPSG:32718", "Synthetic crossing", "memory")
for wkt in ("LINESTRING(400000 8602000,404000 8602000)", "LINESTRING(402000 8600000,402000 8604000)"):
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromWkt(wkt))
    small.dataProvider().addFeatures([f])
from dataclasses import replace

moving_config = replace(
    config,
    local=False,
    structural=False,
    plots=False,
    moving=True,
    q_min=0,
    q_max=2,
    window_sizes_m=(4000,),
    window_step_m=4000,
    origin_ensemble=True,
    proximity_radii_m=(100,),
    scaling_support=True,
    scaling_resolution_m=1,
    scaling_scales_m=tuple(np.geomspace(2, 250, 8)),
)
moving_output = session / "moving_task"
original_recipe = json.loads(json.dumps(moving_config.recipe()))
dock.apply_config(moving_config)
assert dock.config().recipe() == original_recipe, {
    key: (value, dock.config().recipe()["parameters"][key])
    for key, value in original_recipe["parameters"].items()
    if value != dock.config().recipe()["parameters"][key]
}
dock.start_snapshot(snapshot_sources(small, boundary, crs), moving_config, moving_output)
wait_until(lambda: dock.task is None)
moving_manifest = json.loads((moving_output / "run_manifest.json").read_text())
assert moving_manifest["status"] == "complete", moving_manifest
assert Path(moving_manifest["outputs"]["moving_gis"]).is_file()
from musa_qgis._core.musa.spectrum_products import list_spectra, read_spectrum
spectral_index = list_spectra(moving_output / "spectrum_curves.sqlite")
assert {s["source"] for s in spectral_index} == {"analysis", "assessment"}
assert {s["estimator"] for s in spectral_index} == {"canonical", "zeta"}
ds = ogr.Open(str(moving_manifest["outputs"]["moving_gis"]))
assert ds.GetLayerByName("window_spectrum_summary").GetFeatureCount() == len(spectral_index)
ds = None
assert dock.spectrum_domain.isEnabled()
for domain in range(dock.spectrum_domain.count()):
    dock.spectrum_domain.setCurrentIndex(domain)
    for estimator in range(dock.spectrum_estimator.count()):
        dock.spectrum_estimator.setCurrentIndex(estimator)
        assert dock._spectrum_figure is not None, dock.spectrum_note.text()
        assert "alpha(q=0)" in dock.spectrum_note.text()
        suffix = f"{domain}_{estimator}"
        dock.export_selected_spectrum(session / f"spectrum_{suffix}.png")
        dock.export_selected_spectrum(session / f"spectrum_{suffix}.svg")
assert len(list(session.glob("spectrum_*.svg"))) == len(spectral_index)
assert dock.result_tabs.count() == 3
assert dock.spectrum_values.rowCount() == 3
assert dock.spectrum_panel.isEnabled()
from qgis.PyQt.QtTest import QTest
dock.result_tabs.setCurrentIndex(0)
app.processEvents()
canvas = dock.spectrum_preview.canvas
QTest.mouseClick(canvas, Qt.LeftButton, pos=canvas.rect().center())
app.processEvents()
assert len(dock.spectrum_preview.dialogs) == 1
dialog = dock.spectrum_preview.dialogs[0]
assert dialog.isVisible()
dialog.close()
app.processEvents()
assert not dock.spectrum_preview.dialogs
one = next(s for s in spectral_index if s["source"] == "analysis" and s["kind"] == "window" and s["estimator"] == "canonical")
curve = read_spectrum(moving_output / "spectrum_curves.sqlite", one["series_id"])
assert all(p["tau"] is None or abs(p["tau"]-(p["q"]-1)*p["dq"]) < 1e-9 for p in curve["points"])
dock.tabs.setCurrentWidget(dock.results_page)
app.processEvents()
assert iface.window.grab().save(str(session / "qgis_window_spectra.png"))
dock.open_completed_run(session / "scaling_processing")
assert {s["source"] for s in dock._spectrum_index} == {"assessment"}
assert dock._spectrum_figure is not None
dock.open_completed_run(moving_output)
assert {s["source"] for s in dock._spectrum_index} == {"analysis", "assessment"}
failed_view = session / "failed_view"
failed_view.mkdir()
(failed_view / "run_manifest.json").write_text(json.dumps({"status": "failed"}))
try:
    dock.open_completed_run(failed_view)
except ValueError:
    pass
else:
    raise AssertionError("Incomplete run was loaded as completed spectra")
assert dock.last_output == moving_output
older_view = session / "older_view"
older_view.mkdir()
(older_view / "run_manifest.json").write_text(json.dumps({"status": "complete"}))
dock.open_completed_run(older_view)
assert not dock._spectrum_index and not dock.spectrum_export.isEnabled()
dock.open_completed_run(moving_output)
print("PASS indexed global/window spectra, canonical/zeta selectors, singularity summaries and PNG/SVG export", flush=True)
support_reports = json.loads(Path(moving_manifest["outputs"]["scaling_support_json"]).read_text())
assert len(support_reports["supports"]) >= 2
assert all(r["null"]["holm_family_size"] == len(support_reports["supports"]) for r in support_reports["supports"])
assert any(layer.name() == "Renyi scaling support - diagnostics" for layer in project.mapLayers().values())
assert "Renyi scaling (support/q)" in dock.summary.text()
dock.tabs.setCurrentIndex(1)
app.processEvents()
dock.tabs.widget(1).verticalScrollBar().setValue(dock.tabs.widget(1).verticalScrollBar().maximum())
app.processEvents()
assert iface.window.grab().save(str(session / "qgis_scaling_quality.png"))
from processing.gui.AlgorithmDialog import AlgorithmDialog
scaling_dialog = AlgorithmDialog(QgsApplication.processingRegistry().algorithmById("musa:scaling_support").create())
scaling_dialog.setParameters(scaling_params)
scaling_dialog.resize(1100, 850)
scaling_dialog.show()
app.processEvents()
assert scaling_dialog.grab().save(str(session / "qgis_scaling_processing.png"))
scaling_dialog.close()
scaling_dialog = None
print("PASS experimental windows, 16 origins and proximity in a background task", flush=True)

# Cancellation/unload while the worker owns copied inputs must not access deleted UI.
detached_output = session / "detached"
dock.start_snapshot(snapshot, config, detached_output)
wait_until(lambda: (detached_output / "run_manifest.json").exists() or dock.task is None)
plugin.unload()
wait_until(lambda: not QgsApplication.taskManager().activeTasks())
app.processEvents()
assert QgsApplication.processingRegistry().providerById("musa") is None
if (detached_output / "run_manifest.json").exists():
    detached = json.loads((detached_output / "run_manifest.json").read_text())
    assert detached["status"] in ("cancelled", "complete"), detached
print("PASS unload during active task and provider removal", flush=True)
report = {"qgis_version": Qgis.QGIS_VERSION, "bundle": str(args.bundle), "session": str(session), "status": "passed"}
(session / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("VALIDATION", session / "validation.json", flush=True)
iface.window.close()
project.clear()
app.processEvents()
app.exitQgis()

"""Generate fault-like data, run the bundled QGIS plugin and save a demo project."""

# ruff: noqa: E402
import argparse
import csv
import faulthandler
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import zipfile

from synthetic_fault_network import FAMILIES, generate, write_dataset

faulthandler.enable()

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("bundle", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(parents=True, exist_ok=False)
session = Path(os.environ["DEVRESOURCES_SESSION"]) / "fault_demo"
session.mkdir()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = str(session / "profile")
os.environ["QGIS_AUTH_DB_DIR_PATH"] = str(session / "profile/auth")
with zipfile.ZipFile(args.bundle) as archive:
    assert all(name.startswith("musa_qgis/") and ".." not in Path(name).parts for name in archive.namelist())
    archive.extractall(session / "plugins")
sys.path.insert(0, str(session / "plugins"))

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsGraduatedSymbolRenderer,
    QgsLayerTreeModel,
    QgsLineSymbol,
    QgsProject,
    QgsRendererCategory,
    QgsRendererRange,
    QgsSymbol,
    QgsVectorLayer,
    QgsReferencedRectangle,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase
from qgis.PyQt.QtWidgets import QMainWindow, QSplitter
from qgis.gui import QgsLayerTreeView, QgsMapCanvas

app = QgsApplication([], True)
app.initQgis()
font = Path("C:/Windows/Fonts/arial.ttf")
if font.is_file():
    QFontDatabase.addApplicationFont(str(font))
    app.setFont(QFont("Arial", 10))
from musa_qgis import classFactory
from musa_qgis.inputs import snapshot_sources
from musa_qgis.runtime import core

description = write_dataset(root / "dataset")
print("DATASET", json.dumps(description), flush=True)
project = QgsProject.instance()
crs = QgsCoordinateReferenceSystem("EPSG:32718")
project.setCrs(crs)
project.setTitle("MUSA — Synthetic fault network")
source = root / "dataset/synthetic_faults.gpkg"
lines = QgsVectorLayer(f"{source}|layername=fault_traces", "Synthetic fault traces", "ogr")
boundary = QgsVectorLayer(f"{source}|layername=analysis_boundary", "Synthetic study boundary", "ogr")
assert lines.isValid() and boundary.isValid()
assert lines.featureCount() == description["feature_count"]
categories = []
for family, (color, order) in FAMILIES.items():
    symbol = QgsLineSymbol.createSimple(
        {
            "line_color": color,
            "line_width": str({1: 0.6, 2: 0.35, 3: 0.2}[order]),
            "line_style": "solid",
            "capstyle": "round",
            "joinstyle": "round",
        }
    )
    categories.append(QgsRendererCategory(family, symbol, family))
lines.setRenderer(QgsCategorizedSymbolRenderer("family", categories))
boundary.renderer().setSymbol(
    QgsFillSymbol.createSimple({"color": "245,244,239,255", "outline_color": "#6a7870", "outline_width": "0.4"})
)
project.addMapLayer(boundary)
project.addMapLayer(lines)


class Interface:
    def __init__(self):
        self.window = QMainWindow()
        self.window.resize(1700, 1100)
        self.window.setWindowTitle("MUSA | Synthetic fault network | QGIS runtime")
        self.canvas = QgsMapCanvas(self.window)
        self.canvas.setCanvasColor(QColor("#fafaf7"))
        self.canvas.setDestinationCrs(crs)
        self.tree = QgsLayerTreeView()
        self.model = QgsLayerTreeModel(project.layerTreeRoot())
        self.tree.setModel(self.model)
        split = QSplitter()
        split.addWidget(self.tree)
        split.addWidget(self.canvas)
        split.setSizes([260, 820])
        self.window.setCentralWidget(split)
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


def wait_until(predicate, timeout=300):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.03)
    raise TimeoutError("QGIS task did not finish within five minutes")


iface = Interface()
plugin = classFactory(iface)
plugin.initGui()
plugin.show_workbench()
dock = plugin.dock
_, RunConfig, _ = core()
config = RunConfig(
    mother_cell_m=4000, divisors=(2, 4, 8, 16, 32), q_min=-4, q_max=4, q_step=1, min_r2=0.9, network=True
)
dock.lines.setLayer(lines)
dock.boundary.setLayer(boundary)
dock.crs.setCrs(crs)
dock.output_root.setText(str(root))
dock.apply_config(config)
iface.window.resizeDocks([dock], [590], Qt.Horizontal)
iface.window.show()
extent = boundary.extent()
extent.scale(1.08)
iface.canvas.setExtent(extent)
captures = root / "screenshots"
captures.mkdir()


def capture(filename, layers):
    for layer in project.mapLayers().values():
        node = project.layerTreeRoot().findLayer(layer.id())
        if node:
            node.setItemVisibilityChecked(layer in layers)
    iface.canvas.setLayers(layers)
    iface.canvas.refresh()
    iface.canvas.waitWhileRendering()
    app.processEvents()
    assert iface.window.grab().save(str(captures / filename))


dock.tabs.setCurrentIndex(0)
capture("01_fault_network.png", [lines, boundary])
snapshot = snapshot_sources(lines, boundary, crs)
snapshot["info"].update(synthetic=True, seed=description["seed"], real_location=False)
output = root / "MUSA_results"
dock.start_snapshot(snapshot, config, output)
wait_until(lambda: dock.task is None)
manifest = json.loads((output / "run_manifest.json").read_text())
assert manifest["status"] == "complete", manifest
assert dock.status.text() == "Analysis complete", dock.log.toPlainText()
for relative, digest in manifest["files"].items():
    assert hashlib.sha256((output / relative).read_bytes()).hexdigest() == digest
print("RUN", manifest["status"], "accepted_q", manifest["accepted_q"], "rejected_q", manifest["rejected_q"], flush=True)


def thematic_layer(name, field, colors):
    gpkg = output / "musa_mother_cells.gpkg"
    table = "mother_structural_stats" if field == "density_m_per_km2" else "mother_multifractal_display"
    layer = QgsVectorLayer(f"{gpkg}|layername={table}", name, "ogr")
    values = []
    for feature in layer.getFeatures():
        try:
            value = float(feature[field])
            if math.isfinite(value):
                values.append(value)
        except (TypeError, ValueError):
            pass
    assert values, field
    lo, hi = min(values), max(values)
    ranges = []
    for i, color in enumerate(colors):
        low, high = lo + (hi - lo) * i / len(colors), lo + (hi - lo) * (i + 1) / len(colors)
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(QColor(color))
        ranges.append(QgsRendererRange(low, high, symbol, f"{low:.3g} – {high:.3g}"))
    layer.setRenderer(QgsGraduatedSymbolRenderer(field, ranges))
    layer.setOpacity(0.8)
    project.addMapLayer(layer)
    return layer


density = thematic_layer(
    "Fault length density (m/km2)", "density_m_per_km2", ["#fff7bc", "#fee391", "#fec44f", "#fe9929", "#cc4c02"]
)
alpha = thematic_layer("Canonical alpha (q=2)", "alpha", ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"])
zeta = thematic_layer(
    "Numerical reliability — mean zeta (q=2)", "zeta_mean", ["#eff3ff", "#bdd7e7", "#6baed6", "#3182bd", "#08519c"]
)
dock.tabs.setCurrentWidget(dock.results_page)
dock.show_figure("dq_scatterplot.png")
capture("02_density_results.png", [lines, density, boundary])
dock.show_figure("multifractal_singularity_spectrum_by_q.png")
capture("03_multifractal_results.png", [lines, alpha, boundary])
capture("04_reliability_results.png", [lines, zeta, boundary])

# Preserve a portable QGIS project with relative file references and all results.
project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(iface.canvas.extent(), crs))
project.setFileName(str(root / "MUSA_synthetic_faults.qgz"))
project.setFilePathStorage(Qgis.FilePathType.Relative)
assert project.write()
with zipfile.ZipFile(root / "MUSA_synthetic_faults.qgz") as archive:
    xml = archive.read(next(name for name in archive.namelist() if name.endswith(".qgs"))).decode("utf-8")
    assert "./dataset/synthetic_faults.gpkg" in xml
    assert "DevResources" not in xml

with (output / "multifractal_mother_agg.csv").open(newline="", encoding="utf-8") as file:
    local = list(csv.DictReader(file))
with (output / "lineament_mother_structural_stats.csv").open(newline="", encoding="utf-8") as file:
    structural = list(csv.DictReader(file))
q2 = [row for row in local if float(row["q"]) == 2]
summary = dict(
    description,
    accepted_q=manifest["accepted_q"],
    rejected_q=manifest["rejected_q"],
    mother_cells=len(structural),
    q2_reliable_cells=sum(float(row["reliable"]) >= 1 for row in q2),
    minimum_fit_r2=config.min_r2,
    plugin_bundle=str(args.bundle.resolve()),
    qgis_version=Qgis.QGIS_VERSION,
)
(root / "demo_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

# Export a standalone scientific figure from the same input geometry and CSV values.
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as PlotPolygon
from matplotlib.lines import Line2D
import numpy as np

boundary_geom, features = generate(description["seed"])
figure = Figure(figsize=(15, 12), layout="constrained")
FigureCanvasAgg(figure)
axes = figure.subplots(2, 2)
origin = np.array([400000, 8600000])


def draw_faults(axis, color=None, opacity=1):
    xy = (np.asarray(boundary_geom.exterior.coords) - origin) / 1000
    axis.fill(xy[:, 0], xy[:, 1], color="#f5f4ef", zorder=0)
    for row in features:
        xy = (np.asarray(row["geometry"].coords) - origin) / 1000
        chosen, order = FAMILIES[row["family"]]
        axis.plot(
            xy[:, 0],
            xy[:, 1],
            color=color or chosen,
            linewidth={1: 1.4, 2: 0.8, 3: 0.5}[order],
            alpha=opacity,
            zorder=2,
        )
    axis.set(
        xlim=(-0.5, 24.5),
        ylim=(-0.5, 20.5),
        xlabel="Easting offset (km)",
        ylabel="Northing offset (km)",
        aspect="equal",
    )
    axis.grid(alpha=0.15)


draw_faults(axes[0, 0])
axes[0, 0].set_title("Synthetic fault traces — five construction families")
axes[0, 0].legend(
    handles=[Line2D([], [], color=color, label=family) for family, (color, _) in FAMILIES.items()],
    fontsize=8,
    loc="upper left",
)
for axis, rows, field, title, cmap in (
    (axes[0, 1], structural, "density_m_per_km2", "Fault length density (m/km2)", "YlOrBr"),
    (axes[1, 0], q2, "alpha", "Canonical alpha at q=2 (includes flagged fits)", "viridis"),
    (axes[1, 1], q2, "zeta_mean", "Mean zeta at q=2 — numerical support", "Blues"),
):
    draw_faults(axis, color="#384a4d", opacity=0.6)
    patches, values = [], []
    from shapely.geometry import box

    for row in rows:
        try:
            value = float(row[field])
        except (TypeError, ValueError):
            continue
        if not np.isfinite(value):
            continue
        x, y, size = (float(row[key]) for key in ("mother_centroid_x", "mother_centroid_y", "mother_scale_m"))
        polygon = box(x - size / 2, y - size / 2, x + size / 2, y + size / 2).intersection(boundary_geom)
        if polygon.is_empty:
            continue
        xy = (np.asarray(polygon.exterior.coords) - origin) / 1000
        patches.append(PlotPolygon(xy, closed=True))
        values.append(value)
    collection = PatchCollection(patches, cmap=cmap, alpha=0.85, edgecolor="#ffffff", linewidth=0.5, zorder=1)
    collection.set_array(np.asarray(values))
    axis.add_collection(collection)
    figure.colorbar(collection, ax=axis, shrink=0.75)
    axis.set_title(title)
figure.suptitle(
    f"MUSA | Synthetic fault-network demonstration\n{description['feature_count']} traces · {description['area_km2']:.1f} km² · seed {description['seed']}",
    fontsize=16,
)
figure.savefig(root / "fault_network_analysis.png", dpi=180)
figure.savefig(root / "fault_network_analysis.pdf")

report = f"""# MUSA synthetic fault-network demonstration

This dataset contains {description["feature_count"]} fault-like traces in five construction
families, with curved traces, conjugate directions, branch splays, short segments,
gaps and uneven density. It is entirely synthetic, in arbitrary projected
EPSG:32718 coordinates; it does not represent a real site or a mechanical model.

Seed: {description["seed"]}. Boundary area: {description["area_km2"]:.2f} km2.
Total trace length: {description["total_length_km"]:.2f} km.

## Execution

The packaged MUSA QGIS plugin ran in a real QGIS {Qgis.QGIS_VERSION} Python runtime,
using its background task and the same core as the workbench. The temporary
host window provides native QGIS map, layer tree and plugin widgets. Screenshots
are offscreen runtime captures, not a screenshot of the full QGIS desktop shell.
No real QGIS user profile was modified.

Mother cell: 4000 m. Internal divisors: 2,4,8,16,32.
q: -4 to 4, step 1. Minimum fit R2: 0.9; default mean zeta threshold: 0.15.
Computed global and mother-cell spectra, structural density/orientation,
whole-network statistics, GIS layers and figures. Moving windows and bootstrap
were not enabled for this baseline demonstration.

Accepted global q: {summary["accepted_q"]}. Rejected global q: {summary["rejected_q"]}.
Occupied mother cells: {summary["mother_cells"]}.
Reliable mother cells at q=2: {summary["q2_reliable_cells"]} of {len(q2)}.
Rejected estimates and local reliability flags are retained. Canonical alpha,
weighted alpha, density and zeta have different meanings. The overview maps
include flagged local fits; consult reliable fields before interpreting them.

Network statistics in the existing core count intersecting input trace pairs,
not unique planar junctions or inferred geological fault identities. Synthetic
structural orders describe the generator hierarchy only.

## Open in QGIS

Open MUSA_synthetic_faults.qgz. All layer paths are relative to this folder.
Dataset: dataset/synthetic_faults.gpkg, layers fault_traces and analysis_boundary.
Results: MUSA_results, including CSV, PNG, GeoPackage, recipe and hashed manifest.
Screenshots: screenshots, all interface labels in English.
Overview: fault_network_analysis.png and fault_network_analysis.pdf.

This is a reproducible functional demonstration, not scientific calibration or
evidence that any geological process, permeability or prospectivity was recovered.
"""
(root / "README.md").write_text(report, encoding="utf-8")
print("SUMMARY", json.dumps(summary), flush=True)
plugin.unload()
iface.window.close()
project.clear()
app.processEvents()
app.exitQgis()

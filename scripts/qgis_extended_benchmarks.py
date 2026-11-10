"""Native QGIS projects, Processing parity and completed-run viewer stress QA."""
# ruff: noqa: E402
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
parser.add_argument("bundle", type=Path)
args = parser.parse_args()
root = args.output
session = Path(tempfile.mkdtemp(prefix="musa_")) / "extended_qgis"
session.mkdir()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = str(session / "profile")
os.environ["QGIS_AUTH_DB_DIR_PATH"] = str(session / "profile/auth")
with zipfile.ZipFile(args.bundle) as archive:
    archive.extractall(session / "plugins")
sys.path.insert(0, str(session / "plugins"))
from qgis.core import (
    Qgis, QgsApplication, QgsProject, QgsVectorLayer, QgsLineSymbol, QgsFillSymbol,
    QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsReferencedRectangle,
    QgsProcessingContext, QgsProcessingFeedback,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase
from qgis.PyQt.QtWidgets import QMainWindow
from qgis.gui import QgsMapCanvas
app = QgsApplication([], True)
app.initQgis()
QFontDatabase.addApplicationFont("C:/Windows/Fonts/arial.ttf")
app.setFont(QFont("Arial", 10))
sys.path.insert(0, str(Path(QgsApplication.prefixPath()) / "python/plugins"))
from processing.core.Processing import Processing
Processing.initialize()
import processing
from musa_qgis import classFactory
from musa_qgis.inputs import validate_metric_crs

catalog = json.loads((root / "input_catalog.json").read_text())
summary = json.loads((root / "summary.json").read_text())
successful = {r["dataset_id"] for r in summary["cases"]}
cases = [c for c in catalog["cases"] if c["dataset_id"] in successful]
by_name = {c["dataset_id"]: c for c in cases}
groups = defaultdict(list)
for case in cases:
    family = "naturales_EPSG3067" if case["georeferenced"] else case["source"]
    groups[family].append(case)
project = QgsProject.instance()
project_dir, screenshots = root / "projects", root / "screenshots"
project_dir.mkdir(exist_ok=True)
screenshots.mkdir(exist_ok=True)


class Interface:
    def __init__(self):
        self.window = QMainWindow()
        self.window.resize(1800, 1150)
        self.canvas = QgsMapCanvas(self.window)
        self.canvas.setCanvasColor(QColor("#f8f9f6"))
        self.window.setCentralWidget(self.canvas)
        self.menu = self.window.menuBar().addMenu("Vector")
        self.toolbar = self.window.addToolBar("MUSA")
        self.layer = None

    def mainWindow(self):
        return self.window

    def activeLayer(self):
        return self.layer

    def addPluginToVectorMenu(self, name, action):
        self.menu.addAction(action)

    def removePluginVectorMenu(self, name, action):
        self.menu.removeAction(action)

    def addToolBarIcon(self, action):
        self.toolbar.addAction(action)

    def removeToolBarIcon(self, action):
        self.toolbar.removeAction(action)

    def addDockWidget(self, area, dock):
        self.window.addDockWidget(area, dock)

    def removeDockWidget(self, dock):
        self.window.removeDockWidget(dock)


def settle(seconds=1.):
    until = time.monotonic()+seconds
    while time.monotonic() < until:
        app.processEvents()
        time.sleep(.02)


def layer_for(path, table, label):
    layer = QgsVectorLayer(Path(path).as_posix()+"|layername="+table, label, "ogr")
    assert layer.isValid() and layer.featureCount() > 0, (path, table)
    validate_metric_crs(layer.crs())
    return layer


def add_case(case, group):
    child = group.addGroup(case["dataset_id"])
    rows = [(case["input"], "lineaments", "Trazas", "line"),
            (case["input"], "boundary", "Dominio observado", "domain"),
            (root / "results" / case["dataset_id"] / "window_results.gpkg", "q0", "Ventanas — D0", "window")]
    layers = []
    for path, table, label, kind in rows:
        if not Path(path).exists():
            continue
        layer = layer_for(path, table, label)
        if kind == "line":
            layer.renderer().setSymbol(QgsLineSymbol.createSimple({"line_color": "#1c5269", "line_width": ".2"}))
        elif kind == "domain":
            layer.renderer().setSymbol(QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#8e6541", "outline_style": "dash", "outline_width": ".4"}))
        else:
            categories = []
            for status, color, label in (("compatible_finite_range", "76,160,104,60", "Compatible en intervalo finito"),
                                         ("not_supported", "196,73,62,60", "Escalamiento no respaldado"),
                                         ("insufficient_information", "220,164,59,60", "Información insuficiente")):
                symbol = QgsFillSymbol.createSimple({"color": color, "outline_color": "#777777", "outline_width": ".2"})
                categories.append(QgsRendererCategory(status, symbol, label))
            layer.setRenderer(QgsCategorizedSymbolRenderer("status", categories))
        layer.setCustomProperty("musa/benchmark_metadata", json.dumps(case["metadata"]))
        project.addMapLayer(layer, False)
        child.addLayer(layer)
        child.findLayer(layer.id()).setItemVisibilityChecked(kind != "window")
        layers.append((kind, layer))
    child.setExpanded(False)
    return child, layers


iface = Interface()
plugin = classFactory(iface)
plugin.initGui()
plugin.show_workbench()
dock = plugin.dock
iface.window.resizeDocks([dock], [850], Qt.Horizontal)
iface.window.show()
projects, viewer_checks = [], []
for family, members in groups.items():
    project.clear()
    print("QGIS FAMILY", family, len(members), flush=True)
    selected = "aland_getaberget_20m_1_3_area" if family == "naturales_EPSG3067" else members[0]["dataset_id"]
    family_group = project.layerTreeRoot().addGroup(family)
    selected_layers = None
    for case in members:
        node, layers = add_case(case, family_group)
        node.setItemVisibilityChecked(case["dataset_id"] == selected)
        if case["dataset_id"] == selected:
            selected_layers = layers
            node.setExpanded(True)
    assert selected_layers
    active = next(layer for kind, layer in selected_layers if kind == "line")
    iface.layer = active
    project.setCrs(active.crs())
    extent = active.extent()
    extent.scale(1.08)
    project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(extent, project.crs()))
    project.setTitle("MUSA — " + family + " — ver README.md para unidades y procedencia")
    project.setFilePathStorage(Qgis.FilePathType.Relative)
    target = project_dir / (family + ".qgz")
    assert project.write(str(target))
    reader = QgsProject()
    assert reader.read(str(target))
    assert len(reader.mapLayers()) == len(project.mapLayers())
    assert all(layer.isValid() and layer.featureCount() > 0 for layer in reader.mapLayers().values())
    with zipfile.ZipFile(target) as archive:
        from xml.etree import ElementTree
        xml = ElementTree.fromstring(archive.read(next(name for name in archive.namelist() if name.endswith(".qgs"))))
        assert all("D:/" not in node.text and "D:\\" not in node.text for node in xml.findall(".//datasource") if node.text)
    projects.append(dict(family=family, path=str(target), layers=len(project.mapLayers()), reopened_all_valid=True, relative_paths=True))
    reader.clear()
    iface.canvas.setDestinationCrs(project.crs())
    iface.canvas.setLayers([layer for kind, layer in selected_layers if kind != "window"])
    iface.canvas.setExtent(extent)
    iface.window.setWindowTitle("MUSA — " + selected)
    dock.open_completed_run(root / "results" / selected)
    dock.tabs.setCurrentWidget(dock.results_page)
    for index in range(dock.spectrum_domain.count()):
        if dock.spectrum_domain.itemData(index) == ("assessment", "global"):
            dock.spectrum_domain.setCurrentIndex(index)
            break
    assert dock._spectrum_figure is not None
    settle(1.)
    iface.canvas.refresh()
    settle(1.)
    assert iface.window.grab().save(str(screenshots / (family + "_viewer.png")))
    iface.canvas.saveAsImage(str(screenshots / (family + "_map.png")))
    if family == "naturales_EPSG3067":
        index = next((i for i in range(dock.spectrum_domain.count())
                      if tuple(dock.spectrum_domain.itemData(i)) == ("assessment", "window")), -1)
        assert index >= 0
        dock.spectrum_domain.setCurrentIndex(index)
        center = dock.spectrum_center.findData(4)
        assert center >= 0
        dock.spectrum_center.setCurrentIndex(center)
        windows = next(layer for kind, layer in selected_layers if kind == "window")
        windows.selectByExpression('"support_id" = \'interior_window_4\'')
        iface.canvas.setLayers([windows]+[layer for kind, layer in selected_layers if kind != "window"])
        iface.canvas.refresh()
        settle(1.)
        assert iface.window.grab().save(str(screenshots / "naturales_ventana_interior.png"))
    # Exercise every stored global/window/source/estimator combination. This
    # loads saved numerical products; it never silently reruns a calculation.
    for case in members:
        dock.open_completed_run(root / "results" / case["dataset_id"])
        assert dock._spectrum_index
        for index in range(dock.spectrum_domain.count()):
            dock.spectrum_domain.setCurrentIndex(index)
            for center in range(max(1, dock.spectrum_center.count())):
                if dock.spectrum_center.count():
                    dock.spectrum_center.setCurrentIndex(center)
                for estimator in range(dock.spectrum_estimator.count()):
                    dock.spectrum_estimator.setCurrentIndex(estimator)
                    assert dock._spectrum_figure is not None
        viewer_checks.append(dict(dataset_id=case["dataset_id"], stored_series=len(dock._spectrum_index), opened=True))

# Re-run two representative cases through actual QGIS Processing and compare
# every q/scale entropy with the earlier Python path, not just a screenshot.
parity = []
for identity in ("aland_getaberget_20m_1_3_area", "hatchfrac_growth_7"):
    case = by_name[identity]
    project.clear()
    lines = layer_for(case["input"], "lineaments", identity)
    boundary = layer_for(case["input"], "boundary", identity+" domain")
    project.addMapLayers([boundary, lines])
    project.setCrs(lines.crs())
    context, feedback = QgsProcessingContext(), QgsProcessingFeedback()
    context.setProject(project)
    params = dict(LINES=lines, BOUNDARY=boundary, CRS=lines.crs(),
                  SCALES=",".join(str(v) for v in case["scales"]), RESOLUTION=case["resolution"],
                  Q_MIN=-4, Q_MAX=4, Q_STEP=1, NULL_REPLICATES=0, SEED=20261102,
                  OUTPUT=str(root / "native_processing" / session.parent.name / identity))
    result = processing.run("musa:scaling_support", params, context=context, feedback=feedback)
    actual = json.loads(Path(result["REPORT"]).read_text())["supports"][0]
    expected = json.loads((root / "results" / identity / "scaling_support.json").read_text())["supports"][0]
    assert len(actual["curves"]) == len(expected["curves"])
    maximum = max(abs(a["entropy"]-b["entropy"]) for a, b in zip(actual["curves"], expected["curves"]))
    assert maximum < 1e-8, maximum
    assert [r["status"] for r in actual["q_results"]] == [r["status"] for r in expected["q_results"]]
    parity.append(dict(dataset_id=identity, curves=len(actual["curves"]), max_entropy_difference=maximum, statuses_equal=True))
    print("PROCESSING PARITY", parity[-1], flush=True)
validation = dict(qgis=Qgis.QGIS_VERSION, projects=projects, viewer_checks=viewer_checks, processing_parity=parity,
                  normal_profile_modified=False, bundle=str(args.bundle), session=str(session))
(root / "qgis_validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
print("NATIVE QA COMPLETE", len(projects), "projects", len(viewer_checks), "viewers", flush=True)
plugin.unload()
iface.window.close()
project.clear()
app.processEvents()

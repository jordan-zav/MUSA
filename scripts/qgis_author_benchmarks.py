"""Build and reopen the benchmark project in native QGIS; exercise its viewer."""
# ruff: noqa: E402
import argparse
import json
import os
from pathlib import Path
import sys
import time
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
parser.add_argument("bundle", type=Path)
args = parser.parse_args()
root = args.output
session = Path(os.environ["DEVRESOURCES_SESSION"]) / "author_qgis"
session.mkdir()
os.environ["SQLITE_TMPDIR"] = str(session)
os.environ["CPL_TMPDIR"] = str(session)
os.environ["OGR_SQLITE_USE_OGR_VFS"] = "NO"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = str(session / "profile")
os.environ["QGIS_AUTH_DB_DIR_PATH"] = str(session / "profile/auth")
with zipfile.ZipFile(args.bundle) as archive:
    archive.extractall(session / "plugins")
sys.path.insert(0, str(session / "plugins"))
from qgis.core import (
    Qgis, QgsApplication, QgsProject, QgsVectorLayer, QgsLineSymbol,
    QgsFillSymbol, QgsReferencedRectangle,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase
from qgis.PyQt.QtWidgets import QMainWindow
from qgis.gui import QgsMapCanvas
from osgeo import gdal
gdal.SetConfigOption("OGR_SQLITE_USE_OGR_VFS", "NO")
gdal.SetConfigOption("CPL_TMPDIR", str(session))
app = QgsApplication([], True)
app.initQgis()
QFontDatabase.addApplicationFont("C:/Windows/Fonts/arial.ttf")
app.setFont(QFont("Arial", 10))
from musa_qgis import classFactory
from musa_qgis.inputs import validate_metric_crs

project = QgsProject.instance()
summaries = json.loads((root / "summary.json").read_text())
gpkg = root / "datasets/benchmarks.gpkg"
tree = project.layerTreeRoot()
selected = "sahu_roy_author_map_6"
initial = []
count = 0
for item in summaries:
    identity = item["dataset_id"]
    print("QGIS", identity, flush=True)
    group = tree.addGroup(identity)
    for source, label in (("lineaments", "Line traces"), ("boundaries", "Model domain"), ("windows_q0", "Windows q=0")):
        dataset = root / "datasets/cases" / (identity + ".gpkg")
        layer = QgsVectorLayer(dataset.as_posix() + "|layername=" + source, label, "ogr")
        assert layer.isValid(), source
        assert layer.featureCount() > 0
        validate_metric_crs(layer.crs())
        project.addMapLayer(layer, False)
        group.addLayer(layer)
        if source == "lineaments":
            layer.renderer().setSymbol(QgsLineSymbol.createSimple({"line_color": "#164d5b", "line_width": ".15"}))
            if identity == selected:
                active = layer
                project.setCrs(layer.crs())
        else:
            layer.renderer().setSymbol(QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#a66b37", "outline_style": "dash", "outline_width": ".35"}))
        metadata = layer.metadata()
        metadata.setAbstract("UNLOCATED normalized model coordinates. Not a georeferenced natural outcrop. See README.md for source and derivative attribution.")
        layer.setMetadata(metadata)
        group.findLayer(layer.id()).setItemVisibilityChecked(source != "windows_q0")
        if identity == selected and source != "windows_q0":
            initial.append(layer)
        count += 1
    group.setItemVisibilityChecked(identity == selected)
    group.setExpanded(identity == selected)
project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(active.extent(), project.crs()))
project.setTitle("MUSA public-author benchmarks | UNLOCATED model plane")
project.setFilePathStorage(Qgis.FilePathType.Relative)
project_path = root / "MUSA_author_benchmarks.qgz"
assert project.write(str(project_path))


class Interface:
    def __init__(self):
        self.window = QMainWindow()
        self.window.resize(1800, 1100)
        self.window.setWindowTitle("MUSA — published fractal map 6 | UNLOCATED model plane")
        self.canvas = QgsMapCanvas(self.window)
        self.canvas.setCanvasColor(QColor("#f5f7f5"))
        self.window.setCentralWidget(self.canvas)
        self.menu = self.window.menuBar().addMenu("Vector")
        self.toolbar = self.window.addToolBar("MUSA")

    def mainWindow(self):
        return self.window

    def activeLayer(self):
        return active

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


iface = Interface()
iface.canvas.setDestinationCrs(project.crs())
iface.canvas.setLayers(initial)
extent = active.extent()
extent.scale(1.05)
iface.canvas.setExtent(extent)
plugin = classFactory(iface)
plugin.initGui()
plugin.show_workbench()
dock = plugin.dock
dock.open_completed_run(root / "results" / selected)
dock.tabs.setCurrentWidget(dock.results_page)
for index in range(dock.spectrum_domain.count()):
    if dock.spectrum_domain.itemData(index) == ("assessment", "global"):
        dock.spectrum_domain.setCurrentIndex(index)
        break
assert len(dock._spectrum_index) >= 6
assert dock._spectrum_figure is not None
iface.window.resizeDocks([dock], [850], Qt.Horizontal)
iface.window.show()
iface.canvas.refresh()
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
    app.processEvents()
    time.sleep(.02)
assert iface.window.grab().save(str(root / "qgis_author_viewer.png"))
iface.canvas.saveAsImage(str(root / "qgis_author_map.png"))
# Read the portable project back and check all source/subset references.
reader = QgsProject()
assert reader.read(str(project_path))
assert len(reader.mapLayers()) == count == 60
assert all(layer.isValid() and layer.featureCount() > 0 for layer in reader.mapLayers().values())
validation = dict(qgis=Qgis.QGIS_VERSION, layers=count, project_reopened=True, all_sources_valid=True,
                  metric_model_crs_valid=True, completed_run_viewer_opened=True,
                  normal_profile_modified=False, bundle=str(args.bundle), session=str(session))
(root / "qgis_validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
print(json.dumps(validation), flush=True)
plugin.unload()
iface.window.close()
reader.clear()
project.clear()
app.processEvents()
# Qt objects remain application-owned until process exit, matching the existing
# native smoke harness. No forced exit or manual deletion of QGIS internals.

"""Capture the real plugin UI for a user guide using public example inputs.

Run with the QGIS Python launcher. This does not alter an installed plugin or
the user's profile. Bundle, input GeoPackage and completed run are explicit.
"""
# ruff: noqa: E402
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('bundle', type=Path)
parser.add_argument('input', type=Path)
parser.add_argument('run', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(parents=True, exist_ok=True)
images = root / 'screenshots'
images.mkdir(exist_ok=True)
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QGIS_CUSTOM_CONFIG_PATH'] = str(root / 'qa-profile')
os.environ['QGIS_AUTH_DB_DIR_PATH'] = str(root / 'qa-profile/auth')
plugins = Path(__file__).resolve().parents[1] / 'temp' / ('manual-plugins-' + str(time.time_ns()))
with zipfile.ZipFile(args.bundle) as archive:
    if not all(n.startswith('musa_qgis/') and '..' not in Path(n).parts for n in archive.namelist()):
        raise ValueError('Unexpected bundle paths')
    archive.extractall(plugins)
sys.path.insert(0, str(plugins))
from qgis.core import Qgis, QgsApplication, QgsProject, QgsVectorLayer, QgsLineSymbol, QgsFillSymbol, QgsReferencedRectangle
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QPoint, QRect
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase
from qgis.PyQt.QtWidgets import QMainWindow
app = QgsApplication([], True)
app.initQgis()
QFontDatabase.addApplicationFont('C:/Windows/Fonts/arial.ttf')
app.setFont(QFont('Arial', 10))
from musa_qgis import classFactory
from musa_qgis.runtime import core

example = root / 'example'
example.mkdir(exist_ok=True)
copied = example / 'Aland_fractures_and_domain.gpkg'
shutil.copy2(args.input, copied)
lines = QgsVectorLayer(copied.as_posix() + '|layername=lineaments', 'Aland - published fractures', 'ogr')
boundary = QgsVectorLayer(copied.as_posix() + '|layername=boundary', 'Aland - observed domain', 'ogr')
assert lines.isValid() and boundary.isValid()
lines.renderer().setSymbol(QgsLineSymbol.createSimple({'line_color':'#243f53', 'line_width':'.3'}))
boundary.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'246,242,228,140', 'outline_color':'#b46431', 'outline_width':'.5'}))
project = QgsProject.instance()
project.setCrs(lines.crs())
project.addMapLayer(boundary)
project.addMapLayer(lines)


class Interface:
    def __init__(self):
        self.window = QMainWindow()
        self.window.resize(1100, 1220)
        self.canvas = QgsMapCanvas()
        self.canvas.setLayers([lines, boundary])
        self.canvas.setDestinationCrs(lines.crs())
        self.canvas.setCanvasColor(QColor('#fafbf8'))
        extent = boundary.extent()
        extent.scale(1.1)
        self.canvas.setExtent(extent)
        self.window.setCentralWidget(self.canvas)
    def mainWindow(self):
        return self.window
    def activeLayer(self):
        return lines
    def addDockWidget(self, area, dock):
        self.window.addDockWidget(area, dock)


def settle():
    for _ in range(12):
        app.processEvents()
        time.sleep(.025)


def capture(name, widget, height=None):
    settle()
    pixmap = widget.grab() if height is None else widget.grab(QRect(0, 0, widget.width(), height))
    assert pixmap.save(str(images / name))


def capture_form(name):
    settle()
    page = dock.tabs.currentWidget().widget()
    from qgis.PyQt.QtWidgets import QLabel, QGroupBox, QPushButton, QWidget
    bottoms = [w.mapTo(dock, QPoint(0, w.height())).y() for w in page.findChildren(QWidget)
               if w.isVisible() and isinstance(w, (QLabel, QGroupBox, QPushButton))]
    capture(name, dock, min(dock.height(), max(bottoms) + 18))


iface = Interface()
iface.window.show()
settle()
capture('00-map.png', iface.canvas)
plugin = classFactory(iface)
plugin.show_workbench()
dock = plugin.dock
dock.setFloating(True)
dock.resize(900, 1220)
manifest = json.loads((args.run / 'run_manifest.json').read_text(encoding='utf-8'))
config = core()[1].from_recipe(manifest['recipe'])
dock.apply_config(config)
assert dock.config().recipe() == config.recipe()
dock.lines.setLayer(lines)
dock.boundary.setLayer(boundary)
dock.crs.setCrs(lines.crs())
runs = root / 'runs'
runs.mkdir(exist_ok=True)
dock.output_root.setText(str(runs))
dock.update_source()
for index, name in ((0, '01-analysis.png'), (1, '02-quality.png'), (2, '03-moving-windows.png')):
    dock.tabs.setCurrentIndex(index)
    dock.tabs.widget(index).verticalScrollBar().setValue(0)
    capture_form(name)
    if index == 1:
        dock.tabs.widget(index).verticalScrollBar().setValue(dock.tabs.widget(index).verticalScrollBar().maximum())
        capture_form('02b-scaling-options.png')
dock.open_completed_run(args.run)
index = next(i for i in range(dock.spectrum_domain.count()) if tuple(dock.spectrum_domain.itemData(i)) == ('assessment', 'window'))
dock.spectrum_domain.setCurrentIndex(index)
center = dock.spectrum_center.currentData()
dock.spectrum_panel.setCurrentIndex(dock.spectrum_panel.findData('dq'))
capture('04-window-dq.png', dock)
dock.spectrum_panel.setCurrentIndex(dock.spectrum_panel.findData('f_alpha'))
capture('05-window-spectrum.png', dock)
popup = dock.spectrum_preview.open_enlarged()
capture('06-enlarged-spectrum.png', popup)
popup.close()
settle()
dock.spectrum_values.setMinimumHeight(370)
capture('07-per-q-values.png', dock.spectrum_values)
dock.spectrum_values.setMinimumHeight(120)
dock.spectrum_center.setCurrentIndex(dock.spectrum_center.findData(1))
capture('08-low-coverage.png', dock)
assert '66.7%' in dock.spectrum_note.text()
dock.spectrum_center.setCurrentIndex(dock.spectrum_center.findData(center))
dock.result_tabs.setCurrentIndex(1)
dock.figure_list.setCurrentRow(0)
capture('09-figures.png', dock)
popup = dock.preview.open_enlarged()
capture('10-enlarged-figure.png', popup)
popup.close()
dock.result_tabs.setCurrentIndex(2)
dock.log.verticalScrollBar().setValue(0)
capture('11-run-details.png', dock, 760)
assert 'Analysis settings' in dock.log.toPlainText()
dock.result_tabs.setCurrentIndex(0)
dock.resize(720, 650)
settle()
bar = dock.results_page.verticalScrollBar()
assert bar.maximum() > 0
bar.setValue(bar.maximum())
capture('12-results-scroll.png', dock)
(example / 'recipe.json').write_text(json.dumps(config.recipe(), indent=2), encoding='utf-8')
project.setFileName(str(example / 'MUSA_Aland.qgz'))
project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(iface.canvas.extent(), lines.crs()))
assert project.write()
summary = {'qgis_version': Qgis.QGIS_VERSION, 'line_features': lines.featureCount(),
           'crs': lines.crs().authid(), 'selected_center': center, 'screenshots': sorted(p.name for p in images.glob('*.png')),
           'source_run': str(args.run), 'bundle': str(args.bundle), 'status':'pass'}
(root / 'capture_validation.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
dock.detach()
dock.close()
iface.window.close()
app.processEvents()

"""Execute and capture the complete real QGIS workflow with synthetic inputs.

Run with QGIS Python: capture_user_guide_qgis.py bundle.zip --output NEW_FOLDER.
All Qt widgets run offscreen; no desktop input, user profile or modal exec loop.
"""
# ruff: noqa: E402
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('bundle', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--affected-only', action='store_true', help='Capture only round-3 affected guide steps')
parser.add_argument('--completed-run', type=Path, help='Reopen an existing run for selective recapture without recalculation')
args = parser.parse_args()
root = Path(os.path.abspath(args.output))  # keep the caller's (possibly mapped) path in screenshots
root.mkdir(parents=True, exist_ok=False)
images = root / 'screenshots'
walk = root / 'recorrido'
images.mkdir()
walk.mkdir()
profile = root / 'qa-profile'
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QGIS_CUSTOM_CONFIG_PATH'] = str(profile)
os.environ['QGIS_AUTH_DB_DIR_PATH'] = str(profile / 'auth')
plugins = profile / 'python/plugins'
with zipfile.ZipFile(args.bundle) as archive:
    if not all(n.startswith('musa_qgis/') and '..' not in Path(n).parts for n in archive.namelist()):
        raise ValueError('Unexpected bundle paths')
    archive.extractall(plugins)
sys.path.insert(0, str(plugins))
from qgis.core import (Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsFeature,
                       QgsGeometry, QgsProject, QgsVectorLayer, QgsLineSymbol, QgsFillSymbol,
                       QgsVectorFileWriter, QgsReferencedRectangle)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QUrl, QLocale
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase, QTextCursor, QPixmap
from qgis.PyQt.QtWidgets import QMainWindow
import numpy as np

wall_started, cpu_started = time.perf_counter(), time.process_time()
app = QgsApplication([], True, str(profile))
app.initQgis()
QgsApplication.setMaxThreads(2)
QLocale.setDefault(QLocale('en_US'))
assert Qgis.QGIS_VERSION.startswith('3.44.12')
assert Path(QgsApplication.qgisSettingsDirPath()).resolve().is_relative_to(profile.resolve())
QFontDatabase.addApplicationFont('C:/Windows/Fonts/arial.ttf')
app.setFont(QFont('Arial', 10))
sys.path.insert(0, str(Path(QgsApplication.prefixPath()) / 'python/plugins'))
from processing.core.Processing import Processing
from processing.gui.AlgorithmDialog import AlgorithmDialog
Processing.initialize()
from musa_qgis import classFactory
from musa_qgis.runtime import core

project = QgsProject.instance()
crs = QgsCoordinateReferenceSystem()
assert crs.createFromProj('+proj=eqc +R=6371000 +units=m +no_defs +type=crs')
assert crs.createFromWkt(crs.toWkt().replace('unknown', 'MUSA synthetic UNLOCATED model metres'))
project.setCrs(crs)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tutorial_network import fracture_network
network, domain, families = fracture_network()
lines = QgsVectorLayer('LineString', '627 fractures: three families (model m)', 'memory')
boundary = QgsVectorLayer('Polygon', 'Synthetic observed domain (model m)', 'memory')
for layer, geometries in ((lines, network), (boundary, [domain])):
    layer.setCrs(crs)
    features = []
    for geometry in geometries:
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt(geometry.wkt))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    project.addMapLayer(layer)
lines.renderer().setSymbol(QgsLineSymbol.createSimple({'line_color':'#243f53', 'line_width':'.3'}))
boundary.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'246,242,228,140', 'outline_color':'#b46431', 'outline_width':'.5'}))
example = root / 'example'
example.mkdir()
inputs = example / 'synthetic.gpkg'
for i, (name, layer) in enumerate((('lineaments', lines), ('boundary', boundary))):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'GPKG'
    options.layerName = name
    if i:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    result = QgsVectorFileWriter.writeAsVectorFormatV3(layer, str(inputs), project.transformContext(), options)
    assert result[0] == QgsVectorFileWriter.NoError, result


class Interface:
    def __init__(self):
        self.window = QMainWindow()
        self.window.setWindowTitle('QGIS 3.44.12 | MUSA synthetic example')
        self.window.resize(1100, 1000)
        self.canvas = QgsMapCanvas()
        self.canvas.setLayers([lines, boundary])
        self.canvas.setDestinationCrs(crs)
        self.canvas.setCanvasColor(QColor('#fafbf8'))
        extent = boundary.extent()
        extent.scale(1.1)
        self.canvas.setExtent(extent)
        self.window.setCentralWidget(self.canvas)
        self.menu = self.window.menuBar().addMenu('Vector')
        self.toolbar = self.window.addToolBar('MUSA')
    def mainWindow(self):
        return self.window
    def activeLayer(self):
        return lines
    def addDockWidget(self, area, dock):
        self.window.addDockWidget(area, dock)
    def removeDockWidget(self, dock):
        self.window.removeDockWidget(dock)
    def addPluginToVectorMenu(self, name, action):
        self.menu.addAction(action)
    def removePluginVectorMenu(self, name, action):
        self.menu.removeAction(action)
    def addToolBarIcon(self, action):
        self.toolbar.addAction(action)
    def removeToolBarIcon(self, action):
        self.toolbar.removeAction(action)


def settle():
    for _ in range(8):
        app.processEvents()
        time.sleep(.025)


def wait_until(predicate, seconds=180):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            settle()
            return
        time.sleep(.02)
    raise AssertionError('Timed out waiting for task')


rows = []
def capture(name, widget, action, outcome):
    if args.affected_only and name not in {
        '02-quality.png', '02b-scaling-options.png', '14-comparison.png',
        '14b-global-spectrum.png', '11-run-details.png', '17-comparison-es.png',
        '18-processing-scaling_support.png', '19-processing-scaling_support-complete.png',
        '20-reopened.png', '04-window-dq.png', '05-window-spectrum.png',
        '08-low-coverage.png', '08b-curved-window.png',
    }:
        return
    settle()
    # Render the whole widget independently of the offscreen backing store.
    # Reused floating windows can otherwise retain partially painted headers.
    widget.repaint()
    image = QPixmap(widget.size())
    image.fill(QColor('white'))
    widget.render(image)
    assert image.save(str(images / name))
    filename = f'{len(rows)+1:02d}-{name}'
    assert image.save(str(walk / filename))
    rows.append(dict(step=len(rows)+1, action=action, result=outcome, capture=filename, status='OK'))
    print('CAPTURE', filename, flush=True)


iface = Interface()
iface.window.show()
iface.canvas.refresh()
iface.canvas.waitWhileRendering()
capture('00-map.png', iface.window, 'Cargar traza y polígono sintéticos', '627 trazas; tres familias 20°, 80°, 140°; polígono heptagonal; metros de modelo sin ubicación geográfica')
plugin = classFactory(iface)
plugin.initGui()
plugin.show_workbench()
dock = plugin.dock
dock.setFloating(True)
dock.resize(1000, 1240)
MUSA, RunConfig, execute = core()
scales = tuple(np.geomspace(125, 2500, 16))
config = RunConfig(mother_cell_m=2000, divisors=(2,4,8,16), q_min=0, q_max=4, q_step=.5,
                   min_r2=.9, threshold_m=0, local=False, structural=False,
                   moving=True, window_sizes_m=(6000,), window_step_m=2000,
                   moving_divisors=(2,4,8,16), plots=True, gis=True,
                   scaling_resolution_m=1, scaling_scales_m=scales,
                   scaling_null_replicates=99, scaling_null_tail='two_sided',
                   renyi_order_policy='inform_q0_q2', classic_comparison=True)
dock.learning_language_selector.setCurrentIndex(dock.learning_language_selector.findData('en'))
dock.apply_config(config)
dock.lines.setLayer(lines)
dock.boundary.setLayer(boundary)
dock.crs.setCrs(crs)
runs = root / 'runs'
runs.mkdir()
dock.output_root.setText(str(runs))
dock.update_source()
for index, name, action in ((0,'01-analysis.png','Configurar Analysis'),
                             (1,'02-quality.png','Configurar Quality'),
                             (2,'03-moving-windows.png','Configurar Moving windows')):
    dock.tabs.setCurrentIndex(index)
    page = dock.tabs.widget(index)
    page.verticalScrollBar().setValue(0)
    capture(name, dock, action, 'Valores explícitos conservados en example/recipe.json')
    if index == 1:
        dock.resize(1000, 900)
        settle()
        page.verticalScrollBar().setValue(page.verticalScrollBar().maximum())
        settle()
        assert page.verticalScrollBar().value() > 0
        capture('02b-scaling-options.png', dock, 'Declarar resolución, intervalo, comparación y Monte Carlo',
                'Resolución 1 m; 16 escalas 125–2500 m; 99 réplicas; cola bilateral')
        dock.resize(1000, 1240)
(example / 'recipe.json').write_text(json.dumps(config.recipe(), indent=2), encoding='utf-8')
dock.tabs.setCurrentIndex(0)
settle()
analysis_started = time.perf_counter()
if args.completed_run:
    dock.open_completed_run(args.completed_run.resolve())
else:
    dock.run_button.click()
    assert dock.task is not None
    capture('13-running.png', dock, 'Pulsar Run MUSA', 'Tarea real de fondo iniciada; botón desactivado durante la ejecución')
    wait_until(lambda: dock.task is None, seconds=600)
analysis_seconds = time.perf_counter() - analysis_started
if not args.completed_run:
    assert dock.status.text() == 'Analysis complete', dock.log.toPlainText()
run = dock.last_output
assert json.loads((run / 'run_manifest.json').read_text())['status'] == 'complete'
assert 'failed' not in dock.log.toPlainText().lower(), dock.log.toPlainText()
report = json.loads((run / 'scaling_support.json').read_text())
global_report = next(s for s in report['supports'] if s['support_id'] == 'global')
assert global_report['null']['status'] == 'complete', global_report['null']
dock.spectrum_panel.setCurrentIndex(dock.spectrum_panel.findData('dq'))
capture('14-comparison.png', dock, 'Leer comparación clásica y D0 de MUSA', 'Ejecución completa; comparación en bloque propio; estado e intervalo conservados')
dock.spectrum_panel.setCurrentIndex(dock.spectrum_panel.findData('f_alpha'))
dock.resize(1000, 1050)
settle()
dock.results_page.ensureWidgetVisible(dock.spectrum_note)
capture('14b-global-spectrum.png', dock, 'Leer espectro global', 'La forma global conserva su motivo de abstención; la ventana elegida muestra cuatro puntos respaldados')
dock.resize(1000, 1240)

dock.spectrum_domain.setCurrentIndex(next(i for i in range(dock.spectrum_domain.count())
                                          if tuple(dock.spectrum_domain.itemData(i)) == ('assessment','window')))
from musa_qgis._core.musa.spectrum_products import read_spectrum, spectrum_shape_reasons
candidates = [series for series in dock._spectrum_index
              if series['source'] == 'assessment' and series['kind'] == 'window'
              and not spectrum_shape_reasons(read_spectrum(run / 'spectrum_curves.sqlite', series['series_id']))
              and sum(point['accepted'] for point in read_spectrum(
                  run / 'spectrum_curves.sqlite', series['series_id'])['points']) >= 4]
assert candidates, 'The teaching example must contain a visible supported window spectrum'
assert any(sum(p['accepted'] for p in read_spectrum(run / 'spectrum_curves.sqlite', c['series_id'])['points']) >= 4 for c in candidates)
selected = max(candidates, key=lambda series: dock._support_details[series['support_id']]['coverage'])['center_id']
dock.spectrum_center.setCurrentIndex(dock.spectrum_center.findData(selected))
dock.spectrum_panel.setCurrentIndex(dock.spectrum_panel.findData('dq'))
capture('04-window-dq.png', dock, 'Leer Dq por ventana', 'Estados de cada q y motivos visibles; centro seleccionado por disponibilidad')
dock.spectrum_panel.setCurrentIndex(dock.spectrum_panel.findData('f_alpha'))
capture('05-window-spectrum.png', dock, 'Leer f(alpha)', 'Espectro del mismo soporte; referencias del pico separadas')
popup = dock.spectrum_preview.open_enlarged()
capture('06-enlarged-spectrum.png', popup, 'Ampliar espectro', 'Vista nativa con barra de navegación')
popup.close()
dock.export_selected_spectrum(root / 'selected-spectrum.svg')
capture('07-per-q-values.png', dock.spectrum_values, 'Revisar tabla por q', 'Tabla completa de nueve órdenes; valores y estados separados')
# Boundary windows have insufficient observed area; select one from the saved index.
from musa_qgis._core.musa.spectrum_products import read_spectrum
low = None
for series in dock._spectrum_index:
    if series['source'] == 'assessment' and series['kind'] == 'window':
        curve = read_spectrum(run / 'spectrum_curves.sqlite', series['series_id'])
        if dock._support_details.get(series['support_id'], {}).get('coverage', 1) < .8:
            low = series['center_id']
            break
assert low is not None
index = dock.spectrum_center.findData(low)
assert index >= 0
dock.spectrum_center.setCurrentIndex(index)
capture('08-low-coverage.png', dock, 'Examinar ventana sin dimensión', 'Se conservan valores ausentes y el motivo de información insuficiente')
dock.spectrum_center.setCurrentIndex(dock.spectrum_center.findData(selected))
dock.spectrum_center.setCurrentIndex(dock.spectrum_center.findData(11))
dock.spectrum_panel.setCurrentIndex(dock.spectrum_panel.findData('dq'))
capture('08b-curved-window.png', dock, 'Leer ventana con curvatura y soporte útil',
        'Centro 11: cobertura 97.61%; D0 compatible, D1 no respaldado por curvatura y q=4 insuficiente')
dock.spectrum_center.setCurrentIndex(dock.spectrum_center.findData(selected))
dock.spectrum_panel.setCurrentIndex(dock.spectrum_panel.findData('f_alpha'))

dock.result_tabs.setCurrentIndex(1)
assert dock.figure_list.count() > 0
dock.figure_list.setCurrentRow(0)
dock.results_page.verticalScrollBar().setValue(dock.results_page.verticalScrollBar().maximum())
capture('09-figures.png', dock, 'Seleccionar figura guardada', 'Galería y figura de la ejecución vigente')
popup = dock.preview.open_enlarged()
capture('10-enlarged-figure.png', popup, 'Ampliar figura', 'Controles de zoom y ajuste disponibles')
popup.close()
dock.result_tabs.setCurrentIndex(2)
dock.results_page.verticalScrollBar().setValue(0)
dock.log.verticalScrollBar().setValue(0)
capture('11-run-details.png', dock, 'Leer detalles y resultado Monte Carlo',
        f"Manifiesto completo; Monte Carlo global: p={global_report['null']['p_value']}; 99 réplicas")
dock.result_tabs.setCurrentIndex(0)
dock.resize(760,650)
dock.results_page.verticalScrollBar().setValue(dock.results_page.verticalScrollBar().maximum())
capture('12-results-scroll.png', dock, 'Desplazar Results en panel pequeño', 'Desplazamiento exterior e interior disponibles')
dock.resize(1000,1240)
dock.results_page.verticalScrollBar().setValue(0)
for language in ('en','es'):
    dock.learning_language_selector.setCurrentIndex(dock.learning_language_selector.findData(language))
    dock.tabs.setCurrentWidget(dock.learning_page)
    dock.learning_reader.verticalScrollBar().setValue(0)
    capture(f'15-learn-{language}.png', dock, f'Abrir Fundamentos ({language})', 'Capítulo canónico cargado con selector de idioma')
    for section, text in (('rods','An example: high R' if language=='en' else 'Un ejemplo: R'),
                           ('raster','From vector length' if language=='en' else 'De la longitud vectorial')):
        dock.learning_reader.moveCursor(QTextCursor.Start)
        assert dock.learning_reader.find(text)
        dock.learning_reader.ensureCursorVisible()
        settle()
        bar = dock.learning_reader.verticalScrollBar()
        bar.setValue(bar.value() + dock.learning_reader.cursorRect().top() - 12)
        cursor = dock.learning_reader.textCursor()
        cursor.clearSelection()
        dock.learning_reader.setTextCursor(cursor)
        capture(f'16-{section}-{language}.png', dock, f'Leer ejemplo {section} ({language})', 'Figura local y explicación calculada disponibles')
    for filename in (f'knowledge_{name}.{language}.png' for name in ('box_counting', 'raster', 'cantor', 'rods')):
        assert dock.learning_reader.document().resource(2, QUrl('images/'+filename)) is not None
    assert dock.learning_reader.horizontalScrollBar().maximum() == 0
    if language == 'es':
        dock.tabs.setCurrentWidget(dock.results_page)
        capture('17-comparison-es.png', dock, 'Leer comparación en español', 'Bloque de comparación traducido íntegramente')
dock.learning_language_selector.setCurrentIndex(dock.learning_language_selector.findData('en'))
# Run each Processing algorithm through its real dialog and Run button.
processing_results = {}
base = dict(LINES=lines.id(), BOUNDARY=boundary.id(), CRS=crs)
for alg, parameters in (
    ('analyze', dict(base, MOTHER=2000, DIVISORS='2,4,8,16', RESOLUTION=1, Q_MIN=0,Q_MAX=4,Q_STEP=.5,
                     LOCAL=False, STRUCTURAL=False, PLOTS=True, MIN_R2=.9, CLASSIC_COMPARISON=True)),
    ('scaling_support', dict(base, SCALES=','.join(map(str,scales)), RESOLUTION=1, Q_MIN=0,Q_MAX=4,Q_STEP=.5,
                             NULL_REPLICATES=99, RENYI_ORDER_POLICY=1, NULL_TAIL=1, CLASSIC_COMPARISON=True)),
    ('run_recipe', dict(base, RECIPE=str(example / 'processing-recipe.json')))) if not args.completed_run else ():
    if alg == 'run_recipe':
        (example / 'processing-recipe.json').write_text(
            json.dumps(replace(config, moving=False, scaling_null_replicates=0).recipe()), encoding='utf-8')
    output = root / ('processing-'+alg)
    parameters['OUTPUT'] = str(output)
    algorithm = QgsApplication.processingRegistry().algorithmById('musa:'+alg).create()
    dialog = AlgorithmDialog(algorithm)
    dialog.setParameters(parameters)
    dialog.resize(1150,1000)
    dialog.show()
    capture(f'18-processing-{alg}.png', dialog, 'Configurar musa:'+alg, 'Parámetros y ayuda del algoritmo real')
    dialog.runButton().click()
    wait_until(lambda: (output / 'run_manifest.json').is_file() and
               json.loads((output / 'run_manifest.json').read_text())['status'] in ('complete','failed'))
    wait_until(lambda: not QgsApplication.taskManager().activeTasks())
    manifest = json.loads((output / 'run_manifest.json').read_text())
    assert manifest['status'] == 'complete', manifest
    dialog.showLog()
    capture(f'19-processing-{alg}-complete.png', dialog, 'Ejecutar musa:'+alg, 'Manifiesto complete y registro final real')
    processing_results[alg] = manifest
    dialog.close()
dock.open_completed_run(run)
dock.tabs.setCurrentWidget(dock.results_page)
dock.result_tabs.setCurrentIndex(2)
dock.log.verticalScrollBar().setValue(0)
assert 'Saved analysis' in dock.log.toPlainText()
capture('20-reopened.png', dock, 'Reabrir ejecución guardada', 'Espectros y detalles recuperados sin recalcular')
project.setFileName(str(example / 'MUSA_synthetic.qgz'))
project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(iface.canvas.extent(),crs))
assert project.write()
(root / 'walkthrough.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(walk / 'RECORRIDO.md').write_text('# Recorrido QGIS 3.44.12\n\n'
    'Datos sintéticos sin ubicación geográfica. Qt fuera de pantalla; widgets completos. Revisión visual pendiente hasta inspección de cada PNG.\n\n'
    '| Paso | Acción | Resultado | Captura | Estado |\n| --- | --- | --- | --- | --- |\n'+
    '\n'.join(f"| {r['step']} | {r['action']} | {r['result']} | [{r['capture']}]({r['capture']}) | {r['status']} |" for r in rows)+'\n',encoding='utf-8')
summary = dict(qgis_version=Qgis.QGIS_VERSION, bundle=str(args.bundle),
               bundle_sha256=hashlib.sha256(args.bundle.read_bytes()).hexdigest(),
               run=str(run), global_assessment=global_report, screenshot_count=len(rows),
               low_center=low, selected_center=selected, settings_path=QgsApplication.qgisSettingsDirPath(),
               analysis_seconds=analysis_seconds,
               wall_seconds=time.perf_counter()-wall_started,cpu_seconds_main_process=time.process_time()-cpu_started,
               status='pass')
(root / 'capture_validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('PASS',len(rows),'captures',flush=True)
plugin.unload()
iface.window.close()
project.clear()
app.processEvents()

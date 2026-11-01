"""English QGIS workbench: project inputs, recipes, background execution, results."""

from datetime import datetime
import json
from pathlib import Path
import uuid
import weakref

from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QColor, QDesktopServices, QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    QgsApplication,
    QgsGraduatedSymbolRenderer,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsRendererRange,
    QgsSymbol,
    QgsTask,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox, QgsProjectionSelectionWidget

from .inputs import make_analyzer, snapshot_sources, validate_metric_crs
from .native_gis import export_mother_layers
from .runtime import core, icon_path


class AnalysisTask(QgsTask):
    message = pyqtSignal(str)

    def __init__(self, snapshot, config, output, receiver):
        super().__init__("MUSA — multifractal analysis", QgsTask.CanCancel)
        self.snapshot, self.config, self.output = snapshot, config, output
        self.receiver = weakref.ref(receiver)
        self.manifest, self.error = None, ""

    def run(self):
        try:
            _, _, execute = core()
            self.manifest = execute(
                make_analyzer(self.snapshot, self.config),
                self.config,
                self.output,
                source_info=self.snapshot["info"],
                cancelled=self.isCanceled,
                progress=self.report,
                gis_exporter=export_mother_layers,
            )
            return not self.isCanceled()
        except Exception as exc:
            self.error = str(exc)
            return False

    def report(self, value, message):
        self.setProgress(value)
        self.message.emit(message)

    def finished(self, success):
        receiver = self.receiver()
        if receiver is not None and not sip.isdeleted(receiver):
            receiver.task_finished(self, success)


def _spin(value, minimum=0, maximum=1e9, decimals=3):
    widget = QDoubleSpinBox()
    widget.setRange(minimum, maximum)
    widget.setDecimals(decimals)
    widget.setValue(value)
    return widget


class MusaDock(QDockWidget):
    def __init__(self, iface):
        super().__init__("MUSA — Multifractal Workbench", iface.mainWindow())
        self.iface, self.task, self.last_output = iface, None, None
        self.setObjectName("MusaWorkbench")
        self.setMinimumWidth(380)
        self.setWindowIcon(QIcon(icon_path()))
        body = QWidget()
        layout = QVBoxLayout(body)
        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(icon_path()).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header.addWidget(logo)
        title = QLabel("<b>MUSA</b><br>Multifractal Spectrum Analyzer")
        header.addWidget(title, 1)
        layout.addLayout(header)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        analysis, form = self._tab("Analysis")
        self.lines = self._layer_combo(QgsMapLayerProxyModel.LineLayer)
        self.boundary = self._layer_combo(QgsMapLayerProxyModel.PolygonLayer)
        inputs = self._group(form, "1 · Project inputs")
        inputs.addRow("Lineaments", self.lines)
        inputs.addRow("Boundary", self.boundary)
        self.selected_only = QCheckBox("Use selected lines only")
        inputs.addRow(self.selected_only)
        self.crs = QgsProjectionSelectionWidget()
        self.crs.setCrs(QgsProject.instance().crs())
        inputs.addRow("Analysis CRS", self.crs)
        self.source_info = QLabel("Choose a line layer and polygon boundary. Analysis units must be metres.")
        self.source_info.setWordWrap(True)
        inputs.addRow(self.source_info)
        self.lines.layerChanged.connect(self.update_source)
        self.boundary.layerChanged.connect(self.update_source)
        self.crs.crsChanged.connect(self.update_source)
        scales = self._group(form, "2 · Scale design")
        self.mother = _spin(4000, 0.001)
        self.divisors = QLineEdit("2,4,6,8,16")
        scales.addRow("Mother cell (m)", self.mother)
        scales.addRow("Internal divisors", self.divisors)
        self.q_min, self.q_max, self.q_step = _spin(-4, -100, 100), _spin(4, -100, 100), _spin(1, 0.001, 200)
        q_row = QHBoxLayout()
        for label, widget in (("Min", self.q_min), ("Max", self.q_max), ("Step", self.q_step)):
            q_row.addWidget(QLabel(label))
            q_row.addWidget(widget)
        scales.addRow("q range", q_row)
        scales.addRow(QLabel("Internal box sizes = mother size / divisors."))
        products = self._group(form, "3 · Products")
        self.options = {}
        for key, label, checked in (
            ("local", "Mother-cell spectra and zeta reliability", True),
            ("structural", "Density, orientation and anisotropy", True),
            ("network", "Whole-network connectivity statistics", False),
            ("plots", "Spectrum and diagnostic figures", True),
            ("gis", "GeoPackage layers", True),
        ):
            box = QCheckBox(label)
            box.setChecked(checked)
            self.options[key] = box
            products.addRow(box)
        products.addRow(QLabel("Global spectra and scale diagnostics are always included."))
        output = self._group(form, "4 · Output")
        self.output_root = QLineEdit()
        self.output_root.setPlaceholderText("Choose a parent folder; each run creates a new subfolder")
        row = QHBoxLayout()
        row.addWidget(self.output_root, 1)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse_output)
        row.addWidget(browse)
        output.addRow(row)
        self.add_layers = QCheckBox("Load spatial results into QGIS")
        self.add_layers.setChecked(True)
        output.addRow(self.add_layers)
        recipes = QHBoxLayout()
        for label, callback in (("Load recipe", self.load_recipe), ("Save recipe", self.save_recipe)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            recipes.addWidget(button)
        form.addLayout(recipes)
        form.addStretch()
        _, advanced = self._tab("Quality")
        quality = self._group(advanced, "Numerical quality")
        self.min_r2 = _spin(0.9, 0, 0.999999, 6)
        self.threshold = _spin(0.01, 0, 1e9, 4)
        self.min_zeta = _spin(0.15, 0, 1, 4)
        self.zeta_floor = _spin(0.25, 0, 1, 4)
        self.zeta_exponents = QLineEdit("1,1,1,1")
        self.negative_floor = _spin(0, 0, 1, 6)
        self.bootstrap, self.local_bootstrap, self.seed = QSpinBox(), QSpinBox(), QSpinBox()
        for spin in (self.bootstrap, self.local_bootstrap):
            spin.setRange(0, 10000)
        self.seed.setRange(0, 2147483647)
        self.seed.setValue(42)
        self.confidence = _spin(0.95, 0.001, 0.999, 3)
        for label, widget in (
            ("Minimum fit R2", self.min_r2),
            ("Cell length threshold (m)", self.threshold),
            ("Minimum mean zeta", self.min_zeta),
            ("Zeta scale floor", self.zeta_floor),
            ("Zeta exponents", self.zeta_exponents),
            ("Negative-q floor fraction", self.negative_floor),
            ("Global bootstrap iterations", self.bootstrap),
            ("Local bootstrap iterations", self.local_bootstrap),
            ("Confidence level", self.confidence),
            ("Random seed", self.seed),
        ):
            quality.addRow(label, widget)
        self.sensitivity = QCheckBox("Export zeta sensitivity comparisons")
        quality.addRow(self.sensitivity)
        note = QLabel(
            "Canonical and zeta-weighted estimates remain separate. Zeta measures numerical support; it is not a physical property or geological probability."
        )
        note.setWordWrap(True)
        advanced.addWidget(note)
        advanced.addStretch()
        _, moving = self._tab("Moving windows")
        windows = self._group(moving, "Experimental · overlapping supports")
        self.moving = QCheckBox("Enable moving-window analysis")
        windows.addRow(self.moving)
        self.window_sizes = QLineEdit("2000,4000,8000")
        self.window_step = _spin(1000, 0.001)
        self.window_divisors = QLineEdit("2,4,8,16")
        self.ensemble = QCheckBox("Average 16 grid origins (slower)")
        self.proximity = QLineEdit()
        self.proximity.setPlaceholderText("Optional: 100,250,500")
        for label, widget in (
            ("Window sizes (m)", self.window_sizes),
            ("Centre spacing (m)", self.window_step),
            ("Internal divisors", self.window_divisors),
            ("Proximity radii (m)", self.proximity),
        ):
            windows.addRow(label, widget)
        windows.addRow(self.ensemble)
        note = QLabel(
            "Exports overlapping spectra, planar junctions and descriptive structural context. Requires GeoPandas and its GIS dependencies. No inferred permeability or prospectivity. Cancellation is checked between workflow stages; a window stage can take time."
        )
        note.setWordWrap(True)
        moving.addWidget(note)
        moving.addStretch()
        self.results_page, results = self._tab("Results")
        self.summary = QLabel("No analysis yet.")
        self.summary.setWordWrap(True)
        results.addWidget(self.summary)
        self.figure_list = QListWidget()
        self.figure_list.setMaximumHeight(120)
        self.figure_list.currentTextChanged.connect(self.show_figure)
        results.addWidget(self.figure_list)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        results.addWidget(self.preview)
        open_folder = QPushButton("Open output folder")
        open_folder.clicked.connect(self.open_output)
        results.addWidget(open_folder)
        self.log = QTextBrowser()
        self.log.setMinimumHeight(100)
        results.addWidget(self.log, 1)
        buttons = QHBoxLayout()
        self.run_button = QPushButton("Run MUSA")
        self.run_button.clicked.connect(self.start_run)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_run)
        self.cancel_button.setEnabled(False)
        buttons.addWidget(self.run_button, 1)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.status = QLabel("Ready")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.setWidget(body)
        active = iface.activeLayer()
        if isinstance(active, QgsVectorLayer) and active.geometryType() == 1:
            self.lines.setLayer(active)
            try:
                validate_metric_crs(active.crs())
                self.crs.setCrs(active.crs())
            except ValueError:
                pass
        self.update_source()

    def _tab(self, name):
        page = QWidget()
        layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.tabs.addTab(scroll, name)
        return scroll, layout

    @staticmethod
    def _group(layout, title):
        group = QGroupBox(title)
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        layout.addWidget(group)
        return form

    @staticmethod
    def _layer_combo(filters):
        combo = QgsMapLayerComboBox()
        combo.setFilters(filters)
        combo.setAllowEmptyLayer(True)
        combo.setLayer(None)
        return combo

    def update_source(self, *args):
        line, boundary = self.lines.currentLayer(), self.boundary.currentLayer()
        try:
            validate_metric_crs(self.crs.crs())
            self.source_info.setText(
                f"Analysis CRS: {self.crs.crs().authid() or 'custom metric CRS'}. "
                f"{line.featureCount() if line else 0} line features; {boundary.featureCount() if boundary else 0} boundary features. "
                "Input layers are transformed to this CRS for analysis."
            )
        except ValueError as exc:
            self.source_info.setText(str(exc))

    @staticmethod
    def _numbers(widget):
        return tuple(float(value.strip()) for value in widget.text().split(",") if value.strip())

    def config(self):
        _, RunConfig, _ = core()
        return RunConfig(
            mother_cell_m=self.mother.value(),
            divisors=self._numbers(self.divisors),
            q_min=self.q_min.value(),
            q_max=self.q_max.value(),
            q_step=self.q_step.value(),
            threshold_m=self.threshold.value(),
            min_r2=self.min_r2.value(),
            bootstrap_iterations=self.bootstrap.value(),
            local_bootstrap_iterations=self.local_bootstrap.value(),
            bootstrap_ci=self.confidence.value(),
            seed=self.seed.value(),
            negative_q_floor_fraction=self.negative_floor.value(),
            reliable_min_zeta=self.min_zeta.value(),
            zeta_exponents=self._numbers(self.zeta_exponents),
            zeta_scale_floor=self.zeta_floor.value(),
            zeta_sensitivity=self.sensitivity.isChecked(),
            moving=self.moving.isChecked(),
            window_sizes_m=self._numbers(self.window_sizes),
            window_step_m=self.window_step.value(),
            moving_divisors=self._numbers(self.window_divisors),
            origin_ensemble=self.ensemble.isChecked(),
            proximity_radii_m=self._numbers(self.proximity),
            **{key: box.isChecked() for key, box in self.options.items()},
        ).validate()

    def apply_config(self, config):
        for widget, value in (
            (self.mother, config.mother_cell_m),
            (self.q_min, config.q_min),
            (self.q_max, config.q_max),
            (self.q_step, config.q_step),
            (self.threshold, config.threshold_m),
            (self.min_r2, config.min_r2),
            (self.bootstrap, config.bootstrap_iterations),
            (self.local_bootstrap, config.local_bootstrap_iterations),
            (self.confidence, config.bootstrap_ci),
            (self.seed, config.seed),
            (self.negative_floor, config.negative_q_floor_fraction),
            (self.min_zeta, config.reliable_min_zeta),
            (self.zeta_floor, config.zeta_scale_floor),
            (self.window_step, config.window_step_m),
        ):
            widget.setValue(value)
        for widget, values in (
            (self.divisors, config.divisors),
            (self.zeta_exponents, config.zeta_exponents),
            (self.window_sizes, config.window_sizes_m),
            (self.window_divisors, config.moving_divisors),
            (self.proximity, config.proximity_radii_m),
        ):
            widget.setText(",".join(f"{v:g}" for v in values))
        for key, box in self.options.items():
            box.setChecked(getattr(config, key))
        self.moving.setChecked(config.moving)
        self.ensemble.setChecked(config.origin_ensemble)
        self.sensitivity.setChecked(config.zeta_sensitivity)

    def browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Choose output parent folder", self.output_root.text())
        if path:
            self.output_root.setText(path)

    def save_recipe(self):
        try:
            recipe = self.config().recipe()
            path, _ = QFileDialog.getSaveFileName(self, "Save MUSA recipe", "musa_recipe.json", "JSON (*.json)")
            if path:
                Path(path).write_text(json.dumps(recipe, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "MUSA", str(exc))

    def load_recipe(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load MUSA recipe", "", "JSON (*.json)")
        if not path:
            return
        try:
            _, RunConfig, _ = core()
            self.apply_config(RunConfig.from_recipe(json.loads(Path(path).read_text(encoding="utf-8"))))
        except Exception as exc:
            QMessageBox.warning(self, "MUSA", str(exc))

    def start_run(self):
        if self.task is not None:
            return
        try:
            config = self.config()
            parent = Path(self.output_root.text())
            if not self.output_root.text().strip() or not parent.is_dir():
                raise ValueError("Choose an existing output parent folder.")
            snapshot = snapshot_sources(
                self.lines.currentLayer(),
                self.boundary.currentLayer(),
                self.crs.crs(),
                selected_only=self.selected_only.isChecked(),
            )
            output = parent / ("MUSA_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8])
            self.start_snapshot(snapshot, config, output)
        except Exception as exc:
            self.status.setText(str(exc))
            self.log.append(str(exc))

    def start_snapshot(self, snapshot, config, output):
        if self.task is not None:
            raise RuntimeError("An analysis is already running.")
        self.task = AnalysisTask(snapshot, config, str(output), self)
        self.task.progressChanged.connect(self.update_progress)
        self.task.message.connect(self.on_message)
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setValue(0)
        self.status.setText("Running")
        self.load_results = self.add_layers.isChecked()
        QgsApplication.taskManager().addTask(self.task)

    def on_message(self, message):
        self.status.setText(message)
        self.log.append(message)

    def update_progress(self, value):
        self.progress.setValue(int(value))

    def cancel_run(self):
        if self.task is not None:
            self.task.cancel()
            self.status.setText("Cancellation requested; waiting for the current operation.")

    def detach(self):
        if self.task is not None:
            self.task.receiver = lambda: None
            self.task.cancel()
            for signal in (self.task.progressChanged, self.task.message):
                try:
                    signal.disconnect()
                except (TypeError, RuntimeError):
                    pass
            self.task = None

    def task_finished(self, task, success):
        self.task = None
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.last_output = Path(task.output)
        if not success:
            self.on_message(task.error or "Analysis cancelled. Partial outputs retained.")
            return
        manifest = task.manifest
        self.progress.setValue(100)
        self.on_message("Analysis complete")
        self.summary.setText(
            f"Accepted q: {manifest['accepted_q']} · Rejected q: {manifest['rejected_q']}\n{task.output}"
        )
        self.figure_list.clear()
        self.figure_list.addItems([file.name for file in sorted(self.last_output.glob("*.png"))])
        if self.figure_list.count():
            self.figure_list.setCurrentRow(0)
        if self.load_results:
            try:
                load_spatial_results(task.output)
            except Exception as exc:
                self.log.append(f"Analysis saved; layer loading failed: {exc}")
        self.tabs.setCurrentWidget(self.results_page)

    def show_figure(self, filename):
        if self.last_output and filename:
            self.preview.setPixmap(
                QPixmap(str(self.last_output / filename)).scaled(
                    max(300, self.width() - 55), 350, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )

    def open_output(self):
        if self.last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output)))


def load_spatial_results(output):
    """Main-thread only. Group each run and keep density/reliability separate."""
    from osgeo import ogr
    import math

    project = QgsProject.instance()
    group = project.layerTreeRoot().addGroup(Path(output).name)
    count = 0
    for path in sorted(Path(output).glob("*.gpkg")):
        datasource = ogr.Open(str(path))
        if datasource is None:
            continue
        names = [layer.GetName() for layer in datasource]
        datasource = None
        for name in names:
            if name in ("layer_styles", "candidate_evidence", "candidate_scoring"):
                continue
            layer = QgsVectorLayer(f"{path}|layername={name}", name.replace("_", " ").title(), "ogr")
            if not layer.isValid():
                continue
            field = (
                "zeta_mean" if "multifractal" in name else "density_m_per_km2" if "structural_stats" in name else None
            )
            if field and layer.fields().indexFromName(field) >= 0:
                values = []
                for feature in layer.getFeatures():
                    try:
                        value = float(feature[field])
                        if math.isfinite(value):
                            values.append(value)
                    except (ValueError, TypeError):
                        pass
                if values and max(values) > min(values):
                    lo, hi = min(values), max(values)
                    ranges = []
                    for i, color in enumerate(("#eff3ff", "#bdd7e7", "#6baed6", "#3182bd", "#08519c")):
                        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
                        symbol.setColor(QColor(color))
                        low, high = lo + (hi - lo) * i / 5, lo + (hi - lo) * (i + 1) / 5
                        ranges.append(QgsRendererRange(low, high, symbol, f"{low:.3g} – {high:.3g}"))
                    layer.setRenderer(QgsGraduatedSymbolRenderer(field, ranges))
            project.addMapLayer(layer, False)
            node = group.addLayer(layer)
            node.setItemVisibilityChecked(
                name not in ("mother_multifractal_all_q", "mother_monofractal", "window_shifted_spectra")
            )
            count += 1
    return count

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
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
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
from .chart_view import ChartView, ImagePreview, ScrollSafeComboBox


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
        logo.setPixmap(QPixmap(icon_path()).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
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
        scaling = self._group(advanced, "Finite-range Renyi scaling support")
        self.scaling_support = QCheckBox("Assess scaling support (experimental)")
        self.scaling_resolution = _spin(0, 0, 1e9, 4)
        self.scaling_scales = QLineEdit()
        self.scaling_scales.setPlaceholderText("Blank: analysis scales; need at least 8 resolved scales")
        self.scaling_null = QSpinBox()
        self.scaling_null.setRange(0, 9999)
        self.scaling_limit = QSpinBox()
        self.scaling_limit.setRange(1, 1000)
        self.scaling_limit.setValue(25)
        self.scaling_order_policy = QComboBox()
        self.scaling_order_policy.addItem("Legacy: block on spectrum order", "legacy_block")
        self.scaling_order_policy.addItem("Inform q=0,2: warning without order veto", "inform_q0_q2")
        self.scaling_null_tail = QComboBox()
        self.scaling_null_tail.addItem("Upper tail (legacy)", "upper")
        self.scaling_null_tail.addItem("Two-sided", "two_sided")
        self.scaling_coarse_trim = _spin(0, 0, 1e6, 2)
        scaling.addRow(self.scaling_support)
        scaling.addRow("Observation resolution (m; required)", self.scaling_resolution)
        scaling.addRow("Box sizes (m)", self.scaling_scales)
        scaling.addRow("Trace-relocation null replicates (0=off; >=19)", self.scaling_null)
        scaling.addRow("Maximum windows to assess", self.scaling_limit)
        scaling.addRow("Renyi order policy", self.scaling_order_policy)
        scaling.addRow("Null test tail", self.scaling_null_tail)
        scaling.addRow("Coarse-end trimming: min effective q=2 boxes (0=off)", self.scaling_coarse_trim)
        note = QLabel("Tests fixed-interval Renyi Dq stability and curvature. Inform q=0,2 reports an order warning without blocking the finite-range slope contrast; all other gates remain. The optional null preserves trace shapes, lengths and orientations, but relocates them. A rejection concerns conditional spatial heterogeneity, not proof of multifractality. See also Processing: Assess Renyi scaling support, which runs independently of legacy fit acceptance.")
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
        self.summary.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        results.addWidget(self.summary)
        self.spectrum_open = QPushButton("Open completed run")
        self.spectrum_open.clicked.connect(self.browse_completed_run)
        results.addWidget(self.spectrum_open)
        self.result_tabs = QTabWidget()
        results.addWidget(self.result_tabs, 1)
        spectrum_page = QWidget()
        spectrum_layout = QVBoxLayout(spectrum_page)
        self.result_tabs.addTab(spectrum_page, "Spectra")
        spectra = self._group(spectrum_layout, "Choose domain or window")
        self.spectrum_domain, self.spectrum_center, self.spectrum_size, self.spectrum_estimator = (ScrollSafeComboBox() for _ in range(4))
        for combo in (self.spectrum_domain, self.spectrum_center, self.spectrum_size, self.spectrum_estimator):
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(12)
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._spectrum_index = []
        self._spectrum_figure = None
        for label, combo in (("Domain / calculation", self.spectrum_domain), ("Window center", self.spectrum_center),
                             ("Window size", self.spectrum_size), ("Estimator", self.spectrum_estimator)):
            spectra.addRow(label, combo)
        self.spectrum_note = QLabel("No indexed spectra yet.")
        self.spectrum_note.setWordWrap(True)
        self.spectrum_note.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        spectra.addRow(self.spectrum_note)
        self.spectrum_panel = ScrollSafeComboBox()
        self.spectrum_panel.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.spectrum_panel.setMinimumContentsLength(12)
        for label, name in (("Singularity spectrum · f(alpha)", "f_alpha"), ("Renyi dimensions · Dq", "dq"),
                            ("Mass exponent · tau(q)", "tau"), ("Singularity exponent · alpha(q)", "alpha"),
                            ("Overview · four charts", "all")):
            self.spectrum_panel.addItem(label, name)
        spectra.addRow("Chart", self.spectrum_panel)
        self.spectrum_panel.currentIndexChanged.connect(self.render_selected_spectrum)
        self.spectrum_preview = ChartView()
        self.spectrum_values = QTableWidget(0, 8)
        self.spectrum_values.setHorizontalHeaderLabels(["q", "Dq", "tau", "alpha", "f(alpha)", "Dq status", "Spectrum", "Reason"])
        self.spectrum_values.setEditTriggers(QTableWidget.NoEditTriggers)
        self.spectrum_values.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.spectrum_values.horizontalHeader().setStretchLastSection(True)
        self.spectrum_values.setMinimumHeight(120)
        self.spectrum_values.setToolTip("All requested q are retained. A dash means no estimate; inspect the reason column.")
        spectrum_split = QSplitter(Qt.Vertical)
        spectrum_split.addWidget(self.spectrum_preview)
        spectrum_split.addWidget(self.spectrum_values)
        spectrum_split.setStretchFactor(0, 4)
        spectrum_split.setStretchFactor(1, 1)
        spectrum_layout.addWidget(spectrum_split, 1)
        self.spectrum_export = QPushButton("Export selected curves (PNG / SVG)")
        self.spectrum_export.setEnabled(False)
        self.spectrum_export.clicked.connect(self.save_spectrum_chart)
        spectrum_layout.addWidget(self.spectrum_export)
        self.spectrum_domain.currentIndexChanged.connect(self.select_spectrum_domain)
        self.spectrum_center.currentIndexChanged.connect(self.select_spectrum_center)
        self.spectrum_size.currentIndexChanged.connect(self.select_spectrum_size)
        self.spectrum_estimator.currentIndexChanged.connect(self.render_selected_spectrum)
        gallery_page = QWidget()
        gallery = QVBoxLayout(gallery_page)
        self.result_tabs.addTab(gallery_page, "Figures")
        gallery.addWidget(QLabel("Select a figure. Click its preview to enlarge, zoom or pan."))
        self.figure_list = QListWidget()
        self.figure_list.setMaximumHeight(120)
        self.figure_list.currentTextChanged.connect(self.show_figure)
        gallery.addWidget(self.figure_list)
        self.preview = ImagePreview()
        gallery.addWidget(self.preview, 1)
        details_page = QWidget()
        details = QVBoxLayout(details_page)
        self.result_tabs.addTab(details_page, "Run details")
        open_folder = QPushButton("Open output folder")
        open_folder.clicked.connect(self.open_output)
        details.addWidget(open_folder)
        self.log = QTextBrowser()
        self.log.setMinimumHeight(100)
        details.addWidget(self.log, 1)
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

    def _tab(self, name, scrollable=True):
        page = QWidget()
        layout = QVBoxLayout(page)
        if not scrollable:
            self.tabs.addTab(page, name)
            return page, layout
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
            scaling_support=self.scaling_support.isChecked(),
            scaling_resolution_m=self.scaling_resolution.value(),
            scaling_scales_m=self._numbers(self.scaling_scales),
            scaling_null_replicates=self.scaling_null.value(),
            scaling_window_limit=self.scaling_limit.value(),
            renyi_order_policy=self.scaling_order_policy.currentData(),
            scaling_null_tail=self.scaling_null_tail.currentData(),
            scaling_coarse_trim_min_effective_q2=self.scaling_coarse_trim.value(),
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
            (self.scaling_resolution, config.scaling_resolution_m),
            (self.scaling_null, config.scaling_null_replicates),
            (self.scaling_limit, config.scaling_window_limit),
            (self.scaling_coarse_trim, config.scaling_coarse_trim_min_effective_q2),
        ):
            widget.setValue(value)
        for widget, values in (
            (self.divisors, config.divisors),
            (self.zeta_exponents, config.zeta_exponents),
            (self.window_sizes, config.window_sizes_m),
            (self.window_divisors, config.moving_divisors),
            (self.proximity, config.proximity_radii_m),
            (self.scaling_scales, config.scaling_scales_m),
        ):
            # Shortest round-trip representation: general :g formatting drops
            # scale precision and changes a loaded recipe before its next run.
            widget.setText(",".join(str(float(v)) for v in values))
            widget.setCursorPosition(0)
            widget.setToolTip(widget.text())
        for key, box in self.options.items():
            box.setChecked(getattr(config, key))
        self.moving.setChecked(config.moving)
        self.ensemble.setChecked(config.origin_ensemble)
        self.sensitivity.setChecked(config.zeta_sensitivity)
        self.scaling_support.setChecked(config.scaling_support)
        self.scaling_order_policy.setCurrentIndex(self.scaling_order_policy.findData(config.renyi_order_policy))
        self.scaling_null_tail.setCurrentIndex(self.scaling_null_tail.findData(config.scaling_null_tail))

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
        self.log.clear()
        for widget in self._spectrum_controls():
            widget.setEnabled(False)
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
            self.spectrum_open.setEnabled(True)
            self._spectrum_index = []
            self._spectrum_figure = None
            self.spectrum_preview.clear()
            self.spectrum_values.setRowCount(0)
            self.spectrum_note.setText("Failed/cancelled run: incomplete spectra are not loaded. Partial outputs remain on disk.")
            self.on_message(task.error or "Analysis cancelled. Partial outputs retained.")
            return
        manifest = task.manifest
        self.progress.setValue(100)
        self.on_message("Analysis complete")
        self.set_run_summary(self.last_output, manifest)
        self.show_run_details(self.last_output, manifest, self.log.toPlainText())
        self.figure_list.clear()
        self.figure_list.addItems([file.name for file in sorted(self.last_output.glob("*.png"))])
        if self.figure_list.count():
            self.figure_list.setCurrentRow(0)
        self.load_spectrum_index()
        if self.load_results:
            try:
                load_spatial_results(task.output)
            except Exception as exc:
                self.log.append(f"Analysis saved; layer loading failed: {exc}")
        self.tabs.setCurrentWidget(self.results_page)

    def set_run_summary(self, folder, manifest):
        prefix = f"Global fit: {manifest['accepted_q']} accepted q · {manifest['rejected_q']} rejected q" if "accepted_q" in manifest else "Completed run"
        self.summary.setText(f"{prefix}\n{Path(folder).name}")
        self.summary.setToolTip(str(folder))
        scaling_path = Path(folder) / "scaling_support.json"
        if scaling_path.is_file():
            from collections import Counter
            report = json.loads(Path(scaling_path).read_text(encoding="utf-8"))
            counts = Counter(row["status"] for support in report["supports"] for row in support["q_results"])
            self.summary.setText(self.summary.text() + "\nRenyi scaling (support/q): " +
                                 f"{counts['compatible_finite_range']} compatible · {counts['not_supported']} unsupported · "
                                 f"{counts['insufficient_information']} insufficient. Select a support below.")
            policies = sorted({support.get("renyi_order_policy", "legacy_block") for support in report["supports"]})
            warnings = sum(support.get("renyi_pair_order", {}).get("warning") is True
                           for support in report["supports"])
            self.summary.setText(self.summary.text() + "\nOrder policy: " + ", ".join(policies) +
                                 f". q=0,2 order warnings: {warnings}; these describe finite-range slopes.")

    def show_figure(self, filename):
        if self.last_output and filename:
            self.preview.load(self.last_output / filename)

    def show_run_details(self, folder, manifest, messages=""):
        lines = ["Saved analysis", f"Status: {manifest.get('status', 'unknown')}",
                 f"MUSA version: {manifest.get('software_version', 'unknown')}", f"Output folder: {folder}",
                 f"Started (UTC): {manifest.get('started_at_utc', 'not recorded')}",
                 f"Finished (UTC): {manifest.get('finished_at_utc', 'not recorded')}"]
        if "accepted_q" in manifest:
            lines.append(f"Global fit q: {manifest['accepted_q']} accepted, {manifest['rejected_q']} rejected")
        for title, data in (("Inputs and provenance", manifest.get('source', {})),
                            ("Analysis settings", manifest.get('recipe', {}).get('parameters', {})),
                            ("Output files", manifest.get('outputs', {}))):
            lines.extend(["", title, json.dumps(data, indent=2, ensure_ascii=False)])
        if messages:
            lines.extend(["", "Processing messages for this execution", messages])
        self.log.setPlainText("\n".join(lines))
        self.log.verticalScrollBar().setValue(0)

    def open_output(self):
        if self.last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output)))

    def _spectrum_controls(self):
        return (self.spectrum_domain, self.spectrum_center, self.spectrum_size, self.spectrum_estimator,
                self.spectrum_panel, self.spectrum_export, self.spectrum_open)

    def open_completed_run(self, folder):
        if self.task is not None:
            raise RuntimeError("Wait for the current analysis to finish.")
        folder = Path(folder)
        manifest = json.loads((folder / "run_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("status") != "complete":
            raise ValueError("Only completed runs can be opened in the spectrum viewer.")
        self.last_output = folder
        self.set_run_summary(folder, manifest)
        self.show_run_details(folder, manifest)
        self.figure_list.clear()
        self.preview.load(None)
        self.figure_list.addItems([file.name for file in sorted(folder.glob("*.png"))])
        if self.figure_list.count():
            self.figure_list.setCurrentRow(0)
        self.load_spectrum_index()
        self.tabs.setCurrentWidget(self.results_page)

    def browse_completed_run(self):
        folder = QFileDialog.getExistingDirectory(self, "Open a completed MUSA run", str(self.last_output or ""))
        if folder:
            try:
                self.open_completed_run(folder)
            except Exception as exc:
                QMessageBox.warning(self, "MUSA", str(exc))

    @staticmethod
    def _fill_spectrum_combo(combo, entries):
        blocked = combo.blockSignals(True)
        try:
            combo.clear()
            for label, value in entries:
                combo.addItem(label, value)
        finally:
            combo.blockSignals(blocked)

    def load_spectrum_index(self):
        from ._core.musa.spectrum_products import list_spectra
        self._spectrum_index = []
        self._spectrum_figure = None
        self._support_details = {}
        self.spectrum_panel.setEnabled(True)
        assessment = self.last_output / "scaling_support.json"
        if assessment.is_file():
            report = json.loads(assessment.read_text(encoding="utf-8"))
            self._support_details = {s["support_id"]: {"coverage": s.get("coverage"),
                "min_coverage": s.get("options", {}).get("min_coverage", .8)} for s in report["supports"]}
        self.spectrum_export.setEnabled(False)
        self.spectrum_open.setEnabled(True)
        path = self.last_output / "spectrum_curves.sqlite"
        if path.is_file():
            self._spectrum_index = list_spectra(path)
        domains = sorted({(s["source"], s["kind"]) for s in self._spectrum_index})
        entries = [(f"{'Global' if kind == 'global' else 'Moving windows'} — "
                    f"{'analysis' if source == 'analysis' else 'scaling assessment'}", (source, kind)) for source, kind in domains]
        self._fill_spectrum_combo(self.spectrum_domain, entries)
        self.spectrum_domain.setEnabled(bool(entries))
        self.select_spectrum_domain()

    def _domain_spectra(self):
        domain = self.spectrum_domain.currentData()
        return [s for s in self._spectrum_index if domain and (s["source"], s["kind"]) == tuple(domain)]

    def select_spectrum_domain(self):
        items = self._domain_spectra()
        centers = sorted({s["center_id"] for s in items if s["kind"] == "window"})
        counts = {center: max(s.get("summary", {}).get("valid_q_count", 0)
                             for s in items if s.get("center_id") == center) for center in centers}
        self._fill_spectrum_combo(self.spectrum_center, [(f"Center {center} · up to {counts[center]} usable q", center) for center in centers])
        if centers:
            blocked = self.spectrum_center.blockSignals(True)
            self.spectrum_center.setCurrentIndex(centers.index(max(centers, key=lambda c: counts[c])))
            self.spectrum_center.blockSignals(blocked)
        self.spectrum_center.setEnabled(bool(centers))
        self.select_spectrum_center()

    def select_spectrum_center(self):
        items = self._domain_spectra()
        sizes = sorted({s["window_m"] for s in items if s["kind"] == "window" and s["center_id"] == self.spectrum_center.currentData()})
        self._fill_spectrum_combo(self.spectrum_size, [(f"{size:g} m", size) for size in sizes])
        self.spectrum_size.setEnabled(bool(sizes))
        self.select_spectrum_size()

    def select_spectrum_size(self):
        items = self._selected_support_spectra()
        previous = self.spectrum_estimator.currentData()
        estimators = sorted({s["estimator"] for s in items})
        self._fill_spectrum_combo(self.spectrum_estimator,
                                  [("Canonical" if name == "canonical" else "Zeta weighted", name) for name in estimators])
        if previous in estimators:
            index = self.spectrum_estimator.findData(previous)
            self.spectrum_estimator.setCurrentIndex(index)
        self.spectrum_estimator.setEnabled(bool(estimators))
        self.render_selected_spectrum()

    def _selected_support_spectra(self):
        return [s for s in self._domain_spectra() if s["kind"] == "global" or
                (s["center_id"] == self.spectrum_center.currentData() and s["window_m"] == self.spectrum_size.currentData())]

    def render_selected_spectrum(self):
        from ._core.musa.spectrum_products import read_spectrum, spectrum_figure
        item = next((s for s in self._selected_support_spectra() if s["estimator"] == self.spectrum_estimator.currentData()), None)
        self.spectrum_export.setEnabled(False)
        if self._spectrum_figure is not None:
            self._spectrum_figure.clear()
            self._spectrum_figure = None
        self.spectrum_preview.clear()
        self.spectrum_values.setRowCount(0)
        if item is None:
            self.spectrum_note.setText("No indexed spectrum for this selection. Older runs remain available as files.")
            return
        try:
            spectrum = read_spectrum(self.last_output / "spectrum_curves.sqlite", item["series_id"])
            panel = self.spectrum_panel.currentData()
            self._spectrum_figure = spectrum_figure(spectrum, panel=panel)
            self.spectrum_preview.set_figure(self._spectrum_figure, lambda: spectrum_figure(spectrum, panel=panel))
            summary = spectrum["summary"]
            def value(number):
                return "unavailable" if number is None else f"{number:.5g}"
            observed = value(summary["observed_peak_alpha"])
            if summary["observed_peak_tied"]:
                observed = observed + " (multiple q)" if summary["observed_peak_alpha"] is not None else "ties: " + ", ".join(value(v) for v in summary["observed_peak_alphas"][:3])
            reasons = list(dict.fromkeys(self.friendly_reason(p['reason']) for p in spectrum['points'] if p['reason']))
            detail = self._support_details.get(spectrum['support_id'], {}) if spectrum['source'] == 'assessment' else {}
            coverage = detail.get('coverage')
            coverage_text = f" Coverage: {coverage:.1%} (minimum {detail['min_coverage']:.0%})." if coverage is not None else ""
            prefix = "No usable full-spectrum q." if not summary['valid_q_count'] else f"Usable full-spectrum q: {summary['valid_q_count']}/{summary['requested_q_count']}."
            self.spectrum_note.setText(
                f"{prefix}{coverage_text}\n"
                f"alpha(q=0): {value(summary['alpha_q0'])} · Observed peak: {observed} · Fitted peak: {value(summary['fit_peak_alpha'])}\n"
                + ("; ".join(reasons[:2]) if reasons else "See per-q diagnostics below. Click the chart to enlarge."))
            self.spectrum_note.setToolTip(
                f"q=0: {summary['alpha_q0_status']}; fitted peak: {summary['fit_status']}; "
                f"peak at q edge: {summary['observed_peak_at_q_edge']}; identities: {summary['identity_status']}. "
                "Peaks are descriptive; compatibility over finite scales is not proof of multifractality.")
            self.spectrum_values.setRowCount(len(spectrum['points']))
            for row, point in enumerate(spectrum['points']):
                status = point.get('statuses', {}).get('dq') or ('accepted' if point['accepted'] else 'not_supported')
                reason = self.friendly_reason(point['reason'])
                unsupported = [f"{name}: {state.replace('_', ' ')}" for name, state in point.get('statuses', {}).items()
                               if state not in ('compatible_finite_range', 'identity')]
                if unsupported:
                    reason = '; '.join(filter(None, [reason, ', '.join(unsupported)]))
                values = [f"{point['q']:g}", *["—" if point[n] is None else f"{point[n]:.6g}" for n in ('dq', 'tau', 'alpha', 'f_alpha')],
                          status.replace('_', ' '), 'usable' if point['accepted'] else 'not usable', reason]
                for col, text in enumerate(values):
                    cell = QTableWidgetItem(text)
                    cell.setToolTip(text)
                    self.spectrum_values.setItem(row, col, cell)
            self.spectrum_export.setEnabled(True)
        except Exception as exc:
            self.spectrum_note.setText(f"Could not display spectrum: {exc}")
            self.log.append(str(exc))

    @staticmethod
    def friendly_reason(reason):
        labels = {'low_coverage': 'Too little of this window lies inside the observed domain',
                  'insufficient_effective_boxes': 'Too few effective occupied boxes at this q',
                  'quadratic_predicts_better': 'A curved model predicts better than a straight scaling law',
                  'no_line_support': 'No observed line support in this window',
                  'no_resolved_scales': 'No scales remain above the observation resolution',
                  'accepted': 'Fit accepted; inspect scaling assessment separately'}
        return '; '.join(labels.get(part, part.replace('_', ' ')) for part in reason.split(';') if part)

    def export_selected_spectrum(self, path):
        if self._spectrum_figure is None or self.task is not None:
            raise ValueError("Select a completed spectrum first.")
        path = Path(path)
        if path.suffix.lower() not in (".png", ".svg"):
            raise ValueError("Choose a PNG or SVG filename.")
        self._spectrum_figure.savefig(path, dpi=160)

    def save_spectrum_chart(self):
        if self._spectrum_figure is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export selected spectrum", str(self.last_output / "selected_spectrum.png"),
                                             "PNG (*.png);;SVG (*.svg)")
        if path:
            try:
                self.export_selected_spectrum(path)
            except Exception as exc:
                QMessageBox.warning(self, "MUSA", str(exc))


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
    table_path = Path(output) / "scaling_support.csv"
    if table_path.is_file():
        uri = QUrl.fromLocalFile(str(table_path)).toString() + "?type=csv&geomType=none&detectTypes=yes"
        table = QgsVectorLayer(uri, "Renyi scaling support - diagnostics", "delimitedtext")
        if table.isValid():
            project.addMapLayer(table, False)
            group.addLayer(table)
            count += 1
    return count

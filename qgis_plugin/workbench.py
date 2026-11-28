"""Bilingual (English / Spanish) QGIS workbench: project inputs, recipes, background execution, results."""

from datetime import datetime
import json
from pathlib import Path
import uuid
import weakref

from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QColor, QDesktopServices, QIcon, QPixmap, QTextCursor, QTextDocument, QTextBlockFormat
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
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
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QPlainTextEdit,
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

from .i18n import UI_TEXTS, tr
from .inputs import make_analyzer, snapshot_sources, validate_metric_crs
from .native_gis import export_mother_layers
from .runtime import core, icon_path
from .chart_view import ChartView, ImagePreview, ScrollSafeComboBox, ScrollSafeDoubleSpinBox, ScrollSafeSpinBox
from .learning import TEXTS, comparison_text, default_language, learning_html, source_path, relocation_text, image_display_size


class AnalysisTask(QgsTask):
    message = pyqtSignal(str)

    def __init__(self, snapshot, config, output, receiver, language="en"):
        super().__init__(tr(language, "task_title"), QgsTask.CanCancel)
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
    widget = ScrollSafeDoubleSpinBox()
    widget.setRange(minimum, maximum)
    widget.setDecimals(decimals)
    widget.setValue(value)
    return widget


class ScaleListEdit(QPlainTextEdit):
    """Wrap a declared interval while retaining the numeric form's text API."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(78)

    def text(self):
        return self.toPlainText().replace('\n', ' ')

    def setText(self, text):
        self.setPlainText(text)

    def setCursorPosition(self, position):
        cursor = self.textCursor()
        cursor.setPosition(position)
        self.setTextCursor(cursor)


class LearningBrowser(QTextBrowser):
    """Keep the teaching diagram inside a resized dock's text column."""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_images()

    def fit_images(self):
        changes = []
        image_blocks = []
        block = self.document().begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():
                    block_format = block.blockFormat()
                    if block_format.lineHeight() != 100 or block_format.lineHeightType() != QTextBlockFormat.ProportionalHeight:
                        image_blocks.append(block.position())
                    fmt = fragment.charFormat().toImageFormat()
                    resource = self.document().resource(QTextDocument.ImageResource, QUrl(fmt.name()))
                    if resource is not None and hasattr(resource, "width") and resource.width() > 0:
                        width, height = image_display_size(self.viewport().width(), resource.width(),
                                                           resource.height(), self.document().documentMargin())
                        if abs(fmt.width() - width) > .01 or abs(fmt.height() - height) > .01:
                            fmt.setWidth(width)
                            fmt.setHeight(height)
                            changes.append((fragment.position(), fragment.length(), fmt))
                iterator += 1
            block = block.next()
        # Mutating image formats while walking QTextBlock iterators can leave
        # later text blocks with empty layout rectangles in Qt 5.15.
        if changes or image_blocks:
            cursor = QTextCursor(self.document())
            cursor.beginEditBlock()
            for position in image_blocks:
                cursor.setPosition(position)
                block_format = cursor.blockFormat()
                block_format.setLineHeight(100, QTextBlockFormat.ProportionalHeight)
                cursor.setBlockFormat(block_format)
            for position, length, fmt in changes:
                cursor.setPosition(position)
                cursor.setPosition(position + length, QTextCursor.KeepAnchor)
                cursor.setCharFormat(fmt)
            cursor.endEditBlock()
            self.document().markContentsDirty(0, self.document().characterCount())


class MusaDock(QDockWidget):
    def __init__(self, iface, on_language_changed=None):
        self.learning_language = default_language()
        super().__init__(tr(self.learning_language, "dock_title"), iface.mainWindow())
        self.iface, self.task, self.last_output = iface, None, None
        self._on_language_changed = on_language_changed
        self._i18n_labels = []
        self._i18n_groups = []
        self._i18n_placeholders = []
        self._i18n_tooltips = []
        self._status_state = ("key", "status_ready")
        self._last_manifest = None
        self._last_messages = ""
        self._failed_run = False
        defaults = core()[1]()
        self.setObjectName("MusaWorkbench")
        self.setMinimumWidth(380)
        self.setWindowIcon(QIcon(icon_path()))
        body = QWidget()
        layout = QVBoxLayout(body)
        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(icon_path()).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header.addWidget(logo)
        self.header_title = QLabel()
        self._bind_label(self.header_title, "header_title")
        header.addWidget(self.header_title, 1)
        self.lang_label = QLabel()
        self._bind_label(self.lang_label, "lang_label")
        header.addWidget(self.lang_label)
        self.learning_language_selector = QComboBox()
        self.learning_language_selector.addItem("English", "en")
        self.learning_language_selector.addItem("Español", "es")
        self.learning_language_selector.setCurrentIndex(self.learning_language_selector.findData(self.learning_language))
        header.addWidget(self.learning_language_selector)
        layout.addLayout(header)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self.analysis_page, form = self._tab("Analysis")
        self.lines = self._layer_combo(QgsMapLayerProxyModel.LineLayer)
        self.boundary = self._layer_combo(QgsMapLayerProxyModel.PolygonLayer)
        inputs = self._group(form, "grp_inputs")
        self._add_row(inputs, "lbl_lineaments", self.lines)
        self._add_row(inputs, "lbl_boundary", self.boundary)
        self.selected_only = self._checkbox("chk_selected_only")
        inputs.addRow(self.selected_only)
        self.crs = QgsProjectionSelectionWidget()
        self.crs.setCrs(QgsProject.instance().crs())
        self._add_row(inputs, "lbl_crs", self.crs)
        self.source_info = QLabel()
        self.source_info.setWordWrap(True)
        inputs.addRow(self.source_info)
        self.lines.layerChanged.connect(self.update_source)
        self.boundary.layerChanged.connect(self.update_source)
        self.crs.crsChanged.connect(self.update_source)

        scales = self._group(form, "grp_scales")
        self.mother = _spin(4000, 0.001)
        self.divisors = QLineEdit(",".join(str(v) for v in defaults.divisors))
        self._add_row(scales, "lbl_mother", self.mother)
        self._add_row(scales, "lbl_divisors", self.divisors)
        self.q_min, self.q_max, self.q_step = _spin(0, -100, 100), _spin(4, -100, 100), _spin(1, 0.001, 200)
        q_row = QHBoxLayout()
        for key, widget in (("lbl_min", self.q_min), ("lbl_max", self.q_max), ("lbl_step", self.q_step)):
            lbl = QLabel()
            self._bind_label(lbl, key)
            q_row.addWidget(lbl)
            q_row.addWidget(widget)
        self._add_row(scales, "lbl_q_range", q_row)
        self.negative_q_note = self._note("note_neg_q")
        self.negative_q_note.setVisible(False)
        self.q_min.valueChanged.connect(lambda value: self.negative_q_note.setVisible(value < 0))
        scales.addRow(self.negative_q_note)
        scales.addRow(self._note("note_box_sizes"))

        products = self._group(form, "grp_products")
        self.options = {}
        for key, label_key, checked in (
            ("local", "opt_local", True),
            ("structural", "opt_structural", True),
            ("network", "opt_network", False),
            ("plots", "opt_plots", True),
            ("gis", "opt_gis", True),
        ):
            box = self._checkbox(label_key, checked=checked)
            self.options[key] = box
            products.addRow(box)
        products.addRow(self._note("note_global_included"))

        output = self._group(form, "grp_output")
        self.output_root = QLineEdit()
        self._bind_placeholder(self.output_root, "ph_output_root")
        row = QHBoxLayout()
        row.addWidget(self.output_root, 1)
        browse = self._button("btn_browse", self.browse_output)
        row.addWidget(browse)
        output.addRow(row)
        self.add_layers = self._checkbox("chk_add_layers", checked=True)
        output.addRow(self.add_layers)
        recipes = QHBoxLayout()
        for key, callback in (("btn_load_recipe", self.load_recipe), ("btn_save_recipe", self.save_recipe)):
            recipes.addWidget(self._button(key, callback))
        form.addLayout(recipes)
        form.addStretch()

        self.quality_page, advanced = self._tab("Quality")
        quality = self._group(advanced, "grp_quality")
        self.min_r2 = _spin(0.9, 0, 0.999999, 6)
        self.threshold = _spin(0.01, 0, 1e9, 4)
        self.min_zeta = _spin(0.15, 0, 1, 4)
        self.zeta_floor = _spin(0.25, 0, 1, 4)
        self.zeta_exponents = QLineEdit("1,1,1,1")
        self.negative_floor = _spin(0, 0, 1, 6)
        self.bootstrap, self.local_bootstrap, self.seed = ScrollSafeSpinBox(), ScrollSafeSpinBox(), ScrollSafeSpinBox()
        for spin in (self.bootstrap, self.local_bootstrap):
            spin.setRange(0, 10000)
        self.seed.setRange(0, 2147483647)
        self.seed.setValue(42)
        self.confidence = _spin(0.95, 0.001, 0.999, 3)
        for key, widget in (
            ("lbl_min_r2", self.min_r2),
            ("lbl_threshold", self.threshold),
            ("lbl_min_zeta", self.min_zeta),
            ("lbl_zeta_floor", self.zeta_floor),
            ("lbl_zeta_exponents", self.zeta_exponents),
            ("lbl_neg_floor", self.negative_floor),
            ("lbl_boot_global", self.bootstrap),
            ("lbl_boot_local", self.local_bootstrap),
            ("lbl_confidence", self.confidence),
            ("lbl_seed", self.seed),
        ):
            self._add_row(quality, key, widget)
        self.sensitivity = self._checkbox("chk_sensitivity")
        quality.addRow(self.sensitivity)
        advanced.addWidget(self._note("note_quality"))

        scaling = self._group(advanced, "grp_scaling")
        self.scaling_support = self._checkbox("chk_scaling_support", checked=defaults.scaling_support)
        self.scaling_resolution = _spin(defaults.scaling_resolution_m, 0, 1e9, 4)
        self._bind_tooltip(self.scaling_resolution, "tt_scaling_resolution")
        self.scaling_scales = ScaleListEdit()
        self._bind_placeholder(self.scaling_scales, "ph_scaling_scales")
        self.scaling_null = ScrollSafeSpinBox()
        self.scaling_null.setRange(19, 9999)
        self.scaling_null.setValue(199)
        self.scaling_null.setEnabled(False)
        self.scaling_null_enabled = self._checkbox("chk_null_enabled")
        self._bind_tooltip(self.scaling_null_enabled, "tt_null")
        self._bind_tooltip(self.scaling_null, "tt_null")
        self.scaling_null_enabled.toggled.connect(self.scaling_null.setEnabled)
        self.scaling_limit = ScrollSafeSpinBox()
        self.scaling_limit.setRange(1, 1000)
        self.scaling_limit.setValue(25)
        self.scaling_order_policy = ScrollSafeComboBox()
        self.scaling_order_policy.addItem("", "legacy_block")
        self.scaling_order_policy.addItem("", "inform_q0_q2")
        self.scaling_null_tail = ScrollSafeComboBox()
        self.scaling_null_tail.addItem("", "upper")
        self.scaling_null_tail.addItem("", "two_sided")
        self.scaling_null_tail.setEnabled(False)
        self.scaling_null_enabled.toggled.connect(self.scaling_null_tail.setEnabled)
        self.scaling_coarse_trim = _spin(0, 0, 1e6, 2)
        scaling.addRow(self.scaling_support)
        self.classic_comparison = QCheckBox()
        scaling.addRow(self.classic_comparison)
        self._add_row(scaling, "lbl_resolution", self.scaling_resolution)
        self._add_row(scaling, "lbl_box_sizes", self.scaling_scales)
        self._add_row(scaling, "lbl_max_windows", self.scaling_limit)
        self._add_row(scaling, "lbl_order_policy", self.scaling_order_policy)
        self._add_row(scaling, "lbl_coarse_trim", self.scaling_coarse_trim)

        null_test = self._group(advanced, "grp_null")
        null_test.addRow(self.scaling_null_enabled)
        self._add_row(null_test, "lbl_null_replicates", self.scaling_null)
        self._add_row(null_test, "lbl_null_tail", self.scaling_null_tail)
        advanced.addWidget(self._note("note_scaling"))
        advanced.addStretch()

        self.moving_page, moving = self._tab("Moving windows")
        windows = self._group(moving, "grp_windows")
        self.moving = self._checkbox("chk_moving")
        windows.addRow(self.moving)
        self.window_sizes = QLineEdit("2000,4000,8000")
        self.window_step = _spin(1000, 0.001)
        self.window_divisors = QLineEdit("2,4,8,16")
        self.ensemble = self._checkbox("chk_ensemble")
        self.proximity = QLineEdit()
        self._bind_placeholder(self.proximity, "ph_proximity")
        for key, widget in (
            ("lbl_win_sizes", self.window_sizes),
            ("lbl_win_step", self.window_step),
            ("lbl_win_divisors", self.window_divisors),
            ("lbl_proximity", self.proximity),
        ):
            self._add_row(windows, key, widget)
        windows.addRow(self.ensemble)
        moving.addWidget(self._note("note_moving"))
        moving.addStretch()

        self.results_page, results = self._tab("Results")
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        results.addWidget(self.summary)
        self.comparison_summary = QLabel()
        self.comparison_summary.setWordWrap(True)
        self.comparison_summary.setVisible(False)
        results.addWidget(self.comparison_summary)
        self.spectrum_open = self._button("btn_open_run", self.browse_completed_run)
        results.addWidget(self.spectrum_open)
        self.result_tabs = QTabWidget()
        results.addWidget(self.result_tabs, 1)

        self.spectrum_page = QWidget()
        spectrum_layout = QVBoxLayout(self.spectrum_page)
        self.result_tabs.addTab(self.spectrum_page, "Spectra")
        spectra = self._group(spectrum_layout, "grp_choose_domain")
        self.spectrum_domain, self.spectrum_center, self.spectrum_size, self.spectrum_estimator = (ScrollSafeComboBox() for _ in range(4))
        for combo in (self.spectrum_domain, self.spectrum_center, self.spectrum_size, self.spectrum_estimator):
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(12)
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._spectrum_index = []
        self._spectrum_figure = None
        for key, combo in (("lbl_domain", self.spectrum_domain), ("lbl_win_center", self.spectrum_center),
                           ("lbl_win_size", self.spectrum_size), ("lbl_estimator", self.spectrum_estimator)):
            self._add_row(spectra, key, combo)
        self.spectrum_note = QLabel()
        self.spectrum_note.setWordWrap(True)
        self.spectrum_note.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        spectra.addRow(self.spectrum_note)
        self.spectrum_panel = ScrollSafeComboBox()
        self.spectrum_panel.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.spectrum_panel.setMinimumContentsLength(12)
        for name in ("f_alpha", "dq", "tau", "alpha", "all"):
            self.spectrum_panel.addItem("", name)
        self._add_row(spectra, "lbl_chart", self.spectrum_panel)
        self.spectrum_panel.currentIndexChanged.connect(self.render_selected_spectrum)
        self.spectrum_preview = ChartView(language=self.learning_language)
        self.spectrum_values = QTableWidget(0, 8)
        self.spectrum_values.setEditTriggers(QTableWidget.NoEditTriggers)
        self.spectrum_values.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.spectrum_values.horizontalHeader().setStretchLastSection(True)
        self.spectrum_values.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.spectrum_values.setMinimumHeight(120)
        self._bind_tooltip(self.spectrum_values, "tt_table")
        spectrum_split = QSplitter(Qt.Vertical)
        spectrum_split.addWidget(self.spectrum_preview)
        spectrum_split.addWidget(self.spectrum_values)
        spectrum_split.setStretchFactor(0, 4)
        spectrum_split.setStretchFactor(1, 1)
        spectrum_layout.addWidget(spectrum_split, 1)
        self.spectrum_export = self._button("btn_export_spectrum", self.save_spectrum_chart)
        self.spectrum_export.setEnabled(False)
        spectrum_layout.addWidget(self.spectrum_export)
        self.spectrum_domain.currentIndexChanged.connect(self.select_spectrum_domain)
        self.spectrum_center.currentIndexChanged.connect(self.select_spectrum_center)
        self.spectrum_size.currentIndexChanged.connect(self.select_spectrum_size)
        self.spectrum_estimator.currentIndexChanged.connect(self.render_selected_spectrum)

        self.gallery_page = QWidget()
        gallery = QVBoxLayout(self.gallery_page)
        self.result_tabs.addTab(self.gallery_page, "Figures")
        gallery.addWidget(self._note("note_figures"))
        self.figure_list = QListWidget()
        self.figure_list.setMaximumHeight(120)
        self.figure_list.currentTextChanged.connect(self.show_figure)
        gallery.addWidget(self.figure_list)
        self.preview = ImagePreview(language=self.learning_language)
        gallery.addWidget(self.preview, 1)

        self.details_page = QWidget()
        details = QVBoxLayout(self.details_page)
        self.result_tabs.addTab(self.details_page, "Run details")
        details.addWidget(self._button("btn_open_folder", self.open_output))
        self.log = QTextBrowser()
        self.log.setMinimumHeight(100)
        details.addWidget(self.log, 1)

        self.learning_page, learning = self._tab(TEXTS[self.learning_language]["learn"], scrollable=False)
        self.learning_reader = LearningBrowser()
        self.learning_reader.setOpenExternalLinks(True)
        learning.addWidget(self.learning_reader, 1)

        buttons = QHBoxLayout()
        self.run_button = self._button("btn_run", self.start_run)
        self.cancel_button = self._button("btn_cancel", self.cancel_run)
        self.cancel_button.setEnabled(False)
        buttons.addWidget(self.run_button, 1)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.setWidget(body)

        self.learning_language_selector.currentIndexChanged.connect(self.update_learning_language)
        self.update_learning_language()

        active = iface.activeLayer()
        if isinstance(active, QgsVectorLayer) and active.geometryType() == 1:
            self.lines.setLayer(active)
            try:
                validate_metric_crs(active.crs(), language=self.learning_language)
                self.crs.setCrs(active.crs())
            except ValueError:
                pass
        self.update_source()

    def _t(self, key):
        return tr(self.learning_language, key)

    def _bind_label(self, widget, key):
        self._i18n_labels.append((widget, key))
        return widget

    def _bind_placeholder(self, widget, key):
        self._i18n_placeholders.append((widget, key))
        return widget

    def _bind_tooltip(self, widget, key):
        self._i18n_tooltips.append((widget, key))
        return widget

    def _checkbox(self, key, checked=False):
        box = QCheckBox()
        box.setChecked(checked)
        return self._bind_label(box, key)

    def _button(self, key, callback):
        btn = QPushButton()
        btn.clicked.connect(callback)
        return self._bind_label(btn, key)

    def _note(self, key):
        lbl = QLabel()
        lbl.setWordWrap(True)
        return self._bind_label(lbl, key)

    def _add_row(self, form, key, field):
        lbl = QLabel()
        self._bind_label(lbl, key)
        form.addRow(lbl, field)

    def _set_status_key(self, key):
        self._status_state = ("key", key)
        self.status.setText(self._t(key))

    def _set_status_raw(self, message):
        self._status_state = ("raw", message)
        self.status.setText(message)

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

    def update_learning_language(self):
        self.learning_language = self.learning_language_selector.currentData() or "en"
        lang = self.learning_language
        text = TEXTS[lang]
        ui = UI_TEXTS[lang]

        self.setWindowTitle(ui["dock_title"])
        for widget, key in self._i18n_labels:
            widget.setText(ui[key])
        for group, key in self._i18n_groups:
            group.setTitle(ui[key])
        for widget, key in self._i18n_placeholders:
            widget.setPlaceholderText(ui[key])
        for widget, key in self._i18n_tooltips:
            widget.setToolTip(ui[key])

        for page, key in (
            (self.analysis_page, "tab_analysis"),
            (self.quality_page, "tab_quality"),
            (self.moving_page, "tab_moving"),
            (self.results_page, "tab_results"),
        ):
            self.tabs.setTabText(self.tabs.indexOf(page), ui[key])
        self.tabs.setTabText(self.tabs.indexOf(self.learning_page), text["learn"])
        for page, key in (
            (self.spectrum_page, "subtab_spectra"),
            (self.gallery_page, "subtab_figures"),
            (self.details_page, "subtab_details"),
        ):
            self.result_tabs.setTabText(self.result_tabs.indexOf(page), ui[key])

        self.scaling_order_policy.setItemText(0, ui["policy_legacy_block"])
        self.scaling_order_policy.setItemText(1, ui["policy_inform_q0_q2"])
        self.scaling_null_tail.setItemText(0, ui["tail_upper"])
        self.scaling_null_tail.setItemText(1, ui["tail_two_sided"])
        for idx, panel_key in enumerate(("panel_f_alpha", "panel_dq", "panel_tau", "panel_alpha", "panel_all")):
            self.spectrum_panel.setItemText(idx, ui[panel_key])
        self.spectrum_values.setHorizontalHeaderLabels(ui["tbl_headers"])

        self.spectrum_preview.set_language(lang)
        self.preview.set_language(lang)
        self.learning_language_selector.setToolTip(text["language"])
        path = source_path(lang)
        self.learning_reader.document().setBaseUrl(QUrl.fromLocalFile(str(path.parent) + "/"))
        self.learning_reader.setSearchPaths([str(path.parent)])
        self.learning_reader.setHtml(learning_html(path.read_text(encoding="utf-8")))
        self.learning_reader.fit_images()
        self.classic_comparison.setText(text["classic"])
        self.classic_comparison.setToolTip(text["warning"])

        if self._status_state[0] == "key":
            self.status.setText(ui[self._status_state[1]])
        self.update_source()

        if self.last_output is not None and self._last_manifest is not None:
            self.set_run_summary(self.last_output, self._last_manifest)
            self.show_run_details(self.last_output, self._last_manifest, self._last_messages)
            prev_domain = self.spectrum_domain.currentData()
            prev_center = self.spectrum_center.currentData()
            prev_size = self.spectrum_size.currentData()
            prev_est = self.spectrum_estimator.currentData()
            self.load_spectrum_index()
            if prev_domain is not None and self.spectrum_domain.findData(prev_domain) >= 0:
                self.spectrum_domain.setCurrentIndex(self.spectrum_domain.findData(prev_domain))
            if prev_center is not None and self.spectrum_center.findData(prev_center) >= 0:
                self.spectrum_center.setCurrentIndex(self.spectrum_center.findData(prev_center))
            if prev_size is not None and self.spectrum_size.findData(prev_size) >= 0:
                self.spectrum_size.setCurrentIndex(self.spectrum_size.findData(prev_size))
            if prev_est is not None and self.spectrum_estimator.findData(prev_est) >= 0:
                self.spectrum_estimator.setCurrentIndex(self.spectrum_estimator.findData(prev_est))
        elif self._failed_run:
            self.summary.setText(ui["summary_none"])
            self.spectrum_note.setText(ui["failed_spectrum_note"])
            self.update_comparison_summary()
        else:
            self.summary.setText(ui["summary_none"])
            self.spectrum_note.setText(ui["spectrum_none"])
            self.update_comparison_summary()

        if self._on_language_changed is not None:
            self._on_language_changed(lang)

    def update_comparison_summary(self, folder=None):
        folder = folder or self.last_output
        text = comparison_text(folder, self.learning_language) if folder else ""
        self.comparison_summary.setText(text)
        self.comparison_summary.setVisible(bool(text))

    def _group(self, layout, key):
        group = QGroupBox()
        self._i18n_groups.append((group, key))
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
            validate_metric_crs(self.crs.crs(), language=self.learning_language)
            self.source_info.setText(
                self._t("source_summary").format(
                    crs=self.crs.crs().authid() or self._t("custom_metric_crs"),
                    lines=line.featureCount() if line else 0,
                    boundaries=boundary.featureCount() if boundary else 0,
                )
            )
        except ValueError as exc:
            self.source_info.setText(str(exc))

    @staticmethod
    def _numbers(widget):
        return tuple(float(value.strip()) for value in widget.text().split(",") if value.strip())

    def config(self):
        _, RunConfig, _ = core()
        if self.scaling_support.isChecked() and (
            not self.scaling_resolution.cleanText().strip() or self.scaling_resolution.value() <= 0
        ):
            raise ValueError(self._t("err_missing_resolution"))
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
            classic_comparison=self.classic_comparison.isChecked(),
            scaling_resolution_m=self.scaling_resolution.value(),
            scaling_scales_m=self._numbers(self.scaling_scales),
            scaling_null_replicates=self.scaling_null.value() if self.scaling_null_enabled.isChecked() else 0,
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
            (self.scaling_null, config.scaling_null_replicates or 199),
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
        self.classic_comparison.setChecked(config.classic_comparison)
        self.scaling_null_enabled.setChecked(config.scaling_null_replicates > 0)
        self.scaling_order_policy.setCurrentIndex(self.scaling_order_policy.findData(config.renyi_order_policy))
        self.scaling_null_tail.setCurrentIndex(self.scaling_null_tail.findData(config.scaling_null_tail))

    def browse_output(self):
        path = QFileDialog.getExistingDirectory(self, self._t("dlg_output_parent"), self.output_root.text())
        if path:
            self.output_root.setText(path)

    def save_recipe(self):
        try:
            recipe = self.config().recipe()
            path, _ = QFileDialog.getSaveFileName(self, self._t("dlg_save_recipe"), "musa_recipe.json", "JSON (*.json)")
            if path:
                Path(path).write_text(json.dumps(recipe, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "MUSA", str(exc))

    def load_recipe(self):
        path, _ = QFileDialog.getOpenFileName(self, self._t("dlg_load_recipe"), "", "JSON (*.json)")
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
        missing_res = self.scaling_support.isChecked() and (
            not self.scaling_resolution.cleanText().strip() or self.scaling_resolution.value() <= 0
        )
        try:
            config = self.config()
            parent = Path(self.output_root.text())
            if not self.output_root.text().strip() or not parent.is_dir():
                raise ValueError(self._t("err_missing_output"))
            snapshot = snapshot_sources(
                self.lines.currentLayer(),
                self.boundary.currentLayer(),
                self.crs.crs(),
                selected_only=self.selected_only.isChecked(),
                language=self.learning_language,
            )
            output = parent / ("MUSA_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8])
            self.start_snapshot(snapshot, config, output)
        except Exception as exc:
            self._set_status_raw(str(exc))
            self.log.append(str(exc))
            if missing_res:
                self.tabs.setCurrentWidget(self.quality_page)
                self.scaling_resolution.setFocus()
                self.scaling_resolution.selectAll()

    def start_snapshot(self, snapshot, config, output):
        if self.task is not None:
            raise RuntimeError(self._t("err_already_running"))
        self.log.clear()
        self._last_messages = ""
        for widget in self._spectrum_controls():
            widget.setEnabled(False)
        self.task = AnalysisTask(snapshot, config, str(output), self, language=self.learning_language)
        self.task.progressChanged.connect(self.update_progress)
        self.task.message.connect(self.on_message)
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setValue(0)
        self._set_status_key("status_running")
        self.load_results = self.add_layers.isChecked()
        QgsApplication.taskManager().addTask(self.task)

    def on_message(self, message):
        self._set_status_raw(message)
        self.log.append(message)

    def update_progress(self, value):
        self.progress.setValue(int(value))

    def cancel_run(self):
        if self.task is not None:
            self.task.cancel()
            self._set_status_key("status_cancelling")

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
            self._failed_run = True
            self._last_manifest = None
            self.spectrum_open.setEnabled(True)
            self._spectrum_index = []
            self._spectrum_figure = None
            self.spectrum_preview.clear()
            self.spectrum_values.setRowCount(0)
            self.spectrum_note.setText(self._t("failed_spectrum_note"))
            if task.error:
                self.on_message(task.error)
            else:
                self._set_status_key("status_cancelled")
                self.log.append(self.status.text())
            return
        self._failed_run = False
        manifest = task.manifest
        self._last_manifest = manifest
        self.progress.setValue(100)
        self._set_status_key("status_complete")
        self.log.append(self.status.text())
        self._last_messages = self.log.toPlainText()
        self.set_run_summary(self.last_output, manifest)
        self.show_run_details(self.last_output, manifest, self._last_messages)
        self.figure_list.clear()
        self.figure_list.addItems([file.name for file in sorted(self.last_output.glob("*.png"))])
        if self.figure_list.count():
            self.figure_list.setCurrentRow(0)
        self.load_spectrum_index()
        if self.load_results:
            try:
                load_spatial_results(task.output, language=self.learning_language)
            except Exception as exc:
                self.log.append(self._t("err_layer_load").format(exc=exc))
        self.tabs.setCurrentWidget(self.results_page)

    def set_run_summary(self, folder, manifest):
        self._last_manifest = manifest
        self._failed_run = False
        self.update_comparison_summary(folder)
        prefix = (
            self._t("summary_global_fit").format(accepted=manifest["accepted_q"], rejected=manifest["rejected_q"])
            if "accepted_q" in manifest
            else self._t("summary_completed_run")
        )
        self.summary.setText(f"{prefix}\n{Path(folder).name}")
        self.summary.setToolTip(str(folder))
        scaling_path = Path(folder) / "scaling_support.json"
        if scaling_path.is_file():
            from collections import Counter
            report = json.loads(Path(scaling_path).read_text(encoding="utf-8"))
            counts = Counter(row["status"] for support in report["supports"] for row in support["q_results"])
            self.summary.setText(
                self.summary.text()
                + self._t("summary_renyi").format(
                    comp=counts["compatible_finite_range"],
                    unsup=counts["not_supported"],
                    insuf=counts["insufficient_information"],
                )
            )
            policies = sorted({support.get("renyi_order_policy", "legacy_block") for support in report["supports"]})
            policy_map = {
                "legacy_block": self._t("policy_legacy_block"),
                "inform_q0_q2": self._t("policy_inform_q0_q2"),
            }
            warnings = sum(support.get("renyi_pair_order", {}).get("warning") is True
                           for support in report["supports"])
            self.summary.setText(
                self.summary.text()
                + self._t("summary_policy").format(
                    policies=", ".join(policy_map[p] for p in policies),
                    warnings=warnings,
                )
            )
            global_support = next((support for support in report['supports'] if support['support_id'] == 'global'), None)
            null_text = relocation_text(global_support.get('null', {}), language=self.learning_language) if global_support else ''
            if null_text:
                self.summary.setText(self.summary.text() + '\n' + null_text)

    def show_figure(self, filename):
        if self.last_output and filename:
            self.preview.load(self.last_output / filename)

    def show_run_details(self, folder, manifest, messages=""):
        self._last_messages = messages
        lines = [
            self._t("details_saved"),
            self._t("details_status").format(status=manifest.get("status", self._t("details_unknown"))),
            self._t("details_version").format(version=manifest.get("software_version", self._t("details_unknown"))),
            self._t("details_folder").format(folder=folder),
            self._t("details_started").format(started=manifest.get("started_at_utc", self._t("details_not_recorded"))),
            self._t("details_finished").format(finished=manifest.get("finished_at_utc", self._t("details_not_recorded"))),
        ]
        if "accepted_q" in manifest:
            lines.append(self._t("details_global_q").format(accepted=manifest["accepted_q"], rejected=manifest["rejected_q"]))
        for title, data in (
            (self._t("details_inputs"), manifest.get('source', {})),
            (self._t("details_settings"), manifest.get('recipe', {}).get('parameters', {})),
            (self._t("details_outputs"), manifest.get('outputs', {})),
        ):
            lines.extend(["", title, json.dumps(data, indent=2, ensure_ascii=False)])
        if messages:
            lines.extend(["", self._t("details_messages"), messages])
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
            raise RuntimeError(self._t("err_wait_finish"))
        folder = Path(folder)
        manifest = json.loads((folder / "run_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("status") != "complete":
            raise ValueError(self._t("err_only_completed"))
        self.last_output = folder
        self._last_messages = ""
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
        folder = QFileDialog.getExistingDirectory(self, self._t("dlg_open_run"), str(self.last_output or ""))
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
        domains = sorted({(s["source"], s["kind"]) for s in self._spectrum_index},
                         key=lambda item: (item[0] != "assessment", item[1] != "global", item))
        entries = [(f"{self._t('dom_global' if kind == 'global' else 'dom_moving')} — "
                    f"{self._t('src_analysis' if source == 'analysis' else 'src_assessment')}", (source, kind))
                   for source, kind in domains]
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
        self._fill_spectrum_combo(
            self.spectrum_center,
            [(self._t("center_item").format(center=center, count=counts[center]), center) for center in centers],
        )
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
        self._fill_spectrum_combo(
            self.spectrum_estimator,
            [(self._t("est_standard" if name == "canonical" else "est_weighted"), name) for name in estimators],
        )
        if previous in estimators:
            blocked = self.spectrum_estimator.blockSignals(True)
            try:
                index = self.spectrum_estimator.findData(previous)
                self.spectrum_estimator.setCurrentIndex(index)
            finally:
                self.spectrum_estimator.blockSignals(blocked)
        self.spectrum_estimator.setEnabled(bool(estimators))
        self.render_selected_spectrum()

    def _selected_support_spectra(self):
        return [s for s in self._domain_spectra() if s["kind"] == "global" or
                (s["center_id"] == self.spectrum_center.currentData() and s["window_m"] == self.spectrum_size.currentData())]

    def render_selected_spectrum(self):
        from ._core.musa.spectrum_products import read_spectrum, spectrum_figure, spectrum_shape_reasons
        item = next((s for s in self._selected_support_spectra() if s["estimator"] == self.spectrum_estimator.currentData()), None)
        self.spectrum_export.setEnabled(False)
        if self._spectrum_figure is not None:
            self._spectrum_figure.clear()
            self._spectrum_figure = None
        self.spectrum_preview.clear()
        self.spectrum_values.setRowCount(0)
        if item is None:
            self.spectrum_note.setText(self._t("no_indexed_selection"))
            return
        lang = self.learning_language
        try:
            spectrum = read_spectrum(self.last_output / "spectrum_curves.sqlite", item["series_id"])
            panel = self.spectrum_panel.currentData()
            self._spectrum_figure = spectrum_figure(spectrum, panel=panel, language=lang)
            self.spectrum_preview.set_figure(
                self._spectrum_figure,
                lambda: spectrum_figure(spectrum, panel=panel, language=lang),
            )
            summary = spectrum["summary"]
            def value(number):
                return "—" if number is None else f"{number:.5g}"
            observed = value(summary["observed_peak_alpha"])
            if summary["observed_peak_tied"]:
                observed = (
                    observed + self._t("ties_multiple_q")
                    if summary["observed_peak_alpha"] is not None
                    else self._t("ties_prefix") + ", ".join(value(v) for v in summary["observed_peak_alphas"][:3])
                )
            detail = self._support_details.get(spectrum['support_id'], {}) if spectrum['source'] == 'assessment' else {}
            coverage = detail.get('coverage')
            coverage_text = (
                self._t("coverage_fmt").format(cov=coverage, min_cov=detail["min_coverage"])
                if coverage is not None
                else ""
            )
            prefix = (
                self._t("no_joint_q")
                if not summary["valid_q_count"]
                else self._t("per_q_avail").format(valid=summary["valid_q_count"], total=summary["requested_q_count"])
            )
            shape_reasons = spectrum_shape_reasons(spectrum, language=lang)
            shape_note = (self._t("joint_withheld") + ' '.join(shape_reasons) + '\n') if shape_reasons else ''
            self.spectrum_note.setText(
                self._t("spectrum_note_body").format(
                    prefix=prefix,
                    coverage=coverage_text,
                    a0=value(summary["alpha_q0"]),
                    obs=observed,
                    fit=value(summary["fit_peak_alpha"]),
                    shape=shape_note,
                )
            )
            self.spectrum_note.setToolTip(self._t("tt_spectrum_note"))
            self.spectrum_values.setRowCount(len(spectrum['points']))
            for row, point in enumerate(spectrum['points']):
                status = point.get('statuses', {}).get('dq') or ('accepted' if point['accepted'] else 'not_supported')
                reason = self.friendly_reason(point['reason'], language=lang)
                unsupported = [
                    f"{name}: {self.friendly_status(state, language=lang)}"
                    for name, state in point.get('statuses', {}).items()
                    if state not in ('compatible_finite_range', 'identity')
                ]
                if unsupported:
                    reason = '; '.join(filter(None, [reason, ', '.join(unsupported)]))
                values = [
                    f"{point['q']:g}",
                    *["—" if point[n] is None else f"{point[n]:.6g}" for n in ('dq', 'tau', 'alpha', 'f_alpha')],
                    self.friendly_status(status, language=lang),
                    self._t("val_available" if point['accepted'] else "val_unavailable"),
                    reason,
                ]
                for col, text in enumerate(values):
                    cell = QTableWidgetItem(text)
                    cell.setToolTip(text)
                    self.spectrum_values.setItem(row, col, cell)
            self.spectrum_values.resizeRowsToContents()
            self.spectrum_export.setEnabled(True)
        except Exception as exc:
            self.spectrum_note.setText(self._t("err_display_spectrum").format(exc=exc))
            self.log.append(str(exc))

    @staticmethod
    def friendly_status(status, language="en"):
        ui = UI_TEXTS.get(language, UI_TEXTS["en"])
        return ui["statuses"].get(status, ui["status_fallback"])

    @staticmethod
    def friendly_reason(reason, language="en"):
        ui = UI_TEXTS.get(language, UI_TEXTS["en"])
        labels = ui["reasons"]
        fallback = ui["reason_fallback"]
        return '; '.join(labels.get(part, fallback) for part in reason.split(';') if part)

    def export_selected_spectrum(self, path):
        if self._spectrum_figure is None or self.task is not None:
            raise ValueError(self._t("err_select_spectrum"))
        path = Path(path)
        if path.suffix.lower() not in (".png", ".svg"):
            raise ValueError(self._t("err_png_svg"))
        self._spectrum_figure.savefig(path, dpi=160)

    def save_spectrum_chart(self):
        if self._spectrum_figure is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, self._t("dlg_export_spectrum"), str(self.last_output / "selected_spectrum.png"),
                                             "PNG (*.png);;SVG (*.svg)")
        if path:
            try:
                self.export_selected_spectrum(path)
            except Exception as exc:
                QMessageBox.warning(self, "MUSA", str(exc))


def load_spatial_results(output, language="en"):
    """Main-thread only. Group each run and keep density/reliability separate."""
    from osgeo import ogr
    import math

    ui = UI_TEXTS.get(language, UI_TEXTS["en"])
    layer_names = ui["layer_names"]
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
            title = layer_names.get(name) or name.replace("_", " ").title()
            layer = QgsVectorLayer(f"{path}|layername={name}", title, "ogr")
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
        table = QgsVectorLayer(uri, ui["layer_scaling_diag"], "delimitedtext")
        if table.isValid():
            project.addMapLayer(table, False)
            group.addLayer(table)
            count += 1
    return count

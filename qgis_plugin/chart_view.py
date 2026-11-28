"""Responsive figures and enlarged views owned by the QGIS workbench."""
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QPainter, QPixmap
from qgis.PyQt.QtWidgets import (
    QApplication, QComboBox, QDialog, QDoubleSpinBox, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT

from .i18n import tr


def _dialog(parent, title):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.resize(1100, 820)
    dialog.setModal(False)
    return dialog


def _scroll_page(widget, event):
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QScrollArea):
            QApplication.sendEvent(parent.viewport(), event)
            return
        parent = parent.parentWidget()
    event.ignore()


class ClickCanvas(FigureCanvasQTAgg):
    clicked = pyqtSignal()

    def wheelEvent(self, event):
        # Inline charts must let the containing Results page scroll.
        _scroll_page(self, event)

    def mousePressEvent(self, event):
        self._press = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and (event.pos() - getattr(self, '_press', event.pos())).manhattanLength() < 5:
            self.clicked.emit()


class ScrollSafeComboBox(QComboBox):
    def wheelEvent(self, event):
        # The open popup still scrolls normally; hovering must not change data.
        _scroll_page(self, event)


class ScrollSafeDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            _scroll_page(self, event)


class ScrollSafeSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            _scroll_page(self, event)


class ChartView(QWidget):
    def __init__(self, parent=None, language="en"):
        super().__init__(parent)
        self.language = language
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = None
        self.factory = None
        self.dialogs = []
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_language(self, language):
        self.language = language
        if self.canvas is not None:
            self.canvas.setToolTip(tr(self.language, 'tt_chart_enlarge'))

    def clear(self):
        if self.canvas is not None:
            self.layout.removeWidget(self.canvas)
            self.canvas.figure.clear()
            self.canvas.deleteLater()
            self.canvas = None
        self.factory = None

    def set_figure(self, figure, factory):
        self.clear()
        self.factory = factory
        self.canvas = ClickCanvas(figure)
        self.canvas.setCursor(Qt.PointingHandCursor)
        self.canvas.setToolTip(tr(self.language, 'tt_chart_enlarge'))
        self.canvas.clicked.connect(self.open_enlarged)
        self.layout.addWidget(self.canvas)
        self.canvas.draw_idle()

    def open_enlarged(self):
        if self.factory is None:
            return
        dialog = _dialog(self, tr(self.language, 'dlg_enlarged_spectrum'))
        layout = QVBoxLayout(dialog)
        figure = self.factory()
        canvas = FigureCanvasQTAgg(figure)
        layout.addWidget(NavigationToolbar2QT(canvas, dialog))
        layout.addWidget(canvas, 1)
        self.dialogs.append(dialog)

        def _cleanup(_):
            figure.clear()
            if dialog in self.dialogs:
                self.dialogs.remove(dialog)

        dialog.finished.connect(_cleanup)
        dialog.show()
        canvas.draw_idle()
        return dialog


class ImagePreview(QLabel):
    """Fit the original image on every resize; clicking opens a zoomable original."""
    def __init__(self, parent=None, language="en"):
        self.language = language
        self._loaded_once = False
        super().__init__(tr(language, 'img_select_prompt'), parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.original = QPixmap()
        self.dialogs = []

    def set_language(self, language):
        self.language = language
        if not self.original.isNull():
            self.setToolTip(tr(self.language, 'tt_img_enlarge'))
        else:
            self.setToolTip('')
            self.setText(tr(self.language, 'img_none' if self._loaded_once else 'img_select_prompt'))

    def load(self, path):
        self._loaded_once = True
        self.original = QPixmap(str(path)) if path else QPixmap()
        self.setToolTip(tr(self.language, 'tt_img_enlarge') if not self.original.isNull() else '')
        self._fit()

    def _fit(self):
        if self.original.isNull():
            self.setCursor(Qt.ArrowCursor)
            self.clear()
            self.setText(tr(self.language, 'img_none' if self._loaded_once else 'img_select_prompt'))
        else:
            self.setCursor(Qt.PointingHandCursor)
            self.setPixmap(self.original.scaled(self.contentsRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def mousePressEvent(self, event):
        self._press = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and (event.pos() - getattr(self, '_press', event.pos())).manhattanLength() < 5:
            self.open_enlarged()
        super().mouseReleaseEvent(event)

    def open_enlarged(self):
        if self.original.isNull():
            return
        dialog = _dialog(self, tr(self.language, 'dlg_enlarged_figure'))
        layout = QVBoxLayout(dialog)
        scene = QGraphicsScene(dialog)
        scene.addPixmap(self.original)
        view = QGraphicsView(scene)
        view.setRenderHint(QPainter.SmoothPixmapTransform)
        view.setDragMode(QGraphicsView.ScrollHandDrag)
        controls = QHBoxLayout()
        for key, callback in (
            ('btn_zoom_in', lambda: view.scale(1.25, 1.25)),
            ('btn_zoom_out', lambda: view.scale(.8, .8)),
            ('btn_fit', lambda: view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)),
            ('btn_actual_px', view.resetTransform),
        ):
            button = QPushButton(tr(self.language, key))
            button.clicked.connect(lambda checked=False, callback=callback: callback())
            controls.addWidget(button)
        layout.addLayout(controls)
        layout.addWidget(view, 1)
        self.dialogs.append(dialog)
        dialog.finished.connect(lambda _: self.dialogs.remove(dialog) if dialog in self.dialogs else None)
        dialog.show()
        view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
        return dialog

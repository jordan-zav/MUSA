"""Responsive figures and enlarged views owned by the QGIS workbench."""
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QPainter, QPixmap
from qgis.PyQt.QtWidgets import (
    QApplication, QComboBox, QDialog, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT


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


class ChartView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = None
        self.factory = None
        self.dialogs = []
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        self.canvas.setToolTip('Click to enlarge; zoom, pan and export in the enlarged view.')
        self.canvas.clicked.connect(self.open_enlarged)
        self.layout.addWidget(self.canvas)
        self.canvas.draw_idle()

    def open_enlarged(self):
        if self.factory is None:
            return
        dialog = _dialog(self, 'MUSA — enlarged spectrum')
        layout = QVBoxLayout(dialog)
        canvas = FigureCanvasQTAgg(self.factory())
        layout.addWidget(NavigationToolbar2QT(canvas, dialog))
        layout.addWidget(canvas, 1)
        self.dialogs.append(dialog)
        dialog.finished.connect(lambda _: self.dialogs.remove(dialog))
        dialog.show()
        canvas.draw_idle()
        return dialog


class ImagePreview(QLabel):
    """Fit the original image on every resize; clicking opens a zoomable original."""
    def __init__(self, parent=None):
        super().__init__('Select a figure to preview.', parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.original = QPixmap()
        self.dialogs = []

    def load(self, path):
        self.original = QPixmap(str(path)) if path else QPixmap()
        self.setToolTip('Click to enlarge. The enlarged view supports zoom and pan.')
        self._fit()

    def _fit(self):
        if self.original.isNull():
            self.clear()
            self.setText('No figure selected.')
        else:
            self.setPixmap(self.original.scaled(self.contentsRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.open_enlarged()
        super().mouseReleaseEvent(event)

    def open_enlarged(self):
        if self.original.isNull():
            return
        dialog = _dialog(self, 'MUSA — enlarged figure')
        layout = QVBoxLayout(dialog)
        scene = QGraphicsScene(dialog)
        scene.addPixmap(self.original)
        view = QGraphicsView(scene)
        view.setRenderHint(QPainter.SmoothPixmapTransform)
        view.setDragMode(QGraphicsView.ScrollHandDrag)
        controls = QHBoxLayout()
        for label, callback in (
            ('Zoom +', lambda: view.scale(1.25, 1.25)),
            ('Zoom −', lambda: view.scale(.8, .8)),
            ('Fit', lambda: view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)),
            ('Actual pixels', view.resetTransform),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, callback=callback: callback())
            controls.addWidget(button)
        layout.addLayout(controls)
        layout.addWidget(view, 1)
        self.dialogs.append(dialog)
        dialog.finished.connect(lambda _: self.dialogs.remove(dialog))
        dialog.show()
        view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
        return dialog

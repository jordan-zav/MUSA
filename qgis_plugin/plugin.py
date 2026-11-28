from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .i18n import tr
from .learning import default_language
from .runtime import icon_path


class MusaPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.dock = None
        self.actions = []

    def initProcessing(self):
        if self.provider is None:
            from .provider import MusaProvider

            self.provider = MusaProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()
        if self.iface is None or self.actions:
            return
        lang = default_language()
        for key, callback in (
            ("menu_workbench", self.show_workbench),
            ("menu_processing", self.open_processing),
        ):
            action = QAction(QIcon(icon_path()), tr(lang, key), self.iface.mainWindow())
            action.triggered.connect(callback)
            self.iface.addPluginToVectorMenu("MUSA", action)
            self.actions.append(action)
        self.iface.addToolBarIcon(self.actions[0])

    def update_action_labels(self, language):
        if len(self.actions) == 2:
            self.actions[0].setText(tr(language, "menu_workbench"))
            self.actions[1].setText(tr(language, "menu_processing"))

    def show_workbench(self):
        if self.dock is None:
            from .workbench import MusaDock

            self.dock = MusaDock(self.iface, on_language_changed=self.update_action_labels)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.show()
        self.dock.raise_()

    def open_processing(self):
        import processing

        processing.execAlgorithmDialog("musa:analyze", {})

    def unload(self):
        if self.dock is not None:
            self.dock.detach()
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        for action in self.actions:
            self.iface.removePluginVectorMenu("MUSA", action)
            self.iface.removeToolBarIcon(action)
            action.deleteLater()
        self.actions.clear()
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

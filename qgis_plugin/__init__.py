"""MUSA QGIS plugin entry point. Numerical code is bundled under _core."""


def classFactory(iface):
    from .plugin import MusaPlugin

    return MusaPlugin(iface)

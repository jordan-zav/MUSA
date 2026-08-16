from tkinter import TclError, Tk

import pytest

from musa.interface import MusaInterface


def _tk_root():
    try:
        root = Tk()
    except TclError as exc:
        pytest.skip(f"Tk runtime is unavailable: {exc}")
    root.withdraw()
    return root


def test_interface_defaults_to_explorer_mode_with_advanced_controls_hidden():
    root = _tk_root()
    try:
        app = MusaInterface(root)

        assert app.workflow_mode.get() == "Explorer"
        assert app.robustness_card.grid_info() == {}
        assert app.aggregate_mother.get() is True
        assert app.export_gis_package.get() is True
        assert app.create_zip_package.get() is True
        assert app.export_zeta_sensitivity.get() is False
        assert app.viewport.cget("xscrollcommand")
        assert app.viewport.cget("yscrollcommand")
        assert "Explorer" in app.summary_method.get()
    finally:
        app.logo_image = None
        app.window_icon_image = None
        root.destroy()


def test_interface_geomatics_mode_shows_advanced_controls():
    root = _tk_root()
    try:
        app = MusaInterface(root)
        app.workflow_mode.set("Geomatics")
        app._sync_workflow_mode()

        assert app.workflow_mode.get() == "Geomatics"
        assert app.robustness_card.grid_info() != {}
        assert "Geomatics" in app.summary_method.get()
    finally:
        app.logo_image = None
        app.window_icon_image = None
        root.destroy()


def test_interface_language_switch_updates_primary_labels():
    root = _tk_root()
    try:
        app = MusaInterface(root)

        app.language.set("Español")
        app._apply_language()
        assert app.run_button.cget("text") == "Ejecutar MUSA"
        assert app.suggest_button.cget("text") == "Sugerir escalas"
        assert "Explorer" in app.summary_method.get()
        assert "Global" in app.summary_outputs.get()

        app.language.set("English")
        app._apply_language()
        assert app.run_button.cget("text") == "Run MUSA"
        assert app.suggest_button.cget("text") == "Suggest Scales"
    finally:
        app.logo_image = None
        app.window_icon_image = None
        root.destroy()

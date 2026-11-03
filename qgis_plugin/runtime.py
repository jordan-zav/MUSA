"""Private core imports; never shadow another installed musa package."""

from pathlib import Path


def core():
    try:
        from ._core.musa import MUSA
        from ._core.musa.workflow import RunConfig, execute_analysis
    except ImportError as exc:
        raise ImportError(
            "MUSA needs NumPy, SciPy, Shapely and Matplotlib in the QGIS Python runtime. "
            "Use your QGIS distribution's dependency manager, then restart QGIS. "
            f"Details: {exc}"
        ) from exc
    return MUSA, RunConfig, execute_analysis


def icon_path():
    return str(Path(__file__).parent / "_core/musa/assets/icon_no_bg.png")

"""Scoped figure typography; never change the QGIS host's rcParams."""
from contextlib import contextmanager
from functools import wraps

import matplotlib as mpl


@contextmanager
def figure_style():
    with mpl.rc_context({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans"],
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
        "axes.linewidth": .7, "lines.linewidth": 1, "pdf.fonttype": 42,
    }):
        yield


def styled_figure(function):
    """Keep late-created legends, annotations and color bars in the same style."""
    @wraps(function)
    def render(*args, **kwargs):
        with figure_style():
            return function(*args, **kwargs)
    return render

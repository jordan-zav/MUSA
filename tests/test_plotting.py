import numpy as np

from musa.core import MUSAResult
from musa.plotting import export_analysis_plots


def test_import_and_render_do_not_switch_host_matplotlib_backend(tmp_path):
    import importlib
    import matplotlib
    import musa.plotting
    from types import SimpleNamespace

    original = matplotlib.get_backend()
    try:
        matplotlib.use("svg")
        importlib.reload(musa.plotting)
        assert matplotlib.get_backend().lower() == "svg"
        axis = musa.plotting.plot_singularity_spectrum(
            SimpleNamespace(alpha=np.array([1.0, 1.5, 2.0]), f_alpha=np.array([1.0, 1.5, 1.0]))
        )
        axis.figure.savefig(tmp_path / "host_backend.png")
        assert (tmp_path / "host_backend.png").is_file()
        assert matplotlib.get_backend().lower() == "svg"
    finally:
        matplotlib.use(original)


def test_export_analysis_plots_writes_q_colored_spectrum(tmp_path):
    result = MUSAResult(
        q=np.array([-2, -1, 0, 1, 2], dtype=float),
        scales=np.array([4000, 2000, 1000], dtype=float),
        dq=np.array([1.2, 1.3, 1.4, 1.5, 1.6], dtype=float),
        tau=np.zeros(5, dtype=float),
        alpha=np.array([1.4, 1.2, 1.3, 1.55, 1.6], dtype=float),
        f_alpha=np.array([1.0, 1.35, 1.4, 1.5, 1.62], dtype=float),
        r2=np.ones(5, dtype=float) * 0.99,
        p_values=np.ones(5, dtype=float) * 0.01,
        alpha_r2=np.ones(5, dtype=float) * 0.99,
        f_alpha_r2=np.ones(5, dtype=float) * 0.99,
        min_r2=0.9,
        rejected_q=np.array([], dtype=float),
        rejected_r2=np.array([], dtype=float),
        rejected_alpha_r2=np.array([], dtype=float),
        rejected_f_alpha_r2=np.array([], dtype=float),
    )

    outputs = export_analysis_plots(tmp_path, result)

    assert "multifractal_singularity_spectrum_by_q" in outputs
    assert (tmp_path / "multifractal_singularity_spectrum_by_q.png").is_file()


def test_uniform_line_plot_shows_dimension_one_without_tiny_offset_axis(tmp_path, monkeypatch):
    from shapely.geometry import LineString, box
    from musa import MUSA
    import musa.plotting as plotting
    result = MUSA.from_line_geometries([LineString([(0, 500), (1000, 500)])],
                                      box(0, 0, 1000, 1000), 'EPSG:32718', q_values=[0, 1, 2]).run_analysis(
                                          resolutions_m=[1000, 500, 250, 125, 62.5])
    figures = []
    monkeypatch.setattr(plotting, '_close', figures.append)
    export_analysis_plots(tmp_path, result)
    axis = next(fig.axes[0] for fig in figures if fig.axes[0].get_title() == 'Generalized dimensions Dq')
    low, high = axis.get_ylim()
    assert low < 1 < high and high - low >= .039
    assert not axis.yaxis.get_major_formatter().get_useOffset()
    assert axis.collections[-1].norm.vmin == 0 and axis.collections[-1].norm.vmax == 1

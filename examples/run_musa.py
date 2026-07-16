import numpy as np

from musa import MUSA, plot_singularity_spectrum, resolutions_from_mother_cell


def run_spatial_demo():
    points = np.random.rand(5000, 2)
    q_values = np.linspace(-4, 4, 9)
    analyzer = MUSA(points, q_values=q_values)
    result = analyzer.run_analysis(min_scale=0.01, max_scale=0.4, num_scales=24)
    print("Spatial demo")
    print("q count:", len(result.q))
    print("Dq sample:", result.dq[:5])
    print("alpha sample:", result.alpha[:5])
    plot_singularity_spectrum(result)


def run_gis_demo(path):
    q_values = np.arange(-4, 5, 1, dtype=float)
    analyzer = MUSA(
        data=path,
        boundary="data/test/extent_bh.shp",
        q_values=q_values,
        gis_reproject_to="auto",
    )
    resolutions = resolutions_from_mother_cell(
        mother_cell_m=4000,
        divisors=[2, 4, 6, 8, 16],
        include_mother=True,
    )
    result = analyzer.run_analysis(
        resolutions_m=resolutions,
        cell_length_threshold_m=0.01,
        bootstrap_iterations=200,
        bootstrap_seed=42,
        negative_q_floor_fraction=0.02,
    )
    print("GIS demo")
    print("q accepted:", result.q.tolist())
    print("Dq sample:", result.dq[:5])
    outputs = analyzer.export_cell_outputs(
        output_dir="outputs/test_cells",
        resolutions_m=resolutions,
        cell_length_threshold_m=0.01,
        aggregate_to_mother=True,
        q_values=result.q,
        reliable_min_zeta=0.15,
        reliable_min_r2=0.9,
        local_bootstrap_iterations=100,
        local_bootstrap_seed=42,
        negative_q_floor_fraction=0.02,
        zeta_exponents=(1.0, 1.0, 1.0),
        export_zeta_sensitivity=True,
    )
    from musa.plotting import export_mother_plots

    outputs["analysis_report"] = MUSA.export_analysis_report("outputs/test_cells", result)
    outputs["analysis_scale_diagnostics"] = MUSA.export_analysis_scale_diagnostics("outputs/test_cells", result)
    outputs.update(export_mother_plots("outputs/test_cells", result, highlight_q=2.0))
    print("CSV outputs:", outputs)
    plot_singularity_spectrum(result)


if __name__ == "__main__":
    run_spatial_demo()
    # run_gis_demo("data/lineamientos.shp")

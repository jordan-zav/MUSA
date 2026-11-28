"""Generate the bilingual workflow reference, diagram and control-to-core map."""
from pathlib import Path

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]

# UI names remain English so they can be located in the actual Workbench.
# A group includes every control named in its first column; files are conditional.
ROWS = [
    ('Analysis: Lineaments, Boundary, Use selected lines only, Analysis CRS', 'qgis_plugin/inputs.py: snapshot_sources, make_analyzer → MUSA.from_line_geometries', 'run_manifest.json: source; WKB in memory', 4, '2'),
    ('Analysis: Mother cell, Internal divisors', 'core.py: resolutions_from_mother_cell → run_analysis', 'analysis_report.csv; analysis_scale_diagnostics.csv', 1, '3'),
    ('Analysis: q Min, Max, Step', 'workflow.py: RunConfig → core.py: run_analysis; scaling.py', 'analysis_report.csv; scaling_support.csv; spectrum_curves.sqlite', 4, '3'),
    ('Analysis: Mother-cell spectra and reliability', 'core.py: export_cell_outputs', 'monofractal_cells.csv; multifractal_cells.csv; multifractal_mother_agg.csv', 4, '3'),
    ('Analysis: Density, orientation and anisotropy', 'structural.py: compute_lineament_mother_structural_stats', 'lineament_mother_structural_stats.csv', 5, '6'),
    ('Analysis: Whole-network connectivity statistics', 'network.py: compute_lineament_network_stats', 'lineament_network_stats.csv', 5, '6'),
    ('Analysis: Spectrum and diagnostic figures', 'plotting.py: export_analysis_plots, export_mother_plots', 'dq_scatterplot.png; r2_fit_quality.png; multifractal_singularity_spectrum*.png', 5, '8'),
    ('Analysis: GeoPackage layers', 'qgis_plugin/native_gis.py: export_mother_layers; moving.py: export_moving_windows', 'musa_mother_cells.gpkg; musa_moving_windows.gpkg', 5, '9'),
    ('Analysis: Output, Browse, Load spatial results into QGIS', 'workflow.py: execute_analysis; workbench.py: load_spatial_results', 'new run folder; QGIS layers', 5, '3'),
    ('Analysis: Save recipe, Load recipe', 'workflow.py: RunConfig.recipe, from_recipe; workbench.py: apply_config', 'recipe.json (parameters)', 5, '3'),
    ('Quality: Minimum fit R2, Cell length threshold', 'core.py: run_analysis, _probabilities_for_scale', 'analysis_report.csv; optional mother-cell tables', 4, '3'),
    ('Quality: Minimum mean zeta, Zeta scale floor, Zeta exponents', 'core.py: _zeta_mother_scale, _is_reliable, export_cell_outputs', 'multifractal_mother_agg.csv: canonical and weighted fields', 5, '3'),
    ('Quality: Negative-q floor fraction', 'core.py: _stabilize_probs_for_q', 'analysis_report.csv; recipe.json', 4, '3'),
    ('Quality: Global/Local bootstrap iterations, Confidence level, Random seed', 'core.py: _bootstrap_global_confidence_intervals, _bootstrap_regression_ci', 'confidence columns in analysis_report.csv / mother tables', 5, '3'),
    ('Quality: Export zeta sensitivity comparisons', 'core.py: export_zeta_sensitivity_summary', 'zeta_sensitivity_summary.csv', 5, '3'),
    ('Quality: Assess scaling support, Observation resolution, Box sizes', 'scaling.py: assess_lineament_scaling, assess_curve', 'scaling_support.json; scaling_support.csv', 4, '4'),
    ('Quality: Maximum windows to assess', 'workflow.py: execute_analysis window assessment loop', 'scaling_support.json: requested supports and states', 4, '6'),
    ('Quality: Renyi order policy, Coarse-end trimming', 'scaling.py: _pair_order, _trim_coarse, assess_lineament_scaling', 'scaling_support.json: order diagnostics, scale_trimming', 4, '4'),
    ('Quality: Classic box counting (comparison only)', 'classic.py: classic_box_counting, write_classic_comparison', 'classic_comparison.json; classic_box_counting.csv', 2, '8'),
    ('Quality: Run trace-relocation Monte Carlo test, Relocation replicates, Test tail', 'scaling.py: _relocate, monte_carlo_two_sided, monte_carlo_tail, holm_adjust', 'scaling_support.json: null; scaling_support.csv: p and Holm', 4, '5'),
    ('Moving windows: Enable, Window sizes, Centre spacing, Internal divisors', 'moving.py: analyze_moving_windows, export_moving_windows', 'moving_windows.csv; moving_nodes.csv; moving_windows_config.json', 5, '6'),
    ('Moving windows: Average 16 grid origins', 'moving.py: ENSEMBLE_OFFSETS, analyze_moving_windows', 'moving_windows.csv; moving_windows_config.json', 5, '6'),
    ('Moving windows: Proximity radii', 'proximity.py: analyze_fault_proximity; candidates.py: evaluate_candidates', 'potential_relations.csv; candidate_evidence.csv; trap_candidates.csv', 5, '6'),
    ('Run MUSA, Cancel, progress and status', 'workbench.py: AnalysisTask → workflow.py: execute_analysis; control.py: check_cancelled', 'run_manifest.json: complete/failed/cancelled; partial files retained', 5, '7'),
    ('Results: classic comparison and Monte Carlo summary', 'learning.py: comparison_text, relocation_text; workbench.py: set_run_summary', 'reads classic_comparison.json and scaling_support.json', 5, '8'),
    ('Results: Domain/calculation, Window center, Window size, Estimator', 'spectrum_products.py: list_spectra, read_spectrum', 'reads spectrum_curves.sqlite; spectrum_summary.csv', 5, '8'),
    ('Results: Chart, per-q table, Reason', 'spectrum_products.py: spectrum_figure, spectrum_shape_reasons; workbench.py: render_selected_spectrum', 'q-indexed curves and joint-spectrum gates; in-memory view', 4, '8'),
    ('Results: click spectrum, Export selected curves', 'qgis_plugin/chart_view.py: ChartView.open_enlarged; spectrum_products.py: spectrum_figure', 'selected PNG or SVG', 5, '8'),
    ('Results: Figures, click preview, Zoom/Fit/Actual pixels', 'qgis_plugin/chart_view.py: ImagePreview', 'reads saved PNG; in-memory enlarged view', 5, '8'),
    ('Results: Run details, Open completed run, Open output folder', 'workbench.py: show_run_details, open_completed_run, open_output', 'reads run_manifest.json and saved spectral index; no recalculation', 5, '8'),
    ('Learn / Fundamentos: language, chapter, links', 'qgis_plugin/learning.py: source_path, learning_html; workbench.py: LearningBrowser', 'docs/KNOWLEDGE_BASE*.md → packaged Markdown and HTML, three figures', 1, '11'),
    ('Processing: musa:analyze (LINES, BOUNDARY, CRS, MOTHER, DIVISORS, RESOLUTION, q, R2, products, CLASSIC_COMPARISON, OUTPUT)', 'provider.py: AnalyzeAlgorithm → workflow.py: execute_analysis', 'same global, optional mother/structural, assessment and classic files; run_manifest.json', 5, '3'),
    ('Processing: musa:scaling_support (inputs, SCALES, RESOLUTION, q, NULL_REPLICATES, RENYI_ORDER_POLICY, NULL_TAIL, COARSE_TRIM, SEED, CLASSIC_COMPARISON, OUTPUT)', 'provider.py: ScalingSupportAlgorithm → scaling.py: assess_lineament_scaling, write_scaling_reports', 'scaling_support.json/CSV; spectrum_curves.sqlite; classic files if requested; run_manifest.json', 4, '4'),
    ('Processing: musa:run_recipe (LINES, BOUNDARY, CRS, RECIPE, OUTPUT)', 'provider.py: AnalyzeAlgorithm(recipe=True) → RunConfig.from_recipe → execute_analysis', 'all enabled recipe products; recipe.json; run_manifest.json', 5, '3'),
    ('Processing: Help / local knowledge link', 'provider.py: helpUrl → learning.py: help_url', 'packaged KNOWLEDGE_BASE*.html; same canonical chapter', 1, '11'),
]


def diagram(language, folder):
    labels = {
        'en': ['Lines + observed polygon\nMetric CRS, resolution, declared scales',
               'QGIS snapshot / Python geometries\nValidate, reproject in host, clip',
               'Exact segment length per box\nConserved total length → probabilities',
               'Descriptive analysis\nGlobal + mother cells\nR², bootstrap, zeta',
               'Scaling assessment\nFour origins; fixed interval\nThree states per observable',
               'Moving windows\nSize, step, coverage\nLocal spectra + topology',
               'Optional trace relocation\nD0−D2, p, Holm, test resolution',
               'Tables / GeoPackage / figures\nSpectral SQLite index + summaries',
               'Results / reopen run\nRead saved estimates and reasons',
               'Recipe + run manifest\nParameters, provenance, hashes',
               'Learn / bilingual chapter\nSame source as Processing help',
               'Optional classic comparison\nAll scales, one origin; D_BC and R²'],
        'es': ['Trazas + polígono observado\nCRS métrico, resolución, escalas declaradas',
               'Copia QGIS / geometrías Python\nValidar, reproyectar en anfitrión, recortar',
               'Longitud exacta por caja\nLongitud total conservada → probabilidades',
               'Análisis descriptivo\nGlobal + celdas madre\nR², bootstrap, zeta',
               'Diagnóstico de escalamiento\nCuatro orígenes; intervalo fijo\nTres estados por observable',
               'Ventanas móviles\nTamaño, paso, cobertura\nEspectros locales + topología',
               'Recolocación opcional\nD0−D2, p, Holm, resolución de la prueba',
               'Tablas / GeoPackage / figuras\nÍndice espectral SQLite + resúmenes',
               'Results / reabrir ejecución\nLeer estimaciones y motivos guardados',
               'Receta + manifiesto\nParámetros, procedencia, hashes',
               'Fundamentos bilingües\nMisma fuente para ayuda de Processing',
               'Comparación clásica opcional\nTodas las escalas, un origen; D_BC y R²']}
    fig = Figure(figsize=(12, 10), constrained_layout=True)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.set(xlim=(0, 12.6), ylim=(-.7, 11.6))
    ax.axis('off')
    centers = [(4.4, 10.7), (4.4, 9.1), (4.4, 7.5), (1.9, 5.5), (5.9, 5.5),
               (9.9, 5.5), (6.5, 3.6), (4.4, 1.8), (4.4, .1), (10.1, 9.1), (9.9, .1), (10.1, 7.5)]
    widths = [6.7, 6.7, 6.7, 3.5, 3.5, 3.5, 4.8, 6.7, 6.7, 3.5, 3.5, 3.5]
    for i, ((x, y), width, label) in enumerate(zip(centers, widths, labels[language])):
        ax.add_patch(FancyBboxPatch((x-width/2, y-.55), width, 1.1, boxstyle='round,pad=.06',
                                   facecolor='#edf3f4' if i != 6 else '#f7eddf', edgecolor='#426777'))
        ax.text(x, y, label, ha='center', va='center', fontsize=9)
    def arrow(start, end, dotted=False):
        ax.annotate('', xy=end, xytext=start, arrowprops=dict(arrowstyle='->', color='#426777',
                                                           linestyle='--' if dotted else '-'))
    arrow((4.4, 10.1), (4.4, 9.7))
    arrow((4.4, 8.5), (4.4, 8.1))
    for x in (1.9, 5.9, 9.9):
        arrow((x if x < 8 else 7.6, 6.9), (x, 6.1))
    arrow((1.9, 4.9), (2, 2.4))
    ax.plot([9.9, 9.9], [4.9, 2.7], color='#426777', linewidth=1)
    arrow((9.9, 2.7), (7.8, 2.2))
    arrow((5.9, 4.9), (6.5, 4.2), True)
    arrow((6.5, 3), (6.5, 2.4))
    arrow((4.2, 4.9), (3.6, 2.4))
    arrow((4.4, 1.2), (4.4, .7))
    arrow((8.3, 9.1), (7.8, 9.1), True)
    arrow((7.8, 7.5), (8.3, 7.5), True)
    ax.plot([11.95, 12.3, 12.3], [7.5, 7.5, 1.8], color='#426777', linewidth=1)
    arrow((12.3, 1.8), (7.8, 1.8))
    ax.text(11.7, 10.7, 'MUSA 1.3.1', ha='right', fontsize=12, color='#24536b')
    for extension in ('png', 'svg'):
        fig.savefig(folder / f'workflow.{language}.{extension}', dpi=120)


def build():
    folder = ROOT / 'docs/images'
    for lang, suffix in (('en', ''), ('es', '.es')):
        diagram(lang, folder)
        title = 'Mapa del flujo y referencia de controles' if lang == 'es' else 'Workflow map and control reference'
        intro = ('Cada fila relaciona un control visible con su adaptador y función del núcleo. Los productos dependen '
                 'de las opciones activadas; el inventario efectivo está en run_manifest.json. Las rutas sin prefijo '
                 'pertenecen a src/musa; workbench.py y provider.py pertenecen a qgis_plugin. El selector de idioma '
                 'superior traduce toda la interfaz a español o inglés; la primera columna conserva los identificadores canónicos en inglés.' if lang == 'es' else
                 'Each row maps a visible control to its adapter and core function. Products depend on enabled options; '
                 'run_manifest.json is the actual inventory. Unprefixed core paths belong to src/musa; workbench.py and '
                 'provider.py belong to qgis_plugin. The header language selector switches the entire interface between English and Spanish; the first column lists the canonical English labels.')
        text = f'# {title}\n\n[English](WORKFLOW.md) · [Español](WORKFLOW.es.md)\n\n{intro}\n\n'
        text += f'![{title}](images/workflow.{lang}.png)\n\n[SVG](images/workflow.{lang}.svg)\n\n'
        text += ('El diagrama y esta tabla se regeneran con python scripts/build_workflow_map.py. '
                 'Las flechas discontinuas representan configuración o una etapa opcional.\n\n' if lang == 'es' else
                 'Regenerate the diagram and this table with python scripts/build_workflow_map.py. '
                 'Dashed arrows mark configuration or an optional stage.\n\n')
        text += ('| Pestaña / control o algoritmo | Adaptador → núcleo | Producto o efecto | Fundamentos / guía |\n' if lang == 'es' else
                 '| Tab / control or algorithm | Adapter → core | Product or effect | Learn / guide |\n')
        text += '| --- | --- | --- | --- |\n'
        for control, function, product, chapter, guide in ROWS:
            chapter = {1: 5, 2: 6, 3: 6, 4: 7, 5: 8}[chapter]
            if control.startswith('Learn /') or control == 'Processing: Help / local knowledge link':
                chapter = '1–8'
            product = product.replace('three figures', '13 figures per language')
            guide_section = guide
            text += f'| {control} | {function} | {product} | [KB §{chapter}](KNOWLEDGE_BASE{suffix}.md); [Guide §{guide_section}](USER_GUIDE{suffix}.md) |\n'
        text += ('\n## Lectura del flujo\n\nEl flujo descriptivo siempre calcula el ajuste global y exige al menos dos q aceptados. '
                 'El diagnóstico independiente conserva sus tres estados y puede ejecutarse mediante musa:scaling_support '
                 'sin ese filtro global. La comparación clásica usa todas las escalas y un origen; la longitud exacta '
                 'alimenta ambos cálculos. La prueba espacial utiliza únicamente el intervalo retenido antes de simular. '
                 'Las ventanas tienen cobertura y estados propios. Reabrir una ejecución lee sus archivos.\n\n'
                 'La disponibilidad de estimaciones por q y la aceptación de la forma conjunta f(alpha) se evalúan '
                 'por separado. Las vistas indican por qué se retiene una curva. Los cuadernos de '
                 '[API Python](../notebooks/README.md) recorren esos contratos sin QGIS.\n' if lang == 'es' else
                 '\n## Reading the flow\n\nThe descriptive workflow always fits the global spectrum and requires at least '
                 'two accepted q values. Independent assessment retains three states and can run through '
                 'musa:scaling_support without that global filter. Classic comparison uses all scales and one origin; '
                 'exact length supplies both calculations. The spatial test uses the interval retained before simulation. '
                 'Windows carry their own coverage and states. Reopening a run reads its files.\n\n'
                 'Per-q availability and the joint f(alpha) shape gates are assessed separately. Views explain why a '
                 'curve is withheld. The [Python API notebooks](../notebooks/README.md) cover these contracts without QGIS.\n')
        (ROOT / f'docs/WORKFLOW{suffix}.md').write_text(text, encoding='utf-8')


if __name__ == '__main__':
    build()

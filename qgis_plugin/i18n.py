"""Bilingual (English / Spanish) UI strings for the MUSA QGIS plugin and Processing provider."""

UI_TEXTS = {
    "en": {
        "dock_title": "MUSA — Multifractal Workbench",
        "header_title": "<b>MUSA</b><br>Multifractal Spectrum Analyzer",
        "lang_label": "Language",
        "menu_workbench": "MUSA Workbench",
        "menu_processing": "Multifractal analysis / batch…",
        "task_title": "MUSA — multifractal analysis",
        # Main tabs
        "tab_analysis": "Analysis",
        "tab_quality": "Quality",
        "tab_moving": "Moving windows",
        "tab_results": "Results",
        # Analysis tab
        "grp_inputs": "1 · Project inputs",
        "lbl_lineaments": "Lineaments",
        "lbl_boundary": "Boundary",
        "chk_selected_only": "Use selected lines only",
        "lbl_crs": "Analysis CRS",
        "source_prompt": "Choose a line layer and polygon boundary. Analysis units must be metres.",
        "source_summary": (
            "Analysis CRS: {crs}. {lines} line features; {boundaries} boundary features. "
            "Input layers are transformed to this CRS for analysis."
        ),
        "custom_metric_crs": "custom metric CRS",
        "grp_scales": "2 · Scale design",
        "lbl_mother": "Mother cell (m)",
        "lbl_divisors": "Internal divisors",
        "lbl_min": "Min",
        "lbl_max": "Max",
        "lbl_step": "Step",
        "lbl_q_range": "q range",
        "note_neg_q": "Negative q may be unreliable. See docs/NEGATIVE_Q.md.",
        "note_box_sizes": "Internal box sizes = mother size / divisors.",
        "grp_products": "3 · Products",
        "opt_local": "Mother-cell spectra and reliability",
        "opt_structural": "Density, orientation and anisotropy",
        "opt_network": "Whole-network connectivity statistics",
        "opt_plots": "Spectrum and diagnostic figures",
        "opt_gis": "GeoPackage layers",
        "note_global_included": "Global spectra and scale diagnostics are always included.",
        "grp_output": "4 · Output",
        "ph_output_root": "Choose a parent folder; each run creates a new subfolder",
        "btn_browse": "Browse…",
        "chk_add_layers": "Load spatial results into QGIS",
        "btn_load_recipe": "Load recipe",
        "btn_save_recipe": "Save recipe",
        # Quality tab
        "grp_quality": "Numerical quality",
        "lbl_min_r2": "Minimum fit R2",
        "lbl_threshold": "Cell length threshold (m)",
        "lbl_min_zeta": "Minimum mean zeta",
        "lbl_zeta_floor": "Zeta scale floor",
        "lbl_zeta_exponents": "Zeta exponents",
        "lbl_neg_floor": "Negative-q floor fraction",
        "lbl_boot_global": "Global bootstrap iterations",
        "lbl_boot_local": "Local bootstrap iterations",
        "lbl_confidence": "Confidence level",
        "lbl_seed": "Random seed",
        "chk_sensitivity": "Export zeta sensitivity comparisons",
        "note_quality": (
            "Standard and weighted estimates are reported separately. "
            "The reliability weight measures numerical support."
        ),
        "grp_scaling": "Finite-range Renyi scaling support",
        "chk_scaling_support": "Assess scaling support",
        "tt_scaling_resolution": (
            "Enter the observation resolution of your source map before running; "
            "it is not inferred from the CRS or the cell sizes."
        ),
        "ph_scaling_scales": "Blank: analysis scales; need at least 8 resolved scales",
        "chk_null_enabled": "Run trace-relocation Monte Carlo test",
        "tt_null": (
            "Optional; off by default. Reference timing for 1201 traces, 12 scales and four grid origins: "
            "about 5 minutes for 199 replicates or 25 minutes for 999. Runtime varies with the map and computer. "
            "The scaling diagnostic runs without this test; unsupported scaling can prevent the test from starting."
        ),
        "policy_legacy_block": "Require ordered dimensions",
        "policy_inform_q0_q2": "Warn about D0–D2 order",
        "tail_upper": "Upper tail",
        "tail_two_sided": "Two-sided",
        "lbl_resolution": "Observation resolution (m; required)",
        "lbl_box_sizes": "Box sizes (m)",
        "lbl_max_windows": "Maximum windows to assess",
        "lbl_order_policy": "Renyi order policy",
        "lbl_coarse_trim": "Coarse-end trimming: min effective q=2 boxes (0=off)",
        "grp_null": "Optional Monte Carlo test",
        "lbl_null_replicates": "Relocation replicates",
        "lbl_null_tail": "Test tail",
        "note_scaling": (
            "Checks dimension stability and curvature across the declared scales. "
            "The warning option retains the D0–D2 contrast when dimension order fails; all fit checks still apply. "
            "The optional spatial test relocates traces while preserving their shapes, lengths and orientations."
        ),
        # Moving windows tab
        "grp_windows": "Overlapping windows (experimental)",
        "chk_moving": "Enable moving-window analysis",
        "chk_ensemble": "Average 16 grid origins (slower)",
        "ph_proximity": "Optional: 100,250,500",
        "lbl_win_sizes": "Window sizes (m)",
        "lbl_win_step": "Centre spacing (m)",
        "lbl_win_divisors": "Internal divisors",
        "lbl_proximity": "Proximity radii (m)",
        "note_moving": (
            "Estimates spectra and structural statistics in overlapping windows. "
            "Requires GeoPandas. Cancellation takes effect after the current stage."
        ),
        # Results tab
        "summary_none": "No analysis yet.",
        "btn_open_run": "Open completed run",
        "subtab_spectra": "Spectra",
        "subtab_figures": "Figures",
        "subtab_details": "Run details",
        "grp_choose_domain": "Choose domain or window",
        "lbl_domain": "Domain / calculation",
        "lbl_win_center": "Window center",
        "lbl_win_size": "Window size",
        "lbl_estimator": "Estimator",
        "spectrum_none": "No indexed spectra yet.",
        "panel_f_alpha": "Multifractal spectrum",
        "panel_dq": "Generalized dimensions Dq",
        "panel_tau": "Mass exponent τ(q)",
        "panel_alpha": "Singularity exponent α(q)",
        "panel_all": "Overview",
        "lbl_chart": "Chart",
        "tbl_headers": ["q", "Dq", "tau", "alpha", "f(alpha)", "Dq status", "Per-q values", "Reason"],
        "tt_table": "All requested q are retained. A dash means no estimate; inspect the reason column.",
        "btn_export_spectrum": "Export selected curves (PNG / SVG)",
        "note_figures": "Select a figure. Click its preview to enlarge, zoom or pan.",
        "btn_open_folder": "Open output folder",
        # Bottom controls & status
        "btn_run": "Run MUSA",
        "btn_cancel": "Cancel",
        "status_ready": "Ready",
        "status_running": "Running",
        "status_cancelling": "Cancellation requested; waiting for the current operation.",
        "status_complete": "Analysis complete",
        "status_cancelled": "Analysis cancelled. Partial outputs retained.",
        # File dialogs & runtime errors
        "dlg_output_parent": "Choose output parent folder",
        "dlg_save_recipe": "Save MUSA recipe",
        "dlg_load_recipe": "Load MUSA recipe",
        "dlg_open_run": "Open a completed MUSA run",
        "dlg_export_spectrum": "Export selected spectrum",
        "err_missing_resolution": "Enter the observation resolution of your source map in metres under Quality before running.",
        "err_missing_output": "Choose an existing output parent folder.",
        "err_already_running": "An analysis is already running.",
        "err_wait_finish": "Wait for the current analysis to finish.",
        "err_only_completed": "Only completed runs can be opened in the spectrum viewer.",
        "err_select_spectrum": "Select a completed spectrum first.",
        "err_png_svg": "Choose a PNG or SVG filename.",
        "err_layer_load": "Analysis saved; layer loading failed: {exc}",
        "err_metric_crs": "Choose a projected analysis CRS in metres.",
        "err_both_crs": "Both inputs need a defined source CRS.",
        "err_geom_types": "Choose a line layer and a polygon boundary layer.",
        "err_prep_cancelled": "Input preparation cancelled.",
        "err_invalid_geom": "Invalid geometry in feature {fid}; repair the input layer first.",
        "err_invalid_transformed": "Feature {fid} is invalid after transformation.",
        "err_empty_input": "Input is empty (or the explicit line selection is empty).",
        # Run summaries & details
        "failed_spectrum_note": "Failed/cancelled run: incomplete spectra are not loaded. Partial outputs remain on disk.",
        "summary_global_fit": "Global fit: {accepted} accepted q · {rejected} rejected q",
        "summary_completed_run": "Completed run",
        "summary_renyi": (
            "\nRenyi scaling (support/q): {comp} compatible · {unsup} unsupported · "
            "{insuf} insufficient. Select a support below."
        ),
        "summary_policy": "\nOrder policy: {policies}. q=0,2 order warnings: {warnings}; these describe finite-range slopes.",
        "details_saved": "Saved analysis",
        "details_status": "Status: {status}",
        "details_version": "MUSA version: {version}",
        "details_folder": "Output folder: {folder}",
        "details_started": "Started (UTC): {started}",
        "details_finished": "Finished (UTC): {finished}",
        "details_unknown": "unknown",
        "details_not_recorded": "not recorded",
        "details_global_q": "Global fit q: {accepted} accepted, {rejected} rejected",
        "details_inputs": "Inputs and provenance",
        "details_settings": "Analysis settings",
        "details_outputs": "Output files",
        "details_messages": "Processing messages for this execution",
        # Spectrum viewer dynamic strings
        "dom_global": "Global",
        "dom_moving": "Moving windows",
        "src_analysis": "analysis",
        "src_assessment": "scaling assessment",
        "center_item": "Center {center} · up to {count} usable q",
        "est_standard": "Standard",
        "est_weighted": "Weighted",
        "no_indexed_selection": "No indexed spectrum for this selection. Older runs remain available as files.",
        "ties_multiple_q": " (multiple q)",
        "ties_prefix": "ties: ",
        "coverage_fmt": " Coverage: {cov:.1%} (minimum {min_cov:.0%}).",
        "no_joint_q": "No jointly supported per-q estimates.",
        "per_q_avail": "Per-q estimates available: {valid}/{total}.",
        "joint_withheld": "Joint spectrum withheld: ",
        "spectrum_note_body": (
            "{prefix}{coverage}\n"
            "alpha(q=0): {a0} · Observed peak: {obs} · Fitted peak: {fit}\n"
            "{shape}See per-q diagnostics below. Click the chart to enlarge."
        ),
        "tt_spectrum_note": (
            "Direct Chhabra–Jensen estimates from regressions across box sizes. "
            "Standard estimates use ordinary least squares; weighted estimates use reliability weights. "
            "Analysis uses one grid origin; scaling assessment averages four shifted origins. "
            "The spectrum is shown only when scaling diagnostics and spectrum shape support it. "
            "A quadratic peak is descriptive and does not establish multifractality."
        ),
        "val_available": "available",
        "val_unavailable": "unavailable",
        "err_display_spectrum": "Could not display spectrum: {exc}",
        # ChartView / ImagePreview
        "tt_chart_enlarge": "Click to enlarge; zoom, pan and export in the enlarged view.",
        "dlg_enlarged_spectrum": "MUSA — enlarged spectrum",
        "img_select_prompt": "Select a figure to preview.",
        "tt_img_enlarge": "Click to enlarge. The enlarged view supports zoom and pan.",
        "img_none": "No figure selected.",
        "dlg_enlarged_figure": "MUSA — enlarged figure",
        "btn_zoom_in": "Zoom +",
        "btn_zoom_out": "Zoom −",
        "btn_fit": "Fit",
        "btn_actual_px": "Actual pixels",
        # Statuses & reasons
        "statuses": {
            "compatible_finite_range": "Compatible over the tested scales",
            "identity": "Fixed by normalization",
            "insufficient_information": "Insufficient information",
            "not_supported": "Not supported",
            "accepted": "Regression accepted",
        },
        "status_fallback": "See diagnostics",
        "reasons": {
            "low_coverage": "Too little of this window lies inside the observed domain",
            "insufficient_effective_boxes": "Too few effective occupied boxes at this q",
            "quadratic_predicts_better": "A curved model predicts better than a straight scaling law",
            "no_line_support": "No observed line support in this window",
            "no_resolved_scales": "No scales remain above the observation resolution",
            "accepted": "Fit threshold met",
            "legacy_fit_rejected": "Regression does not meet the fit threshold",
            "too_few_resolved_scales": "Fewer than eight resolved scales",
            "short_scaling_interval": "Scale interval spans less than one decade",
            "poor_linear_fit": "Scaling curve does not meet the fit threshold",
            "scale_sensitive_dimension": "Estimate changes when scales are omitted",
            "grid_sensitive_dimension": "Estimate changes with grid placement",
            "segmented_predicts_better": "A segmented model predicts better than a straight scaling law",
            "renyi_dimension_order_violation": "Dimensions do not decrease with q",
            "dimension_outside_planar_range": "Dimension lies outside the expected planar range",
            "constant_curve": "No change across the declared scales",
            "below_observation_resolution": "Cell sizes fall below observation resolution",
            "normalization_identity_not_scaling_evidence": "Fixed by normalization",
            "coarse_scale_trimming_below_one_decade": "Coarse-scale removal leaves too short an interval",
        },
        "reason_fallback": "See the detailed diagnostic report",
        # Layer names (English kept canonical; Spanish localized when requested)
        "layer_scaling_diag": "Renyi scaling support - diagnostics",
        "layer_names": {},
        # Processing provider
        "proc_group": "Lineament analysis",
        "proc_analyze": "Multifractal and structural analysis",
        "proc_recipe": "Run analysis recipe",
        "proc_scaling": "Assess Renyi scaling support",
        "proc_boundary": "Analysis boundary",
        "proc_crs": "Analysis CRS (projected, metres)",
        "proc_recipe_file": "MUSA analysis recipe",
        "proc_mother": "Mother cell size (m)",
        "proc_divisors": "Internal scale divisors",
        "proc_q_min": "q minimum",
        "proc_q_max": "q maximum",
        "proc_q_step": "q step",
        "proc_local": "Mother-cell spectra",
        "proc_structural": "Structural statistics",
        "proc_network": "Network statistics",
        "proc_plots": "Spectrum figures",
        "proc_output": "New output folder",
        "proc_manifest": "Run manifest",
        "proc_scales": "Box sizes (m; enter for your source map)",
        "proc_res_decl": "Observation resolution (m; must be declared)",
        "proc_null_reps": "Conditional trace-relocation replicates (0=off; >=19)",
        "proc_null_tail": "Monte Carlo tail of the D0-D2 test",
        "proc_coarse_trim": "Coarse-end trimming: minimum effective q=2 boxes (0=off)",
        "proc_report": "Scaling support JSON",
        "proc_help_analyze": (
            "Analyze line length at multiple scales with the shared MUSA core. "
            "Choose a projected analysis CRS in metres. Inputs can have different CRSs. "
            "Boundary uses all features. Use QGIS feature-source selection for selected lines. "
            "Output must be a new folder; temporary output is supported. "
            "Reliability describes numerical support, not geological probability. "
            "Recipes include all workbench options, including experimental moving windows. "
            "Negative q may be unreliable; see docs/NEGATIVE_Q.md. "
            "Learn / Fundamentos is available in MUSA Workbench. "
            '<a href="{url}">Learn / Fundamentos: illustrated knowledge base</a>.'
        ),
        "proc_help_scaling": (
            "Assess finite-range generalized Renyi dimensions Dq on fixed box sizes. "
            "Declare observation resolution in metres. Needs at least eight resolved scales "
            "spanning one decade; boxes above one quarter of the smaller domain extent are excluded. "
            "Compares linear, quadratic and segmented log-log fits by leave-one-scale-out prediction, "
            "reselecting the breakpoint in each training fold. Four shifted origins diagnose grid effects. "
            "Optional independent trace translations preserve shapes, lengths and orientations inside "
            "the boundary. Their Monte Carlo test concerns spatial heterogeneity, not proof of "
            "multifractality. Use zero replicates to disable, or at least 19; the minimum p is 1/(B+1). "
            "Outputs retain every q, including insufficient/unsupported fits. No best-range search. "
            "Dimension order is checked by default. The optional D0–D2 warning "
            "retains the slope contrast when order fails; fit and curvature checks still apply. "
            "The two-sided tail gives p = min(1, 2 min(upper, lower)), minimum 2/(B+1). "
            "Coarse-end trimming (0=off) drops coarse scales with too few effective q=2 boxes "
            "on the observed map before any replicate; less than one decade left means abstention. "
            "This tool assesses scaling independently of the analysis regression filter. "
            "Negative q may be unreliable; see docs/NEGATIVE_Q.md. "
            "The optional classic comparison uses all input scales and one origin. "
            "High R² alone leaves scaling unvalidated. "
            '<a href="{url}">Learn / Fundamentos: illustrated knowledge base</a>.'
        ),
    },
    "es": {
        "dock_title": "MUSA — Entorno Multifractal",
        "header_title": "<b>MUSA</b><br>Analizador de Espectros Multifractales",
        "lang_label": "Idioma",
        "menu_workbench": "Entorno MUSA",
        "menu_processing": "Análisis multifractal / por lotes…",
        "task_title": "MUSA — análisis multifractal",
        # Main tabs
        "tab_analysis": "Análisis",
        "tab_quality": "Calidad",
        "tab_moving": "Ventanas móviles",
        "tab_results": "Resultados",
        # Analysis tab
        "grp_inputs": "1 · Entradas del proyecto",
        "lbl_lineaments": "Lineamientos",
        "lbl_boundary": "Límite / dominio",
        "chk_selected_only": "Usar solo las líneas seleccionadas",
        "lbl_crs": "CRS de análisis",
        "source_prompt": "Elija una capa de líneas y un polígono de límite. Las unidades de análisis deben estar en metros.",
        "source_summary": (
            "CRS de análisis: {crs}. {lines} entidades de línea; {boundaries} entidades de límite. "
            "Las capas de entrada se transforman a este CRS para el análisis."
        ),
        "custom_metric_crs": "CRS métrico personalizado",
        "grp_scales": "2 · Diseño de escalas",
        "lbl_mother": "Celda madre (m)",
        "lbl_divisors": "Divisores internos",
        "lbl_min": "Mín.",
        "lbl_max": "Máx.",
        "lbl_step": "Paso",
        "lbl_q_range": "Rango de q",
        "note_neg_q": "Los órdenes q negativos pueden ser inestables. Véase docs/NEGATIVE_Q.md.",
        "note_box_sizes": "Tamaños internos de caja = tamaño de celda madre / divisores.",
        "grp_products": "3 · Productos",
        "opt_local": "Espectros y confiabilidad por celda madre",
        "opt_structural": "Densidad, orientación y anisotropía",
        "opt_network": "Estadísticas de conectividad de toda la red",
        "opt_plots": "Figuras de espectros y diagnóstico",
        "opt_gis": "Capas GeoPackage",
        "note_global_included": "Los espectros globales y los diagnósticos de escala se incluyen siempre.",
        "grp_output": "4 · Salida",
        "ph_output_root": "Elija una carpeta base; cada ejecución crea una subcarpeta nueva",
        "btn_browse": "Examinar…",
        "chk_add_layers": "Cargar resultados espaciales en QGIS",
        "btn_load_recipe": "Cargar receta",
        "btn_save_recipe": "Guardar receta",
        # Quality tab
        "grp_quality": "Calidad numérica",
        "lbl_min_r2": "R² mínimo de ajuste",
        "lbl_threshold": "Umbral de longitud por celda (m)",
        "lbl_min_zeta": "Zeta media mínima",
        "lbl_zeta_floor": "Piso de escala para zeta",
        "lbl_zeta_exponents": "Exponentes de zeta",
        "lbl_neg_floor": "Fracción de piso para q negativo",
        "lbl_boot_global": "Iteraciones bootstrap globales",
        "lbl_boot_local": "Iteraciones bootstrap locales",
        "lbl_confidence": "Nivel de confianza",
        "lbl_seed": "Semilla aleatoria",
        "chk_sensitivity": "Exportar comparaciones de sensibilidad de zeta",
        "note_quality": (
            "Las estimaciones estándar y ponderadas se reportan por separado. "
            "El peso de confiabilidad mide soporte numérico, no probabilidad geológica."
        ),
        "grp_scaling": "Soporte de escalamiento de Rényi de rango finito",
        "chk_scaling_support": "Evaluar soporte de escalamiento",
        "tt_scaling_resolution": (
            "Ingrese la resolución de observación de su mapa fuente antes de ejecutar; "
            "no se infiere del CRS ni del tamaño de las celdas."
        ),
        "ph_scaling_scales": "Vacío: escalas del análisis; se requieren al menos 8 escalas resueltas",
        "chk_null_enabled": "Ejecutar prueba Monte Carlo de reubicación de trazas",
        "tt_null": (
            "Opcional; desactivado por defecto. Tiempo orientativo para 1201 trazas, 12 escalas y cuatro orígenes: "
            "unos 5 minutos con 199 réplicas o 25 minutos con 999. El tiempo varía según el mapa y el equipo. "
            "El diagnóstico de escalamiento se ejecuta sin esta prueba; si el escalamiento no está respaldado, la prueba no se inicia."
        ),
        "policy_legacy_block": "Exigir dimensiones ordenadas",
        "policy_inform_q0_q2": "Advertir sobre el orden D0–D2",
        "tail_upper": "Cola superior",
        "tail_two_sided": "Bilateral (dos colas)",
        "lbl_resolution": "Resolución de observación (m; obligatoria)",
        "lbl_box_sizes": "Tamaños de caja (m)",
        "lbl_max_windows": "Máximo de ventanas a evaluar",
        "lbl_order_policy": "Política de orden de Rényi",
        "lbl_coarse_trim": "Recorte de escalas gruesas: mín. cajas efectivas q=2 (0=desact.)",
        "grp_null": "Prueba Monte Carlo opcional",
        "lbl_null_replicates": "Réplicas de reubicación",
        "lbl_null_tail": "Cola de la prueba",
        "note_scaling": (
            "Comprueba la estabilidad y curvatura de la dimensión en las escalas declaradas. "
            "La opción de advertencia conserva el contraste D0–D2 cuando falla el orden; los demás criterios de ajuste se mantienen. "
            "La prueba espacial opcional reubica las trazas conservando su forma, longitud y orientación."
        ),
        # Moving windows tab
        "grp_windows": "Ventanas superpuestas (experimental)",
        "chk_moving": "Activar análisis por ventanas móviles",
        "chk_ensemble": "Promediar 16 orígenes de grilla (más lento)",
        "ph_proximity": "Opcional: 100,250,500",
        "lbl_win_sizes": "Tamaños de ventana (m)",
        "lbl_win_step": "Espaciamiento entre centros (m)",
        "lbl_win_divisors": "Divisores internos",
        "lbl_proximity": "Radios de proximidad (m)",
        "note_moving": (
            "Estima espectros y estadísticas estructurales en ventanas superpuestas. "
            "Requiere GeoPandas. La cancelación surte efecto al terminar la etapa actual."
        ),
        # Results tab
        "summary_none": "Aún no hay ningún análisis.",
        "btn_open_run": "Abrir ejecución completada",
        "subtab_spectra": "Espectros",
        "subtab_figures": "Figuras",
        "subtab_details": "Detalles de ejecución",
        "grp_choose_domain": "Elegir dominio o ventana",
        "lbl_domain": "Dominio / cálculo",
        "lbl_win_center": "Centro de ventana",
        "lbl_win_size": "Tamaño de ventana",
        "lbl_estimator": "Estimador",
        "spectrum_none": "Aún no hay espectros indexados.",
        "panel_f_alpha": "Espectro multifractal",
        "panel_dq": "Dimensiones generalizadas Dq",
        "panel_tau": "Exponente de masa τ(q)",
        "panel_alpha": "Exponente de singularidad α(q)",
        "panel_all": "Vista general",
        "lbl_chart": "Gráfico",
        "tbl_headers": ["q", "Dq", "tau", "alpha", "f(alpha)", "Estado de Dq", "Valores por q", "Motivo"],
        "tt_table": "Se conservan todos los órdenes q solicitados. Un guion indica ausencia de estimación; revise la columna de motivo.",
        "btn_export_spectrum": "Exportar curvas seleccionadas (PNG / SVG)",
        "note_figures": "Seleccione una figura. Haga clic en la vista previa para ampliar, hacer zoom o desplazar.",
        "btn_open_folder": "Abrir carpeta de salida",
        # Bottom controls & status
        "btn_run": "Ejecutar MUSA",
        "btn_cancel": "Cancelar",
        "status_ready": "Listo",
        "status_running": "Ejecutando",
        "status_cancelling": "Cancelación solicitada; esperando a que finalice la operación actual.",
        "status_complete": "Análisis completado",
        "status_cancelled": "Análisis cancelado. Se conservan las salidas parciales.",
        # File dialogs & runtime errors
        "dlg_output_parent": "Elegir carpeta base de salida",
        "dlg_save_recipe": "Guardar receta de MUSA",
        "dlg_load_recipe": "Cargar receta de MUSA",
        "dlg_open_run": "Abrir una ejecución completada de MUSA",
        "dlg_export_spectrum": "Exportar espectro seleccionado",
        "err_missing_resolution": "Ingrese la resolución de observación del mapa fuente en metros en la pestaña Calidad antes de ejecutar.",
        "err_missing_output": "Elija una carpeta base de salida existente.",
        "err_already_running": "Ya hay un análisis en ejecución.",
        "err_wait_finish": "Espere a que termine el análisis actual.",
        "err_only_completed": "Solo pueden abrirse ejecuciones completadas en el visor de espectros.",
        "err_select_spectrum": "Seleccione primero un espectro completado.",
        "err_png_svg": "Elija un nombre de archivo PNG o SVG.",
        "err_layer_load": "Análisis guardado; falló la carga de capas: {exc}",
        "err_metric_crs": "Elija un CRS de análisis proyectado en metros.",
        "err_both_crs": "Ambas capas de entrada requieren un CRS de origen definido.",
        "err_geom_types": "Elija una capa de líneas y una capa poligonal de límite.",
        "err_prep_cancelled": "Preparación de entradas cancelada.",
        "err_invalid_geom": "Geometría inválida en la entidad {fid}; repare primero la capa de entrada.",
        "err_invalid_transformed": "La entidad {fid} resultó inválida tras la transformación de CRS.",
        "err_empty_input": "La entrada está vacía (o la selección explícita de líneas está vacía).",
        # Run summaries & details
        "failed_spectrum_note": "Ejecución fallida o cancelada: no se cargan espectros incompletos. Las salidas parciales permanecen en disco.",
        "summary_global_fit": "Ajuste global: {accepted} órdenes q aceptados · {rejected} rechazados",
        "summary_completed_run": "Ejecución completada",
        "summary_renyi": (
            "\nEscalamiento de Rényi (soporte/q): {comp} compatibles · {unsup} no respaldados · "
            "{insuf} insuficientes. Seleccione un soporte abajo."
        ),
        "summary_policy": "\nPolítica de orden: {policies}. Advertencias de orden q=0,2: {warnings}; describen pendientes de rango finito.",
        "details_saved": "Análisis guardado",
        "details_status": "Estado: {status}",
        "details_version": "Versión de MUSA: {version}",
        "details_folder": "Carpeta de salida: {folder}",
        "details_started": "Inicio (UTC): {started}",
        "details_finished": "Fin (UTC): {finished}",
        "details_unknown": "desconocido",
        "details_not_recorded": "no registrado",
        "details_global_q": "Ajuste global q: {accepted} aceptados, {rejected} rechazados",
        "details_inputs": "Entradas y procedencia",
        "details_settings": "Parámetros del análisis",
        "details_outputs": "Archivos de salida",
        "details_messages": "Mensajes de procesamiento de esta ejecución",
        # Spectrum viewer dynamic strings
        "dom_global": "Global",
        "dom_moving": "Ventanas móviles",
        "src_analysis": "análisis",
        "src_assessment": "diagnóstico de escalamiento",
        "center_item": "Centro {center} · hasta {count} órdenes q utilizables",
        "est_standard": "Estándar",
        "est_weighted": "Ponderado",
        "no_indexed_selection": "No hay espectro indexado para esta selección. Las corridas anteriores siguen disponibles como archivos.",
        "ties_multiple_q": " (múltiples q)",
        "ties_prefix": "empates: ",
        "coverage_fmt": " Cobertura: {cov:.1%} (mínimo {min_cov:.0%}).",
        "no_joint_q": "Sin estimaciones por orden q respaldadas conjuntamente.",
        "per_q_avail": "Estimaciones por q disponibles: {valid}/{total}.",
        "joint_withheld": "Espectro conjunto retenido: ",
        "spectrum_note_body": (
            "{prefix}{coverage}\n"
            "alpha(q=0): {a0} · Pico observado: {obs} · Pico ajustado: {fit}\n"
            "{shape}Véanse abajo los diagnósticos por orden q. Haga clic en el gráfico para ampliar."
        ),
        "tt_spectrum_note": (
            "Estimaciones directas de Chhabra–Jensen mediante regresiones sobre tamaños de caja. "
            "El estimador estándar usa mínimos cuadrados ordinarios; el ponderado usa pesos de confiabilidad. "
            "El análisis usa un origen de grilla; el diagnóstico de escalamiento promedia cuatro orígenes desplazados. "
            "El espectro se muestra solo cuando el diagnóstico de escalamiento y la forma espectral lo respaldan. "
            "Un pico cuadrático es descriptivo y no demuestra multifractalidad."
        ),
        "val_available": "disponible",
        "val_unavailable": "no disponible",
        "err_display_spectrum": "No se pudo mostrar el espectro: {exc}",
        # ChartView / ImagePreview
        "tt_chart_enlarge": "Haga clic para ampliar; haga zoom, desplace y exporte en la vista ampliada.",
        "dlg_enlarged_spectrum": "MUSA — espectro ampliado",
        "img_select_prompt": "Seleccione una figura para previsualizar.",
        "tt_img_enlarge": "Haga clic para ampliar. La vista ampliada permite hacer zoom y desplazar.",
        "img_none": "Ninguna figura seleccionada.",
        "dlg_enlarged_figure": "MUSA — figura ampliada",
        "btn_zoom_in": "Zoom +",
        "btn_zoom_out": "Zoom −",
        "btn_fit": "Ajustar",
        "btn_actual_px": "Píxeles reales",
        # Statuses & reasons
        "statuses": {
            "compatible_finite_range": "Compatible en las escalas evaluadas",
            "identity": "Fijado por normalización",
            "insufficient_information": "Información insuficiente",
            "not_supported": "No respaldado",
            "accepted": "Regresión aceptada",
        },
        "status_fallback": "Ver diagnósticos",
        "reasons": {
            "low_coverage": "Muy poca área de esta ventana cae dentro del dominio observado",
            "insufficient_effective_boxes": "Muy pocas cajas ocupadas efectivas en este orden q",
            "quadratic_predicts_better": "Un modelo curvo predice mejor que una recta de escalamiento",
            "no_line_support": "Sin soporte de líneas observadas en esta ventana",
            "no_resolved_scales": "No quedan escalas por encima de la resolución de observación",
            "accepted": "Umbral de ajuste cumplido",
            "legacy_fit_rejected": "La regresión no alcanza el umbral de ajuste",
            "too_few_resolved_scales": "Menos de ocho escalas resueltas",
            "short_scaling_interval": "El intervalo de escalas abarca menos de una década",
            "poor_linear_fit": "La curva de escalamiento no alcanza el umbral lineal",
            "scale_sensitive_dimension": "La estimación cambia al omitir escalas",
            "grid_sensitive_dimension": "La estimación cambia con la posición de la grilla",
            "segmented_predicts_better": "Un modelo segmentado predice mejor que una recta de escalamiento",
            "renyi_dimension_order_violation": "Las dimensiones no decrecen con q",
            "dimension_outside_planar_range": "La dimensión cae fuera del rango planar esperado",
            "constant_curve": "Sin variación a lo largo de las escalas declaradas",
            "below_observation_resolution": "Los tamaños de celda caen por debajo de la resolución de observación",
            "normalization_identity_not_scaling_evidence": "Fijado por normalización",
            "coarse_scale_trimming_below_one_decade": "El recorte de escalas gruesas deja menos de una década",
        },
        "reason_fallback": "Véase el informe detallado de diagnóstico",
        # Layer names
        "layer_scaling_diag": "Soporte de escalamiento de Rényi - diagnósticos",
        "layer_names": {
            "mother_multifractal_display": "Celdas madre - visualización multifractal",
            "mother_multifractal_all_q": "Celdas madre - todos los órdenes q",
            "mother_monofractal": "Celdas madre - monofractal",
            "mother_structural_stats": "Celdas madre - estadísticas estructurales",
            "window_spectrum_summary": "Ventanas móviles - resumen espectral",
            "window_shifted_spectra": "Ventanas móviles - espectros desplazados",
            "window_structural_stats": "Ventanas móviles - estadísticas estructurales",
        },
        # Processing provider
        "proc_group": "Análisis de lineamientos",
        "proc_analyze": "Análisis multifractal y estructural",
        "proc_recipe": "Ejecutar receta de análisis",
        "proc_scaling": "Evaluar soporte de escalamiento de Rényi",
        "proc_boundary": "Límite de análisis",
        "proc_crs": "CRS de análisis (proyectado, metros)",
        "proc_recipe_file": "Receta de análisis de MUSA",
        "proc_mother": "Tamaño de celda madre (m)",
        "proc_divisors": "Divisores internos de escala",
        "proc_q_min": "q mínimo",
        "proc_q_max": "q máximo",
        "proc_q_step": "Paso de q",
        "proc_local": "Espectros por celda madre",
        "proc_structural": "Estadísticas estructurales",
        "proc_network": "Estadísticas de red",
        "proc_plots": "Figuras de espectros",
        "proc_output": "Nueva carpeta de salida",
        "proc_manifest": "Manifiesto de ejecución",
        "proc_scales": "Tamaños de caja (m; ingrese según su mapa fuente)",
        "proc_res_decl": "Resolución de observación (m; debe declararse)",
        "proc_null_reps": "Réplicas condicionales de reubicación de trazas (0=desact.; >=19)",
        "proc_null_tail": "Cola Monte Carlo de la prueba D0-D2",
        "proc_coarse_trim": "Recorte de escalas gruesas: mínimo de cajas efectivas q=2 (0=desact.)",
        "proc_report": "JSON de soporte de escalamiento",
        "proc_help_analyze": (
            "Analiza la longitud de líneas en múltiples escalas con el núcleo compartido de MUSA. "
            "Elija un CRS de análisis proyectado en metros. Las entradas pueden tener distintos CRS. "
            "El límite utiliza todas sus entidades. Use la selección nativa de QGIS para líneas seleccionadas. "
            "La salida debe ser una carpeta nueva; se admite salida temporal. "
            "La confiabilidad describe soporte numérico, no probabilidad geológica. "
            "Las recetas incluyen todas las opciones del entorno, incluidas las ventanas móviles experimentales. "
            "Los órdenes q negativos pueden ser inestables; véase docs/NEGATIVE_Q.md. "
            "Learn / Fundamentos está disponible en el Entorno MUSA. "
            '<a href="{url}">Learn / Fundamentos: base de conocimientos ilustrada</a>.'
        ),
        "proc_help_scaling": (
            "Evalúa dimensiones generalizadas de Rényi Dq de rango finito sobre tamaños de caja fijos. "
            "Declare la resolución de observación en metros. Requiere al menos ocho escalas resueltas "
            "que abarquen una década; se excluyen cajas mayores a un cuarto del lado menor del dominio. "
            "Compara ajustes lineal, cuadrático y segmentado en log-log mediante validación cruzada dejando una escala fuera, "
            "reseleccionando el punto de quiebre en cada pliegue. Cuatro orígenes desplazados diagnostican efectos de grilla. "
            "Las traslaciones independientes opcionales conservan forma, longitud y orientación dentro "
            "del límite. Su prueba Monte Carlo evalúa heterogeneidad espacial, no demuestra "
            "multifractalidad. Use cero réplicas para desactivar, o al menos 19; el p mínimo es 1/(B+1). "
            "Las salidas conservan todos los órdenes q, incluidos los insuficientes o no respaldados. No busca rangos óptimos. "
            "El orden dimensional se verifica por defecto. La advertencia opcional D0–D2 "
            "conserva el contraste de pendientes cuando falla el orden; las pruebas de ajuste y curvatura siguen aplicándose. "
            "La cola bilateral entrega p = min(1, 2 min(superior, inferior)), con mínimo 2/(B+1). "
            "El recorte grueso (0=desact.) descarta escalas gruesas con muy pocas cajas efectivas q=2 "
            "en el mapa observado antes de cualquier réplica; menos de una década restante implica abstención. "
            "Esta herramienta evalúa el escalamiento con independencia del filtro de regresión del análisis. "
            "Los órdenes q negativos pueden ser inestables; véase docs/NEGATIVE_Q.md. "
            "La comparación clásica opcional usa todas las escalas de entrada y un solo origen. "
            "Un R² alto por sí solo no valida el escalamiento. "
            '<a href="{url}">Learn / Fundamentos: base de conocimientos ilustrada</a>.'
        ),
    },
}


def tr(language: str, key: str) -> str:
    table = UI_TEXTS.get(language, UI_TEXTS["en"])
    return table[key]

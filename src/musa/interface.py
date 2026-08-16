from __future__ import annotations

import math
import os
import sys
import threading
from pathlib import Path
from datetime import datetime


def _configure_tcl_tk_runtime() -> None:
    """Point tkinter at the Tcl/Tk libraries bundled with the active Python."""
    if os.name != "nt" or getattr(sys, "frozen", False):
        return
    tcl_root = Path(sys.base_prefix) / "tcl"
    tcl_library = tcl_root / "tcl8.6"
    tk_library = tcl_root / "tk8.6"
    if tcl_library.is_dir():
        os.environ.setdefault("TCL_LIBRARY", str(tcl_library))
    if tk_library.is_dir():
        os.environ.setdefault("TK_LIBRARY", str(tk_library))


_configure_tcl_tk_runtime()

from tkinter import BooleanVar, Canvas, END, PhotoImage, StringVar, TclError, Tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import numpy as np

from .core import MUSA
from .packaging import package_run_output
from .plotting import export_analysis_plots, export_mother_plots
from .spectrum import write_spectrum_fit_summary


def _parse_csv_floats(raw: str) -> list[float]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError("Debes ingresar al menos un valor.")
    values = [float(p) for p in parts]
    return values


class MusaInterface:
    COLORS = {
        "ivory": "#F2EFE8",
        "panel": "#ECE5D8",
        "slate": "#314E60",
        "petrol": "#18323F",
        "schist": "#4E6B5A",
        "sand": "#BFA27A",
        "rock": "#7A8388",
        "charcoal": "#1F2326",
        "white": "#FBFAF7",
        "line": "#BBB19F",
        "input_fill": "#FFFFFF",
        "input_border": "#7F8B8E",
        "input_focus": "#314E60",
        "input_disabled": "#E2DDD2",
    }

    ROBUSTNESS_PRESETS = {
        "baseline": {
            "bootstrap_iterations": "0",
            "bootstrap_ci": "0.95",
            "bootstrap_seed": "",
            "local_bootstrap_iterations": "0",
            "local_bootstrap_ci": "0.95",
            "reliable_min_zeta": "0.15",
            "reliable_min_r2": "0.90",
            "negative_q_floor_fraction": "0.00",
            "zeta_cov_exp": "1.0",
            "zeta_mass_exp": "1.0",
            "zeta_scale_exp": "1.0",
            "zeta_neff_exp": "1.0",
            "zeta_scale_floor": "0.25",
            "export_zeta_sensitivity": False,
        },
        "balanced": {
            "bootstrap_iterations": "25",
            "bootstrap_ci": "0.95",
            "bootstrap_seed": "42",
            "local_bootstrap_iterations": "10",
            "local_bootstrap_ci": "0.95",
            "reliable_min_zeta": "0.15",
            "reliable_min_r2": "0.90",
            "negative_q_floor_fraction": "0.01",
            "zeta_cov_exp": "1.0",
            "zeta_mass_exp": "1.0",
            "zeta_scale_exp": "1.0",
            "zeta_neff_exp": "1.0",
            "zeta_scale_floor": "0.25",
            "export_zeta_sensitivity": False,
        },
        "experimental": {
            "bootstrap_iterations": "50",
            "bootstrap_ci": "0.95",
            "bootstrap_seed": "42",
            "local_bootstrap_iterations": "25",
            "local_bootstrap_ci": "0.95",
            "reliable_min_zeta": "0.10",
            "reliable_min_r2": "0.85",
            "negative_q_floor_fraction": "0.02",
            "zeta_cov_exp": "1.0",
            "zeta_mass_exp": "1.0",
            "zeta_scale_exp": "1.0",
            "zeta_neff_exp": "1.0",
            "zeta_scale_floor": "0.25",
            "export_zeta_sensitivity": True,
        },
    }

    UI_ES = {
        "Geological multiscale workspace": "Espacio geomatico multiescala",
        "Multifractal analysis for lineaments, scale logic, and spatial robustness": "Analisis multifractal de lineamientos, escalas y robustez espacial",
        "Mode": "Modo",
        "Language": "Idioma",
        "Run MUSA": "Ejecutar MUSA",
        "Suggest Scales": "Sugerir escalas",
        "Project Inputs": "Datos del proyecto",
        "Lines": "Lineamientos",
        "Boundary": "Limite",
        "Output Directory": "Directorio de salida",
        "Browse": "Buscar",
        "Scale Design": "Diseno de escalas",
        "Unit Cell (m)": "Celda unidad (m)",
        "Mother Cell (m)": "Celda madre (m)",
        "Divisors": "Divisores",
        "q-min": "q-min",
        "q-max": "q-max",
        "q-step": "paso q",
        "Cell Length Threshold (m)": "Umbral de longitud (m)",
        "Output Options": "Opciones de salida",
        "Aggregate to mother cell outputs": "Agregar salidas por celda madre",
        "Auto-expand boundary to fit target mother": "Autoexpandir limite para ajustar celda madre",
        "Export GIS GeoPackage": "Exportar GeoPackage GIS",
        "Create ZIP package": "Crear paquete ZIP",
        "Run Summary": "Resumen de corrida",
        "Method": "Metodo",
        "q Window": "Ventana q",
        "Outputs": "Salidas",
        "Run State": "Estado",
        "Robustness Controls": "Controles de robustez",
        "Run Quality": "Calidad global",
        "Local Reliability": "Confiabilidad local",
        "Zeta Weighting": "Ponderacion zeta",
        "Preset": "Preset",
        "Apply Preset": "Aplicar preset",
        "Baseline is the defensible default. Experimental increases uncertainty handling and zeta sweeps.": "Baseline es el valor defendible por defecto. Experimental aumenta manejo de incertidumbre y barridos zeta.",
        "Bootstrap": "Bootstrap",
        "CI": "IC",
        "Seed": "Semilla",
        "Negative q floor": "Piso q negativo",
        "Local Bootstrap": "Bootstrap local",
        "Local CI": "IC local",
        "Reliable zeta": "zeta confiable",
        "Reliable R2": "R2 confiable",
        "Reliable filters control which mother cells are safest for interpolation and GIS validation.": "Los filtros reliable controlan que celdas madre son mas seguras para interpolacion y validacion GIS.",
        "zeta exponent c": "exponente zeta c",
        "zeta exponent m": "exponente zeta m",
        "zeta exponent s": "exponente zeta s",
        "zeta exponent neff": "exponente zeta neff",
        "zeta scale floor": "piso de escala zeta",
        "Export zeta sensitivity profiles": "Exportar perfiles de sensibilidad zeta",
        "Execution Log": "Log de ejecucion",
        "Recent execution messages": "Mensajes recientes de ejecucion",
        "Clear Log": "Limpiar log",
        "Global": "Global",
        "local": "local",
        "zeta": "zeta",
        "Idle": "Inactivo",
        "Pending": "Pendiente",
        "Cost: pending": "Costo: pendiente",
        "Preset: pending   Cost: incomplete config": "Preset: pendiente   Costo: configuracion incompleta",
        "Starting MUSA run...": "Iniciando corrida MUSA...",
        "Running": "Ejecutando",
        "Complete": "Completo",
        "Error": "Error",
        "Geomatics": "Geomatica",
        "Analysis completed successfully.": "Analisis completado correctamente.",
    }

    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("MUSA - Multifractal Spectrum Analyzer")
        self.root.geometry("1080x860")
        self.root.minsize(980, 760)
        self.root.configure(bg=self.COLORS["ivory"])
        self.viewport = Canvas(self.root, bg=self.COLORS["ivory"], highlightthickness=0)
        self.main_frame = ttk.Frame(self.viewport, padding=16)
        self.vertical_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.viewport.yview)
        self.horizontal_scrollbar = ttk.Scrollbar(self.root, orient="horizontal", command=self.viewport.xview)
        self.viewport.configure(
            yscrollcommand=self.vertical_scrollbar.set,
            xscrollcommand=self.horizontal_scrollbar.set,
        )
        self.logo_image: PhotoImage | None = None
        self.window_icon_image: PhotoImage | None = None

        self.language = StringVar(value="English")
        self.workflow_mode = StringVar(value="Explorer")
        self.robustness_mode = StringVar(value="baseline")
        self.aggregate_mother = BooleanVar(value=True)
        self.auto_expand_target = BooleanVar(value=True)
        self.export_gis_package = BooleanVar(value=True)
        self.create_zip_package = BooleanVar(value=True)
        self.export_zeta_sensitivity = BooleanVar(value=False)
        self.summary_method = StringVar(value="Chhabra-Jensen")
        self.summary_q = StringVar(value="Pending")
        self.summary_outputs = StringVar(value="Global")
        self.summary_cost = StringVar(value="Cost: pending")
        self.summary_status = StringVar(value="Idle")
        self.log_messages: list[str] = []

        self._configure_styles()
        self._configure_window_icon()
        self._build_layout()
        self._set_defaults()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("App.TFrame", background=self.COLORS["ivory"])
        style.configure("Sidebar.TFrame", background=self.COLORS["ivory"])
        style.configure("Content.TFrame", background=self.COLORS["ivory"])
        style.configure("Panel.TFrame", background=self.COLORS["panel"])
        style.configure("Header.TFrame", background=self.COLORS["white"])
        style.configure("HeaderActions.TFrame", background=self.COLORS["white"])
        style.configure(
            "Card.TLabelframe",
            background=self.COLORS["panel"],
            borderwidth=1,
            relief="solid",
            bordercolor=self.COLORS["line"],
            lightcolor=self.COLORS["line"],
            darkcolor=self.COLORS["line"],
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=self.COLORS["panel"],
            foreground=self.COLORS["slate"],
            font=("Segoe UI Semibold", 11),
        )
        style.configure("TLabel", background=self.COLORS["ivory"], foreground=self.COLORS["charcoal"])
        style.configure("HeaderTitle.TLabel", background=self.COLORS["white"], foreground=self.COLORS["petrol"], font=("Segoe UI Semibold", 24))
        style.configure("HeaderSub.TLabel", background=self.COLORS["white"], foreground=self.COLORS["rock"], font=("Segoe UI", 11))
        style.configure("Muted.TLabel", background=self.COLORS["white"], foreground=self.COLORS["rock"], font=("Segoe UI", 9))
        style.configure("Field.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["slate"], font=("Segoe UI Semibold", 10))
        style.configure("Body.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["charcoal"], font=("Segoe UI", 9))
        style.configure("StatValue.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["petrol"], font=("Segoe UI Semibold", 16))
        style.configure("StatCaption.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["rock"], font=("Segoe UI", 9))
        style.configure(
            "Accent.TLabel",
            background=self.COLORS["sand"],
            foreground=self.COLORS["charcoal"],
            font=("Segoe UI Semibold", 9),
            padding=(8, 4),
        )
        style.configure(
            "Ghost.TButton",
            background=self.COLORS["white"],
            foreground=self.COLORS["slate"],
            bordercolor=self.COLORS["line"],
            lightcolor=self.COLORS["line"],
            darkcolor=self.COLORS["line"],
            borderwidth=1,
            padding=(10, 8),
        )
        style.map("Ghost.TButton", background=[("active", self.COLORS["panel"])])
        style.configure(
            "Primary.TButton",
            background=self.COLORS["slate"],
            foreground=self.COLORS["white"],
            borderwidth=0,
            focusthickness=0,
            padding=(14, 8),
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.COLORS["petrol"]), ("disabled", self.COLORS["rock"])],
            foreground=[("disabled", self.COLORS["white"])],
        )
        style.configure(
            "Secondary.TButton",
            background=self.COLORS["sand"],
            foreground=self.COLORS["charcoal"],
            borderwidth=0,
            focusthickness=0,
            padding=(12, 8),
        )
        style.map("Secondary.TButton", background=[("active", "#A98D65"), ("disabled", "#CBBCA4")])
        style.configure(
            "Form.TEntry",
            fieldbackground=self.COLORS["input_fill"],
            background=self.COLORS["input_fill"],
            foreground=self.COLORS["charcoal"],
            insertcolor=self.COLORS["charcoal"],
            bordercolor=self.COLORS["input_border"],
            lightcolor=self.COLORS["input_border"],
            darkcolor=self.COLORS["input_border"],
            padding=(8, 7),
            relief="solid",
            borderwidth=2,
        )
        style.map(
            "Form.TEntry",
            fieldbackground=[("disabled", self.COLORS["input_disabled"])],
            bordercolor=[("focus", self.COLORS["input_focus"]), ("!focus", self.COLORS["input_border"])],
            lightcolor=[("focus", self.COLORS["input_focus"]), ("!focus", self.COLORS["input_border"])],
            darkcolor=[("focus", self.COLORS["input_focus"]), ("!focus", self.COLORS["input_border"])],
        )
        style.configure(
            "Form.TCombobox",
            fieldbackground=self.COLORS["input_fill"],
            background=self.COLORS["input_fill"],
            foreground=self.COLORS["charcoal"],
            arrowsize=14,
            arrowcolor=self.COLORS["petrol"],
            bordercolor=self.COLORS["input_border"],
            lightcolor=self.COLORS["input_border"],
            darkcolor=self.COLORS["input_border"],
            padding=(8, 6),
            relief="solid",
            borderwidth=2,
        )
        style.map(
            "Form.TCombobox",
            fieldbackground=[("readonly", self.COLORS["input_fill"]), ("disabled", self.COLORS["input_disabled"])],
            bordercolor=[("focus", self.COLORS["input_focus"]), ("!focus", self.COLORS["input_border"])],
            lightcolor=[("focus", self.COLORS["input_focus"]), ("!focus", self.COLORS["input_border"])],
            darkcolor=[("focus", self.COLORS["input_focus"]), ("!focus", self.COLORS["input_border"])],
            background=[("readonly", self.COLORS["input_fill"])],
        )
        style.configure("TCheckbutton", background=self.COLORS["panel"], foreground=self.COLORS["charcoal"])
        style.map("TCheckbutton", background=[("active", self.COLORS["panel"])])
        style.configure(
            "TNotebook",
            background=self.COLORS["panel"],
            borderwidth=0,
            tabmargins=(0, 4, 0, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background=self.COLORS["ivory"],
            foreground=self.COLORS["slate"],
            padding=(12, 7),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.COLORS["white"]), ("active", self.COLORS["panel"])],
            foreground=[("selected", self.COLORS["petrol"])],
        )

    def _load_asset_image(self, filename: str, max_width: int | None = None) -> PhotoImage | None:
        asset_path = Path(__file__).resolve().parent / "assets" / filename
        if not asset_path.is_file():
            return None
        try:
            image = PhotoImage(file=str(asset_path))
        except TclError:
            return None
        if max_width is not None and image.width() > max_width:
            scale = max(1, math.ceil(image.width() / max_width))
            if scale > 1:
                image = image.subsample(scale, scale)
        return image

    def _configure_window_icon(self) -> None:
        self.window_icon_image = self._load_asset_image("icon_no_bg.png")
        if self.window_icon_image is None:
            self.window_icon_image = self._load_asset_image("icon.png")
        if self.window_icon_image is not None:
            self.root.iconphoto(True, self.window_icon_image)

    def _load_logo_image(self) -> PhotoImage | None:
        logo = self._load_asset_image("logo.png", max_width=300)
        if logo is not None:
            return logo
        icon_like = self._load_asset_image("icon_no_bg.png", max_width=90)
        if icon_like is None:
            icon_like = self._load_asset_image("icon.png", max_width=90)
        return icon_like

    def _build_layout(self) -> None:
        pad = {"padx": 10, "pady": 7}
        frm = self.main_frame
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.viewport.grid(row=0, column=0, sticky="nsew")
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        viewport_window = self.viewport.create_window((0, 0), window=frm, anchor="nw")

        def refresh_scroll_region(_event=None) -> None:
            self.viewport.configure(scrollregion=self.viewport.bbox("all"))

        def fit_content_to_viewport(event) -> None:
            self.viewport.itemconfigure(
                viewport_window,
                width=max(event.width, frm.winfo_reqwidth()),
                height=max(event.height, frm.winfo_reqheight()),
            )

        frm.bind("<Configure>", refresh_scroll_region)
        self.viewport.bind("<Configure>", fit_content_to_viewport)
        frm.configure(style="App.TFrame")
        frm.columnconfigure(0, weight=0)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(1, weight=1)

        header = ttk.Frame(frm, style="Header.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 14))
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=0)
        self.logo_image = self._load_logo_image()
        logo_has_wordmark = self.logo_image is not None and self.logo_image.width() >= 180
        if self.logo_image is not None:
            ttk.Label(header, image=self.logo_image, background=self.COLORS["white"]).grid(
                row=0, column=0, rowspan=2, sticky="w", padx=(18, 16), pady=16
            )
        if logo_has_wordmark:
            ttk.Label(header, text="Geological multiscale workspace", style="Accent.TLabel").grid(
                row=0, column=1, sticky="sw", padx=8, pady=(20, 4)
            )
        else:
            ttk.Label(header, text="MUSA", style="HeaderTitle.TLabel").grid(
                row=0, column=1, sticky="sw", padx=8, pady=(14, 0)
            )
        ttk.Label(
            header,
            text="Multifractal analysis for lineaments, scale logic, and spatial robustness",
            style="HeaderSub.TLabel",
        ).grid(row=1, column=1, sticky="nw", padx=8, pady=(0, 18))
        header_actions = ttk.Frame(header, style="HeaderActions.TFrame")
        header_actions.grid(row=0, column=2, rowspan=2, sticky="e", padx=(16, 18), pady=16)
        ttk.Label(header_actions, text="Language", style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.language_box = ttk.Combobox(
            header_actions,
            textvariable=self.language,
            values=["English", "Español"],
            state="readonly",
            width=10,
            style="Form.TCombobox",
        )
        self.language_box.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(header_actions, text="Mode", style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=(0, 8))
        self.workflow_mode_box = ttk.Combobox(
            header_actions,
            textvariable=self.workflow_mode,
            values=["Explorer", "Geomatics"],
            state="readonly",
            width=12,
            style="Form.TCombobox",
        )
        self.workflow_mode_box.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.run_button = ttk.Button(header_actions, text="Run MUSA", command=self.run_analysis, style="Primary.TButton")
        self.run_button.grid(row=1, column=2, sticky="e", padx=(0, 8))
        self.suggest_button = ttk.Button(
            header_actions, text="Suggest Scales", command=self.suggest_scales_from_boundary, style="Ghost.TButton"
        )
        self.suggest_button.grid(row=1, column=3, sticky="e")

        sidebar = ttk.Frame(frm, style="Sidebar.TFrame")
        sidebar.grid(row=1, column=0, sticky="ns", padx=(4, 10))
        sidebar.columnconfigure(0, weight=1)

        content = ttk.Frame(frm, style="Content.TFrame")
        content.grid(row=1, column=1, sticky="nsew", padx=(0, 4))
        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)

        data_card = ttk.LabelFrame(sidebar, text="Project Inputs", style="Card.TLabelframe")
        data_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        data_card.columnconfigure(0, weight=1)
        data_card.columnconfigure(1, weight=0)
        self.lines_path = ttk.Entry(data_card, width=34, style="Form.TEntry")
        self.boundary_path = ttk.Entry(data_card, width=34, style="Form.TEntry")
        self.output_dir = ttk.Entry(data_card, width=34, style="Form.TEntry")
        ttk.Label(data_card, text="Lines", style="Field.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", **pad)
        self.lines_path.grid(row=1, column=0, sticky="ew", **pad)
        ttk.Button(data_card, text="Browse", command=self._pick_lines, style="Secondary.TButton", width=11).grid(row=1, column=1, sticky="e", **pad)
        ttk.Label(data_card, text="Boundary", style="Field.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", **pad)
        self.boundary_path.grid(row=3, column=0, sticky="ew", **pad)
        ttk.Button(data_card, text="Browse", command=self._pick_boundary, style="Secondary.TButton", width=11).grid(row=3, column=1, sticky="e", **pad)
        ttk.Label(data_card, text="Output Directory", style="Field.TLabel").grid(row=4, column=0, columnspan=2, sticky="w", **pad)
        self.output_dir.grid(row=5, column=0, sticky="ew", **pad)
        ttk.Button(data_card, text="Browse", command=self._pick_output, style="Secondary.TButton", width=11).grid(row=5, column=1, sticky="e", **pad)

        scale_card = ttk.LabelFrame(sidebar, text="Scale Design", style="Card.TLabelframe")
        scale_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        scale_card.columnconfigure(1, weight=1)
        scale_card.columnconfigure(3, weight=1)
        self.unit_cell = ttk.Entry(scale_card, width=12, style="Form.TEntry")
        self.mother_cell = ttk.Entry(scale_card, width=12, style="Form.TEntry")
        self.divisors = ttk.Entry(scale_card, width=28, style="Form.TEntry")
        self.q_min = ttk.Entry(scale_card, width=8, style="Form.TEntry")
        self.q_max = ttk.Entry(scale_card, width=8, style="Form.TEntry")
        self.q_step = ttk.Entry(scale_card, width=8, style="Form.TEntry")
        self.threshold = ttk.Entry(scale_card, width=12, style="Form.TEntry")
        ttk.Label(scale_card, text="Unit Cell (m)", style="Field.TLabel").grid(row=0, column=0, sticky="w", **pad)
        self.unit_cell.grid(row=0, column=1, sticky="ew", **pad)
        ttk.Label(scale_card, text="Mother Cell (m)", style="Field.TLabel").grid(row=0, column=2, sticky="w", **pad)
        self.mother_cell.grid(row=0, column=3, sticky="ew", **pad)
        ttk.Label(scale_card, text="Divisors", style="Field.TLabel").grid(row=1, column=0, sticky="w", **pad)
        self.divisors.grid(row=1, column=1, columnspan=3, sticky="ew", **pad)
        ttk.Label(scale_card, text="q-min", style="Field.TLabel").grid(row=2, column=0, sticky="w", **pad)
        self.q_min.grid(row=2, column=1, sticky="ew", **pad)
        ttk.Label(scale_card, text="q-max", style="Field.TLabel").grid(row=2, column=2, sticky="w", **pad)
        self.q_max.grid(row=2, column=3, sticky="ew", **pad)
        ttk.Label(scale_card, text="q-step", style="Field.TLabel").grid(row=3, column=0, sticky="w", **pad)
        self.q_step.grid(row=3, column=1, sticky="ew", **pad)
        ttk.Label(scale_card, text="Cell Length Threshold (m)", style="Field.TLabel").grid(row=3, column=2, sticky="w", **pad)
        self.threshold.grid(row=3, column=3, sticky="ew", **pad)

        options_card = ttk.LabelFrame(sidebar, text="Output Options", style="Card.TLabelframe")
        options_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        options_card.columnconfigure(0, weight=1)
        self.aggregate_check = ttk.Checkbutton(
            options_card,
            text="Aggregate to mother cell outputs",
            variable=self.aggregate_mother,
            command=self._sync_robustness_state,
        )
        self.aggregate_check.grid(row=0, column=0, sticky="w", **pad)
        ttk.Checkbutton(
            options_card,
            text="Auto-expand boundary to fit target mother",
            variable=self.auto_expand_target,
        ).grid(row=1, column=0, sticky="w", **pad)
        self.gis_package_check = ttk.Checkbutton(
            options_card,
            text="Export GIS GeoPackage",
            variable=self.export_gis_package,
            command=self._refresh_summary,
        )
        self.gis_package_check.grid(row=2, column=0, sticky="w", **pad)
        ttk.Checkbutton(
            options_card,
            text="Create ZIP package",
            variable=self.create_zip_package,
            command=self._refresh_summary,
        ).grid(row=3, column=0, sticky="w", **pad)

        summary_card = ttk.LabelFrame(content, text="Run Summary", style="Card.TLabelframe")
        summary_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for col in range(4):
            summary_card.columnconfigure(col, weight=1)
        ttk.Label(summary_card, text="Method", style="StatCaption.TLabel").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))
        ttk.Label(summary_card, textvariable=self.summary_method, style="StatValue.TLabel").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
        ttk.Label(summary_card, text="q Window", style="StatCaption.TLabel").grid(row=0, column=1, sticky="w", padx=10, pady=(10, 2))
        ttk.Label(summary_card, textvariable=self.summary_q, style="StatValue.TLabel").grid(row=1, column=1, sticky="w", padx=10, pady=(0, 10))
        ttk.Label(summary_card, text="Outputs", style="StatCaption.TLabel").grid(row=0, column=2, sticky="w", padx=10, pady=(10, 2))
        ttk.Label(summary_card, textvariable=self.summary_outputs, style="StatValue.TLabel").grid(row=1, column=2, sticky="w", padx=10, pady=(0, 10))
        ttk.Label(summary_card, text="Run State", style="StatCaption.TLabel").grid(row=0, column=3, sticky="w", padx=10, pady=(10, 2))
        ttk.Label(summary_card, textvariable=self.summary_status, style="StatValue.TLabel").grid(row=1, column=3, sticky="w", padx=10, pady=(0, 10))
        ttk.Label(summary_card, textvariable=self.summary_cost, style="Body.TLabel").grid(row=2, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 10))

        self.robustness_card = ttk.LabelFrame(content, text="Robustness Controls", style="Card.TLabelframe")
        self.robustness_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.robustness_card.columnconfigure(0, weight=1)
        robustness_tabs = ttk.Notebook(self.robustness_card)
        robustness_tabs.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        quality_tab = ttk.Frame(robustness_tabs, style="Panel.TFrame")
        local_tab = ttk.Frame(robustness_tabs, style="Panel.TFrame")
        zeta_tab = ttk.Frame(robustness_tabs, style="Panel.TFrame")
        robustness_tabs.add(quality_tab, text="Run Quality")
        robustness_tabs.add(local_tab, text="Local Reliability")
        robustness_tabs.add(zeta_tab, text="Zeta Weighting")
        for tab in (quality_tab, local_tab, zeta_tab):
            for col in range(4):
                tab.columnconfigure(col, weight=1)

        self.preset_box = ttk.Combobox(
            quality_tab,
            textvariable=self.robustness_mode,
            values=["baseline", "balanced", "experimental", "custom"],
            state="readonly",
            width=16,
            style="Form.TCombobox",
        )
        self.apply_preset_button = ttk.Button(
            quality_tab, text="Apply Preset", command=self._apply_selected_preset, style="Secondary.TButton"
        )
        self.bootstrap_iterations = ttk.Entry(quality_tab, width=12, style="Form.TEntry")
        self.bootstrap_ci = ttk.Entry(quality_tab, width=10, style="Form.TEntry")
        self.bootstrap_seed = ttk.Entry(quality_tab, width=10, style="Form.TEntry")
        self.local_bootstrap_iterations = ttk.Entry(local_tab, width=12, style="Form.TEntry")
        self.local_bootstrap_ci = ttk.Entry(local_tab, width=10, style="Form.TEntry")
        self.reliable_min_zeta = ttk.Entry(local_tab, width=12, style="Form.TEntry")
        self.reliable_min_r2 = ttk.Entry(local_tab, width=10, style="Form.TEntry")
        self.negative_q_floor_fraction = ttk.Entry(quality_tab, width=12, style="Form.TEntry")
        self.zeta_cov_exp = ttk.Entry(zeta_tab, width=8, style="Form.TEntry")
        self.zeta_mass_exp = ttk.Entry(zeta_tab, width=8, style="Form.TEntry")
        self.zeta_scale_exp = ttk.Entry(zeta_tab, width=8, style="Form.TEntry")
        self.zeta_neff_exp = ttk.Entry(zeta_tab, width=8, style="Form.TEntry")
        self.zeta_scale_floor = ttk.Entry(zeta_tab, width=8, style="Form.TEntry")
        ttk.Label(quality_tab, text="Preset", style="Field.TLabel").grid(row=0, column=0, sticky="w", **pad)
        self.preset_box.grid(row=1, column=0, sticky="ew", **pad)
        self.apply_preset_button.grid(row=1, column=1, sticky="w", **pad)
        ttk.Label(
            quality_tab,
            text="Baseline is the defensible default. Experimental increases uncertainty handling and zeta sweeps.",
            style="Body.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=0, column=2, columnspan=2, rowspan=2, sticky="w", padx=10, pady=10)
        ttk.Label(quality_tab, text="Bootstrap", style="Field.TLabel").grid(row=2, column=0, sticky="w", **pad)
        self.bootstrap_iterations.grid(row=3, column=0, sticky="ew", **pad)
        ttk.Label(quality_tab, text="CI", style="Field.TLabel").grid(row=2, column=1, sticky="w", **pad)
        self.bootstrap_ci.grid(row=3, column=1, sticky="ew", **pad)
        ttk.Label(quality_tab, text="Seed", style="Field.TLabel").grid(row=2, column=2, sticky="w", **pad)
        self.bootstrap_seed.grid(row=3, column=2, sticky="ew", **pad)
        ttk.Label(quality_tab, text="Negative q floor", style="Field.TLabel").grid(row=2, column=3, sticky="w", **pad)
        self.negative_q_floor_fraction.grid(row=3, column=3, sticky="ew", **pad)
        ttk.Label(local_tab, text="Local Bootstrap", style="Field.TLabel").grid(row=0, column=0, sticky="w", **pad)
        self.local_bootstrap_iterations.grid(row=1, column=0, sticky="ew", **pad)
        ttk.Label(local_tab, text="Local CI", style="Field.TLabel").grid(row=0, column=1, sticky="w", **pad)
        self.local_bootstrap_ci.grid(row=1, column=1, sticky="ew", **pad)
        ttk.Label(local_tab, text="Reliable zeta", style="Field.TLabel").grid(row=0, column=2, sticky="w", **pad)
        self.reliable_min_zeta.grid(row=1, column=2, sticky="ew", **pad)
        ttk.Label(local_tab, text="Reliable R2", style="Field.TLabel").grid(row=0, column=3, sticky="w", **pad)
        self.reliable_min_r2.grid(row=1, column=3, sticky="ew", **pad)
        ttk.Label(
            local_tab,
            text="Reliable filters control which mother cells are safest for interpolation and GIS validation.",
            style="Body.TLabel",
            wraplength=640,
            justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=10, pady=(6, 10))
        ttk.Label(zeta_tab, text="zeta exponent c", style="Field.TLabel").grid(row=0, column=0, sticky="w", **pad)
        self.zeta_cov_exp.grid(row=1, column=0, sticky="ew", **pad)
        ttk.Label(zeta_tab, text="zeta exponent m", style="Field.TLabel").grid(row=0, column=1, sticky="w", **pad)
        self.zeta_mass_exp.grid(row=1, column=1, sticky="ew", **pad)
        ttk.Label(zeta_tab, text="zeta exponent s", style="Field.TLabel").grid(row=0, column=2, sticky="w", **pad)
        self.zeta_scale_exp.grid(row=1, column=2, sticky="ew", **pad)
        ttk.Label(zeta_tab, text="zeta exponent neff", style="Field.TLabel").grid(row=0, column=3, sticky="w", **pad)
        self.zeta_neff_exp.grid(row=1, column=3, sticky="ew", **pad)
        ttk.Label(zeta_tab, text="zeta scale floor", style="Field.TLabel").grid(row=2, column=0, sticky="w", **pad)
        self.zeta_scale_floor.grid(row=3, column=0, sticky="ew", **pad)
        self.sensitivity_check = ttk.Checkbutton(
            zeta_tab,
            text="Export zeta sensitivity profiles",
            variable=self.export_zeta_sensitivity,
            command=self._sync_robustness_state,
        )
        self.sensitivity_check.grid(row=3, column=2, columnspan=2, sticky="w", padx=10, pady=7)

        log_card = ttk.LabelFrame(content, text="Execution Log", style="Card.TLabelframe")
        log_card.grid(row=2, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)
        log_toolbar = ttk.Frame(log_card, style="Content.TFrame")
        log_toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        log_toolbar.columnconfigure(0, weight=1)
        ttk.Label(log_toolbar, text="Recent execution messages", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        self.clear_log_button = ttk.Button(log_toolbar, text="Clear Log", command=self._clear_log, style="Ghost.TButton")
        self.clear_log_button.grid(row=0, column=1, sticky="e")
        self.log_box = ScrolledText(
            log_card,
            wrap="word",
            font=("Consolas", 10),
            bg=self.COLORS["white"],
            fg=self.COLORS["charcoal"],
            insertbackground=self.COLORS["charcoal"],
            relief="solid",
            bd=1,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.log_box.configure(state="disabled")

    def _set_defaults(self) -> None:
        self.lines_path.insert(0, str(Path("data/test/T_Lines.shp")))
        self.boundary_path.insert(0, str(Path("data/test/extent_bh.shp")))
        self.output_dir.insert(0, str(Path("outputs/ui_run")))
        self.unit_cell.insert(0, "30")
        self.mother_cell.insert(0, "4000")
        self.divisors.insert(0, "2,4,6,8,16")
        self.q_min.insert(0, "-4")
        self.q_max.insert(0, "4")
        self.q_step.insert(0, "1")
        self.threshold.insert(0, "0.01")
        self._apply_preset_values("baseline")
        self.preset_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_selected_preset())
        self.language_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_language())
        self.workflow_mode_box.bind("<<ComboboxSelected>>", lambda _event: self._sync_workflow_mode())
        tracked_entries = [
            self.lines_path,
            self.boundary_path,
            self.output_dir,
            self.unit_cell,
            self.mother_cell,
            self.divisors,
            self.q_min,
            self.q_max,
            self.q_step,
            self.threshold,
            self.bootstrap_iterations,
            self.bootstrap_ci,
            self.bootstrap_seed,
            self.local_bootstrap_iterations,
            self.local_bootstrap_ci,
            self.reliable_min_zeta,
            self.reliable_min_r2,
            self.negative_q_floor_fraction,
            self.zeta_cov_exp,
            self.zeta_mass_exp,
            self.zeta_scale_exp,
            self.zeta_neff_exp,
            self.zeta_scale_floor,
        ]
        for entry in tracked_entries:
            entry.bind("<FocusOut>", lambda _event: self._maybe_mark_custom())
            entry.bind("<KeyRelease>", lambda _event: self._refresh_summary())
        self._sync_workflow_mode()
        self._apply_language()
        self._refresh_summary()

    def _ui_text(self, text: str) -> str:
        if self._is_spanish():
            return self.UI_ES.get(text, text)
        reverse = {v: k for k, v in self.UI_ES.items()}
        return reverse.get(text, text)

    def _is_spanish(self) -> bool:
        return self.language.get().strip().lower().startswith("espa")

    def _apply_language(self) -> None:
        self._translate_widget_tree(self.main_frame)
        self._refresh_summary()
        self.summary_status.set(self._ui_text(self.summary_status.get()))

    def _translate_widget_tree(self, widget) -> None:
        try:
            current = widget.cget("text")
            if current:
                widget.configure(text=self._ui_text(str(current)))
        except TclError:
            pass
        if isinstance(widget, ttk.Notebook):
            for tab_id in widget.tabs():
                current = widget.tab(tab_id, option="text")
                widget.tab(tab_id, text=self._ui_text(str(current)))
        for child in widget.winfo_children():
            self._translate_widget_tree(child)

    def _set_entry_value(self, entry: ttk.Entry, value: str) -> None:
        entry.delete(0, END)
        entry.insert(0, value)

    def _apply_preset_values(self, preset_name: str) -> None:
        preset = self.ROBUSTNESS_PRESETS[preset_name]
        self._set_entry_value(self.bootstrap_iterations, preset["bootstrap_iterations"])
        self._set_entry_value(self.bootstrap_ci, preset["bootstrap_ci"])
        self._set_entry_value(self.bootstrap_seed, preset["bootstrap_seed"])
        self._set_entry_value(self.local_bootstrap_iterations, preset["local_bootstrap_iterations"])
        self._set_entry_value(self.local_bootstrap_ci, preset["local_bootstrap_ci"])
        self._set_entry_value(self.reliable_min_zeta, preset["reliable_min_zeta"])
        self._set_entry_value(self.reliable_min_r2, preset["reliable_min_r2"])
        self._set_entry_value(self.negative_q_floor_fraction, preset["negative_q_floor_fraction"])
        self._set_entry_value(self.zeta_cov_exp, preset["zeta_cov_exp"])
        self._set_entry_value(self.zeta_mass_exp, preset["zeta_mass_exp"])
        self._set_entry_value(self.zeta_scale_exp, preset["zeta_scale_exp"])
        self._set_entry_value(self.zeta_neff_exp, preset["zeta_neff_exp"])
        self._set_entry_value(self.zeta_scale_floor, preset["zeta_scale_floor"])
        self.export_zeta_sensitivity.set(bool(preset["export_zeta_sensitivity"]))
        self.robustness_mode.set(preset_name)
        self._sync_robustness_state()

    def _apply_selected_preset(self) -> None:
        preset_name = self.robustness_mode.get().strip().lower()
        if preset_name == "custom":
            self._sync_robustness_state()
            return
        self._apply_preset_values(preset_name)
        self._log(f"Applied robustness preset: {preset_name}")

    def _set_widget_state(self, widget: ttk.Entry | ttk.Button, enabled: bool) -> None:
        widget.configure(state="normal" if enabled else "disabled")

    def _sync_robustness_state(self) -> None:
        aggregate_enabled = self.aggregate_mother.get()
        if not aggregate_enabled and self.export_zeta_sensitivity.get():
            self.export_zeta_sensitivity.set(False)
        if not aggregate_enabled and self.export_gis_package.get():
            self.export_gis_package.set(False)

        local_widgets = [
            self.local_bootstrap_iterations,
            self.local_bootstrap_ci,
            self.reliable_min_zeta,
            self.reliable_min_r2,
            self.zeta_cov_exp,
            self.zeta_mass_exp,
            self.zeta_scale_exp,
            self.zeta_neff_exp,
            self.zeta_scale_floor,
        ]
        for widget in local_widgets:
            self._set_widget_state(widget, aggregate_enabled)

        sensitivity_enabled = aggregate_enabled
        if not sensitivity_enabled:
            self.export_zeta_sensitivity.set(False)
        self.sensitivity_check.configure(state="normal" if sensitivity_enabled else "disabled")
        self.gis_package_check.configure(state="normal" if aggregate_enabled else "disabled")
        self._maybe_mark_custom()
        self._refresh_summary()

    def _sync_workflow_mode(self) -> None:
        if self.workflow_mode.get().strip() == "Explorer":
            self.aggregate_mother.set(True)
            self.export_gis_package.set(True)
            self.create_zip_package.set(True)
            self.export_zeta_sensitivity.set(False)
            self._apply_preset_values("baseline")
            self.robustness_card.grid_remove()
        else:
            self.robustness_card.grid()
        self._sync_robustness_state()

    def _maybe_mark_custom(self) -> None:
        current_preset = self.robustness_mode.get().strip().lower()
        if current_preset == "custom":
            return
        preset = self.ROBUSTNESS_PRESETS.get(current_preset)
        if preset is None:
            self.robustness_mode.set("custom")
            return
        current_state = {
            "bootstrap_iterations": self.bootstrap_iterations.get().strip(),
            "bootstrap_ci": self.bootstrap_ci.get().strip(),
            "bootstrap_seed": self.bootstrap_seed.get().strip(),
            "local_bootstrap_iterations": self.local_bootstrap_iterations.get().strip(),
            "local_bootstrap_ci": self.local_bootstrap_ci.get().strip(),
            "reliable_min_zeta": self.reliable_min_zeta.get().strip(),
            "reliable_min_r2": self.reliable_min_r2.get().strip(),
            "negative_q_floor_fraction": self.negative_q_floor_fraction.get().strip(),
            "zeta_cov_exp": self.zeta_cov_exp.get().strip(),
            "zeta_mass_exp": self.zeta_mass_exp.get().strip(),
            "zeta_scale_exp": self.zeta_scale_exp.get().strip(),
            "zeta_neff_exp": self.zeta_neff_exp.get().strip(),
            "zeta_scale_floor": self.zeta_scale_floor.get().strip(),
            "export_zeta_sensitivity": self.export_zeta_sensitivity.get(),
        }
        for key, preset_value in preset.items():
            if current_state[key] != preset_value:
                self.robustness_mode.set("custom")
                return

    def _read_run_config(self) -> dict[str, object]:
        bootstrap_seed_raw = self.bootstrap_seed.get().strip()
        config = {
            "lines": self.lines_path.get().strip(),
            "boundary": self.boundary_path.get().strip(),
            "out_dir": self.output_dir.get().strip(),
            "mother_cell_m": float(self.mother_cell.get().strip()),
            "divisors": _parse_csv_floats(self.divisors.get().strip()),
            "qmin": float(self.q_min.get().strip()),
            "qmax": float(self.q_max.get().strip()),
            "qstep": float(self.q_step.get().strip()),
            "threshold_m": float(self.threshold.get().strip()),
            "bootstrap_iterations": int(float(self.bootstrap_iterations.get().strip())),
            "bootstrap_ci": float(self.bootstrap_ci.get().strip()),
            "bootstrap_seed": None if not bootstrap_seed_raw else int(float(bootstrap_seed_raw)),
            "local_bootstrap_iterations": int(float(self.local_bootstrap_iterations.get().strip())),
            "local_bootstrap_ci": float(self.local_bootstrap_ci.get().strip()),
            "reliable_min_zeta": float(self.reliable_min_zeta.get().strip()),
            "reliable_min_r2": float(self.reliable_min_r2.get().strip()),
            "negative_q_floor_fraction": float(self.negative_q_floor_fraction.get().strip()),
            "zeta_exponents": (
                float(self.zeta_cov_exp.get().strip()),
                float(self.zeta_mass_exp.get().strip()),
                float(self.zeta_scale_exp.get().strip()),
                float(self.zeta_neff_exp.get().strip()),
            ),
            "zeta_scale_floor": float(self.zeta_scale_floor.get().strip()),
            "aggregate_mother": self.aggregate_mother.get(),
            "export_gis_package": self.export_gis_package.get(),
            "create_zip_package": self.create_zip_package.get(),
            "export_zeta_sensitivity": self.export_zeta_sensitivity.get(),
            "language": self.language.get(),
            "preset": self.robustness_mode.get().strip().lower(),
        }
        return config

    def _validate_run_config(self, config: dict[str, object]) -> None:
        qstep = float(config["qstep"])
        qmax = float(config["qmax"])
        qmin = float(config["qmin"])
        bootstrap_iterations = int(config["bootstrap_iterations"])
        local_bootstrap_iterations = int(config["local_bootstrap_iterations"])
        bootstrap_ci = float(config["bootstrap_ci"])
        local_bootstrap_ci = float(config["local_bootstrap_ci"])
        reliable_min_zeta = float(config["reliable_min_zeta"])
        reliable_min_r2 = float(config["reliable_min_r2"])
        negative_q_floor_fraction = float(config["negative_q_floor_fraction"])
        zeta_exponents = tuple(config["zeta_exponents"])
        zeta_scale_floor = float(config["zeta_scale_floor"])
        aggregate_mother = bool(config["aggregate_mother"])
        export_gis_package = bool(config["export_gis_package"])
        export_zeta_sensitivity = bool(config["export_zeta_sensitivity"])

        if qstep <= 0:
            raise ValueError("q-step debe ser > 0.")
        if qmax <= qmin:
            raise ValueError("q-max debe ser mayor que q-min.")
        if bootstrap_iterations < 0:
            raise ValueError("Bootstrap Iterations debe ser >= 0.")
        if local_bootstrap_iterations < 0:
            raise ValueError("Local Bootstrap debe ser >= 0.")
        if not 0.0 < bootstrap_ci < 1.0:
            raise ValueError("Bootstrap CI debe ser > 0 y < 1.")
        if not 0.0 < local_bootstrap_ci < 1.0:
            raise ValueError("Local Bootstrap CI debe ser > 0 y < 1.")
        if reliable_min_zeta < 0:
            raise ValueError("Reliable zeta min debe ser >= 0.")
        if not 0.0 <= reliable_min_r2 <= 1.0:
            raise ValueError("Reliable R2 debe estar entre 0 y 1.")
        if negative_q_floor_fraction < 0:
            raise ValueError("Negative q floor debe ser >= 0.")
        if any(v < 0 for v in zeta_exponents):
            raise ValueError("Los exponentes de zeta deben ser >= 0.")
        if not 0.0 <= zeta_scale_floor <= 1.0:
            raise ValueError("zeta scale floor debe estar entre 0 y 1.")
        if export_zeta_sensitivity and not aggregate_mother:
            raise ValueError("zeta sensitivity requiere Aggregate to mother cell outputs.")
        if export_gis_package and not aggregate_mother:
            raise ValueError("GIS GeoPackage requiere Aggregate to mother cell outputs.")

    def _estimate_run_cost(self, config: dict[str, object]) -> tuple[int, str]:
        q_count = int(np.floor((float(config["qmax"]) - float(config["qmin"])) / float(config["qstep"]))) + 1
        scale_count = len(list(config["divisors"])) + 1
        profiles = 5 if bool(config["export_zeta_sensitivity"]) else 1
        bootstrap_total = max(int(config["bootstrap_iterations"]), 1)
        local_bootstrap_total = max(int(config["local_bootstrap_iterations"]), 1)
        cost_score = q_count * scale_count * (bootstrap_total + profiles * local_bootstrap_total)
        if cost_score >= 5000:
            label = "high"
        elif cost_score >= 1200:
            label = "medium"
        else:
            label = "low"
        return cost_score, label

    def _refresh_summary(self) -> None:
        self.summary_method.set(f"{self._ui_text(self.workflow_mode.get())} / Chhabra-Jensen")
        q_join = "a" if self._is_spanish() else "to"
        q_text = f"{self.q_min.get().strip() or '?'} {q_join} {self.q_max.get().strip() or '?'}"
        self.summary_q.set(q_text)
        outputs = [self._ui_text("Global")]
        if self.aggregate_mother.get():
            outputs.append(self._ui_text("local"))
            if self.export_gis_package.get():
                outputs.append("GIS")
            if self.create_zip_package.get():
                outputs.append("ZIP")
            if self.export_zeta_sensitivity.get():
                outputs.append(self._ui_text("zeta"))
        self.summary_outputs.set(", ".join(outputs))
        try:
            config = self._read_run_config()
            cost_score, cost_label = self._estimate_run_cost(config)
            cost_word = "Costo" if self._is_spanish() else "Cost"
            scales_word = "Escalas" if self._is_spanish() else "Scales"
            self.summary_cost.set(
                f"{self._ui_text('Preset')}: {str(config['preset']).title()}   {cost_word}: {cost_label} ({cost_score})   {scales_word}: {len(list(config['divisors'])) + 1}"
            )
        except Exception:
            self.summary_cost.set(self._ui_text("Preset: pending   Cost: incomplete config"))

    def _set_status(self, text: str) -> None:
        self.summary_status.set(self._ui_text(text))

    def _clear_log(self) -> None:
        self.log_messages.clear()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", END)
        self.log_box.configure(state="disabled")

    def _pick_lines(self) -> None:
        p = filedialog.askopenfilename(
            title="Select lines layer",
            filetypes=[("Vector", "*.shp *.gpkg *.geojson"), ("All files", "*.*")],
        )
        if p:
            self.lines_path.delete(0, END)
            self.lines_path.insert(0, p)
            self._refresh_summary()

    def _pick_boundary(self) -> None:
        p = filedialog.askopenfilename(
            title="Select boundary layer",
            filetypes=[("Vector", "*.shp *.gpkg *.geojson"), ("All files", "*.*")],
        )
        if p:
            self.boundary_path.delete(0, END)
            self.boundary_path.insert(0, p)
            self._refresh_summary()

    def _pick_output(self) -> None:
        p = filedialog.askdirectory(title="Select output directory")
        if p:
            self.output_dir.delete(0, END)
            self.output_dir.insert(0, p)
            self._refresh_summary()

    def _log(self, msg: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_messages.append(f"[{timestamp}] {msg}")
        self.log_box.configure(state="normal")
        self.log_box.insert(END, f"[{timestamp}] {msg}\n")
        self.log_box.see(END)
        self.log_box.configure(state="disabled")

    def _log_text(self) -> str:
        return "\n".join(self.log_messages) + ("\n" if self.log_messages else "")

    def run_analysis(self) -> None:
        self.run_button.config(state="disabled")
        self._set_status("Running")
        self._sync_robustness_state()
        self._log(self._ui_text("Starting MUSA run..."))
        worker = threading.Thread(target=self._run_analysis_worker, daemon=True)
        worker.start()

    def suggest_scales_from_boundary(self) -> None:
        try:
            boundary = self.boundary_path.get().strip()
            if not boundary:
                raise ValueError("Selecciona Boundary antes de sugerir escalas.")

            import geopandas as gpd

            bdf = gpd.read_file(boundary)
            if bdf.crs is None:
                raise ValueError("Boundary sin CRS definido.")
            if bdf.crs.is_geographic:
                utm = bdf.estimate_utm_crs()
                if utm is None:
                    raise ValueError("No se pudo estimar UTM para boundary.")
                bdf = bdf.to_crs(utm)

            minx, miny, maxx, maxy = bdf.total_bounds
            width = float(maxx - minx)
            height = float(maxy - miny)

            width_i = int(round(width))
            height_i = int(round(height))
            if abs(width - width_i) > 1e-6 or abs(height - height_i) > 1e-6:
                raise ValueError(
                    "El extent del boundary no es entero en metros. Revisa CRS/proyeccion para sugerencia exacta."
                )

            preferred_units = [50, 30, 25, 20, 10, 5, 1]
            valid_units = [u for u in preferred_units if (width_i % u == 0 and height_i % u == 0)]
            if not valid_units:
                raise ValueError("No hay unidad base exacta en la lista estandar (50,30,25,20,10,5,1).")

            target_mother = 4000
            preferred_divisors = [2, 4, 5, 8, 10, 16]

            target_mother = int(round(float(self.mother_cell.get().strip())))
            if target_mother <= 0:
                raise ValueError("Mother Cell target debe ser > 0.")

            gcd_wh = math.gcd(width_i, height_i)
            unit_candidates: list[tuple[int, int, int, int]] = []
            for unit in valid_units:
                exact_mothers = [m for m in range(unit, gcd_wh + 1, unit) if gcd_wh % m == 0]
                if not exact_mothers:
                    continue
                large_exact = [m for m in exact_mothers if m >= 2000]
                pool = large_exact if large_exact else exact_mothers
                best_m = min(pool, key=lambda m: abs(m - target_mother))
                div_count = sum(1 for d in preferred_divisors if best_m % d == 0)
                unit_candidates.append((abs(best_m - target_mother), -div_count, unit, best_m))

            if not unit_candidates:
                raise ValueError("No hay combinacion exacta unit/mother sin recorte para este boundary.")

            unit_candidates.sort(key=lambda t: (t[0], t[1]))
            _, neg_div_count, unit, mother_cell = unit_candidates[0]
            mode = "unit-then-mother-exact"
            expand_x = 0
            expand_y = 0

            if self.auto_expand_target.get() and target_mother % unit == 0:
                pad_x = (target_mother - (width_i % target_mother)) % target_mother
                pad_y = (target_mother - (height_i % target_mother)) % target_mother
                mother_cell = target_mother
                mode = "unit-then-mother-target-expanded"
                expand_x = pad_x
                expand_y = pad_y

            mother_units = mother_cell // unit
            exact_divisors = [d for d in preferred_divisors if mother_cell % d == 0]
            if len(exact_divisors) < 3:
                backup = [d for d in [2, 3, 4, 5, 6, 8, 10, 12, 16, 20] if mother_units % d == 0]
                exact_divisors = sorted(set(exact_divisors + backup))
            if len(exact_divisors) < 3:
                raise ValueError("No hay suficientes divisores exactos para la celda madre sugerida.")

            self.unit_cell.delete(0, END)
            self.unit_cell.insert(0, str(unit))
            self.mother_cell.delete(0, END)
            self.mother_cell.insert(0, str(mother_cell))
            self.divisors.delete(0, END)
            self.divisors.insert(0, ",".join(str(d) for d in exact_divisors))

            preview_res = [mother_cell / d for d in exact_divisors]
            nx = width / mother_cell
            ny = height / mother_cell
            self._log(
                f"Boundary {Path(boundary).name}: width={width_i}m height={height_i}m, "
                f"suggested unit={unit}m, suggested mother={mother_cell}m"
            )
            self._log(f"Suggestion mode: {mode}, no-crop=true, divisor_score={len(exact_divisors)}")
            if mode == "unit-then-mother-target-expanded":
                self._log(
                    "Expanded frame for exact mother fit: "
                    f"dx=+{expand_x}m, dy=+{expand_y}m "
                    f"(new width={width_i + expand_x}m, new height={height_i + expand_y}m)"
                )
            self._log(f"Mother-grid count over extent: Nx={nx:.2f}, Ny={ny:.2f}")
            self._log(f"Suggested divisors: {exact_divisors}")
            self._log(f"Suggested resolutions (m): {preview_res}")
            self._refresh_summary()
        except Exception as exc:
            self._log(f"Suggest error: {exc}")
            messagebox.showerror("Suggest Scales Error", str(exc))

    def _run_analysis_worker(self) -> None:
        try:
            config = self._read_run_config()
            self._validate_run_config(config)
            cost_score, cost_label = self._estimate_run_cost(config)
            self.root.after(
                0,
                lambda: self._log(
                    "Robustness mode="
                    f"{config['preset']} cost={cost_label} score={cost_score} "
                    f"aggregate={config['aggregate_mother']} gis={config['export_gis_package']} "
                    f"zip={config['create_zip_package']} "
                    f"sensitivity={config['export_zeta_sensitivity']}"
                ),
            )

            q_values = np.arange(
                float(config["qmin"]),
                float(config["qmax"]) + 0.5 * float(config["qstep"]),
                float(config["qstep"]),
                dtype=float,
            )
            resolutions = MUSA.resolutions_from_mother_cell(
                mother_cell_m=float(config["mother_cell_m"]),
                divisors=list(config["divisors"]),
                include_mother=True,
            )

            self.root.after(0, lambda: self._log(f"Using resolutions (m): {resolutions.tolist()}"))

            analyzer = MUSA(
                data=str(config["lines"]),
                boundary=str(config["boundary"]),
                q_values=q_values,
                gis_reproject_to="auto",
            )
            result = analyzer.run_analysis(
                resolutions_m=resolutions,
                cell_length_threshold_m=float(config["threshold_m"]),
                min_r2=0.9,
                bootstrap_iterations=int(config["bootstrap_iterations"]),
                bootstrap_ci=float(config["bootstrap_ci"]),
                bootstrap_seed=config["bootstrap_seed"],
                negative_q_floor_fraction=float(config["negative_q_floor_fraction"]),
            )
            outputs = analyzer.export_cell_outputs(
                output_dir=str(config["out_dir"]),
                resolutions_m=resolutions,
                cell_length_threshold_m=float(config["threshold_m"]),
                aggregate_to_mother=bool(config["aggregate_mother"]),
                q_values=result.q,
                reliable_min_zeta=float(config["reliable_min_zeta"]),
                reliable_min_r2=float(config["reliable_min_r2"]),
                local_bootstrap_iterations=int(config["local_bootstrap_iterations"]),
                local_bootstrap_ci=float(config["local_bootstrap_ci"]),
                local_bootstrap_seed=config["bootstrap_seed"],
                negative_q_floor_fraction=float(config["negative_q_floor_fraction"]),
                zeta_exponents=tuple(config["zeta_exponents"]),
                zeta_scale_floor=float(config["zeta_scale_floor"]),
                export_zeta_sensitivity=bool(config["export_zeta_sensitivity"]),
                export_gis_package=bool(config["export_gis_package"]),
            )
            outputs["analysis_report"] = MUSA.export_analysis_report(str(config["out_dir"]), result)
            outputs["analysis_scale_diagnostics"] = MUSA.export_analysis_scale_diagnostics(
                str(config["out_dir"]), result
            )
            outputs["spectrum_fit_summary"] = write_spectrum_fit_summary(str(config["out_dir"]), result)
            outputs.update(export_analysis_plots(str(config["out_dir"]), result))
            if bool(config["aggregate_mother"]):
                outputs.update(export_mother_plots(str(config["out_dir"]), result, highlight_q=2.0))
            if bool(config["create_zip_package"]):
                zip_result = package_run_output(
                    str(config["out_dir"]),
                    run_name=f"MUSA_Run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    run_config=config,
                    execution_log=self._log_text(),
                )
                outputs["zip_package"] = zip_result["zip_path"]

            def _dimension_label(q_target: float, name: str) -> str:
                matches = np.where(np.isclose(result.q, q_target))[0]
                if matches.size == 0:
                    return f"{name}=eliminated"
                return f"{name}={result.dq[int(matches[0])]:.4f}"

            dimension_summary = "  ".join(
                [
                    _dimension_label(0.0, "D0"),
                    _dimension_label(1.0, "D1"),
                    _dimension_label(2.0, "D2"),
                ]
            )
            self.root.after(
                0,
                lambda: self._log(
                    f"R2 filter: accepted={result.accepted_count}, eliminated={result.rejected_count}, "
                    f"threshold=>{result.min_r2}"
                ),
            )
            if result.rejected_count:
                rejected_preview = ", ".join(
                    f"q={float(q):g} Dq_R2={float(r2):.6f} alpha_R2={float(alpha_r2):.6f} "
                    f"f_R2={float(f_alpha_r2):.6f}"
                    for q, r2, alpha_r2, f_alpha_r2 in zip(
                        result.rejected_q[:10],
                        result.rejected_r2[:10],
                        result.rejected_alpha_r2[:10],
                        result.rejected_f_alpha_r2[:10],
                    )
                )
                extra = "" if result.rejected_count <= 10 else f" ... +{result.rejected_count - 10} more"
                self.root.after(0, lambda: self._log(f"R2 eliminated detail: {rejected_preview}{extra}"))
            self.root.after(0, lambda: self._log(dimension_summary))
            for k, v in outputs.items():
                self.root.after(0, lambda kk=k, vv=v: self._log(f"{kk}: {vv}"))
            self.root.after(0, lambda: self._set_status("Complete"))
            self.root.after(0, lambda: messagebox.showinfo("MUSA", self._ui_text("Analysis completed successfully.")))
        except Exception as exc:  # pragma: no cover
            self.root.after(0, lambda error=exc: self._log(f"Error: {error}"))
            self.root.after(0, lambda: self._set_status("Error"))
            self.root.after(
                0,
                lambda error=exc: messagebox.showerror("MUSA Error", str(error)),
            )
        finally:
            self.root.after(0, lambda: self.run_button.config(state="normal"))
            self.root.after(0, self._refresh_summary)


def launch_interface() -> None:
    root = Tk()
    ttk.Style(root).theme_use("clam")
    MusaInterface(root)
    root.mainloop()


if __name__ == "__main__":
    launch_interface()

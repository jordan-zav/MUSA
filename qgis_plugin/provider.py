"""Processing entry points share the same workbench pipeline and recipes."""

import json

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingOutputString,
    QgsProcessingProvider,
)

from .i18n import tr
from .inputs import make_analyzer, snapshot_sources
from .native_gis import export_mother_layers
from .runtime import core
from .learning import TEXTS, default_language, help_url


class MusaProvider(QgsProcessingProvider):
    def id(self):
        return "musa"

    def name(self):
        return "MUSA"

    def longName(self):
        return tr(default_language(), "dock_title")

    def loadAlgorithms(self):
        self.addAlgorithm(AnalyzeAlgorithm())
        self.addAlgorithm(AnalyzeAlgorithm(recipe=True))
        self.addAlgorithm(ScalingSupportAlgorithm())


class AnalyzeAlgorithm(QgsProcessingAlgorithm):
    def __init__(self, recipe=False):
        super().__init__()
        self.use_recipe = recipe
        self.snapshot = None

    def name(self):
        return "run_recipe" if self.use_recipe else "analyze"

    def displayName(self):
        return tr(default_language(), "proc_recipe" if self.use_recipe else "proc_analyze")

    def group(self):
        return tr(default_language(), "proc_group")

    def groupId(self):
        return "lineaments"

    def createInstance(self):
        return AnalyzeAlgorithm(self.use_recipe)

    def shortHelpString(self):
        return tr(default_language(), "proc_help_analyze").format(url=help_url())

    def helpUrl(self):
        return help_url()

    def initAlgorithm(self, config=None):
        lang = default_language()
        self.addParameter(QgsProcessingParameterFeatureSource("LINES", tr(lang, "lbl_lineaments"), [QgsProcessing.TypeVectorLine]))
        self.addParameter(
            QgsProcessingParameterFeatureSource("BOUNDARY", tr(lang, "proc_boundary"), [QgsProcessing.TypeVectorPolygon])
        )
        self.addParameter(
            QgsProcessingParameterCrs("CRS", tr(lang, "proc_crs"), defaultValue="ProjectCrs")
        )
        if self.use_recipe:
            self.addParameter(QgsProcessingParameterFile("RECIPE", tr(lang, "proc_recipe_file"), extension="json"))
        else:
            self.addParameter(
                QgsProcessingParameterNumber(
                    "MOTHER",
                    tr(lang, "proc_mother"),
                    type=QgsProcessingParameterNumber.Double,
                    defaultValue=4000.0,
                    minValue=0.001,
                )
            )
            self.addParameter(
                QgsProcessingParameterString("DIVISORS", tr(lang, "proc_divisors"),
                    defaultValue=",".join(str(v) for v in core()[1]().divisors))
            )
            self.addParameter(QgsProcessingParameterNumber(
                "RESOLUTION", tr(lang, "lbl_resolution"),
                type=QgsProcessingParameterNumber.Double, defaultValue=0, minValue=0))
            for key, label_key, value in (
                ("Q_MIN", "proc_q_min", 0),
                ("Q_MAX", "proc_q_max", 4),
                ("Q_STEP", "proc_q_step", 1),
                ("MIN_R2", "lbl_min_r2", 0.9),
            ):
                self.addParameter(
                    QgsProcessingParameterNumber(
                        key, tr(lang, label_key), type=QgsProcessingParameterNumber.Double, defaultValue=value
                    )
                )
            for key, label, default in (
                ("LOCAL", tr(lang, "proc_local"), True),
                ("STRUCTURAL", tr(lang, "proc_structural"), True),
                ("NETWORK", tr(lang, "proc_network"), False),
                ("PLOTS", tr(lang, "proc_plots"), True),
                ("CLASSIC_COMPARISON", TEXTS[lang]["classic"], False),
            ):
                self.addParameter(QgsProcessingParameterBoolean(key, label, defaultValue=default))
        self.addParameter(QgsProcessingParameterFolderDestination("OUTPUT", tr(lang, "proc_output")))
        self.addOutput(QgsProcessingOutputString("MANIFEST", tr(lang, "proc_manifest")))

    def prepareAlgorithm(self, parameters, context, feedback):
        try:
            lang = default_language()
            _, RunConfig, _ = core()
            if self.use_recipe:
                from pathlib import Path

                self.config = RunConfig.from_recipe(
                    json.loads(Path(self.parameterAsFile(parameters, "RECIPE", context)).read_text(encoding="utf-8"))
                )
            else:
                self.config = RunConfig(
                    mother_cell_m=self.parameterAsDouble(parameters, "MOTHER", context),
                    scaling_resolution_m=self.parameterAsDouble(parameters, "RESOLUTION", context),
                    divisors=tuple(
                        float(v.strip()) for v in self.parameterAsString(parameters, "DIVISORS", context).split(",")
                    ),
                    q_min=self.parameterAsDouble(parameters, "Q_MIN", context),
                    q_max=self.parameterAsDouble(parameters, "Q_MAX", context),
                    q_step=self.parameterAsDouble(parameters, "Q_STEP", context),
                    min_r2=self.parameterAsDouble(parameters, "MIN_R2", context),
                    local=self.parameterAsBool(parameters, "LOCAL", context),
                    structural=self.parameterAsBool(parameters, "STRUCTURAL", context),
                    network=self.parameterAsBool(parameters, "NETWORK", context),
                    plots=self.parameterAsBool(parameters, "PLOTS", context),
                    classic_comparison=self.parameterAsBool(parameters, "CLASSIC_COMPARISON", context),
                ).validate()
            if self.config.q_min < 0:
                feedback.pushWarning(tr(lang, "note_neg_q"))
            self.snapshot = snapshot_sources(
                self.parameterAsSource(parameters, "LINES", context),
                self.parameterAsSource(parameters, "BOUNDARY", context),
                self.parameterAsCrs(parameters, "CRS", context),
                context.transformContext(),
                cancelled=feedback.isCanceled,
            )
            return True
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc

    def processAlgorithm(self, parameters, context, feedback):
        from pathlib import Path

        try:
            _, _, execute = core()
            output = self.parameterAsString(parameters, "OUTPUT", context)
            execute(
                make_analyzer(self.snapshot, self.config), self.config, output,
                source_info=self.snapshot["info"], cancelled=feedback.isCanceled,
                progress=lambda value, message: (feedback.setProgress(value), feedback.pushInfo(message)),
                gis_exporter=export_mother_layers,
            )
            return {"OUTPUT": output, "MANIFEST": str(Path(output) / "run_manifest.json")}
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc


class ScalingSupportAlgorithm(QgsProcessingAlgorithm):
    """Independent assessment, including datasets rejected by legacy R2 gates."""

    def name(self):
        return "scaling_support"

    def displayName(self):
        return tr(default_language(), "proc_scaling")

    def group(self):
        return tr(default_language(), "proc_group")

    def groupId(self):
        return "lineaments"

    def createInstance(self):
        return ScalingSupportAlgorithm()

    def shortHelpString(self):
        return tr(default_language(), "proc_help_scaling").format(url=help_url())

    def helpUrl(self):
        return help_url()

    def initAlgorithm(self, config=None):
        lang = default_language()
        self.addParameter(QgsProcessingParameterFeatureSource("LINES", tr(lang, "lbl_lineaments"), [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterFeatureSource("BOUNDARY", tr(lang, "proc_boundary"), [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterCrs("CRS", tr(lang, "proc_crs"), defaultValue="ProjectCrs"))
        self.addParameter(QgsProcessingParameterString("SCALES", tr(lang, "proc_scales"), defaultValue="", multiLine=True))
        for key, label_key, value in (
            ("RESOLUTION", "proc_res_decl", 0),
            ("Q_MIN", "proc_q_min", 0),
            ("Q_MAX", "proc_q_max", 2),
            ("Q_STEP", "proc_q_step", 1),
        ):
            self.addParameter(QgsProcessingParameterNumber(key, tr(lang, label_key), type=QgsProcessingParameterNumber.Double, defaultValue=value))
        self.addParameter(QgsProcessingParameterNumber("NULL_REPLICATES", tr(lang, "proc_null_reps"), type=QgsProcessingParameterNumber.Integer, defaultValue=0, minValue=0, maxValue=9999))
        self.addParameter(QgsProcessingParameterEnum(
            "RENYI_ORDER_POLICY", tr(lang, "lbl_order_policy"),
            options=[tr(lang, "policy_legacy_block"), tr(lang, "policy_inform_q0_q2")], defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            "NULL_TAIL", tr(lang, "proc_null_tail"),
            options=[tr(lang, "tail_upper"), tr(lang, "tail_two_sided")], defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            "COARSE_TRIM", tr(lang, "proc_coarse_trim"),
            type=QgsProcessingParameterNumber.Double, defaultValue=0, minValue=0, maxValue=1e6))
        self.addParameter(QgsProcessingParameterNumber("SEED", tr(lang, "lbl_seed"), type=QgsProcessingParameterNumber.Integer, defaultValue=42, minValue=0))
        self.addParameter(QgsProcessingParameterBoolean(
            "CLASSIC_COMPARISON", TEXTS[lang]["classic"], defaultValue=False))
        self.addParameter(QgsProcessingParameterFolderDestination("OUTPUT", tr(lang, "proc_output")))
        self.addOutput(QgsProcessingOutputString("REPORT", tr(lang, "proc_report")))

    def prepareAlgorithm(self, parameters, context, feedback):
        try:
            lang = default_language()
            _, RunConfig, _ = core()
            scales_text = self.parameterAsString(parameters, "SCALES", context).strip()
            if not scales_text:
                raise ValueError("Enter source-specific box sizes in metres.")
            self.config = RunConfig(
                q_min=self.parameterAsDouble(parameters, "Q_MIN", context),
                q_max=self.parameterAsDouble(parameters, "Q_MAX", context),
                q_step=self.parameterAsDouble(parameters, "Q_STEP", context),
                scaling_support=True,
                classic_comparison=self.parameterAsBool(parameters, "CLASSIC_COMPARISON", context),
                scaling_resolution_m=self.parameterAsDouble(parameters, "RESOLUTION", context),
                scaling_scales_m=tuple(float(v.strip()) for v in scales_text.split(",")),
                scaling_null_replicates=self.parameterAsInt(parameters, "NULL_REPLICATES", context),
                renyi_order_policy=("legacy_block", "inform_q0_q2")[
                    self.parameterAsEnum(parameters, "RENYI_ORDER_POLICY", context)],
                scaling_null_tail=("upper", "two_sided")[self.parameterAsEnum(parameters, "NULL_TAIL", context)],
                scaling_coarse_trim_min_effective_q2=self.parameterAsDouble(parameters, "COARSE_TRIM", context),
                seed=self.parameterAsInt(parameters, "SEED", context),
            ).validate()
            if self.config.q_min < 0:
                feedback.pushWarning(tr(lang, "note_neg_q"))
            self.snapshot = snapshot_sources(
                self.parameterAsSource(parameters, "LINES", context),
                self.parameterAsSource(parameters, "BOUNDARY", context),
                self.parameterAsCrs(parameters, "CRS", context), context.transformContext(),
                cancelled=feedback.isCanceled)
            return True
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc

    def processAlgorithm(self, parameters, context, feedback):
        import hashlib
        from datetime import datetime, timezone
        from pathlib import Path
        # The same private package as the dock, without changing sys.path.
        try:
            from ._core.musa import scaling
            from ._core.musa import __version__
            from ._core.musa.control import check_cancelled
            check_cancelled(feedback.isCanceled)
            output = Path(self.parameterAsString(parameters, "OUTPUT", context))
            output.mkdir(parents=True, exist_ok=False)
            manifest = {"format": "musa-scaling-run", "version": 1, "software_version": __version__,
                        "started_at_utc": datetime.now(timezone.utc).isoformat(), "status": "running",
                        "source": self.snapshot["info"], "recipe": self.config.recipe()}
            manifest_path = output / "run_manifest.json"
            try:
                if self.config.classic_comparison:
                    from ._core.musa.classic import classic_box_counting, write_classic_comparison
                    comparison = classic_box_counting(make_analyzer(self.snapshot, self.config),
                                                      self.config.scaling_scales_m, cancelled=feedback.isCanceled)
                    manifest["outputs"] = write_classic_comparison(output, comparison)
                report = scaling.assess_lineament_scaling(
                    make_analyzer(self.snapshot, self.config), self.config.scaling_scales_m,
                    self.config.scaling_options(),
                    cancelled=feedback.isCanceled, progress=feedback.pushInfo)
                manifest.setdefault("outputs", {}).update(scaling.write_scaling_reports(output, [report]))
                check_cancelled(feedback.isCanceled)
                manifest["status"] = "complete"
            except Exception as exc:
                manifest.update(status="cancelled" if feedback.isCanceled() else "failed", error=str(exc))
                raise
            finally:
                manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
                manifest["files"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in output.iterdir() if path.is_file() and path.name != "run_manifest.json"}
                manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
            return {"OUTPUT": str(output), "REPORT": str(output / "scaling_support.json")}
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc

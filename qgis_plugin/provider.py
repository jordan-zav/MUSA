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

from .inputs import make_analyzer, snapshot_sources
from .native_gis import export_mother_layers
from .runtime import core


class MusaProvider(QgsProcessingProvider):
    def id(self):
        return "musa"

    def name(self):
        return "MUSA"

    def longName(self):
        return "MUSA — Multifractal Spectrum Analyzer"

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
        return "Run analysis recipe" if self.use_recipe else "Multifractal and structural analysis"

    def group(self):
        return "Lineament analysis"

    def groupId(self):
        return "lineaments"

    def createInstance(self):
        return AnalyzeAlgorithm(self.use_recipe)

    def shortHelpString(self):
        return (
            "Analyze line length at multiple scales with the shared MUSA core. "
            "Choose a projected analysis CRS in metres. Inputs can have different CRSs. "
            "Boundary uses all features. Use QGIS feature-source selection for selected lines. "
            "Output must be a new folder; temporary output is supported. "
            "Reliability describes numerical support, not geological probability. "
            "Recipes expose all workbench options, including experimental moving windows."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource("LINES", "Lineaments", [QgsProcessing.TypeVectorLine]))
        self.addParameter(
            QgsProcessingParameterFeatureSource("BOUNDARY", "Analysis boundary", [QgsProcessing.TypeVectorPolygon])
        )
        self.addParameter(
            QgsProcessingParameterCrs("CRS", "Analysis CRS (projected, metres)", defaultValue="ProjectCrs")
        )
        if self.use_recipe:
            self.addParameter(QgsProcessingParameterFile("RECIPE", "MUSA analysis recipe", extension="json"))
        else:
            self.addParameter(
                QgsProcessingParameterNumber(
                    "MOTHER",
                    "Mother cell size (m)",
                    type=QgsProcessingParameterNumber.Double,
                    defaultValue=4000.0,
                    minValue=0.001,
                )
            )
            self.addParameter(
                QgsProcessingParameterString("DIVISORS", "Internal scale divisors", defaultValue="2,4,6,8,16")
            )
            for key, label, value in (
                ("Q_MIN", "q minimum", -4),
                ("Q_MAX", "q maximum", 4),
                ("Q_STEP", "q step", 1),
                ("MIN_R2", "Minimum fit R2", 0.9),
            ):
                self.addParameter(
                    QgsProcessingParameterNumber(
                        key, label, type=QgsProcessingParameterNumber.Double, defaultValue=value
                    )
                )
            for key, label, default in (
                ("LOCAL", "Mother-cell spectra", True),
                ("STRUCTURAL", "Structural statistics", True),
                ("NETWORK", "Network statistics", False),
                ("PLOTS", "Spectrum figures", True),
            ):
                self.addParameter(QgsProcessingParameterBoolean(key, label, defaultValue=default))
        self.addParameter(QgsProcessingParameterFolderDestination("OUTPUT", "New output folder"))
        self.addOutput(QgsProcessingOutputString("MANIFEST", "Run manifest"))

    def prepareAlgorithm(self, parameters, context, feedback):
        try:
            _, RunConfig, _ = core()
            if self.use_recipe:
                from pathlib import Path

                self.config = RunConfig.from_recipe(
                    json.loads(Path(self.parameterAsFile(parameters, "RECIPE", context)).read_text(encoding="utf-8"))
                )
            else:
                self.config = RunConfig(
                    mother_cell_m=self.parameterAsDouble(parameters, "MOTHER", context),
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
                ).validate()
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
        return "Assess Renyi scaling support (experimental)"

    def group(self):
        return "Lineament analysis"

    def groupId(self):
        return "lineaments"

    def createInstance(self):
        return ScalingSupportAlgorithm()

    def shortHelpString(self):
        return (
            "Assess finite-range generalized Renyi dimensions Dq on fixed box sizes. "
            "Declare observation resolution in metres. Needs at least eight resolved scales "
            "spanning one decade; boxes above one quarter of the smaller domain extent are excluded. "
            "Compares linear, quadratic and segmented log-log fits by leave-one-scale-out prediction, "
            "reselecting the breakpoint in each training fold. Four shifted origins diagnose grid effects. "
            "Optional independent trace translations preserve shapes, lengths and orientations inside "
            "the boundary. Their Monte Carlo test concerns spatial heterogeneity, not proof of "
            "multifractality. Use zero replicates to disable, or at least 19; the minimum p is 1/(B+1). "
            "Outputs retain every q, including insufficient/unsupported fits. No best-range search. "
            "Renyi order policy defaults to the legacy spectrum veto. The optional q=0,2 warning "
            "does not veto the finite-range slope contrast; fit and curvature gates still apply. "
            "The two-sided tail gives p = min(1, 2 min(upper, lower)), minimum 2/(B+1). "
            "Coarse-end trimming (0=off) drops coarse scales with too few effective q=2 boxes "
            "on the observed map before any replicate; less than one decade left means abstention. "
            "This independent tool does not require legacy spectrum fit acceptance."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource("LINES", "Lineaments", [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterFeatureSource("BOUNDARY", "Analysis boundary", [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterCrs("CRS", "Analysis CRS (projected, metres)", defaultValue="ProjectCrs"))
        self.addParameter(QgsProcessingParameterString("SCALES", "Fixed box sizes (m; review for your data)", defaultValue="25,40,63,100,160,250,400,630"))
        for key, label, value in (
            ("RESOLUTION", "Observation resolution (m; must be declared)", 0),
            ("Q_MIN", "q minimum", 0), ("Q_MAX", "q maximum", 2),
            ("Q_STEP", "q step", 1),
        ):
            self.addParameter(QgsProcessingParameterNumber(key, label, type=QgsProcessingParameterNumber.Double, defaultValue=value))
        self.addParameter(QgsProcessingParameterNumber("NULL_REPLICATES", "Conditional trace-relocation replicates (0=off; >=19)", type=QgsProcessingParameterNumber.Integer, defaultValue=0, minValue=0, maxValue=9999))
        self.addParameter(QgsProcessingParameterEnum(
            "RENYI_ORDER_POLICY", "Renyi order policy",
            options=["Legacy: block on spectrum order", "Inform q=0,2: warning without order veto"], defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            "NULL_TAIL", "Monte Carlo tail of the D0-D2 test",
            options=["Upper tail (legacy)", "Two-sided"], defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            "COARSE_TRIM", "Coarse-end trimming: minimum effective q=2 boxes (0=off)",
            type=QgsProcessingParameterNumber.Double, defaultValue=0, minValue=0, maxValue=1e6))
        self.addParameter(QgsProcessingParameterNumber("SEED", "Random seed", type=QgsProcessingParameterNumber.Integer, defaultValue=42, minValue=0))
        self.addParameter(QgsProcessingParameterFolderDestination("OUTPUT", "New output folder"))
        self.addOutput(QgsProcessingOutputString("REPORT", "Scaling support JSON"))

    def prepareAlgorithm(self, parameters, context, feedback):
        try:
            _, RunConfig, _ = core()
            self.config = RunConfig(
                q_min=self.parameterAsDouble(parameters, "Q_MIN", context),
                q_max=self.parameterAsDouble(parameters, "Q_MAX", context),
                q_step=self.parameterAsDouble(parameters, "Q_STEP", context),
                scaling_support=True,
                scaling_resolution_m=self.parameterAsDouble(parameters, "RESOLUTION", context),
                scaling_scales_m=tuple(float(v.strip()) for v in self.parameterAsString(parameters, "SCALES", context).split(",")),
                scaling_null_replicates=self.parameterAsInt(parameters, "NULL_REPLICATES", context),
                renyi_order_policy=("legacy_block", "inform_q0_q2")[
                    self.parameterAsEnum(parameters, "RENYI_ORDER_POLICY", context)],
                scaling_null_tail=("upper", "two_sided")[self.parameterAsEnum(parameters, "NULL_TAIL", context)],
                scaling_coarse_trim_min_effective_q2=self.parameterAsDouble(parameters, "COARSE_TRIM", context),
                seed=self.parameterAsInt(parameters, "SEED", context),
            ).validate()
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
                report = scaling.assess_lineament_scaling(
                    make_analyzer(self.snapshot, self.config), self.config.scaling_scales_m,
                    self.config.scaling_options(),
                    cancelled=feedback.isCanceled, progress=feedback.pushInfo)
                manifest["outputs"] = scaling.write_scaling_reports(output, [report])
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

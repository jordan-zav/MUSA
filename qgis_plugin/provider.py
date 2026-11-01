"""Processing entry points share the same workbench pipeline and recipes."""

import json

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
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
                make_analyzer(self.snapshot, self.config),
                self.config,
                output,
                source_info=self.snapshot["info"],
                cancelled=feedback.isCanceled,
                progress=lambda value, message: (feedback.setProgress(value), feedback.pushInfo(message)),
                gis_exporter=export_mother_layers,
            )
            return {"OUTPUT": output, "MANIFEST": str(Path(output) / "run_manifest.json")}
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc

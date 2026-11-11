# Installation and execution routes

Reference for MUSA 1.2.0; the first QGIS plugin release was 1.1.0.

## Choose a route

| Goal | Install | Run |
| --- | --- | --- |
| Maps and windows in QGIS | Plugin ZIP from the matching release or source checkout | Vector > MUSA > MUSA Workbench, or Processing |
| Engine in scripts/notebooks | Python package from the repository, in a virtual environment | Import MUSA and musa.workflow functions |
| Reproduce benchmarks | Source and optional benchmarks dependencies | Validation scripts with external originals/results |

The distribution name is musa-multifractal; the Python import is musa. The built
plugin identifier is musa_qgis. These are different distribution names for the
same numerical core.

## Python from GitHub

Use Python 3.10 or later. Create and activate your own virtual environment; do
not use QGIS Python for this route.

~~~text
python -m venv .venv
~~~

Windows PowerShell:

~~~powershell
.\.venv\Scripts\Activate.ps1
~~~

Linux/macOS:

~~~sh
source .venv/bin/activate
~~~

Install the published 1.2.0 source (requires Git):

~~~text
python -m pip install "musa-multifractal[gis] @ git+https://github.com/jordan-zav/MUSA.git@v1.2.0"
~~~

For a reproducible run, record the resolved commit hash. To work with examples
and edit the source:

~~~text
git clone --branch v1.2.0 https://github.com/jordan-zav/MUSA.git
cd MUSA
python -m pip install -e ".[gis]"
~~~

The following commands assume the repository root and an active environment.
Examples added after the v1.2.0 tag require a source checkout that contains
those files. In particular, the scaling tutorial names its required generator
and reference file; the tagged package alone does not provide those additions.

| Extra | Purpose and dependencies |
| --- | --- |
| None | Point API and calculations using NumPy >=1.24, SciPy >=1.10, Matplotlib >=3.7 |
| gis | Shapely >=2.0, GeoPandas >=0.14, PyProj >=3.6 for lines, vector files, and GIS exports |
| fast | Optional Numba >=0.64 acceleration; the Python alternative remains available |
| benchmarks | GIS adapters, Pyogrio, Pillow, requests, and PyMuPDF for validation sources |

For benchmarks or development:

~~~text
python -m pip install -e ".[benchmarks]"
python -m pip install -r requirements-dev.txt
~~~

The second command also installs pytest and Ruff. It does not download author
datasets. See [extended benchmarks](EXTENDED_BENCHMARKS.md) for downloads,
licenses, and limits. Exact dependency bounds are in pyproject.toml.

## Run without QGIS

The [Python API](PYTHON_API.md) describes points, lines, and recipes. A synthetic
source example is available:

~~~text
python examples/headless_workflow.py --output outputs/headless_demo
~~~

The output folder must be new. The example opens no windows and needs no QGIS.
It produces a recipe, manifest, CSV files, spectral cache, figures, and GIS
products. Its synthetic plane has no real location. For an independent
assessment and relocation test, follow [TUTORIAL.md](TUTORIAL.md).

## QGIS

Metadata declares QGIS 3.34–3.99 compatibility; the version checked in this
documentation is 3.44.12. This range does not mean every version/system was tested.

1. Obtain the source and build the ZIP using development Python:

~~~text
python scripts/build_qgis_plugin.py
~~~

2. In QGIS, select Plugins > Manage and Install Plugins > Install from ZIP.
   Choose the new file in dist/qgis, or obtain the matching release ZIP.
3. Open Vector > MUSA > MUSA Workbench. The current panel is in English.

The ZIP bundles the core without the Tk interface. NumPy, SciPy, Shapely, and
Matplotlib must be available in QGIS Python; the plugin does not run pip
automatically. For missing modules, use the dependency manager/environment of
your QGIS distribution and restart QGIS. Installing packages in an external
virtual environment does not install them in QGIS.

See [QGIS.md](QGIS.md) for layer selection, CRS, tasks, cancellation, recipes,
and results.

## Distribution status and limits

| Route | Recorded status |
| --- | --- |
| GitHub source / pip from Git | Available; pin a release or commit |
| Python wheel from pyproject.toml | Built and installed separately in the earlier audit; a point example ran without QGIS |
| PyPI, musa-multifractal | The November 2, 2026 audit found no project; these instructions do not assume a later PyPI publication |
| Plugin ZIP 1.2.0 | Release v1.2.0 on GitHub; QGIS 3.44.12 was tested |
| Official QGIS plugin catalog | Check the catalog's version separately; the earlier audit did not establish a catalog publication |
| musa analysis command / python -m musa | Not implemented |
| musa-ui | Legacy Tk launcher; neither the QGIS interface nor a recipe runner |

Do not assume that a PyPI install command is available without checking that
distribution. The absence of a general analysis CLI does not prevent headless
use through Python or your own scripts.

Builds must respect pip isolation and the setuptools >=77 requirement in
pyproject.toml. An older setuptools with --no-build-isolation may reject the
SPDX license declaration. The wheel audit reused available scientific
dependencies on Windows/Python 3.11; it was not a clean-install matrix for all systems.

## Development checks

Run development commands from the repository root. Native check scripts use
scripts/run_qgis_python.cmd and MUSA_QGIS_ROOT for development only.

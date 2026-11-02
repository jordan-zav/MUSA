"""Consolidate reproducible evidence, scientific limits and portable delivery."""
import argparse
from collections import Counter
import csv
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import zipfile

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
import numpy as np

from extended_benchmark_inputs import RAW, sha256

STATUS = {"insufficient_information": 0, "not_supported": 1, "compatible_finite_range": 2}
LABELS = {"aland_2023": "Åland", "loviisa_2022": "Loviisa", "bristol_2019": "Bristol",
          "hatchfrac_author": "HatchFrac", "fracpaq_examples": "FracPaQ",
          "fraxet_selected": "FraXet", "analytic_control": "Cantor",
          "finite_negative_control": "Malla periódica", "hornelen_published_figure": "Hornelen / figuras"}


def csv_write(path, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def source_inventory(root, cases):
    counts = Counter(c["source"] for c in cases)
    rows = [
        dict(source="aland_2023", doi="10.5281/zenodo.7919843", article="10.5194/se-14-603-2023", status="analyzed_author_vectors", license="other-open archive metadata; author/GTK ownership retained; local research use", limit="includes subsets/modalities of the same area and two resolution variants, not independent sites"),
        dict(source="loviisa_2022", doi="10.5281/zenodo.7077846", status="analyzed_author_vectors", license="CC BY 4.0", limit="eight observation polygons; operational 0.05m resolution assumption"),
        dict(source="bristol_2019", doi="10.13020/ah7v-6n67", status="analyzed_author_matlab_graph", license="CC0 1.0", limit="source coordinate units not verified; inferred rectangular observation domain"),
        dict(source="hatchfrac_author", doi="10.17632/zhs97tsdry.1", status="analyzed_author_2d_examples", license="CC BY 4.0 Mendeley metadata", limit="existing author output examples; no author C++/MATLAB code executed; no analytical fractal target"),
        dict(source="hornelen_published_figure", doi="10.5194/adgeo-56-117-2021", status="analyzed_identified_figure_derivatives", license="CC BY 4.0 article figures, modified from Odling 1997", limit="three representations/insets of related maps, not three independent outcrops; no exact D0 target"),
        dict(source="fracpaq_examples", url="https://github.com/DaveHealy-github/FracPaQ", status="analyzed_author_repository_samples", license="MIT software/LICENSE retained; sample map origins not independently confirmed", limit="map1/map7 naming does not establish Hornelen provenance; drawing units and inferred bounds"),
        dict(source="fraxet_selected", doi="10.5281/zenodo.17069947", article="10.5194/se-17-1087-2026", status="analyzed_declared_test_subset", license="CC BY 4.0", limit="24 preselected test masks: 20 nonempty, 4 empty; two additional resolution variants; no reconstructed continuous outcrop"),
        dict(source="geocrack", doi="10.7910/DVN/E4OXHQ", article="10.1038/s41597-024-04107-0", status="metadata_only_download_blocked", license="CC0 dataset per DataCite; distinct from article license", limit="Harvard Dataverse API returned HTTP403; landing page required bot verification; no masks downloaded or analyzed"),
        dict(source="zhu_2022", doi="10.4121/14464893", article="10.1016/j.jsg.2021.104508", status="metadata_only_download_unavailable", license="CC BY-NC 4.0", limit="earlier public download attempts returned timeout/502/504; no outcrop coordinates analyzed"),
    ]
    # The publisher's Mendeley file metadata contains an authoritative SHA256.
    entries = json.loads((RAW / "extended_metadata/hatchfrac_all_files.json").read_text())
    checks = []
    provenance = json.loads((RAW / "hatchfrac/provenance.json").read_text())
    by_url = {r["content_details"]["download_url"]: r for r in entries}
    for file in provenance["files"]:
        expected = by_url[file["url"]]["content_details"]["sha256_hash"]
        actual = sha256(Path(file["path"]))
        assert actual == expected, file["path"]
        checks.append(dict(path=file["path"], author_sha256=expected, verified=True))
    (root / "hatchfrac_author_hash_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    for row in rows:
        row["processed_cases"] = counts[row["source"]]
    (root / "source_inventory.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    csv_write(root / "source_inventory.csv", rows)
    return rows


def figures(root, catalog, summaries, reports):
    out = root / "figures"
    out.mkdir(exist_ok=True)
    cmap = ListedColormap(["#ddb453", "#c66961", "#57a179"])
    names = [c["dataset_id"] for c in catalog]
    qs = list(range(-4, 5))
    matrix = np.array([[STATUS[r["status"]] for r in reports[name][0]["q_results"]] for name in names])
    fig, ax = plt.subplots(figsize=(12, max(8, .23*len(names))), constrained_layout=True)
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=2, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(len(qs)), qs)
    ax.set_yticks(range(len(names)), names, fontsize=7)
    ax.set(xlabel="q — evaluación global de Dq", title="MUSA: amarillo = insuficiente; rojo = no respaldado; verde = compatible en intervalo finito")
    fig.savefig(out / "global_q_assessments.png", dpi=145)
    plt.close(fig)
    families = list(dict.fromkeys(r["source"] for r in summaries))
    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    for index, source in enumerate(families):
        points = [r for r in summaries if r["source"] == source and r["d0"] is not None]
        for j, row in enumerate(points):
            x = index + (j/max(1, len(points)-1)-.5)*.35
            ax.scatter(x, row["d0"], color=cmap(STATUS[row["status"]]), s=28, edgecolors="#444444", linewidth=.3)
    ax.set_xticks(range(len(families)), [LABELS[v] for v in families], rotation=22, ha="right")
    ax.set(ylabel="Pendiente global D0, incluidos ajustes no respaldados", title="Resultados finitos por familia; los puntos no son validaciones de fractalidad")
    ax.grid(axis="y", alpha=.2)
    fig.savefig(out / "global_d0_by_source.png", dpi=160)
    plt.close(fig)
    chosen = ["aland_getaberget_20m_1_3_area", "loviisa_kb7", "bristol_graph", "hatchfrac_growth_7", "hornelen_fig7_map1", "fraxet_samsu19_hnn_18_58"]
    by_name = {c["dataset_id"]: c for c in catalog}
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), constrained_layout=True)
    for ax, name in zip(axes.ravel(), chosen):
        case = by_name[name]
        frame = gpd.read_file(case["input"], layer="lineaments")
        segments = [np.asarray(line.coords) for line in frame.geometry]
        ax.add_collection(LineCollection(segments, colors="#225b70", linewidths=.35))
        bounds = case["boundary_bounds"]
        ax.set(xlim=(bounds[0], bounds[2]), ylim=(bounds[1], bounds[3]), aspect="equal")
        ax.ticklabel_format(useOffset=False, style="plain")
        ax.tick_params(labelsize=6)
        ax.set_title(name+"\n"+("EPSG:3067 / m" if case["georeferenced"] else "Sin georreferencia / unidades de origen"), fontsize=9)
    fig.savefig(out / "input_networks.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    for name in ("control_periodic_grid", "control_periodic_grid_wide_range"):
        report = reports[name][0]
        curve = [r for r in report["curves"] if r["q"] == 0]
        label = "Rango inicial" if name == "control_periodic_grid" else "Rango ampliado exploratorio"
        axes[0].plot([np.log10(1/r["scale_m"]) for r in curve], [r["entropy"]/np.log(10) for r in curve], "o-", ms=3, label=label)
        x = np.log([1/r["scale_m"] for r in curve])
        y = np.array([r["entropy"] for r in curve])
        axes[1].plot([r["scale_m"] for r in curve], np.gradient(y, x), "o-", ms=3, label=label)
    axes[0].set(xlabel="log10(1/tamaño de caja)", ylabel="H0 / ln(10)", title="Una malla periódica puede aparentar escalamiento")
    axes[1].axvline(156.25, ls="--", color="#b46c24", label="Separación conocida")
    axes[1].set(xlabel="Tamaño de caja (unidades de modelo)", ylabel="Pendiente local", xscale="log", title="El intervalo ampliado detecta el cambio de régimen")
    for ax in axes:
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.savefig(out / "periodic_grid_range_sensitivity.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--archive", action="store_true")
    args = parser.parse_args()
    root = args.output
    catalog = json.loads((root / "input_catalog.json").read_text())
    summary = json.loads((root / "summary.json").read_text())
    assert not summary["failures"] and not catalog["failures"]
    assert len(summary["cases"]) == len(catalog["cases"])
    sources = source_inventory(root, catalog["cases"])
    repo = Path(__file__).resolve().parents[1]
    code_files = list((repo / "src/musa").rglob("*.py")) + list((repo / "scripts").glob("*benchmark*.py"))
    code_files += [repo / "scripts/fetch_selected_masks.py", repo / "scripts/fetch_hatchfrac_inputs.py",
                   repo / "scripts/fetch_hornelen_figures.py", repo / "scripts/resolve_extended_sources.py", repo / "pyproject.toml"]
    software = dict(source_repository=str(repo), source_hashes={str(path.relative_to(repo)): sha256(path) for path in code_files},
        package_versions={name: version(name) for name in ("numpy", "scipy", "matplotlib", "geopandas", "shapely", "pyproj", "pyogrio", "pillow", "requests", "pymupdf")},
        interpretation="local source hashes; no new release published; data remain outside plugin")
    (root / "software_manifest.json").write_text(json.dumps(software, indent=2), encoding="utf-8")
    reports, rows, spectrum_rows, residuals, representation_rows = {}, [], [], [], []
    for case in catalog["cases"]:
        folder = root / "results" / case["dataset_id"]
        report = json.loads((folder / "scaling_support.json").read_text())
        manifest = json.loads((folder / "run_manifest.json").read_text())
        independent = manifest.get("independent_mask_counts")
        if case["source"] == "hornelen_published_figure":
            from PIL import Image
            from run_extended_benchmarks import independent_mask_counts
            pixels = np.asarray(Image.open(case["metadata"]["path"]).convert("RGB"))
            left, top, right, bottom = case["metadata"]["crop_pixel_bounds"]
            pixels = pixels[top:bottom, left:right]
            independent = independent_mask_counts(pixels.mean(axis=2) < case["metadata"]["threshold"], case["scales"])
        if independent:
            q0 = manifest["global_q0"]
            representation_rows.append(dict(dataset_id=case["dataset_id"], source=case["source"],
                musa_d0=q0["d0"], musa_status=q0["status"], raster_descriptive_d0=independent["d0_slope"],
                difference=q0["d0"]-independent["d0_slope"] if q0["d0"] is not None and independent["d0_slope"] is not None else None,
                comparison="different representations/origins; descriptive difference, not an exact-reference accuracy test"))
        reports[case["dataset_id"]] = report["supports"]
        for support in report["supports"]:
            for q in support["q_results"]:
                rows.append(dict(dataset_id=case["dataset_id"], source=case["source"], support_id=support["support_id"],
                                 georeferenced=case["georeferenced"], q=q["q"], dq=q["dimension"], status=q["status"],
                                 tau=q.get("tau"), alpha=q.get("alpha"), f_alpha=q.get("f_alpha"),
                                 tau_status=q.get("observables", {}).get("tau", {}).get("status"),
                                 alpha_status=q.get("observables", {}).get("alpha", {}).get("status"),
                                 f_alpha_status=q.get("observables", {}).get("f_alpha", {}).get("status"),
                                 coverage=support["coverage"], reasons="; ".join(q["reasons"])))
                rows[-1].update(window_grid=support.get("window_grid", "global" if support["support_id"] == "global" else "bounding_box_quarters"),
                                scale_count=q.get("scale_count"), span_decades=q.get("span_decades"))
                identity = q.get("identities", {})
                if identity.get("max_error") is not None:
                    residuals.append(identity["max_error"])
        with (folder / "spectrum_summary.csv").open(encoding="utf-8-sig", newline="") as stream:
            spectrum_rows.extend(dict(dataset_id=case["dataset_id"], **row) for row in csv.DictReader(stream))
    csv_write(root / "all_supports_q.csv", rows)
    csv_write(root / "representation_comparison.csv", representation_rows)
    csv_write(root / "all_spectrum_summaries.csv", spectrum_rows)
    csv_write(root / "global_summary.csv", [{k: v for k, v in row.items() if k != "global_counts"} for row in summary["cases"]])
    figures(root, catalog["cases"], summary["cases"], reports)
    native = json.loads((root / "qgis_validation.json").read_text())
    software["qgis_bundle_sha256"] = sha256(repo / native["bundle"])
    software["qgis_version"] = native["qgis"]
    (root / "software_manifest.json").write_text(json.dumps(software, indent=2), encoding="utf-8")
    exact = json.loads((root / "geometric_cascade_validation.json").read_text())
    counts = Counter(row["status"] for row in rows)
    evidence = dict(cases=len(catalog["cases"]), source_counts=dict(Counter(c["source"] for c in catalog["cases"])),
                    not_applicable=len(catalog["not_applicable"]), supports=sum(len(v) for v in reports.values()),
                    support_q_records=len(rows), statuses=dict(counts),
                    max_available_identity_residual=max(residuals, default=None),
                    exact_geometric_core_max_error=exact["max_absolute_error"], exact_geometric_core_passed=exact["passed"],
                    qgis=native["qgis"], native_projects=len(native["projects"]),
                    native_viewer_checks=len(native["viewer_checks"]), native_processing_parity=native["processing_parity"],
                    failures=summary["failures"]+catalog["failures"])
    evidence["window_grid_statuses"] = {
        grid: dict(Counter(r["status"] for r in rows if r["window_grid"] == grid))
        for grid in sorted({r["window_grid"] for r in rows})}
    (root / "validation_summary.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    source_table = "\n".join(f"| {r['source']} | {r['processed_cases']} | {r['status']} | {r['doi'] if 'doi' in r else r['url']} |" for r in sources)
    nulls = json.loads((root / "conditional_null_results.json").read_text())
    null_text = "\n".join(f"- {r['dataset_id']}: {r['status']}; p = {r['p_value']}; p Holm (familia global) = {r['p_holm_extended_global_family']}." for r in nulls)
    report = f"""# MUSA — validación ampliada con datos publicados

Se completaron {evidence['cases']} casos procesables, {evidence['supports']} soportes globales/ventanas y {evidence['support_q_records']} evaluaciones de Dq para q de −4 a 4. Se conservaron {evidence['not_applicable']} máscaras seleccionadas vacías como no aplicables, sin reemplazarlas por otras. Cero errores de preparación o ejecución pendientes. Los casos incluyen recortes, modalidades y variantes del mismo material: no son {evidence['cases']} afloramientos independientes.

## Abrir los resultados

Abrir projects/naturales_EPSG3067.qgz para Åland y Loviisa. Los otros proyectos separan modelos, dibujos y píxeles sin georreferencia. Activar un caso a la vez; los dominios de modelo superpuestos no representan ubicaciones compartidas. Cada grupo incluye trazas, dominio y ventanas D0 con leyenda de estados. Todas las q y observables permanecen en los GeoPackage/CSV.

En MUSA, usar Open completed run y elegir results/NOMBRE_DEL_CASO para explorar Dq, tau, alpha, f(alpha), fuentes de cálculo y ventanas. El proyecto QGIS guarda capas; el visor abre sus resultados guardados por separado. Las columnas terminadas en m del software usan píxeles/unidades de modelo en los casos sin georreferencia, según input_manifest.json.

Se conservaron los cuatro cuadrantes del rectángulo exterior y se añadieron cuatro ventanas interiores solapadas para los casos georreferenciados. Los centros interiores están a 3/8 y 5/8 de cada eje, con el mismo lado de ventana, sin optimización por resultados ni cambio del umbral de cobertura. Un cuadrante de círculo tiene cobertura pi/4 ≈ 0,785, inferior al mínimo 0,8; por eso se añadió esta comparación geométrica. Las ventanas solapadas no son réplicas independientes. El informe previo se conserva en quarter_grid_scaling_support.json.

## Evidencia y límites

- Se verificó el núcleo geométrico real con 65.536 segmentos que codifican una cascada binomial 2D de pesos diádicos. Error máximo Dq/tau/alpha/f(alpha): {exact['max_absolute_error']:.3g}. Es una comprobación exacta de partición y fórmulas en una cuadrícula alineada y un intervalo finito; no certifica precisión para datos naturales ni independencia del origen de cuadrícula. La otra cascada de masas verifica entropía y referencia algebraica sin geometría.
- Los controles Cantor tienen aproximaciones finitas y errores registrados. El indicador compatible_finite_range expresa compatibilidad operacional de una observable en el intervalo solicitado; no declara fractalidad demostrada. Cada observable tiene su propio estado: Dq aceptado no garantiza alpha o f(alpha) respaldados.
- Una malla periódica obtuvo D0 = 1,846293 y compatibilidad en el rango inicial. El seguimiento exploratorio amplió el rango sin cambiar umbrales y fue rechazado por mejores modelos cuadrático/segmentado. Se conservan ambos resultados. Esta limitación impide presentar el diagnóstico como detector universal de fractalidad. Ver figures/periodic_grid_range_sensitivity.png.
- Hornelen se analizó a partir de figuras identificadas, con recortes registrados, esqueletización y unidades de píxel. Los resultados finitos no reproducen directamente el aproximadamente 1,8 de Bour/Roy: cambian representación, medida y rango. FracPaQ map1/map7 conserva su identidad de ejemplo; no se atribuye a Hornelen solo por el nombre.
- Los vectores originales de Åland/Loviisa conservan EPSG:3067 y sus polígonos de observación. Las resoluciones operacionales son supuestos explícitos, no precisiones de levantamiento verificadas; se incluyen sensibilidades por factores 2 y 4. Bristol usa un rectángulo inferido y unidades originales no verificadas. Estas diferencias están registradas y limitan la interpretación.
- FraXet usa 24 máscaras de prueba seleccionadas antes de ajustar, ocho por familia: 20 con trazas y cuatro vacías. Se verificó CRC de miembros originales y SHA256 local; no se descargó ni verificó el MD5 de todo el archivo de 2,6 GB. No se unen parches como si formasen un afloramiento continuo. Se compara conteo binario ráster con derivados de esqueletización; no son medidas idénticas.
- Se conserva longitud antes/después de unión exacta, sin snapping ni relleno de huecos. La unidad del contraste nulo es el segmento único nodificado; no se afirma que se preserve la identidad original de cada fractura.

## Contrastes nulos condicionales

Se declararon tres soportes globales antes de ajustar, con 99 réplicas solicitadas por soporte. Si q0/q2 no tienen respaldo, no se inventa p. La corrección en conditional_null_results.json cubre la familia de tres globales; la corrección de cada scaling_support.json cubre únicamente los soportes de ese archivo. No es una calibración general de tasa de falsos positivos.

{null_text}

## QGIS y verificaciones

QGIS {native['qgis']}: {len(native['projects'])} proyectos escritos y reabiertos con referencias relativas y capas válidas. Se ejercitó el visor con {len(native['viewer_checks'])} ejecuciones guardadas, cambiando dominios, ventanas y estimadores. Dos ejecuciones reales de Processing compararon cada curva/estado con la ruta Python; los errores máximos están en qgis_validation.json. Perfil normal sin modificar. Las capturas provienen de Qt/QGIS nativo en una ventana de prueba aislada, no de una sesión interactiva del usuario.

El conjunto dirigido de pruebas de adaptadores, controles, escalamiento y productos espectrales se registra en TESTS.md. No se publica una release ni se modifica el paquete instalable por añadir estos datos.

## Inventario

| Fuente | Casos procesados | Estado | Identificador |
| --- | ---: | --- | --- |
{source_table}

GeoCrack: se obtuvo metadato de DataCite, con licencia de dataset CC0; Harvard Dataverse respondió 403 y exigió verificación antibot. No se sorteó esa verificación ni se procesaron imágenes. Zhu: las coordenadas siguen sin descargarse por indisponibilidad de endpoints; no se afirma haber procesado esos afloramientos. Los documentos y derivados de esta entrega son para revisión local, con atribución y permisos originales conservados.

## Bibliografía y comparación de métodos

- [Ovaskainen et al., 2023](https://doi.org/10.5194/se-14-603-2023): datos naturales de varias escalas y límites de observación; no ofrece Dq exactos para cada ventana.
- [Bour et al., 2002](https://doi.org/10.1029/2001JB000176): normalización de mapas de Hornelen y dimensión de correlación; no equivale automáticamente a una medida de longitud de líneas sobre cualquier recorte.
- [Roy et al., 2007](https://doi.org/10.1029/2006JB004582): técnica box-counting mejorada y tratamiento de cortes de escala; los mapas no tienen resolución ilimitada.
- [Sahu y Roy, 2021](https://doi.org/10.5194/adgeo-56-117-2021): procedencia explícita de las figuras naturales utilizadas.
- [De Souza y Rostirolla, 2011](https://doi.org/10.1016/j.cageo.2010.09.001): controles IFS/Cantor y sensibilidad a muestreo/interpolación, especialmente en momentos negativos. No se ejecutó su programa MATLAB ni se afirma reproducir toda su publicación.
- [Berkowitz y Hadad, 1997](https://doi.org/10.1029/97JB00304): análisis de mapas naturales y sintéticos; contexto metodológico, no coordenadas descargadas en esta entrega.
- [Ouillon et al., 1995](https://doi.org/10.5194/npg-2-158-1995): dependencia del rango de escalas y anisotropía; no se implementó su algoritmo de wavelets anisotrópicas como parte de esta suite.
- [Fatihi et al., 2026](https://doi.org/10.5194/se-17-1087-2026): anotaciones y efectos de representación; FraXet no trae dimensiones fractales exactas de referencia.

## Reproducir

Usar DEVRESOURCES_RUN.cmd desde el repositorio. Scripts principales: discover_extended_benchmarks.py, fetch_extended_benchmarks.py, resolve_extended_sources.py, fetch_selected_masks.py, fetch_hatchfrac_inputs.py, fetch_hornelen_figures.py, extended_benchmark_inputs.py, run_extended_benchmarks.py, qgis_extended_benchmarks.py y report_extended_benchmarks.py. Cada preparación debe usar una carpeta nueva; el ejecutor permite reanudar casos completados con entradas coincidentes. Los originales se conservan en D:/DevResources/Shared/MUSA-benchmarks. Los datos no se incluyen en el plugin.

Ejecutar add_interior_benchmark_windows.py después del análisis inicial y antes de QGIS para reproducir la comparación con ventanas interiores. representation_comparison.csv contrasta descripciones ráster y vectoriales de las máscaras/figuras, sin equiparar ambas medidas.
"""
    (root / "README.md").write_text(report, encoding="utf-8")
    sources_out = root / "sources"
    sources_out.mkdir(exist_ok=True)
    for source in ("aland_zenodo", "loviisa", "bristol", "hatchfrac", "fracpaq", "fraxet_selected", "hornelen_sahu_2021"):
        provenance = RAW / source / "provenance.json"
        if provenance.exists():
            shutil.copy2(provenance, sources_out / (source+"_provenance.json"))
    for name in ("geocrack_datacite.json", "bristol_doi.json", "aland_zenodo.json", "loviisa.json", "fraxet.json"):
        shutil.copy2(RAW / "extended_metadata" / name, sources_out / name)
    shutil.copy2(RAW / "fracpaq/original/LICENSE", sources_out / "FracPaQ_LICENSE.txt")
    (root / "prior_suite.json").write_text(json.dumps(dict(path="D:/DevResources/Sessions/MUSA-author-benchmarks-20261102_135150", scope="earlier 20 author-map/control cases, not rerun or counted as additional independent sites here"), indent=2), encoding="utf-8")
    print("REPORT COMPLETE", evidence, flush=True)
    if args.archive:
        archive_delivery(root)


def archive_delivery(root):
    catalog = json.loads((root / "input_catalog.json").read_text())
    verified_files = 0
    for case in catalog["cases"]:
        assert sha256(Path(case["input"])) == case["input_sha256"], case["dataset_id"]
        folder = root / "results" / case["dataset_id"]
        manifest = json.loads((folder / "run_manifest.json").read_text())
        assert manifest["status"] == "complete"
        for name, expected in manifest["files"].items():
            assert sha256(folder / name) == expected, (case["dataset_id"], name)
            verified_files += 1
    (root / "integrity_validation.json").write_text(json.dumps(dict(input_cases=len(catalog["cases"]),
        result_files_verified=verified_files, status="passed", method="compare current file SHA256 against input and completed-run manifests"), indent=2), encoding="utf-8")
    def included(path):
        return path.is_file() and not path.name.endswith("~") and path.name != "delivery_hashes.json"
    hashes = {str(path.relative_to(root)): sha256(path) for path in sorted(root.rglob("*")) if included(path)}
    (root / "delivery_hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    target = root.with_suffix(".zip")
    if target.exists():
        raise ValueError("Preserve existing delivery; choose a new archive name")
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if included(path) or path.name == "delivery_hashes.json":
                archive.write(path, path.relative_to(root.parent))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(digest+"  "+target.name+"\n", encoding="ascii")
    print("DELIVERY", target, target.stat().st_size, digest, flush=True)


if __name__ == "__main__":
    main()

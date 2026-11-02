"""Bundle an illustrated guide, public example, saved results and plugin ZIP.

The caller must choose inputs that may be shared. Only an explicit allowlist of
documentation and example files is archived; temporary profiles are excluded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def package(root, run, plugin):
    for suffix in ('docx', 'pdf', 'html', 'md'):
        if not (root / f'Manual_MUSA_QGIS_es.{suffix}').is_file():
            raise ValueError(f'Missing manual format: {suffix}')
    manifest = json.loads((run / 'run_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('status') != 'complete':
        raise ValueError('Only completed example runs can be bundled')
    destination = root / 'example' / 'completed_run'
    shutil.copytree(run, destination, dirs_exist_ok=True)
    for path in run.rglob('*'):
        if path.is_file() and digest(path) != digest(destination / path.relative_to(run)):
            raise ValueError(f'Example copy differs: {path.name}')
    software = root / 'software'
    software.mkdir(exist_ok=True)
    shutil.copy2(plugin, software / 'MUSA_QGIS_1.0.0.zip')
    (root / 'LEEME.txt').write_text(
        'MUSA 1.0.0 experimental — manual y ejemplo\n\n'
        '1. Extraer el ZIP completo.\n'
        '2. Leer Manual_MUSA_QGIS_es.pdf o abrir el Word editable.\n'
        '3. Instalar software/MUSA_QGIS_1.0.0.zip desde el gestor de complementos de QGIS.\n'
        '4. Guardar el proyecto abierto y reiniciar QGIS si había una copia anterior cargada.\n'
        '5. Abrir example/MUSA_Aland.qgz para cargar líneas y dominio.\n'
        '6. En MUSA, seleccionar las capas y cargar example/recipe.json. Elegir una carpeta padre existente.\n'
        '7. Para inspeccionar sin recalcular: Results > Open completed run > example/completed_run.\n\n'
        'Las rutas registradas en el manifiesto conservan la ubicación original de la ejecución; '
        'las copias de los archivos y sus hashes se conservan intactos. El visor abre la carpeta seleccionada.\n'
        'Los datos mantienen las condiciones de su fuente, independientes de la licencia GPL del software. '
        'Ver example/SOURCE.txt y las referencias del manual. No son datos privados.\n'
        'Las capturas originales están en screenshots. Los perfiles temporales de QA no forman parte de este ZIP.\n',
        encoding='utf-8')
    (root / 'example' / 'SOURCE.txt').write_text(
        'Red publicada de fracturas de Aland, Ovaskainen y colaboradores.\n'
        'Dataset: https://doi.org/10.5281/zenodo.7919843\n'
        'Artículo: https://doi.org/10.5194/se-14-603-2023\n'
        'Caso: aland_getaberget_20m_1_3_area; EPSG:3067.\n'
        'Preparación: recorte al dominio y unión geométrica exacta; 610 segmentos.\n'
        'La resolución de 0,05 m es una hipótesis operacional, no precisión medida de los autores.\n'
        'El archivo público figura como other-open; el README de autores conserva titularidad GTK/autores. '
        'La licencia del software MUSA no reemplaza las condiciones de los datos.\n', encoding='utf-8')
    allowed = [*root.glob('Manual_MUSA_QGIS_es.*'), root / 'LEEME.txt']
    for name in ('capture_validation.json', 'QA.md'):
        if (root / name).is_file():
            allowed.append(root / name)
    for directory in ('screenshots', 'example', 'software'):
        allowed.extend(p for p in (root / directory).rglob('*') if p.is_file())
    hashes = {p.relative_to(root).as_posix(): digest(p) for p in sorted(allowed)}
    checksums = root / 'checksums.json'
    checksums.write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    allowed.append(checksums)
    target = root.parent / (root.name + '.zip')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(allowed):
            archive.write(path, path.relative_to(root).as_posix())
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive integrity check failed')
    print(json.dumps({'zip': str(target), 'sha256': digest(target), 'files': len(allowed)}, indent=2))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manual_root', type=Path)
    parser.add_argument('completed_run', type=Path)
    parser.add_argument('plugin', type=Path)
    args = parser.parse_args()
    package(args.manual_root.resolve(), args.completed_run.resolve(), args.plugin.resolve())

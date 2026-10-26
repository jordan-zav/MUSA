"""QGIS default styles embedded in the standard layer_styles table."""
from pathlib import Path
import sqlite3


def embed_styles(path):
    styles = Path(__file__).parent / "assets" / "styles"
    with sqlite3.connect(path) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS layer_styles (
            id INTEGER PRIMARY KEY AUTOINCREMENT, f_table_catalog TEXT,
            f_table_schema TEXT, f_table_name TEXT, f_geometry_column TEXT,
            styleName TEXT, styleQML TEXT, styleSLD TEXT, useAsDefault BOOLEAN,
            description TEXT, owner TEXT, ui TEXT,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        for layer in ("window_spectra", "window_shifted_spectra", "structural_candidates", "topology_controls", "potential_relations", "interaction_search_zones", "trap_candidates", "candidate_centered_spectra", "candidate_shifted_spectra"):
            found = db.execute('SELECT column_name FROM gpkg_geometry_columns WHERE table_name=?', (layer,)).fetchone()
            if found is None:
                continue
            style_layer = 'window_spectra' if layer in ('candidate_centered_spectra', 'candidate_shifted_spectra', 'window_shifted_spectra') else layer
            qml = (styles / (style_layer + '.qml')).read_text(encoding='utf-8')
            geom = found[0]
            db.execute('DELETE FROM layer_styles WHERE f_table_name=?', (layer,))
            db.execute('''INSERT INTO layer_styles
                (f_table_catalog,f_table_schema,f_table_name,f_geometry_column,
                 styleName,styleQML,styleSLD,useAsDefault,description,owner,ui)
                VALUES ('','',?,?,?,?,'',1,?,'MUSA','')''',
                (layer, geom, 'MUSA_'+layer, qml, 'Structural geometry; not a permeability score.'))

        # Keep a selectable weighted comparison without duplicating geometries.
        if "evidence_class_w" in {r[1] for r in db.execute("PRAGMA table_info(trap_candidates)")}:
            geom = db.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name='trap_candidates'").fetchone()[0]
            qml = (styles / 'trap_candidates_zeta.qml').read_text(encoding='utf-8')
            db.execute("""INSERT INTO layer_styles
                (f_table_catalog,f_table_schema,f_table_name,f_geometry_column,
                 styleName,styleQML,styleSLD,useAsDefault,description,owner,ui)
                VALUES ('','','trap_candidates',?,'MUSA_trap_candidates_zeta',?,'',0,
                        'Zeta weighted comparison; confidence and grid stability remain separate.','MUSA','')""", (geom,qml))

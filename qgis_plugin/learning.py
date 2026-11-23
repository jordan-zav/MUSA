"""Local learning reader: canonical Markdown also used by Processing help."""

from html import escape
from pathlib import Path
import re


TEXTS = {
    "en": {"learn": "Learn", "classic": "Classic box counting (comparison only)",
           "warning": "High R² alone leaves scaling unvalidated.",
           "musa": "Global MUSA D0", "interval": "Retained interval", "absent": "Assessment unavailable",
           "compatible_finite_range": "Compatible", "not_supported": "Not supported",
           "insufficient_information": "Insufficient information", "scales": "scales",
           "all_scales": "All input scales", "language": "Learning and comparison language"},
    "es": {"learn": "Fundamentos", "classic": "Box counting clásico (solo comparación)",
           "warning": "Un R² alto por sí solo deja sin validar el escalamiento.",
           "musa": "D0 global de MUSA", "interval": "Intervalo retenido", "absent": "Diagnóstico ausente",
           "compatible_finite_range": "Compatible", "not_supported": "No respaldado",
           "insufficient_information": "Información insuficiente", "scales": "escalas",
           "all_scales": "Todas las escalas de entrada", "language": "Idioma de fundamentos y comparación"},
}


def default_language():
    from qgis.PyQt.QtCore import QLocale, QSettings
    settings = QSettings()
    locale = (str(settings.value("locale/userLocale", "en"))
              if settings.value("locale/overrideFlag", False, type=bool) else QLocale().name())
    return "es" if locale.lower().startswith("es") else "en"


def source_path(language):
    filename = "KNOWLEDGE_BASE.es.md" if language == "es" else "KNOWLEDGE_BASE.md"
    bundled = Path(__file__).parent / "knowledge" / filename
    return bundled if bundled.is_file() else Path(__file__).resolve().parents[1] / "docs" / filename


def learning_html(source):
    """Render the chapter's deliberately small Markdown subset without extras.

    Keeping this renderer free of Qt lets the packaging script produce local
    HTML help from exactly the same sources read by Workbench.
    """
    def inline(value):
        value = escape(value)
        # Only these four literal tags are allowed in the chapter's math subset.
        value = re.sub(r'&lt;(/?(?:sup|sub))&gt;', r'<\1>', value)
        value = re.sub(r"!\[([^]]*)\]\(([^)]+)\)", r'<img alt="\1" src="\2">', value)
        # DOI URLs commonly contain a parenthesized publication year.
        return re.sub(r"\[([^]]*)\]\(((?:[^()\s]|\([^()]*\))+)\)", r'<a href="\2">\1</a>', value)

    blocks = []
    for block in source.strip().split("\n\n"):
        if block.startswith("#"):
            title = re.match(r"(#+) (.*)", block)
            level = len(title[1])
            blocks.append(f"<h{level}>{inline(title[2])}</h{level}>")
        elif block.startswith('::math '):
            blocks.append('<p class="formula" align="center">'
                          + inline(block[7:].replace('\n', ' ')) + '</p>')
        elif re.match(r"(?:Figura|Figure) \d+\. ", block):
            blocks.append('<p class="figure-caption" align="center"><small>'
                          + inline(block.replace("\n", " ")) + '</small></p>')
        elif block.startswith("!["):
            blocks.append('<p class="figure" align="center">' + inline(block) + '</p>')
        elif block.startswith("- ") or re.match(r"1\. ", block):
            ordered = not block.startswith("- ")
            tag = "ol" if ordered else "ul"
            items = [re.sub(r"^(?:- |\d+\. )", "", line) for line in block.splitlines()]
            blocks.append(f"<{tag}>" + "".join(f"<li>{inline(item)}</li>" for item in items) + f"</{tag}>")
        else:
            blocks.append("<p>" + inline(block.replace("\n", " ")) + "</p>")
    return ('<!doctype html><html><head><meta charset="utf-8">'
            '<style>body{font-family:sans-serif;margin:16px;line-height:1.5;}'
            'p,li{margin-bottom:12px}h1,h2,h3{margin-top:28px;margin-bottom:14px;}'
            '.formula{margin-top:18px;margin-bottom:18px;line-height:150%;}'
            '.figure{line-height:100%;margin-bottom:4px}.figure-caption{margin-top:4px;margin-bottom:22px;color:#46515b;}'
            'img{max-width:100%;height:auto}</style></head><body>'
            + "\n".join(blocks) + "</body></html>")


def image_display_size(viewport_width, source_width, source_height, document_margin=4):
    """Qt ignores CSS max-width; use source dimensions and actual text-column width."""
    if source_width <= 0 or source_height <= 0:
        return None
    available = max(1., viewport_width - 2 * document_margin - 32)
    width = min(source_width, available, 760.)
    return width, width * source_height / source_width


def help_url():
    from qgis.PyQt.QtCore import QUrl
    return QUrl.fromLocalFile(str(source_path(default_language()).with_suffix(".html"))).toString()


def comparison_text(folder, language):
    import json
    text = TEXTS[language]
    classic_path = Path(folder) / "classic_comparison.json"
    if not classic_path.is_file():
        return ""
    comparison = json.loads(classic_path.read_text(encoding="utf-8"))["comparison"]
    def number(value):
        return "—" if value is None else f"{value:.5g}"

    scales = comparison["scales_m"]
    lines = [text["classic"], f"D_BC = {number(comparison['dimension'])} · R² = {number(comparison['r2'])}",
             f"{text['all_scales']}: {min(scales):g}–{max(scales):g} m ({len(scales)} {text['scales']})",
             text["warning"]]
    assessment = Path(folder) / "scaling_support.json"
    row, used = None, []
    if assessment.is_file():
        report = json.loads(assessment.read_text(encoding="utf-8"))
        support = next((s for s in report["supports"] if s["support_id"] == "global"), None)
        if support:
            row = next((r for r in support["q_results"] if r["q"] == 0), None)
            used = support["used_scales_m"]
    lines.append(f"{text['musa']}: " + (f"{number(row.get('dimension'))} · {text[row['status']]}"
                                      if row else text["absent"]))
    lines.append(text["interval"] + ": " +
                 (f"{min(used):g}–{max(used):g} m ({len(used)} {text['scales']})" if used else "—"))
    return "\n".join(lines)


def relocation_text(null):
    """Display the global conditional test together with its Monte Carlo resolution."""
    requested = null.get('replicates_requested', 0)
    if not requested:
        return ''
    valid = len(null.get('values', []))
    if null.get('status') != 'complete':
        return f'Global trace relocation: no p value; support or placement requirements unmet ({valid}/{requested} replicates).'
    text = (f"Global trace relocation: p={null['p_value']:.4g}; Holm p={null.get('p_holm', null['p_value']):.4g}; "
            f"{valid}/{requested} replicates; minimum raw p={null['minimum_p']:.4g}.")
    if null.get('resolution_sufficient_for_family_at_0_05') is False:
        text += ' Too few replicates to resolve rejection at 0.05 for this family.'
    return text

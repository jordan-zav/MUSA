"""Build the illustrated user guide as DOCX, HTML and portable Markdown.

Requires python-docx and Pillow in the documentation environment. PDF conversion
is a separate step, for example with an existing LibreOffice installation.
"""
import argparse
from html import escape
from pathlib import Path
import re
import shutil

from docx import Document
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor
from PIL import Image


def inline(text):
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'{m[1]} ({m[2]})', text)


def build(source, output):
    output.mkdir(parents=True, exist_ok=True)
    screenshots = output / 'screenshots'
    screenshots.mkdir(exist_ok=True)
    document = Document()
    section = document.sections[0]
    section.page_height, section.page_width = Cm(29.7), Cm(21)
    section.top_margin = section.bottom_margin = Cm(1.8)
    section.left_margin = section.right_margin = Cm(2)
    normal = document.styles['Normal']
    normal.font.name = 'Arial'
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.08
    for style in ('Heading 1', 'Heading 2'):
        document.styles[style].font.name = 'Arial'
        document.styles[style].font.color.rgb = RGBColor.from_string('174B61')
    document.core_properties.title = 'Manual de usuario de MUSA para QGIS'
    document.core_properties.author = 'MUSA'
    document.core_properties.subject = 'Uso de QGIS, ventanas móviles y lectura de resultados'
    section.header.paragraphs[0].text = 'MUSA · Guía práctica de QGIS · versión experimental 1.0.0'
    footer = section.footer.paragraphs[0]
    footer.alignment = 2
    footer.add_run('Página ')
    field = OxmlElement('w:fldSimple')
    from docx.oxml.ns import qn
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    html = []
    portable = []
    paragraph = []

    def flush():
        if paragraph:
            text = ' '.join(paragraph)
            document.add_paragraph(inline(text))
            html.append('<p>' + escape(inline(text)) + '</p>')
            paragraph.clear()

    for line in source.read_text(encoding='utf-8').splitlines():
        image = re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)', line)
        if image:
            flush()
            path = source.parent / image[2]
            target = screenshots / path.name
            if path.resolve() != target.resolve():
                shutil.copy2(path, target)
            with Image.open(path) as picture:
                width, height = picture.size
            scale = min(16.5 / width, 17 / height)
            p = document.add_paragraph()
            p.alignment = 1
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(str(path), width=Cm(width * scale), height=Cm(height * scale))
            caption = document.add_paragraph(image[1], style='Caption')
            caption.paragraph_format.keep_together = True
            html.append(f'<figure><a href="screenshots/{escape(path.name)}"><img src="screenshots/{escape(path.name)}" alt="{escape(image[1])}"></a><figcaption>{escape(image[1])}</figcaption></figure>')
            portable.append(f'![{image[1]}](screenshots/{path.name})')
        elif line.startswith('# '):
            flush()
            document.add_heading(line[2:], 0)
            html.append('<h1>' + escape(line[2:]) + '</h1>')
            portable.append(line)
        elif line.startswith('## '):
            flush()
            document.add_heading(line[3:], 1)
            html.append('<h2>' + escape(line[3:]) + '</h2>')
            portable.append(line)
        elif line.startswith('- '):
            flush()
            document.add_paragraph(inline(line[2:]), style='List Bullet')
            html.append('<p class="bullet">• ' + escape(inline(line[2:])) + '</p>')
            portable.append(line)
        elif not line.strip():
            flush()
            portable.append('')
        else:
            paragraph.append(line)
            portable.append(line)
    flush()
    target = output / 'Manual_MUSA_QGIS_es.docx'
    document.save(target)
    (output / 'Manual_MUSA_QGIS_es.md').write_text('\n'.join(portable) + '\n', encoding='utf-8')
    css = 'body{font:17px/1.65 Arial,sans-serif;color:#172d3a;max-width:980px;margin:40px auto;padding:0 24px}h1,h2{color:#174b61}h2{margin-top:2.2em}figure{margin:24px 0;padding:16px;background:#f3f6f7;border-radius:8px}img{display:block;max-width:100%;max-height:1000px;margin:auto}figcaption{font-size:.9em;color:#465963;margin-top:10px}a{color:#146b90}.bullet{margin-left:20px}@media print{figure{break-inside:avoid}body{font-size:11pt}}'
    (output / 'Manual_MUSA_QGIS_es.html').write_text('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Manual MUSA para QGIS</title><style>' + css + '</style><main>' + '\n'.join(html) + '</main></html>', encoding='utf-8')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(build(args.source.resolve(), args.output.resolve()))

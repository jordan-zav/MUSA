"""Review every chapter position in real QGIS widgets without desktop control.

Run with QGIS Python: capture_learning_qgis.py BUNDLE --output NEW_DIRECTORY.
The isolated installed ZIP is used at 1000 and 1400 pixel widget widths.
"""
# ruff: noqa: E402
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('bundle', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(parents=True, exist_ok=False)
profile = root/'profile'
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QGIS_CUSTOM_CONFIG_PATH'] = str(profile)
os.environ['QGIS_AUTH_DB_DIR_PATH'] = str(profile/'auth')
plugins = profile/'python/plugins'
with zipfile.ZipFile(args.bundle) as archive:
    assert all(n.startswith('musa_qgis/') and '..' not in Path(n).parts for n in archive.namelist())
    archive.extractall(plugins)
sys.path.insert(0, str(plugins))
from qgis.core import Qgis, QgsApplication
from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase, QFontInfo, QFontMetrics, QPixmap, QTextCursor
from qgis.PyQt.QtWidgets import QMainWindow
app = QgsApplication([], True, str(profile))
app.initQgis()
QgsApplication.setMaxThreads(2)
assert Qgis.QGIS_VERSION.startswith('3.44.12')
assert Path(QgsApplication.qgisSettingsDirPath()).resolve().is_relative_to(profile)
windows_dir = os.environ.get("WINDIR")
font = Path(windows_dir) / "Fonts/arial.ttf" if windows_dir else None
if font is not None and font.is_file():
    QFontDatabase.addApplicationFont(str(font))
app.setFont(QFont('Arial', 11))
from musa_qgis.workbench import MusaDock
from musa_qgis.learning import source_path


class Interface:
    def __init__(self):
        self.window = QMainWindow()
    def mainWindow(self):
        return self.window
    def activeLayer(self):
        return None


iface = Interface()
dock = MusaDock(iface)
iface.window.addDockWidget(Qt.RightDockWidgetArea, dock)
dock.setFloating(True)
dock.setWindowTitle('MUSA 1.3.1 | QGIS 3.44.12')
dock.show()
reader = dock.learning_reader


def settle():
    for _ in range(6):
        app.processEvents()
    reader.fit_images()
    reader.document().documentLayout().documentSize()
    for _ in range(4):
        app.processEvents()


def fragments():
    block = reader.document().begin()
    result = []
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            f = it.fragment()
            if f.isValid() and f.charFormat().isImageFormat():
                result.append(f)
            it += 1
        block = block.next()
    return result


rows = []
glyphs = {}
for lang in ('en', 'es'):
    dock.learning_language_selector.setCurrentIndex(dock.learning_language_selector.findData(lang))
    dock.tabs.setCurrentWidget(dock.learning_page)
    for width in (1000, 1400):
        # Tall enough to show a complete square map and caption at both widths.
        dock.resize(width, 1700)
        settle()
        assert dock.width() == width
        assert reader.horizontalScrollBar().maximum() == 0
        # Inspect the font actually assigned to every rendered text fragment.
        # Images and layout control characters have no text glyph to check.
        checked, missing, families = set(), [], set()
        block = reader.document().begin()
        formulas = 0
        while block.isValid():
            if block.text().startswith(('N(ε) =', 'Hq =', 'ρr(x)', 'd(x) =')):
                assert block.blockFormat().alignment() & Qt.AlignHCenter
                formulas += 1
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid() and not fragment.charFormat().isImageFormat():
                    font = fragment.charFormat().font().resolve(reader.document().defaultFont())
                    metrics = QFontMetrics(font)
                    family = QFontInfo(font).family()
                    families.add(family)
                    for char in fragment.text():
                        if not char.isspace() and ord(char) != 0xfffc:
                            checked.add(char)
                            if not metrics.inFontUcs4(ord(char)):
                                missing.append(dict(character=char, codepoint=f'U+{ord(char):04X}', font=family))
                it += 1
            block = block.next()
        assert not missing, (lang, missing)
        assert formulas >= 4, (lang, formulas)
        glyphs[lang] = dict(characters=''.join(sorted(checked)), count=len(checked),
                            fonts=sorted(families), missing=missing)
        fs = fragments()
        assert len(fs) == 13
        dimensions = []
        for fragment in fs:
            fmt = fragment.charFormat().toImageFormat()
            assert fmt.name().endswith(f'.{lang}.png')
            resource = reader.document().resource(2, QUrl(fmt.name()))
            assert resource is not None and resource.width() > 0
            assert abs(fmt.width()/fmt.height()-resource.width()/resource.height()) < 1e-6
            assert fmt.width() <= reader.viewport().width()
            assert fmt.width() <= 760
            dimensions.append(dict(name=fmt.name(), width=fmt.width(), height=fmt.height()))
        # Verify real Qt caption alignment and font size, in addition to pure renderer tests.
        block = reader.document().begin()
        captions = 0
        while block.isValid():
            if re.match(r'(?:Figura|Figure) \d+\. ', block.text()):
                assert block.blockFormat().alignment() & Qt.AlignHCenter
                cursor = QTextCursor(block)
                cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
                assert cursor.charFormat().fontPointSize() < app.font().pointSizeF()
                captions += 1
            block = block.next()
        assert captions == 13
        bar = reader.verticalScrollBar()
        # Sequential traversal with overlap covers every document row. Figure anchors
        # add complete figure+caption views independent of pagination boundaries.
        targets = [(f'page-{i+1:02d}', y) for i, y in enumerate(range(0, bar.maximum()+1, reader.viewport().height()-180))]
        targets.append(('end', bar.maximum()))
        for i, fragment in enumerate(fs, 1):
            cursor = QTextCursor(reader.document())
            cursor.setPosition(fragment.position())
            rect = reader.cursorRect(cursor)
            top = rect.top()+bar.value()-20
            targets.append((f'figure-{i:02d}', max(0, top)))
        for label, y in targets:
            bar.setValue(y)
            settle()
            if label.startswith('figure-'):
                fragment = fs[int(label.split('-')[1])-1]
                cursor = QTextCursor(reader.document())
                cursor.setPosition(fragment.position())
                rect = reader.cursorRect(cursor)
                # Image and following caption must fit together in the anchored view.
                image_block = cursor.block()
                caption_block = image_block.next()
                while caption_block.isValid() and not caption_block.text().strip():
                    caption_block = caption_block.next()
                caption_rect = reader.document().documentLayout().blockBoundingRect(caption_block)
                image_rect = reader.document().documentLayout().blockBoundingRect(image_block)
                image_height = fragment.charFormat().toImageFormat().height()
                assert image_rect.height() <= image_height+24, (label, image_rect.height(), image_height)
                assert caption_rect.top()-image_rect.bottom() < 30, label
                assert rect.top() >= 0, (label, rect.top())
                assert caption_rect.bottom()-bar.value() <= reader.viewport().height(), label
            pixmap = QPixmap(dock.size())
            pixmap.fill(QColor('white'))
            dock.render(pixmap)
            name = f'{lang}-{width}-{label}.png'
            assert pixmap.save(str(root/name))
            rows.append(dict(language=lang, width=width, capture=name, scroll=bar.value(),
                             viewport=[reader.viewport().width(), reader.viewport().height()],
                             images=dimensions, captions=captions, horizontal_scroll=0))
        if width == 1000:
            # A complete reference map and its caption remain visible in the guide.
            dock.resize(1000, 1400)
            settle()
            cursor = QTextCursor(reader.document())
            cursor.setPosition(fragments()[0].position())
            bar.setValue(reader.cursorRect(cursor).top()+bar.value()-20)
            settle()
            pixmap = QPixmap(dock.size())
            pixmap.fill(QColor('white'))
            dock.render(pixmap)
            assert pixmap.save(str(root/f'15-learn-{lang}.png'))
        assert source_path(lang).is_relative_to(profile)
(root/'capture_manifest.json').write_text(json.dumps(dict(
    qgis=Qgis.QGIS_VERSION, bundle_sha256=hashlib.sha256(args.bundle.read_bytes()).hexdigest(),
    rows=rows, glyphs=glyphs,
    assertions='all text glyphs in actual fonts, centered formulas, full-color figures <=760px, aspect, captions, no horizontal scroll'),
    ensure_ascii=False, indent=2), encoding='utf-8')
print(f'PASS {len(rows)} chapter views plus two guide captures', flush=True)
dock.detach()
dock.close()
# No desktop application or unrelated process is closed.

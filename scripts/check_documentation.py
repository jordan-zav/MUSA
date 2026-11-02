"""Check repository documentation links and the syntax of Python examples."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


def main():
    root = Path(__file__).resolve().parents[1]
    documents = [root / "README.md", root / "README.es.md", *sorted((root / "docs").glob("*.md"))]
    failures = []
    examples = 0
    for path in documents:
        content = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\[[^\]\n]*\]\(([^)]+)\)", content):
            target = match.group(1).strip().split(' "', 1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = root / unquote(parsed.path.lstrip("/")) if parsed.path.startswith("/") else path.parent / unquote(parsed.path)
            if not destination.exists():
                failures.append(f"{path.relative_to(root)}: missing link {target}")
        for match in re.finditer(r"(?m)^(~~~|```)python[^\n]*\n(.*?)^\1\s*$", content, re.S | re.M):
            try:
                compile(match.group(2), str(path.relative_to(root)), "exec")
                examples += 1
            except SyntaxError as exc:
                failures.append(f"{path.relative_to(root)}: invalid Python example: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Documentation OK: {len(documents)} documents, {examples} Python examples; local links checked.")
    print("External URLs, Markdown anchors and example runtime dependencies are not checked here.")


if __name__ == "__main__":
    main()

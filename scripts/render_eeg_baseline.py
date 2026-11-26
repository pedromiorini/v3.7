#!/usr/bin/env python3
"""Render the EEGBCI Markdown technical note to a new PDF without overwriting."""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from markdown import markdown
from weasyprint import HTML

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "v4.0-closed-loop" / "diwt_v40_eegbci_baseline.md"
DEFAULT_OUTPUT = REPO_ROOT / "v4.0-closed-loop" / "diwt_v40_eegbci_baseline.pdf"
STYLE = """
@page { size: A4; margin: 17mm 16mm 18mm; @bottom-right { content: counter(page); color: #666; font: 9pt sans-serif; } }
body { font: 10pt sans-serif; line-height: 1.42; color: #222; }
h1 { font-size: 19pt; line-height: 1.15; margin-top: 0; }
h2 { font-size: 14pt; margin-top: 1.2em; }
p { margin: 0.55em 0; }
table { border-collapse: collapse; table-layout: fixed; width: 100%; font-size: 8.4pt; }
th, td { border: 1px solid #aaa; padding: 4px; vertical-align: top; overflow-wrap: anywhere; }
th { background: #f0f2f4; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f4f4f4; padding: 7px; font-size: 8pt; }
code { font-family: monospace; font-size: 0.92em; }
a { color: #145da0; }
"""


def render(source: Path, output: Path) -> Path:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Markdown source not found: {source}")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to overwrite existing PDF: {output}")

    html_body = markdown(
        source.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    html_document = (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        f"<style>{STYLE}</style></head><body>{html_body}</body></html>"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
        HTML(string=html_document, base_url=str(source.parent)).write_pdf(temporary)
        # Same-directory hard-link publication is atomic and fails if a competing
        # writer has created the destination; it never replaces that file.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(f"Wrote {render(args.source, args.output)}")


if __name__ == "__main__":
    main()

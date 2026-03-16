#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nbconvert.exporters import MarkdownExporter

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>__TITLE__</title>
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/katex@0.16.25/dist/katex.min.css"
      integrity="sha384-WcoG4HRXMzYzfCgiyfrySxx90XSl2rxY5mnVY5TwtWE6KLrArNKn0T/mOgNL0Mmi"
      crossorigin="anonymous"
    />
    <style>
      :root {
        color-scheme: light;
      }

      body {
        margin: 0;
        padding: 24px;
        background: #ffffff;
        color: #1f2328;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        line-height: 1.6;
      }

      #content {
        max-width: 920px;
        margin: 0 auto;
      }

      h1, h2, h3, h4, h5, h6 {
        line-height: 1.25;
        margin-top: 1.6em;
        margin-bottom: 0.6em;
      }

      pre {
        background: #f6f8fa;
        border: 1px solid #d0d7de;
        border-radius: 6px;
        padding: 12px;
        overflow-x: auto;
      }

      code {
        font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, "Liberation Mono", monospace;
      }

      table {
        border-collapse: collapse;
      }

      table th,
      table td {
        border: 1px solid #d0d7de;
        padding: 6px 12px;
      }

      img {
        max-width: 100%;
      }
    </style>
  </head>
  <body>
    <main id="content"></main>

    <script src="https://cdn.jsdelivr.net/npm/markdown-it@14.1.0/dist/markdown-it.min.js"></script>
    <script
      defer
      src="https://cdn.jsdelivr.net/npm/katex@0.16.25/dist/katex.min.js"
      integrity="sha384-J+9dG2KMoiR9hqcFao0IBLwxt6zpcyN68IgwzsCSkbreXUjmNVRhPFTssqdSGjwQ"
      crossorigin="anonymous"
    ></script>
    <script
      defer
      src="https://cdn.jsdelivr.net/npm/katex@0.16.25/dist/contrib/auto-render.min.js"
      integrity="sha384-hCXGrW6PitJEwbkoStFjeJxv+fSOOQKOPbJxSfM6G5sWZjAyWhXiTIIAmQqnlLlh"
      crossorigin="anonymous"
    ></script>
    <script>
      const source = __MARKDOWN_JSON__;
      const md = window.markdownit({
        html: true,
        linkify: true,
        typographer: true
      });
      // Preserve LaTeX commands like "\\," until KaTeX processes math.
      md.disable(["escape"]);

      window.addEventListener("load", () => {
        const content = document.getElementById("content");
        content.innerHTML = md.render(source);

        window.renderMathInElement(content, {
          throwOnError: false,
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "\\\\[", right: "\\\\]", display: true },
            { left: "$", right: "$", display: false },
            { left: "\\\\(", right: "\\\\)", display: false }
          ]
        });
      });
    </script>
  </body>
</html>
"""

PDF_FOOTER_TEMPLATE = """
<div style="width: 100%; font-size: 10px; color: #57606a; padding: 0 10mm;">
  <div style="float: right;">
    <span class="pageNumber"></span> / <span class="totalPages"></span>
  </div>
</div>
"""


def _write_markdown_assets(resources: dict, output_dir: Path) -> None:
    outputs = resources.get("outputs", {})
    for rel_name, data in outputs.items():
        target = output_dir / rel_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            target.write_text(data, encoding="utf-8")
        else:
            target.write_bytes(data)


def notebook_to_markdown(notebook_path: Path, output_dir: Path) -> str:
    exporter = MarkdownExporter()
    body, resources = exporter.from_filename(str(notebook_path))
    _write_markdown_assets(resources, output_dir)
    return body


def build_html(markdown_text: str, title: str) -> str:
    html = HTML_TEMPLATE.replace("__TITLE__", title)
    html = html.replace("__MARKDOWN_JSON__", json.dumps(markdown_text))
    return html


def write_pdf_from_html(html_path: Path, pdf_path: Path, page_numbers: bool) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        msg = (
            "Playwright is not installed. Install requirements first with:\n"
            "  .venv/bin/pip install -r requirements.txt"
        )
        raise RuntimeError(msg) from exc

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.emulate_media(media="screen")
            pdf_kwargs = {
                "path": str(pdf_path),
                "format": "A4",
                "print_background": True,
                "margin": {"top": "12mm", "right": "12mm", "bottom": "14mm", "left": "12mm"},
            }
            if page_numbers:
                pdf_kwargs["display_header_footer"] = True
                pdf_kwargs["header_template"] = "<div></div>"
                pdf_kwargs["footer_template"] = PDF_FOOTER_TEMPLATE
                pdf_kwargs["margin"] = {
                    "top": "12mm",
                    "right": "12mm",
                    "bottom": "18mm",
                    "left": "12mm",
                }

            page.pdf(
                **pdf_kwargs,
            )
            browser.close()
    except Exception as exc:  # noqa: BLE001
        msg = (
            "Failed to render PDF. If this is the first run, install Chromium with:\n"
            "  .venv/bin/playwright install chromium"
        )
        raise RuntimeError(msg) from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a notebook via markdown-it + KaTeX HTML, with optional PDF print."
    )
    parser.add_argument("notebook", type=Path, help="Path to .ipynb file")
    parser.add_argument(
        "--html-out",
        type=Path,
        default=None,
        help="Output HTML path (default: <notebook>.mdit.html)",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also print the generated HTML to PDF using Playwright",
    )
    parser.add_argument(
        "--pdf-out",
        type=Path,
        default=None,
        help="Output PDF path (default: <notebook>.mdit.pdf)",
    )
    parser.add_argument(
        "--no-page-numbers",
        action="store_true",
        help="Disable page numbers in the generated PDF",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    notebook_path = args.notebook.resolve()
    if not notebook_path.exists():
        print(f"Notebook not found: {notebook_path}", file=sys.stderr)
        return 1

    html_out = args.html_out or notebook_path.with_suffix(".mdit.html")
    pdf_out = args.pdf_out or notebook_path.with_suffix(".mdit.pdf")

    markdown_text = notebook_to_markdown(notebook_path, html_out.parent.resolve())
    html = build_html(markdown_text, notebook_path.stem)
    html_out.write_text(html, encoding="utf-8")
    print(f"Wrote HTML: {html_out}")

    if args.pdf:
        write_pdf_from_html(html_out, pdf_out, page_numbers=not args.no_page_numbers)
        print(f"Wrote PDF:  {pdf_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

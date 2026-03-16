#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from nbconvert.exporters import MarkdownExporter

SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = SCRIPT_DIR / "assets"

REQUIRED_ASSET_FILES = (
    "markdown-it/markdown-it.min.js",
    "katex/katex.min.css",
    "katex/katex.min.js",
    "katex/contrib/auto-render.min.js",
)

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>__TITLE__</title>
    <base href="__BASE_HREF__" />
    <link rel="stylesheet" href="__KATEX_CSS__" />
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

    <script src="__MARKDOWN_IT_JS__"></script>
    <script defer src="__KATEX_JS__"></script>
    <script defer src="__KATEX_AUTORENDER_JS__"></script>
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


def _extract_css_asset_paths(css_text: str) -> list[str]:
    matches = re.findall(r"url\(([^)]+)\)", css_text)
    paths: list[str] = []
    for raw in matches:
        cleaned = raw.strip().strip("\"'")
        if not cleaned or cleaned.startswith("data:"):
            continue
        cleaned = cleaned.split("?", 1)[0].split("#", 1)[0]
        paths.append(cleaned)
    return paths


def validate_local_assets(assets_dir: Path) -> None:
    missing: list[str] = []

    for rel_path in REQUIRED_ASSET_FILES:
        target = assets_dir / rel_path
        if not target.exists():
            missing.append(str(target))

    katex_css_path = assets_dir / "katex/katex.min.css"
    if katex_css_path.exists():
        css_text = katex_css_path.read_text(encoding="utf-8")
        for rel_css_path in _extract_css_asset_paths(css_text):
            if rel_css_path.startswith(("http://", "https://")):
                missing.append(f"remote asset referenced by katex.min.css: {rel_css_path}")
                continue

            candidate = (katex_css_path.parent / rel_css_path.lstrip("/")).resolve()
            assets_root = assets_dir.resolve()
            if assets_root != candidate and assets_root not in candidate.parents:
                msg = f"Unsafe asset path in katex.min.css: {rel_css_path}"
                raise RuntimeError(msg)

            if not candidate.exists():
                missing.append(str(candidate))

    if missing:
        msg = (
            "Missing local export assets. Expected all files inside 'export/assets'.\n"
            + "\n".join(f"- {item}" for item in missing)
        )
        raise RuntimeError(msg)


def _relative_href(from_dir: Path, to_path: Path) -> str:
    return Path(os.path.relpath(to_path, from_dir)).as_posix()


def _base_href(from_dir: Path, notebook_dir: Path) -> str:
    rel = _relative_href(from_dir, notebook_dir)
    if rel == ".":
        return "./"
    return rel.rstrip("/") + "/"


def asset_refs_for_notebook(notebook_dir: Path, assets_dir: Path) -> dict[str, str]:
    return {
        "markdown_it_js": _relative_href(notebook_dir, assets_dir / "markdown-it/markdown-it.min.js"),
        "katex_css": _relative_href(notebook_dir, assets_dir / "katex/katex.min.css"),
        "katex_js": _relative_href(notebook_dir, assets_dir / "katex/katex.min.js"),
        "katex_autorender_js": _relative_href(
            notebook_dir,
            assets_dir / "katex/contrib/auto-render.min.js",
        ),
    }


def build_html(markdown_text: str, title: str, base_href: str, asset_refs: dict[str, str]) -> str:
    html = HTML_TEMPLATE.replace("__TITLE__", title)
    html = html.replace("__BASE_HREF__", base_href)
    html = html.replace("__MARKDOWN_JSON__", json.dumps(markdown_text))
    html = html.replace("__MARKDOWN_IT_JS__", asset_refs["markdown_it_js"])
    html = html.replace("__KATEX_CSS__", asset_refs["katex_css"])
    html = html.replace("__KATEX_JS__", asset_refs["katex_js"])
    html = html.replace("__KATEX_AUTORENDER_JS__", asset_refs["katex_autorender_js"])
    return html


def write_pdf_from_html(html_path: Path, pdf_path: Path, page_numbers: bool, pdf_scale: float) -> None:
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
                "scale": pdf_scale,
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

            page.pdf(**pdf_kwargs)
            browser.close()
    except Exception as exc:  # noqa: BLE001
        msg = (
            "Failed to render PDF. Ensure Chromium is installed for Playwright:\n"
            "  .venv/bin/playwright install chromium"
        )
        raise RuntimeError(msg) from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a notebook via markdown-it + KaTeX HTML, with PDF print by default."
    )
    parser.add_argument("notebook", type=Path, help="Path to .ipynb file")
    parser.add_argument(
        "--html-out",
        type=Path,
        default=None,
        help="Output HTML path (default: export/<notebook>.export.html)",
    )
    parser.add_argument(
        "--pdf-out",
        type=Path,
        default=None,
        help="Output PDF path (default: export/<notebook>.export.pdf)",
    )
    parser.add_argument(
        "--no-page-numbers",
        action="store_true",
        help="Disable page numbers in the generated PDF",
    )
    parser.add_argument(
        "--pdf-scale",
        type=float,
        default=0.8,
        help="Scale factor for PDF rendering (0.1 to 2.0, default: 0.8)",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Generate HTML only (skip PDF generation)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    notebook_path = args.notebook.resolve()
    if not notebook_path.exists():
        print(f"Notebook not found: {notebook_path}", file=sys.stderr)
        return 1

    html_out = args.html_out.resolve() if args.html_out else SCRIPT_DIR / f"{notebook_path.stem}.export.html"
    pdf_out = args.pdf_out.resolve() if args.pdf_out else SCRIPT_DIR / f"{notebook_path.stem}.export.pdf"

    html_out.parent.mkdir(parents=True, exist_ok=True)
    if not args.html_only:
        pdf_out.parent.mkdir(parents=True, exist_ok=True)

    validate_local_assets(ASSETS_DIR)

    notebook_dir = notebook_path.parent.resolve()
    markdown_text = notebook_to_markdown(notebook_path, html_out.parent.resolve())
    html = build_html(
        markdown_text,
        notebook_path.stem,
        base_href=_base_href(html_out.parent.resolve(), notebook_dir),
        asset_refs=asset_refs_for_notebook(notebook_dir, ASSETS_DIR.resolve()),
    )
    html_out.write_text(html, encoding="utf-8")
    print(f"Wrote HTML: {html_out}")

    if not args.html_only:
        if not (0.1 <= args.pdf_scale <= 2.0):
            print("--pdf-scale must be between 0.1 and 2.0", file=sys.stderr)
            return 1
        write_pdf_from_html(
            html_out,
            pdf_out,
            page_numbers=not args.no_page_numbers,
            pdf_scale=args.pdf_scale,
        )
        print(f"Wrote PDF:  {pdf_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

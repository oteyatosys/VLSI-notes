# 02205 VLSI Prep

Study material and helper code for VLSI calculations.

## Contents

- `cap.ipynb`: capacitance calculations from stick-diagram geometry.
- `effots.ipynb`: logical effort calculations and formatted tables.
- `design_rules.py`: reusable capacitance model and process constants.
- `img/`: diagrams used by the notebooks.

## Quick Start (VS Code)

1. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Open this folder in VS Code.
4. Open a notebook (`.ipynb`) and select the `.venv` Python kernel.

Tested with Python 3.13.

## Optional: Run notebooks outside VS Code

If you want browser-based notebooks, install and run JupyterLab:

```bash
pip install jupyterlab
jupyter lab
```

## Export Notebook (VS Code-like Markdown + KaTeX)

This route renders notebook content through `markdown-it` and KaTeX first,
and by default writes both HTML and PDF:

```bash
.venv/bin/python export/main.py effots.ipynb
```

All export outputs are written to the `export/` folder by default.
Default filenames are `export/<notebook>.export.html` and `export/<notebook>.export.pdf`.
Required local assets are stored in `export/assets/` (no download step in the script).
Use `--pdf-scale` to shrink or enlarge the rendered PDF content (default is `0.8`):

```bash
.venv/bin/python export/main.py effots.ipynb --pdf-scale 0.85
```

PDF page numbers are enabled by default. Disable them with:

```bash
.venv/bin/python export/main.py effots.ipynb --no-page-numbers
```

To export only HTML (skip PDF):

```bash
.venv/bin/python export/main.py effots.ipynb --html-only
```

If Chromium is missing on first run:

```bash
.venv/bin/playwright install chromium
```

## Export Notebook (Default nbconvert WebPDF)

```bash
.venv/bin/jupyter nbconvert --to webpdf --allow-chromium-download effots.ipynb
```

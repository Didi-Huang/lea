[中文](./README_zh.md) | [日本語](./README_ja.md) | English

<div align="center">

# LEA — Lab Experiment Assistant

**A desktop GUI tool for the full physics/chemistry experiment workflow.**

Project init → Data analysis → Visualization → Format conversion → Cleanup

</div>

> [!NOTE]
> The `user_data/` directory is gitignored and not tracked by Git.
> Create it manually if needed and place your user data files there.

## Features

### Project — One-click scaffolding
Create a standard experiment directory structure from templates (Default / Scientific / Custom).
Optionally generate `.gitignore` and initialize a git repository.

### Data — CSV analysis & visualization **[core]**
- Load CSV files with configurable encoding, separator, and header row
- Preview data in a table view
- **Scatter plot** and **histogram** with embedded matplotlib figures
- **Linear fit** via `scipy.optimize.curve_fit` with uncertainty and R² output
- Copy fit results as LaTeX formula / export plots as PNG

### Convertor — Beamer PDF to PPTX
- Render each PDF page at adjustable DPI (100–400) and embed as full-slide PNG into `.pptx`
- **PDF Page Editor**: delete, extract, or split pages by range (`1,3,5-8,10-`)

### Cache Cleaner
- LaTeX: clear output PDFs and auxiliary files (`.aux`, `.log`, `.toc`, `.out`, etc.)
- Python: recursively remove `__pycache__/`, `*.pyc`, `*.pyo`

### Settings
- **Live language switching** — 中文 / English / 日本語 (181 translation keys)
- Font family and size, default DPI / output format, student ID for templates

## Installation

```bash
# Clone
git clone https://github.com/Didi-Huang/lea.git
cd lea

# Create venv & install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install PySide6 pymupdf python-pptx pandas matplotlib scipy numpy
```

## Usage

```bash
python main.py
```

1. **Project** tab — enter experiment name, choose parent folder and template, hit "Create"
2. **Data** tab — browse CSV → "Load" → choose X/Y columns → "Scatter" / "Histogram" / "Linear Fit"
3. **Convertor** tab — select source PDF, output folder, DPI, click "Convert"
4. **Cache Cleaner** — click "Auto Clear" for LaTeX or Python
5. **Settings** — switch language, save preferences

## Project Structure

```
lea/
├── main.py                  # PySide6 GUI entry point
├── src/
│   ├── convertor.py         # Beamer PDF → PPTX conversion
│   ├── pdf_editor.py        # PDF page delete / extract / split
│   └── project_builder.py   # Experiment directory scaffolding
├── ui/
│   └── main_window.ui       # Qt Designer UI layout
├── locales/
│   ├── en.json / zh_CN.json / ja.json   # i18n (181 keys each)
├── templates/
│   ├── structures/          # Project directory templates (JSON)
│   ├── gitignore/           # .gitignore templates
│   └── readme/              # README templates
├── fonts/                   # HarmonyOS Sans font files
└── user_data/               # User settings, history, custom templates (gitignored)
```

## Dependencies

| Package | Purpose |
|---------|---------|
| PySide6 | GUI framework |
| PyMuPDF (`fitz`) | PDF rendering & page manipulation |
| python-pptx | PPTX generation |
| pandas | CSV data loading |
| matplotlib | Plotting (scatter, histogram, fit) |
| scipy | Curve fitting |
| numpy | Numerical arrays |

## License

MIT

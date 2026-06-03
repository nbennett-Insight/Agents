# PDF Convert Scripts

This folder contains scripts for converting between HTML and PDF formats.

## Scripts

### `html_section_to_pdf.py`
Converts OneNote-exported HTML section content into one or more PDF files.

- Supports single-section mode and multi-section root mode.
- Splits output by word limit.
- Embeds and optionally downscales images.
- Can process multiple sections in parallel.

### `pdf_to_html.py`
Converts one or more PDF files into HTML, creating one folder per PDF named after the PDF filename (without `.pdf`).

- Default mode writes one consolidated file: `<pdf_stem>.html`.
- Optional `pages` mode writes one HTML file per page: `page_0001.html`, `page_0002.html`, etc.
- In `pages` mode, also creates an `index.html` with links to all generated pages.
- Supports multiple input PDFs in one run.

## Example (requested file)

```powershell
e:/VSCode-Root/.venv/Scripts/python.exe E:/VSCode-Root/pdf-convert/pdf_to_html.py E:/VSCode-Root/CCA-F-Exam-Guide.pdf --out-root E:/VSCode-Root/pdf-convert --overwrite
```

This (default mode) generates a single consolidated file in:

- `E:/VSCode-Root/pdf-convert/CCA-F-Exam-Guide/`

Use per-page mode explicitly:

```powershell
e:/VSCode-Root/.venv/Scripts/python.exe E:/VSCode-Root/pdf-convert/pdf_to_html.py E:/VSCode-Root/CCA-F-Exam-Guide.pdf --out-root E:/VSCode-Root/pdf-convert --output-mode pages --overwrite
```

#!/usr/bin/env python3
"""
Convert PDF files into HTML.

For each input PDF, this script creates a new output folder named after the
PDF file stem and writes either:
1. A single consolidated HTML file (default), or
2. Per-page HTML files plus index.html when pages mode is selected.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Iterable

import fitz


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert one or more PDF files to HTML.",
    )
    parser.add_argument(
        "pdfs",
        nargs="+",
        type=Path,
        help="Path(s) to PDF files to convert.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path.cwd(),
        help="Folder where PDF-named output folders are created.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing HTML files if output folder already exists.",
    )
    parser.add_argument(
        "--output-mode",
        choices=["single", "pages"],
        default="single",
        help="Output style: single (default) writes one merged HTML file; pages writes one file per page.",
    )
    return parser.parse_args()


def write_index_file(out_dir: Path, pdf_name: str, page_count: int) -> None:
    links = "\n".join(
        f'<li><a href="page_{idx:04d}.html">Page {idx}</a></li>'
        for idx in range(1, page_count + 1)
    )
    title = html.escape(pdf_name)
    index_html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title} - HTML Export</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 2rem; }}
    h1 {{ margin-top: 0; }}
    ul {{ line-height: 1.7; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>Total pages: {page_count}</p>
  <ul>
    {links}
  </ul>
</body>
</html>
"""
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")


def _extract_body_content(page_html: str) -> str:
        body_match = re.search(r"<body[^>]*>(.*?)</body>", page_html, flags=re.IGNORECASE | re.DOTALL)
        if body_match:
                return body_match.group(1).strip()
        return page_html


def write_single_file(out_dir: Path, pdf_path: Path, page_html_blocks: list[str], overwrite: bool) -> None:
        out_file = out_dir / f"{pdf_path.stem}.html"
        if out_file.exists() and not overwrite:
                return

        title = html.escape(pdf_path.name)
        nav_links = "\n".join(
                f'<li><a href="#page-{idx}">Page {idx}</a></li>'
                for idx in range(1, len(page_html_blocks) + 1)
        )
        sections = "\n".join(
                (
                        f'<section class="page" id="page-{idx}">'
                        f'<h2>Page {idx}</h2>{content}</section>'
                )
                for idx, content in enumerate(page_html_blocks, start=1)
        )

        merged_html = f"""<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{title} - Consolidated HTML Export</title>
    <style>
        body {{ font-family: Segoe UI, Arial, sans-serif; margin: 2rem; line-height: 1.45; }}
        h1 {{ margin-top: 0; }}
        .toc {{ margin-bottom: 2rem; }}
        .toc ul {{ columns: 3; max-width: 1100px; padding-left: 1.2rem; }}
        .page {{ margin-bottom: 2rem; padding-top: 1rem; border-top: 1px solid #d7d7d7; }}
        .page h2 {{ margin-top: 0; color: #333; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Total pages: {len(page_html_blocks)}</p>
    <div class=\"toc\">
        <h2>Pages</h2>
        <ul>
            {nav_links}
        </ul>
    </div>
    {sections}
</body>
</html>
"""
        out_file.write_text(merged_html, encoding="utf-8")


def convert_pdf(pdf_path: Path, out_root: Path, overwrite: bool, output_mode: str) -> None:
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a valid PDF file: {pdf_path}")

    out_dir = out_root / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as document:
        if output_mode == "pages":
            for index, page in enumerate(document, start=1):
                out_file = out_dir / f"page_{index:04d}.html"
                if out_file.exists() and not overwrite:
                    continue
                page_html = page.get_text("html")
                out_file.write_text(page_html, encoding="utf-8")

            write_index_file(out_dir, pdf_path.name, document.page_count)
        else:
            page_html_blocks = [
                _extract_body_content(page.get_text("html"))
                for page in document
            ]
            write_single_file(
                out_dir=out_dir,
                pdf_path=pdf_path,
                page_html_blocks=page_html_blocks,
                overwrite=overwrite,
            )

    print(f"Converted {pdf_path} -> {out_dir} (mode={output_mode})")


def iter_pdf_paths(pdfs: Iterable[Path]) -> list[Path]:
    resolved: list[Path] = []
    for pdf_path in pdfs:
        resolved.append(pdf_path.expanduser().resolve())
    return resolved


def main() -> None:
    args = parse_args()
    out_root = args.out_root.expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    for pdf_path in iter_pdf_paths(args.pdfs):
        convert_pdf(
            pdf_path=pdf_path,
            out_root=out_root,
            overwrite=args.overwrite,
            output_mode=args.output_mode,
        )


if __name__ == "__main__":
    main()

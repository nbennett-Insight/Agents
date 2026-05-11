#!/usr/bin/env python3
"""
Merge all HTML pages under a section folder (or every section under a notebook
root) into one or more PDFs, splitting by word limit.

Optimizations included
----------------------
1. Skip images narrower than --min-image-px (drops tiny icons/bullets).
2. Downscale images wider than --max-image-px to keep PDF file size sane.
3. TOC bookmark list at the top of every PDF part.
6. Concurrent section processing when --root is used (one worker per section).
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import io
import json
import re
import struct
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Convert OneNote HTML section exports to PDF(s).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--section-folder",
        type=Path,
        help="Single section folder (e.g. .../Bennett-Notes/Avamar).",
    )
    target.add_argument(
        "--root",
        type=Path,
        help="Notebook root; processes every direct child section in parallel.",
    )
    p.add_argument("--out-dir", type=Path, required=True, help="Folder for output PDFs.")
    p.add_argument(
        "--word-limit",
        type=int,
        default=300_000,
        help="Max words per PDF part (default 300000).",
    )
    p.add_argument(
        "--min-image-px",
        type=int,
        default=24,
        help="Skip images narrower than this px (opt 1). Default 24.",
    )
    p.add_argument(
        "--max-image-px",
        type=int,
        default=1200,
        help="Downscale images wider than this px (opt 2). Default 1200. 0=disabled.",
    )
    p.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Parallel workers when using --root (opt 6). Default 4.",
    )
    p.add_argument(
        "--groups-json",
        type=Path,
        help=(
            "JSON file mapping output PDF name -> list of page-folder names (or null for "
            "all remaining folders). Only valid with --section-folder."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned output without creating PDFs.",
    )
    p.add_argument(
        "--browser",
        choices=["msedge", "chrome", "chromium"],
        default="msedge",
        help=(
            "Browser to use for PDF rendering. "
            "'msedge' (default) uses the system-installed Edge - no download needed. "
            "'chromium' requires: playwright install chromium."
        ),
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Image helpers  (opts 1 & 2)
# ---------------------------------------------------------------------------

def _png_width(data: bytes) -> Optional[int]:
    try:
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            return None
        return struct.unpack(">I", data[16:20])[0]
    except Exception:
        return None


def _jpeg_width(data: bytes) -> Optional[int]:
    try:
        i = 2
        while i < len(data) - 1:
            if data[i] != 0xFF:
                break
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                return struct.unpack(">H", data[i + 7:i + 9])[0]
            seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg_len
    except Exception:
        pass
    return None


def image_width_px(path: Path) -> Optional[int]:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if HAS_PIL:
        try:
            with PILImage.open(io.BytesIO(data)) as im:
                return im.width
        except Exception:
            pass
    ext = path.suffix.lower()
    if ext == ".png":
        return _png_width(data)
    if ext in (".jpg", ".jpeg"):
        return _jpeg_width(data)
    return None


def maybe_downscale(path: Path, max_px: int) -> Optional[str]:
    """Return data-URI of downscaled image, or None if no downscale needed."""
    if not HAS_PIL or max_px <= 0:
        return None
    try:
        data = path.read_bytes()
        with PILImage.open(io.BytesIO(data)) as im:
            if im.width <= max_px:
                return None
            ratio = max_px / im.width
            new_size = (max_px, max(1, int(im.height * ratio)))
            resized = im.resize(new_size, PILImage.LANCZOS)
            buf = io.BytesIO()
            fmt = im.format or "PNG"
            if fmt == "JPEG":
                resized.save(buf, format="JPEG", quality=85)
                mime = "image/jpeg"
            else:
                resized.save(buf, format="PNG")
                mime = "image/png"
            b64 = base64.b64encode(buf.getvalue()).decode()
            return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def embed_image(path: Path) -> str:
    ext_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
    }
    mime = ext_map.get(path.suffix.lower(), "application/octet-stream")
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


# ---------------------------------------------------------------------------
# HTML processing
# ---------------------------------------------------------------------------

def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def sorted_html_files(section_folder: Path) -> List[Path]:
    files = [p for p in section_folder.rglob("*.html") if p.is_file()]
    return sorted(files, key=lambda p: str(p.relative_to(section_folder)).lower())


def linearize_absolute_layout(container) -> None:
    absolute_blocks = []
    for block in list(container.find_all("div", recursive=False)):
        style = block.get("style", "")
        normalized_style = style.replace(" ", "").lower()
        if "position:absolute" not in normalized_style:
            continue

        top_match = re.search(r"top:\s*([0-9.]+)px", style, re.IGNORECASE)
        left_match = re.search(r"left:\s*([0-9.]+)px", style, re.IGNORECASE)
        absolute_blocks.append(
            (
                float(top_match.group(1)) if top_match else 0.0,
                float(left_match.group(1)) if left_match else 0.0,
                block,
            )
        )

    if not absolute_blocks:
        return

    for _, _, block in absolute_blocks:
        block.extract()

    for _, _, block in sorted(absolute_blocks, key=lambda item: (item[0], item[1])):
        style = block.get("style", "")
        style = re.sub(r"position\s*:\s*absolute\s*;?", "", style, flags=re.IGNORECASE)
        style = re.sub(r"left\s*:\s*[^;]+;?", "", style, flags=re.IGNORECASE)
        style = re.sub(r"top\s*:\s*[^;]+;?", "", style, flags=re.IGNORECASE)
        style = re.sub(r"width\s*:\s*[^;]+;?", "", style, flags=re.IGNORECASE)
        style = re.sub(r"\s*;\s*", "; ", style).strip(" ;")
        if style:
            block["style"] = style
        elif "style" in block.attrs:
            del block["style"]
        container.append(block)


def process_html(html_path: Path, min_px: int, max_px: int) -> Tuple[str, int]:
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "lxml")
    container = soup.body if soup.body else soup

    if soup.body:
        soup.body.attrs.pop("data-absolute-enabled", None)

    linearize_absolute_layout(container)

    for img in list(container.find_all("img")):
        src = (img.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        if src.startswith(("http://", "https://", "file://")):
            img.decompose()
            continue
        img_path = (html_path.parent / src).resolve()
        if not img_path.exists():
            img.decompose()
            continue
        # Opt 1 - drop tiny images
        w = image_width_px(img_path)
        if w is not None and w < min_px:
            img.decompose()
            continue
        # Opt 2 - downscale or embed at original size
        uri = maybe_downscale(img_path, max_px) or embed_image(img_path)
        img["src"] = uri

    text = container.get_text(" ", strip=True)
    return str(container), word_count(text)


# ---------------------------------------------------------------------------
# HTML document assembly
# ---------------------------------------------------------------------------

_STYLE = """
@page { size: Letter; margin: 0.5in; }
body { font-family: "Segoe UI", Arial, sans-serif; line-height: 1.4;
       font-size: 11pt; color: #111; }
.page-block * { position: static !important; left: auto !important; top: auto !important; }
.page-block div { width: auto !important; max-width: 100% !important; }
.toc { background: #f4f8fc; border: 1px solid #c8dff0;
       padding: 10px 16px; margin-bottom: 18px; }
.toc-heading { font-size: 13pt; margin: 0 0 6px 0; color: #0b3d62; }
.toc ol { margin: 0; padding-left: 20px; font-size: 10pt; }
.toc li { margin-bottom: 2px; }
.toc-rule { border: none; border-top: 2px solid #0b3d62; margin: 0 0 18px 0; }
.page-block { margin-bottom: 22px; page-break-inside: avoid; }
.divider { font-size: 17pt; color: #0b3d62;
           border-left: 4px solid #0b3d62; padding-left: 10px; margin: 0 0 3px 0; }
.source { font-size: 8pt; color: #888; margin-bottom: 8px; word-break: break-all; }
hr { border: none; border-top: 1px solid #ddd; margin: 8px 0 12px 0; }
a { color: #0b57a3; text-decoration: none; }
ul, ol { margin-top: 0.4em; margin-bottom: 0.8em; }
p { margin-top: 0.15em; margin-bottom: 0.45em; }
img { max-width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; font-size: 10pt; }
td, th { border: 1px solid #ccc; padding: 4px 8px; vertical-align: top; }
th { background: #e8f0fe; }
"""


def toc_html(titles: List[str]) -> str:
    items = "".join(f"<li>{t}</li>" for t in titles)
    return (
        '<nav class="toc">'
        '<h2 class="toc-heading">Contents</h2>'
        f"<ol>{items}</ol></nav>"
        '<hr class="toc-rule" />'
    )


def wrap_page(title: str, source_path: Path, body: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", title)
    return (
        f'<section class="page-block" id="{safe_id}">'
        f'<h1 class="divider">#{title}</h1>'
        f'<div class="source">{source_path.as_posix()}</div>'
        f"<hr />{body}</section>"
    )


def full_html(doc_title: str, toc: str, fragments: List[str]) -> str:
    body = "\n".join(fragments)
    return (
        f'<!doctype html><html><head><meta charset="utf-8" />'
        f"<title>{doc_title}</title><style>{_STYLE}</style></head>"
        f"<body>{toc}\n{body}</body></html>"
    )


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------

def render_pdf(html_content: str, out_path: Path, browser_channel: str = "msedge") -> None:
    with sync_playwright() as pw:
        if browser_channel == "chromium":
            browser = pw.chromium.launch()
        elif browser_channel == "chrome":
            browser = pw.chromium.launch(channel="chrome")
        else:
            browser = pw.chromium.launch(channel="msedge")
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(
            path=str(out_path),
            format="Letter",
            print_background=True,
            margin={
                "top": "0.5in",
                "right": "0.5in",
                "bottom": "0.6in",
                "left": "0.5in",
            },
        )
        browser.close()


# ---------------------------------------------------------------------------
# Section pipeline
# ---------------------------------------------------------------------------

def process_section(
    section_folder: Path,
    out_dir: Path,
    word_limit: int,
    min_image_px: int,
    max_image_px: int,
    dry_run: bool,
    browser_channel: str = "msedge",
    allowed_folders: Optional[Set[str]] = None,
    output_name: Optional[str] = None,
) -> List[Path]:
    html_files = sorted_html_files(section_folder)
    if allowed_folders is not None:
        html_files = [f for f in html_files if f.parent.name in allowed_folders]
    if not html_files:
        print(f"[SKIP] No HTML: {section_folder}")
        return []

    section_name = output_name if output_name else section_folder.name
    parts: List[Tuple[List[str], List[str]]] = []
    cur_frags: List[str] = []
    cur_titles: List[str] = []
    cur_words = 0

    for html_path in html_files:
        title = html_path.parent.name
        try:
            body_frag, words = process_html(html_path, min_image_px, max_image_px)
        except Exception as exc:
            print(f"  [WARN] {html_path.name}: {exc}")
            continue

        if cur_frags and (cur_words + words) > word_limit:
            parts.append((cur_frags[:], cur_titles[:]))
            cur_frags, cur_titles, cur_words = [], [], 0

        cur_frags.append(wrap_page(title, html_path, body_frag))
        cur_titles.append(title)
        cur_words += words

    if cur_frags:
        parts.append((cur_frags, cur_titles))

    out_paths: List[Path] = []
    for idx, (fragments, titles) in enumerate(parts, start=1):
        suffix = "" if idx == 1 else f"_{idx}"
        doc_title = f"{section_name}{suffix}"
        out_pdf = out_dir / f"{doc_title}.pdf"
        content = full_html(doc_title, toc_html(titles), fragments)

        if dry_run:
            print(f"  [DRY-RUN] {out_pdf}  ({len(titles)} pages)")
        else:
            print(f"  Rendering {out_pdf}  ({len(titles)} pages) ...")
            render_pdf(content, out_pdf, browser_channel=browser_channel)
            print(f"  Created:  {out_pdf}")

        out_paths.append(out_pdf)

    return out_paths


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    out_dir: Path = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not HAS_PIL:
        print(
            "[WARN] Pillow not installed - image downscaling (opt 2) disabled. "
            "pip install Pillow"
        )

    if args.section_folder and getattr(args, "groups_json", None):
        # ----- Grouped mode: one PDF per group defined in the JSON -----
        section_folder = args.section_folder.resolve()
        groups_data: Dict[str, Optional[List[str]]] = json.loads(
            args.groups_json.read_text(encoding="utf-8")
        )
        mentioned: Set[str] = set()
        for folders in groups_data.values():
            if folders is not None:
                mentioned.update(folders)
        all_page_folders: Set[str] = {
            d.name for d in section_folder.iterdir() if d.is_dir()
        }
        remaining = all_page_folders - mentioned

        print(f"Section  : {section_folder.name}")
        print(f"Output   : {out_dir}")
        print(f"Groups   : {len(groups_data)}")
        print(f"Word lim : {args.word_limit:,}")
        print(f"Img range: {args.min_image_px}px - {args.max_image_px}px")
        print()

        all_pdfs: List[Path] = []
        for group_name, folders in groups_data.items():
            allowed: Set[str] = remaining if folders is None else set(folders)
            print(f"Group: {group_name!r}  ({len(allowed)} folders)")
            all_pdfs.extend(
                process_section(
                    section_folder,
                    out_dir=out_dir,
                    word_limit=args.word_limit,
                    min_image_px=args.min_image_px,
                    max_image_px=args.max_image_px,
                    dry_run=args.dry_run,
                    browser_channel=args.browser,
                    allowed_folders=allowed,
                    output_name=group_name,
                )
            )

        print(f"\nDone. {len(all_pdfs)} PDF(s) created.")
        return 0
    elif args.section_folder:
        sections = [args.section_folder.resolve()]
        workers = 1
    else:
        root = args.root.resolve()
        sections = sorted(
            [d for d in root.iterdir() if d.is_dir()],
            key=lambda d: d.name.lower(),
        )
        workers = min(args.max_workers, len(sections))

    print(f"Sections : {len(sections)}")
    print(f"Output   : {out_dir}")
    print(f"Word lim : {args.word_limit:,}")
    print(f"Img range: {args.min_image_px}px - {args.max_image_px}px")
    if workers > 1:
        print(f"Workers  : {workers} (parallel, opt 6)")
    print()

    kw = dict(
        out_dir=out_dir,
        word_limit=args.word_limit,
        min_image_px=args.min_image_px,
        max_image_px=args.max_image_px,
        dry_run=args.dry_run,
        browser_channel=args.browser,
    )

    all_pdfs: List[Path] = []

    if workers <= 1:
        for s in sections:
            print(f"Section: {s.name}")
            all_pdfs.extend(process_section(s, **kw))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(process_section, s, **kw): s for s in sections}
            for fut in concurrent.futures.as_completed(futures):
                s = futures[fut]
                try:
                    pdfs = fut.result()
                    all_pdfs.extend(pdfs)
                    print(f"[OK] {s.name} -> {len(pdfs)} PDF(s)")
                except Exception as exc:
                    print(f"[ERROR] {s.name}: {exc}")

    print(f"\nTotal PDFs: {len(all_pdfs)}")
    for p in sorted(all_pdfs, key=lambda x: x.name):
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

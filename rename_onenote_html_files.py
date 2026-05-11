#!/usr/bin/env python3
"""
Rename OneNote exported HTML files from 'page.html' to '<parent-folder-name>.html'.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_ROOT = Path(r"E:\VSCode-Root\onenote\Bennett-Notes")


def clean_name_for_file(name: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|]', "_", name).strip().rstrip(".")
    return clean if clean else "Untitled"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename 'page.html' files to match their parent folder names."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Root folder to scan recursively.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite destination file if it already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned renames without changing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.root.exists():
        raise RuntimeError(f"Root folder not found: {args.root}")

    renamed = 0
    skipped_exists = 0

    for src in args.root.rglob("page.html"):
        parent_name = clean_name_for_file(src.parent.name)
        dest = src.parent / f"{parent_name}.html"

        if dest.exists() and not args.overwrite:
            skipped_exists += 1
            print(f"Skip (exists): {dest}")
            continue

        print(f"Rename: {src} -> {dest}")
        if not args.dry_run:
            if dest.exists() and args.overwrite:
                dest.unlink()
            src.rename(dest)
        renamed += 1

    print("\nDone.")
    print(f"Renamed: {renamed}")
    print(f"Skipped existing destination: {skipped_exists}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

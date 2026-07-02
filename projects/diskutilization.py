#!/usr/bin/env python3
"""
Disk usage report: top N directories by size with % of drive used.

Examples:
  python diskutilization.py
  python diskutilization.py --path D:\\ --top 30 --levels 3 --branch-top 5
"""

from __future__ import annotations

import argparse
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find top disk-consuming directories and expand details for the highest path."
    )
    parser.add_argument("--path", default="C:\\", help="Root path to scan (default: C:\\)")
    parser.add_argument("--top", type=int, default=20, help="Number of top directories to report")
    parser.add_argument(
        "--levels",
        type=int,
        default=3,
        help=(
            "How many subfolder levels to expand for the highest-utilization path "
            "(default: 3)"
        ),
    )
    parser.add_argument(
        "--branch-top",
        type=int,
        default=5,
        help="How many child folders to show per level in the expanded breakdown",
    )
    return parser.parse_args()


def safe_relative(path: Path, base: Path) -> str:
    try:
        rel = path.resolve().relative_to(base.resolve())
        text = str(rel)
        return "." if text == "." else text
    except Exception:
        return str(path)


def walk_file_sizes(root: Path) -> Iterable[Tuple[Path, int]]:
    for dirpath, _, filenames in os.walk(root, topdown=True, onerror=None):
        folder = Path(dirpath)
        for name in filenames:
            f = folder / name
            try:
                yield f, f.stat().st_size
            except OSError:
                continue


def safe_list_dirs(folder: Path) -> List[Path]:
    try:
        return [p for p in folder.iterdir() if p.is_dir()]
    except OSError:
        return []


def build_size_index(scan_root: Path) -> Dict[Path, int]:
    # Index every folder's cumulative file size while traversing once.
    sizes: Dict[Path, int] = defaultdict(int)

    for file_path, size in walk_file_sizes(scan_root):
        current = file_path.parent
        while True:
            sizes[current] += size
            if current == scan_root:
                break
            parent = current.parent
            if parent == current:
                break
            current = parent

    return dict(sizes)


def get_top_level_results(scan_root: Path, size_index: Dict[Path, int], disk_total: int) -> List[dict]:
    rows: List[dict] = []
    for child in sorted(safe_list_dirs(scan_root), key=lambda p: p.name.lower()):

        size = size_index.get(child, 0)
        pct = round((size / disk_total) * 100, 1) if disk_total else 0.0
        rows.append(
            {
                "directory": child,
                "bytes": size,
                "size_gb": round(size / (1024**3), 2),
                "pct": pct,
            }
        )

    rows.sort(key=lambda r: r["bytes"], reverse=True)
    return rows


def print_top_results(results: List[dict], top: int) -> None:
    print("-" * 90)
    for row in results[:top]:
        bar_len = min(40, int(row["pct"]))
        bar = "#" * bar_len
        print(f"{row['size_gb']:>7.2f} GB  {row['pct']:>5.1f}%  {bar:<40}  {row['directory']}")


def print_highest_path_breakdown(
    highest: Path,
    scan_root: Path,
    size_index: Dict[Path, int],
    disk_total: int,
    levels: int,
    branch_top: int,
) -> None:
    print("\nExpanded Breakdown For Highest-Utilization Path")
    print(f"Root: {highest}")
    print("-" * 90)

    current_level = [highest]
    for level in range(1, levels + 1):
        next_level: List[Path] = []
        print(f"Level {level}:")

        for parent in current_level:
            children = safe_list_dirs(parent)
            ranked = sorted(
                children,
                key=lambda p: size_index.get(p, 0),
                reverse=True,
            )[:branch_top]

            if not ranked:
                continue

            for child in ranked:
                size = size_index.get(child, 0)
                pct_disk = round((size / disk_total) * 100, 2) if disk_total else 0.0
                pct_parent = (
                    round((size / size_index.get(parent, 1)) * 100, 2)
                    if size_index.get(parent, 0)
                    else 0.0
                )
                rel = safe_relative(child, scan_root)
                print(
                    f"  {rel:<60} "
                    f"{size / (1024**3):>8.2f} GB  "
                    f"{pct_disk:>6.2f}% of disk  "
                    f"{pct_parent:>6.2f}% of parent"
                )
                next_level.append(child)

        if not next_level:
            print("  (no deeper folders found)")
            break

        current_level = next_level


def main() -> int:
    args = parse_args()
    scan_root = Path(args.path)

    if not scan_root.exists() or not scan_root.is_dir():
        print(f"Path not found or not a directory: {scan_root}")
        return 1

    usage = shutil.disk_usage(scan_root)
    disk_total = usage.total

    print(f"Scanning {scan_root} ... (large drives can take a while)")
    size_index = build_size_index(scan_root)
    results = get_top_level_results(scan_root, size_index, disk_total)

    drive_full_pct = round((usage.used / disk_total) * 100, 1) if disk_total else 0.0
    print()
    print(
        f"Drive {scan_root.drive or scan_root}:  "
        f"{usage.used / (1024**3):.1f} GB used / {disk_total / (1024**3):.1f} GB total  "
        f"({drive_full_pct}% full)"
    )

    if not results:
        print("No subdirectories found under the scan path.")
        return 0

    print_top_results(results, args.top)

    highest = results[0]["directory"]
    print_highest_path_breakdown(
        highest=highest,
        scan_root=scan_root,
        size_index=size_index,
        disk_total=disk_total,
        levels=max(1, args.levels),
        branch_top=max(1, args.branch_top),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Validate OneNote export completeness and produce a summary report.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Dict, List


DEFAULT_ROOT = Path(r"E:\VSCode-Root\onenote\Bennett-Notes")
DEFAULT_FAIL_LOG = Path(r"E:\VSCode-Root\onenote\image_download_failures.log")
DEFAULT_REPORT = Path(r"E:\VSCode-Root\onenote\export_validation_report.txt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate exported OneNote HTML and image assets.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Root folder of exported notebook content.")
    parser.add_argument("--fail-log", type=Path, default=DEFAULT_FAIL_LOG, help="Path to image download failure log.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Path for generated text report.")
    parser.add_argument("--sample-limit", type=int, default=20, help="How many sample remaining Graph-URL HTML paths to list.")
    return parser.parse_args()


def count_html_metrics(root: Path) -> Dict:
    html_files = [p for p in root.rglob("*.html") if p.is_file()]

    remaining_graph_urls = 0
    local_image_refs = 0
    sample_remaining: List[str] = []

    for html in html_files:
        try:
            content = html.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        has_graph = "https://graph.microsoft.com/v1.0/" in content
        has_local = ('src="images/' in content) or ('data-fullres-src="images/' in content)

        if has_graph:
            remaining_graph_urls += 1
            sample_remaining.append(str(html))
        if has_local:
            local_image_refs += 1

    image_files = []
    for images_dir in root.rglob("images"):
        if images_dir.is_dir():
            image_files.extend([p for p in images_dir.iterdir() if p.is_file()])

    ext_counter = Counter((p.suffix.lower() or "<noext>") for p in image_files)

    return {
        "total_html": len(html_files),
        "html_with_graph_urls": remaining_graph_urls,
        "html_with_local_image_refs": local_image_refs,
        "total_image_files": len(image_files),
        "image_extensions": ext_counter,
        "sample_remaining": sample_remaining,
    }


def parse_failure_log(path: Path) -> Dict:
    if not path.exists():
        return {
            "exists": False,
            "total": 0,
            "by_code": Counter(),
            "sample": [],
        }

    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    by_code = Counter()
    for line in lines:
        code = line.split("\t", 1)[0]
        by_code[code] += 1

    return {
        "exists": True,
        "total": len(lines),
        "by_code": by_code,
        "sample": lines[:20],
    }


def build_report(root: Path, metrics: Dict, fail_info: Dict, sample_limit: int) -> str:
    lines = []
    lines.append("OneNote Export Validation Report")
    lines.append("=" * 32)
    lines.append(f"Root: {root}")
    lines.append("")

    lines.append("HTML Metrics")
    lines.append("-" * 12)
    lines.append(f"Total HTML files: {metrics['total_html']}")
    lines.append(f"HTML with remaining Graph URLs: {metrics['html_with_graph_urls']}")
    lines.append(f"HTML with local images references: {metrics['html_with_local_image_refs']}")
    lines.append("")

    lines.append("Image Metrics")
    lines.append("-" * 13)
    lines.append(f"Total files in images folders: {metrics['total_image_files']}")
    if metrics["image_extensions"]:
        lines.append("By extension:")
        for ext, count in metrics["image_extensions"].most_common():
            lines.append(f"  {ext}: {count}")
    else:
        lines.append("By extension: none")
    lines.append("")

    lines.append("Failure Log")
    lines.append("-" * 11)
    if fail_info["exists"]:
        lines.append(f"Failure log present: yes")
        lines.append(f"Total failure entries: {fail_info['total']}")
        if fail_info["by_code"]:
            lines.append("By code:")
            for code, count in fail_info["by_code"].most_common():
                lines.append(f"  {code}: {count}")
    else:
        lines.append("Failure log present: no")
    lines.append("")

    if metrics["html_with_graph_urls"] > 0:
        lines.append("Sample HTML still containing Graph URLs")
        lines.append("-" * 40)
        for path in metrics["sample_remaining"][:sample_limit]:
            lines.append(path)
        lines.append("")

    complete = metrics["html_with_graph_urls"] == 0
    lines.append("Overall Status")
    lines.append("-" * 14)
    lines.append("Complete: yes" if complete else "Complete: no")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    if not args.root.exists():
        raise RuntimeError(f"Root not found: {args.root}")

    metrics = count_html_metrics(args.root)
    fail_info = parse_failure_log(args.fail_log)
    report = build_report(args.root, metrics, fail_info, args.sample_limit)

    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report written to: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

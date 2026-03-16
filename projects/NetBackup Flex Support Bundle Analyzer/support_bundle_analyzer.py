from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import tarfile
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from io import BufferedReader
from pathlib import Path
from typing import Iterable

BUNDLE_PATTERN = re.compile(
    r"^sosreport-(?P<appliance>[^-]+)-(?P<timestamp>\d{14})-(?P<trigger>[^-]+)-(?P<tag>.+)\.tar\.xz$"
)

NETBACKUP_KEYWORDS = [
    "netbackup",
    "nbu",
    "veritas",
    "vnetd",
    "bp",
    "flex",
    "vcs",
    "vx",
]

ERROR_PATTERNS = [
    re.compile(r"\b(error|failed|failure|fatal|panic|critical)\b", re.IGNORECASE),
    re.compile(r"\b(warn|warning|degraded|timeout|timed out)\b", re.IGNORECASE),
]

TIMESTAMP_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?\b"),
    re.compile(r"\b[A-Z][a-z]{2} +\d{1,2} \d{2}:\d{2}:\d{2}\b"),
]

MAX_FILES_TO_SCAN = 2500
MAX_FILE_BYTES = 1_000_000
MAX_LINES_PER_FILE = 6000
TOP_ISSUES_COUNT = 25
WINDOWS_INVALID_CHARS = '<>:"/\\|?*'
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


@dataclass
class BundleMetadata:
    bundle_name: str
    appliance: str | None
    timestamp: str | None
    trigger: str | None
    tag: str | None


@dataclass
class AnalysisResult:
    analyzed_at_utc: str
    bundle_metadata: BundleMetadata
    extracted_root: str
    total_files_indexed: int
    files_scanned: int
    netbackup_related_files: list[str]
    host_name: str | None
    os_release: str | None
    first_timestamp_seen: str | None
    last_timestamp_seen: str | None
    error_lines_count: int
    warning_lines_count: int
    top_issue_patterns: list[dict[str, int | str]]
    notable_findings: list[str]


def parse_bundle_name(bundle_path: Path) -> BundleMetadata:
    m = BUNDLE_PATTERN.match(bundle_path.name)
    if not m:
        return BundleMetadata(
            bundle_name=bundle_path.name,
            appliance=None,
            timestamp=None,
            trigger=None,
            tag=None,
        )
    return BundleMetadata(
        bundle_name=bundle_path.name,
        appliance=m.group("appliance"),
        timestamp=m.group("timestamp"),
        trigger=m.group("trigger"),
        tag=m.group("tag"),
    )


def _is_safe_posix_member_path(name: str) -> bool:
    normalized = posixpath.normpath(name).replace("\\", "/")
    if normalized in ("", "."):
        return False
    if normalized.startswith("/"):
        return False
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if any(part == ".." for part in parts):
        return False
    return True


def _sanitize_windows_component(component: str) -> str:
    out = "".join("_" if ch in WINDOWS_INVALID_CHARS or ord(ch) < 32 else ch for ch in component)
    out = out.rstrip(" .")
    if not out:
        out = "_"
    stem = out.split(".", 1)[0]
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        out = f"_{out}"
    return out


def _member_relative_path(member_name: str, target_is_windows: bool) -> Path:
    normalized = posixpath.normpath(member_name).replace("\\", "/")
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if target_is_windows:
        parts = [_sanitize_windows_component(p) for p in parts]
    return Path(*parts)


def _dedupe_path(path: Path) -> Path:
    if not path.exists():
        return path

    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    idx = 1
    while True:
        candidate = parent / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def _extract_file(member: tarfile.TarInfo, file_obj: BufferedReader | None, out_path: Path) -> None:
    if file_obj is None:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    safe_out = _dedupe_path(out_path)
    with safe_out.open("wb") as out_f:
        while True:
            chunk = file_obj.read(1024 * 1024)
            if not chunk:
                break
            out_f.write(chunk)


def _safe_extractall(tf: tarfile.TarFile, destination: Path) -> None:
    target_is_windows = os.name == "nt"
    for member in tf.getmembers():
        if not _is_safe_posix_member_path(member.name):
            raise ValueError(f"Unsafe archive member path: {member.name}")

    for member in tf.getmembers():
        rel_path = _member_relative_path(member.name, target_is_windows)
        out_path = destination / rel_path

        if member.isdir():
            out_path.mkdir(parents=True, exist_ok=True)
            continue

        if member.issym() or member.islnk() or member.ischr() or member.isblk() or member.isfifo():
            # Skip special file types in a support bundle extraction on non-native hosts.
            continue

        file_obj = tf.extractfile(member)
        _extract_file(member, file_obj, out_path)


def extract_bundle(bundle_path: Path, output_dir: Path) -> Path:
    extract_root = output_dir / "extracted"
    extract_root.mkdir(parents=True, exist_ok=True)

    with tarfile.open(bundle_path, mode="r:xz") as tf:
        _safe_extractall(tf, extract_root)

    top_dirs = [p for p in extract_root.iterdir() if p.is_dir()]
    if len(top_dirs) == 1:
        return top_dirs[0]
    return extract_root


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            yield Path(dirpath) / name


def is_probably_text(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(2048)
        return b"\x00" not in chunk
    except OSError:
        return False


def normalize_issue_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?\b", "<ts>", line)
    line = re.sub(r"\b\d+\b", "<n>", line)
    line = re.sub(r"\s+", " ", line)
    return line[:300]


def find_timestamp(line: str) -> str | None:
    for pattern in TIMESTAMP_PATTERNS:
        m = pattern.search(line)
        if m:
            return m.group(0)
    return None


def load_hostname(root: Path) -> str | None:
    candidates = [
        root / "etc" / "hostname",
        root / "sos_commands" / "hostname" / "hostname",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            try:
                text = c.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    return text.splitlines()[0].strip()
            except OSError:
                pass
    return None


def load_os_release(root: Path) -> str | None:
    c = root / "etc" / "os-release"
    if not c.exists() or not c.is_file():
        return None
    try:
        text = c.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    name = None
    version = None
    for line in text.splitlines():
        if line.startswith("NAME=") and name is None:
            name = line.split("=", 1)[1].strip().strip('"')
        if line.startswith("VERSION=") and version is None:
            version = line.split("=", 1)[1].strip().strip('"')
    if name and version:
        return f"{name} {version}"
    if name:
        return name
    return None


def analyze(root: Path, bundle_metadata: BundleMetadata) -> AnalysisResult:
    files = list(iter_files(root))

    netbackup_related_files: list[str] = []
    issue_counter: Counter[str] = Counter()
    first_ts = None
    last_ts = None
    error_count = 0
    warning_count = 0

    scanned = 0

    for p in files:
        rel = p.relative_to(root).as_posix().lower()
        if any(k in rel for k in NETBACKUP_KEYWORDS):
            netbackup_related_files.append(p.relative_to(root).as_posix())

        if scanned >= MAX_FILES_TO_SCAN:
            continue
        if not p.is_file():
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            continue
        if not is_probably_text(p):
            continue

        scanned += 1
        try:
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f):
                    if i >= MAX_LINES_PER_FILE:
                        break
                    ts = find_timestamp(line)
                    if ts:
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts

                    if ERROR_PATTERNS[0].search(line):
                        error_count += 1
                        issue_counter[normalize_issue_line(line)] += 1
                    elif ERROR_PATTERNS[1].search(line):
                        warning_count += 1
                        issue_counter[normalize_issue_line(line)] += 1
        except OSError:
            continue

    top_issues = [
        {"pattern": pat, "count": count}
        for pat, count in issue_counter.most_common(TOP_ISSUES_COUNT)
        if pat
    ]

    notable_findings: list[str] = []
    if len(netbackup_related_files) == 0:
        notable_findings.append("No obvious NetBackup/Flex related file paths were detected.")
    else:
        notable_findings.append(
            f"Detected {len(netbackup_related_files)} NetBackup/Flex related files by path keyword match."
        )

    if error_count > 0:
        notable_findings.append(f"Detected {error_count} error-like log lines.")
    if warning_count > 0:
        notable_findings.append(f"Detected {warning_count} warning-like log lines.")

    if scanned >= MAX_FILES_TO_SCAN:
        notable_findings.append(
            f"Scan capped at {MAX_FILES_TO_SCAN} text files to keep runtime predictable."
        )

    return AnalysisResult(
        analyzed_at_utc=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        bundle_metadata=bundle_metadata,
        extracted_root=str(root),
        total_files_indexed=len(files),
        files_scanned=scanned,
        netbackup_related_files=sorted(set(netbackup_related_files))[:1500],
        host_name=load_hostname(root),
        os_release=load_os_release(root),
        first_timestamp_seen=first_ts,
        last_timestamp_seen=last_ts,
        error_lines_count=error_count,
        warning_lines_count=warning_count,
        top_issue_patterns=top_issues,
        notable_findings=notable_findings,
    )


def write_outputs(result: AnalysisResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(asdict(result), indent=2),
        encoding="utf-8",
    )

    report_lines: list[str] = []
    report_lines.append("# NetBackup Flex Support Bundle Analysis")
    report_lines.append("")
    report_lines.append(f"Analyzed at (UTC): {result.analyzed_at_utc}")
    report_lines.append(f"Bundle: {result.bundle_metadata.bundle_name}")
    report_lines.append("")
    report_lines.append("## Bundle Metadata")
    report_lines.append(f"- Appliance: {result.bundle_metadata.appliance or 'unknown'}")
    report_lines.append(f"- Timestamp: {result.bundle_metadata.timestamp or 'unknown'}")
    report_lines.append(f"- Trigger: {result.bundle_metadata.trigger or 'unknown'}")
    report_lines.append(f"- Tag: {result.bundle_metadata.tag or 'unknown'}")
    report_lines.append("")
    report_lines.append("## Environment")
    report_lines.append(f"- Hostname: {result.host_name or 'unknown'}")
    report_lines.append(f"- OS Release: {result.os_release or 'unknown'}")
    report_lines.append(f"- Extracted Root: {result.extracted_root}")
    report_lines.append("")
    report_lines.append("## Scan Stats")
    report_lines.append(f"- Total Files Indexed: {result.total_files_indexed}")
    report_lines.append(f"- Text Files Scanned: {result.files_scanned}")
    report_lines.append(f"- Error-like Lines: {result.error_lines_count}")
    report_lines.append(f"- Warning-like Lines: {result.warning_lines_count}")
    report_lines.append(f"- First Timestamp Seen: {result.first_timestamp_seen or 'not found'}")
    report_lines.append(f"- Last Timestamp Seen: {result.last_timestamp_seen or 'not found'}")
    report_lines.append("")
    report_lines.append("## Notable Findings")
    for finding in result.notable_findings:
        report_lines.append(f"- {finding}")
    report_lines.append("")

    report_lines.append("## Top Issue Patterns")
    if result.top_issue_patterns:
        for issue in result.top_issue_patterns:
            report_lines.append(f"- ({issue['count']}) {issue['pattern']}")
    else:
        report_lines.append("- None")
    report_lines.append("")

    report_lines.append("## Sample NetBackup/Flex Related Files")
    if result.netbackup_related_files:
        for rel in result.netbackup_related_files[:200]:
            report_lines.append(f"- {rel}")
    else:
        report_lines.append("- None")

    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")


def build_output_dir(bundle_path: Path, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg).resolve()
    stem = bundle_path.name.removesuffix(".tar.xz")
    return bundle_path.parent / f"{stem}_analysis"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract and analyze a NetBackup Flex appliance support bundle."
    )
    parser.add_argument("--bundle", required=True, help="Path to sosreport .tar.xz bundle")
    parser.add_argument("--output", required=False, help="Output folder for extracted data and reports")
    args = parser.parse_args()

    bundle_path = Path(args.bundle).resolve()
    if not bundle_path.exists() or not bundle_path.is_file():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    output_dir = build_output_dir(bundle_path, args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = parse_bundle_name(bundle_path)
    extracted_root = extract_bundle(bundle_path, output_dir)
    result = analyze(extracted_root, metadata)
    write_outputs(result, output_dir)

    print("Analysis complete")
    print(f"Output directory: {output_dir}")
    print(f"Report: {output_dir / 'report.md'}")
    print(f"Summary: {output_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

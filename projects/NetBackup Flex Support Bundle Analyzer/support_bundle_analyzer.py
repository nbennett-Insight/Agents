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
from typing import Any, Iterable

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

SKIP_DISK_PREFIXES = (
    "loop",
    "ram",
    "dm-",
    "sr",
    "md",
    "zd",
)

OBFUSCATION_PATTERNS = {
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "uuid": re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    ),
    "mac": re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b"),
    "serial": re.compile(r"\b(?:VTAS\d{6,}|[A-Z0-9]{12,})\b"),
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
    system_serial_number: str | None
    disk_io_summary: dict[str, Any]
    instance_details: dict[str, Any]
    network_details: dict[str, Any]
    failed_component_alerts: list[dict[str, str]]


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


def _extract_file(file_obj: BufferedReader | None, out_path: Path) -> None:
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
        _extract_file(file_obj, out_path)


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


def first_existing_file(root: Path, candidates: list[str]) -> Path | None:
    for rel in candidates:
        p = root / rel
        if p.exists() and p.is_file():
            return p
    return None


def read_text_limited(path: Path, max_bytes: int = MAX_FILE_BYTES) -> str:
    try:
        with path.open("rb") as f:
            raw = f.read(max_bytes)
        return raw.decode("utf-8", errors="ignore")
    except OSError:
        return ""


def extract_system_serial(root: Path) -> str | None:
    direct = first_existing_file(
        root,
        [
            "sys/class/dmi/id/product_serial",
            "sys/devices/virtual/dmi/id/product_serial",
        ],
    )
    if direct:
        text = read_text_limited(direct).strip()
        if text:
            return text.splitlines()[0].strip()

    dmidecode = first_existing_file(root, ["sos_commands/hardware/dmidecode"])
    if not dmidecode:
        return None
    text = read_text_limited(dmidecode)
    if not text:
        return None

    sys_section = re.search(r"System Information(.*?)(?:\nHandle\s+0x|\Z)", text, re.DOTALL)
    if sys_section:
        m = re.search(r"^\s*Serial Number:\s*(.+?)\s*$", sys_section.group(1), re.MULTILINE)
        if m and m.group(1).strip() and m.group(1).strip().lower() != "unknown":
            return m.group(1).strip()

    m = re.search(r"^\s*Serial Number:\s*(.+?)\s*$", text, re.MULTILINE)
    if m and m.group(1).strip() and m.group(1).strip().lower() != "unknown":
        return m.group(1).strip()
    return None


def parse_disk_io(root: Path) -> dict[str, Any]:
    diskstats = first_existing_file(root, ["proc/diskstats"])
    if not diskstats:
        return {
            "source": None,
            "device_count": 0,
            "top_devices_by_io": [],
        }

    devices: list[dict[str, Any]] = []
    try:
        with diskstats.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 14:
                    continue
                dev = parts[2]
                if dev.startswith(SKIP_DISK_PREFIXES):
                    continue
                try:
                    reads_completed = int(parts[3])
                    writes_completed = int(parts[7])
                    sectors_read = int(parts[5])
                    sectors_written = int(parts[9])
                    ms_io = int(parts[12])
                except ValueError:
                    continue
                total_ios = reads_completed + writes_completed
                devices.append(
                    {
                        "device": dev,
                        "reads_completed": reads_completed,
                        "writes_completed": writes_completed,
                        "sectors_read": sectors_read,
                        "sectors_written": sectors_written,
                        "time_spent_doing_io_ms": ms_io,
                        "total_io_ops": total_ios,
                    }
                )
    except OSError:
        return {
            "source": str(diskstats.relative_to(root).as_posix()),
            "device_count": 0,
            "top_devices_by_io": [],
        }

    devices.sort(key=lambda d: d["total_io_ops"], reverse=True)
    return {
        "source": str(diskstats.relative_to(root).as_posix()),
        "device_count": len(devices),
        "top_devices_by_io": devices[:12],
    }


def parse_podman_instances(root: Path) -> dict[str, Any]:
    ps_path = first_existing_file(root, ["sos_commands/podman/podman_ps"])
    pod_path = first_existing_file(root, ["sos_commands/podman/podman_pod_ps"])
    stats_path = first_existing_file(root, ["sos_commands/podman/podman_stats_--no-stream_--all"])

    instances: list[dict[str, str]] = []
    unhealthy: list[str] = []
    if ps_path:
        text = read_text_limited(ps_path)
        for line in text.splitlines()[1:]:
            if not line.strip():
                continue
            cols = re.split(r"\s{2,}", line.strip())
            if len(cols) < 2:
                continue
            name = cols[-1]
            status = cols[4] if len(cols) > 5 else (cols[2] if len(cols) > 3 else "unknown")
            instances.append(
                {
                    "name": name,
                    "status": status,
                    "id": cols[0],
                    "image": cols[1],
                }
            )
            if "unhealthy" in line.lower() or "exited" in line.lower() or "dead" in line.lower():
                unhealthy.append(name)

    pods: list[dict[str, str]] = []
    if pod_path:
        text = read_text_limited(pod_path)
        for line in text.splitlines()[1:]:
            if not line.strip():
                continue
            cols = re.split(r"\s{2,}", line.strip())
            if len(cols) < 3:
                continue
            pods.append(
                {
                    "pod_id": cols[0],
                    "name": cols[1],
                    "status": cols[2],
                }
            )

    top_resources: list[dict[str, str]] = []
    if stats_path:
        text = read_text_limited(stats_path)
        for line in text.splitlines()[1:]:
            if not line.strip():
                continue
            cols = re.split(r"\s{2,}", line.strip())
            if len(cols) < 4:
                continue
            top_resources.append(
                {
                    "name": cols[1],
                    "cpu_percent": cols[2],
                    "mem_usage_limit": cols[3],
                    "mem_percent": cols[4] if len(cols) > 4 else "unknown",
                }
            )
        top_resources.sort(
            key=lambda r: float(r["cpu_percent"].replace("%", "")) if r["cpu_percent"].endswith("%") else 0.0,
            reverse=True,
        )

    return {
        "container_count": len(instances),
        "pod_count": len(pods),
        "unhealthy_or_stopped_containers": sorted(set(unhealthy)),
        "top_containers_by_cpu": top_resources[:10],
    }


def parse_network_details(root: Path) -> dict[str, Any]:
    ip_addr = first_existing_file(root, ["sos_commands/networking/ip_-d_address"])
    ip_route = first_existing_file(root, ["sos_commands/networking/ip_route_show_table_all"])

    interfaces: list[dict[str, Any]] = []
    down_interfaces: list[str] = []
    if ip_addr:
        current: dict[str, Any] | None = None
        for line in read_text_limited(ip_addr).splitlines():
            m = re.match(r"^(\d+):\s+([^:]+):\s+<([^>]*)>.*\bstate\s+(\S+)", line)
            if m:
                if current:
                    interfaces.append(current)
                name = m.group(2)
                state = m.group(4)
                flags = [f.strip() for f in m.group(3).split(",") if f.strip()]
                current = {
                    "name": name,
                    "state": state,
                    "flags": flags,
                    "ipv4": [],
                    "ipv6": [],
                }
                if state.upper() in ("DOWN", "DORMANT") or "NO-CARRIER" in flags:
                    down_interfaces.append(name)
                continue

            if current is None:
                continue
            m4 = re.search(r"\binet\s+([^\s]+)", line)
            if m4:
                current["ipv4"].append(m4.group(1))
            m6 = re.search(r"\binet6\s+([^\s]+)", line)
            if m6:
                current["ipv6"].append(m6.group(1))

        if current:
            interfaces.append(current)

    routes: list[str] = []
    default_route = None
    if ip_route:
        for line in read_text_limited(ip_route).splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            routes.append(stripped)
            if stripped.startswith("default ") and default_route is None:
                default_route = stripped

    ethtool_mgmt = first_existing_file(root, ["sos_commands/networking/ethtool_mgmt0"])
    link_speed = None
    link_detected = None
    if ethtool_mgmt:
        text = read_text_limited(ethtool_mgmt)
        m_speed = re.search(r"^\s*Speed:\s*(.+)$", text, re.MULTILINE)
        m_link = re.search(r"^\s*Link detected:\s*(.+)$", text, re.MULTILINE)
        if m_speed:
            link_speed = m_speed.group(1).strip()
        if m_link:
            link_detected = m_link.group(1).strip()

    return {
        "interface_count": len(interfaces),
        "interfaces": interfaces[:40],
        "down_or_no_carrier_interfaces": sorted(set(down_interfaces)),
        "default_route": default_route,
        "route_sample": routes[:80],
        "mgmt0_link_speed": link_speed,
        "mgmt0_link_detected": link_detected,
    }


def parse_failed_components(root: Path, instance_details: dict[str, Any], network_details: dict[str, Any]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []

    for name in instance_details.get("unhealthy_or_stopped_containers", []):
        alerts.append(
            {
                "severity": "warning",
                "component": "container",
                "message": f"Container state issue detected: {name}",
            }
        )

    down = network_details.get("down_or_no_carrier_interfaces", [])
    if down:
        alerts.append(
            {
                "severity": "warning",
                "component": "network",
                "message": f"Interfaces down or no-carrier: {', '.join(down[:12])}",
            }
        )

    multipath = first_existing_file(root, ["sos_commands/multipath/multipath_-ll"])
    if multipath:
        for line in read_text_limited(multipath).splitlines():
            low = line.lower()
            if any(k in low for k in ["not loaded", "failed", "fault", "degraded", "error"]):
                alerts.append(
                    {
                        "severity": "warning",
                        "component": "multipath",
                        "message": line.strip(),
                    }
                )

    ata_dir = root / "sos_commands" / "ata"
    if ata_dir.exists() and ata_dir.is_dir():
        for p in ata_dir.glob("smartctl_-a_*.dev.*"):
            text = read_text_limited(p)
            for line in text.splitlines():
                low = line.lower()
                if "smart support is:" in low and ("unavailable" in low or "disabled" in low):
                    alerts.append(
                        {
                            "severity": "warning",
                            "component": "disk",
                            "message": f"{p.name}: {line.strip()}",
                        }
                    )
                    break

    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for alert in alerts:
        key = f"{alert['component']}::{alert['message']}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(alert)
    return deduped[:150]


class Obfuscator:
    def __init__(self) -> None:
        self.maps: dict[str, dict[str, str]] = {
            "ipv4": {},
            "uuid": {},
            "mac": {},
            "serial": {},
        }
        self.counts: dict[str, int] = {
            "ipv4": 0,
            "uuid": 0,
            "mac": 0,
            "serial": 0,
        }

    def _replace_token(self, token_type: str, value: str) -> str:
        mapping = self.maps[token_type]
        if value in mapping:
            return mapping[value]
        self.counts[token_type] += 1
        tag = f"<{token_type.upper()}_{self.counts[token_type]:03d}>"
        mapping[value] = tag
        return tag

    def obfuscate_text(self, text: str) -> str:
        result = text
        for token_type, pattern in OBFUSCATION_PATTERNS.items():
            result = pattern.sub(lambda m: self._replace_token(token_type, m.group(0)), result)
        return result

    def obfuscate_data(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.obfuscate_text(value)
        if isinstance(value, list):
            return [self.obfuscate_data(v) for v in value]
        if isinstance(value, dict):
            return {k: self.obfuscate_data(v) for k, v in value.items()}
        return value


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

    system_serial = extract_system_serial(root)
    disk_io = parse_disk_io(root)
    instances = parse_podman_instances(root)
    network = parse_network_details(root)
    failed_alerts = parse_failed_components(root, instances, network)

    if system_serial:
        notable_findings.append("System serial number extracted.")
    if instances.get("unhealthy_or_stopped_containers"):
        notable_findings.append(
            f"Detected {len(instances['unhealthy_or_stopped_containers'])} unhealthy or stopped containers."
        )
    if failed_alerts:
        notable_findings.append(f"Generated {len(failed_alerts)} component alerts/warnings.")

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
        system_serial_number=system_serial,
        disk_io_summary=disk_io,
        instance_details=instances,
        network_details=network,
        failed_component_alerts=failed_alerts,
    )


def write_outputs(result: AnalysisResult, output_dir: Path, obfuscate: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = asdict(result)
    if obfuscate:
        payload = Obfuscator().obfuscate_data(payload)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    bundle_meta = payload["bundle_metadata"]

    report_lines: list[str] = []
    report_lines.append("# NetBackup Flex Support Bundle Analysis")
    report_lines.append("")
    report_lines.append(f"Analyzed at (UTC): {payload['analyzed_at_utc']}")
    report_lines.append(f"Bundle: {bundle_meta['bundle_name']}")
    report_lines.append(f"Obfuscated Output: {'enabled' if obfuscate else 'disabled'}")
    report_lines.append("")
    report_lines.append("## Bundle Metadata")
    report_lines.append(f"- Appliance: {bundle_meta['appliance'] or 'unknown'}")
    report_lines.append(f"- Timestamp: {bundle_meta['timestamp'] or 'unknown'}")
    report_lines.append(f"- Trigger: {bundle_meta['trigger'] or 'unknown'}")
    report_lines.append(f"- Tag: {bundle_meta['tag'] or 'unknown'}")
    report_lines.append("")
    report_lines.append("## Environment")
    report_lines.append(f"- Hostname: {payload['host_name'] or 'unknown'}")
    report_lines.append(f"- OS Release: {payload['os_release'] or 'unknown'}")
    report_lines.append(f"- Extracted Root: {payload['extracted_root']}")
    report_lines.append(f"- System Serial Number: {payload['system_serial_number'] or 'unknown'}")
    report_lines.append("")
    report_lines.append("## Scan Stats")
    report_lines.append(f"- Total Files Indexed: {payload['total_files_indexed']}")
    report_lines.append(f"- Text Files Scanned: {payload['files_scanned']}")
    report_lines.append(f"- Error-like Lines: {payload['error_lines_count']}")
    report_lines.append(f"- Warning-like Lines: {payload['warning_lines_count']}")
    report_lines.append(f"- First Timestamp Seen: {payload['first_timestamp_seen'] or 'not found'}")
    report_lines.append(f"- Last Timestamp Seen: {payload['last_timestamp_seen'] or 'not found'}")
    report_lines.append("")

    report_lines.append("## Disk I/O Summary")
    disk = payload["disk_io_summary"]
    report_lines.append(f"- Source: {disk['source'] or 'not found'}")
    report_lines.append(f"- Device Count: {disk['device_count']}")
    if disk["top_devices_by_io"]:
        report_lines.append("- Top Devices By Total I/O Ops:")
        for d in disk["top_devices_by_io"]:
            report_lines.append(
                "  - "
                f"{d['device']}: total_ops={d['total_io_ops']}, "
                f"reads={d['reads_completed']}, writes={d['writes_completed']}, "
                f"io_ms={d['time_spent_doing_io_ms']}"
            )
    else:
        report_lines.append("- No disk I/O entries parsed")
    report_lines.append("")

    report_lines.append("## Instance Details")
    instances = payload["instance_details"]
    report_lines.append(f"- Container Count: {instances['container_count']}")
    report_lines.append(f"- Pod Count: {instances['pod_count']}")
    if instances["unhealthy_or_stopped_containers"]:
        report_lines.append("- Unhealthy/Stopped Containers:")
        for c in instances["unhealthy_or_stopped_containers"]:
            report_lines.append(f"  - {c}")
    else:
        report_lines.append("- Unhealthy/Stopped Containers: none")

    report_lines.append("- Top Containers By CPU:")
    if instances["top_containers_by_cpu"]:
        for c in instances["top_containers_by_cpu"]:
            report_lines.append(
                f"  - {c['name']}: cpu={c['cpu_percent']}, mem={c['mem_usage_limit']}, mem%={c['mem_percent']}"
            )
    else:
        report_lines.append("  - none")
    report_lines.append("")

    report_lines.append("## Network Details")
    network = payload["network_details"]
    report_lines.append(f"- Interface Count: {network['interface_count']}")
    report_lines.append(f"- Default Route: {network['default_route'] or 'not found'}")
    report_lines.append(f"- mgmt0 Link Speed: {network['mgmt0_link_speed'] or 'unknown'}")
    report_lines.append(f"- mgmt0 Link Detected: {network['mgmt0_link_detected'] or 'unknown'}")
    if network["down_or_no_carrier_interfaces"]:
        report_lines.append("- Down/No-Carrier Interfaces:")
        for name in network["down_or_no_carrier_interfaces"]:
            report_lines.append(f"  - {name}")
    else:
        report_lines.append("- Down/No-Carrier Interfaces: none")

    report_lines.append("- Interface Address Summary:")
    for iface in network["interfaces"][:20]:
        v4 = ", ".join(iface["ipv4"]) if iface["ipv4"] else "none"
        report_lines.append(f"  - {iface['name']} [{iface['state']}] ipv4={v4}")
    report_lines.append("")

    report_lines.append("## Failed Components And Alerts")
    alerts = payload["failed_component_alerts"]
    if alerts:
        for alert in alerts:
            report_lines.append(
                f"- [{alert['severity'].upper()}] {alert['component']}: {alert['message']}"
            )
    else:
        report_lines.append("- No component failure alerts detected")
    report_lines.append("")

    report_lines.append("## Notable Findings")
    for finding in payload["notable_findings"]:
        report_lines.append(f"- {finding}")
    report_lines.append("")

    report_lines.append("## Top Issue Patterns")
    if payload["top_issue_patterns"]:
        for issue in payload["top_issue_patterns"]:
            report_lines.append(f"- ({issue['count']}) {issue['pattern']}")
    else:
        report_lines.append("- None")
    report_lines.append("")

    report_lines.append("## Sample NetBackup/Flex Related Files")
    if payload["netbackup_related_files"]:
        for rel in payload["netbackup_related_files"][:200]:
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
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--bundle", required=False, help="Path to sosreport .tar.xz bundle")
    source_group.add_argument(
        "--extracted-root",
        required=False,
        help="Path to an already extracted sosreport root directory",
    )
    parser.add_argument("--output", required=False, help="Output folder for extracted data and reports")
    parser.add_argument(
        "--obfuscate",
        action="store_true",
        help="Redact sensitive values (serials, IPs, MACs, UUIDs) in report and summary output",
    )
    args = parser.parse_args()

    if args.bundle:
        bundle_path = Path(args.bundle).resolve()
        if not bundle_path.exists() or not bundle_path.is_file():
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")
        output_dir = build_output_dir(bundle_path, args.output)
        metadata = parse_bundle_name(bundle_path)
        extracted_root = extract_bundle(bundle_path, output_dir)
    else:
        extracted_root = Path(args.extracted_root).resolve()
        if not extracted_root.exists() or not extracted_root.is_dir():
            raise FileNotFoundError(f"Extracted root not found: {extracted_root}")
        output_dir = Path(args.output).resolve() if args.output else extracted_root / "analysis_output"
        metadata = parse_bundle_name(Path(extracted_root.name + ".tar.xz"))

    output_dir.mkdir(parents=True, exist_ok=True)
    result = analyze(extracted_root, metadata)
    write_outputs(result, output_dir, obfuscate=args.obfuscate)

    print("Analysis complete")
    print(f"Output directory: {output_dir}")
    print(f"Report: {output_dir / 'report.md'}")
    print(f"Summary: {output_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

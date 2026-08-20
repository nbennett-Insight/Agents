from __future__ import annotations

import argparse
import html
import json
import os
import posixpath
import re
import tarfile
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
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
MAX_PROBLEM_SAMPLES = 8
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
    typical_problem_findings: list[dict[str, Any]]
    report_card: dict[str, Any]


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


def parse_hardware_disk_failures(root: Path) -> list[dict[str, str]]:
    # ASC logs may contain disk health in JSON snippets or table-like lines.
    candidate_files: list[Path] = []

    autosupport_file = root / "var" / "log" / "asc" / "autosupport" / "asc_monitor.log"
    if autosupport_file.exists() and autosupport_file.is_file():
        candidate_files.append(autosupport_file)

    app_vxul_dir = root / "var" / "log" / "asc" / "app_vxul"
    if app_vxul_dir.exists() and app_vxul_dir.is_dir():
        candidate_files.extend(sorted(app_vxul_dir.glob("*.log"))[:30])

    if not candidate_files:
        return []

    failed_disks: list[dict[str, str]] = []
    seen: set[str] = set()

    block_pattern = re.compile(
        r'"id"\s*:\s*"(?P<disk_id>Controller\s+\d+\s+Enclosure\s+\d+\s+Disk\s+\d+)"\s*,\s*"properties"\s*:\s*\{(?P<props>[^{}]{1,1800})\}',
        re.IGNORECASE,
    )
    serial_pattern = re.compile(r'"Serial Number"\s*:\s*"(?P<serial>[^"]+)"', re.IGNORECASE)
    state_pattern = re.compile(r'"State"\s*:\s*"(?P<state>[^"]+)"', re.IGNORECASE)
    status_pattern = re.compile(r'"Status"\s*:\s*"(?P<status>[^"]+)"', re.IGNORECASE)
    fw_pattern = re.compile(r'"Firmware Version"\s*:\s*"(?P<fw>[^"]+)"', re.IGNORECASE)

    for src in candidate_files:
        text = read_text_limited(src, max_bytes=5_000_000)
        if not text:
            continue

        for m in block_pattern.finditer(text):
            disk_id = m.group("disk_id").strip()
            props = m.group("props")

            state = "unknown"
            status = "unknown"
            serial = "unknown"
            firmware = "unknown"

            m_state = state_pattern.search(props)
            if m_state:
                state = m_state.group("state").strip()

            m_status = status_pattern.search(props)
            if m_status:
                status = m_status.group("status").strip()

            m_serial = serial_pattern.search(props)
            if m_serial:
                serial = m_serial.group("serial").strip()

            m_fw = fw_pattern.search(props)
            if m_fw:
                firmware = m_fw.group("fw").strip()

            if state.lower() != "failed":
                continue

            key = f"{disk_id}::{serial}"
            if key in seen:
                continue
            seen.add(key)

            failed_disks.append(
                {
                    "disk_id": disk_id,
                    "serial_number": serial,
                    "state": state,
                    "status": status,
                    "firmware": firmware,
                    "source": src.relative_to(root).as_posix(),
                }
            )

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("||"):
                continue
            if "Controller" not in stripped or "Disk" not in stripped:
                continue
            if "| Failed |" not in stripped and not stripped.endswith("| Failed | |"):
                continue

            cols = [c.strip() for c in stripped.strip("|").split("|")]
            if not cols:
                continue

            disk_id = cols[0]
            serial = "unknown"
            firmware = "unknown"
            status = "unknown"
            for c in cols:
                if re.fullmatch(r"[A-Z0-9]{10,}", c):
                    serial = c
                if re.fullmatch(r"[A-Z0-9]{4}", c):
                    firmware = c
            if len(cols) > 2:
                status = cols[2]

            key = f"{disk_id}::{serial}"
            if key in seen:
                continue
            seen.add(key)

            failed_disks.append(
                {
                    "disk_id": disk_id,
                    "serial_number": serial,
                    "state": "Failed",
                    "status": status,
                    "firmware": firmware,
                    "source": src.relative_to(root).as_posix(),
                }
            )

    return failed_disks[:80]


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

    for failed_disk in parse_hardware_disk_failures(root):
        alerts.append(
            {
                "severity": "critical",
                "component": "hardware-disk",
                "message": (
                    f"{failed_disk['disk_id']} state={failed_disk['state']}, "
                    f"status={failed_disk['status']}, fw={failed_disk['firmware']}, "
                    f"serial={failed_disk['serial_number']} "
                    f"(source={failed_disk['source']})"
                ),
            }
        )

    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for alert in alerts:
        key = f"{alert['component']}::{alert['message']}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(alert)
    return deduped[:150]


TYPICAL_PROBLEM_PATTERNS = [
    (
        "bad_hdd_ssd",
        "critical",
        "Bad HDD/SSD",
        re.compile(
            r"\b(SMART.*fail|medium error|media error|uncorrectable|I/O error|Buffer I/O error|blk_update_request|critical warning|predictive failure)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "ram_ecc",
        "critical",
        "RAM ECC/MCE",
        re.compile(r"\b(EDAC|MCE|Machine check|memory error|ECC error|uncorrected error|corrected error)\b", re.IGNORECASE),
    ),
    (
        "crc_error",
        "warning",
        "CRC / Link Error",
        re.compile(r"\b(CRC|link reset|hard resetting link|ata\d+.*error|SAS.*error|PCIe Bus Error)\b", re.IGNORECASE),
    ),
    (
        "time_shift",
        "warning",
        "Time Shift",
        re.compile(r"\b(Time has been changed|time shift|clock.*jump|Clocksource.*unstable|chrony.*(?:step|slew)|NTP.*(?:step|offset))\b", re.IGNORECASE),
    ),
    (
        "dmesg_issue",
        "critical",
        "dmesg Kernel Issue",
        re.compile(r"\b(BUG:|Oops|kernel panic|Call Trace|hung task|blocked for more than|segfault|soft lockup|hard lockup)\b", re.IGNORECASE),
    ),
    (
        "warnings",
        "warning",
        "Warnings",
        re.compile(r"\b(warn|warning|degraded|timeout|timed out)\b", re.IGNORECASE),
    ),
    (
        "errors",
        "critical",
        "Errors",
        re.compile(r"\b(error|failed|failure|fatal|critical)\b", re.IGNORECASE),
    ),
]


def _problem_record(category: str, label: str, severity: str) -> dict[str, Any]:
    return {
        "category": category,
        "label": label,
        "severity": severity,
        "count": 0,
        "samples": [],
    }


def _add_problem_sample(records: dict[str, dict[str, Any]], category: str, label: str, severity: str, source: str, line: str) -> None:
    record = records.setdefault(category, _problem_record(category, label, severity))
    record["count"] += 1
    samples = record["samples"]
    sample = {"source": source, "line": line.strip()[:500]}
    if len(samples) < MAX_PROBLEM_SAMPLES and sample not in samples:
        samples.append(sample)


def _scan_problem_file(records: dict[str, dict[str, Any]], root: Path, path: Path, max_lines: int = MAX_LINES_PER_FILE) -> None:
    rel = path.relative_to(root).as_posix()
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line_number, line in enumerate(f, start=1):
                if line_number > max_lines:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                for category, severity, label, pattern in TYPICAL_PROBLEM_PATTERNS:
                    if pattern.search(stripped):
                        _add_problem_sample(records, category, label, severity, f"{rel}:{line_number}", stripped)
    except OSError:
        return


def _scan_smart_health(records: dict[str, dict[str, Any]], root: Path, smart_path: Path) -> None:
    rel = smart_path.relative_to(root).as_posix()
    text = read_text_limited(smart_path)
    if not text:
        return

    interesting_fields = [
        "SMART overall-health self-assessment test result",
        "Critical Warning",
        "Media and Data Integrity Errors",
        "Error Information Log Entries",
        "Reallocated_Sector_Ct",
        "Current_Pending_Sector",
        "Offline_Uncorrectable",
        "UDMA_CRC_Error_Count",
    ]
    for line in text.splitlines():
        stripped = line.strip()
        if not any(field.lower() in stripped.lower() for field in interesting_fields):
            continue
        low = stripped.lower()
        if "passed" in low or stripped.endswith(":    0") or stripped.endswith(":      0") or stripped.endswith(":    0x00"):
            continue
        category = "crc_error" if "crc" in low else "bad_hdd_ssd"
        label = "CRC / Link Error" if category == "crc_error" else "Bad HDD/SSD"
        severity = "warning" if category == "crc_error" else "critical"
        _add_problem_sample(records, category, label, severity, rel, stripped)


def parse_typical_problem_findings(root: Path, failed_alerts: list[dict[str, str]]) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}

    for alert in failed_alerts:
        if alert.get("component") == "hardware-disk":
            source, clean_message = _alert_source_and_message(alert)
            _add_problem_sample(
                records,
                "bad_hdd_ssd",
                "Bad HDD/SSD",
                "critical",
                source or "failed_component_alerts",
                clean_message,
            )

    candidate_files = [
        root / "sos_commands" / "kernel" / "dmesg",
        root / "sos_commands" / "kernel" / "dmesg_-T",
        root / "var" / "log" / "messages",
        root / "var" / "log" / "secure",
        root / "var" / "log" / "kdump.log",
    ]
    for path in candidate_files:
        if path.exists() and path.is_file() and is_probably_text(path):
            _scan_problem_file(records, root, path)

    smart_dirs = [root / "sos_commands" / "nvme", root / "sos_commands" / "ata"]
    for smart_dir in smart_dirs:
        if not smart_dir.exists() or not smart_dir.is_dir():
            continue
        for smart_path in sorted(smart_dir.glob("smartctl*")):
            if smart_path.is_file() and "-j" not in smart_path.name:
                _scan_smart_health(records, root, smart_path)

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(
        records.values(),
        key=lambda r: (severity_order.get(str(r["severity"]), 9), str(r["label"])),
    )


def _parse_dmidecode_block(text: str, title: str) -> dict[str, str]:
    m = re.search(rf"^\s*{re.escape(title)}\s*$(.*?)(?:^Handle\s+0x|\Z)", text, re.MULTILINE | re.DOTALL)
    if not m:
        return {}
    block: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            block[key] = value
    return block


def _read_release_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    text = read_text_limited(path)
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def _smart_field(text: str, field: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip()


def build_report_card(
    root: Path,
    bundle_metadata: BundleMetadata,
    host_name: str | None,
    os_release: str | None,
    system_serial: str | None,
    network_details: dict[str, Any],
) -> dict[str, Any]:
    ip_addresses = sorted(
        {
            ip
            for iface in network_details.get("interfaces", [])
            for ip in iface.get("ipv4", [])
            if ip
        }
    )
    rows: list[dict[str, str]] = []

    dmidecode = first_existing_file(root, ["sos_commands/hardware/dmidecode"])
    system_info: dict[str, str] = {}
    if dmidecode:
        dmi_text = read_text_limited(dmidecode, max_bytes=5_000_000)
        system_info = _parse_dmidecode_block(dmi_text, "System Information")
        bios_info = _parse_dmidecode_block(dmi_text, "BIOS Information")
        board_info = _parse_dmidecode_block(dmi_text, "Base Board Information")

        if system_info:
            rows.append(
                {
                    "component": "Appliance",
                    "device_name": system_info.get("Product Name", bundle_metadata.appliance or "unknown"),
                    "version": system_info.get("Version", "unknown"),
                    "firmware": "",
                    "serial": system_info.get("Serial Number", system_serial or "unknown"),
                    "source": dmidecode.relative_to(root).as_posix(),
                }
            )
        if bios_info:
            rows.append(
                {
                    "component": "BIOS",
                    "device_name": bios_info.get("Vendor", "BIOS"),
                    "version": bios_info.get("Version", "unknown"),
                    "firmware": bios_info.get("Release Date", ""),
                    "serial": "",
                    "source": dmidecode.relative_to(root).as_posix(),
                }
            )
        if board_info:
            rows.append(
                {
                    "component": "Baseboard",
                    "device_name": board_info.get("Product Name", "Baseboard"),
                    "version": board_info.get("Version", "unknown"),
                    "firmware": "",
                    "serial": board_info.get("Serial Number", ""),
                    "source": dmidecode.relative_to(root).as_posix(),
                }
            )

    os_source = first_existing_file(root, ["etc/os-release"])
    if os_release:
        rows.append(
            {
                "component": "Operating System",
                "device_name": host_name or bundle_metadata.appliance or "host",
                "version": os_release,
                "firmware": "",
                "serial": system_serial or "",
                "source": os_source.relative_to(root).as_posix() if os_source else "etc/os-release",
            }
        )

    for rel_path, component in [("etc/flex-release", "Flex"), ("etc/vxos-release", "VxOS")]:
        release_file = root / rel_path
        if release_file.exists() and release_file.is_file():
            values = _read_release_key_values(release_file)
            rows.append(
                {
                    "component": component,
                    "device_name": values.get("product-name", component),
                    "version": values.get("product-version") or values.get("vxos-core-release") or "unknown",
                    "firmware": values.get("flex-core-buildtag") or values.get("vxos-core-buildtag") or "",
                    "serial": system_serial or "",
                    "source": rel_path,
                }
            )

    uname = first_existing_file(root, ["sos_commands/kernel/uname_-a"])
    if uname:
        rows.append(
            {
                "component": "Kernel",
                "device_name": host_name or bundle_metadata.appliance or "host",
                "version": read_text_limited(uname).strip()[:240],
                "firmware": "",
                "serial": "",
                "source": uname.relative_to(root).as_posix(),
            }
        )

    for smart_dir in [root / "sos_commands" / "nvme", root / "sos_commands" / "ata"]:
        if not smart_dir.exists() or not smart_dir.is_dir():
            continue
        for smart_path in sorted(smart_dir.glob("smartctl*")):
            if not smart_path.is_file() or "-j" in smart_path.name:
                continue
            text = read_text_limited(smart_path)
            model = _smart_field(text, "Model Number") or _smart_field(text, "Device Model") or smart_path.name
            serial = _smart_field(text, "Serial Number") or ""
            firmware = _smart_field(text, "Firmware Version") or ""
            health = _smart_field(text, "SMART overall-health self-assessment test result") or ""
            device_match = re.search(r"\.dev\.([^_]+)", smart_path.name)
            device = device_match.group(1) if device_match else smart_path.name
            rows.append(
                {
                    "component": "Storage",
                    "device_name": f"{device} - {model}",
                    "version": health or "SMART data",
                    "firmware": firmware,
                    "serial": serial,
                    "source": smart_path.relative_to(root).as_posix(),
                }
            )

    device_name = system_info.get("Product Name") or bundle_metadata.appliance or host_name or "unknown"
    return {
        "device_name": device_name,
        "hostname": host_name,
        "ip_addresses": ip_addresses,
        "software_firmware_versions": rows[:120],
    }


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

    host_name = load_hostname(root)
    os_release = load_os_release(root)
    system_serial = extract_system_serial(root)
    disk_io = parse_disk_io(root)
    instances = parse_podman_instances(root)
    network = parse_network_details(root)
    failed_alerts = parse_failed_components(root, instances, network)
    typical_problems = parse_typical_problem_findings(root, failed_alerts)
    report_card = build_report_card(root, bundle_metadata, host_name, os_release, system_serial, network)
    hardware_disk_failures = sum(1 for a in failed_alerts if a.get("component") == "hardware-disk")

    if system_serial:
        notable_findings.append("System serial number extracted.")
    if instances.get("unhealthy_or_stopped_containers"):
        notable_findings.append(
            f"Detected {len(instances['unhealthy_or_stopped_containers'])} unhealthy or stopped containers."
        )
    if failed_alerts:
        notable_findings.append(f"Generated {len(failed_alerts)} component alerts/warnings.")
    if hardware_disk_failures:
        notable_findings.append(f"Detected {hardware_disk_failures} failed hardware disk alerts from ASC logs.")
    if typical_problems:
        notable_findings.append(f"Detected {len(typical_problems)} typical hardware datacollect problem categories.")

    return AnalysisResult(
        analyzed_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        bundle_metadata=bundle_metadata,
        extracted_root=str(root),
        total_files_indexed=len(files),
        files_scanned=scanned,
        netbackup_related_files=sorted(set(netbackup_related_files))[:1500],
        host_name=host_name,
        os_release=os_release,
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
        typical_problem_findings=typical_problems,
        report_card=report_card,
    )


def _alert_source_and_message(alert: dict[str, str]) -> tuple[str, str]:
    message = alert.get("message", "")
    m = re.search(r"\s*\(source=([^\)]+)\)\s*$", message)
    if not m:
        return "", message
    source = m.group(1).strip()
    clean_message = message[: m.start()].rstrip()
    return source, clean_message


def _html_text(value: Any, default: str = "unknown") -> str:
    if value is None or value == "":
        return html.escape(default)
    return html.escape(str(value))


def _html_list(items: Iterable[Any], empty: str = "None") -> str:
    rows = [f"<li>{_html_text(item)}</li>" for item in items]
    return "".join(rows) if rows else f"<li>{html.escape(empty)}</li>"


def _severity_badge(severity: str) -> str:
    normalized = severity.lower()
    if normalized == "critical":
        label = "Critical"
        badge_class = "critical"
    elif normalized == "warning":
        label = "Warning"
        badge_class = "warning"
    else:
        label = severity.title() if severity else "Info"
        badge_class = "info"
    return f'<span class="badge {badge_class}">{html.escape(label)}</span>'


def render_html_report(payload: dict[str, Any], obfuscate: bool) -> str:
    bundle_meta = payload["bundle_metadata"]
    disk = payload["disk_io_summary"]
    instances = payload["instance_details"]
    network = payload["network_details"]
    alerts = payload["failed_component_alerts"]
    top_issues = payload.get("top_issue_patterns", [])
    findings = payload.get("notable_findings", [])
    typical_problems = payload.get("typical_problem_findings", [])
    report_card = payload.get("report_card", {})
    version_rows = report_card.get("software_firmware_versions", [])

    severity_counts = Counter(str(alert.get("severity", "info")).lower() for alert in alerts)
    severity_counts.update(str(problem.get("severity", "info")).lower() for problem in typical_problems)
    critical_count = severity_counts.get("critical", 0)
    warning_count = severity_counts.get("warning", 0)
    info_count = len(findings)

    alert_copy_lines: list[str] = []
    alert_rows: list[str] = []
    sources: list[str] = []
    for alert in alerts:
        source, clean_message = _alert_source_and_message(alert)
        if source:
            sources.append(source)
        severity = str(alert.get("severity", "info"))
        component = str(alert.get("component", ""))
        alert_copy_lines.append(f"[{severity.upper()}] {component}: {clean_message}" + (f" ({source})" if source else ""))
        alert_rows.append(
            "<tr>"
            f"<td>{_severity_badge(severity)}</td>"
            f"<td>{_html_text(component)}</td>"
            f"<td>{_html_text(clean_message)}</td>"
            f"<td>{_html_text(source, '-')}</td>"
            "</tr>"
        )

    disk_source = str(disk.get("source") or "")
    if disk_source:
        sources.append(disk_source)

    source_rows = _html_list(sorted(set(sources)), empty="No explicit sources found")
    finding_rows = _html_list(findings, empty="No notable findings recorded")

    issue_rows = "".join(
        "<tr>"
        f"<td>{int(issue.get('count', 0))}</td>"
        f"<td><code>{_html_text(issue.get('pattern', ''))}</code></td>"
        "</tr>"
        for issue in top_issues
    )
    issue_copy_text = "\n".join(
        f"({int(issue.get('count', 0))}) {issue.get('pattern', '')}" for issue in top_issues
    )

    disk_rows = "".join(
        "<tr>"
        f"<td>{_html_text(d.get('device', ''))}</td>"
        f"<td>{int(d.get('total_io_ops', 0)):,}</td>"
        f"<td>{int(d.get('reads_completed', 0)):,}</td>"
        f"<td>{int(d.get('writes_completed', 0)):,}</td>"
        f"<td>{int(d.get('time_spent_doing_io_ms', 0)):,}</td>"
        "</tr>"
        for d in disk.get("top_devices_by_io", [])
    )

    container_rows = "".join(
        "<tr>"
        f"<td>{_html_text(c.get('name', ''))}</td>"
        f"<td>{_html_text(c.get('cpu_percent', ''))}</td>"
        f"<td>{_html_text(c.get('mem_usage_limit', ''))}</td>"
        f"<td>{_html_text(c.get('mem_percent', ''))}</td>"
        "</tr>"
        for c in instances.get("top_containers_by_cpu", [])
    )

    interface_rows = "".join(
        "<tr>"
        f"<td>{_html_text(i.get('name', ''))}</td>"
        f"<td>{_html_text(i.get('state', ''))}</td>"
        f"<td>{_html_text(', '.join(i.get('ipv4', []) or ['none']))}</td>"
        "</tr>"
        for i in network.get("interfaces", [])[:40]
    )

    route_copy_text = "\n".join(str(route) for route in network.get("route_sample", []))
    related_file_rows = _html_list(payload.get("netbackup_related_files", [])[:250], empty="None")
    unhealthy_rows = _html_list(instances.get("unhealthy_or_stopped_containers", []), empty="None")
    down_interface_rows = _html_list(network.get("down_or_no_carrier_interfaces", []), empty="None")
    ip_rows = _html_list(report_card.get("ip_addresses", []), empty="No IPv4 addresses parsed")
    problem_rows = "".join(
        "<tr>"
        f"<td>{_severity_badge(str(problem.get('severity', 'info')))}</td>"
        f"<td>{_html_text(problem.get('label', ''))}</td>"
        f"<td>{int(problem.get('count', 0)):,}</td>"
        "<td><ul>"
        + "".join(
            f"<li><strong>{_html_text(sample.get('source', ''))}</strong>: {_html_text(sample.get('line', ''))}</li>"
            for sample in problem.get("samples", [])
        )
        + "</ul></td></tr>"
        for problem in typical_problems
    )
    version_table_rows = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('component', ''))}</td>"
        f"<td>{_html_text(row.get('device_name', ''))}</td>"
        f"<td>{_html_text(row.get('version', ''), '-')}</td>"
        f"<td>{_html_text(row.get('firmware', ''), '-')}</td>"
        f"<td>{_html_text(row.get('serial', ''), '-')}</td>"
        f"<td>{_html_text(row.get('source', ''), '-')}</td>"
        "</tr>"
        for row in version_rows
    )

    generated_at = _html_text(payload.get("analyzed_at_utc", ""))
    bundle_name = _html_text(bundle_meta.get("bundle_name", ""))
    appliance = _html_text(bundle_meta.get("appliance"))

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>NetBackup Flex Support Bundle Analysis</title>
    <style>
        :root {{
            --page: #edf1f5;
            --panel: #ffffff;
            --ink: #18212f;
            --muted: #5d6878;
            --line: #d8e0ea;
            --header: #12323a;
            --accent: #0f766e;
            --critical: #b42318;
            --warning: #b54708;
            --info: #175cd3;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: "Aptos", "Segoe UI", sans-serif;
            color: var(--ink);
            background:
                linear-gradient(135deg, rgba(15, 118, 110, 0.12), transparent 36%),
                linear-gradient(315deg, rgba(18, 50, 58, 0.10), transparent 34%),
                var(--page);
        }}
        .wrap {{ max-width: 1220px; margin: 0 auto; padding: 24px 16px 44px; }}
        header {{
            color: #fff;
            background: linear-gradient(135deg, var(--header), #0f766e);
            border-radius: 8px;
            padding: 22px 24px;
            box-shadow: 0 16px 32px rgba(18, 33, 47, 0.18);
        }}
        h1 {{ margin: 0 0 10px; font-size: 28px; font-weight: 700; }}
        .meta {{ display: flex; flex-wrap: wrap; gap: 10px 18px; margin: 0; color: rgba(255, 255, 255, 0.92); }}
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 16px 0; }}
        .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
        .metric strong {{ display: block; margin-top: 4px; font-size: 28px; line-height: 1; }}
        .label {{ color: var(--muted); font-size: 12px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }}
        details {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; margin: 12px 0; overflow: hidden; }}
        details[open] {{ box-shadow: 0 8px 20px rgba(18, 33, 47, 0.08); }}
        summary {{ cursor: pointer; padding: 14px 16px; font-size: 17px; font-weight: 700; background: #f8fafc; }}
        .section-body {{ padding: 14px 16px 18px; }}
        .two-col {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }}
        .panel {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fff; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 8px 9px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 13px; }}
        th {{ color: #344054; background: #eef3f8; font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }}
        tr:last-child td {{ border-bottom: 0; }}
        ul {{ margin: 8px 0; padding-left: 20px; }}
        code, textarea {{ font-family: "Cascadia Mono", Consolas, monospace; }}
        textarea {{ width: 100%; min-height: 130px; resize: vertical; border: 1px solid var(--line); border-radius: 8px; padding: 10px; color: var(--ink); }}
        button {{ border: 1px solid #0d9488; border-radius: 6px; padding: 7px 10px; color: #0f4f49; background: #ecfdf5; cursor: pointer; font-weight: 700; }}
        .copy-row {{ display: flex; justify-content: flex-end; margin: 8px 0; }}
        .badge {{ display: inline-block; min-width: 68px; border-radius: 999px; padding: 3px 9px; font-size: 12px; font-weight: 700; text-align: center; }}
        .badge.critical {{ color: var(--critical); background: #fef3f2; border: 1px solid #fecdca; }}
        .badge.warning {{ color: var(--warning); background: #fffaeb; border: 1px solid #fedf89; }}
        .badge.info {{ color: var(--info); background: #eff8ff; border: 1px solid #b2ddff; }}
        .critical-text {{ color: var(--critical); }}
        .warning-text {{ color: var(--warning); }}
        .info-text {{ color: var(--info); }}
        @media print {{
            body {{ background: #fff; }}
            .wrap {{ max-width: none; padding: 0; }}
            header, details {{ box-shadow: none; break-inside: avoid; }}
            details {{ border-color: #9aa4b2; }}
            details:not([open]) .section-body {{ display: block; }}
            summary {{ list-style: none; border-bottom: 1px solid #9aa4b2; }}
            summary::-webkit-details-marker {{ display: none; }}
            button, .copy-row {{ display: none; }}
            textarea {{ border: 0; min-height: auto; }}
        }}
    </style>
</head>
<body>
    <div class="wrap">
        <header>
            <h1>NetBackup Flex Support Bundle Analysis</h1>
            <p class="meta">
                <span><strong>Analyzed:</strong> {generated_at}</span>
                <span><strong>Bundle:</strong> {bundle_name}</span>
                <span><strong>Appliance:</strong> {appliance}</span>
                <span><strong>Obfuscated:</strong> {'enabled' if obfuscate else 'disabled'}</span>
            </p>
        </header>

        <section class="dashboard" aria-label="Summary dashboard">
            <div class="metric"><span class="label critical-text">Critical</span><strong>{critical_count}</strong></div>
            <div class="metric"><span class="label warning-text">Warning</span><strong>{warning_count}</strong></div>
            <div class="metric"><span class="label info-text">Info</span><strong>{info_count}</strong></div>
            <div class="metric"><span class="label">Error-like Lines</span><strong>{int(payload.get('error_lines_count', 0)):,}</strong></div>
            <div class="metric"><span class="label">Warning-like Lines</span><strong>{int(payload.get('warning_lines_count', 0)):,}</strong></div>
            <div class="metric"><span class="label">Files Scanned</span><strong>{int(payload.get('files_scanned', 0)):,}</strong></div>
        </section>

        <details open>
            <summary>Summary</summary>
            <div class="section-body two-col">
                <div class="panel">
                    <div class="label">Environment</div>
                    <p><strong>Hostname:</strong> {_html_text(payload.get('host_name'))}</p>
                    <p><strong>OS Release:</strong> {_html_text(payload.get('os_release'))}</p>
                    <p><strong>System Serial:</strong> {_html_text(payload.get('system_serial_number'))}</p>
                    <p><strong>Extracted Root:</strong> {_html_text(payload.get('extracted_root'))}</p>
                </div>
                <div class="panel">
                    <div class="label">Notable Findings</div>
                    <ul>{finding_rows}</ul>
                </div>
            </div>
        </details>

        <details open>
            <summary>Report Card</summary>
            <div class="section-body">
                <div class="two-col">
                    <div class="panel">
                        <div class="label">Device</div>
                        <p><strong>Name:</strong> {_html_text(report_card.get('device_name'))}</p>
                        <p><strong>Hostname:</strong> {_html_text(report_card.get('hostname'))}</p>
                    </div>
                    <div class="panel">
                        <div class="label">IPs Found</div>
                        <ul>{ip_rows}</ul>
                    </div>
                </div>
                <table>
                    <thead><tr><th>Component</th><th>Device Name</th><th>Version</th><th>Firmware / Build</th><th>Serial</th><th>Source</th></tr></thead>
                    <tbody>{version_table_rows or '<tr><td colspan="6">No software or firmware versions parsed</td></tr>'}</tbody>
                </table>
            </div>
        </details>

        <details open>
            <summary>Typical Hardware Datacollect Problems</summary>
            <div class="section-body">
                <table>
                    <thead><tr><th>Severity</th><th>Problem</th><th>Count</th><th>Samples</th></tr></thead>
                    <tbody>{problem_rows or '<tr><td colspan="4">No typical hardware datacollect problem patterns detected</td></tr>'}</tbody>
                </table>
            </div>
        </details>

        <details open>
            <summary>Hardware</summary>
            <div class="section-body">
                <div class="two-col">
                    <div class="panel">
                        <div class="label">Disk I/O</div>
                        <p><strong>Source:</strong> {_html_text(disk.get('source'), 'not found')}</p>
                        <p><strong>Device Count:</strong> {int(disk.get('device_count', 0))}</p>
                    </div>
                    <div class="panel">
                        <div class="label">Alert Sources</div>
                        <ul>{source_rows}</ul>
                    </div>
                </div>
                <table>
                    <thead><tr><th>Device</th><th>Total Ops</th><th>Reads</th><th>Writes</th><th>I/O ms</th></tr></thead>
                    <tbody>{disk_rows or '<tr><td colspan="5">No disk I/O entries parsed</td></tr>'}</tbody>
                </table>
            </div>
        </details>

        <details open>
            <summary>Failed Components And Alerts</summary>
            <div class="section-body">
                <table>
                    <thead><tr><th>Severity</th><th>Component</th><th>Message</th><th>Source</th></tr></thead>
                    <tbody>{''.join(alert_rows) or '<tr><td colspan="4">No component failure alerts detected</td></tr>'}</tbody>
                </table>
                <div class="copy-row"><button type="button" data-copy-target="alert-copy">Copy alerts</button></div>
                <textarea id="alert-copy" readonly>{html.escape(chr(10).join(alert_copy_lines) or 'No component failure alerts detected')}</textarea>
            </div>
        </details>

        <details>
            <summary>Time Sync And Scan Window</summary>
            <div class="section-body two-col">
                <div class="panel"><div class="label">First Timestamp Seen</div><p>{_html_text(payload.get('first_timestamp_seen'), 'not found')}</p></div>
                <div class="panel"><div class="label">Last Timestamp Seen</div><p>{_html_text(payload.get('last_timestamp_seen'), 'not found')}</p></div>
                <div class="panel"><div class="label">Bundle Timestamp</div><p>{_html_text(bundle_meta.get('timestamp'))}</p></div>
                <div class="panel"><div class="label">Trigger</div><p>{_html_text(bundle_meta.get('trigger'))}</p></div>
            </div>
        </details>

        <details>
            <summary>Logs</summary>
            <div class="section-body">
                <table>
                    <thead><tr><th>Count</th><th>Recurring Pattern</th></tr></thead>
                    <tbody>{issue_rows or '<tr><td colspan="2">None</td></tr>'}</tbody>
                </table>
                <div class="copy-row"><button type="button" data-copy-target="issue-copy">Copy log patterns</button></div>
                <textarea id="issue-copy" readonly>{html.escape(issue_copy_text or 'No recurring issue patterns detected')}</textarea>
            </div>
        </details>

        <details>
            <summary>Containers</summary>
            <div class="section-body">
                <div class="two-col">
                    <div class="panel"><div class="label">Container Count</div><p>{int(instances.get('container_count', 0))}</p></div>
                    <div class="panel"><div class="label">Pod Count</div><p>{int(instances.get('pod_count', 0))}</p></div>
                    <div class="panel"><div class="label">Unhealthy Or Stopped</div><ul>{unhealthy_rows}</ul></div>
                </div>
                <table>
                    <thead><tr><th>Name</th><th>CPU</th><th>Memory</th><th>Mem %</th></tr></thead>
                    <tbody>{container_rows or '<tr><td colspan="4">No container stats found</td></tr>'}</tbody>
                </table>
            </div>
        </details>

        <details>
            <summary>Network</summary>
            <div class="section-body">
                <div class="two-col">
                    <div class="panel"><div class="label">Default Route</div><p>{_html_text(network.get('default_route'), 'not found')}</p></div>
                    <div class="panel"><div class="label">mgmt0 Link</div><p>{_html_text(network.get('mgmt0_link_speed'))}, detected={_html_text(network.get('mgmt0_link_detected'))}</p></div>
                    <div class="panel"><div class="label">Down Or No-Carrier Interfaces</div><ul>{down_interface_rows}</ul></div>
                </div>
                <table>
                    <thead><tr><th>Interface</th><th>State</th><th>IPv4</th></tr></thead>
                    <tbody>{interface_rows or '<tr><td colspan="3">No interface details parsed</td></tr>'}</tbody>
                </table>
                <div class="copy-row"><button type="button" data-copy-target="route-copy">Copy routes</button></div>
                <textarea id="route-copy" readonly>{html.escape(route_copy_text or 'No route sample found')}</textarea>
            </div>
        </details>

        <details>
            <summary>NetBackup And Flex File Index</summary>
            <div class="section-body">
                <p><strong>Total keyword matches retained:</strong> {len(payload.get('netbackup_related_files', [])):,}</p>
                <ul>{related_file_rows}</ul>
            </div>
        </details>
    </div>
    <script>
        document.querySelectorAll('button[data-copy-target]').forEach((button) => {{
            button.addEventListener('click', async () => {{
                const target = document.getElementById(button.dataset.copyTarget);
                if (!target) return;
                await navigator.clipboard.writeText(target.value);
                const original = button.textContent;
                button.textContent = 'Copied';
                setTimeout(() => {{ button.textContent = original; }}, 1200);
            }});
        }});
    </script>
</body>
</html>
"""


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

    report_card = payload.get("report_card", {})
    report_lines.append("## Report Card")
    report_lines.append(f"- Device Name: {report_card.get('device_name') or 'unknown'}")
    report_lines.append(f"- Hostname: {report_card.get('hostname') or 'unknown'}")
    ips = report_card.get("ip_addresses", [])
    report_lines.append(f"- IPs Found: {', '.join(ips) if ips else 'none'}")
    report_lines.append("- Software/Firmware Versions:")
    version_rows = report_card.get("software_firmware_versions", [])
    if version_rows:
        for row in version_rows:
            report_lines.append(
                "  - "
                f"{row.get('component', 'unknown')}: {row.get('device_name', 'unknown')}; "
                f"version={row.get('version') or 'unknown'}; "
                f"firmware/build={row.get('firmware') or 'unknown'}; "
                f"serial={row.get('serial') or 'unknown'}; "
                f"source={row.get('source') or 'unknown'}"
            )
    else:
        report_lines.append("  - none")
    report_lines.append("")

    report_lines.append("## Typical Hardware Datacollect Problems")
    typical_problems = payload.get("typical_problem_findings", [])
    if typical_problems:
        for problem in typical_problems:
            report_lines.append(
                f"- [{str(problem.get('severity', 'info')).upper()}] "
                f"{problem.get('label', 'unknown')}: count={problem.get('count', 0)}"
            )
            for sample in problem.get("samples", []):
                report_lines.append(f"  - {sample.get('source', 'unknown')}: {sample.get('line', '')}")
    else:
        report_lines.append("- No typical hardware datacollect problem patterns detected")
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

    html_path = output_dir / "report.html"
    html_path.write_text(render_html_report(payload, obfuscate=obfuscate), encoding="utf-8")


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
    print(f"HTML report: {output_dir / 'report.html'}")
    print(f"Summary: {output_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

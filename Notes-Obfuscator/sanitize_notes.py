#!/usr/bin/env python3
"""
sanitize_notes.py -- Discover, replace, and validate sensitive entities in
exported HTML notes before public knowledge-base publication.

Requires:  pip install beautifulsoup4

Workflow:
  1. python sanitize_notes.py discover --root ./Bennett-Notes --map mapping.json
  2. Review / edit mapping.json -- adjust tokens, add credentials from flagged lines.
  3. python sanitize_notes.py apply    --root ./Bennett-Notes \
                                       --map mapping.json \
                                       --output ./Sanitized-Notes [--copy-assets]
  4. python sanitize_notes.py validate --root ./Sanitized-Notes --map mapping.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    from bs4 import BeautifulSoup, Comment
except ImportError:
    sys.exit("beautifulsoup4 is required.  Run:  pip install beautifulsoup4")

# -- Defaults ------------------------------------------------------------------
DEFAULT_ROOT   = Path(r"E:\VSCode-Root\onenote\Bennett-Notes")
DEFAULT_MAP    = Path(r"E:\VSCode-Root\onenote\Notes-Obfuscator\mapping.json")
DEFAULT_OUTPUT = Path(r"E:\VSCode-Root\onenote\Sanitized-Notes")

# -- Safelist ------------------------------------------------------------------
SAFELIST_DOMAINS: Set[str] = {
    "dell.com", "emc.com", "dellemc.com",
    "veritas.com",
    "veeam.com",
    "cohesity.com",
    "rubrik.com",
    "commvault.com",
    "netapp.com",
    "quantum.com",
    "spectralogic.com",
    "bravais.com",
    "learnondemand.net",
    "logicaloperations.learnondemand.net",
    "microsoft.com", "microsoftonline.com", "azure.com",
    "graph.microsoft.com",
    "google.com", "googleapis.com", "googlecloud.com",
    "amazon.com", "amazonaws.com", "aws.amazon.com",
    # Safe output-token domains -- never flag as sensitive
    "example.com", "example.net", "example.org", "example.test",
    "corp.local",
}

# RFC 5737 / RFC 3849 documentation ranges used as output tokens
_SAFE_IPV4_PREFIXES: Tuple[str, ...] = (
    "192.0.2.", "198.51.100.", "203.0.113.", "10.10.",
)
_SAFE_IPV6_PREFIX = "2001:db8"

# -- Regex catalog -------------------------------------------------------------
_EMAIL_RE = re.compile(
    r"\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b"
)
# Credential immediately after email:  email@domain - Password123!
_POST_EMAIL_CRED_RE = re.compile(
    r"@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\s+[\-\u2013\u2014:=]\s+(\S{6,})"
)
# Keyword-prefixed credentials
_KW_CRED_RE = re.compile(
    r"(?:password|passwd|pwd|pass|secret|api[_\-]?key|token|cred)s?\s*[:\-=]\s*(\S+)",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"\b(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.])\d{3}[\s\-.]\d{4}"
    r"(?:\s*(?:ext\.?|x)\s*\d{1,6})?\b",
    re.IGNORECASE,
)
_IPV4_RE = re.compile(
    r"\b((?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?))\b"
)
_IPV6_RE = re.compile(
    r"\b((?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4})\b"
)
_FQDN_RE = re.compile(
    r"\b((?:[a-zA-Z0-9\-]+\.){2,}[a-zA-Z]{2,})\b"
)
# [msdp-16.0.1] hostname > command
_SHELL_BRACKET_HOST_RE = re.compile(
    r"\[[^\]]{1,40}\]\s+([a-zA-Z0-9][a-zA-Z0-9\-]{4,})\s+[>#$]"
)
# [user@hostname dir]# or $
_SHELL_AT_HOST_RE = re.compile(
    r"\[(?:[a-zA-Z0-9_\-]+@)([a-zA-Z0-9][a-zA-Z0-9\-]{3,})\s"
)
_UNC_RE = re.compile(
    r"(\\\\[a-zA-Z0-9\-]+(?:\\[^\s<>\"]+)+)"
)
_WIN_PATH_RE = re.compile(
    r"([A-Za-z]:\\(?:[^\\\s<>\"]+\\)*[^\\\s<>\"]+)"
)
_TICKET_RE = re.compile(
    r"\b((?:INC|CHG|REQ|SR|RITM|PRB|TASK)\d{5,10})\b"
)
_AUTH_TOKEN_URL_RE = re.compile(
    r"[?&]((?:token|key|sig|auth|secret|session|api[_\-]?key|"
    r"password|passwd|pwd)=[^\s&\"'<>]+)",
    re.IGNORECASE,
)
_DOMUSER_RE = re.compile(
    r"\b([A-Z][A-Z0-9]{1,14}\\[a-zA-Z0-9_\-]+)\b"
)
_HEADER_NAME_RE = re.compile(
    r"(?:^|\b)(?:From|To|Cc|reply from)\s*:\s*([^\[<\n\r]+)",
    re.IGNORECASE,
)
_STANDALONE_NAME_RE = re.compile(
    r"^\s*([A-Z][a-z]+(?:,\s*[A-Z][a-z]+|(?:\s+[A-Z][a-z]+){1,2}))\s*$"
)
# Training URL with user-ID path segment
_TRAINING_URL_RE = re.compile(
    r"(https?://[^\s\"'<>]+/(?:User|user)/[^\s/\"'<>]+/\d{4,}[^\s\"'<>]*)"
)

_NAME_STOPWORDS = {
    "case", "comments", "data", "engineer", "external", "hello", "insight",
    "message", "operations", "original", "protection", "regards", "reply",
    "senior", "support", "team", "thanks", "veeam", "veritas",
}

# HTML attributes to scan as plain text
_TEXT_ATTRS = {"alt", "title"}
# HTML attributes to scan only when value is an absolute URL
_URL_ATTRS = {"href", "src", "data-fullres-src"}

# Windows / Unix system paths that are not sensitive
_SAFE_WIN_PREFIXES = (
    "c:\\windows", "c:\\program files", "c:\\program files (x86)",
    "/usr/", "/etc/", "/var/", "/opt/", "/tmp/",
)


# -- Mapping I/O ---------------------------------------------------------------

def _empty_mapping() -> Dict:
    return {
        "_metadata": {"version": 1, "counters": {}},
        "emails":       {},
        "names":        {},
        "phone_numbers": {},
        "credentials":  {},
        "ips":          {},
        "hostnames":    {},
        "tickets":      {},
        "domain_users": {},
        "unc_paths":    {},
        "win_paths":    {},
        "auth_tokens":  {},
    }


def load_mapping(path: Path) -> Dict:
    mapping = _empty_mapping()
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            loaded = json.load(fh)

        metadata = loaded.get("_metadata", {})
        mapping["_metadata"].update(metadata)
        mapping["_metadata"]["counters"] = metadata.get("counters", {})

        for key, value in loaded.items():
            if key == "_metadata":
                continue
            if isinstance(value, dict):
                mapping[key] = value

    return mapping


def save_mapping(mapping: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, indent=2, ensure_ascii=False)


def _next_counter(mapping: Dict, key: str) -> int:
    counters = mapping["_metadata"].setdefault("counters", {})
    val = counters.get(key, 0) + 1
    counters[key] = val
    return val


def flat_replacements(mapping: Dict) -> Dict[str, str]:
    """Single {original: token} dict from all categories, for apply phase."""
    result: Dict[str, str] = {}
    for section in (
        "emails", "names", "phone_numbers", "credentials", "ips", "hostnames", "tickets",
        "domain_users", "unc_paths", "win_paths", "auth_tokens",
    ):
        for k, v in mapping.get(section, {}).items():
            if k and v:
                result[k] = v
    return result


# -- Safelist helpers ----------------------------------------------------------

def _domain_of(value: str) -> str:
    parts = value.lower().rstrip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else value.lower()


def is_safelisted(value: str, extra: Set[str]) -> bool:
    low = value.lower()
    all_safe = SAFELIST_DOMAINS | extra
    if low in all_safe:
        return True
    if _domain_of(value) in all_safe:
        return True
    if any(low.startswith(p) for p in _SAFE_IPV4_PREFIXES):
        return True
    if low.startswith(_SAFE_IPV6_PREFIX):
        return True
    return False


def load_extra_safelist(path: Optional[Path]) -> Set[str]:
    if path and path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        return {ln.strip().lower() for ln in lines if ln.strip() and not ln.startswith("#")}
    return set()


def _is_probable_name(value: str) -> bool:
    candidate = value.strip(" <>[]()\"")
    if not candidate or any(ch.isdigit() for ch in candidate):
        return False
    if any(ch in candidate for ch in ("@", "\\", ":", "/")):
        return False

    normalized = candidate.replace(",", " ")
    words = [word.strip(".") for word in normalized.split() if word]
    if len(words) < 2 or len(words) > 3:
        return False

    for word in words:
        if word.lower() in _NAME_STOPWORDS:
            return False
        if not re.fullmatch(r"[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?", word):
            return False

    return True


# -- Entity extraction ---------------------------------------------------------

def extract_entities(text: str, extra_safe: Set[str]) -> Dict[str, Set[str]]:
    """Return {category: set_of_candidate_values} found in text."""
    found: Dict[str, Set[str]] = defaultdict(set)

    # Emails first -- extract their domains so FQDN pass can skip them
    email_domains: Set[str] = set()
    for m in _EMAIL_RE.finditer(text):
        val = m.group(1)
        if not is_safelisted(val, extra_safe):
            found["emails"].add(val)
            email_domains.add(val.split("@", 1)[1].lower())

    # Post-email credential pattern
    for m in _POST_EMAIL_CRED_RE.finditer(text):
        found["credentials"].add(m.group(1))

    # Keyword credential pattern
    for m in _KW_CRED_RE.finditer(text):
        found["credentials"].add(m.group(1))

    # Phone numbers
    for m in _PHONE_RE.finditer(text):
        found["phone_numbers"].add(m.group(0))

    # IPv4
    for m in _IPV4_RE.finditer(text):
        val = m.group(1)
        if not is_safelisted(val, extra_safe):
            found["ips"].add(val)

    # IPv6
    for m in _IPV6_RE.finditer(text):
        val = m.group(1)
        if not is_safelisted(val, extra_safe):
            found["ips"].add(val)

    # FQDNs -- skip if already captured as email domain or safelisted
    for m in _FQDN_RE.finditer(text):
        val = m.group(1)
        if val.lower() in email_domains:
            continue
        if not is_safelisted(val, extra_safe):
            found["hostnames"].add(val)

    # Shell-prompt short hostnames
    for pattern in (_SHELL_BRACKET_HOST_RE, _SHELL_AT_HOST_RE):
        for m in pattern.finditer(text):
            val = m.group(1)
            if not is_safelisted(val, extra_safe):
                found["hostnames"].add(val)

    # Ticket numbers
    for m in _TICKET_RE.finditer(text):
        found["tickets"].add(m.group(1))

    # Domain\user
    for m in _DOMUSER_RE.finditer(text):
        found["domain_users"].add(m.group(1))

    # Person names in email headers and simple signature lines
    for m in _HEADER_NAME_RE.finditer(text):
        value = m.group(1).strip()
        if _is_probable_name(value):
            found["names"].add(value)

    standalone = text.strip()
    if _is_probable_name(standalone):
        found["names"].add(standalone)

    # UNC paths
    for m in _UNC_RE.finditer(text):
        found["unc_paths"].add(m.group(1))

    # Windows absolute paths -- skip common system paths
    for m in _WIN_PATH_RE.finditer(text):
        val = m.group(1)
        if not any(val.lower().startswith(p) for p in _SAFE_WIN_PREFIXES):
            found["win_paths"].add(val)

    # Auth tokens in URLs
    for m in _AUTH_TOKEN_URL_RE.finditer(text):
        found["auth_tokens"].add(m.group(1))

    return dict(found)


def extract_from_html(path: Path, extra_safe: Set[str]) -> Dict[str, Set[str]]:
    """Parse an HTML file; extract entities from text nodes and key attributes."""
    try:
        html = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"  [SKIP] Cannot read {path}: {exc}")
        return {"_read_error": {str(path)}}
    soup = BeautifulSoup(html, "html.parser")
    combined: Dict[str, Set[str]] = defaultdict(set)

    def _merge(new: Dict[str, Set[str]]) -> None:
        for k, v in new.items():
            combined[k].update(v)

    for string in soup.find_all(string=True):
        if string.parent.name in ("script", "style"):
            continue
        _merge(extract_entities(str(string), extra_safe))

    for tag in soup.find_all(True):
        for attr in _TEXT_ATTRS:
            val = tag.get(attr, "")
            if val:
                _merge(extract_entities(val, extra_safe))
        for attr in _URL_ATTRS:
            val = tag.get(attr, "")
            if val and (val.startswith("http://") or val.startswith("https://")):
                _merge(extract_entities(val, extra_safe))

    return dict(combined)


# -- Token generators ----------------------------------------------------------

def _token_email(addr: str, mapping: Dict) -> str:
    n = _next_counter(mapping, "email")
    local = addr.split("@")[0]
    if "-" in local or "_" in local:
        hint = re.sub(r"[^a-z]", "", local.split("-")[0].split("_")[0].lower())[:6]
        return f"{hint or 'team'}{n:03d}@example.com"
    return f"user{n:03d}@example.com"


def _token_name(mapping: Dict) -> str:
    n = _next_counter(mapping, "name")
    return f"Person {n:03d}"


def _token_phone(phone: str, mapping: Dict) -> str:
    n = _next_counter(mapping, "phone")
    token = f"555-01{n:02d}"
    ext_match = re.search(r"(?i)\b(?:ext\.?|x)\s*(\d{1,6})\b", phone)
    if ext_match:
        return f"{token} ext. {100 + n}"
    return token


def _token_ip(addr: str, mapping: Dict) -> str:
    parts = addr.split(".")
    if len(parts) == 4:
        try:
            last = int(parts[3])
            candidate = f"10.10.1.{last}"
            if candidate not in mapping["ips"].values():
                return candidate
        except ValueError:
            pass
    n = _next_counter(mapping, "ip")
    return f"10.10.1.{n}"


def _token_hostname(host: str, mapping: Dict) -> str:
    n = _next_counter(mapping, "host")
    low = host.lower()
    for prefix in ("db", "app", "web", "media", "backup", "proxy",
                   "dc", "ad", "mail", "smtp", "ftp", "nfs"):
        if low.startswith(prefix):
            return f"{prefix}{n:03d}.corp.local"
    return f"host{n:03d}.corp.local"


def _token_ticket(ticket: str, mapping: Dict) -> str:
    prefix = re.match(r"^([A-Z]+)", ticket).group(1)
    n = _next_counter(mapping, f"ticket_{prefix}")
    return f"{prefix}{n:06d}"


def _token_domuser(mapping: Dict) -> str:
    n = _next_counter(mapping, "domuser")
    return f"CORP\\user{n:03d}"


def _token_unc(mapping: Dict) -> str:
    n = _next_counter(mapping, "unc")
    return f"\\\\fileserver{n:03d}\\share{n:03d}"


def _token_win_path(path: str, mapping: Dict) -> str:
    n = _next_counter(mapping, "win_path")
    parts = path.split("\\")

    if len(parts) >= 4 and parts[1].lower() == "users":
        return "\\".join([parts[0], "Users", f"user{n:03d}", *parts[3:]])

    if len(parts) >= 3:
        return "\\".join([parts[0], parts[1], f"path{n:03d}", *parts[3:]])

    return f"C:\\path{n:03d}"


# -- Subcommand: discover ------------------------------------------------------

def cmd_discover(args: argparse.Namespace) -> None:
    extra_safe = load_extra_safelist(args.safelist)
    mapping = load_mapping(args.map)

    html_files = sorted(args.root.rglob("*.html"))
    if not html_files:
        print(f"No .html files found under {args.root}")
        return

    new_counts: Dict[str, int] = defaultdict(int)
    flagged_lines: List[str] = []
    skipped: List[str] = []

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        entities = extract_from_html(html_path, extra_safe)
        if "_read_error" in entities:
            skipped.append(str(rel))
            continue
        try:
            raw = html_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"  [SKIP] Cannot read {html_path}: {exc}")
            skipped.append(str(rel))
            continue

        for email in entities.get("emails", set()):
            if email not in mapping["emails"]:
                mapping["emails"][email] = _token_email(email, mapping)
                new_counts["emails"] += 1
            for line in raw.splitlines():
                if email in line and len(line.strip()) > len(email) + 4:
                    flagged_lines.append(f"  [{rel}]  {line.strip()[:140]}")

        for name in entities.get("names", set()):
            if name not in mapping["names"]:
                mapping["names"][name] = _token_name(mapping)
                new_counts["names"] += 1

        for phone in entities.get("phone_numbers", set()):
            if phone not in mapping["phone_numbers"]:
                mapping["phone_numbers"][phone] = _token_phone(phone, mapping)
                new_counts["phone_numbers"] += 1

        for cred in entities.get("credentials", set()):
            if cred not in mapping["credentials"]:
                mapping["credentials"][cred] = "[REDACTED]"
                new_counts["credentials"] += 1

        for ip in entities.get("ips", set()):
            if ip not in mapping["ips"]:
                mapping["ips"][ip] = _token_ip(ip, mapping)
                new_counts["ips"] += 1

        for host in entities.get("hostnames", set()):
            if host not in mapping["hostnames"]:
                mapping["hostnames"][host] = _token_hostname(host, mapping)
                new_counts["hostnames"] += 1

        for ticket in entities.get("tickets", set()):
            if ticket not in mapping["tickets"]:
                mapping["tickets"][ticket] = _token_ticket(ticket, mapping)
                new_counts["tickets"] += 1

        for du in entities.get("domain_users", set()):
            if du not in mapping["domain_users"]:
                mapping["domain_users"][du] = _token_domuser(mapping)
                new_counts["domain_users"] += 1

        for unc in entities.get("unc_paths", set()):
            if unc not in mapping["unc_paths"]:
                mapping["unc_paths"][unc] = _token_unc(mapping)
                new_counts["unc_paths"] += 1

        for win_path in entities.get("win_paths", set()):
            if win_path not in mapping["win_paths"]:
                mapping["win_paths"][win_path] = _token_win_path(win_path, mapping)
                new_counts["win_paths"] += 1

        for tok in entities.get("auth_tokens", set()):
            if tok not in mapping["auth_tokens"]:
                mapping["auth_tokens"][tok] = "[REDACTED]"
                new_counts["auth_tokens"] += 1

    mapping["_metadata"]["last_discover"] = datetime.now(timezone.utc).isoformat()

    if not args.dry_run:
        save_mapping(mapping, args.map)
        print(f"Mapping written to: {args.map}")
    else:
        print("[dry-run] mapping.json not written")

    print(f"\nScanned {len(html_files)} HTML file(s) ({len(skipped)} skipped)")
    if skipped:
        print("Skipped (unreadable):")
        for s in skipped:
            print(f"  {s}")
    print("New candidates added:")
    for k in ("emails", "names", "phone_numbers", "credentials", "ips", "hostnames", "tickets",
               "win_paths",
               "domain_users", "unc_paths", "auth_tokens"):
        if new_counts.get(k):
            print(f"  {k:<18} {new_counts[k]}")

    if flagged_lines:
        shown = flagged_lines[:40]
        print(f"\nLines for credential review ({len(flagged_lines)} found):")
        for line in shown:
            print(line)
        if len(flagged_lines) > 40:
            print(f"  ... and {len(flagged_lines) - 40} more")
        print(
            "\n  ACTION: review the above lines, then manually add any passwords\n"
            "          found to the 'credentials' section of mapping.json."
        )


# -- Subcommand: apply ---------------------------------------------------------

def _apply_text(text: str, replacements: Dict[str, str]) -> Tuple[str, int]:
    """Replace all mapping keys (longest first) in text. Returns (result, count)."""
    count = 0
    for original in sorted(replacements, key=len, reverse=True):
        if original in text:
            text = text.replace(original, replacements[original])
            count += 1
    return text, count


def _sanitize_html(path: Path, replacements: Dict[str, str]) -> Tuple[str, int]:
    try:
        html = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"  [SKIP] Cannot read {path}: {exc}")
        return "", -1
    soup = BeautifulSoup(html, "html.parser")
    total = 0

    # Text nodes
    for string in soup.find_all(string=True):
        if string.parent.name in ("script", "style"):
            continue
        new, n = _apply_text(str(string), replacements)
        if n:
            string.replace_with(new)
            total += n

    # HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        new, n = _apply_text(str(comment), replacements)
        if n:
            comment.replace_with(Comment(new))
            total += n

    # Attributes
    for tag in soup.find_all(True):
        for attr in _TEXT_ATTRS:
            val = tag.get(attr)
            if val:
                new, n = _apply_text(val, replacements)
                if n:
                    tag[attr] = new
                    total += n
        for attr in _URL_ATTRS:
            val = tag.get(attr)
            if val and (val.startswith("http://") or val.startswith("https://")):
                new, n = _apply_text(val, replacements)
                if n:
                    tag[attr] = new
                    total += n

    return str(soup), total


def cmd_apply(args: argparse.Namespace) -> None:
    if not args.map.exists():
        sys.exit(f"Mapping file not found: {args.map}  (run 'discover' first)")

    mapping = load_mapping(args.map)
    replacements = flat_replacements(mapping)
    html_files = sorted(args.root.rglob("*.html"))

    if not html_files:
        print(f"No .html files found under {args.root}")
        return

    log_lines: List[str] = []
    total_subs = 0
    skipped: List[str] = []

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        out_path = args.output / rel
        sanitized, count = _sanitize_html(html_path, replacements)
        if count == -1:
            skipped.append(str(rel))
            continue
        total_subs += count
        log_lines.append(f"{count:5d}  {rel}")
        if not args.dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(sanitized, encoding="utf-8")

    if args.copy_assets and not args.dry_run:
        for asset in args.root.rglob("*"):
            if asset.is_file() and asset.suffix.lower() != ".html":
                rel = asset.relative_to(args.root)
                dest = args.output / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset, dest)

    log_content = (
        f"sanitize_notes.py -- apply log\n"
        f"Run:    {datetime.now().isoformat()}\n"
        f"Source: {args.root}\n"
        f"Output: {args.output}\n"
        f"Total substitutions: {total_subs}\n\n"
        f"{'Subs':>5}  File\n"
        f"{'─' * 5}  {'─' * 70}\n"
    ) + "\n".join(log_lines)

    if not args.dry_run:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "substitution_log.txt").write_text(log_content, encoding="utf-8")
        print(f"Sanitized {len(html_files) - len(skipped)} file(s) -> {args.output}")
        if skipped:
            print(f"Skipped {len(skipped)} unreadable file(s):")
            for s in skipped:
                print(f"  {s}")
        print(f"Total substitutions: {total_subs}")
    else:
        print(f"[dry-run] {len(html_files) - len(skipped)} file(s), {total_subs} substitution(s)")
        if skipped:
            print(f"Skipped {len(skipped)} unreadable file(s)")
        for line in log_lines[:25]:
            print(f"  {line}")


# -- Subcommand: validate ------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> None:
    extra_safe = load_extra_safelist(args.safelist)

    # Collect already-safe replacement tokens so we don't flag our own output
    known_safe_tokens: Set[str] = set()
    if args.map and args.map.exists():
        for token in flat_replacements(load_mapping(args.map)).values():
            if token:
                known_safe_tokens.add(token)

    html_files = sorted(args.root.rglob("*.html"))
    issues: List[str] = []

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        entities = extract_from_html(html_path, extra_safe)
        if "_read_error" in entities:
            continue
        for category, values in entities.items():
            for val in values:
                if val not in known_safe_tokens:
                    issues.append(f"  [{category:<14}] {val!r:<50}  {rel}")

    if issues:
        print(f"VALIDATE FAILED -- {len(issues)} residual sensitive match(es):\n")
        for issue in sorted(issues)[:100]:
            print(issue)
        if len(issues) > 100:
            print(f"\n  ... and {len(issues) - 100} more")
        sys.exit(1)
    else:
        print(f"VALIDATE PASSED -- {len(html_files)} file(s) clean")


# -- CLI -----------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sanitize sensitive identifiers in exported HTML notes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python sanitize_notes.py discover --root ./Bennett-Notes --map mapping.json\n"
            "  python sanitize_notes.py apply    --root ./Bennett-Notes "
            "--map mapping.json --output ./Sanitized-Notes\n"
            "  python sanitize_notes.py validate --root ./Sanitized-Notes "
            "--map mapping.json\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # discover
    disc = sub.add_parser("discover", help="Scan HTML files and populate mapping.json")
    disc.add_argument("--root",     type=Path, default=DEFAULT_ROOT)
    disc.add_argument("--map",      type=Path, default=DEFAULT_MAP)
    disc.add_argument("--safelist", type=Path, default=None,
                      help="File of extra safe domains/terms, one per line")
    disc.add_argument("--dry-run",  action="store_true")

    # apply
    appl = sub.add_parser("apply", help="Apply mapping.json to HTML files")
    appl.add_argument("--root",        type=Path, default=DEFAULT_ROOT)
    appl.add_argument("--map",         type=Path, default=DEFAULT_MAP)
    appl.add_argument("--output",      type=Path, default=DEFAULT_OUTPUT)
    appl.add_argument("--safelist",    type=Path, default=None)
    appl.add_argument("--copy-assets", action="store_true",
                      help="Copy non-.html files (images, .bin) to output dir")
    appl.add_argument("--dry-run",     action="store_true")

    # validate
    val = sub.add_parser("validate", help="Re-scan output files for residual matches")
    val.add_argument("--root",     type=Path, default=DEFAULT_OUTPUT)
    val.add_argument("--map",      type=Path, default=DEFAULT_MAP)
    val.add_argument("--safelist", type=Path, default=None)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "discover":
        cmd_discover(args)
    elif args.command == "apply":
        cmd_apply(args)
    elif args.command == "validate":
        cmd_validate(args)


if __name__ == "__main__":
    main()

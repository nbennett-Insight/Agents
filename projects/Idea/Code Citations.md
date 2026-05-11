# Code Citations

## License: unknown
https://github.com/tinabuzanis/machine-translation/blob/347a1eec9dab94f6817df89a387f50901d14bcd5/trim_models_and_tok.py

```
Good — confirmed key patterns: `nick.bennett@insight.com - Solana001!!!` (email+credential), `[msdp-16.0.1] jd1ltlanbufwm01 >` (shell prompt hostname), and training URLs with embedded user IDs. Both files are designed around these.

---

## File 1: `sanitize-framework.txt` (full rewrite)

```
==============================================================================
  NOTES SANITIZATION FRAMEWORK  v1.1
  Purpose : Obfuscate sensitive identifiers in exported HTML notes prior to
            publication in a public or broadly-shared knowledge base.
  Updated : 2026-04-24
==============================================================================

  CONTENTS
  ────────
  Section 1  Scope and Exclusions
  Section 2  Sanitization Rules
    2.1  Entity rules and replacement tokens
    2.2  Regex pattern catalog
    2.3  Canonical mapping strategy
  Section 3  Local Script Reference  (sanitize_notes.py)
  Section 4  Image and Alt-Text Handling
  Section 5  HTML Attribute Decision Table
  Section 6  Validation Checklist
  Section 7  Agent Instructions  (Copilot Studio / LLM system prompt)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1  SCOPE AND EXCLUSIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1.1  Purpose
  These notes cover enterprise backup/recovery products (Avamar, Veeam,
  NetBackup, Cohesity, Rubrik, CommVault, NetApp, Quantum, Spectra Logic)
  and cloud platforms (AWS, Azure, GCP).  Most notes are training, lab, and
  field-support references.  Sanitization removes personal and customer
  identifiers while keeping all technical detail intact.

1.2  What MUST be obfuscated
  - Real names of employees, customers, or contacts
  - Internal or customer email addresses  (including work addresses such as
    name@insight.com)
  - Credentials — passwords, API keys, tokens, secrets — appearing anywhere
    in text, including "email - password" patterns from lab notes
  - Internal hostnames and FQDNs (customer/org-specific)
  - Short hostnames appearing in shell prompts  (e.g., [version] hostname >)
  - Real IP addresses (internal and public)
  - Internal ticket, case, or change record numbers  (INC, CHG, REQ, SR …)
  - Internal UNC paths and Windows absolute paths that expose org structure
  - Company and organisation names (customers, employers)
  - Specific office or city names tied to internal infrastructure
  - Training or lab portal URLs that contain a user-specific ID in the path
    (e.g., /User/CurrentTraining/2517591)

1.3  What MUST be preserved  (safelist)
  Vendor product names and their official domains:
    dell.com  emc.com  dellemc.com
    veritas.com
    veeam.com
    cohesity.com
    rubrik.com
    commvault.com
    netapp.com
    quantum.com
    spectralogic.com
    bravais.com                       (Dell training platform)
    learnondemand.net                 (Veeam/LogicalOps training — base domain
                                       is safe; only the user-ID path segment
                                       needs removal)
    microsoft.com  microsoftonline.com  azure.com  graph.microsoft.com
    google.com  googleapis.com
    amazon.com  amazonaws.com

  Technical content that must not be altered:
    - Protocol names  (HTTP, HTTPS, RDP, NFS, SMB, iSCSI …)
    - Port numbers
    - CLI commands and their flags / options
    - Error codes and log severity levels
    - RFC-standard IP ranges already used as output tokens:
        192.0.2.0/24,  198.51.100.0/24,  203.0.113.0/24,  2001:db8::/32
    - Product version strings
    - Configuration key names  (but NOT their values when those values
      contain PII or credentials)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2  SANITIZATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2.1  Entity Rules and Replacement Tokens

  ENTITY TYPE              TOKEN FORMAT              NOTES
  ─────────────────────── ─────────────────────── ─────────────────────────
  Email (personal)         user001@example.com     increment per unique addr
  Email (role/team)        netops@example.com      preserve functional hint
  Credential / password    [REDACTED]              always full replacement;
                                                   never preserve any part
  IPv4 private             10.10.1.N               N = last octet of original
  IPv4 public              198.51.100.N            RFC 5737 range
  IPv6                     2001:db8::N             RFC 3849 range
  FQDN (with dots)         host001.corp.local      preserve role prefix if
                                                   clear (db, app, web …)
  Short hostname           host001                 hostnames without a domain
  Shell-prompt hostname    host001                 from [ver] hostname > or
                                                   [user@hostname dir]#
  Domain\user              CORP\user001            keep CORP\ prefix
  Service account          svc001                  keep svc_ prefix style
  Person name (standalone) PERSON_001
  Ticket INC               INC000001               zero-padded 6 digits
  Ticket CHG               CHG000001
  Ticket REQ/SR/RITM       REQ000001  etc.
  UNC path                 \\fileserver001\share001 replace server + share
  Windows absolute path    C:\data\project001\...  replace non-system folders
  API token in URL query   [REDACTED]              strip entire key=value pair
  Training URL with user   strip the user-ID path  keep base domain + course
  Customer / org name      CustomerA, CustomerB    sequential labels
  City / office            Region-Office-01        e.g., Midwest-Office-01

2.2  Regex Pattern Catalog

  Apply safelist exclusion BEFORE flagging any FQDN or IP match.
  Run email pattern BEFORE FQDN to avoid double-flagging the domain part.

  EMAIL
    \b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b

  CREDENTIAL after email  (lab-note pattern: "email@domain - Password123!")
    @[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\s+[\-\u2013\u2014:=]\s+(\S{6,})

  CREDENTIAL keywords
    (?:password|passwd|pwd|pass|secret|key|token|cred)s?\s*[:\-=]\s*(\S+)

  IPv4
    \b((?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}
       (?:25[0-5]|2[0-4]\d|[01]?\d\d?))\b

  IPv6  (abbreviated forms)
    \b((?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4})\b

  FQDN  (2+ dots; run safelist filter after match)
    \b((?:[a-zA-Z0-9\-]+\.){2,}[a-zA-Z]{2,})\b

  SHORT HOSTNAME in shell prompt — [version] hostname > command
    \[[^\]]{1,40}\]\s+([a-zA-Z0-9][a-zA-Z0-9\-]{4,})\s+[>#$]

  SHORT HOSTNAME in shell prompt — [user@hostname dir]# or $
    \[(?:[a-zA-Z0-9_\-]+@)([a-zA-Z0-9][a-zA-Z0-9\-]{3,})\s

  WINDOWS UNC PATH
    (\\\\[a-zA-Z0-9\-]+(?:\\[^\s<>"]+)+)

  WINDOWS ABSOLUTE PATH
    ([A-Za-z]:\\(?:[^\\\s<>"]+\\)*[^\\\s<>"]+)

  TICKET NUMBERS
    \b((?:INC|CHG|REQ|SR|RITM|PRB|TASK)\d{5,10})\b

  AUTH TOKENS / CREDENTIALS IN URL QUERY STRINGS
    [?&]((?:token|key|sig|auth|secret|session|api[_\-]?key|
          password|passwd|pwd)=[^\s&"'<>]+)

  DOMAIN\USERNAME
    \b([A-Z][A-Z0-9]{1,14}\\[a-zA-Z0-9_\-]+)\b

  TRAINING URL WITH USER ID  (logicaloperations.learnondemand.net pattern)
    (https?://[^\s"'<>]+/(?:User|user)/[^\s/"'<>]+/\d{4,})

2.3  Canonical Mapping Strategy

  Rule: one original value always maps to the same token across ALL files.
  The mapping is built once in mapping.json and reused every run.
  New candidates are appended on re-discovery; existing entries are never
  overwritten automatically.

  mapping.json structure:
  {
    "_metadata": {
      "version": 1,
      "last_discover": "2026-04-24T...",
      "counters": { "email": 2, "host": 4, "ip": 3, "ticket_INC": 1 }
    },
    "emails":       { "nick.bennett@insight.com": "user001@example.com" },
    "credentials":  { "Solana001!!!": "[REDACTED]" },
    "ips":          { "10.45.22.100": "10.10.1.100" },
    "hostnames":    { "jd1ltlanbufwm01": "host001.corp.local" },
    "tickets":      { "INC0438984": "INC000001" },
    "domain_users": { "CORP\\jsmith": "CORP\\user001" },
    "unc_paths":    {},
    "win_paths":    {},
    "auth_tokens":  {}
  }

  Workflow:
    1. Run:  python sanitize_notes.py discover --root ./Bennett-Notes
                                               --map mapping.json
    2. Human reviews mapping.json — confirm tokens, adjust where needed,
       and manually add credentials found in flagged-lines output.
    3. Run:  python sanitize_notes.py apply --root ./Bennett-Notes
                                            --map mapping.json
                                            --output ./Sanitized-Notes
    4. Run:  python sanitize_notes.py validate --root ./Sanitized-Notes
                                               --map mapping.json
    5. Keep mapping.json in a PRIVATE location.
       Never commit it alongside the published notes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3  LOCAL SCRIPT REFERENCE  (sanitize_notes.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Requires:  Python 3.9+,  beautifulsoup4  (pip install beautifulsoup4)

  Subcommands
  ───────────
  discover    Scan all .html files under --root; populate --map with
              candidate entities and auto-generated replacement tokens.
              New candidates are appended on re-runs; existing entries
              are never overwritten.
              Emits a "flagged lines" list of lines containing emails so
              adjacent credentials can be manually added to mapping.json.

  apply       Apply the reviewed --map to all .html files and write
              sanitized copies to --output (mirrors source folder structure).
              Non-HTML assets are copied unchanged when --copy-assets is set.
              Produces substitution_log.txt in the output root.

  validate    Re-scan all .html files in --root against the same regex
              patterns.  Known-safe replacement tokens and safelisted domains
              are excluded.  Exits non-zero if residual sensitive matches
              remain.

  Common options
  ──────────────
  --root          Root folder to scan (default: ./Bennett-Notes)
  --map           Path to mapping.json
  --output        Output folder for sanitized files  (apply only)
  --safelist      Optional file of extra safe domains/terms, one per line
  --dry-run       Show planned changes without writing any files
  --copy-assets   Copy non-.html files (images, .bin) to output dir

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4  IMAGE AND ALT-TEXT HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OneNote exports images as .bin files (binary PNG/JPEG) alongside HTML.
  The alt attribute contains OCR-extracted text from the screenshot.

4.1  Alt text
  - Treat as a first-class text node; apply all regex patterns.
  - If alt text contains sensitive data that cannot be cleanly replaced
    in context, substitute the entire alt value with: [screenshot]

4.2  Binary image files
  - The script copies them unchanged to the output directory.
  - Pixel-level text in screenshots is NOT auto-redacted by the script.
  - Flag for manual review: any image whose alt text triggered a regex match.

4.3  Manual review checklist for images
  - Does the screenshot show a hostname, IP, email, or credential?
  - If yes: crop/blur the sensitive region using an image editor, then
    replace the .bin file in the output directory.
  - Re-run validate after manual image edits.

4.4  EXIF / metadata
  - Strip EXIF metadata from any standalone image files before publishing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5  HTML ATTRIBUTE DECISION TABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Attribute                Action
  ─────────────────────── ────────────────────────────────────────────────────
  alt                      SCAN — apply all patterns; full redact if needed
  title  (element)         SCAN — apply all patterns
  href                     SCAN if absolute URL and domain not on safelist;
                           also strip user-ID segments from training URLs
  src  (img)               SKIP if relative path;  SCAN if absolute URL
  data-fullres-src         SKIP if relative path;  SCAN if absolute URL
  data-src-type            SKIP — MIME type only  (e.g., image/png)
  data-fullres-src-type    SKIP — MIME type only
  data-absolute-enabled    SKIP — layout flag
  style  (inline)          SKIP — layout/formatting only
  width, height            SKIP — numeric dimensions
  lang                     SKIP
  <meta name="created">    PRESERVE — ISO timestamp, not sensitive
  <meta charset>           SKIP
  HTML comments            SCAN — remove entire comment if match found
  <title>  (page)          SCAN — note name is usually a product/topic,
                           safe in practice but confirm before skipping

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6  VALIDATION CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Run the 'validate' subcommand, then confirm all items below pass:

  [ ] No email matches outside example.com / example.net / example.org
  [ ] No IPv4 addresses outside 10.10.x.x and RFC 5737 ranges
  [ ] No IPv6 addresses outside 2001:db8::/32
  [ ] No FQDNs with non-safelisted domains
  [ ] No real ticket numbers  (INC/CHG/REQ/SR/RITM/PRB)
  [ ] No credentials, tokens, or password strings
  [ ] No Domain\user patterns with real domain names
  [ ] No UNC paths with real server names
  [ ] No company or customer name strings
  [ ] No training URLs containing user-specific ID path segments
  [ ] Alt text reviewed for images that triggered regex matches
  [ ] Flagged-lines output reviewed for credential patterns
  [ ] mapping.json stored in private location, not with published files
  [ ] Substitution log reviewed; zero-replacement files investigated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7  AGENT INSTRUCTIONS  (Copilot Studio / LLM system prompt)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Paste everything below this line as the agent's Instructions / system prompt]

You are a Sanitization Assistant for technical notes and logs that will be
republished in a public or broadly shared knowledge base.

Your primary goal is to remove or obfuscate any sensitive information while
preserving the technical detail, structure, and usefulness of the content.

GENERAL BEHAVIOR
  - Do not introduce any real organisations, brands, or identifiable data.
  - Preserve the structure and formatting of the input (HTML, Markdown, or
    plain text), only changing values that reveal sensitive information.
  - Keep timestamps, error codes, configuration option names, command syntax,
    and protocol details unchanged unless they contain sensitive identifiers.
  - Apply replacements consistently: the same original value must always
    produce the same replacement token within a session.
  - Before processing, identify the entity type of each candidate and apply
    the appropriate rule below.

SAFELIST — do not modify anything from these domains or vendors:
  dell.com, emc.com, dellemc.com, veritas.com, veeam.com, cohesity.com,
  rubrik.com, commvault.com, netapp.com, quantum.com, spectralogic.com,
  bravais.com, learnondemand.net, logicaloperations.learnondemand.net,
  microsoft.com, microsoftonline.com, azure.com, graph.microsoft.com,
  google.com, googleapis.com, amazon.com, amazonaws.com,
  example.com, example.net, example.org, example.test, corp.local

SANITIZATION RULES

  1. IP ADDRESSES
     - All real IP addresses are potentially sensitive.
     - Private IPv4: map to 10.10.1.N preserving last octet.
       Example: 10.45.22.100 → 10.10.1.100
     - Public IPv4: map to RFC 5737 range 198.51.100.N.
       Example: 52.183.45.10 → 198.51.100.10
     - IPv6: map to 2001:db8:: prefix.
       Example: 2603:1020:200::5 → 2001:db8:200::5

  2. HOSTNAMES AND DOMAINS
     - Replace real internal hostnames and FQDNs with generic equivalents,
       preserving the role/tier where identifiable:
         prod-db01.corp.com      → db01.corp.local
         backup-media01.acme.com → media01.corp.local
     - For short hostnames in shell prompts — both patterns:
         [msdp-16.0.1] jd1ltlanbufwm01 > command  →  [msdp-16.0.1] host001 > command
         [root@jd1ltlanbuflx01 mnt]#               →  [root@host002 mnt]#
     - Use placeholder domains: example.com, corp.local, lab.example.com.
     - Never modify hostnames/FQDNs on the safelist.

  3. EMAIL ADDRESSES AND USERNAMES
     - Individual: jane.doe@company.com → user001@example.com
     - Role/team:  network-ops@company.com → netops@example.com
     - Usernames:  DOMAIN\jsmith → CORP\user001
     - Service accounts: svc_backup → svc001
     - Maintain distinction between user, admin, and service account types.

  4. CREDENTIALS AND TOKENS
     - Replace ALL passwords, API keys, tokens, and secrets with [REDACTED].
     - Remove auth tokens from URL query strings entirely.
     - Watch specifically for the lab-note pattern where an email is followed
       by a separator and a password on the same line:
         nick.bennett@insight.com - Solana001!!!
         → user001@example.com - [REDACTED]
     - Any string that follows "password:", "passwd:", "pwd:", "secret:",
       "key:", "token:" (case-insensitive) must be replaced with [REDACTED].

  5. COMPANY NAMES, ORGANISATIONS, AND LOCATIONS
     - Replace customer/client org names: ClientCorp → CustomerA
     - Replace employer or internal org identifiers similarly.
     - Replace specific offices/cities: Minneapolis Office → Midwest-Office-01

  6. TICKET AND CASE NUMBERS
     - INC0438984 → INC000001  (zero-padded 6 digits)
     - CHG987654  → CHG000001
     - Preserve the prefix (INC, CHG, REQ, SR, RITM, PRB, TASK).

  7. TRAINING URLS WITH USER-SPECIFIC IDS
     - Safelisted base domain is preserved; only the user-ID segment is removed.
       https://logicaloperations.learnondemand.net/User/CurrentTraining/2517591
       → https://logicaloperations.learnondemand.net/  [user-ID removed]

  8. FILE PATHS
     - UNC:      \\corp-fs01\Finance\Payroll → \\fileserver001\dept001\data001
     - Windows:  C:\Users\jsmith\Projects\ClientX
                 → C:\Users\user001\Projects\project001

  9. HTML FORMATTING RULES
     - Preserve all HTML tags and structural attributes (style, width, height,
       data-absolute-enabled, data-src-type, data-fullres-src-type, lang).
     - Sanitize text nodes and these attributes: alt, title, href (non-safelisted
       absolute URLs).
     - For img alt text: apply all rules; if the alt text contains sensitive
       content that cannot be cleanly replaced in context, substitute the
       entire alt value with: [screenshot]
     - Preserve relative src/href paths (they reference local image files).
     - Remove HTML comments if they contain sensitive identifiers.

  10. WHAT NOT TO DO
      - Do not redact everything; only obfuscate identifiable/sensitive items.
      - Do not change protocols, ports, HTTP verbs, config key names, error
        codes, log severity levels, product version numbers, or CLI syntax.
      - Do not invent real-world company names as replacements.
      - Do not alter the note's technical meaning or remove educational content.
```

---

## File 2: `sanitize_notes.py`

Save alongside the other scripts in `e:\VSCode-Root\onenote\`.

```python
#!/usr/bin/env python3
"""
sanitize_notes.py — Discover, replace, and validate sensitive entities in
exported HTML notes before public knowledge-base publication.

Requires:  pip install beautifulsoup4

Workflow:
  1. python sanitize_notes.py discover --root ./Bennett-Notes --map mapping.json
  2. Review / edit mapping.json — adjust tokens, add credentials from flagged lines.
  3. python sanitize_notes.py apply    --root ./Bennett-Notes \\
                                       --map mapping.json \\
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

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_ROOT   = Path(r"E:\VSCode-Root\onenote\Bennett-Notes")
DEFAULT_MAP    = Path(r"E:\VSCode-Root\onenote\mapping.json")
DEFAULT_OUTPUT = Path(r"E:\VSCode-Root\onenote\Sanitized-Notes")

# ── Safelist ──────────────────────────────────────────────────────────────────
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
    # Safe output-token domains — never flag as sensitive
    "example.com", "example.net", "example.org", "example.test",
    "corp.local",
}

# RFC 5737 / RFC 3849 documentation ranges used as output tokens
_SAFE_IPV4_PREFIXES: Tuple[str, ...] = (
    "192.0.2.", "198.51.100.", "203.0.113.", "10.10.",
)
_SAFE_IPV6_PREFIX = "2001:db8"

# ── Regex catalog ─────────────────────────────────────────────────────────────
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
# Training URL with user-ID path segment
_TRAINING_URL_RE = re.compile(
    r"(https?://[^\s\"'<>]+/(?:User|user)/[^\s/\"'<>]+/\d{4,}[^\s\"'<>]*)"
)

# HTML attributes to scan as plain text
_TEXT_ATTRS = {"alt", "title"}
# HTML attributes to scan only when value is an absolute URL
_URL_ATTRS = {"href", "src", "data-fullres-src"}

# Windows system paths that are not sensitive
_SAFE_WIN_PREFIXES = (
    "c:\\windows", "c:\\program files", "c:\\program files (x86)",
    "/usr/", "/etc/", "/var/", "/opt/", "/tmp/",
)


# ── Mapping I/O ───────────────────────────────────────────────────────────────

def _empty_mapping() -> Dict:
    return {
        "_metadata": {"version": 1, "counters": {}},
        "emails":       {},
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
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return _empty_mapping()


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
        "emails", "credentials", "ips", "hostnames", "tickets",
        "domain_users", "unc_paths", "win_paths", "auth_tokens",
    ):
        for k, v in mapping.get(section, {}).items():
            if k and v:
                result[k] = v
    return result


# ── Safelist helpers ───────────────────────────────────────────────────────────

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


# ── Entity extraction ──────────────────────────────────────────────────────────

def extract_entities(text: str, extra_safe: Set[str]) -> Dict[str, Set[str]]:
    """Return {category: set_of_candidate_values} found in text."""
    found: Dict[str, Set[str]] = defaultdict(set)

    # Emails first — extract their domains so FQDN pass can skip them
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

    # FQDNs — skip if already captured as email domain or safelisted
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

    # UNC paths
    for m in _UNC_RE.finditer(text):
        found["unc_paths"].add(m.group(1))

    # Windows absolute paths — skip common system paths
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
    html = path.read_text(encoding="utf-8", errors="replace")
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


# ── Token generators ───────────────────────────────────────────────────────────

def _token_email(addr: str, mapping: Dict) -> str:
    n = _next_counter(mapping, "email")
    local = addr.split("@")[0]
    if "-" in local or "_" in local:
        hint = re.sub(r"[^a-z]", "", local.split("-")[0].split("_")[0].lower())[:6]
        return f"{hint or 'team'}{n:03d}@example.com"
    return f"user{n:03d}@example.com"


def _token_ip(addr: str, mapping: Dict) -> str:
    parts = addr.split(".")
    if len(parts) == 4:
        try:
            last = int(parts[3])
            # Avoid duplicate last-octet collisions by checking existing values
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


# ── Subcommand: discover ───────────────────────────────────────────────────────

def cmd_discover(args: argparse.Namespace) -> None:
    extra_safe = load_extra_safelist(args.safelist)
    mapping = load_mapping(args.map)

    html_files = sorted(args.root.rglob("*.html"))
    if not html_files:
        print(f"No .html files found under {args.root}")
        return

    new_counts: Dict[str, int] = defaultdict(int)
    flagged_lines: List[str] = []

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        entities = extract_from_html(html_path, extra_safe)
        raw = html_path.read_text(encoding="utf-8", errors="replace")

        for email in entities.get("emails", set()):
            if email not in mapping["emails"]:
                mapping["emails"][email] = _token_email(email, mapping)
                new_counts["emails"] += 1
            # Flag surrounding lines for manual credential review
            for line in raw.splitlines():
                if email in line and len(line.strip()) > len(email) + 4:
                    flagged_lines.append(f"  [{rel}]  {line.strip()[:140]}")

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

    print(f"\nScanned {len(html_files)} HTML file(s)")
    print("New candidates added:")
    for k in ("emails", "credentials", "ips", "hostnames", "tickets",
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


# ── Subcommand: apply ──────────────────────────────────────────────────────────

def _apply_text(text: str, replacements: Dict[str, str]) -> Tuple[str, int]:
    """Replace all mapping keys (longest first) in text. Returns (result, count)."""
    count = 0
    for original in sorted(replacements, key=len, reverse=True):
        if original in text:
            text = text.replace(original, replacements[original])
            count += 1
    return text, count


def _sanitize_html(path: Path, replacements: Dict[str, str]) -> Tuple[str, int]:
    html = path.read_text(encoding="utf-8", errors="replace")
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

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        out_path = args.output / rel
        sanitized, count = _sanitize_html(html_path, replacements)
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
        f"sanitize_notes.py — apply log\n"
        f"Run:    {datetime.now().isoformat()}\n"
        f"Source: {args.root}\n"
        f"Output: {args.output}\n"
        f"Total substitutions: {total_subs}\n\n"
        f"{'Subs':>5}  File\n"
        f"{'─'*5}  {'─'*70}\n"
    ) + "\n".join(log_lines)

    if not args.dry_run:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "substitution_log.txt").write_text(log_content, encoding="utf-8")
        print(f"Sanitized {len(html_files)} file(s) → {args.output}")
        print(f"Total substitutions: {total_subs}")
    else:
        print(f"[dry-run] {len(html_files)} file(s), {total_subs} substitution(s)")
        for line in log_lines[:25]:
            print(f"  {line}")


# ── Subcommand: validate ───────────────────────────────────────────────────────

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
        for category, values in entities.items():
            for val in values:
                if val not in known_safe_tokens:
                    issues.append(f"  [{category:<14}] {val!r:<50}  {rel}")

    if issues:
        print(f"VALIDATE FAILED — {len(issues)} residual sensitive match(es):\n")
        for issue in sorted(issues)[:100]:
            print(issue)
        if len(issues) > 100:
            print(f"\n  ... and {len(issues) - 100} more")
        sys.exit(1)
    else:
        print(f"VALIDATE PASSED — {len(html_files)} file(s) clean")


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
```


## License: unknown
https://github.com/tinabuzanis/machine-translation/blob/347a1eec9dab94f6817df89a387f50901d14bcd5/trim_models_and_tok.py

```
Good — confirmed key patterns: `nick.bennett@insight.com - Solana001!!!` (email+credential), `[msdp-16.0.1] jd1ltlanbufwm01 >` (shell prompt hostname), and training URLs with embedded user IDs. Both files are designed around these.

---

## File 1: `sanitize-framework.txt` (full rewrite)

```
==============================================================================
  NOTES SANITIZATION FRAMEWORK  v1.1
  Purpose : Obfuscate sensitive identifiers in exported HTML notes prior to
            publication in a public or broadly-shared knowledge base.
  Updated : 2026-04-24
==============================================================================

  CONTENTS
  ────────
  Section 1  Scope and Exclusions
  Section 2  Sanitization Rules
    2.1  Entity rules and replacement tokens
    2.2  Regex pattern catalog
    2.3  Canonical mapping strategy
  Section 3  Local Script Reference  (sanitize_notes.py)
  Section 4  Image and Alt-Text Handling
  Section 5  HTML Attribute Decision Table
  Section 6  Validation Checklist
  Section 7  Agent Instructions  (Copilot Studio / LLM system prompt)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1  SCOPE AND EXCLUSIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1.1  Purpose
  These notes cover enterprise backup/recovery products (Avamar, Veeam,
  NetBackup, Cohesity, Rubrik, CommVault, NetApp, Quantum, Spectra Logic)
  and cloud platforms (AWS, Azure, GCP).  Most notes are training, lab, and
  field-support references.  Sanitization removes personal and customer
  identifiers while keeping all technical detail intact.

1.2  What MUST be obfuscated
  - Real names of employees, customers, or contacts
  - Internal or customer email addresses  (including work addresses such as
    name@insight.com)
  - Credentials — passwords, API keys, tokens, secrets — appearing anywhere
    in text, including "email - password" patterns from lab notes
  - Internal hostnames and FQDNs (customer/org-specific)
  - Short hostnames appearing in shell prompts  (e.g., [version] hostname >)
  - Real IP addresses (internal and public)
  - Internal ticket, case, or change record numbers  (INC, CHG, REQ, SR …)
  - Internal UNC paths and Windows absolute paths that expose org structure
  - Company and organisation names (customers, employers)
  - Specific office or city names tied to internal infrastructure
  - Training or lab portal URLs that contain a user-specific ID in the path
    (e.g., /User/CurrentTraining/2517591)

1.3  What MUST be preserved  (safelist)
  Vendor product names and their official domains:
    dell.com  emc.com  dellemc.com
    veritas.com
    veeam.com
    cohesity.com
    rubrik.com
    commvault.com
    netapp.com
    quantum.com
    spectralogic.com
    bravais.com                       (Dell training platform)
    learnondemand.net                 (Veeam/LogicalOps training — base domain
                                       is safe; only the user-ID path segment
                                       needs removal)
    microsoft.com  microsoftonline.com  azure.com  graph.microsoft.com
    google.com  googleapis.com
    amazon.com  amazonaws.com

  Technical content that must not be altered:
    - Protocol names  (HTTP, HTTPS, RDP, NFS, SMB, iSCSI …)
    - Port numbers
    - CLI commands and their flags / options
    - Error codes and log severity levels
    - RFC-standard IP ranges already used as output tokens:
        192.0.2.0/24,  198.51.100.0/24,  203.0.113.0/24,  2001:db8::/32
    - Product version strings
    - Configuration key names  (but NOT their values when those values
      contain PII or credentials)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2  SANITIZATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2.1  Entity Rules and Replacement Tokens

  ENTITY TYPE              TOKEN FORMAT              NOTES
  ─────────────────────── ─────────────────────── ─────────────────────────
  Email (personal)         user001@example.com     increment per unique addr
  Email (role/team)        netops@example.com      preserve functional hint
  Credential / password    [REDACTED]              always full replacement;
                                                   never preserve any part
  IPv4 private             10.10.1.N               N = last octet of original
  IPv4 public              198.51.100.N            RFC 5737 range
  IPv6                     2001:db8::N             RFC 3849 range
  FQDN (with dots)         host001.corp.local      preserve role prefix if
                                                   clear (db, app, web …)
  Short hostname           host001                 hostnames without a domain
  Shell-prompt hostname    host001                 from [ver] hostname > or
                                                   [user@hostname dir]#
  Domain\user              CORP\user001            keep CORP\ prefix
  Service account          svc001                  keep svc_ prefix style
  Person name (standalone) PERSON_001
  Ticket INC               INC000001               zero-padded 6 digits
  Ticket CHG               CHG000001
  Ticket REQ/SR/RITM       REQ000001  etc.
  UNC path                 \\fileserver001\share001 replace server + share
  Windows absolute path    C:\data\project001\...  replace non-system folders
  API token in URL query   [REDACTED]              strip entire key=value pair
  Training URL with user   strip the user-ID path  keep base domain + course
  Customer / org name      CustomerA, CustomerB    sequential labels
  City / office            Region-Office-01        e.g., Midwest-Office-01

2.2  Regex Pattern Catalog

  Apply safelist exclusion BEFORE flagging any FQDN or IP match.
  Run email pattern BEFORE FQDN to avoid double-flagging the domain part.

  EMAIL
    \b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b

  CREDENTIAL after email  (lab-note pattern: "email@domain - Password123!")
    @[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\s+[\-\u2013\u2014:=]\s+(\S{6,})

  CREDENTIAL keywords
    (?:password|passwd|pwd|pass|secret|key|token|cred)s?\s*[:\-=]\s*(\S+)

  IPv4
    \b((?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}
       (?:25[0-5]|2[0-4]\d|[01]?\d\d?))\b

  IPv6  (abbreviated forms)
    \b((?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4})\b

  FQDN  (2+ dots; run safelist filter after match)
    \b((?:[a-zA-Z0-9\-]+\.){2,}[a-zA-Z]{2,})\b

  SHORT HOSTNAME in shell prompt — [version] hostname > command
    \[[^\]]{1,40}\]\s+([a-zA-Z0-9][a-zA-Z0-9\-]{4,})\s+[>#$]

  SHORT HOSTNAME in shell prompt — [user@hostname dir]# or $
    \[(?:[a-zA-Z0-9_\-]+@)([a-zA-Z0-9][a-zA-Z0-9\-]{3,})\s

  WINDOWS UNC PATH
    (\\\\[a-zA-Z0-9\-]+(?:\\[^\s<>"]+)+)

  WINDOWS ABSOLUTE PATH
    ([A-Za-z]:\\(?:[^\\\s<>"]+\\)*[^\\\s<>"]+)

  TICKET NUMBERS
    \b((?:INC|CHG|REQ|SR|RITM|PRB|TASK)\d{5,10})\b

  AUTH TOKENS / CREDENTIALS IN URL QUERY STRINGS
    [?&]((?:token|key|sig|auth|secret|session|api[_\-]?key|
          password|passwd|pwd)=[^\s&"'<>]+)

  DOMAIN\USERNAME
    \b([A-Z][A-Z0-9]{1,14}\\[a-zA-Z0-9_\-]+)\b

  TRAINING URL WITH USER ID  (logicaloperations.learnondemand.net pattern)
    (https?://[^\s"'<>]+/(?:User|user)/[^\s/"'<>]+/\d{4,})

2.3  Canonical Mapping Strategy

  Rule: one original value always maps to the same token across ALL files.
  The mapping is built once in mapping.json and reused every run.
  New candidates are appended on re-discovery; existing entries are never
  overwritten automatically.

  mapping.json structure:
  {
    "_metadata": {
      "version": 1,
      "last_discover": "2026-04-24T...",
      "counters": { "email": 2, "host": 4, "ip": 3, "ticket_INC": 1 }
    },
    "emails":       { "nick.bennett@insight.com": "user001@example.com" },
    "credentials":  { "Solana001!!!": "[REDACTED]" },
    "ips":          { "10.45.22.100": "10.10.1.100" },
    "hostnames":    { "jd1ltlanbufwm01": "host001.corp.local" },
    "tickets":      { "INC0438984": "INC000001" },
    "domain_users": { "CORP\\jsmith": "CORP\\user001" },
    "unc_paths":    {},
    "win_paths":    {},
    "auth_tokens":  {}
  }

  Workflow:
    1. Run:  python sanitize_notes.py discover --root ./Bennett-Notes
                                               --map mapping.json
    2. Human reviews mapping.json — confirm tokens, adjust where needed,
       and manually add credentials found in flagged-lines output.
    3. Run:  python sanitize_notes.py apply --root ./Bennett-Notes
                                            --map mapping.json
                                            --output ./Sanitized-Notes
    4. Run:  python sanitize_notes.py validate --root ./Sanitized-Notes
                                               --map mapping.json
    5. Keep mapping.json in a PRIVATE location.
       Never commit it alongside the published notes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3  LOCAL SCRIPT REFERENCE  (sanitize_notes.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Requires:  Python 3.9+,  beautifulsoup4  (pip install beautifulsoup4)

  Subcommands
  ───────────
  discover    Scan all .html files under --root; populate --map with
              candidate entities and auto-generated replacement tokens.
              New candidates are appended on re-runs; existing entries
              are never overwritten.
              Emits a "flagged lines" list of lines containing emails so
              adjacent credentials can be manually added to mapping.json.

  apply       Apply the reviewed --map to all .html files and write
              sanitized copies to --output (mirrors source folder structure).
              Non-HTML assets are copied unchanged when --copy-assets is set.
              Produces substitution_log.txt in the output root.

  validate    Re-scan all .html files in --root against the same regex
              patterns.  Known-safe replacement tokens and safelisted domains
              are excluded.  Exits non-zero if residual sensitive matches
              remain.

  Common options
  ──────────────
  --root          Root folder to scan (default: ./Bennett-Notes)
  --map           Path to mapping.json
  --output        Output folder for sanitized files  (apply only)
  --safelist      Optional file of extra safe domains/terms, one per line
  --dry-run       Show planned changes without writing any files
  --copy-assets   Copy non-.html files (images, .bin) to output dir

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4  IMAGE AND ALT-TEXT HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OneNote exports images as .bin files (binary PNG/JPEG) alongside HTML.
  The alt attribute contains OCR-extracted text from the screenshot.

4.1  Alt text
  - Treat as a first-class text node; apply all regex patterns.
  - If alt text contains sensitive data that cannot be cleanly replaced
    in context, substitute the entire alt value with: [screenshot]

4.2  Binary image files
  - The script copies them unchanged to the output directory.
  - Pixel-level text in screenshots is NOT auto-redacted by the script.
  - Flag for manual review: any image whose alt text triggered a regex match.

4.3  Manual review checklist for images
  - Does the screenshot show a hostname, IP, email, or credential?
  - If yes: crop/blur the sensitive region using an image editor, then
    replace the .bin file in the output directory.
  - Re-run validate after manual image edits.

4.4  EXIF / metadata
  - Strip EXIF metadata from any standalone image files before publishing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5  HTML ATTRIBUTE DECISION TABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Attribute                Action
  ─────────────────────── ────────────────────────────────────────────────────
  alt                      SCAN — apply all patterns; full redact if needed
  title  (element)         SCAN — apply all patterns
  href                     SCAN if absolute URL and domain not on safelist;
                           also strip user-ID segments from training URLs
  src  (img)               SKIP if relative path;  SCAN if absolute URL
  data-fullres-src         SKIP if relative path;  SCAN if absolute URL
  data-src-type            SKIP — MIME type only  (e.g., image/png)
  data-fullres-src-type    SKIP — MIME type only
  data-absolute-enabled    SKIP — layout flag
  style  (inline)          SKIP — layout/formatting only
  width, height            SKIP — numeric dimensions
  lang                     SKIP
  <meta name="created">    PRESERVE — ISO timestamp, not sensitive
  <meta charset>           SKIP
  HTML comments            SCAN — remove entire comment if match found
  <title>  (page)          SCAN — note name is usually a product/topic,
                           safe in practice but confirm before skipping

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6  VALIDATION CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Run the 'validate' subcommand, then confirm all items below pass:

  [ ] No email matches outside example.com / example.net / example.org
  [ ] No IPv4 addresses outside 10.10.x.x and RFC 5737 ranges
  [ ] No IPv6 addresses outside 2001:db8::/32
  [ ] No FQDNs with non-safelisted domains
  [ ] No real ticket numbers  (INC/CHG/REQ/SR/RITM/PRB)
  [ ] No credentials, tokens, or password strings
  [ ] No Domain\user patterns with real domain names
  [ ] No UNC paths with real server names
  [ ] No company or customer name strings
  [ ] No training URLs containing user-specific ID path segments
  [ ] Alt text reviewed for images that triggered regex matches
  [ ] Flagged-lines output reviewed for credential patterns
  [ ] mapping.json stored in private location, not with published files
  [ ] Substitution log reviewed; zero-replacement files investigated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7  AGENT INSTRUCTIONS  (Copilot Studio / LLM system prompt)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Paste everything below this line as the agent's Instructions / system prompt]

You are a Sanitization Assistant for technical notes and logs that will be
republished in a public or broadly shared knowledge base.

Your primary goal is to remove or obfuscate any sensitive information while
preserving the technical detail, structure, and usefulness of the content.

GENERAL BEHAVIOR
  - Do not introduce any real organisations, brands, or identifiable data.
  - Preserve the structure and formatting of the input (HTML, Markdown, or
    plain text), only changing values that reveal sensitive information.
  - Keep timestamps, error codes, configuration option names, command syntax,
    and protocol details unchanged unless they contain sensitive identifiers.
  - Apply replacements consistently: the same original value must always
    produce the same replacement token within a session.
  - Before processing, identify the entity type of each candidate and apply
    the appropriate rule below.

SAFELIST — do not modify anything from these domains or vendors:
  dell.com, emc.com, dellemc.com, veritas.com, veeam.com, cohesity.com,
  rubrik.com, commvault.com, netapp.com, quantum.com, spectralogic.com,
  bravais.com, learnondemand.net, logicaloperations.learnondemand.net,
  microsoft.com, microsoftonline.com, azure.com, graph.microsoft.com,
  google.com, googleapis.com, amazon.com, amazonaws.com,
  example.com, example.net, example.org, example.test, corp.local

SANITIZATION RULES

  1. IP ADDRESSES
     - All real IP addresses are potentially sensitive.
     - Private IPv4: map to 10.10.1.N preserving last octet.
       Example: 10.45.22.100 → 10.10.1.100
     - Public IPv4: map to RFC 5737 range 198.51.100.N.
       Example: 52.183.45.10 → 198.51.100.10
     - IPv6: map to 2001:db8:: prefix.
       Example: 2603:1020:200::5 → 2001:db8:200::5

  2. HOSTNAMES AND DOMAINS
     - Replace real internal hostnames and FQDNs with generic equivalents,
       preserving the role/tier where identifiable:
         prod-db01.corp.com      → db01.corp.local
         backup-media01.acme.com → media01.corp.local
     - For short hostnames in shell prompts — both patterns:
         [msdp-16.0.1] jd1ltlanbufwm01 > command  →  [msdp-16.0.1] host001 > command
         [root@jd1ltlanbuflx01 mnt]#               →  [root@host002 mnt]#
     - Use placeholder domains: example.com, corp.local, lab.example.com.
     - Never modify hostnames/FQDNs on the safelist.

  3. EMAIL ADDRESSES AND USERNAMES
     - Individual: jane.doe@company.com → user001@example.com
     - Role/team:  network-ops@company.com → netops@example.com
     - Usernames:  DOMAIN\jsmith → CORP\user001
     - Service accounts: svc_backup → svc001
     - Maintain distinction between user, admin, and service account types.

  4. CREDENTIALS AND TOKENS
     - Replace ALL passwords, API keys, tokens, and secrets with [REDACTED].
     - Remove auth tokens from URL query strings entirely.
     - Watch specifically for the lab-note pattern where an email is followed
       by a separator and a password on the same line:
         nick.bennett@insight.com - Solana001!!!
         → user001@example.com - [REDACTED]
     - Any string that follows "password:", "passwd:", "pwd:", "secret:",
       "key:", "token:" (case-insensitive) must be replaced with [REDACTED].

  5. COMPANY NAMES, ORGANISATIONS, AND LOCATIONS
     - Replace customer/client org names: ClientCorp → CustomerA
     - Replace employer or internal org identifiers similarly.
     - Replace specific offices/cities: Minneapolis Office → Midwest-Office-01

  6. TICKET AND CASE NUMBERS
     - INC0438984 → INC000001  (zero-padded 6 digits)
     - CHG987654  → CHG000001
     - Preserve the prefix (INC, CHG, REQ, SR, RITM, PRB, TASK).

  7. TRAINING URLS WITH USER-SPECIFIC IDS
     - Safelisted base domain is preserved; only the user-ID segment is removed.
       https://logicaloperations.learnondemand.net/User/CurrentTraining/2517591
       → https://logicaloperations.learnondemand.net/  [user-ID removed]

  8. FILE PATHS
     - UNC:      \\corp-fs01\Finance\Payroll → \\fileserver001\dept001\data001
     - Windows:  C:\Users\jsmith\Projects\ClientX
                 → C:\Users\user001\Projects\project001

  9. HTML FORMATTING RULES
     - Preserve all HTML tags and structural attributes (style, width, height,
       data-absolute-enabled, data-src-type, data-fullres-src-type, lang).
     - Sanitize text nodes and these attributes: alt, title, href (non-safelisted
       absolute URLs).
     - For img alt text: apply all rules; if the alt text contains sensitive
       content that cannot be cleanly replaced in context, substitute the
       entire alt value with: [screenshot]
     - Preserve relative src/href paths (they reference local image files).
     - Remove HTML comments if they contain sensitive identifiers.

  10. WHAT NOT TO DO
      - Do not redact everything; only obfuscate identifiable/sensitive items.
      - Do not change protocols, ports, HTTP verbs, config key names, error
        codes, log severity levels, product version numbers, or CLI syntax.
      - Do not invent real-world company names as replacements.
      - Do not alter the note's technical meaning or remove educational content.
```

---

## File 2: `sanitize_notes.py`

Save alongside the other scripts in `e:\VSCode-Root\onenote\`.

```python
#!/usr/bin/env python3
"""
sanitize_notes.py — Discover, replace, and validate sensitive entities in
exported HTML notes before public knowledge-base publication.

Requires:  pip install beautifulsoup4

Workflow:
  1. python sanitize_notes.py discover --root ./Bennett-Notes --map mapping.json
  2. Review / edit mapping.json — adjust tokens, add credentials from flagged lines.
  3. python sanitize_notes.py apply    --root ./Bennett-Notes \\
                                       --map mapping.json \\
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

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_ROOT   = Path(r"E:\VSCode-Root\onenote\Bennett-Notes")
DEFAULT_MAP    = Path(r"E:\VSCode-Root\onenote\mapping.json")
DEFAULT_OUTPUT = Path(r"E:\VSCode-Root\onenote\Sanitized-Notes")

# ── Safelist ──────────────────────────────────────────────────────────────────
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
    # Safe output-token domains — never flag as sensitive
    "example.com", "example.net", "example.org", "example.test",
    "corp.local",
}

# RFC 5737 / RFC 3849 documentation ranges used as output tokens
_SAFE_IPV4_PREFIXES: Tuple[str, ...] = (
    "192.0.2.", "198.51.100.", "203.0.113.", "10.10.",
)
_SAFE_IPV6_PREFIX = "2001:db8"

# ── Regex catalog ─────────────────────────────────────────────────────────────
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
# Training URL with user-ID path segment
_TRAINING_URL_RE = re.compile(
    r"(https?://[^\s\"'<>]+/(?:User|user)/[^\s/\"'<>]+/\d{4,}[^\s\"'<>]*)"
)

# HTML attributes to scan as plain text
_TEXT_ATTRS = {"alt", "title"}
# HTML attributes to scan only when value is an absolute URL
_URL_ATTRS = {"href", "src", "data-fullres-src"}

# Windows system paths that are not sensitive
_SAFE_WIN_PREFIXES = (
    "c:\\windows", "c:\\program files", "c:\\program files (x86)",
    "/usr/", "/etc/", "/var/", "/opt/", "/tmp/",
)


# ── Mapping I/O ───────────────────────────────────────────────────────────────

def _empty_mapping() -> Dict:
    return {
        "_metadata": {"version": 1, "counters": {}},
        "emails":       {},
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
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return _empty_mapping()


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
        "emails", "credentials", "ips", "hostnames", "tickets",
        "domain_users", "unc_paths", "win_paths", "auth_tokens",
    ):
        for k, v in mapping.get(section, {}).items():
            if k and v:
                result[k] = v
    return result


# ── Safelist helpers ───────────────────────────────────────────────────────────

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


# ── Entity extraction ──────────────────────────────────────────────────────────

def extract_entities(text: str, extra_safe: Set[str]) -> Dict[str, Set[str]]:
    """Return {category: set_of_candidate_values} found in text."""
    found: Dict[str, Set[str]] = defaultdict(set)

    # Emails first — extract their domains so FQDN pass can skip them
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

    # FQDNs — skip if already captured as email domain or safelisted
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

    # UNC paths
    for m in _UNC_RE.finditer(text):
        found["unc_paths"].add(m.group(1))

    # Windows absolute paths — skip common system paths
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
    html = path.read_text(encoding="utf-8", errors="replace")
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


# ── Token generators ───────────────────────────────────────────────────────────

def _token_email(addr: str, mapping: Dict) -> str:
    n = _next_counter(mapping, "email")
    local = addr.split("@")[0]
    if "-" in local or "_" in local:
        hint = re.sub(r"[^a-z]", "", local.split("-")[0].split("_")[0].lower())[:6]
        return f"{hint or 'team'}{n:03d}@example.com"
    return f"user{n:03d}@example.com"


def _token_ip(addr: str, mapping: Dict) -> str:
    parts = addr.split(".")
    if len(parts) == 4:
        try:
            last = int(parts[3])
            # Avoid duplicate last-octet collisions by checking existing values
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


# ── Subcommand: discover ───────────────────────────────────────────────────────

def cmd_discover(args: argparse.Namespace) -> None:
    extra_safe = load_extra_safelist(args.safelist)
    mapping = load_mapping(args.map)

    html_files = sorted(args.root.rglob("*.html"))
    if not html_files:
        print(f"No .html files found under {args.root}")
        return

    new_counts: Dict[str, int] = defaultdict(int)
    flagged_lines: List[str] = []

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        entities = extract_from_html(html_path, extra_safe)
        raw = html_path.read_text(encoding="utf-8", errors="replace")

        for email in entities.get("emails", set()):
            if email not in mapping["emails"]:
                mapping["emails"][email] = _token_email(email, mapping)
                new_counts["emails"] += 1
            # Flag surrounding lines for manual credential review
            for line in raw.splitlines():
                if email in line and len(line.strip()) > len(email) + 4:
                    flagged_lines.append(f"  [{rel}]  {line.strip()[:140]}")

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

    print(f"\nScanned {len(html_files)} HTML file(s)")
    print("New candidates added:")
    for k in ("emails", "credentials", "ips", "hostnames", "tickets",
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


# ── Subcommand: apply ──────────────────────────────────────────────────────────

def _apply_text(text: str, replacements: Dict[str, str]) -> Tuple[str, int]:
    """Replace all mapping keys (longest first) in text. Returns (result, count)."""
    count = 0
    for original in sorted(replacements, key=len, reverse=True):
        if original in text:
            text = text.replace(original, replacements[original])
            count += 1
    return text, count


def _sanitize_html(path: Path, replacements: Dict[str, str]) -> Tuple[str, int]:
    html = path.read_text(encoding="utf-8", errors="replace")
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

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        out_path = args.output / rel
        sanitized, count = _sanitize_html(html_path, replacements)
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
        f"sanitize_notes.py — apply log\n"
        f"Run:    {datetime.now().isoformat()}\n"
        f"Source: {args.root}\n"
        f"Output: {args.output}\n"
        f"Total substitutions: {total_subs}\n\n"
        f"{'Subs':>5}  File\n"
        f"{'─'*5}  {'─'*70}\n"
    ) + "\n".join(log_lines)

    if not args.dry_run:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "substitution_log.txt").write_text(log_content, encoding="utf-8")
        print(f"Sanitized {len(html_files)} file(s) → {args.output}")
        print(f"Total substitutions: {total_subs}")
    else:
        print(f"[dry-run] {len(html_files)} file(s), {total_subs} substitution(s)")
        for line in log_lines[:25]:
            print(f"  {line}")


# ── Subcommand: validate ───────────────────────────────────────────────────────

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
        for category, values in entities.items():
            for val in values:
                if val not in known_safe_tokens:
                    issues.append(f"  [{category:<14}] {val!r:<50}  {rel}")

    if issues:
        print(f"VALIDATE FAILED — {len(issues)} residual sensitive match(es):\n")
        for issue in sorted(issues)[:100]:
            print(issue)
        if len(issues) > 100:
            print(f"\n  ... and {len(issues) - 100} more")
        sys.exit(1)
    else:
        print(f"VALIDATE PASSED — {len(html_files)} file(s) clean")


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
```


## License: unknown
https://github.com/tinabuzanis/machine-translation/blob/347a1eec9dab94f6817df89a387f50901d14bcd5/trim_models_and_tok.py

```
Good — confirmed key patterns: `nick.bennett@insight.com - Solana001!!!` (email+credential), `[msdp-16.0.1] jd1ltlanbufwm01 >` (shell prompt hostname), and training URLs with embedded user IDs. Both files are designed around these.

---

## File 1: `sanitize-framework.txt` (full rewrite)

```
==============================================================================
  NOTES SANITIZATION FRAMEWORK  v1.1
  Purpose : Obfuscate sensitive identifiers in exported HTML notes prior to
            publication in a public or broadly-shared knowledge base.
  Updated : 2026-04-24
==============================================================================

  CONTENTS
  ────────
  Section 1  Scope and Exclusions
  Section 2  Sanitization Rules
    2.1  Entity rules and replacement tokens
    2.2  Regex pattern catalog
    2.3  Canonical mapping strategy
  Section 3  Local Script Reference  (sanitize_notes.py)
  Section 4  Image and Alt-Text Handling
  Section 5  HTML Attribute Decision Table
  Section 6  Validation Checklist
  Section 7  Agent Instructions  (Copilot Studio / LLM system prompt)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1  SCOPE AND EXCLUSIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1.1  Purpose
  These notes cover enterprise backup/recovery products (Avamar, Veeam,
  NetBackup, Cohesity, Rubrik, CommVault, NetApp, Quantum, Spectra Logic)
  and cloud platforms (AWS, Azure, GCP).  Most notes are training, lab, and
  field-support references.  Sanitization removes personal and customer
  identifiers while keeping all technical detail intact.

1.2  What MUST be obfuscated
  - Real names of employees, customers, or contacts
  - Internal or customer email addresses  (including work addresses such as
    name@insight.com)
  - Credentials — passwords, API keys, tokens, secrets — appearing anywhere
    in text, including "email - password" patterns from lab notes
  - Internal hostnames and FQDNs (customer/org-specific)
  - Short hostnames appearing in shell prompts  (e.g., [version] hostname >)
  - Real IP addresses (internal and public)
  - Internal ticket, case, or change record numbers  (INC, CHG, REQ, SR …)
  - Internal UNC paths and Windows absolute paths that expose org structure
  - Company and organisation names (customers, employers)
  - Specific office or city names tied to internal infrastructure
  - Training or lab portal URLs that contain a user-specific ID in the path
    (e.g., /User/CurrentTraining/2517591)

1.3  What MUST be preserved  (safelist)
  Vendor product names and their official domains:
    dell.com  emc.com  dellemc.com
    veritas.com
    veeam.com
    cohesity.com
    rubrik.com
    commvault.com
    netapp.com
    quantum.com
    spectralogic.com
    bravais.com                       (Dell training platform)
    learnondemand.net                 (Veeam/LogicalOps training — base domain
                                       is safe; only the user-ID path segment
                                       needs removal)
    microsoft.com  microsoftonline.com  azure.com  graph.microsoft.com
    google.com  googleapis.com
    amazon.com  amazonaws.com

  Technical content that must not be altered:
    - Protocol names  (HTTP, HTTPS, RDP, NFS, SMB, iSCSI …)
    - Port numbers
    - CLI commands and their flags / options
    - Error codes and log severity levels
    - RFC-standard IP ranges already used as output tokens:
        192.0.2.0/24,  198.51.100.0/24,  203.0.113.0/24,  2001:db8::/32
    - Product version strings
    - Configuration key names  (but NOT their values when those values
      contain PII or credentials)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2  SANITIZATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2.1  Entity Rules and Replacement Tokens

  ENTITY TYPE              TOKEN FORMAT              NOTES
  ─────────────────────── ─────────────────────── ─────────────────────────
  Email (personal)         user001@example.com     increment per unique addr
  Email (role/team)        netops@example.com      preserve functional hint
  Credential / password    [REDACTED]              always full replacement;
                                                   never preserve any part
  IPv4 private             10.10.1.N               N = last octet of original
  IPv4 public              198.51.100.N            RFC 5737 range
  IPv6                     2001:db8::N             RFC 3849 range
  FQDN (with dots)         host001.corp.local      preserve role prefix if
                                                   clear (db, app, web …)
  Short hostname           host001                 hostnames without a domain
  Shell-prompt hostname    host001                 from [ver] hostname > or
                                                   [user@hostname dir]#
  Domain\user              CORP\user001            keep CORP\ prefix
  Service account          svc001                  keep svc_ prefix style
  Person name (standalone) PERSON_001
  Ticket INC               INC000001               zero-padded 6 digits
  Ticket CHG               CHG000001
  Ticket REQ/SR/RITM       REQ000001  etc.
  UNC path                 \\fileserver001\share001 replace server + share
  Windows absolute path    C:\data\project001\...  replace non-system folders
  API token in URL query   [REDACTED]              strip entire key=value pair
  Training URL with user   strip the user-ID path  keep base domain + course
  Customer / org name      CustomerA, CustomerB    sequential labels
  City / office            Region-Office-01        e.g., Midwest-Office-01

2.2  Regex Pattern Catalog

  Apply safelist exclusion BEFORE flagging any FQDN or IP match.
  Run email pattern BEFORE FQDN to avoid double-flagging the domain part.

  EMAIL
    \b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b

  CREDENTIAL after email  (lab-note pattern: "email@domain - Password123!")
    @[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\s+[\-\u2013\u2014:=]\s+(\S{6,})

  CREDENTIAL keywords
    (?:password|passwd|pwd|pass|secret|key|token|cred)s?\s*[:\-=]\s*(\S+)

  IPv4
    \b((?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}
       (?:25[0-5]|2[0-4]\d|[01]?\d\d?))\b

  IPv6  (abbreviated forms)
    \b((?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4})\b

  FQDN  (2+ dots; run safelist filter after match)
    \b((?:[a-zA-Z0-9\-]+\.){2,}[a-zA-Z]{2,})\b

  SHORT HOSTNAME in shell prompt — [version] hostname > command
    \[[^\]]{1,40}\]\s+([a-zA-Z0-9][a-zA-Z0-9\-]{4,})\s+[>#$]

  SHORT HOSTNAME in shell prompt — [user@hostname dir]# or $
    \[(?:[a-zA-Z0-9_\-]+@)([a-zA-Z0-9][a-zA-Z0-9\-]{3,})\s

  WINDOWS UNC PATH
    (\\\\[a-zA-Z0-9\-]+(?:\\[^\s<>"]+)+)

  WINDOWS ABSOLUTE PATH
    ([A-Za-z]:\\(?:[^\\\s<>"]+\\)*[^\\\s<>"]+)

  TICKET NUMBERS
    \b((?:INC|CHG|REQ|SR|RITM|PRB|TASK)\d{5,10})\b

  AUTH TOKENS / CREDENTIALS IN URL QUERY STRINGS
    [?&]((?:token|key|sig|auth|secret|session|api[_\-]?key|
          password|passwd|pwd)=[^\s&"'<>]+)

  DOMAIN\USERNAME
    \b([A-Z][A-Z0-9]{1,14}\\[a-zA-Z0-9_\-]+)\b

  TRAINING URL WITH USER ID  (logicaloperations.learnondemand.net pattern)
    (https?://[^\s"'<>]+/(?:User|user)/[^\s/"'<>]+/\d{4,})

2.3  Canonical Mapping Strategy

  Rule: one original value always maps to the same token across ALL files.
  The mapping is built once in mapping.json and reused every run.
  New candidates are appended on re-discovery; existing entries are never
  overwritten automatically.

  mapping.json structure:
  {
    "_metadata": {
      "version": 1,
      "last_discover": "2026-04-24T...",
      "counters": { "email": 2, "host": 4, "ip": 3, "ticket_INC": 1 }
    },
    "emails":       { "nick.bennett@insight.com": "user001@example.com" },
    "credentials":  { "Solana001!!!": "[REDACTED]" },
    "ips":          { "10.45.22.100": "10.10.1.100" },
    "hostnames":    { "jd1ltlanbufwm01": "host001.corp.local" },
    "tickets":      { "INC0438984": "INC000001" },
    "domain_users": { "CORP\\jsmith": "CORP\\user001" },
    "unc_paths":    {},
    "win_paths":    {},
    "auth_tokens":  {}
  }

  Workflow:
    1. Run:  python sanitize_notes.py discover --root ./Bennett-Notes
                                               --map mapping.json
    2. Human reviews mapping.json — confirm tokens, adjust where needed,
       and manually add credentials found in flagged-lines output.
    3. Run:  python sanitize_notes.py apply --root ./Bennett-Notes
                                            --map mapping.json
                                            --output ./Sanitized-Notes
    4. Run:  python sanitize_notes.py validate --root ./Sanitized-Notes
                                               --map mapping.json
    5. Keep mapping.json in a PRIVATE location.
       Never commit it alongside the published notes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3  LOCAL SCRIPT REFERENCE  (sanitize_notes.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Requires:  Python 3.9+,  beautifulsoup4  (pip install beautifulsoup4)

  Subcommands
  ───────────
  discover    Scan all .html files under --root; populate --map with
              candidate entities and auto-generated replacement tokens.
              New candidates are appended on re-runs; existing entries
              are never overwritten.
              Emits a "flagged lines" list of lines containing emails so
              adjacent credentials can be manually added to mapping.json.

  apply       Apply the reviewed --map to all .html files and write
              sanitized copies to --output (mirrors source folder structure).
              Non-HTML assets are copied unchanged when --copy-assets is set.
              Produces substitution_log.txt in the output root.

  validate    Re-scan all .html files in --root against the same regex
              patterns.  Known-safe replacement tokens and safelisted domains
              are excluded.  Exits non-zero if residual sensitive matches
              remain.

  Common options
  ──────────────
  --root          Root folder to scan (default: ./Bennett-Notes)
  --map           Path to mapping.json
  --output        Output folder for sanitized files  (apply only)
  --safelist      Optional file of extra safe domains/terms, one per line
  --dry-run       Show planned changes without writing any files
  --copy-assets   Copy non-.html files (images, .bin) to output dir

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4  IMAGE AND ALT-TEXT HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OneNote exports images as .bin files (binary PNG/JPEG) alongside HTML.
  The alt attribute contains OCR-extracted text from the screenshot.

4.1  Alt text
  - Treat as a first-class text node; apply all regex patterns.
  - If alt text contains sensitive data that cannot be cleanly replaced
    in context, substitute the entire alt value with: [screenshot]

4.2  Binary image files
  - The script copies them unchanged to the output directory.
  - Pixel-level text in screenshots is NOT auto-redacted by the script.
  - Flag for manual review: any image whose alt text triggered a regex match.

4.3  Manual review checklist for images
  - Does the screenshot show a hostname, IP, email, or credential?
  - If yes: crop/blur the sensitive region using an image editor, then
    replace the .bin file in the output directory.
  - Re-run validate after manual image edits.

4.4  EXIF / metadata
  - Strip EXIF metadata from any standalone image files before publishing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5  HTML ATTRIBUTE DECISION TABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Attribute                Action
  ─────────────────────── ────────────────────────────────────────────────────
  alt                      SCAN — apply all patterns; full redact if needed
  title  (element)         SCAN — apply all patterns
  href                     SCAN if absolute URL and domain not on safelist;
                           also strip user-ID segments from training URLs
  src  (img)               SKIP if relative path;  SCAN if absolute URL
  data-fullres-src         SKIP if relative path;  SCAN if absolute URL
  data-src-type            SKIP — MIME type only  (e.g., image/png)
  data-fullres-src-type    SKIP — MIME type only
  data-absolute-enabled    SKIP — layout flag
  style  (inline)          SKIP — layout/formatting only
  width, height            SKIP — numeric dimensions
  lang                     SKIP
  <meta name="created">    PRESERVE — ISO timestamp, not sensitive
  <meta charset>           SKIP
  HTML comments            SCAN — remove entire comment if match found
  <title>  (page)          SCAN — note name is usually a product/topic,
                           safe in practice but confirm before skipping

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6  VALIDATION CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Run the 'validate' subcommand, then confirm all items below pass:

  [ ] No email matches outside example.com / example.net / example.org
  [ ] No IPv4 addresses outside 10.10.x.x and RFC 5737 ranges
  [ ] No IPv6 addresses outside 2001:db8::/32
  [ ] No FQDNs with non-safelisted domains
  [ ] No real ticket numbers  (INC/CHG/REQ/SR/RITM/PRB)
  [ ] No credentials, tokens, or password strings
  [ ] No Domain\user patterns with real domain names
  [ ] No UNC paths with real server names
  [ ] No company or customer name strings
  [ ] No training URLs containing user-specific ID path segments
  [ ] Alt text reviewed for images that triggered regex matches
  [ ] Flagged-lines output reviewed for credential patterns
  [ ] mapping.json stored in private location, not with published files
  [ ] Substitution log reviewed; zero-replacement files investigated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7  AGENT INSTRUCTIONS  (Copilot Studio / LLM system prompt)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Paste everything below this line as the agent's Instructions / system prompt]

You are a Sanitization Assistant for technical notes and logs that will be
republished in a public or broadly shared knowledge base.

Your primary goal is to remove or obfuscate any sensitive information while
preserving the technical detail, structure, and usefulness of the content.

GENERAL BEHAVIOR
  - Do not introduce any real organisations, brands, or identifiable data.
  - Preserve the structure and formatting of the input (HTML, Markdown, or
    plain text), only changing values that reveal sensitive information.
  - Keep timestamps, error codes, configuration option names, command syntax,
    and protocol details unchanged unless they contain sensitive identifiers.
  - Apply replacements consistently: the same original value must always
    produce the same replacement token within a session.
  - Before processing, identify the entity type of each candidate and apply
    the appropriate rule below.

SAFELIST — do not modify anything from these domains or vendors:
  dell.com, emc.com, dellemc.com, veritas.com, veeam.com, cohesity.com,
  rubrik.com, commvault.com, netapp.com, quantum.com, spectralogic.com,
  bravais.com, learnondemand.net, logicaloperations.learnondemand.net,
  microsoft.com, microsoftonline.com, azure.com, graph.microsoft.com,
  google.com, googleapis.com, amazon.com, amazonaws.com,
  example.com, example.net, example.org, example.test, corp.local

SANITIZATION RULES

  1. IP ADDRESSES
     - All real IP addresses are potentially sensitive.
     - Private IPv4: map to 10.10.1.N preserving last octet.
       Example: 10.45.22.100 → 10.10.1.100
     - Public IPv4: map to RFC 5737 range 198.51.100.N.
       Example: 52.183.45.10 → 198.51.100.10
     - IPv6: map to 2001:db8:: prefix.
       Example: 2603:1020:200::5 → 2001:db8:200::5

  2. HOSTNAMES AND DOMAINS
     - Replace real internal hostnames and FQDNs with generic equivalents,
       preserving the role/tier where identifiable:
         prod-db01.corp.com      → db01.corp.local
         backup-media01.acme.com → media01.corp.local
     - For short hostnames in shell prompts — both patterns:
         [msdp-16.0.1] jd1ltlanbufwm01 > command  →  [msdp-16.0.1] host001 > command
         [root@jd1ltlanbuflx01 mnt]#               →  [root@host002 mnt]#
     - Use placeholder domains: example.com, corp.local, lab.example.com.
     - Never modify hostnames/FQDNs on the safelist.

  3. EMAIL ADDRESSES AND USERNAMES
     - Individual: jane.doe@company.com → user001@example.com
     - Role/team:  network-ops@company.com → netops@example.com
     - Usernames:  DOMAIN\jsmith → CORP\user001
     - Service accounts: svc_backup → svc001
     - Maintain distinction between user, admin, and service account types.

  4. CREDENTIALS AND TOKENS
     - Replace ALL passwords, API keys, tokens, and secrets with [REDACTED].
     - Remove auth tokens from URL query strings entirely.
     - Watch specifically for the lab-note pattern where an email is followed
       by a separator and a password on the same line:
         nick.bennett@insight.com - Solana001!!!
         → user001@example.com - [REDACTED]
     - Any string that follows "password:", "passwd:", "pwd:", "secret:",
       "key:", "token:" (case-insensitive) must be replaced with [REDACTED].

  5. COMPANY NAMES, ORGANISATIONS, AND LOCATIONS
     - Replace customer/client org names: ClientCorp → CustomerA
     - Replace employer or internal org identifiers similarly.
     - Replace specific offices/cities: Minneapolis Office → Midwest-Office-01

  6. TICKET AND CASE NUMBERS
     - INC0438984 → INC000001  (zero-padded 6 digits)
     - CHG987654  → CHG000001
     - Preserve the prefix (INC, CHG, REQ, SR, RITM, PRB, TASK).

  7. TRAINING URLS WITH USER-SPECIFIC IDS
     - Safelisted base domain is preserved; only the user-ID segment is removed.
       https://logicaloperations.learnondemand.net/User/CurrentTraining/2517591
       → https://logicaloperations.learnondemand.net/  [user-ID removed]

  8. FILE PATHS
     - UNC:      \\corp-fs01\Finance\Payroll → \\fileserver001\dept001\data001
     - Windows:  C:\Users\jsmith\Projects\ClientX
                 → C:\Users\user001\Projects\project001

  9. HTML FORMATTING RULES
     - Preserve all HTML tags and structural attributes (style, width, height,
       data-absolute-enabled, data-src-type, data-fullres-src-type, lang).
     - Sanitize text nodes and these attributes: alt, title, href (non-safelisted
       absolute URLs).
     - For img alt text: apply all rules; if the alt text contains sensitive
       content that cannot be cleanly replaced in context, substitute the
       entire alt value with: [screenshot]
     - Preserve relative src/href paths (they reference local image files).
     - Remove HTML comments if they contain sensitive identifiers.

  10. WHAT NOT TO DO
      - Do not redact everything; only obfuscate identifiable/sensitive items.
      - Do not change protocols, ports, HTTP verbs, config key names, error
        codes, log severity levels, product version numbers, or CLI syntax.
      - Do not invent real-world company names as replacements.
      - Do not alter the note's technical meaning or remove educational content.
```

---

## File 2: `sanitize_notes.py`

Save alongside the other scripts in `e:\VSCode-Root\onenote\`.

```python
#!/usr/bin/env python3
"""
sanitize_notes.py — Discover, replace, and validate sensitive entities in
exported HTML notes before public knowledge-base publication.

Requires:  pip install beautifulsoup4

Workflow:
  1. python sanitize_notes.py discover --root ./Bennett-Notes --map mapping.json
  2. Review / edit mapping.json — adjust tokens, add credentials from flagged lines.
  3. python sanitize_notes.py apply    --root ./Bennett-Notes \\
                                       --map mapping.json \\
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

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_ROOT   = Path(r"E:\VSCode-Root\onenote\Bennett-Notes")
DEFAULT_MAP    = Path(r"E:\VSCode-Root\onenote\mapping.json")
DEFAULT_OUTPUT = Path(r"E:\VSCode-Root\onenote\Sanitized-Notes")

# ── Safelist ──────────────────────────────────────────────────────────────────
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
    # Safe output-token domains — never flag as sensitive
    "example.com", "example.net", "example.org", "example.test",
    "corp.local",
}

# RFC 5737 / RFC 3849 documentation ranges used as output tokens
_SAFE_IPV4_PREFIXES: Tuple[str, ...] = (
    "192.0.2.", "198.51.100.", "203.0.113.", "10.10.",
)
_SAFE_IPV6_PREFIX = "2001:db8"

# ── Regex catalog ─────────────────────────────────────────────────────────────
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
# Training URL with user-ID path segment
_TRAINING_URL_RE = re.compile(
    r"(https?://[^\s\"'<>]+/(?:User|user)/[^\s/\"'<>]+/\d{4,}[^\s\"'<>]*)"
)

# HTML attributes to scan as plain text
_TEXT_ATTRS = {"alt", "title"}
# HTML attributes to scan only when value is an absolute URL
_URL_ATTRS = {"href", "src", "data-fullres-src"}

# Windows system paths that are not sensitive
_SAFE_WIN_PREFIXES = (
    "c:\\windows", "c:\\program files", "c:\\program files (x86)",
    "/usr/", "/etc/", "/var/", "/opt/", "/tmp/",
)


# ── Mapping I/O ───────────────────────────────────────────────────────────────

def _empty_mapping() -> Dict:
    return {
        "_metadata": {"version": 1, "counters": {}},
        "emails":       {},
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
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return _empty_mapping()


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
        "emails", "credentials", "ips", "hostnames", "tickets",
        "domain_users", "unc_paths", "win_paths", "auth_tokens",
    ):
        for k, v in mapping.get(section, {}).items():
            if k and v:
                result[k] = v
    return result


# ── Safelist helpers ───────────────────────────────────────────────────────────

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


# ── Entity extraction ──────────────────────────────────────────────────────────

def extract_entities(text: str, extra_safe: Set[str]) -> Dict[str, Set[str]]:
    """Return {category: set_of_candidate_values} found in text."""
    found: Dict[str, Set[str]] = defaultdict(set)

    # Emails first — extract their domains so FQDN pass can skip them
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

    # FQDNs — skip if already captured as email domain or safelisted
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

    # UNC paths
    for m in _UNC_RE.finditer(text):
        found["unc_paths"].add(m.group(1))

    # Windows absolute paths — skip common system paths
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
    html = path.read_text(encoding="utf-8", errors="replace")
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


# ── Token generators ───────────────────────────────────────────────────────────

def _token_email(addr: str, mapping: Dict) -> str:
    n = _next_counter(mapping, "email")
    local = addr.split("@")[0]
    if "-" in local or "_" in local:
        hint = re.sub(r"[^a-z]", "", local.split("-")[0].split("_")[0].lower())[:6]
        return f"{hint or 'team'}{n:03d}@example.com"
    return f"user{n:03d}@example.com"


def _token_ip(addr: str, mapping: Dict) -> str:
    parts = addr.split(".")
    if len(parts) == 4:
        try:
            last = int(parts[3])
            # Avoid duplicate last-octet collisions by checking existing values
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


# ── Subcommand: discover ───────────────────────────────────────────────────────

def cmd_discover(args: argparse.Namespace) -> None:
    extra_safe = load_extra_safelist(args.safelist)
    mapping = load_mapping(args.map)

    html_files = sorted(args.root.rglob("*.html"))
    if not html_files:
        print(f"No .html files found under {args.root}")
        return

    new_counts: Dict[str, int] = defaultdict(int)
    flagged_lines: List[str] = []

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        entities = extract_from_html(html_path, extra_safe)
        raw = html_path.read_text(encoding="utf-8", errors="replace")

        for email in entities.get("emails", set()):
            if email not in mapping["emails"]:
                mapping["emails"][email] = _token_email(email, mapping)
                new_counts["emails"] += 1
            # Flag surrounding lines for manual credential review
            for line in raw.splitlines():
                if email in line and len(line.strip()) > len(email) + 4:
                    flagged_lines.append(f"  [{rel}]  {line.strip()[:140]}")

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

    print(f"\nScanned {len(html_files)} HTML file(s)")
    print("New candidates added:")
    for k in ("emails", "credentials", "ips", "hostnames", "tickets",
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


# ── Subcommand: apply ──────────────────────────────────────────────────────────

def _apply_text(text: str, replacements: Dict[str, str]) -> Tuple[str, int]:
    """Replace all mapping keys (longest first) in text. Returns (result, count)."""
    count = 0
    for original in sorted(replacements, key=len, reverse=True):
        if original in text:
            text = text.replace(original, replacements[original])
            count += 1
    return text, count


def _sanitize_html(path: Path, replacements: Dict[str, str]) -> Tuple[str, int]:
    html = path.read_text(encoding="utf-8", errors="replace")
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

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        out_path = args.output / rel
        sanitized, count = _sanitize_html(html_path, replacements)
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
        f"sanitize_notes.py — apply log\n"
        f"Run:    {datetime.now().isoformat()}\n"
        f"Source: {args.root}\n"
        f"Output: {args.output}\n"
        f"Total substitutions: {total_subs}\n\n"
        f"{'Subs':>5}  File\n"
        f"{'─'*5}  {'─'*70}\n"
    ) + "\n".join(log_lines)

    if not args.dry_run:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "substitution_log.txt").write_text(log_content, encoding="utf-8")
        print(f"Sanitized {len(html_files)} file(s) → {args.output}")
        print(f"Total substitutions: {total_subs}")
    else:
        print(f"[dry-run] {len(html_files)} file(s), {total_subs} substitution(s)")
        for line in log_lines[:25]:
            print(f"  {line}")


# ── Subcommand: validate ───────────────────────────────────────────────────────

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
        for category, values in entities.items():
            for val in values:
                if val not in known_safe_tokens:
                    issues.append(f"  [{category:<14}] {val!r:<50}  {rel}")

    if issues:
        print(f"VALIDATE FAILED — {len(issues)} residual sensitive match(es):\n")
        for issue in sorted(issues)[:100]:
            print(issue)
        if len(issues) > 100:
            print(f"\n  ... and {len(issues) - 100} more")
        sys.exit(1)
    else:
        print(f"VALIDATE PASSED — {len(html_files)} file(s) clean")


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
```


## License: unknown
https://github.com/tinabuzanis/machine-translation/blob/347a1eec9dab94f6817df89a387f50901d14bcd5/trim_models_and_tok.py

```
Good — confirmed key patterns: `nick.bennett@insight.com - Solana001!!!` (email+credential), `[msdp-16.0.1] jd1ltlanbufwm01 >` (shell prompt hostname), and training URLs with embedded user IDs. Both files are designed around these.

---

## File 1: `sanitize-framework.txt` (full rewrite)

```
==============================================================================
  NOTES SANITIZATION FRAMEWORK  v1.1
  Purpose : Obfuscate sensitive identifiers in exported HTML notes prior to
            publication in a public or broadly-shared knowledge base.
  Updated : 2026-04-24
==============================================================================

  CONTENTS
  ────────
  Section 1  Scope and Exclusions
  Section 2  Sanitization Rules
    2.1  Entity rules and replacement tokens
    2.2  Regex pattern catalog
    2.3  Canonical mapping strategy
  Section 3  Local Script Reference  (sanitize_notes.py)
  Section 4  Image and Alt-Text Handling
  Section 5  HTML Attribute Decision Table
  Section 6  Validation Checklist
  Section 7  Agent Instructions  (Copilot Studio / LLM system prompt)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1  SCOPE AND EXCLUSIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1.1  Purpose
  These notes cover enterprise backup/recovery products (Avamar, Veeam,
  NetBackup, Cohesity, Rubrik, CommVault, NetApp, Quantum, Spectra Logic)
  and cloud platforms (AWS, Azure, GCP).  Most notes are training, lab, and
  field-support references.  Sanitization removes personal and customer
  identifiers while keeping all technical detail intact.

1.2  What MUST be obfuscated
  - Real names of employees, customers, or contacts
  - Internal or customer email addresses  (including work addresses such as
    name@insight.com)
  - Credentials — passwords, API keys, tokens, secrets — appearing anywhere
    in text, including "email - password" patterns from lab notes
  - Internal hostnames and FQDNs (customer/org-specific)
  - Short hostnames appearing in shell prompts  (e.g., [version] hostname >)
  - Real IP addresses (internal and public)
  - Internal ticket, case, or change record numbers  (INC, CHG, REQ, SR …)
  - Internal UNC paths and Windows absolute paths that expose org structure
  - Company and organisation names (customers, employers)
  - Specific office or city names tied to internal infrastructure
  - Training or lab portal URLs that contain a user-specific ID in the path
    (e.g., /User/CurrentTraining/2517591)

1.3  What MUST be preserved  (safelist)
  Vendor product names and their official domains:
    dell.com  emc.com  dellemc.com
    veritas.com
    veeam.com
    cohesity.com
    rubrik.com
    commvault.com
    netapp.com
    quantum.com
    spectralogic.com
    bravais.com                       (Dell training platform)
    learnondemand.net                 (Veeam/LogicalOps training — base domain
                                       is safe; only the user-ID path segment
                                       needs removal)
    microsoft.com  microsoftonline.com  azure.com  graph.microsoft.com
    google.com  googleapis.com
    amazon.com  amazonaws.com

  Technical content that must not be altered:
    - Protocol names  (HTTP, HTTPS, RDP, NFS, SMB, iSCSI …)
    - Port numbers
    - CLI commands and their flags / options
    - Error codes and log severity levels
    - RFC-standard IP ranges already used as output tokens:
        192.0.2.0/24,  198.51.100.0/24,  203.0.113.0/24,  2001:db8::/32
    - Product version strings
    - Configuration key names  (but NOT their values when those values
      contain PII or credentials)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2  SANITIZATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2.1  Entity Rules and Replacement Tokens

  ENTITY TYPE              TOKEN FORMAT              NOTES
  ─────────────────────── ─────────────────────── ─────────────────────────
  Email (personal)         user001@example.com     increment per unique addr
  Email (role/team)        netops@example.com      preserve functional hint
  Credential / password    [REDACTED]              always full replacement;
                                                   never preserve any part
  IPv4 private             10.10.1.N               N = last octet of original
  IPv4 public              198.51.100.N            RFC 5737 range
  IPv6                     2001:db8::N             RFC 3849 range
  FQDN (with dots)         host001.corp.local      preserve role prefix if
                                                   clear (db, app, web …)
  Short hostname           host001                 hostnames without a domain
  Shell-prompt hostname    host001                 from [ver] hostname > or
                                                   [user@hostname dir]#
  Domain\user              CORP\user001            keep CORP\ prefix
  Service account          svc001                  keep svc_ prefix style
  Person name (standalone) PERSON_001
  Ticket INC               INC000001               zero-padded 6 digits
  Ticket CHG               CHG000001
  Ticket REQ/SR/RITM       REQ000001  etc.
  UNC path                 \\fileserver001\share001 replace server + share
  Windows absolute path    C:\data\project001\...  replace non-system folders
  API token in URL query   [REDACTED]              strip entire key=value pair
  Training URL with user   strip the user-ID path  keep base domain + course
  Customer / org name      CustomerA, CustomerB    sequential labels
  City / office            Region-Office-01        e.g., Midwest-Office-01

2.2  Regex Pattern Catalog

  Apply safelist exclusion BEFORE flagging any FQDN or IP match.
  Run email pattern BEFORE FQDN to avoid double-flagging the domain part.

  EMAIL
    \b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b

  CREDENTIAL after email  (lab-note pattern: "email@domain - Password123!")
    @[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\s+[\-\u2013\u2014:=]\s+(\S{6,})

  CREDENTIAL keywords
    (?:password|passwd|pwd|pass|secret|key|token|cred)s?\s*[:\-=]\s*(\S+)

  IPv4
    \b((?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}
       (?:25[0-5]|2[0-4]\d|[01]?\d\d?))\b

  IPv6  (abbreviated forms)
    \b((?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4})\b

  FQDN  (2+ dots; run safelist filter after match)
    \b((?:[a-zA-Z0-9\-]+\.){2,}[a-zA-Z]{2,})\b

  SHORT HOSTNAME in shell prompt — [version] hostname > command
    \[[^\]]{1,40}\]\s+([a-zA-Z0-9][a-zA-Z0-9\-]{4,})\s+[>#$]

  SHORT HOSTNAME in shell prompt — [user@hostname dir]# or $
    \[(?:[a-zA-Z0-9_\-]+@)([a-zA-Z0-9][a-zA-Z0-9\-]{3,})\s

  WINDOWS UNC PATH
    (\\\\[a-zA-Z0-9\-]+(?:\\[^\s<>"]+)+)

  WINDOWS ABSOLUTE PATH
    ([A-Za-z]:\\(?:[^\\\s<>"]+\\)*[^\\\s<>"]+)

  TICKET NUMBERS
    \b((?:INC|CHG|REQ|SR|RITM|PRB|TASK)\d{5,10})\b

  AUTH TOKENS / CREDENTIALS IN URL QUERY STRINGS
    [?&]((?:token|key|sig|auth|secret|session|api[_\-]?key|
          password|passwd|pwd)=[^\s&"'<>]+)

  DOMAIN\USERNAME
    \b([A-Z][A-Z0-9]{1,14}\\[a-zA-Z0-9_\-]+)\b

  TRAINING URL WITH USER ID  (logicaloperations.learnondemand.net pattern)
    (https?://[^\s"'<>]+/(?:User|user)/[^\s/"'<>]+/\d{4,})

2.3  Canonical Mapping Strategy

  Rule: one original value always maps to the same token across ALL files.
  The mapping is built once in mapping.json and reused every run.
  New candidates are appended on re-discovery; existing entries are never
  overwritten automatically.

  mapping.json structure:
  {
    "_metadata": {
      "version": 1,
      "last_discover": "2026-04-24T...",
      "counters": { "email": 2, "host": 4, "ip": 3, "ticket_INC": 1 }
    },
    "emails":       { "nick.bennett@insight.com": "user001@example.com" },
    "credentials":  { "Solana001!!!": "[REDACTED]" },
    "ips":          { "10.45.22.100": "10.10.1.100" },
    "hostnames":    { "jd1ltlanbufwm01": "host001.corp.local" },
    "tickets":      { "INC0438984": "INC000001" },
    "domain_users": { "CORP\\jsmith": "CORP\\user001" },
    "unc_paths":    {},
    "win_paths":    {},
    "auth_tokens":  {}
  }

  Workflow:
    1. Run:  python sanitize_notes.py discover --root ./Bennett-Notes
                                               --map mapping.json
    2. Human reviews mapping.json — confirm tokens, adjust where needed,
       and manually add credentials found in flagged-lines output.
    3. Run:  python sanitize_notes.py apply --root ./Bennett-Notes
                                            --map mapping.json
                                            --output ./Sanitized-Notes
    4. Run:  python sanitize_notes.py validate --root ./Sanitized-Notes
                                               --map mapping.json
    5. Keep mapping.json in a PRIVATE location.
       Never commit it alongside the published notes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3  LOCAL SCRIPT REFERENCE  (sanitize_notes.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Requires:  Python 3.9+,  beautifulsoup4  (pip install beautifulsoup4)

  Subcommands
  ───────────
  discover    Scan all .html files under --root; populate --map with
              candidate entities and auto-generated replacement tokens.
              New candidates are appended on re-runs; existing entries
              are never overwritten.
              Emits a "flagged lines" list of lines containing emails so
              adjacent credentials can be manually added to mapping.json.

  apply       Apply the reviewed --map to all .html files and write
              sanitized copies to --output (mirrors source folder structure).
              Non-HTML assets are copied unchanged when --copy-assets is set.
              Produces substitution_log.txt in the output root.

  validate    Re-scan all .html files in --root against the same regex
              patterns.  Known-safe replacement tokens and safelisted domains
              are excluded.  Exits non-zero if residual sensitive matches
              remain.

  Common options
  ──────────────
  --root          Root folder to scan (default: ./Bennett-Notes)
  --map           Path to mapping.json
  --output        Output folder for sanitized files  (apply only)
  --safelist      Optional file of extra safe domains/terms, one per line
  --dry-run       Show planned changes without writing any files
  --copy-assets   Copy non-.html files (images, .bin) to output dir

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4  IMAGE AND ALT-TEXT HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OneNote exports images as .bin files (binary PNG/JPEG) alongside HTML.
  The alt attribute contains OCR-extracted text from the screenshot.

4.1  Alt text
  - Treat as a first-class text node; apply all regex patterns.
  - If alt text contains sensitive data that cannot be cleanly replaced
    in context, substitute the entire alt value with: [screenshot]

4.2  Binary image files
  - The script copies them unchanged to the output directory.
  - Pixel-level text in screenshots is NOT auto-redacted by the script.
  - Flag for manual review: any image whose alt text triggered a regex match.

4.3  Manual review checklist for images
  - Does the screenshot show a hostname, IP, email, or credential?
  - If yes: crop/blur the sensitive region using an image editor, then
    replace the .bin file in the output directory.
  - Re-run validate after manual image edits.

4.4  EXIF / metadata
  - Strip EXIF metadata from any standalone image files before publishing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5  HTML ATTRIBUTE DECISION TABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Attribute                Action
  ─────────────────────── ────────────────────────────────────────────────────
  alt                      SCAN — apply all patterns; full redact if needed
  title  (element)         SCAN — apply all patterns
  href                     SCAN if absolute URL and domain not on safelist;
                           also strip user-ID segments from training URLs
  src  (img)               SKIP if relative path;  SCAN if absolute URL
  data-fullres-src         SKIP if relative path;  SCAN if absolute URL
  data-src-type            SKIP — MIME type only  (e.g., image/png)
  data-fullres-src-type    SKIP — MIME type only
  data-absolute-enabled    SKIP — layout flag
  style  (inline)          SKIP — layout/formatting only
  width, height            SKIP — numeric dimensions
  lang                     SKIP
  <meta name="created">    PRESERVE — ISO timestamp, not sensitive
  <meta charset>           SKIP
  HTML comments            SCAN — remove entire comment if match found
  <title>  (page)          SCAN — note name is usually a product/topic,
                           safe in practice but confirm before skipping

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6  VALIDATION CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Run the 'validate' subcommand, then confirm all items below pass:

  [ ] No email matches outside example.com / example.net / example.org
  [ ] No IPv4 addresses outside 10.10.x.x and RFC 5737 ranges
  [ ] No IPv6 addresses outside 2001:db8::/32
  [ ] No FQDNs with non-safelisted domains
  [ ] No real ticket numbers  (INC/CHG/REQ/SR/RITM/PRB)
  [ ] No credentials, tokens, or password strings
  [ ] No Domain\user patterns with real domain names
  [ ] No UNC paths with real server names
  [ ] No company or customer name strings
  [ ] No training URLs containing user-specific ID path segments
  [ ] Alt text reviewed for images that triggered regex matches
  [ ] Flagged-lines output reviewed for credential patterns
  [ ] mapping.json stored in private location, not with published files
  [ ] Substitution log reviewed; zero-replacement files investigated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7  AGENT INSTRUCTIONS  (Copilot Studio / LLM system prompt)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Paste everything below this line as the agent's Instructions / system prompt]

You are a Sanitization Assistant for technical notes and logs that will be
republished in a public or broadly shared knowledge base.

Your primary goal is to remove or obfuscate any sensitive information while
preserving the technical detail, structure, and usefulness of the content.

GENERAL BEHAVIOR
  - Do not introduce any real organisations, brands, or identifiable data.
  - Preserve the structure and formatting of the input (HTML, Markdown, or
    plain text), only changing values that reveal sensitive information.
  - Keep timestamps, error codes, configuration option names, command syntax,
    and protocol details unchanged unless they contain sensitive identifiers.
  - Apply replacements consistently: the same original value must always
    produce the same replacement token within a session.
  - Before processing, identify the entity type of each candidate and apply
    the appropriate rule below.

SAFELIST — do not modify anything from these domains or vendors:
  dell.com, emc.com, dellemc.com, veritas.com, veeam.com, cohesity.com,
  rubrik.com, commvault.com, netapp.com, quantum.com, spectralogic.com,
  bravais.com, learnondemand.net, logicaloperations.learnondemand.net,
  microsoft.com, microsoftonline.com, azure.com, graph.microsoft.com,
  google.com, googleapis.com, amazon.com, amazonaws.com,
  example.com, example.net, example.org, example.test, corp.local

SANITIZATION RULES

  1. IP ADDRESSES
     - All real IP addresses are potentially sensitive.
     - Private IPv4: map to 10.10.1.N preserving last octet.
       Example: 10.45.22.100 → 10.10.1.100
     - Public IPv4: map to RFC 5737 range 198.51.100.N.
       Example: 52.183.45.10 → 198.51.100.10
     - IPv6: map to 2001:db8:: prefix.
       Example: 2603:1020:200::5 → 2001:db8:200::5

  2. HOSTNAMES AND DOMAINS
     - Replace real internal hostnames and FQDNs with generic equivalents,
       preserving the role/tier where identifiable:
         prod-db01.corp.com      → db01.corp.local
         backup-media01.acme.com → media01.corp.local
     - For short hostnames in shell prompts — both patterns:
         [msdp-16.0.1] jd1ltlanbufwm01 > command  →  [msdp-16.0.1] host001 > command
         [root@jd1ltlanbuflx01 mnt]#               →  [root@host002 mnt]#
     - Use placeholder domains: example.com, corp.local, lab.example.com.
     - Never modify hostnames/FQDNs on the safelist.

  3. EMAIL ADDRESSES AND USERNAMES
     - Individual: jane.doe@company.com → user001@example.com
     - Role/team:  network-ops@company.com → netops@example.com
     - Usernames:  DOMAIN\jsmith → CORP\user001
     - Service accounts: svc_backup → svc001
     - Maintain distinction between user, admin, and service account types.

  4. CREDENTIALS AND TOKENS
     - Replace ALL passwords, API keys, tokens, and secrets with [REDACTED].
     - Remove auth tokens from URL query strings entirely.
     - Watch specifically for the lab-note pattern where an email is followed
       by a separator and a password on the same line:
         nick.bennett@insight.com - Solana001!!!
         → user001@example.com - [REDACTED]
     - Any string that follows "password:", "passwd:", "pwd:", "secret:",
       "key:", "token:" (case-insensitive) must be replaced with [REDACTED].

  5. COMPANY NAMES, ORGANISATIONS, AND LOCATIONS
     - Replace customer/client org names: ClientCorp → CustomerA
     - Replace employer or internal org identifiers similarly.
     - Replace specific offices/cities: Minneapolis Office → Midwest-Office-01

  6. TICKET AND CASE NUMBERS
     - INC0438984 → INC000001  (zero-padded 6 digits)
     - CHG987654  → CHG000001
     - Preserve the prefix (INC, CHG, REQ, SR, RITM, PRB, TASK).

  7. TRAINING URLS WITH USER-SPECIFIC IDS
     - Safelisted base domain is preserved; only the user-ID segment is removed.
       https://logicaloperations.learnondemand.net/User/CurrentTraining/2517591
       → https://logicaloperations.learnondemand.net/  [user-ID removed]

  8. FILE PATHS
     - UNC:      \\corp-fs01\Finance\Payroll → \\fileserver001\dept001\data001
     - Windows:  C:\Users\jsmith\Projects\ClientX
                 → C:\Users\user001\Projects\project001

  9. HTML FORMATTING RULES
     - Preserve all HTML tags and structural attributes (style, width, height,
       data-absolute-enabled, data-src-type, data-fullres-src-type, lang).
     - Sanitize text nodes and these attributes: alt, title, href (non-safelisted
       absolute URLs).
     - For img alt text: apply all rules; if the alt text contains sensitive
       content that cannot be cleanly replaced in context, substitute the
       entire alt value with: [screenshot]
     - Preserve relative src/href paths (they reference local image files).
     - Remove HTML comments if they contain sensitive identifiers.

  10. WHAT NOT TO DO
      - Do not redact everything; only obfuscate identifiable/sensitive items.
      - Do not change protocols, ports, HTTP verbs, config key names, error
        codes, log severity levels, product version numbers, or CLI syntax.
      - Do not invent real-world company names as replacements.
      - Do not alter the note's technical meaning or remove educational content.
```

---

## File 2: `sanitize_notes.py`

Save alongside the other scripts in `e:\VSCode-Root\onenote\`.

```python
#!/usr/bin/env python3
"""
sanitize_notes.py — Discover, replace, and validate sensitive entities in
exported HTML notes before public knowledge-base publication.

Requires:  pip install beautifulsoup4

Workflow:
  1. python sanitize_notes.py discover --root ./Bennett-Notes --map mapping.json
  2. Review / edit mapping.json — adjust tokens, add credentials from flagged lines.
  3. python sanitize_notes.py apply    --root ./Bennett-Notes \\
                                       --map mapping.json \\
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

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_ROOT   = Path(r"E:\VSCode-Root\onenote\Bennett-Notes")
DEFAULT_MAP    = Path(r"E:\VSCode-Root\onenote\mapping.json")
DEFAULT_OUTPUT = Path(r"E:\VSCode-Root\onenote\Sanitized-Notes")

# ── Safelist ──────────────────────────────────────────────────────────────────
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
    # Safe output-token domains — never flag as sensitive
    "example.com", "example.net", "example.org", "example.test",
    "corp.local",
}

# RFC 5737 / RFC 3849 documentation ranges used as output tokens
_SAFE_IPV4_PREFIXES: Tuple[str, ...] = (
    "192.0.2.", "198.51.100.", "203.0.113.", "10.10.",
)
_SAFE_IPV6_PREFIX = "2001:db8"

# ── Regex catalog ─────────────────────────────────────────────────────────────
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
# Training URL with user-ID path segment
_TRAINING_URL_RE = re.compile(
    r"(https?://[^\s\"'<>]+/(?:User|user)/[^\s/\"'<>]+/\d{4,}[^\s\"'<>]*)"
)

# HTML attributes to scan as plain text
_TEXT_ATTRS = {"alt", "title"}
# HTML attributes to scan only when value is an absolute URL
_URL_ATTRS = {"href", "src", "data-fullres-src"}

# Windows system paths that are not sensitive
_SAFE_WIN_PREFIXES = (
    "c:\\windows", "c:\\program files", "c:\\program files (x86)",
    "/usr/", "/etc/", "/var/", "/opt/", "/tmp/",
)


# ── Mapping I/O ───────────────────────────────────────────────────────────────

def _empty_mapping() -> Dict:
    return {
        "_metadata": {"version": 1, "counters": {}},
        "emails":       {},
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
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return _empty_mapping()


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
        "emails", "credentials", "ips", "hostnames", "tickets",
        "domain_users", "unc_paths", "win_paths", "auth_tokens",
    ):
        for k, v in mapping.get(section, {}).items():
            if k and v:
                result[k] = v
    return result


# ── Safelist helpers ───────────────────────────────────────────────────────────

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


# ── Entity extraction ──────────────────────────────────────────────────────────

def extract_entities(text: str, extra_safe: Set[str]) -> Dict[str, Set[str]]:
    """Return {category: set_of_candidate_values} found in text."""
    found: Dict[str, Set[str]] = defaultdict(set)

    # Emails first — extract their domains so FQDN pass can skip them
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

    # FQDNs — skip if already captured as email domain or safelisted
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

    # UNC paths
    for m in _UNC_RE.finditer(text):
        found["unc_paths"].add(m.group(1))

    # Windows absolute paths — skip common system paths
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
    html = path.read_text(encoding="utf-8", errors="replace")
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


# ── Token generators ───────────────────────────────────────────────────────────

def _token_email(addr: str, mapping: Dict) -> str:
    n = _next_counter(mapping, "email")
    local = addr.split("@")[0]
    if "-" in local or "_" in local:
        hint = re.sub(r"[^a-z]", "", local.split("-")[0].split("_")[0].lower())[:6]
        return f"{hint or 'team'}{n:03d}@example.com"
    return f"user{n:03d}@example.com"


def _token_ip(addr: str, mapping: Dict) -> str:
    parts = addr.split(".")
    if len(parts) == 4:
        try:
            last = int(parts[3])
            # Avoid duplicate last-octet collisions by checking existing values
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


# ── Subcommand: discover ───────────────────────────────────────────────────────

def cmd_discover(args: argparse.Namespace) -> None:
    extra_safe = load_extra_safelist(args.safelist)
    mapping = load_mapping(args.map)

    html_files = sorted(args.root.rglob("*.html"))
    if not html_files:
        print(f"No .html files found under {args.root}")
        return

    new_counts: Dict[str, int] = defaultdict(int)
    flagged_lines: List[str] = []

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        entities = extract_from_html(html_path, extra_safe)
        raw = html_path.read_text(encoding="utf-8", errors="replace")

        for email in entities.get("emails", set()):
            if email not in mapping["emails"]:
                mapping["emails"][email] = _token_email(email, mapping)
                new_counts["emails"] += 1
            # Flag surrounding lines for manual credential review
            for line in raw.splitlines():
                if email in line and len(line.strip()) > len(email) + 4:
                    flagged_lines.append(f"  [{rel}]  {line.strip()[:140]}")

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

    print(f"\nScanned {len(html_files)} HTML file(s)")
    print("New candidates added:")
    for k in ("emails", "credentials", "ips", "hostnames", "tickets",
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


# ── Subcommand: apply ──────────────────────────────────────────────────────────

def _apply_text(text: str, replacements: Dict[str, str]) -> Tuple[str, int]:
    """Replace all mapping keys (longest first) in text. Returns (result, count)."""
    count = 0
    for original in sorted(replacements, key=len, reverse=True):
        if original in text:
            text = text.replace(original, replacements[original])
            count += 1
    return text, count


def _sanitize_html(path: Path, replacements: Dict[str, str]) -> Tuple[str, int]:
    html = path.read_text(encoding="utf-8", errors="replace")
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

    for html_path in html_files:
        rel = html_path.relative_to(args.root)
        out_path = args.output / rel
        sanitized, count = _sanitize_html(html_path, replacements)
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
        f"sanitize_notes.py — apply log\n"
        f"Run:    {datetime.now().isoformat()}\n"
        f"Source: {args.root}\n"
        f"Output: {args.output}\n"
        f"Total substitutions: {total_subs}\n\n"
        f"{'Subs':>5}  File\n"
        f"{'─'*5}  {'─'*70}\n"
    ) + "\n".join(log_lines)

    if not args.dry_run:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "substitution_log.txt").write_text(log_content, encoding="utf-8")
        print(f"Sanitized {len(html_files)} file(s) → {args.output}")
        print(f"Total substitutions: {total_subs}")
    else:
        print(f"[dry-run] {len(html_files)} file(s), {total_subs} substitution(s)")
        for line in log_lines[:25]:
            print(f"  {line}")


# ── Subcommand: validate ───────────────────────────────────────────────────────

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
        for category, values in entities.items():
            for val in values:
                if val not in known_safe_tokens:
                    issues.append(f"  [{category:<14}] {val!r:<50}  {rel}")

    if issues:
        print(f"VALIDATE FAILED — {len(issues)} residual sensitive match(es):\n")
        for issue in sorted(issues)[:100]:
            print(issue)
        if len(issues) > 100:
            print(f"\n  ... and {len(issues) - 100} more")
        sys.exit(1)
    else:
        print(f"VALIDATE PASSED — {len(html_files)} file(s) clean")


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
```


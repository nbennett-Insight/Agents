#!/usr/bin/env python3
"""
Export OneNote page details (HTML) from Microsoft Graph using page IDs from a manifest.
This script writes page.html files into the notebook/section/page folder structure.
Image URLs in HTML are preserved as Graph img src links for later processing.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

try:
    import msal
except ImportError:  # pragma: no cover
    msal = None

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
DEFAULT_EXPORT_ROOT = Path(r"E:\VSCode-Root\onenote")
DEFAULT_MANIFEST = Path(r"E:\VSCode-Root\onenote\onenote_structure.json")
DEFAULT_TENANT = "organizations"
CLIENT_ID = "04f0c124-f2bc-4f59-9e9b-3d0a3f9c17e3"
# Common Microsoft first-party public client used by Azure CLI.
FALLBACK_CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
SCOPES = ["Notes.Read", "User.Read"]


def clean_name_for_path(name: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|]', "_", name)
    clean = clean.strip().rstrip(".")
    return clean if clean else "Untitled"


def next_named_child(
    parent: Path,
    raw_name: str,
    seen_counts: Dict[Tuple[Path, str], int],
) -> Path:
    base_name = clean_name_for_path(raw_name)
    key = (parent, base_name)
    occurrence = seen_counts.get(key, 0) + 1
    seen_counts[key] = occurrence

    if occurrence == 1:
        return parent / base_name

    return parent / f"{base_name} ({occurrence})"


def get_json(url: str, headers: Dict[str, str]) -> Dict:
    req = Request(url, method="GET")
    for key, value in headers.items():
        req.add_header(key, value)

    with urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_text(url: str, headers: Dict[str, str]) -> str:
    req = Request(url, method="GET")
    for key, value in headers.items():
        req.add_header(key, value)

    with urlopen(req, timeout=90) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def try_device_flow(client_id: str, tenant_id: str) -> Dict:
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.PublicClientApplication(client_id, authority=authority)

    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and result.get("access_token"):
            return result

    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        return flow if isinstance(flow, dict) else {}

    print("\n== Device login ==")
    print(f"Tenant: {tenant_id}")
    print(f"Go to: {flow['verification_uri']}")
    print(f"Enter code: {flow['user_code']}\n")
    return app.acquire_token_by_device_flow(flow)


def get_graph_access_token(client_id: str, tenant_id: str) -> str:
    if msal is None:
        raise RuntimeError("Missing dependency: msal. Install with: python -m pip install msal")

    attempts = [(client_id, tenant_id)]
    if tenant_id.lower() != "organizations":
        attempts.append((client_id, "organizations"))
    if client_id != FALLBACK_CLIENT_ID:
        attempts.append((FALLBACK_CLIENT_ID, tenant_id))
        if tenant_id.lower() != "organizations":
            attempts.append((FALLBACK_CLIENT_ID, "organizations"))

    seen = set()
    last_error = "unknown_error"
    last_description = "No details provided."

    for attempt_client_id, attempt_tenant in attempts:
        key = (attempt_client_id, attempt_tenant)
        if key in seen:
            continue
        seen.add(key)

        if key != (client_id, tenant_id):
            print(
                "Retrying device flow with "
                f"client {attempt_client_id} and tenant {attempt_tenant}..."
            )

        result = try_device_flow(client_id=attempt_client_id, tenant_id=attempt_tenant)
        access_token = result.get("access_token") if isinstance(result, dict) else None
        if access_token:
            return access_token

        last_error = result.get("error") if isinstance(result, dict) else "unknown_error"
        last_description = (
            result.get("error_description") if isinstance(result, dict) else "No details provided."
        )

    raise RuntimeError(f"Token request failed: {last_error} | {last_description}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export OneNote page HTML details from Graph into existing folder structure."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to manifest JSON with notebook/sections/pages (title + id).",
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=DEFAULT_EXPORT_ROOT,
        help="Root output folder where notebook folders exist.",
    )
    parser.add_argument(
        "--tenant",
        default=DEFAULT_TENANT,
        help="Tenant ID or domain (for example: organizations, <tenant-guid>, <tenant>.onmicrosoft.com).",
    )
    parser.add_argument(
        "--client-id",
        default=CLIENT_ID,
        help="App client ID for device auth. Use your own app registration if your tenant blocks the default.",
    )
    parser.add_argument(
        "--access-token",
        default=None,
        help="Optional pre-acquired Graph bearer token. If provided, device login is skipped.",
    )
    parser.add_argument(
        "--access-token-file",
        type=Path,
        default=None,
        help="Path to a text file containing a Graph bearer token (single line).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing page.html files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.manifest.exists():
        raise RuntimeError(f"Manifest file not found: {args.manifest}")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    notebook_name = manifest.get("notebook", "Untitled")
    sections: List[Dict] = manifest.get("sections", [])
    if not isinstance(sections, list):
        raise RuntimeError("Manifest error: 'sections' must be a list.")

    print("Signing in to Microsoft Graph...")
    access_token: Optional[str] = args.access_token
    if not access_token and args.access_token_file:
        if not args.access_token_file.exists():
            raise RuntimeError(f"Access token file not found: {args.access_token_file}")
        access_token = args.access_token_file.read_text(encoding="utf-8").strip()

    if not access_token:
        access_token = get_graph_access_token(args.client_id, args.tenant)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "text/html",
    }

    notebook_folder = args.export_root / clean_name_for_path(notebook_name)
    notebook_folder.mkdir(parents=True, exist_ok=True)
    section_counts: Dict[Tuple[Path, str], int] = {}
    page_counts: Dict[Tuple[Path, str], int] = {}

    exported = 0
    skipped_existing = 0
    skipped_missing_id = 0

    for section in sections:
        section_name = section.get("displayName", "Untitled")
        pages = section.get("pages", [])
        if not isinstance(pages, list):
            continue

        section_folder = next_named_child(notebook_folder, section_name, section_counts)
        section_folder.mkdir(parents=True, exist_ok=True)

        print(f"\nSection: {section_name} ({len(pages)} pages)")

        for page in pages:
            title = page.get("title") or "Untitled"
            page_id = page.get("id")
            if not page_id:
                skipped_missing_id += 1
                print(f"  Skip (missing id): {title}")
                continue

            page_folder = next_named_child(section_folder, title, page_counts)
            page_folder.mkdir(parents=True, exist_ok=True)
            html_path = page_folder / "page.html"

            if html_path.exists() and not args.overwrite:
                skipped_existing += 1
                print(f"  Skip (exists): {title}")
                continue

            encoded_page_id = quote(str(page_id), safe="")
            page_content_url = f"{GRAPH_BASE}/me/onenote/pages/{encoded_page_id}/content"

            print(f"  Export HTML: {title}")
            html = get_text(page_content_url, headers)
            html_path.write_text(html, encoding="utf-8")
            exported += 1

    print("\nDone.")
    print(f"Exported page.html files: {exported}")
    print(f"Skipped existing page.html: {skipped_existing}")
    print(f"Skipped missing page IDs: {skipped_missing_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HTTPError, URLError) as exc:
        print(f"Network/API error: {exc}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("Interrupted by user.")
        raise SystemExit(130)

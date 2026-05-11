#!/usr/bin/env python3
"""
Build a local OneNote folder tree (Notebook -> Sections -> Pages) using Microsoft Graph.
Uses device-code auth so it works from a terminal without browser-integrated auth libraries.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import msal
except ImportError:  # pragma: no cover
    msal = None

EXPORT_ROOT = Path(r"E:\VSCode-Root\onenote")
TARGET_NOTEBOOK_NAME = "Bennett-Notes"
TENANT_ID = "organizations"  # Replace with tenant GUID if needed.
CLIENT_ID = "04f0c124-f2bc-4f59-9e9b-3d0a3f9c17e3"  # Public MS Graph client ID.
SCOPES = ["Notes.Read", "User.Read"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def clean_name_for_path(name: str) -> str:
    """Make a safe Windows folder name."""
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

    with urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_graph_access_token(client_id: str, tenant_id: str) -> str:
    if msal is None:
        raise RuntimeError(
            "Missing dependency: msal. Install it with 'python -m pip install msal'."
        )

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.PublicClientApplication(client_id, authority=authority)

    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            error = flow.get("error", "unknown_error") if isinstance(flow, dict) else "unknown_error"
            description = (
                flow.get("error_description", "No details provided.")
                if isinstance(flow, dict)
                else "No details provided."
            )
            raise RuntimeError(f"Failed to start device flow: {error} | {description}")

        print("\n== Device login ==")
        print(f"Go to: {flow['verification_uri']}")
        print(f"Enter code: {flow['user_code']}\n")
        result = app.acquire_token_by_device_flow(flow)

    access_token = result.get("access_token") if isinstance(result, dict) else None
    if access_token:
        return access_token

    error = result.get("error") if isinstance(result, dict) else "unknown_error"
    description = (
        result.get("error_description") if isinstance(result, dict) else "No details provided."
    )
    raise RuntimeError(f"Token request failed: {error} | {description}")


def paged_graph_items(url: str, headers: Dict[str, str]) -> Iterator[Dict]:
    next_url: Optional[str] = url
    while next_url:
        response = get_json(next_url, headers)
        for item in response.get("value", []):
            yield item
        next_url = response.get("@odata.nextLink")


def build_folder_tree(export_root: Path, notebook_name: str, sections: List[Dict]) -> int:
    export_root.mkdir(parents=True, exist_ok=True)
    notebook_root = export_root / clean_name_for_path(notebook_name)
    print(f"Creating notebook root folder: {notebook_root}")
    notebook_root.mkdir(parents=True, exist_ok=True)
    section_counts: Dict[Tuple[Path, str], int] = {}
    page_counts: Dict[Tuple[Path, str], int] = {}

    if not sections:
        print(f"No sections found in notebook '{notebook_name}'.")
        return 0

    for section in sections:
        section_name = section.get("displayName", "Untitled")
        section_folder = next_named_child(notebook_root, section_name, section_counts)

        print(f"\nSection: {section_name}")
        print(f"Creating folder: {section_folder}")
        section_folder.mkdir(parents=True, exist_ok=True)

        pages = section.get("pages", [])
        if not pages:
            print("  No pages in this section.")
            continue

        for page in pages:
            title = page.get("title") or "Untitled"
            page_folder = next_named_child(section_folder, title, page_counts)

            print(f"  Page: {title}")
            print(f"    Creating page folder: {page_folder}")
            page_folder.mkdir(parents=True, exist_ok=True)

    print(f"\nDone building folder structure at: {export_root}")
    return 0
def build_tree_from_graph(
    export_root: Path,
    notebook_name: str,
    tenant: str,
    access_token_override: Optional[str] = None,
) -> int:
    print("Signing in to Microsoft Graph...")
    access_token = access_token_override or get_graph_access_token(CLIENT_ID, tenant)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    print("Retrieving notebooks...")
    notebooks_url = f"{GRAPH_BASE}/me/onenote/notebooks?$top=200"
    notebooks: List[Dict] = list(paged_graph_items(notebooks_url, headers))

    target = next((n for n in notebooks if n.get("displayName") == notebook_name), None)
    if not target:
        print(f"Notebook '{notebook_name}' not found.")
        return 1

    notebook_id = target["id"]
    actual_notebook_name = target.get("displayName", "Untitled")

    print(f"Target notebook ID: {notebook_id}")
    print(f"Retrieving sections for notebook '{actual_notebook_name}'...")
    sections_url = f"{GRAPH_BASE}/me/onenote/notebooks/{notebook_id}/sections?$top=200"
    graph_sections = list(paged_graph_items(sections_url, headers))

    sections: List[Dict] = []
    for section in graph_sections:
        section_id = section["id"]
        pages_url = f"{GRAPH_BASE}/me/onenote/sections/{section_id}/pages?$top=200"
        pages = list(paged_graph_items(pages_url, headers))
        normalized_pages = [{"title": p.get("title") or "Untitled", "id": p.get("id", "")} for p in pages]
        sections.append({"displayName": section.get("displayName", "Untitled"), "pages": normalized_pages})

    return build_folder_tree(export_root=export_root, notebook_name=actual_notebook_name, sections=sections)


def build_tree_from_manifest(export_root: Path, manifest_path: Path) -> int:
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    notebook_name = manifest.get("notebook", TARGET_NOTEBOOK_NAME)
    sections = manifest.get("sections", [])
    if not isinstance(sections, list):
        raise RuntimeError("Manifest error: 'sections' must be a list.")

    print(f"Using manual manifest: {manifest_path}")
    return build_folder_tree(export_root=export_root, notebook_name=notebook_name, sections=sections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build OneNote folder tree from Microsoft Graph or a local manifest."
    )
    parser.add_argument(
        "--mode",
        choices=["graph", "manifest"],
        default="graph",
        help="Use 'graph' for Microsoft Graph live queries or 'manifest' for local JSON input.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("onenote_structure.json"),
        help="Path to manifest JSON when --mode manifest is used.",
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=EXPORT_ROOT,
        help="Output root folder for generated notebook structure.",
    )
    parser.add_argument(
        "--notebook",
        default=TARGET_NOTEBOOK_NAME,
        help="Notebook name to target in graph mode.",
    )
    parser.add_argument(
        "--tenant",
        default=TENANT_ID,
        help="Tenant ID or domain for graph mode (for example: organizations, <tenant-guid>, or <tenant>.onmicrosoft.com).",
    )
    parser.add_argument(
        "--access-token",
        default=None,
        help="Optional pre-acquired Graph bearer token. If provided, device login is skipped.",
    )
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    if args.mode == "manifest":
        return build_tree_from_manifest(export_root=args.export_root, manifest_path=args.manifest)
    return build_tree_from_graph(
        export_root=args.export_root,
        notebook_name=args.notebook,
        tenant=args.tenant,
        access_token_override=args.access_token,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HTTPError, URLError) as exc:
        print(f"Network/API error: {exc}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("Interrupted by user.")
        raise SystemExit(130)

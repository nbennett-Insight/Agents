#!/usr/bin/env python3
"""
Download Graph-hosted OneNote image resources referenced in HTML files,
save them locally under an images/ folder, and rewrite HTML URLs to local paths.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_ROOT = Path(r"E:\VSCode-Root\onenote\Bennett-Notes")
GRAPH_RESOURCE_RE = re.compile(
    r"https://graph\.microsoft\.com/v1\.0/[^\"\s>]*?/onenote/resources/[^\"\s>]*?/\$value"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Graph image resources and rewrite HTML img src references."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Root folder to scan recursively for .html files.")
    parser.add_argument("--access-token", default=None, help="Graph bearer token.")
    parser.add_argument("--access-token-file", type=Path, default=None, help="Text file containing bearer token.")
    parser.add_argument("--overwrite-images", action="store_true", help="Re-download images even if already present.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.0,
        help="Optional delay in seconds after each successful image download.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=6,
        help="Max retry attempts for transient failures like HTTP 429.",
    )
    parser.add_argument(
        "--retry-base-seconds",
        type=float,
        default=2.0,
        help="Base wait in seconds for exponential retry backoff.",
    )
    parser.add_argument(
        "--fail-log",
        type=Path,
        default=Path("image_download_failures.log"),
        help="Where to write failed image download details.",
    )
    return parser.parse_args()


def get_token(args: argparse.Namespace) -> str:
    if args.access_token:
        return args.access_token.strip()
    if args.access_token_file:
        if not args.access_token_file.exists():
            raise RuntimeError(f"Token file not found: {args.access_token_file}")
        token = args.access_token_file.read_text(encoding="utf-8").strip()
        if token:
            return token
    raise RuntimeError("Provide --access-token or --access-token-file.")


def ext_from_content_type(content_type: str) -> str:
    ct = (content_type or "").lower().split(";")[0].strip()
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tif",
        "image/svg+xml": ".svg",
    }
    return mapping.get(ct, ".bin")


def extract_resource_id(url: str) -> str:
    marker = "/onenote/resources/"
    start = url.find(marker)
    if start == -1:
        return "resource"
    remainder = url[start + len(marker):]
    resource_id = remainder.split("/$value", 1)[0]
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", resource_id)
    return safe or "resource"


def download_image(url: str, token: str) -> Tuple[bytes, str]:
    req = Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    with urlopen(req, timeout=120) as resp:
        content_type = resp.headers.get("Content-Type", "")
        return resp.read(), content_type


def download_image_with_retry(
    url: str,
    token: str,
    max_retries: int,
    retry_base_seconds: float,
) -> Tuple[bytes, str]:
    attempt = 0
    while True:
        attempt += 1
        try:
            return download_image(url, token)
        except HTTPError as exc:
            if exc.code == 429 and attempt <= max_retries:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                if retry_after and str(retry_after).isdigit():
                    wait_seconds = float(retry_after)
                else:
                    wait_seconds = retry_base_seconds * (2 ** (attempt - 1))
                print(f"Throttle 429, retry {attempt}/{max_retries} after {wait_seconds:.1f}s")
                time.sleep(wait_seconds)
                continue
            raise
        except URLError:
            if attempt <= max_retries:
                wait_seconds = retry_base_seconds * (2 ** (attempt - 1))
                print(f"Network retry {attempt}/{max_retries} after {wait_seconds:.1f}s")
                time.sleep(wait_seconds)
                continue
            raise


def main() -> int:
    args = parse_args()
    token = get_token(args)

    if not args.root.exists():
        raise RuntimeError(f"Root folder not found: {args.root}")

    html_files = list(args.root.rglob("*.html"))
    updated_files = 0
    downloaded_images = 0
    failed_downloads = 0
    failures = []
    auth_expired = False

    for html_path in html_files:
        if not html_path.is_file():
            continue

        try:
            html = html_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"Skip (unreadable): {html_path} | {exc}")
            continue
        urls = sorted(set(GRAPH_RESOURCE_RE.findall(html)))
        if not urls:
            continue

        page_folder = html_path.parent
        images_folder = page_folder / "images"
        rewrite_map: Dict[str, str] = {}

        for url in urls:
            resource_id = extract_resource_id(url)

            existing = sorted(images_folder.glob(f"{resource_id}.*")) if images_folder.exists() else []
            if existing and not args.overwrite_images:
                local_name = existing[0].name
                rewrite_map[url] = f"images/{local_name}"
                continue

            print(f"Download image: {url}")
            if args.dry_run:
                rewrite_map[url] = f"images/{resource_id}.png"
                continue

            try:
                data, content_type = download_image_with_retry(
                    url=url,
                    token=token,
                    max_retries=args.max_retries,
                    retry_base_seconds=args.retry_base_seconds,
                )
            except HTTPError as exc:
                failed_downloads += 1
                failures.append(f"{exc.code}\t{url}\t{html_path}")
                print(f"Skip (HTTP {exc.code}): {url}")
                if exc.code == 401:
                    auth_expired = True
                    print("Token appears expired/unauthorized (401). Stopping early so you can refresh token and resume.")
                    break
                continue
            except (URLError, OSError) as exc:
                failed_downloads += 1
                failures.append(f"ERROR\t{url}\t{html_path}\t{exc}")
                print(f"Skip (download error): {url} | {exc}")
                continue

            ext = ext_from_content_type(content_type)
            local_name = f"{resource_id}{ext}"
            local_path = images_folder / local_name
            images_folder.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)
            rewrite_map[url] = f"images/{local_name}"
            downloaded_images += 1
            if args.request_delay > 0:
                time.sleep(args.request_delay)

        new_html = html
        for source_url, local_rel in rewrite_map.items():
            new_html = new_html.replace(source_url, local_rel)

        if new_html != html:
            print(f"Rewrite HTML: {html_path}")
            if not args.dry_run:
                html_path.write_text(new_html, encoding="utf-8")
            updated_files += 1

        if auth_expired:
            break

    print("\nDone.")
    print(f"HTML files updated: {updated_files}")
    print(f"Images downloaded: {downloaded_images}")
    print(f"Image downloads failed: {failed_downloads}")

    if failures and not args.dry_run:
        args.fail_log.write_text("\n".join(failures) + "\n", encoding="utf-8")
        print(f"Failure log: {args.fail_log}")

    if auth_expired:
        print("Refresh your token and re-run; existing images are skipped automatically.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

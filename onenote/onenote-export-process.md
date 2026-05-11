# OneNote Export Process Runbook

## Purpose
Document the exact process used to export OneNote content from Microsoft Graph into portable local HTML plus image assets.

## Prerequisites
- Python available in workspace (.venv recommended)
- Access to notebook metadata and page lists
- Graph access token (Graph Explorer token method used successfully)
- Working folder: E:\VSCode-Root\onenote

## Inputs
- Section/page metadata manifest: onenote_structure.json
- Token file: graph_token.txt
- Export root: E:\VSCode-Root\onenote\Bennett-Notes

## Workflow

### 1. Build folder tree
Script: build_onenote_folder_tree.py
Mode used: manifest mode (manual section/page inputs)

Command:
python.exe .\build_onenote_folder_tree.py --mode manifest --manifest .\onenote_structure.json

Notes:
- Folder names are page-title based (no ID suffixes).
- Duplicate titles are handled by adding numeric suffixes.

### 2. Export page HTML content
Script: export_onenote_page_details.py

Command (token file or token arg also supported):
python.exe .\export_onenote_page_details.py --manifest .\onenote_structure.json --export-root E:\VSCode-Root\onenote --access-token-file .\graph_token.txt --overwrite

Output:
- page.html files per page folder (later renamed)
- HTML includes Graph-hosted image src URLs initially

### 3. Rename page.html to folder-name.html
Script: rename_onenote_html_files.py

Command:
python.exe .\rename_onenote_html_files.py --root .\Bennett-Notes

Result:
- page.html -> <page-folder-name>.html

### 4. Download images and rewrite HTML paths
Script: download_onenote_images_and_rewrite_html.py

Baseline command:
python.exe .\download_onenote_images_and_rewrite_html.py --root .\Bennett-Notes --access-token-file .\graph_token.txt

Throttling-safe command used:
python.exe .\download_onenote_images_and_rewrite_html.py --root .\Bennett-Notes --access-token-file .\graph_token.txt --request-delay 0.75 --max-retries 5 --retry-base-seconds 2

Behavior:
- Finds Graph resource URLs in HTML
- Downloads each resource to page-local images folder
- Rewrites HTML references to images/<resource-id>.<ext>
- Logs failed downloads to image_download_failures.log

### 5. Validate completion
Script: validate_onenote_export.py

Command:
python.exe .\validate_onenote_export.py --root .\Bennett-Notes --fail-log .\image_download_failures.log --report .\export_validation_report.txt

Checks:
- Remaining Graph URLs in HTML
- Local image references present
- Image file counts
- Failure log summary

## Error Handling Guide

### AADSTS50059 / unauthorized_client
- Use access token file mode rather than device flow.
- Refresh Graph Explorer token when needed.

### HTTP 401 during image downloads
- Token expired mid-run.
- Refresh token and re-run; script resumes and skips existing files.

### HTTP 429 throttling
- Use request delay and retry backoff settings.
- Re-run in passes until failures approach zero.

### PermissionError on pseudo .html paths
- Script was patched to process only real files and skip unreadable entries.

## Security and Data Handling
- Sensitive sections can be intentionally excluded from manifest.
- Token file should be protected and rotated/removed when no longer needed.
- Output is portable because HTML references local images, not Graph URLs.

## Deliverables Produced
- Local notebook export tree under Bennett-Notes
- Renamed HTML pages per page folder
- Local images directories and files
- Validation report: export_validation_report.txt
- Failure audit log: image_download_failures.log

## Completion Criteria (met)
- Export run completed
- HTML with Graph URLs reduced to zero
- Local image files populated
- Validation report generated

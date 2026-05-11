# OneNote Export Summary

## Objective
Export a SharePoint-hosted OneNote notebook into a portable local structure with:
- Notebook -> section -> page folders
- One HTML file per page
- Local image files downloaded and referenced from each HTML page
- No remaining live Graph image URLs in exported HTML

## Scope Completed
Notebook processed: Bennett-Notes
Location: E:\VSCode-Root\onenote\Bennett-Notes

Sections intentionally omitted from source population:
- Datalink (sensitive/password-protected content)
- Spectra Logic (no longer used)

## What Was Built
The following scripts were created/updated to complete the workflow:
- build_onenote_folder_tree.py
- export_onenote_page_details.py
- rename_onenote_html_files.py
- download_onenote_images_and_rewrite_html.py
- validate_onenote_export.py

Supporting data files used:
- onenote_structure.json
- graph_token.txt
- image_download_failures.log
- export_validation_report.txt

## Key Issues Encountered and Resolved
1. PowerShell execution policy blocked script execution.
- Resolved by moving workflow to Python.

2. Device auth errors (AADSTS50059, unauthorized_client) in tenant-specific flow.
- Added access-token support and token-file mode.
- Used Graph Explorer token path for reliable execution.

3. Folder naming included unwanted ID suffix (__<id>).
- Updated folder builder to use title-only naming and duplicate-safe suffixes.

4. Initial image rewrite pass missed URLs.
- Fixed Graph resource URL matching for users('id') URL format.

5. Long image runs failed due to throttling (HTTP 429).
- Added retry/backoff logic, optional request delay, and failure logging.

## Final Validation Snapshot
From final validation report:
- Total HTML files: 338
- HTML files with remaining Graph URLs: 0
- HTML files with local image references: 189
- Image files in images folders: 1038
- Residual failure entries: 1 (429)
- Overall status: complete

## Operational Notes
- Re-runs are resumable. Existing local images are skipped unless overwrite is requested.
- Token refresh may be required on long runs.
- Failure log allows targeted retry and post-run audit.

# NetBackup Flex Support Bundle Analyzer

This tool extracts a NetBackup Flex appliance support bundle in this format:

- `sosreport-<appliance>-<timestamp>-ondemand-<tag>.tar.xz`

Then it scans the extracted data for NetBackup and Flex related signals, including:

- Appliance and OS metadata
- System serial number
- Software and firmware version report card with device name, hostname, and parsed IPs
- Disk I/O summary from `proc/diskstats`
- Container and pod instance details from podman command outputs
- Network interface and route details
- Failed component alerts and warnings
- Typical hardware datacollect problem checks, including bad HDD/SSD, RAM ECC/MCE, CRC/link errors, time shifts, dmesg kernel issues, warnings, and errors
- NetBackup/Flex related files
- Error and warning lines in logs
- Top recurring issue patterns

## Requirements

- Python 3.9+

No external dependencies are required.

## Windows Extraction Behavior

Support bundles are generated on Linux and can contain file names that are invalid on Windows (for example `:` in sysfs paths).

When running on Windows, extraction behavior is:

- Archive is read with Python `tarfile` in `r:xz` mode
- Path traversal entries are rejected
- Invalid Windows filename characters are replaced with `_` during extraction
- Symlinks, device files, and other special Linux file types are skipped

This keeps extraction safe and allows analysis to proceed on Windows hosts.

## Usage

```bash
python support_bundle_analyzer.py \
  --bundle "C:/path/to/sosreport-VTAS0031037-20251022102519-ondemand-wtagxag.tar.xz" \
  --output "C:/path/to/output"
```

Analyze an already extracted sosreport tree (skips archive extraction):

```bash
python support_bundle_analyzer.py \
  --extracted-root "E:/testing-flex-bundle/extracted/sosreport-VTAS0031037-20251022102519-ondemand-wtagxag" \
  --output "E:/testing-flex-bundle-v2"
```

Optional obfuscated output:

```bash
python support_bundle_analyzer.py \
  --bundle "C:/path/to/sosreport-VTAS0031037-20251022102519-ondemand-wtagxag.tar.xz" \
  --output "C:/path/to/output" \
  --obfuscate
```

If `--output` is not provided, output is created in a folder next to the bundle.

## Output

The tool writes:

- `summary.json`: structured machine-readable results
- `report.md`: human-readable analysis report
- `report.html`: browser-friendly review report with a summary dashboard, collapsible sections, severity badges, copy buttons, and print-friendly CSS

`summary.json` includes structured `typical_problem_findings` and `report_card` sections that can be reused later for CSV/XLSX or Power BI import work.

When `--obfuscate` is used, sensitive values are redacted in all report outputs:

- IPv4 addresses
- MAC addresses
- UUID values
- Serial-like identifiers

## Example

```bash
python support_bundle_analyzer.py --bundle "sosreport-VTAS0031037-20251022102519-ondemand-wtagxag.tar.xz"
```

## Notes

- The analyzer intentionally limits how much content it reads from each file.
- Binary files are ignored.
- This is an offline parser and does not send data anywhere.

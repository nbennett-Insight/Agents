# Linux Health Check (LHC)

`Vx-LHC-Linux_Health_Check.sh` is a shell-based data collection and diagnostics utility for Linux systems, with optional deep reporting for Veritas NetBackup and MSDP environments.

The script can run:
- Full collection (`complete`)
- Guided partial collection (`partial`)
- Targeted report menus (for example `os`, `performance`, `netbackup`, `msdp`)
- Support-focused helper workflows (for example `logs`, `trace`)

At the end of execution, it creates a compressed archive (`.tgz`) intended for upload to Veritas Support.

## Windows PowerShell Equivalent

A Windows counterpart is now available:

- `Vx-LHC-Windows_Health_Check.ps1`

This script provides the same operational pattern for Windows systems:

- `complete` run for all major report categories
- `partial` run with prompts for selective data collection
- direct report execution (`os`, `memory`, `storage`, `network`, `performance`, `netbackup`, `logs`)
- notifications summary and final compressed archive creation

### Windows Usage

```powershell
# Run all report categories
powershell -ExecutionPolicy Bypass -File .\Vx-LHC-Windows_Health_Check.ps1 -Option complete -OutputPath C:\Temp

# Run partial (interactive prompts)
powershell -ExecutionPolicy Bypass -File .\Vx-LHC-Windows_Health_Check.ps1 -Option partial -OutputPath C:\Temp

# Run a single category
powershell -ExecutionPolicy Bypass -File .\Vx-LHC-Windows_Health_Check.ps1 -Option performance -OutputPath C:\Temp
```

### Windows Output

The PowerShell script creates:

- Output directory:
  - `<output_path>\<date>-LHC-Windows_Health_Check-<host>-<epoch>-<time>`
- Consolidated report folder:
  - `Reports\`
- Final archive:
  - `<output_dir>.zip`

Primary report domains include OS, memory, storage, network, performance, NetBackup (if installed), and Windows event log summaries.

## Version

- Script version reported internally: `2.0`

## What It Collects

Depending on host type and selected options, the script collects data for:

- OS/platform overview and configuration
- Kernel/system messages and error patterns
- Memory usage, process-level memory summaries
- Network routing/interfaces/statistics
- Storage layout and volume/device details
- Performance:
  - Historical (`sar`/sysstat-based)
  - Snapshot (short interval telemetry capture)
- NetBackup software environment/configuration/SLP
- MSDP status, dedupe, cloud, and session/performance data
- Appliance-specific details (NetBackup/Flex/NBFS/Access, IPMI/VCS where available)
- Notification summary of notable findings

## Prerequisites

Minimum requirements from script behavior:

- Linux host with `/proc` available
- `bash`
- `timeout` command available in:
  - `$PATH`, or
  - `/bin/timeout`, or
  - `/usr/bin/timeout`
- A writable output path with at least ~10 GB free space
- Working directory path and selected output path must not contain spaces

Recommended:

- Run as a privileged user (or with sufficient permissions) so all system and application commands can execute successfully.

## Host Detection

The script auto-detects platform capabilities and exposes options accordingly:

- NetBackup host: `/usr/openv/netbackup/version`
- MSDP host: `/etc/pdregistry.cfg`
- Appliance markers:
  - `/etc/nbapp-release`
  - `/etc/flex-release`
  - `/etc/nbfs-app-release`
  - `/etc/ltr-app-release`
- Container/app-instance context: `/.dockerenv` and `/proc/1/cgroup`

## Usage

### 1) Make executable

```bash
chmod +x Vx-LHC-Linux_Health_Check.sh
```

### 2) Run interactively (main menu)

```bash
./Vx-LHC-Linux_Health_Check.sh
```

### 3) Run with a direct option

```bash
./Vx-LHC-Linux_Health_Check.sh complete
```

### 4) Verbose shell tracing

```bash
./Vx-LHC-Linux_Health_Check.sh verbose
```

## Main Menu Options

Base options shown by the script include:

- `complete`
- `partial`
- `performance`
- `os`
- `memory`
- `storage`
- `network`
- `logs`
- `trace`
- `compress`
- `quit`

Additional options appear automatically when applicable:

- `netbackup` (NetBackup host)
- `msdp` (MSDP host)
- `appliance` (supported appliance platforms)

## Execution Modes

- `complete`
  - Runs all available reports for detected host features.
- `partial`
  - Prompts for individual report families (OS, memory, network, storage, performance, NetBackup, MSDP, appliance).
- Direct option (for example `os`, `msdp`, `logs`)
  - Opens that area/menu and allows specific sub-report selection.

## Output and Archive

You are prompted for an output path at runtime. The script creates:

- Output directory:
  - `<output_path>/<date>-LHC-Linux_Health_Check-<host>-<epoch>-<time>`
- Report subdirectory:
  - `Reports/`

Artifacts include:

- `LHC-Version.cfg`
- `LHC-Platform.txt` and `LHC-Platform.cfg`
- `LHC-Log.csv` and rendered `LHC-Log.txt`
- `Notifications.txt`
- Report text files under `Reports/` (renamed with date/host/time suffixes)

Final archive:

- `<output_dir>.tgz`

The script prints upload guidance to send this archive to Veritas Support.

## Logging Behavior

- Default execution uses a process log (`.log`) via `tee`.
- `verbose` enables shell tracing (`set -x`) and also logs via `tee`.
- Function runtime timing is recorded in `LHC-Log.csv`.

## Notes and Caveats

- The script enforces no spaces in:
  - Current working directory
  - Chosen output path
- Relative output paths are rejected; output path must begin with `/`.
- Some reports are environment-specific and will no-op or show errors if dependencies are absent.
- The script uses many external system commands and Veritas utilities; command availability varies by distro and installed product set.

## Typical Workflow

```bash
# 1) Run complete collection
./Vx-LHC-Linux_Health_Check.sh complete

# 2) Select an output path when prompted
# 3) Wait for report and archive creation
# 4) Upload the resulting .tgz file to Veritas Support
```

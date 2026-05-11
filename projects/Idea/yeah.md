# Cohesity DP Collector (NBSU-style)

Script: `cohesity_dp_collector.ps1`

## What It Does
- Connects to a Cohesity cluster (API key or credential)
- Collects raw JSON for cluster/jobs/job runs/alerts (+ optional audit)
- Builds normalized CSV summaries
- Writes manifest and text summary report
- Optionally compresses output and supports passphrase-based encrypted artifact

## Live Collection (API key)
```powershell
pwsh .\cohesity_dp_collector.ps1 `
	-Server 10.10.10.10 `
	-ApiKey "<api-key>" `
	-Hours 24 `
	-IncludeAudit `
	-OutputRoot .\out `
	-Compress
```

## Live Collection (credential)
```powershell
$cred = Get-Credential
pwsh .\cohesity_dp_collector.ps1 `
	-Server cluster-vip.mycorp.local `
	-Credential $cred `
	-Hours 72 `
	-OutputRoot .\out
```

## Offline Re-Processing
Use this mode to rebuild normalized outputs from a prior run:

```powershell
pwsh .\cohesity_dp_collector.ps1 `
	-InputBundle .\out\cdsu_YYYYMMDD_HHMMSS `
	-OutputRoot .\out_offline
```

## Output Layout
- `raw\*.json`
- `normalized\job_summary.csv`
- `normalized\failure_summary.csv`
- `normalized\alert_summary.csv`
- `metadata\manifest.json`
- `report\report.txt`

## Notes
- Requires `Cohesity.PowerShell` module for live mode.
- In live mode, output includes only what the connected account can access.
- Use `-Encrypt -Passphrase "..."` only when you need protected handoff artifacts.

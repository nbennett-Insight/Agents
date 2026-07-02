<#
  Disk-Usage-Report.ps1
  Wrapper for diskutilization.py.
  Usage:  .\diskutilization.ps1                          # scans C:\, top 20
          .\diskutilization.ps1 -Path D:\ -Top 30 -Levels 4 -BranchTop 6
#>
param(
    [string]$Path = "C:\",
    [int]$Top = 20,
    [int]$Levels = 3,
    [int]$BranchTop = 5
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "diskutilization.py"

if (-not (Test-Path $pythonScript)) {
    Write-Error "Python script not found: $pythonScript"
    exit 1
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "python is not available in PATH. Activate your virtual environment or install Python."
    exit 1
}

$argList = @(
    $pythonScript,
    "--path", $Path,
    "--top", "$Top",
    "--levels", "$Levels",
    "--branch-top", "$BranchTop"
)

& $pythonCmd.Source @argList
exit $LASTEXITCODE
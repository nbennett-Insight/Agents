[CmdletBinding(DefaultParameterSetName='LiveApiKey')]
param(
    [Parameter(ParameterSetName='LiveApiKey', Mandatory=$true)]
    [Parameter(ParameterSetName='LiveCredential', Mandatory=$true)]
    [string]$Server,

    [Parameter(ParameterSetName='LiveApiKey', Mandatory=$true)]
    [string]$ApiKey,

    [Parameter(ParameterSetName='LiveCredential', Mandatory=$true)]
    [System.Management.Automation.PSCredential]$Credential,

    [Parameter(ParameterSetName='Offline', Mandatory=$true)]
    [string]$InputBundle,

    [int]$Hours = 24,
    [string]$OutputRoot = ".",
    [switch]$IncludeAudit,
    [switch]$Compress,
    [switch]$Encrypt,
    [string]$Passphrase
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host "[cdsu] $Message"
}

function New-OutputTree {
    param([string]$Root)

    $runId = Get-Date -Format 'yyyyMMdd_HHmmss'
    $base = Join-Path $Root ("cdsu_{0}" -f $runId)

    $paths = @{
        Base       = $base
        Raw        = Join-Path $base 'raw'
        Normalized = Join-Path $base 'normalized'
        Report     = Join-Path $base 'report'
        Metadata   = Join-Path $base 'metadata'
    }

    foreach ($p in $paths.Values) {
        New-Item -ItemType Directory -Path $p -Force | Out-Null
    }

    return $paths
}

function Assert-CohesityModule {
    $module = Get-Module -ListAvailable -Name Cohesity.PowerShell
    if (-not $module) {
        throw "Cohesity.PowerShell module is not installed. Install-Module Cohesity.PowerShell -Scope CurrentUser"
    }
    Import-Module Cohesity.PowerShell -ErrorAction Stop
}

function Connect-Cluster {
    param(
        [string]$Target,
        [string]$ApiKeyValue,
        [System.Management.Automation.PSCredential]$Cred
    )

    if ($ApiKeyValue) {
        Connect-CohesityCluster -Server $Target -APIKey $ApiKeyValue | Out-Null
    }
    else {
        Connect-CohesityCluster -Server $Target -Credential $Cred | Out-Null
    }
}

function Get-StartUsecs {
    param([int]$HoursBack)
    $startUtc = (Get-Date).ToUniversalTime().AddHours(-1 * $HoursBack)
    $epoch = Get-Date '1970-01-01T00:00:00Z'
    return [int64](($startUtc - $epoch).TotalMilliseconds * 1000)
}

function Invoke-Safe {
    param(
        [scriptblock]$Script,
        [string]$Name
    )

    try {
        return & $Script
    }
    catch {
        Write-Warning ("{0}: {1}" -f $Name, $_.Exception.Message)
        return @()
    }
}

function Collect-LiveData {
    param([int]$HoursBack, [switch]$IncludeAuditLogs)

    $startUsecs = Get-StartUsecs -HoursBack $HoursBack

    $data = [ordered]@{}
    $data.cluster = Invoke-Safe -Name 'Get-CohesityCluster' -Script { Get-CohesityCluster }
    $data.sourcesSummary = Invoke-Safe -Name 'Get-CohesityProtectionSourceSummary' -Script { Get-CohesityProtectionSourceSummary }
    $data.storageDomains = Invoke-Safe -Name 'Get-CohesityStorageDomain' -Script { Get-CohesityStorageDomain }
    $data.jobs = Invoke-Safe -Name 'Get-CohesityProtectionJob' -Script { Get-CohesityProtectionJob }

    $jobRuns = Invoke-Safe -Name 'Get-CohesityProtectionJobRun' -Script {
        Get-CohesityProtectionJobRun -StartTimeUsecs $startUsecs
    }
    $data.jobRuns = $jobRuns

    $data.alerts = Invoke-Safe -Name 'Get-CohesityAlert' -Script { Get-CohesityAlert }

    if ($IncludeAuditLogs) {
        $data.audit = Invoke-Safe -Name 'Get-CohesityAuditLog' -Script { Get-CohesityAuditLog -StartTimeUsecs $startUsecs }
    }
    else {
        $data.audit = @()
    }

    return $data
}

function Save-RawData {
    param(
        [hashtable]$Data,
        [string]$RawDir
    )

    foreach ($key in $Data.Keys) {
        $outFile = Join-Path $RawDir ("{0}.json" -f $key)
        $Data[$key] | ConvertTo-Json -Depth 12 | Out-File -FilePath $outFile -Encoding utf8
    }
}

function Resolve-RunStatus {
    param($Run)

    foreach ($prop in @('status', 'backupRunStatus', 'state', 'jobStatus')) {
        if ($Run.PSObject.Properties.Name -contains $prop -and $Run.$prop) {
            return [string]$Run.$prop
        }
    }
    return 'Unknown'
}

function Resolve-RunDurationSec {
    param($Run)

    $start = $null
    $end = $null

    foreach ($s in @('startTimeUsecs', 'startUsecs')) {
        if ($Run.PSObject.Properties.Name -contains $s -and $Run.$s) {
            $start = [int64]$Run.$s
            break
        }
    }

    foreach ($e in @('endTimeUsecs', 'endUsecs')) {
        if ($Run.PSObject.Properties.Name -contains $e -and $Run.$e) {
            $end = [int64]$Run.$e
            break
        }
    }

    if ($start -and $end -and $end -ge $start) {
        return [math]::Round((($end - $start) / 1000000), 2)
    }

    return $null
}

function Build-Normalized {
    param([hashtable]$Data)

    $jobRuns = @($Data.jobRuns)
    $alerts = @($Data.alerts)

    $jobSummary = foreach ($run in $jobRuns) {
        [pscustomobject]@{
            JobName      = if ($run.jobName) { $run.jobName } else { $run.name }
            JobId        = if ($run.jobId) { $run.jobId } else { $run.id }
            Status       = Resolve-RunStatus -Run $run
            StartUsecs   = if ($run.startTimeUsecs) { $run.startTimeUsecs } elseif ($run.startUsecs) { $run.startUsecs } else { $null }
            EndUsecs     = if ($run.endTimeUsecs) { $run.endTimeUsecs } elseif ($run.endUsecs) { $run.endUsecs } else { $null }
            DurationSec  = Resolve-RunDurationSec -Run $run
            LogicalBytes = if ($run.logicalSizeBytes) { $run.logicalSizeBytes } else { $null }
            ReadBytes    = if ($run.readBytes) { $run.readBytes } else { $null }
            WrittenBytes = if ($run.writtenBytes) { $run.writtenBytes } else { $null }
        }
    }

    $failureSummary = $jobSummary |
        Where-Object { $_.Status -notin @('Succeeded', 'kSuccess', 'Success') } |
        Group-Object Status |
        Sort-Object Count -Descending |
        ForEach-Object {
            [pscustomobject]@{
                Status = $_.Name
                Count  = $_.Count
            }
        }

    $alertSummary = $alerts |
        Group-Object severity |
        Sort-Object Count -Descending |
        ForEach-Object {
            [pscustomobject]@{
                Severity = if ($_.Name) { $_.Name } else { 'Unknown' }
                Count    = $_.Count
            }
        }

    return [ordered]@{
        job_summary     = $jobSummary
        failure_summary = $failureSummary
        alert_summary   = $alertSummary
    }
}

function Save-Normalized {
    param(
        [hashtable]$Normalized,
        [string]$NormalizedDir
    )

    $Normalized.job_summary | Export-Csv -Path (Join-Path $NormalizedDir 'job_summary.csv') -NoTypeInformation -Encoding utf8
    $Normalized.failure_summary | Export-Csv -Path (Join-Path $NormalizedDir 'failure_summary.csv') -NoTypeInformation -Encoding utf8
    $Normalized.alert_summary | Export-Csv -Path (Join-Path $NormalizedDir 'alert_summary.csv') -NoTypeInformation -Encoding utf8
}

function Save-Manifest {
    param(
        [string]$Path,
        [hashtable]$Data,
        [hashtable]$Normalized,
        [string]$ServerName,
        [int]$HoursBack,
        [bool]$AuditEnabled,
        [string]$Mode
    )

    $manifest = [ordered]@{
        collector = 'cdsu'
        version = '0.1.0'
        mode = $Mode
        server = $ServerName
        generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
        hours = $HoursBack
        includeAudit = $AuditEnabled
        counts = [ordered]@{
            jobs = @($Data.jobs).Count
            jobRuns = @($Data.jobRuns).Count
            alerts = @($Data.alerts).Count
            audit = @($Data.audit).Count
            failures = @($Normalized.failure_summary | Measure-Object Count -Sum).Sum
        }
    }

    $manifest | ConvertTo-Json -Depth 8 | Out-File -FilePath $Path -Encoding utf8
}

function Save-Report {
    param(
        [string]$Path,
        [hashtable]$ManifestObj,
        [hashtable]$Normalized
    )

    $lines = @()
    $lines += "Cohesity DataProtect Support Collector Summary"
    $lines += "Generated (UTC): $($ManifestObj.generatedUtc)"
    $lines += "Mode: $($ManifestObj.mode)"
    $lines += "Server: $($ManifestObj.server)"
    $lines += "Window (hours): $($ManifestObj.hours)"
    $lines += ""
    $lines += "Counts:"
    $lines += "- Jobs: $($ManifestObj.counts.jobs)"
    $lines += "- Job Runs: $($ManifestObj.counts.jobRuns)"
    $lines += "- Alerts: $($ManifestObj.counts.alerts)"
    $lines += "- Audit Events: $($ManifestObj.counts.audit)"
    $lines += "- Failed/Non-success Runs: $($ManifestObj.counts.failures)"
    $lines += ""
    $lines += "Top Failure Statuses:"

    $topFailures = @($Normalized.failure_summary | Select-Object -First 10)
    if ($topFailures.Count -eq 0) {
        $lines += "- none"
    }
    else {
        foreach ($f in $topFailures) {
            $lines += "- $($f.Status): $($f.Count)"
        }
    }

    $lines | Out-File -FilePath $Path -Encoding utf8
}

function Compress-Output {
    param(
        [string]$BasePath,
        [switch]$DoEncrypt,
        [string]$Secret
    )

    $zipPath = "{0}.zip" -f $BasePath
    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }

    Compress-Archive -Path (Join-Path $BasePath '*') -DestinationPath $zipPath -Force
    Write-Step ("Compressed bundle: {0}" -f $zipPath)

    if ($DoEncrypt) {
        if (-not $Secret) {
            throw "-Encrypt requires -Passphrase"
        }

        $secure = ConvertTo-SecureString -String $Secret -AsPlainText -Force
        $encPath = "{0}.secure" -f $zipPath
        if (Test-Path $encPath) {
            Remove-Item $encPath -Force
        }

        $payload = [System.Convert]::ToBase64String([System.IO.File]::ReadAllBytes($zipPath))
        $payload | ConvertFrom-SecureString -SecureKey ([Text.Encoding]::UTF8.GetBytes(($Secret.PadRight(32).Substring(0,32)))) | Out-File -FilePath $encPath -Encoding ascii
        Write-Step ("Encrypted bundle: {0}" -f $encPath)
    }
}

function Load-OfflineData {
    param([string]$BundlePath)

    if (-not (Test-Path $BundlePath)) {
        throw "Input bundle path not found: $BundlePath"
    }

    $rawDir = Join-Path $BundlePath 'raw'
    if (-not (Test-Path $rawDir)) {
        throw "Offline bundle missing raw folder: $rawDir"
    }

    $data = [ordered]@{}
    foreach ($name in @('cluster','sourcesSummary','storageDomains','jobs','jobRuns','alerts','audit')) {
        $file = Join-Path $rawDir ("{0}.json" -f $name)
        if (Test-Path $file) {
            $json = Get-Content -Path $file -Raw
            $data[$name] = if ($json.Trim()) { $json | ConvertFrom-Json } else { @() }
        }
        else {
            $data[$name] = @()
        }
    }

    return $data
}

$paths = New-OutputTree -Root $OutputRoot
$mode = if ($PSCmdlet.ParameterSetName -eq 'Offline') { 'offline' } else { 'live' }

Write-Step ("Output: {0}" -f $paths.Base)

if ($mode -eq 'live') {
    Assert-CohesityModule
    Write-Step ("Connecting to Cohesity cluster {0}" -f $Server)
    Connect-Cluster -Target $Server -ApiKeyValue $ApiKey -Cred $Credential
    try {
        Write-Step ("Collecting live data (last {0}h)" -f $Hours)
        $data = Collect-LiveData -HoursBack $Hours -IncludeAuditLogs:$IncludeAudit
    }
    finally {
        Disconnect-CohesityCluster | Out-Null
    }
}
else {
    Write-Step ("Loading offline bundle: {0}" -f $InputBundle)
    $data = Load-OfflineData -BundlePath $InputBundle
    $Server = 'offline-bundle'
}

Write-Step 'Saving raw JSON payloads'
Save-RawData -Data $data -RawDir $paths.Raw

Write-Step 'Building normalized summaries'
$normalized = Build-Normalized -Data $data
Save-Normalized -Normalized $normalized -NormalizedDir $paths.Normalized

$manifestPath = Join-Path $paths.Metadata 'manifest.json'
Save-Manifest -Path $manifestPath -Data $data -Normalized $normalized -ServerName $Server -HoursBack $Hours -AuditEnabled ([bool]$IncludeAudit) -Mode $mode
$manifestObj = Get-Content -Path $manifestPath -Raw | ConvertFrom-Json

$reportPath = Join-Path $paths.Report 'report.txt'
Save-Report -Path $reportPath -ManifestObj $manifestObj -Normalized $normalized

if ($Compress) {
    Compress-Output -BasePath $paths.Base -DoEncrypt:$Encrypt -Secret $Passphrase
}

Write-Step 'Done'
Write-Host "Collector output ready: $($paths.Base)"

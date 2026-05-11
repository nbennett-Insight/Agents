[CmdletBinding()]
param(
    [ValidateSet('complete', 'partial', 'os', 'memory', 'storage', 'network', 'performance', 'netbackup', 'logs', 'compress', 'quit')]
    [string]$Option,
    [string]$OutputPath = (Get-Location).Path,
    [switch]$VerboseLogging
)

$ErrorActionPreference = 'Stop'
$script:LhcVersion = '2.0-windows'
$script:StartTime = Get-Date
$script:RunLog = New-Object System.Collections.Generic.List[object]
$script:CreateArchiveComplete = $false

function Add-RunLog {
    param([string]$FunctionName)

    $now = Get-Date
    $totalSeconds = [math]::Round(($now - $script:StartTime).TotalSeconds, 2)
    $script:RunLog.Add([pscustomobject]@{
            Epoch        = [int][double]::Parse((Get-Date -Date $now -UFormat %s))
            DateTime      = $now.ToString('yyyy-MM-dd HH:mm:ss')
            TotalSeconds  = $totalSeconds
            Function      = $FunctionName
        })
}

function Write-Section {
    param([string]$Title)
    Write-Host ''
    Write-Host ('=' * 90)
    Write-Host $Title
    Write-Host ('=' * 90)
}

function Save-TextReport {
    param(
        [string]$Path,
        [object]$InputObject
    )
    $InputObject | Out-File -FilePath $Path -Encoding UTF8 -Width 4096
}

function Save-JsonReport {
    param(
        [string]$Path,
        [object]$InputObject,
        [int]$Depth = 6
    )
    $InputObject | ConvertTo-Json -Depth $Depth | Out-File -FilePath $Path -Encoding UTF8
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Initialize-Platform {
    $nbuPathCandidates = @(
        'C:\Program Files\Veritas\NetBackup\bin\bpclntcmd.exe',
        'C:\Program Files (x86)\Veritas\NetBackup\bin\bpclntcmd.exe'
    )

    $script:Platform = [pscustomobject]@{
        ComputerName = $env:COMPUTERNAME
        IsAdmin      = Test-IsAdmin
        NetBackup    = ($nbuPathCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1)
        MSDP         = $false
    }

    if (-not $script:Platform.IsAdmin) {
        Write-Warning 'Running without Administrator privileges may reduce report completeness.'
    }

    Add-RunLog -FunctionName 'Initialize-Platform'
}

function Initialize-Output {
    if (-not [System.IO.Path]::IsPathRooted($OutputPath)) {
        throw "OutputPath must be an absolute path. Provided: $OutputPath"
    }

    if (-not (Test-Path -LiteralPath $OutputPath)) {
        throw "OutputPath does not exist: $OutputPath"
    }

    $targetItem = Get-Item -LiteralPath $OutputPath
    if ($targetItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Write-Warning 'OutputPath is a reparse point. Ensure this is intentional.'
    }

    $drive = Get-PSDrive -Name ([System.IO.Path]::GetPathRoot($OutputPath).TrimEnd('\').TrimEnd(':'))
    if ($null -ne $drive -and $drive.Free -lt 10GB) {
        throw "Output path drive has less than 10 GB free space: $($drive.Free / 1GB -as [int]) GB"
    }

    $date = Get-Date -Format 'yyyy-MM-dd'
    $epoch = [int][double]::Parse((Get-Date -UFormat %s))
    $clock = Get-Date -Format 'HHh_mm_mss'
    $hostShort = $env:COMPUTERNAME

    $script:OutputDir = Join-Path $OutputPath "$date-LHC-Windows_Health_Check-$hostShort-$epoch-$clock"
    $script:ReportDir = Join-Path $script:OutputDir 'Reports'

    $directories = @(
        $script:OutputDir,
        $script:ReportDir,
        (Join-Path $script:OutputDir 'OS'),
        (Join-Path $script:OutputDir 'Memory'),
        (Join-Path $script:OutputDir 'Storage'),
        (Join-Path $script:OutputDir 'Network'),
        (Join-Path $script:OutputDir 'Performance'),
        (Join-Path $script:OutputDir 'NetBackup'),
        (Join-Path $script:OutputDir 'Logs')
    )

    foreach ($dir in $directories) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    }

    $platformCfg = @(
        "LHC_Version=$script:LhcVersion"
        "ComputerName=$($script:Platform.ComputerName)"
        "IsAdmin=$($script:Platform.IsAdmin)"
        "NetBackupInstalled=$([bool]$script:Platform.NetBackup)"
        "NetBackupPath=$($script:Platform.NetBackup)"
        "MSDPHost=$($script:Platform.MSDP)"
    )

    $platformCfg | Out-File -FilePath (Join-Path $script:OutputDir 'LHC-Platform.cfg') -Encoding UTF8
    Add-RunLog -FunctionName 'Initialize-Output'
}

function Invoke-ExternalCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$OutFile
    )

    if (-not (Test-Path -LiteralPath $FilePath)) {
        "Skipped. File not found: $FilePath" | Out-File -FilePath $OutFile -Encoding UTF8
        return
    }

    try {
        $output = & $FilePath @Arguments 2>&1
        $output | Out-File -FilePath $OutFile -Encoding UTF8 -Width 4096
    }
    catch {
        "Command failed: $FilePath $($Arguments -join ' ')" | Out-File -FilePath $OutFile -Encoding UTF8
        $_ | Out-File -FilePath $OutFile -Encoding UTF8 -Append
    }
}

function Get-TopProcessesByMemory {
    Get-Process |
        Sort-Object -Property WorkingSet64 -Descending |
        Select-Object -First 50 Name, Id,
        @{ Name = 'WorkingSetMB'; Expression = { [math]::Round($_.WorkingSet64 / 1MB, 2) } },
        @{ Name = 'PrivateMemoryMB'; Expression = { [math]::Round($_.PrivateMemorySize64 / 1MB, 2) } },
        CPU, StartTime
}

function Collect-OSReport {
    Write-Section 'Collecting OS Report'
    $osDir = Join-Path $script:OutputDir 'OS'

    Save-TextReport -Path (Join-Path $osDir 'computerinfo.txt') -InputObject (systeminfo)
    Save-TextReport -Path (Join-Path $osDir 'os-caption.txt') -InputObject (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, LastBootUpTime, CSName)
    Save-TextReport -Path (Join-Path $osDir 'computer-system.txt') -InputObject (Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, Domain, TotalPhysicalMemory)
    Save-TextReport -Path (Join-Path $osDir 'bios.txt') -InputObject (Get-CimInstance Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion, ReleaseDate, SerialNumber)
    Save-TextReport -Path (Join-Path $osDir 'timezone.txt') -InputObject (Get-TimeZone)
    Save-TextReport -Path (Join-Path $osDir 'hotfixes-last-100.txt') -InputObject (Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 100)
    Save-TextReport -Path (Join-Path $osDir 'services-auto-not-running.txt') -InputObject (Get-Service | Where-Object { $_.StartType -eq 'Automatic' -and $_.Status -ne 'Running' } | Sort-Object Name)

    $eventFilter = @{ LogName = @('System', 'Application'); Level = 1, 2, 3; StartTime = (Get-Date).AddHours(-24) }
    Save-TextReport -Path (Join-Path $osDir 'events-last-24h-critical-error-warning.txt') -InputObject (Get-WinEvent -FilterHashtable $eventFilter -ErrorAction SilentlyContinue | Select-Object -First 1000 TimeCreated, Id, LevelDisplayName, ProviderName, LogName, Message)

    Copy-Item -LiteralPath (Join-Path $osDir 'os-caption.txt') -Destination (Join-Path $script:ReportDir 'OS-Overview.txt') -Force
    Add-RunLog -FunctionName 'Collect-OSReport'
}

function Collect-MemoryReport {
    Write-Section 'Collecting Memory Report'
    $memDir = Join-Path $script:OutputDir 'Memory'

    $os = Get-CimInstance Win32_OperatingSystem
    $totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $usedGB = [math]::Round($totalGB - $freeGB, 2)
    $usedPct = if ($totalGB -gt 0) { [math]::Round(($usedGB / $totalGB) * 100, 2) } else { 0 }

    $summary = [pscustomobject]@{
        TotalMemoryGB = $totalGB
        UsedMemoryGB  = $usedGB
        FreeMemoryGB  = $freeGB
        UsedPercent   = $usedPct
    }

    Save-TextReport -Path (Join-Path $memDir 'memory-summary.txt') -InputObject $summary
    Save-TextReport -Path (Join-Path $memDir 'processes-top-50-memory.txt') -InputObject (Get-TopProcessesByMemory)

    Get-Counter '\Memory\Available MBytes', '\Memory\Committed Bytes', '\Memory\% Committed Bytes In Use' |
        Select-Object -ExpandProperty CounterSamples |
        Select-Object Path, CookedValue |
        Export-Csv -Path (Join-Path $memDir 'memory-counters.csv') -NoTypeInformation

    Copy-Item -LiteralPath (Join-Path $memDir 'memory-summary.txt') -Destination (Join-Path $script:ReportDir 'Memory-Summary.txt') -Force
    Add-RunLog -FunctionName 'Collect-MemoryReport'
}

function Collect-StorageReport {
    Write-Section 'Collecting Storage Report'
    $storageDir = Join-Path $script:OutputDir 'Storage'

    Save-TextReport -Path (Join-Path $storageDir 'volumes.txt') -InputObject (Get-Volume | Sort-Object DriveLetter)
    Save-TextReport -Path (Join-Path $storageDir 'logical-disks.txt') -InputObject (Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, DriveType, FileSystem, Size, FreeSpace, VolumeName)
    Save-TextReport -Path (Join-Path $storageDir 'partitions.txt') -InputObject (Get-Partition | Sort-Object DiskNumber, PartitionNumber)
    Save-TextReport -Path (Join-Path $storageDir 'disks.txt') -InputObject (Get-Disk | Sort-Object Number)

    try {
        Save-TextReport -Path (Join-Path $storageDir 'physical-disks.txt') -InputObject (Get-PhysicalDisk | Sort-Object FriendlyName)
    }
    catch {
        Save-TextReport -Path (Join-Path $storageDir 'physical-disks.txt') -InputObject 'Get-PhysicalDisk is not available on this system.'
    }

    Copy-Item -LiteralPath (Join-Path $storageDir 'volumes.txt') -Destination (Join-Path $script:ReportDir 'Storage-Volumes.txt') -Force
    Add-RunLog -FunctionName 'Collect-StorageReport'
}

function Collect-NetworkReport {
    Write-Section 'Collecting Network Report'
    $netDir = Join-Path $script:OutputDir 'Network'

    Save-TextReport -Path (Join-Path $netDir 'ipconfig-all.txt') -InputObject (ipconfig /all)
    Save-TextReport -Path (Join-Path $netDir 'net-adapters.txt') -InputObject (Get-NetAdapter | Sort-Object Status, Name)
    Save-TextReport -Path (Join-Path $netDir 'net-ipconfiguration.txt') -InputObject (Get-NetIPConfiguration)
    Save-TextReport -Path (Join-Path $netDir 'routes.txt') -InputObject (Get-NetRoute -AddressFamily IPv4 | Sort-Object DestinationPrefix, RouteMetric)
    Save-TextReport -Path (Join-Path $netDir 'dns-client-server-address.txt') -InputObject (Get-DnsClientServerAddress)
    Save-TextReport -Path (Join-Path $netDir 'tcp-connections.txt') -InputObject (Get-NetTCPConnection | Sort-Object State, LocalPort)

    Copy-Item -LiteralPath (Join-Path $netDir 'net-ipconfiguration.txt') -Destination (Join-Path $script:ReportDir 'Network-IPConfiguration.txt') -Force
    Add-RunLog -FunctionName 'Collect-NetworkReport'
}

function Collect-PerformanceReport {
    Write-Section 'Collecting Performance Report (60 seconds)'
    $perfDir = Join-Path $script:OutputDir 'Performance'

    $counterPaths = @(
        '\Processor(_Total)\% Processor Time',
        '\Memory\Available MBytes',
        '\PhysicalDisk(_Total)\Avg. Disk sec/Read',
        '\PhysicalDisk(_Total)\Avg. Disk sec/Write',
        '\Network Interface(*)\Bytes Total/sec'
    )

    $samples = Get-Counter -Counter $counterPaths -SampleInterval 5 -MaxSamples 12

    $flat = foreach ($sample in $samples.CounterSamples) {
        [pscustomobject]@{
            TimeStamp = $sample.TimeStamp
            Path      = $sample.Path
            Value     = [math]::Round($sample.CookedValue, 4)
        }
    }

    $flat | Export-Csv -Path (Join-Path $perfDir 'performance-timeseries.csv') -NoTypeInformation

    $summary = $flat |
        Group-Object Path |
        ForEach-Object {
            [pscustomobject]@{
                Counter = $_.Name
                Min     = [math]::Round(($_.Group.Value | Measure-Object -Minimum).Minimum, 4)
                Avg     = [math]::Round(($_.Group.Value | Measure-Object -Average).Average, 4)
                Max     = [math]::Round(($_.Group.Value | Measure-Object -Maximum).Maximum, 4)
            }
        }

    Save-TextReport -Path (Join-Path $perfDir 'performance-summary.txt') -InputObject $summary
    Copy-Item -LiteralPath (Join-Path $perfDir 'performance-summary.txt') -Destination (Join-Path $script:ReportDir 'Performance-Summary.txt') -Force
    Add-RunLog -FunctionName 'Collect-PerformanceReport'
}

function Collect-NetBackupReport {
    Write-Section 'Collecting NetBackup Report'
    $nbuDir = Join-Path $script:OutputDir 'NetBackup'

    if (-not $script:Platform.NetBackup) {
        Save-TextReport -Path (Join-Path $nbuDir 'netbackup-status.txt') -InputObject 'NetBackup binaries were not detected on this host.'
        Add-RunLog -FunctionName 'Collect-NetBackupReport'
        return
    }

    $binDir = Split-Path -Path $script:Platform.NetBackup -Parent

    Invoke-ExternalCommand -FilePath (Join-Path $binDir 'bpclntcmd.exe') -Arguments @('-pn') -OutFile (Join-Path $nbuDir 'bpclntcmd-pn.txt')
    Invoke-ExternalCommand -FilePath (Join-Path $binDir 'bpps.exe') -Arguments @('-x') -OutFile (Join-Path $nbuDir 'bpps-x.txt')
    Invoke-ExternalCommand -FilePath (Join-Path $binDir 'bpdbjobs.exe') -Arguments @('-report') -OutFile (Join-Path $nbuDir 'bpdbjobs-report.txt')

    Copy-Item -LiteralPath (Join-Path $nbuDir 'bpps-x.txt') -Destination (Join-Path $script:ReportDir 'NetBackup-Processes.txt') -Force -ErrorAction SilentlyContinue
    Add-RunLog -FunctionName 'Collect-NetBackupReport'
}

function Collect-LogReport {
    Write-Section 'Collecting Windows Event Logs'
    $logDir = Join-Path $script:OutputDir 'Logs'

    $sys = Get-WinEvent -FilterHashtable @{ LogName = 'System'; Level = 1, 2, 3; StartTime = (Get-Date).AddDays(-3) } -ErrorAction SilentlyContinue |
        Select-Object -First 5000 TimeCreated, Id, LevelDisplayName, ProviderName, Message
    $app = Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Level = 1, 2, 3; StartTime = (Get-Date).AddDays(-3) } -ErrorAction SilentlyContinue |
        Select-Object -First 5000 TimeCreated, Id, LevelDisplayName, ProviderName, Message

    Save-JsonReport -Path (Join-Path $logDir 'system-events-last-3-days.json') -InputObject $sys -Depth 5
    Save-JsonReport -Path (Join-Path $logDir 'application-events-last-3-days.json') -InputObject $app -Depth 5

    Save-TextReport -Path (Join-Path $script:ReportDir 'Logs-Counts.txt') -InputObject @(
        "System events captured: $($sys.Count)"
        "Application events captured: $($app.Count)"
    )

    Add-RunLog -FunctionName 'Collect-LogReport'
}

function Build-Notifications {
    Write-Section 'Building Notifications Summary'

    $notifications = New-Object System.Collections.Generic.List[string]

    $volumes = Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter }
    foreach ($v in $volumes) {
        if ($v.SizeRemaining -lt 10GB) {
            $notifications.Add("WARNING: Low disk space on $($v.DriveLetter): - free $([math]::Round($v.SizeRemaining / 1GB, 2)) GB")
        }
    }

    $os = Get-CimInstance Win32_OperatingSystem
    $totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $usedPct = if ($totalGB -gt 0) { [math]::Round((($totalGB - $freeGB) / $totalGB) * 100, 2) } else { 0 }
    if ($usedPct -ge 90) {
        $notifications.Add("WARNING: High memory utilization: $usedPct%")
    }

    $autoStopped = Get-Service -ErrorAction SilentlyContinue | Where-Object { $_.StartType -eq 'Automatic' -and $_.Status -ne 'Running' }
    if ($autoStopped.Count -gt 0) {
        $notifications.Add("WARNING: Automatic services not running: $($autoStopped.Count)")
    }

    if ($notifications.Count -eq 0) {
        $notifications.Add('No immediate warning conditions were detected by the summary checks.')
    }

    $notifications | Out-File -FilePath (Join-Path $script:OutputDir 'Notifications.txt') -Encoding UTF8
    Copy-Item -LiteralPath (Join-Path $script:OutputDir 'Notifications.txt') -Destination (Join-Path $script:ReportDir 'Notifications.txt') -Force
    Add-RunLog -FunctionName 'Build-Notifications'
}

function Write-RunLogFiles {
    $csvPath = Join-Path $script:OutputDir 'LHC-Log.csv'
    $txtPath = Join-Path $script:OutputDir 'LHC-Log.txt'

    $script:RunLog | Export-Csv -Path $csvPath -NoTypeInformation
    Save-TextReport -Path $txtPath -InputObject $script:RunLog
}

function Create-Archive {
    if ($script:CreateArchiveComplete) {
        return
    }

    Write-Section 'Creating Output Archive'

    Write-RunLogFiles

    $zipPath = "$script:OutputDir.zip"
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    Compress-Archive -Path $script:OutputDir -DestinationPath $zipPath -CompressionLevel Optimal

    $script:CreateArchiveComplete = $true

    Write-Host ''
    Write-Host "Report folder : $script:OutputDir"
    Write-Host "Report archive: $zipPath"

    Add-RunLog -FunctionName 'Create-Archive'
}

function Run-Complete {
    Collect-OSReport
    Collect-MemoryReport
    Collect-StorageReport
    Collect-NetworkReport
    Collect-PerformanceReport
    Collect-NetBackupReport
    Collect-LogReport
}

function Confirm-RunSection {
    param([string]$Prompt)

    $answer = Read-Host "$Prompt (y/n)"
    return $answer -match '^(y|yes)$'
}

function Run-Partial {
    if (Confirm-RunSection -Prompt 'Run OS report?') { Collect-OSReport }
    if (Confirm-RunSection -Prompt 'Run Memory report?') { Collect-MemoryReport }
    if (Confirm-RunSection -Prompt 'Run Storage report?') { Collect-StorageReport }
    if (Confirm-RunSection -Prompt 'Run Network report?') { Collect-NetworkReport }
    if (Confirm-RunSection -Prompt 'Run Performance report?') { Collect-PerformanceReport }
    if (Confirm-RunSection -Prompt 'Run NetBackup report?') { Collect-NetBackupReport }
    if (Confirm-RunSection -Prompt 'Run Logs report?') { Collect-LogReport }
}

function Show-MainMenu {
    Write-Host ''
    Write-Host 'Windows Health Check - Main Menu'
    Write-Host ''
    Write-Host '  complete     - Run all report categories'
    Write-Host '  partial      - Prompt for selected categories'
    Write-Host '  os           - Run OS report only'
    Write-Host '  memory       - Run Memory report only'
    Write-Host '  storage      - Run Storage report only'
    Write-Host '  network      - Run Network report only'
    Write-Host '  performance  - Run Performance report only'
    Write-Host '  netbackup    - Run NetBackup report only'
    Write-Host '  logs         - Run Windows event log report only'
    Write-Host '  compress     - Build notifications and zip archive'
    Write-Host '  quit         - Exit'
    Write-Host ''

    return Read-Host 'Enter option'
}

try {
    Initialize-Platform
    Initialize-Output

    if ($VerboseLogging) {
        $transcriptPath = Join-Path $script:OutputDir 'Process-Transcript.log'
        Start-Transcript -Path $transcriptPath -Force | Out-Null
    }

    if (-not $Option) {
        $Option = Show-MainMenu
    }

    switch ($Option) {
        'complete' { Run-Complete }
        'partial' { Run-Partial }
        'os' { Collect-OSReport }
        'memory' { Collect-MemoryReport }
        'storage' { Collect-StorageReport }
        'network' { Collect-NetworkReport }
        'performance' { Collect-PerformanceReport }
        'netbackup' { Collect-NetBackupReport }
        'logs' { Collect-LogReport }
        'compress' { }
        'quit' { return }
        default { throw "Invalid option: $Option" }
    }

    Build-Notifications
    Create-Archive

    Write-Host ''
    Write-Host 'Done. Upload the generated .zip archive to support if requested.'
}
catch {
    Write-Error $_
    exit 9
}
finally {
    if ($VerboseLogging) {
        try { Stop-Transcript | Out-Null } catch { }
    }
}

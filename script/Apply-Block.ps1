$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigDir = Join-Path $ProjectRoot "config"
$StateDir = Join-Path $ProjectRoot "state"
$LogDir = Join-Path $ProjectRoot "logs"

$BlockedSitesFile = Join-Path $ConfigDir "blocked-sites.txt"
$BackupFile = Join-Path $StateDir "hosts.original.bak"
$HostsFile = Join-Path $env:SystemRoot "System32\drivers\etc\hosts"
$LogFile = Join-Path $LogDir "SeeUat4.log"

$StartMarker = "# SEEuat4_START"
$EndMarker = "# SEEuat4_END"

function Test-Administrator {
    $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $Principal = New-Object Security.Principal.WindowsPrincipal($Identity)

    return $Principal.IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
}

if (-not (Test-Administrator)) {
    throw "Run PowerShell as Administrator."
}

if (-not (Test-Path $BlockedSitesFile)) {
    throw "Missing configuration file: $BlockedSitesFile"
}

if (-not (Test-Path $HostsFile)) {
    throw "Windows Hosts file not found."
}

New-Item -ItemType Directory -Force -Path $StateDir, $LogDir |
    Out-Null

$Domains = @(
    Get-Content -LiteralPath $BlockedSitesFile |
    ForEach-Object { $_.Trim() } |
    Where-Object {
        $_ -ne "" -and -not $_.StartsWith("#")
    } |
    Sort-Object -Unique
)

if ($Domains.Count -eq 0) {
    throw "No domains configured."
}

$DomainPattern = '^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$'

foreach ($Domain in $Domains) {
    if ($Domain -notmatch $DomainPattern) {
        throw "Invalid domain in blocked-sites.txt: $Domain"
    }
}

$Content = [System.IO.File]::ReadAllText($HostsFile)

$StartCount = ([regex]::Matches(
    $Content, [regex]::Escape($StartMarker)
)).Count

$EndCount = ([regex]::Matches(
    $Content, [regex]::Escape($EndMarker)
)).Count

if ($StartCount -ne $EndCount -or $StartCount -gt 1) {
    throw "Invalid or duplicated SeeUat4 markers in Hosts file."
}

if (-not (Test-Path $BackupFile)) {
    if ($StartCount -gt 0) {
        throw "Cannot create an original backup: SeeUat4 markers already exist."
    }

    Copy-Item -LiteralPath $HostsFile -Destination $BackupFile

    Write-Host "Original Hosts backup created."
}

if ($StartCount -eq 1) {
    $Pattern = '(?ms)^' +
        [regex]::Escape($StartMarker) +
        '\r?\n.*?^' +
        [regex]::Escape($EndMarker) +
        '(?:\r?\n|$)'

    if (-not [regex]::IsMatch($Content, $Pattern)) {
        throw "SeeUat4 marker block is malformed."
    }

    $Content = [regex]::Replace($Content, $Pattern, "")
}

$BlockLines = @($StartMarker)

foreach ($Domain in $Domains) {
    $BlockLines += "0.0.0.0 $Domain"
}

$BlockLines += $EndMarker

$NewContent = $Content.TrimEnd() +
    [Environment]::NewLine +
    ($BlockLines -join [Environment]::NewLine) +
    [Environment]::NewLine

$TempFile = Join-Path $env:SystemRoot "System32\drivers\etc\hosts.seeu4.tmp"

try {
    [System.IO.File]::WriteAllText(
        $TempFile,
        $NewContent,
        [System.Text.Encoding]::ASCII
    )

    Move-Item -LiteralPath $TempFile -Destination $HostsFile -Force

    ipconfig /flushdns | Out-Null

    Add-Content -LiteralPath $LogFile -Value (
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - LOCK APPLIED"
    )

    Write-Host "SeeUat4 block successfully applied."
    Write-Host "Blocked domains: $($Domains.Count)"
    Write-Host "Backup: $BackupFile"
}
finally {
    if (Test-Path $TempFile) {
        Remove-Item -LiteralPath $TempFile -Force
    }
}
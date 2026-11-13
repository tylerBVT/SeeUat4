$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $ProjectRoot "state"
$LogDir = Join-Path $ProjectRoot "logs"

$ApplyScript = Join-Path $PSScriptRoot "Apply-Block.ps1"
$StatusFile = Join-Path $StateDir "status.json"
$HostsFile = Join-Path $env:SystemRoot "System32\drivers\etc\hosts"
$LogFile = Join-Path $LogDir "SeeUat4.log"

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

New-Item -ItemType Directory -Force -Path $StateDir, $LogDir |
    Out-Null

Write-Host "Applying SeeUat4 block..."

& $ApplyScript

$HostsContent = [System.IO.File]::ReadAllText($HostsFile)

if (
    $HostsContent -notmatch [regex]::Escape("# SEEuat4_START") -or
    $HostsContent -notmatch [regex]::Escape("# SEEuat4_END")
) {
    throw "Block verification failed. Status was not changed."
}

$Status = [PSCustomObject]@{
    mode = "LOCKED"
    unlockedAt = $null
    unlockedBy = $null
}

$Status | ConvertTo-Json |
    Set-Content -LiteralPath $StatusFile -Encoding UTF8

Add-Content -LiteralPath $LogFile -Value (
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - STATUS LOCKED"
)

Write-Host ""
Write-Host "SEE U AT 4 - LOCKED."

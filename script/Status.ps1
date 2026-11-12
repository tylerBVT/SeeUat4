$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $ProjectRoot "state"

$StatusFile = Join-Path $StateDir "status.json"
$HostsFile = Join-Path $env:SystemRoot "System32\drivers\etc\hosts"

Write-Host ""
Write-Host "=============================="
Write-Host "          SeeUat4"
Write-Host "=============================="

if (Test-Path $HostsFile) {
    $Content = [System.IO.File]::ReadAllText($HostsFile)

    $HasStart = $Content.Contains("# SEEuat4_START")
    $HasEnd = $Content.Contains("# SEEuat4_END")

    if ($HasStart -and $HasEnd) {
        Write-Host "Hosts block: PRESENT (sites blocked)"
    }
    elseif (-not $HasStart -and -not $HasEnd) {
        Write-Host "Hosts block: ABSENT (sites not blocked)"
    }
    else {
        Write-Warning "Hosts block: INVALID OR INCOMPLETE"
    }
}
else {
    Write-Warning "Windows Hosts file not found."
}

if (Test-Path $StatusFile) {
    try {
        $Status = Get-Content $StatusFile -Raw | ConvertFrom-Json

        Write-Host "Last recorded mode: $($Status.mode)"
        Write-Host "Last unlocked at: $($Status.unlockedAt)"
    }
    catch {
        Write-Warning "Could not read status.json."
    }
}

Write-Host "=============================="
Write-Host ""
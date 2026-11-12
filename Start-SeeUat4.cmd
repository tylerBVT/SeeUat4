
@echo off
setlocal

set "SEEUAT4_ROOT=%~dp0"

start "SeeUat4 - PowerShell" powershell.exe ^
    -NoLogo ^
    -NoProfile ^
    -NoExit ^
    -ExecutionPolicy Bypass ^
    -Command "Set-Location -LiteralPath $env:SEEUAT4_ROOT"

endlocal





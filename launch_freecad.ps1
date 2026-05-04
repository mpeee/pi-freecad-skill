<#
.SYNOPSIS
    Launch FreeCAD with the remote server pre-configured.

.DESCRIPTION
    - Searches common installation paths for FreeCAD
    - Ensures freecad_server.py is in the FreeCAD Macro folder
    - Configures InitGui.py autostart (once)
    - Launches FreeCAD

    After FreeCAD opens, the server starts automatically in the background.
    No macro menu navigation needed.

.PARAMETER FreeCADPath
    Override the FreeCAD executable path if auto-detection fails.

.PARAMETER MacroSource
    Path to freecad_server.py if not in the default project location.

.EXAMPLE
    .\launch_freecad.ps1
    .\launch_freecad.ps1 -FreeCADPath "D:\Apps\FreeCAD\bin\FreeCAD.exe"
#>

param(
    [string]$FreeCADPath = "",
    [string]$MacroSource = ""
)

$ErrorActionPreference = "Stop"

# ── Find FreeCAD executable ──────────────────────────────────────────────────
if (-not $FreeCADPath) {
    $candidates = @(
        "C:\Program Files\FreeCAD 1.0\bin\FreeCAD.exe",
        "C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe",
        "C:\Program Files\FreeCAD 0.20\bin\FreeCAD.exe",
        "C:\Program Files (x86)\FreeCAD 0.21\bin\FreeCAD.exe",
        "$env:LOCALAPPDATA\Programs\FreeCAD 1.0\bin\FreeCAD.exe",
        "$env:LOCALAPPDATA\Programs\FreeCAD 0.21\bin\FreeCAD.exe"
    )
    # Also scan Program Files for any FreeCAD* folder
    foreach ($base in @("C:\Program Files", "C:\Program Files (x86)")) {
        if (Test-Path $base) {
            Get-ChildItem $base -Directory -Filter "FreeCAD*" | ForEach-Object {
                $candidates += "$($_.FullName)\bin\FreeCAD.exe"
            }
        }
    }
    $FreeCADPath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $FreeCADPath -or -not (Test-Path $FreeCADPath)) {
    Write-Host ""
    Write-Host "ERROR: FreeCAD not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Specify the path manually:"
    Write-Host "  .\launch_freecad.ps1 -FreeCADPath 'C:\path\to\FreeCAD.exe'"
    exit 1
}

Write-Host "FreeCAD: $FreeCADPath" -ForegroundColor Cyan

# ── Locate source macro ───────────────────────────────────────────────────────
if (-not $MacroSource) {
    # Default: relative to this script (project root)
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $MacroSource = Join-Path $scriptDir ".pi\skills\freecad-remote\server\freecad_server.py"
}

if (-not (Test-Path $MacroSource)) {
    Write-Host ""
    Write-Host "ERROR: Server script not found at:" -ForegroundColor Red
    Write-Host "  $MacroSource"
    Write-Host ""
    Write-Host "Run the setup wizard first:  /freecad:setup  (in pi)"
    exit 1
}

# ── Install macro to FreeCAD Macro folder ─────────────────────────────────────
$macroDir = "$env:APPDATA\FreeCAD\Macro"
if (-not (Test-Path $macroDir)) {
    New-Item -ItemType Directory -Path $macroDir -Force | Out-Null
    Write-Host "Created macro folder: $macroDir" -ForegroundColor Yellow
}

$macroTarget = Join-Path $macroDir "freecad_server.py"
Copy-Item $MacroSource $macroTarget -Force
Write-Host "Macro installed: $macroTarget" -ForegroundColor Green

# ── Configure InitGui.py autostart ────────────────────────────────────────────
$initGuiPath = "$env:APPDATA\FreeCAD\InitGui.py"
$marker      = "# FreeCAD Remote Server — auto-start"
$snippet = @"

# FreeCAD Remote Server — auto-start (added by launch_freecad.ps1)
import os as _fc_os
_fc_macro = _fc_os.path.join(_fc_os.path.dirname(__file__), 'Macro', 'freecad_server.py')
if _fc_os.path.exists(_fc_macro):
    exec(open(_fc_macro).read())
del _fc_os, _fc_macro

"@

$existing = if (Test-Path $initGuiPath) { Get-Content $initGuiPath -Raw } else { "" }
if ($existing -notlike "*$marker*") {
    Add-Content -Path $initGuiPath -Value $snippet -Encoding UTF8
    Write-Host "Autostart configured: $initGuiPath" -ForegroundColor Green
} else {
    Write-Host "Autostart already configured." -ForegroundColor Cyan
}

# ── Check firewall ────────────────────────────────────────────────────────────
$rule = Get-NetFirewallRule -DisplayName "FreeCAD Remote Server" -ErrorAction SilentlyContinue
if (-not $rule) {
    Write-Host ""
    Write-Host "Firewall rule missing — creating it now (requires admin)..." -ForegroundColor Yellow
    try {
        New-NetFirewallRule `
            -DisplayName "FreeCAD Remote Server" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort 7978 `
            -Action Allow | Out-Null
        Write-Host "Firewall rule created for port 7978." -ForegroundColor Green
    } catch {
        Write-Host "Could not create firewall rule (not running as admin?)." -ForegroundColor Red
        Write-Host "Run manually as Administrator:"
        Write-Host "  New-NetFirewallRule -DisplayName 'FreeCAD Remote Server' -Direction Inbound -Protocol TCP -LocalPort 7978 -Action Allow"
    }
} else {
    Write-Host "Firewall rule OK (port 7978)." -ForegroundColor Cyan
}

# ── Launch FreeCAD ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Starting FreeCAD..." -ForegroundColor Cyan
Write-Host "The remote server will start automatically." -ForegroundColor Cyan
Write-Host ""
Write-Host "Once FreeCAD is open, check the Report View for:" -ForegroundColor Yellow
Write-Host "  FreeCAD-Server gestartet auf 0.0.0.0:7978" -ForegroundColor Yellow
Write-Host ""
Write-Host "Then in pi, run:  /freecad:status" -ForegroundColor Yellow

Start-Process $FreeCADPath

@echo off
:: launch_freecad.bat — Launch FreeCAD with the remote server
::
:: Double-click this file, or run from CMD:
::   launch_freecad.bat
::
:: Requires PowerShell (included in Windows 10/11).
:: The first run may ask for admin rights to create the firewall rule.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_freecad.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Launch failed. See error above.
    pause
)

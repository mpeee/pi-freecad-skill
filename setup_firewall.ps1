New-NetFirewallRule -DisplayName "FreeCAD Remote Server" -Direction Inbound -Protocol TCP -LocalPort 7978 -Action Allow
Write-Host "Firewall-Regel erstellt. Port 7978 ist jetzt offen."

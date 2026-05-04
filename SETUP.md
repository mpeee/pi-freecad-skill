# FreeCAD Remote — Setup Guide

This guide walks you through the setup wizard step by step.
Open this file alongside pi so you can copy paths and commands when needed.

---

## Before You Start

**You need:**
- FreeCAD installed on Windows (0.21 or 1.0)
- pi coding agent installed on Linux / WSL2
- This project cloned and open in pi

**Start pi from the project directory:**
```bash
cd /path/to/freecad-skill
pi
```

---

## Run the Wizard

In the pi chat, type:
```
/freecad:setup
```

The wizard runs through 6 steps. Most are automatic — you will only be asked a few yes/no questions and one manual action in FreeCAD.

---

## Step 1 — Connection Check

The wizard checks if FreeCAD is already reachable.

| What you see | What it means |
|-------------|---------------|
| *"Already connected! FreeCAD 0.21 at …"* | Server is running. Nothing to do. |
| *(continues to step 2)* | FreeCAD not yet reachable. Setup proceeds. |

---

## Step 2 — Environment Detection

**Automatic.** The wizard detects:
- Whether you are running in WSL2
- Which Windows drives are mounted (`/mnt/c`, `/mnt/d`, …)
- Your Windows username

**Expected output (WSL2):**
```
Environment: WSL2 — Windows drives: c: d:  |  Windows user: yourname
```

**If not in WSL2** (native Linux/macOS):
The wizard cannot access the Windows filesystem automatically.
Skip to [Manual Setup](#manual-setup-without-wizard).

---

## Step 3 — Find FreeCAD + Macro Folder

**Automatic.** The wizard scans:
```
C:\Program Files\FreeCAD*
C:\Program Files (x86)\FreeCAD*
C:\Users\<you>\AppData\Local\Programs\FreeCAD*
```

**If multiple versions are found:** A selection prompt appears — choose the one you want to use.

**Macro folder** is found or created at:
```
C:\Users\<you>\AppData\Roaming\FreeCAD\Macro\
```

> **WSL2 path:** `/mnt/c/Users/<you>/AppData/Roaming/FreeCAD/Macro/`

---

## Step 4 — Install Server Macro

**Automatic.** The wizard copies:
```
.pi/skills/freecad-remote/server/freecad_server.py
    → C:\Users\<you>\AppData\Roaming\FreeCAD\Macro\freecad_server.py
```

**Expected output:**
```
✓ Server macro installed:
  /mnt/c/Users/yourname/AppData/Roaming/FreeCAD/Macro/freecad_server.py
```

**If the copy fails** → see [Manual Setup](#manual-setup-without-wizard).

---

## Step 5 — Windows Firewall

The wizard asks:
```
Firewall Setup
Allow FreeCAD server on port 7978?
This requires administrator privileges in Windows. A UAC prompt may appear.
[Yes] [No]
```

**Confirm with Yes.** A Windows UAC dialog appears asking for administrator permission — accept it.

**Expected output:**
```
✓ Firewall rule created for port 7978
```

**If the UAC prompt does not appear** or the rule fails, run this manually in **Windows PowerShell as Administrator**:
```powershell
New-NetFirewallRule `
  -DisplayName "FreeCAD Remote Server" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 7978 `
  -Action Allow
```

To verify the rule exists later:
```powershell
Get-NetFirewallRule -DisplayName "FreeCAD Remote Server"
```

---

## Step 5b — Autostart (Optional)

The wizard asks:
```
Autostart
Configure FreeCAD to start the server automatically at launch?
This writes a small snippet to FreeCAD's InitGui.py.
[Yes] [No]
```

**Recommended: Yes** — after this, starting FreeCAD is all you ever need to do.

The wizard writes to:
```
C:\Users\<you>\AppData\Roaming\FreeCAD\InitGui.py
```

The added snippet:
```python
# FreeCAD Remote Server — auto-start (added by pi setup wizard)
import os as _fc_os
_fc_macro = _fc_os.path.join(_fc_os.path.dirname(__file__), 'Macro', 'freecad_server.py')
if _fc_os.path.exists(_fc_macro):
    exec(open(_fc_macro).read())
del _fc_os, _fc_macro
```

> **Safe to undo:** Remove the lines above from `InitGui.py` to disable autostart.

---

## Step 6 — Start the Server in FreeCAD

Choose the method that suits you best:

### Option A — Launch Script (easiest, Windows only)

Double-click `launch_freecad.bat` in the project folder,
or run from PowerShell:

```powershell
.\launch_freecad.ps1
```

The script:
- Installs the macro (if not already done)
- Configures autostart via `InitGui.py`
- Creates the firewall rule
- Launches FreeCAD

FreeCAD opens and the server starts automatically. No menu navigation needed.

---

### Option B — FreeCAD Python Console (one line)

1. Open FreeCAD
2. Open the Python Console: **View → Panels → Python Console**
3. Paste and press Enter:

```python
exec(open(FreeCAD.getUserMacroDir(True) + "freecad_server.py").read())
```

The Report View shows:
```
FreeCAD-Server gestartet auf 0.0.0.0:7978
```

> **Copy this line:**
> ```
> exec(open(FreeCAD.getUserMacroDir(True) + "freecad_server.py").read())
> ```

---

### Option C — Macro Menu (original method)

1. **Open FreeCAD** on Windows

2. Open the macro dialog:
   - German UI: **Extras → Makros → Makro ausführen…**
   - English UI: **Tools → Macros → Execute Macro…**

3. Select **`freecad_server.py`** from the list

4. Click **Ausführen / Execute**

---

### After any of the above

FreeCAD **Report View** (bottom panel) shows:
```
FreeCAD-Server gestartet auf 0.0.0.0:7978
```

**Switch back to pi** — the wizard is polling every 2 seconds.

**Expected wizard output:**
```
✓ Connected! FreeCAD 0.21 at 172.x.x.x:7978

Setup complete. You can now use:
  freecad_run        — execute Python in FreeCAD
  freecad_screenshot — capture 3D view
  freecad_script_*   — manage script library
  /freecad:status    — check status anytime
```

The pi footer shows: `⬡ FreeCAD 172.x.x.x:7978`

---

## Verify

After setup, confirm everything works:
```
/freecad:status
```

Expected:
```
✓ Connected — FreeCAD 0.21 at 172.x.x.x:7978
Scripts — project: 0, global: 0
Project dir: /path/to/freecad-skill/fc-scripts
Global dir:  /home/you/.pi/freecad-scripts
```

Quick test:
```
# In pi, the agent will run:
freecad_run("2 + 2")   # → RESULT: 4
```

---

## Manual Setup (without wizard)

Use this if the wizard cannot find your FreeCAD installation or you are not on WSL2.

### 1 — Copy the server macro

**From WSL2:**
```bash
# Replace <you> with your Windows username
cp .pi/skills/freecad-remote/server/freecad_server.py \
   "/mnt/c/Users/<you>/AppData/Roaming/FreeCAD/Macro/"
```

**From Windows (PowerShell):**
```powershell
# Run from the project directory on Windows
Copy-Item ".pi\skills\freecad-remote\server\freecad_server.py" `
  "$env:APPDATA\FreeCAD\Macro\"
```

### 2 — Configure the firewall

In **Windows PowerShell as Administrator**:
```powershell
.\setup_firewall.ps1
```

### 3 — (Optional) Configure autostart

Add to `C:\Users\<you>\AppData\Roaming\FreeCAD\InitGui.py` (create if missing):
```python
# FreeCAD Remote Server — auto-start
import os as _fc_os
_fc_macro = _fc_os.path.join(_fc_os.path.dirname(__file__), 'Macro', 'freecad_server.py')
if _fc_os.path.exists(_fc_macro):
    exec(open(_fc_macro).read())
del _fc_os, _fc_macro
```

### 4 — Run the macro in FreeCAD

**Extras → Makros → Makro ausführen… → freecad_server.py → Ausführen**

### 5 — Set the host manually if needed

Find your Windows IP from WSL2:
```bash
cat /etc/resolv.conf | grep nameserver | awk '{print $2}'
```

Start pi with explicit host:
```bash
FC_HOST=172.x.x.x pi
```

---

## Troubleshooting

### "⬡ FreeCAD offline" in footer

1. Confirm FreeCAD console shows: `FreeCAD-Server gestartet auf 0.0.0.0:7978`
2. Check firewall: `Get-NetFirewallRule -DisplayName "FreeCAD Remote Server"`
3. Find your Windows host IP and set manually:
   ```bash
   cat /etc/resolv.conf | grep nameserver
   # → 172.28.80.1
   FC_HOST=172.28.80.1 pi
   ```

### Wizard times out after 90 seconds

- The server macro did not print the startup message — check the FreeCAD Report View
- Try running the macro again (Extras → Makros → Makro ausführen)
- Run the protocol test to diagnose:
  ```bash
  FC_HOST=<windows-ip> python3 tests/test_protocol.py
  ```

### PowerShell not accessible from WSL2

```bash
which powershell.exe   # should return /mnt/c/Windows/System32/WindowsPowerShell/...
```

If missing, run the firewall rule from Windows directly:
```powershell
# In Windows PowerShell (as Administrator):
New-NetFirewallRule -DisplayName "FreeCAD Remote Server" `
  -Direction Inbound -Protocol TCP -LocalPort 7978 -Action Allow
```

### FreeCAD macro folder not found by wizard

Common locations to check:
```
C:\Users\<you>\AppData\Roaming\FreeCAD\Macro\   ← standard
C:\Users\<you>\Documents\FreeCAD\Macro\          ← alternative
```

From FreeCAD itself:
```python
# In FreeCAD Python console (View → Panels → Python Console):
import FreeCAD
print(FreeCAD.getUserMacroDir())
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `/freecad:setup` | Run the setup wizard |
| `/freecad:status` | Check connection and script library |
| `freecad_run` | Execute Python code in FreeCAD |
| `freecad_screenshot` | Save 3D view as PNG |
| `freecad_script_save` | Save a script to the library |
| `freecad_script_list` | List saved scripts |
| `freecad_script_run` | Run a saved script by name |

| Path | Description |
|------|-------------|
| `C:\Users\<you>\AppData\Roaming\FreeCAD\Macro\` | FreeCAD Macro folder |
| `C:\Users\<you>\AppData\Roaming\FreeCAD\InitGui.py` | FreeCAD autostart file |
| `.pi/skills/freecad-remote/server/freecad_server.py` | Server macro source |
| `./fc-scripts/` | Project script library |
| `~/.pi/freecad-scripts/` | Global script library |

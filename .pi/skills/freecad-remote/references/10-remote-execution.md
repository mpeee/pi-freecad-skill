# Remote Execution — How Code Runs Inside FreeCAD

## Connection Troubleshooting (WSL2)

```powershell
# 1. Verify server listening
netstat -an | Select-String '7978'
# Must show: TCP 0.0.0.0:7978 LISTENING

# 2. Firewall rule (Admin PowerShell)
New-NetFirewallRule -DisplayName "FreeCAD Remote Server" -Direction Inbound -Protocol TCP -LocalPort 7978 -Action Allow -Profile Any -Enabled True

# 3. Portproxy — required in WSL2 NAT mode (Admin PowerShell)
netsh interface portproxy add v4tov4 listenport=7978 listenaddress=0.0.0.0 connectport=7978 connectaddress=127.0.0.1
netsh interface portproxy show all
# Persists across reboots
```

If netstat shows many `CLOSE_WAIT` on port 7978 → server frozen → restart FreeCAD.

## Critical Rules

- **Never raw-socket to port 7978** alongside `freecad_run`. Server is single-threaded; parallel connections freeze it. Only use `freecad_run` / `freecad_script_run` tools.
- **All GUI/FreeCAD calls must run on the Qt main thread.** The server dispatches via Qt signal. Do not bypass.

## Execution Namespace

Pre-available: `App=FreeCAD`, `Gui=FreeCADGui`. Everything else needs explicit import:
```python
import Part, Sketcher, MeshPart, TechDraw, Draft
from FreeCAD import Base  # Base.Vector == App.Vector
```

## File Convention — Everything in Workspace

All screenshots and FCStd saves go in the **current working directory** — never in system paths.
```python
import os
cwd_win = os.getcwd().replace("/mnt/d/","D:/").replace("/mnt/c/","C:/")
view.saveImage(f"{cwd_win}/check.png", 1200, 900, "White")
doc.saveAs(f"{cwd_win}/model.FCStd")
```

## Screenshot

```python
import FreeCADGui
v = FreeCADGui.activeDocument().activeView()
v.viewIsometric(); v.fitAll()
v.saveImage(f"{cwd_win}/check.png", 1200, 900, "White")
```
Take screenshots: after creating solids, after booleans, before saving, when user asks.

## freecad_run vs freecad_script_run

| | freecad_run | freecad_script_run |
|--|------------|-------------------|
| Use for | exploration, one-off, debugging | saved scripts worth reusing |
| Code | inline | from fc-scripts/ library |
| Persists | no | yes |

## Error Handling

Server response fields: `result`, `output`, `stderr`, `error` (traceback or null).

Common errors:
- `NameError: 'Part'` → add `import Part`
- `AttributeError: 'NoneType'` → `App.ActiveDocument` is None, create doc first
- `Part.OCCError` → Boolean failed, check co-planar faces
- `Standard_NullObject` → upstream feature invalid, check DoF=0 and shape.isValid()

Fix: read traceback → fix that exact line → re-run. Document is stateful between calls.

Cleanup bad objects:
```python
doc.removeObject("BadPart"); doc.recompute()
```

## Stateful Execution

Objects added in one `freecad_run` call persist for the next call.
- Clean up test objects explicitly: `doc.removeObject("name")`
- Duplicate names fail silently — check before adding
- Nothing auto-saves: `doc.saveAs(f"{cwd_win}/model.FCStd")`

## result vs output vs _result

```python
"2+2"               # result=4, output=""       — eval path
"x=2+2"             # result=None, output=""    — exec path
"x=2+2; _result=x" # result=4, output=""       — use _result to return from exec
"print('hi')"       # result=None, output="hi\n"
```

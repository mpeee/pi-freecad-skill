---
name: freecad-remote
description: Remote-controls a running FreeCAD instance via a TCP socket server. Use when the user wants to create, modify, or inspect FreeCAD models; read or set object properties; execute Python code or scripts inside FreeCAD; capture screenshots of the 3D view; or get guidance on designing parts for FDM 3D printing (tolerances, orientation, supports, materials). Requires FreeCAD running on Windows with freecad_server.py loaded as a macro.
compatibility: FreeCAD on Windows (host). Python 3 stdlib only on the agent side (Linux/WSL2). Communicates over TCP port 7978.
---

# FreeCAD Remote Skill

## Skill Maintenance Rules

When modifying any file in this skill (SKILL.md, references/*.md):
- **English only** — no other language in skill/reference content
- **Token-efficient** — concise recipes, no prose, no redundancy; prefer tables and code blocks over paragraphs

## Role

You are an **experienced FreeCAD design engineer** with deep expertise in:
- Parametric mechanical design (PartDesign, Part/CSG, Sketcher)
- FDM 3D printing design rules (tolerances, printability, orientation)
- FreeCAD Python scripting and automation

**Act accordingly:**
- Make engineering judgments, not just API calls. When multiple solutions exist,
  choose the one that is structurally sound, stable under parameter changes, and
  manufacturable — then explain why.
- Proactively consider wall thickness, overhangs, load paths, tolerances, and
  feature ordering without waiting to be asked.
- If a requirement is geometrically problematic (wall too thin, unprintable
  overhang, fragile topology reference), flag it and suggest a better approach.
- Use your own FreeCAD, CAD, and 3D-printing knowledge from training. The skill
  references document experience-based traps and empirical data — they complement
  your knowledge, they do not replace it.
- Think step by step: plan roughly, then build and inspect incrementally.

---

## Architecture

```
Agent (pi extension + tools)
  └─ freecad_run / freecad_script_* tools  ──TCP:7978──►  FreeCAD (Windows)
                                                            └─ server/freecad_server.py (Macro)
```

The pi extension (`.pi/extensions/freecad.ts`) connects directly via TCP — no bash wrapper needed.
The CLI (`cli/fc.py`) is available as fallback for the interactive REPL.

## Setup (once)

Run the interactive setup wizard:
```
/freecad:setup
```

The wizard automatically:
- Detects WSL2 and finds mounted Windows drives
- Searches common FreeCAD installation paths (`Program Files`, `AppData/Local/Programs`)
- Finds or creates the FreeCAD Macro folder
- Copies `freecad_server.py` into the Macro folder
- Configures the Windows firewall rule via `powershell.exe`
- Optionally writes an autostart entry to FreeCAD's `InitGui.py`
- Waits up to 90 seconds for the connection and confirms

**The only manual step:** Open FreeCAD → Extras → Macros → Execute freecad_server.py

> If autostart was configured this step is only needed once — subsequent FreeCAD launches start the server automatically.

Manual setup (without wizard):
```bash
# Copy macro, then in FreeCAD: Extras → Macros → Execute freecad_server.py
```

Override host/port if needed:
```bash
FC_HOST=192.168.1.42 FC_PORT=7978
```

## Tools (via Extension)

The extension registers these tools — prefer them over the CLI for all scripted work:

| Tool | Use |
|------|-----|
| `freecad_run` | Execute Python code in FreeCAD. `App`/`FreeCAD` are pre-available; everything else needs `import` |
| `freecad_screenshot` | Save 3D view as PNG to a Windows path |
| `freecad_script_save` | Save a script to the library (project or global scope) |
| `freecad_script_list` | List all scripts in the library with descriptions |
| `freecad_script_run` | Execute a named script from the library in FreeCAD |
| `freecad_script_show` | Print source code of a named script |
| `freecad_script_delete` | Remove a script from the library |

Command: `/freecad:status` — connection check + library stats shown in footer.

## Script Library

Two scopes — choose based on reusability:

| Scope | Location | Use for |
|-------|----------|---------|
| `project` | `<cwd>/fc-scripts/` | Part scripts tied to this project; git-trackable |
| `global` | `~/.pi/freecad-scripts/` | Reusable utilities across all projects |

Project scope takes precedence when a name exists in both.
Each scope has `_index.json` with name, description, and timestamps.

**Naming:** `snake_case` — e.g. `part_housing`, `util_validate`, `fixture_mount_plate`

**Temporary scripts** (one-off): use `freecad_run` inline — these do not persist.

## Execution Context

Inside FreeCAD, code runs in this namespace — **everything else must be imported**:
```python
App = FreeCAD    # always available
Gui = FreeCADGui # always available

# Must import explicitly:
import Part
import Sketcher
```

## Workflow Pattern

1. `/freecad:status` — verify connection
2. `freecad_run` with inspection code — understand current document state
3. `freecad_run` or `freecad_script_run` — create / modify geometry
4. For OpenSCAD / NopSCADlib workflows: load `nopscadlib_bridge` from the script library, render via OpenSCAD, then inspect imported geometry
5. `freecad_screenshot` — visual verification
6. `freecad_script_save` — persist any script worth keeping

## FreeCAD Python API Essentials

```python
doc = App.newDocument("Name")          # create document
doc = App.ActiveDocument               # get active document
obj = doc.addObject("Part::Box", "Box")
obj = doc.getObject("Box")
obj.Length = 100.0
doc.recompute()                        # always call after changes
doc.saveAs("/path/to/file.FCStd")

for o in doc.Objects:
    print(o.Name, o.TypeId, o.Label)
```

## File Convention: Everything in the Workspace

All temporary files (screenshots, FCStd saves) belong in the **current working
directory** — the folder from which the pi session was started.
Never use system paths like `C:/Users/Public`, `D:/temp`, or `/tmp`.

```python
import os
# Convert Linux/WSL path to Windows path
cwd_win = os.getcwd().replace("/mnt/d/", "D:/").replace("/mnt/c/", "C:/")

# Screenshot:
view.saveImage(f"{cwd_win}/check.png", 1200, 900, "White")

# Save model:
doc.saveAs(f"{cwd_win}/mymodel.FCStd")
```

## Capturing Hard-Won Insights

After any session where modeling was difficult (wrong constraints, API surprises, coordinate confusion, freezes):

- Write the solution immediately as a concrete recipe in `references/13-core-patterns.md`
- Format: "to achieve X, do Y" — not API docs, not prose
- The skill improves only through real modeling experience

## Knowledge Base

Load a reference file only when the task requires it — do not load all at once.

### Core References (experience-based, not in model training)

These files contain knowledge that is **not reliably in model training**:
experience-based patterns, known API traps, workflow recipes validated against
198 real FreeCAD files, and remote execution setup.

| File | Load when… |
|------|-----------|
| [references/14-dsl-generator.md](references/14-dsl-generator.md) | **Always load first** — DSL/JSON approach avoids Sketcher complexity; LLM outputs JSON, generator builds the model |
| [references/15-openscad-nopscadlib.md](references/15-openscad-nopscadlib.md) | OpenSCAD / NopSCADlib workflow: library detection, render/import bridge, when mesh-vs-shape is acceptable |
| [references/00-decision-guide.md](references/00-decision-guide.md) | Planning which approach to use, or exploring an existing document for the first time |
| [references/08-robustness.md](references/08-robustness.md) | Model breaks, Boolean failures, Topological Naming Problem, validating shapes |
| [references/10-remote-execution.md](references/10-remote-execution.md) | Execution context, error handling, screenshot workflow, stateful sessions, WSL2 connection troubleshooting |
| [references/13-core-patterns.md](references/13-core-patterns.md) | **Always load for PartDesign/Sketcher work** — workflow discipline, coordinate systems, attachment offset, known API traps, build rules, constraint cheatsheet |
| [references/11-sketcher-python.md](references/11-sketcher-python.md) | **Always load for any Sketcher work** — full constraint syntax, verified centering patterns, circles/arcs, external geometry |
| [references/13-feature-recipes.md](references/13-feature-recipes.md) | Specific feature syntax: thread (Helix+Sweep), AdditivePipe, Groove, Loft, MultiTransform, ShapeBinder, SubShapeBinder, tutorial patterns |
| [references/09-cad-best-practices.md](references/09-cad-best-practices.md) | Feature ordering, parametric stability, empirical data from tutorial scan |
| [references/12-3d-print-design.md](references/12-3d-print-design.md) | FDM design: resolution systems, wall thickness rules, support-free design |
| [references/06-python-api.md](references/06-python-api.md) | Import/Export (STEP/STL), face coloring, geometry search, placement math |

### Background References (load only if uncertain)

These files contain **general FreeCAD knowledge** that a capable model already
knows from training. Only load if genuinely unsure or when using a weaker model.

| File | Load when… |
|------|-----------|
| [references/background/01-concepts.md](references/background/01-concepts.md) | Unsure about FreeCAD fundamentals: document, DAG, workbenches |
| [references/background/02-sketcher.md](references/background/02-sketcher.md) | Need reminder on Sketcher concepts: constraints, fully constrained |
| [references/background/03-partdesign.md](references/background/03-partdesign.md) | Need reminder on PartDesign: Pad/Pocket/Revolution feature tree |
| [references/background/04-part-csg.md](references/background/04-part-csg.md) | Need reminder on Part/CSG: primitives, Boolean ops |
| [references/background/05-spreadsheet-expressions.md](references/background/05-spreadsheet-expressions.md) | Need reminder on expression syntax and spreadsheet API |
| [references/background/07-techdraw.md](references/background/07-techdraw.md) | Generating 2D drawings, dimensions, PDF/SVG export |

## CLI (fallback)

Use `cli/fc.py` only when extension tools are insufficient (e.g. interactive REPL):

```bash
python3 cli/fc.py console              # interactive REPL inside FreeCAD
python3 cli/fc.py run "<expr>"         # quick one-liner with --json flag
```

## Environment Variables

- `FC_HOST` — FreeCAD host IP (auto-detected in WSL2 via `/etc/resolv.conf`)
- `FC_PORT` — port, default `7978`

## Error Handling

- `freecad_run` returns `isError: true` when FreeCAD raises an exception — read the traceback
- Connection timeout → server macro not running, or Windows firewall blocking port 7978
- `_result` variable in `exec`-ed multi-statement code is returned as the result value

## Tutorial Repositories

Clone these repos on a new machine to have example files and learning material.
FCStd files can be read without FreeCAD by unzipping and parsing `Document.xml`.

```bash
# BPLRFE YouTube Tutorial Models (38 files, Tutorial 01–30)
# Topics: PartDesign, threads (Helix+Sweep), bearings, propeller, spreadsheet, animation
git clone https://github.com/BPLRFE/Youtube-Tutorial-Models

# FreeCAD Official Examples (198 files)
# Topics: 100 CAD exercises (2D+3D), PartDesign tutorial, Sketcher, TechDraw, Attachment
git clone https://github.com/FreeCAD/Examples.git FreeCAD-Examples
```

| Repository | Contents | Most valuable |
|-----------|----------|---------------|
| BPLRFE/Youtube-Tutorial-Models | T01–T30, complete parts | T08/T09 threads (Helix+Sweep), T06 spring, T12 bearing |
| FreeCAD/Examples | 100CadExercises, Basic_Part_Design_Tutorial, AttachmentTutorial | 3D-19 Groove, 3D-15 AdditivePipe, 3D-35 Loft, ShapeBinder |

### Quick scan without FreeCAD

```python
import zipfile, xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

def scan_types(path):
    with zipfile.ZipFile(path) as zf:
        with zf.open("Document.xml") as f:
            root = ET.parse(f).getroot()
    return Counter(o.get("type","") for o in root.findall(".//Objects/Object"))

for f in Path("FreeCAD-Examples").rglob("*.fcstd"):
    types = scan_types(f)
    if "PartDesign::Groove" in types:
        print(f.name, dict(types))
```

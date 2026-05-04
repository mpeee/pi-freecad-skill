# FreeCAD Remote — pi Skill & Extension

Control a running FreeCAD instance with natural language via the [pi coding agent](https://github.com/badlogic/pi-coding-agent).

```
You (chat) → pi agent → freecad_run tool → TCP:7978 → FreeCAD (Windows)
                                                         └─ freecad_server.py macro
```

---

## What This Is

A **pi skill + extension** that lets an LLM agent:

- Create, modify, and inspect 3D models in FreeCAD via Python
- Manage a persistent script library (project-local and global)
- Take screenshots of the 3D view for visual verification
- Work with a built-in knowledge base covering FreeCAD concepts, best practices, and the Python API

**Typical interactions:**

> *"Create a parametric box 100×50×30mm with a 10mm hole centred on the top face"*  
> *"The wall thickness in the active document should be 22mm — check and fix it"*  
> *"Save the current model and export it as STEP"*  
> *"Show me all objects in the open document and their bounding boxes"*

---

## Requirements

| Component | Where |
|-----------|-------|
| **FreeCAD 0.21 or 1.0** | Windows (the 3D application) |
| **pi coding agent** | Linux / WSL2 / macOS (the agent host) |
| **Python 3** | On the agent host — stdlib only, no extra packages |
| TCP port **7978** | Reachable from agent host to Windows (WSL2: auto-detected) |

---

## Installation

### 1 — Install pi

Follow the [pi coding agent installation guide](https://github.com/badlogic/pi-coding-agent).

```bash
npm install -g @mariozechner/pi-coding-agent
```

### 2 — Clone this repository

```bash
git clone https://github.com/youruser/freecad-skill.git
cd freecad-skill
```

Or copy the `.pi/` directory into any existing project where you work with FreeCAD files.

### 3 — Start FreeCAD with the server

**Option A — Launch script (easiest):** Double-click `launch_freecad.bat`
or run from PowerShell:
```powershell
.\launch_freecad.ps1
```
This installs the macro, configures autostart, creates the firewall rule, and opens FreeCAD — server starts automatically.

**Option B — Python console one-liner:**
Open FreeCAD → **View → Panels → Python Console**, paste:
```python
exec(open(FreeCAD.getUserMacroDir(True) + "freecad_server.py").read())
```

**Option C — Macro menu:**
Extras → Makros → Makro ausführen → `freecad_server.py` → Execute

See [SETUP.md](SETUP.md) for detailed step-by-step instructions.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FC_HOST` | auto-detect | FreeCAD host IP. Set if auto-detection fails |
| `FC_PORT` | `7978` | TCP port |

```bash
FC_HOST=192.168.1.42 pi
```

---

## Project Structure

```
freecad-skill/
│
├── .pi/
│   ├── extensions/
│   │   └── freecad.ts              # pi extension: tools + script library
│   │
│   └── skills/freecad-remote/
│       ├── SKILL.md                # Skill entry point + knowledge base index
│       ├── server/
│       │   └── freecad_server.py   # FreeCAD macro (run inside FreeCAD)
│       ├── cli/
│       │   └── fc.py               # CLI fallback (interactive REPL etc.)
│       └── references/
│           ├── 00-decision-guide.md    Which approach when; explore workflow
│           ├── 01-concepts.md          Document, DAG, workbenches
│           ├── 02-sketcher.md          Constraints, fully constrained sketches
│           ├── 03-partdesign.md        Pad, Pocket, feature-based modeling
│           ├── 04-part-csg.md          Primitives, Boolean ops, Python geometry
│           ├── 05-spreadsheet-expressions.md  Parametric variables
│           ├── 06-python-api.md        FreeCAD Python API cheat sheet
│           ├── 07-techdraw.md          2D drawings, dimensions, export
│           ├── 08-robustness.md        Failure modes, TNP, validation
│           ├── 09-cad-best-practices.md  Engineering best practices
│           ├── 10-remote-execution.md  Execution context, error handling
│           └── 11-sketcher-python.md   Sketcher constraint API reference
│
├── fc-scripts/                     # Project-local script library (auto-created)
│   └── _index.json
│
├── server/freecad_server.py        # Standalone copy of the macro (original)
├── cli/fc.py                       # Standalone CLI (original)
├── setup_firewall.ps1              # Windows firewall setup
└── README.md
```

---

## Tools Available to the Agent

Once the skill is loaded, the agent has these tools:

| Tool | Purpose |
|------|---------|
| `freecad_run` | Execute any Python code in FreeCAD |
| `freecad_screenshot` | Save 3D view as PNG to a Windows path |
| `freecad_script_save` | Save a script to the library |
| `freecad_script_list` | List saved scripts |
| `freecad_script_run` | Run a saved script by name |
| `freecad_script_show` | Print script source code |
| `freecad_script_delete` | Remove a script from the library |

### Script Library

Scripts are stored in two scopes:

| Scope | Location | Use for |
|-------|----------|---------|
| `project` | `./fc-scripts/` | Project-specific scripts, git-trackable |
| `global` | `~/.pi/freecad-scripts/` | Reusable utilities across projects |

---

## Knowledge Base

The skill includes 12 reference files loaded on demand — the agent reads only what the current task requires:

| Reference | Topic |
|-----------|-------|
| `00-decision-guide` | Which modeling approach to use, how to explore existing documents |
| `01-concepts` | FreeCAD document, parametric DAG, workbench overview |
| `02-sketcher` | Sketcher constraints, fully constrained sketches |
| `03-partdesign` | Feature-based solid modeling workflow |
| `04-part-csg` | Part workbench, CSG, Python geometry from scratch |
| `05-spreadsheet-expressions` | Parametric variables, named cells, expressions |
| `06-python-api` | Full Python API cheat sheet |
| `07-techdraw` | 2D technical drawings |
| `08-robustness` | Common failure modes, Topological Naming Problem |
| `09-cad-best-practices` | Engineering design principles, revision management |
| `10-remote-execution` | Execution namespace, error handling, screenshots |
| `11-sketcher-python` | Sketcher constraint syntax for Python scripting |
| `12-3d-print-design` | FDM design rules: orientation, tolerances, supports, flexures, fasteners, materials |

---

## CLI Fallback

The CLI (`cli/fc.py`) is still available for interactive use independent of pi:

```bash
# Check connection
python3 .pi/skills/freecad-remote/cli/fc.py status

# Interactive REPL inside FreeCAD
python3 .pi/skills/freecad-remote/cli/fc.py console

# Quick one-liner
python3 .pi/skills/freecad-remote/cli/fc.py run "App.ActiveDocument.Name"
```

---

## Troubleshooting

**`⬡ FreeCAD offline` in footer**
- Verify the server macro is running in FreeCAD (console shows the startup message)
- Check Windows firewall: port 7978 TCP inbound must be allowed (`setup_firewall.ps1`)
- Set `FC_HOST` explicitly if auto-detection fails: `FC_HOST=<windows-ip> pi`

**`NameError: name 'Part' is not defined`**
- Always add `import Part` at the top of code sent to FreeCAD — only `App` and `FreeCAD` are pre-available

**Boolean operation produces invalid shape**
- Extend cutting tools 1–2 mm past the target surface to avoid co-planar face failures

**Sketch breaks after adding a feature**
- This is the Topological Naming Problem — see `references/08-robustness.md`
- Attach sketches to datum planes, not model faces

---

## Testing

### Offline Tests (no FreeCAD required)

Tests the TCP protocol and the script library logic using a mock server:

```bash
./tests/run_tests.sh
```

This runs:
- **Protocol tests** (`tests/test_protocol.py`) — sends real JSON over TCP to the mock server, verifies all response patterns
- **Script library tests** (`tests/test_script_library.py`) — unit tests for save/load/list/find/delete logic with a temp directory

### Live Tests (real FreeCAD required)

Load the `freecad-tests` skill in pi and run the full showcase suite:

```bash
pi
# then in pi:
/skill:freecad-tests
```

The test skill instructs the agent to run 7 scenario groups against your running FreeCAD instance:

| Scenario | Tests |
|----------|-------|
| T01 Basic Execution | eval, exec, print, NameError, import |
| T02 Document & Objects | create box, validate BoundBox, isValid |
| T03 CSG Boolean | box.cut(cylinder), validate solid |
| T04 Spreadsheet Parameters | alias-driven dimensions, live update |
| T05 Script Library | save → list → run → show → delete |
| T06 Error Recovery | bad code, session survives |
| T07 Screenshot | PNG written to Windows filesystem |

Validation is **programmatic** — the agent runs `freecad_run` with assertion code and checks actual values against expected values. Results are collected into a pass/fail summary table.

### Test File Structure

```
tests/
├── mock_server.py          # Simulates freecad_server.py (no FreeCAD needed)
├── test_protocol.py        # TCP protocol tests against mock or real server
├── test_script_library.py  # Unit tests for script library helpers
└── run_tests.sh            # Runs all offline tests

.pi/skills/freecad-tests/
└── SKILL.md                # Live test suite for the pi agent
```

### Running protocol tests against real FreeCAD

```bash
FC_HOST=<windows-ip> python3 tests/test_protocol.py
```

---

## Related

- [pi coding agent](https://github.com/badlogic/pi-coding-agent) — the agent harness this runs on
- [Agent Skills standard](https://agentskills.io/specification) — the skill format used
- [FreeCAD documentation](https://wiki.freecad.org/Main_Page)
- [FreeCAD Python API](https://wiki.freecad.org/Power_users_hub)

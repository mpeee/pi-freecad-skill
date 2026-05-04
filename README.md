# pi-freecad-skill

A prototype skill that lets the **Pi AI assistant** remote-control [FreeCAD](https://www.freecad.org/) through a lightweight REST API.

---

## Overview

```
┌──────────────┐   HTTP (JSON)   ┌──────────────────────┐   Python API   ┌─────────────┐
│  Pi / client │ ─────────────▶ │  Skill server        │ ─────────────▶ │  FreeCAD    │
│  (AI agent)  │ ◀───────────── │  server.py           │ ◀───────────── │  (3-D CAD)  │
└──────────────┘                 └──────────────────────┘                └─────────────┘
                                         │
                                  freecad_bridge.py
                                  (real or mock mode)
```

The skill server exposes a set of REST endpoints.  When FreeCAD is running and its Python bindings are available the server drives FreeCAD directly.  Without FreeCAD (e.g. in CI) the bridge falls back to an in-memory **mock/simulation mode** so the API can still be exercised and tested.

---

## Files

| File | Purpose |
|---|---|
| `server.py` | HTTP skill server (stdlib only, no extra dependencies) |
| `freecad_bridge.py` | FreeCAD interface – real bindings or mock fallback |
| `skill.json` | Skill manifest – capabilities, endpoints, parameters |
| `requirements.txt` | Runtime dependencies (none required; pytest for dev) |
| `tests/test_server.py` | Unit + integration tests (run without FreeCAD) |

---

## Quick Start

### Option A – Run inside FreeCAD (live mode)

1. Open FreeCAD and create or open a document.
2. Open the **Macro editor** (`Macro → Macros…`).
3. Paste or load `server.py` and execute it.
4. The server starts on `http://127.0.0.1:5000` and drives FreeCAD directly.

### Option B – Run standalone (simulation/mock mode)

No FreeCAD installation required:

```bash
python3 server.py               # default: 127.0.0.1:5000
python3 server.py --port 8080   # custom port
```

---

## API Reference

All responses are JSON.  Default base URL: `http://127.0.0.1:5000`.

### Health & info

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/info` | Skill metadata and endpoint list |

### Document

| Method | Path | Description |
|--------|------|-------------|
| GET | `/document` | Current document state (name + object list) |
| POST | `/document/reset` | Clear document. Body: `{ "name": "MyDoc" }` |

### Objects

| Method | Path | Description |
|--------|------|-------------|
| GET | `/objects` | List all objects in the document |
| POST | `/objects/box` | Create a box. Body: `{ "name", "length", "width", "height" }` |
| POST | `/objects/sphere` | Create a sphere. Body: `{ "name", "radius" }` |
| POST | `/objects/cylinder` | Create a cylinder. Body: `{ "name", "radius", "height" }` |
| POST | `/objects/cone` | Create a cone. Body: `{ "name", "radius1", "radius2", "height" }` |
| DELETE | `/objects/<name>` | Remove a named object |

All numeric dimensions are in **millimetres**.

---

## Example Session

```bash
# Health check
curl http://127.0.0.1:5000/health
# {"status": "ok", "mock": true}

# Create a 30 × 20 × 10 mm box
curl -X POST http://127.0.0.1:5000/objects/box \
     -H "Content-Type: application/json" \
     -d '{"name": "MyBox", "length": 30, "width": 20, "height": 10}'

# Create a sphere with radius 15 mm
curl -X POST http://127.0.0.1:5000/objects/sphere \
     -H "Content-Type: application/json" \
     -d '{"name": "Ball", "radius": 15}'

# List all objects
curl http://127.0.0.1:5000/objects

# Delete an object
curl -X DELETE http://127.0.0.1:5000/objects/MyBox
```

---

## Running the Tests

```bash
pip install pytest            # one-time setup
python3 -m pytest tests/ -v
```

All 24 tests run in mock mode and require no FreeCAD installation.

---

## Skill Manifest

`skill.json` describes every capability so that the Pi assistant can discover and call them automatically:

```json
{
  "name": "pi-freecad-skill",
  "version": "0.1.0",
  "base_url": "http://127.0.0.1:5000",
  "capabilities": [...]
}
```

---

## Extending the Skill

To add a new shape or operation:

1. Add a method to `FreeCADBridge` in `freecad_bridge.py` (both real and mock paths).
2. Add a route in `server.py` (`do_POST` / `do_GET` / `do_DELETE`).
3. Add an entry in `skill.json` under `capabilities`.
4. Add tests in `tests/test_server.py`.

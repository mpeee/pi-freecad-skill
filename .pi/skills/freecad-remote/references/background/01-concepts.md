# FreeCAD Core Concepts

## Document
- `.FCStd` is a zip archive; contains all objects, history, and parameters
- Multiple documents can be open simultaneously; one is active
- Every object has:
  - **Name** — unique, immutable, auto-assigned (e.g. `Pad001`). Use this in `getObject()` and expressions
  - **Label** — editable, not unique. Never use in expressions (ambiguous)
- `doc.recompute()` is NOT automatic from Python — always call it after changes
- Objects marked with a blue icon in the tree have pending recomputation

## Parametric DAG
- FreeCAD tracks dependencies as a Directed Acyclic Graph
- Dependency flows in one direction only — **circular dependencies crash FreeCAD**
- If A depends on B, B must not depend on A (directly or transitively)
- `Tools → Dependency graph` visualises the DAG — use it to debug broken models
- When a parent changes, all downstream children must be recomputed

## Workbenches
| Workbench | Purpose |
|-----------|---------|
| **PartDesign** | Feature-based solid modeling from sketches — preferred for mechanical parts |
| **Part** | CSG Boolean operations on primitives; direct geometry scripting |
| **Sketcher** | 2D constrained profiles used as input for PartDesign/Part |
| **Spreadsheet** | Parameter tables; drive model dimensions from named cells |
| **TechDraw** | 2D technical drawings with dimensions from 3D models |

## Two Modeling Paradigms

### PartDesign (feature-based) — preferred for mechanical parts
- All features live inside one **Body** container
- Build a single solid by stacking additive/subtractive features on top of each other
- Every feature is based on a Sketch attached to a face or datum plane
- Model tree = modeling history; any step can be edited or reordered

### Part / CSG
- Start with primitives (Box, Cylinder, Sphere …)
- Combine with Boolean ops: Fuse, Cut, Common
- Best for: quick geometry, scripted shapes, geometry not suited to sketch workflow
- **Do not mix Part and PartDesign objects inside one Body**

## Object State Check (Python)
```python
for obj in doc.Objects:
    if hasattr(obj, 'Shape') and obj.Shape.isNull():
        print(f"NULL shape: {obj.Name}")
    if "Invalid" in getattr(obj, "State", []):
        print(f"Invalid: {obj.Name}")
```

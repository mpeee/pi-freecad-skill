# Robustness — How to Avoid Fragile and Broken Models

## Most Common Failure Modes

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Sketch detaches after edit | Sketch attached to face that got renamed (TNP) | Always attach to datum planes, not faces |
| Boolean op fails silently | Co-planar faces in Fuse/Cut | Extend cutter 1–2 mm past target surface |
| Circular dependency error | A → B → A | Redesign DAG; use separate read/write spreadsheets |
| Over-constrained sketch | Redundant constraint added after geometry changed | Remove auto-added constraints; check DoF = 0 |
| Under-constrained sketch | Missing constraints | Fully constrain before leaving sketch edit mode |
| Feature breaks on reorder | Feature referenced a face by index that shifted | Use Named Constraints and Datum Planes |
| `recompute()` silently skips | Parent object invalid; dependency chain broken | Check `obj.State` for `"Invalid"` |
| Expression unit mismatch | Mixed dimensioned/dimensionless values | Always add `mm`, `deg`, etc. to literal numbers in expressions |
| Null shape on export | Boolean failure produced empty solid | Call `shape.isValid()` before saving |

## The Topological Naming Problem (TNP)
When you add, remove, or reorder features, FreeCAD may rename internal face/edge identifiers.
Any sketch or feature that was attached by face name will break.

**Mitigation:**
- Attach all sketches to **datum planes** (`PartDesign → Datum Plane`)
- Reference only the origin planes (XY, XZ, YZ) for the first sketch; create offsets as datum planes
- Never attach a sketch to a face if you might add features between the sketch and that face later

## Golden Rules

1. **Fully constrain every sketch** — sketch turns green, DoF = 0
2. **Attach sketches to datum planes, not model faces**
3. **One Body, one component** — never mix Part and PartDesign objects inside a Body
4. **Centralise all dimensions in a Spreadsheet** with named aliases
5. **Name everything** before building on it: Body, sketches, features, aliases — rename immediately
6. **Dependency flows one way** — upstream to downstream, never circular
7. **Extend Boolean cutters past the target surface** — avoid co-planar OpenCascade failures
8. **Call `doc.recompute()` after every change** — check for `Invalid` state after
9. **Test after each feature** — catch breaks early, don't stack 20 features then recompute
10. **Dress-ups (Fillet/Chamfer) always last** — they're most likely to break on model changes

## Validate a Model in Python
```python
doc.recompute()
errors = []
for obj in doc.Objects:
    state = getattr(obj, "State", [])
    if "Invalid" in state:
        errors.append(f"Invalid: {obj.Name} ({obj.Label})")
    if hasattr(obj, "Shape"):
        if obj.Shape.isNull():
            errors.append(f"Null shape: {obj.Name}")
        elif not obj.Shape.isValid():
            errors.append(f"Invalid shape: {obj.Name}")

if errors:
    for e in errors: print(e)
else:
    print("All objects valid")
```

## Stripping History (for export / reuse)
When sharing or embedding a finished part, strip its parametric history to avoid carrying fragile references:
```python
import Part

# Option A: Create a simple static copy (no history, no expressions)
original = doc.getObject("MyBody")
copy_shape = original.Shape.copy()
static = doc.addObject("Part::Feature", "MyBody_Static")
static.Shape = copy_shape
doc.recompute()

# Option B: Export as STEP and re-import
# File → Export → .step  →  re-import into a new document
```

## Checking Boolean Results
```python
result = shape_a.cut(shape_b)
print(result.isValid())       # must be True
print(len(result.Solids))     # should be ≥ 1 for a usable solid
print(result.isNull())        # must be False
```

## Debugging a Broken Model
```python
# 1. Find broken objects
for obj in doc.Objects:
    print(obj.Name, getattr(obj, "State", []))

# 2. Inspect shape of a specific object
obj = doc.getObject("Pad001")
print(obj.Shape.ShapeType)
print(obj.Shape.isValid())
print(obj.Shape.BoundBox)

# 3. Force recompute of single object
obj.touch()
doc.recompute()
```

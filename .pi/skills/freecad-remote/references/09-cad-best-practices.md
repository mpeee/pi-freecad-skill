# CAD Best Practices

## Feature Order (empirical — 198 FreeCAD tutorial files)

Most common sequences:
```
Body → Pad (113x)         ← first feature always Pad or Revolution
Pad → Pad (101x)          ← stack additive
Pad → Pocket (80x)        ← then subtract
Pocket → Pocket (67x)
Pad/Pocket → Fillet (20x) ← dress-up last
Pad → Mirrored (20x)      ← pattern after base
Revolution → Pocket (17x)
Pocket → Mirrored (16x)   ← pocket before mirror, not after
```

Stable axis references used in tutorials:
```
Revolution → Sketch.V_Axis (56x)
Mirrored   → Sketch.Axis   (51x)
PolarPattern → Sketch.Axis (21x)
LinearPattern → Sketch.Axis (13x)
```

What precedes Fillet/Chamfer: Pad (25x), Pocket (18x), Fillet (17x), PolarPattern (6x)
→ Fillets stack: one group of edges, then another Fillet for more edges.

**Golden rule (data-confirmed):**
1. Base Pad or Revolution — attach to XY/YZ/XZ plane
2. More Pads — datum planes, never faces
3. Pockets and holes — datum planes
4. Patterns and Mirrored — sketch axes
5. Fillet → Chamfer — last, stacking allowed

## Sketch Attachment Strategy (empirical)

| Strategy | Count | Share | Stability |
|----------|-------|-------|-----------|
| → Datum plane (XY/XZ/YZ) | 412 | 90.4% | ✅ stable |
| → Custom DatumPlane | 11 | 2.4% | ✅ stable |
| → Feature face | 44 | 9.6% | ⚠️ fragile (TNP) |
| → Edge (NormalToEdge) | 2 | 0.4% | ⚠️ fragile |

Dominant plane: XY_Plane (64%), XZ_Plane (10%), YZ_Plane (9%), custom datum (5%).
Face references are the #1 cause of TNP failures.

## Reference Hierarchy

```
Origin planes (XY, XZ, YZ)   ← most stable
  └─ Datum planes             ← explicit, stable
       └─ Base sketch          ← first solid feature
            └─ Feature sketches ← reference datum planes only
                 └─ Pockets, holes, patterns
                      └─ Fillets, Chamfers  ← most fragile, always last
```

Rules:
- Sketch → datum plane or origin plane — never to a model face
- Face names change on feature reorder → TNP
- Base sketch: reference only origin planes, fully symmetric where possible

## Design Intent

Before modeling, define:
- Critical dimensions (→ Spreadsheet aliases)
- What can change (material, wall thickness, bolt pattern)
- What is fixed (interfaces, standard parts)
- Relation to adjacent parts

Implement: critical dims → Spreadsheet; interfaces → constrained first as anchors; shared dims → master sketch or top-down Spreadsheet.

## Parametric Variables

All changeable dimensions in a Spreadsheet, not in sketches.
```python
ss.set("B1","3 mm"); ss.setAlias("B1","wall")
obj.setExpression("Length","Params.wall")
# Never read and write same object from same spreadsheet (circular dep)
```

## Boolean Operations — Avoid Co-Planar Faces

Extend cutter 1–2 mm past target on both sides:
```python
# Bad: cutter flush with target at Z=5
cutter = Part.makeBox(10,10,5, App.Vector(0,0,0))
# Good: extends past
cutter = Part.makeBox(10,10,7, App.Vector(0,0,-1))  # -1 to +6
```

## Naming

Name immediately, before building on top. Rename after = update all references.
```
Body_HousingLid / Sketch_BaseProfile / Pad_BaseBlock / Pocket_MountingHoles / Params
```

## Validation

```python
doc.recompute()
for obj in doc.Objects:
    if "Invalid" in getattr(obj,"State",[]):
        print(f"BROKEN: {obj.Name}")
    if hasattr(obj,"Shape"):
        if obj.Shape.isNull(): print(f"NULL: {obj.Name}")
        elif not obj.Shape.isValid(): print(f"INVALID: {obj.Name}")
```

## Checklists

**Before modeling:**
```
[ ] Critical dims identified → Spreadsheet
[ ] Naming scheme decided
[ ] Document units set
[ ] Base sketch → origin/datum plane
```

**During modeling:**
```
[ ] Each sketch: DoF=0 (green)
[ ] Geometric constraints before dimensional
[ ] Recompute + BoundBox check after each feature
[ ] No magic numbers — all from Params
[ ] Fillet/Chamfer deferred to end
```

**Before handoff:**
```
[ ] recompute() → no Invalid, no Null shapes
[ ] BoundBox matches expected dims
[ ] Standard parts are static copies (no history)
[ ] Export tested (STEP/STL)
```

# Decision Guide

Load when: planning approach, or exploring an existing document for the first time.

## Which Approach?

```
CREATE geometry:
  Simple / no edit history needed  → Part/CSG (primitives + boolean)
  User-editable parametric history → PartDesign (Pad/Pocket/Revolution)

MODIFY existing model → explore first, then targeted change
READ/INSPECT          → explore workflow below
GENERATE 2D drawing   → TechDraw
```

## Part/CSG vs PartDesign

| | Part/CSG | PartDesign |
|--|---------|-----------|
| Python scripting | ✅ simple | ✅ workable (load 13-core-patterns.md) |
| User edits later | ❌ no history | ✅ full history |
| Complex booleans | ✅ natural | ⚠️ awkward |
| Sketch profiles | ⚠️ manual Wire/Face | ✅ native |
| Patterns/mirrors | ⚠️ manual | ✅ built-in |
| Speed | ✅ faster | ⚠️ more setup |

Rule: use Part/CSG for scripted geometry. PartDesign only when the user needs editable history.

## Part/CSG Additional Types (from tutorials)

| Type | Use | Tutorial |
|------|-----|---------|
| `Part::MultiCommon` | intersection of shapes (Box ∩ Sphere = rounded box) | T03 |
| `Part::MultiFuse` | union of multiple shapes in one step | T07,T13,T15 |
| `Part::Helix` | helix path for Sweep | T06,T08,T09 |
| `Part::Sweep` | sweep profile along path (Frenet=True for auto-orient) | T06–T09 |
| `Part::Thickness` | solid → hollow shell | T21 |
| `Part::Extrusion` | extrude in arbitrary direction | T13 |
| `PartDesign::PolarPattern` | N-fold rotation pattern | T13 |

## Explore Existing Document

```python
# 1. List all objects
for o in App.ActiveDocument.Objects:
    print(o.Name, o.TypeId, o.Label, getattr(o,'State',[]))

# 2. Find by type
bodies   = [o for o in doc.Objects if o.TypeId=="PartDesign::Body"]
sketches = [o for o in doc.Objects if o.TypeId=="Sketcher::SketchObject"]
sheets   = [o for o in doc.Objects if o.TypeId=="Spreadsheet::Sheet"]

# 3. Inspect specific object
obj = doc.getObject("MyPart")
bb = obj.Shape.BoundBox
print(f"{bb.XLength:.1f}x{bb.YLength:.1f}x{bb.ZLength:.1f} valid={obj.Shape.isValid()}")

# 4. PartDesign history
for feat in body.Group:
    print(feat.Name, feat.TypeId)

# 5. Spreadsheet params
ss = doc.getObject("Params")
for attr in dir(ss):
    if not attr.startswith('_'):
        try:
            v = getattr(ss,attr)
            if isinstance(v,(int,float,str)): print(attr,'=',v)
        except: pass

# 6. Check expression-driven properties (must change spreadsheet, not object)
print(obj.ExpressionEngine)  # non-empty = expression-driven
```

## When to Ask the User

- Unexpected object names or state
- Multiple possible targets for a modification
- Change would break downstream features
- Dimension is expression-driven (must change spreadsheet cell)

## Live API Introspection

```python
import Part; print([m for m in dir(Part) if not m.startswith('_')])
import Part; help(Part.makeCylinder)
print(doc.getObject('Box').PropertiesList)
print(doc.supportedTypes())
```

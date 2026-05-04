# Sketcher Python API — Constraint Syntax

## Geometry Indices

`addGeometry()` returns the index (0-based, insertion order).

Point indices per element:
- `0` = whole edge (Horizontal/Vertical use this)
- `1` = start point
- `2` = end point
- `3` = center (arcs/circles only — NOT midpoint of line)

Built-in indices (always available):
- `-1` = X-axis, `-2` = Y-axis, `-3` = origin point
- External geometry: `-3`, `-4`, `-5`… in reverse insertion order

## Constraint Syntax

```python
import Sketcher
C = Sketcher.Constraint

# Geometric
sk.addConstraint(C("Horizontal", geo))
sk.addConstraint(C("Vertical",   geo))
sk.addConstraint(C("Coincident", geo1,pt1, geo2,pt2))
sk.addConstraint(C("PointOnObject", geo1,pt1, geo2))
sk.addConstraint(C("Parallel",    geo1, geo2))
sk.addConstraint(C("Perpendicular",geo1, geo2))
sk.addConstraint(C("Tangent",     geo1, geo2))
sk.addConstraint(C("Equal",       geo1, geo2))
sk.addConstraint(C("Block",       geo, pt))

# Symmetric: pt1 and pt2 symmetric about sym reference
sk.addConstraint(C("Symmetric", geo1,pt1, geo2,pt2, sym_geo,sym_pt))
# sym_geo=-2 → Y-axis, sym_geo=-1 → X-axis, sym_geo=-3 → origin

# Dimensional
sk.addConstraint(C("Distance",  geo, length))                     # line length
sk.addConstraint(C("Distance",  geo1,pt1, geo2,pt2, dist))        # between points
sk.addConstraint(C("DistanceX", geo,pt, value))                   # absolute X
sk.addConstraint(C("DistanceX", geo1,pt1, geo2,pt2, value))       # horizontal dist
sk.addConstraint(C("DistanceY", geo,pt, value))                   # absolute Y
sk.addConstraint(C("DistanceY", geo1,pt1, geo2,pt2, value))       # vertical dist
sk.addConstraint(C("Radius",   geo, r))
sk.addConstraint(C("Diameter", geo, d))
sk.addConstraint(C("Angle",    geo, angle_rad))
sk.addConstraint(C("Angle",    geo1,pt1, geo2,pt2, angle_rad))
```

## Symmetric — Preferred Centering (verified from tutorial files)

```python
# ThirdPos=0 = the axis as a LINE (not a point on it) — confirmed from FCStd XML scan
# -2 = Y-axis (mirror left↔right),  -1 = X-axis (mirror top↔bottom)

# Symmetric about Y-axis: same-line endpoints → line is centered horizontally
sk.addConstraint(C("Symmetric", 0,1, 0,2, -2,0))  # ✓ ThirdPos=0, NOT 1
# Symmetric about X-axis: same-line endpoints → line is centered vertically
sk.addConstraint(C("Symmetric", 1,1, 1,2, -1,0))  # ✓
```

⚠️ `(-2, 1)` (start-point of Y-axis = origin) also compiles but means point-symmetry,
not axis-mirror. Tutorial files consistently use `(-2, 0)` / `(-1, 0)`.

## Fully Constrained Centered Rectangle — Two Variants

### Variant A: Symmetric (preferred — stays centered when W/H change)

```python
import Part, Sketcher
W, H = 40.0, 20.0
C = Sketcher.Constraint

sk.addGeometry(Part.LineSegment(App.Vector(-W/2,-H/2,0), App.Vector( W/2,-H/2,0)))  # 0 bottom
sk.addGeometry(Part.LineSegment(App.Vector( W/2,-H/2,0), App.Vector( W/2, H/2,0)))  # 1 right
sk.addGeometry(Part.LineSegment(App.Vector( W/2, H/2,0), App.Vector(-W/2, H/2,0)))  # 2 top
sk.addGeometry(Part.LineSegment(App.Vector(-W/2, H/2,0), App.Vector(-W/2,-H/2,0)))  # 3 left

# Close the loop
sk.addConstraint(C("Coincident",0,2,1,1)); sk.addConstraint(C("Coincident",1,2,2,1))
sk.addConstraint(C("Coincident",2,2,3,1)); sk.addConstraint(C("Coincident",3,2,0,1))
# H/V
sk.addConstraint(C("Horizontal",0)); sk.addConstraint(C("Horizontal",2))
sk.addConstraint(C("Vertical",  1)); sk.addConstraint(C("Vertical",  3))
# Center via Symmetric (verified pattern from Sketcher tutorial FCStd files)
sk.addConstraint(C("Symmetric", 0,1, 0,2, -2,0))  # bottom line centered on Y-axis
sk.addConstraint(C("Symmetric", 1,1, 1,2, -1,0))  # right line centered on X-axis
# Dimensions only — no position anchors needed
sk.addConstraint(C("DistanceX", 0,1, 0,2, W))     # width
sk.addConstraint(C("DistanceY", 1,1, 1,2, H))     # height
assert sk.solve() == 0
# Total: 12 constraints, DoF=0
```

### Variant B: DistanceX position anchor (use when center ≠ origin, or for expressions)

```python
# 4 dimensional constraints replace 2 Symmetric + 2 dimensional
ci = len(sk.Constraints)  # capture index BEFORE adding
sk.addConstraint(C("DistanceX", 0,1, cx-W/2))    # ci+0: anchor X (can be negative ✓)
sk.addConstraint(C("DistanceY", 0,1, cy-H/2))    # ci+1: anchor Y (can be negative ✓)
sk.addConstraint(C("DistanceX", 0,1, 0,2, W))    # ci+2: width
sk.addConstraint(C("DistanceY", 1,1, 1,2, H))    # ci+3: height
# Bind to spreadsheet:
sk.setExpression(f'.Constraints[{ci+0}]', '-Parameter.BW / 2')  # negative expr ✓
sk.setExpression(f'.Constraints[{ci+2}]', 'Parameter.BW')
```

## Circles and Arcs

```python
import Part, math

sk.addGeometry(Part.Circle(App.Vector(0,0,0), App.Vector(0,0,1), 10))
sk.addGeometry(Part.ArcOfCircle(
    Part.Circle(App.Vector(0,0,0), App.Vector(0,0,1), 10), 0, math.pi))

# Circle center to origin:
sk.addConstraint(Sketcher.Constraint("Coincident", geo_circle, 3, -3, 1))
sk.addConstraint(Sketcher.Constraint("Radius", geo_circle, 10.0))
```

## Custom Datum Plane

```python
dp = doc.addObject("PartDesign::Plane","DatumPlane")
body.addObject(dp)

# Offset from XY_Plane by 20mm in Z:
dp.AttachmentSupport = [(doc.getObject("XY_Plane"),"")]
dp.MapMode = "FlatFace"
dp.AttachmentOffset = App.Placement(App.Vector(0,0,20), App.Rotation())

# Perpendicular to an edge:
dp.AttachmentSupport = [(pad, ["Edge3"])]
dp.MapMode = "NormalToEdge"

# At 30° angle:
dp.AttachmentOffset = App.Placement(App.Vector(0,0,0), App.Rotation(App.Vector(1,0,0),30))
doc.recompute()

sk.AttachmentSupport = [(dp,"")]; sk.MapMode="FlatFace"
```

## External Geometry (TNP risk — prefer datum planes)

```python
sk.addExternalGeometry(doc.getObject("Pad"), ["Edge3"])
# Creates reference geometry (red dashed) at index -3, -4, -5…
sk.addConstraint(Sketcher.Constraint("Coincident", 0,1, -3,1))
```

## State Check

```python
doc.recompute()
print("DoF:", sk.solve())  # 0=fully constrained, >0=under, <0=over
for i,c in enumerate(sk.Constraints):
    print(i, c.Type, getattr(c,'Value',''))
```

## When to Avoid Sketcher Python

Geometry indices are implicit (insertion order), point indices must be memorized,
solver order-sensitive. For pure scripted geometry → use Part/CSG instead.
Use Sketcher Python only for simple profiles or when PartDesign history is needed.

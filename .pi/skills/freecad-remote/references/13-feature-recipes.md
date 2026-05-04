# PartDesign Feature Recipes

Load when: need specific feature syntax — threads, pipes, grooves, lofts, patterns, binders.

## Thread — Part::Helix + Part::Sweep + Part::Cut

`PartDesign::SubtractiveHelix` fails with `Standard_NullObject`. Use CSG instead:

```python
import Part

# 1. Helix path
helix = doc.addObject("Part::Helix","Helix")
helix.Pitch      = pitch_mm      # e.g. 1.0 for M6
helix.Height     = thread_height
helix.Radius     = minor_radius  # helix runs at thread root, not nominal
helix.Angle      = 0.0           # 0=cylindrical
helix.LocalCoord = "Right-handed"
helix.Style      = "New style"
doc.recompute()

# 2. Thread profile sketch — NO AttachmentSupport (leave empty [])
# Draw triangle at helix start position in world coordinates
# Frenet=True rotates it automatically along the helix
sk = doc.addObject("Sketcher::SketchObject","Sk_Thread")
# sk.AttachmentSupport stays empty

# 3. Sweep
sweep = doc.addObject("Part::Sweep","ThreadSweep")
sweep.Sections   = [sk]
sweep.Spine      = (helix, ["Edge1"])
sweep.Frenet     = True   # profile rotates with helix — critical
sweep.Transition = "Right corner"
doc.recompute()

# 4. Subtract
cut = doc.addObject("Part::Cut","ThreadCut")
cut.Base = base_body
cut.Tool = sweep
doc.recompute()
```

ISO metric V-profile (60°) for Mx, pitch p:
- `major_r = x/2` (e.g. M6 → 3.0 mm)
- `minor_r = major_r - 0.6495 * p`
- Triangle: base at major_r, tip at minor_r, height = p

## Spring — Part::Helix + circular Sweep

```python
helix = doc.addObject("Part::Helix","Helix")
helix.Pitch=6.0; helix.Height=60.0; helix.Radius=10.0
doc.recompute()

sk = doc.addObject("Sketcher::SketchObject","Sk_Wire")
# No AttachmentSupport — circle at helix start point
sk.addGeometry(Part.Circle(App.Vector(helix.Radius,0,0), App.Vector(0,0,1), wire_r))
import Sketcher
sk.addConstraint(Sketcher.Constraint("DistanceX",0,3,helix.Radius))
sk.addConstraint(Sketcher.Constraint("DistanceY",0,3,0.0))
sk.addConstraint(Sketcher.Constraint("Radius",0,wire_r))
doc.recompute()

sweep = doc.addObject("Part::Sweep","Spring")
sweep.Sections=[sk]; sweep.Spine=(helix,["Edge1"])
sweep.Frenet=True; sweep.Transition="Right corner"
doc.recompute()
```

## AdditivePipe — Profile Along Path

```python
pipe = doc.addObject("PartDesign::AdditivePipe","Pipe")
body.addObject(pipe)
pipe.Profile    = (sk_profile, [])
pipe.Spine      = (sk_path, ["Edge1","Edge2","Edge3"])  # multi-edge spine
pipe.Mode       = "Standard"     # or "Frenet", "Binormal"
pipe.Transition = "Transformed"
doc.recompute()

# With Part::Helix as spine (spiral pipe):
base = doc.addObject("PartDesign::FeatureBase","BaseFeature")
body.addObject(base)
base.Shape = helix.Shape
pipe.Spine = (base, ["Edge1","Edge2","Edge3"])
```

## SubtractivePipe

Same API as AdditivePipe:
```python
pipe = doc.addObject("PartDesign::SubtractivePipe","SubPipe")
body.addObject(pipe)
pipe.Profile=(sk_profile,[]); pipe.Spine=(sk_path,["Edge1","Edge2","Edge3"])
pipe.Mode="Standard"; pipe.Transition="Transformed"
doc.recompute()
```

## Groove — Subtractive Revolution

```python
groove = doc.addObject("PartDesign::Groove","Groove")
body.addObject(groove)
groove.Profile       = (sk, [])
groove.ReferenceAxis = (sk, ["H_Axis"])  # or DatumLine
groove.Angle         = 360.0
groove.Reversed      = True
doc.recompute()

# With DatumLine as axis:
dl = doc.addObject("PartDesign::Line","DatumLine")
body.addObject(dl)
dl.AttachmentSupport = [(pad, ("Edge9",))]
dl.MapMode = "TwoPointLine"
doc.recompute()
groove.ReferenceAxis = (dl, [""])
```

## AdditiveLoft — Connect Profiles

```python
loft = doc.addObject("PartDesign::AdditiveLoft","Loft")
body.addObject(loft)
loft.Profiles = [sk_bottom, sk_top]  # ≥2 sketches on different planes
loft.Closed = False; loft.Ruled = False
doc.recompute()
# Note: unstable in some versions — check shape.isValid()
```

## MultiTransform — Combined Patterns

```python
lp1 = doc.addObject("PartDesign::LinearPattern","LP_X")
lp1.Direction=(body,["H_Axis"]); lp1.Length=80.0; lp1.Occurrences=5

lp2 = doc.addObject("PartDesign::LinearPattern","LP_Y")
lp2.Direction=(sketch,["V_Axis"]); lp2.Length=80.0; lp2.Occurrences=5

mt = doc.addObject("PartDesign::MultiTransform","Grid")
body.addObject(mt)
mt.Originals=[pocket_feature]
mt.Transformations=[lp1,lp2]  # 5×5 grid
doc.recompute()
```

## ShapeBinder — Share Geometry Between Bodies

Each Body is isolated. ShapeBinder/SubShapeBinder bridges across bodies.

Pattern from tutorial (Page_056 — star shape shared across 3 bodies):
```
Body    → Sketch(star) → Pad → …        (master body)
Body001 → ShapeBinder(→Sketch) → Pocket  (uses star for cutout)
Body002 → ShapeBinder(→Sketch) → Pad     (uses star as profile)
```
Change the star sketch → all three bodies update.

```python
# PartDesign::ShapeBinder (FreeCAD 0.17+) — whole objects only
binder = doc.addObject("PartDesign::ShapeBinder","Ref")
body_b.addObject(binder)
binder.Support = [(source_sketch, ("",))]  # no sub = whole object
binder.TraceSupport = False  # True = follows source placement changes
doc.recompute()
sk.AttachmentSupport = [(binder,"")]  # attach sketch to copied shape

# PartDesign::SubShapeBinder (FreeCAD 0.20+) — sub-elements, cross-doc
binder = doc.addObject("PartDesign::SubShapeBinder","Ref")
body_b.addObject(binder)
binder.Support = [(source_body, ("Face3","Face5"))]  # specific faces
binder.Support = [(body_a,("Face2",)), (body_b,("Edge3",))]  # multi-source
binder.BindMode = 0  # 0=Synchronized, 1=Frozen, 2=Detached
doc.recompute()
```

Use ShapeBinder for simple whole-object copy; SubShapeBinder when specific faces/edges needed or cross-document.

## Radius-Based Primitives (No Sketch)

```python
# Subtractive cylinder (hole without sketch)
cyl = doc.addObject("PartDesign::SubtractiveCylinder","Hole")
body.addObject(cyl); cyl.Radius=3.5; cyl.Height=30.0; doc.recompute()

# Subtractive ellipsoid
el = doc.addObject("PartDesign::SubtractiveEllipsoid","Ellipsoid")
body.addObject(el)
el.Radius1=8.5; el.Radius2=13.5; el.Radius3=0.0  # 0=symmetric Z
el.Angle1=-90.0; el.Angle2=90.0; el.Angle3=360.0

# Available: Additive/Subtractive × Box, Cylinder, Sphere, Cone, Ellipsoid, Torus, Prism, Wedge
```

## Part/CSG Patterns from Tutorials

```python
# Rounded box without fillet (T03): Box ∩ Sphere = rounded corners
rounded = doc.addObject("Part::MultiCommon","Rounded")
rounded.Shapes = [box, sphere]

# Shell operation (T21): solid → hollow with open face
thick = doc.addObject("Part::Thickness","Shell")
thick.Faces=(solid,["Face1"]); thick.Value=-2.0  # negative=inward
thick.Mode="Skin"; thick.Join="Arc"; doc.recompute()

# Fuse multiple (T07,T15)
fuse = doc.addObject("Part::MultiFuse","Fused")
fuse.Shapes=[s1,s2,s3]; doc.recompute()

# 2D offset
offset = doc.addObject("Part::Offset2D","Offset")
offset.Source=wire; offset.Value=5.0  # positive=outward
offset.Join=2; offset.Fill=False; doc.recompute()
```

## Advanced MapModes

```python
# Sketch perpendicular to an edge
sk.MapMode="NormalToEdge"
sk.AttachmentSupport=[(other_sketch,("Edge3",))]

# Datum plane from 3 points
dp.MapMode="ThreePointsPlane"
dp.AttachmentSupport=[(sk1,("Vertex1","Vertex3")),(sk2,("Vertex1",))]

# Datum plane at angle offset
dp.AttachmentOffset=App.Placement(App.Vector(0,0,0),App.Rotation(App.Vector(1,0,0),30))
```

## PartDesign Type Frequency (198 tutorial files)

| Type | Count | Notes |
|------|-------|-------|
| `Pad` | 154 | always first feature |
| `Pocket` | 107 | |
| `Mirrored` | 41 | uses sketch axis |
| `Fillet` | 40 | always last |
| `PolarPattern` | 37 | |
| `Revolution` | 33 | YZ_Plane+V_Axis confirmed |
| `SubtractiveCylinder` | 21 | no sketch needed |
| `MultiTransform` | 19 | |
| `LinearPattern` | 9 | |
| `AdditivePipe` | 7 | multi-edge spine |
| `Groove` | 5 | subtractive revolution |
| `AdditiveLoft` | 2 | version-sensitive |
| `SubtractivePipe` | 2 | same API as Additive |
| `ShapeBinder` | 1 | whole-object cross-body ref |
| `SubShapeBinder` | 0* | FreeCAD 0.20+, sub-element ref |

*Not in tutorial files (too old), but preferred for new projects.

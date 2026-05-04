# PartDesign — Feature-Based Solid Modeling

## Concept
PartDesign builds one solid by stacking features inside a **Body** container.
Each feature adds or removes material from the previous result.
The model tree is the full modeling history — any step can be re-edited at any time.

## Workflow Pattern
```
1. New Body
2. New Sketch  →  attach to XY/XZ/YZ datum plane (not a face)
3. Fully constrain the sketch
4. Pad / Revolution  →  first solid
5. New Sketch  →  attach to datum plane or existing face
6. Pad / Pocket / Hole / Groove  →  add or remove material
7. Repeat 5–6 for each feature
8. Dress-ups last: Fillet → Chamfer → Draft → Thickness
```

## Additive Features (add material)
| Feature | Description |
|---------|-------------|
| **Pad** | Extrude closed sketch to a depth |
| **Revolution** | Rotate sketch profile around an axis |
| **Additive Loft** | Transition solid between ≥2 sketch profiles |
| **Additive Pipe** | Sweep a profile along a path sketch |
| **Additive Helix** | Sweep along a helical path |
| Additive Box/Cylinder/Sphere/Cone | Primitives added directly to the Body |

## Subtractive Features (remove material)
| Feature | Description |
|---------|-------------|
| **Pocket** | Extrude-cut into the solid |
| **Hole** | Threaded or clearance hole from a circle sketch |
| **Groove** | Revolution-cut |
| **Subtractive Loft/Pipe/Helix** | Same as additive counterparts but subtract |

## Transformation Features (pattern/mirror)
| Feature | Description |
|---------|-------------|
| **Linear Pattern** | Repeat a feature N times along an axis |
| **Polar Pattern** | Repeat N times around an axis |
| **Mirror** | Mirror a feature across a plane |
| **MultiTransform** | Chain multiple transformations |

## Dress-Up Features (apply to final solid)
- **Fillet** — round selected edges
- **Chamfer** — bevel selected edges
- **Draft** — angular taper on faces (for mold release)
- **Thickness** — hollow out the solid, keeping selected faces open

## Datum Objects
Create these to have stable references that survive topology changes:
- `PartDesign → Datum Plane` — a named reference plane
- `PartDesign → Datum Line` — a named reference axis
- `PartDesign → Datum Point` — a named reference point

Attach sketches to datum planes, not model faces.

## Python — PartDesign Basics
```python
import Part, Sketcher

doc  = App.ActiveDocument
body = doc.addObject("PartDesign::Body", "Body")

# Attach sketch to XY plane origin
sk = doc.addObject("Sketcher::SketchObject", "BaseSketch")
body.addObject(sk)
sk.AttachmentSupport = [(doc.getObject("XY_Plane"), "")]
sk.MapMode = "FlatFace"

# Add a fully constrained rectangle (width=40, height=20, bottom-left at origin)
hw = 20.0
sk.addGeometry(Part.LineSegment(App.Vector(-hw, 0,  0), App.Vector(hw,  0,  0)))  # 0
sk.addGeometry(Part.LineSegment(App.Vector( hw, 0,  0), App.Vector(hw,  20, 0)))  # 1
sk.addGeometry(Part.LineSegment(App.Vector( hw, 20, 0), App.Vector(-hw, 20, 0)))  # 2
sk.addGeometry(Part.LineSegment(App.Vector(-hw, 20, 0), App.Vector(-hw, 0,  0)))  # 3
sk.addConstraint(Sketcher.Constraint("Coincident", 0,2, 1,1))
sk.addConstraint(Sketcher.Constraint("Coincident", 1,2, 2,1))
sk.addConstraint(Sketcher.Constraint("Coincident", 2,2, 3,1))
sk.addConstraint(Sketcher.Constraint("Coincident", 3,2, 0,1))
sk.addConstraint(Sketcher.Constraint("Horizontal", 0))
sk.addConstraint(Sketcher.Constraint("Horizontal", 2))
sk.addConstraint(Sketcher.Constraint("Vertical",   1))
sk.addConstraint(Sketcher.Constraint("Vertical",   3))
sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, -hw))        # left X
sk.addConstraint(Sketcher.Constraint("DistanceY", 0, 1, 0))          # bottom Y
sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 40.0)) # width
sk.addConstraint(Sketcher.Constraint("DistanceY", 1, 1, 1, 2, 20.0)) # height
# DoF = 0  ← verify with sk.solve()

# Pad
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sk
pad.Length  = 15.0
doc.recompute()
```

> **Note:** PartDesign from Python is verbose but workable. Use recipes from `13-partdesign-patterns.md`.
> For quick one-off geometry with no edit history needed, Part/CSG is faster.

## Pad / Pocket Key Properties
```python
pad.Length         = 20.0      # extrusion depth
pad.Length2        = 5.0       # second depth (two-direction)
pad.Midplane       = True      # center on sketch plane (FreeCAD 1.0: Midplane, not Symmetric or MidPlane)
pad.Reversed       = False     # flip direction
pad.TaperAngle     = 0.0       # draft angle on side faces

pocket.Length      = 10.0
pocket.Type        = "Blind"   # "Blind", "ThroughAll", "UpToFace", "UpToLast"
```

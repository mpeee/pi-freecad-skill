# Part Workbench — CSG and Direct Geometry

## Concept
The Part workbench works with BREP (Boundary Representation) geometry managed by OpenCascade.
Objects are constructed by combining primitives and applying Boolean operations — no feature history, no Body.

## Primitives
```python
import Part

box    = Part.makeBox(length, width, height)
box    = Part.makeBox(l, w, h, App.Vector(x, y, z))           # with placement
cyl    = Part.makeCylinder(radius, height)
cyl    = Part.makeCylinder(r, h, App.Vector(x,y,z), App.Vector(ax,ay,az), angle_deg)
sphere = Part.makeSphere(radius)
cone   = Part.makeCone(r1, r2, height)                        # r1=base, r2=top
torus  = Part.makeTorus(major_r, minor_r)
```

## Boolean Operations
```python
result = a.fuse(b)       # union  (A + B)
result = a.cut(b)        # subtract  (A − B) — order matters: a is kept, b is removed
result = a.common(b)     # intersection  (A ∩ B)
```

**Avoid co-planar faces in Boolean ops** — extend the cutter slightly past the target surface to prevent OpenCascade failures:
```python
# Bad: cutter face is exactly flush with target
cutter = Part.makeBox(10, 10, 5, App.Vector(0, 0, 0))

# Good: cutter extends 1mm past on each side
cutter = Part.makeBox(10, 10, 7, App.Vector(0, 0, -1))
```

## Adding Shapes to the Document
```python
doc  = App.ActiveDocument
feat = doc.addObject("Part::Feature", "MyPart")
feat.Shape = result
doc.recompute()

# Shortcut (auto-names):
Part.show(result)
```

## Parametric Part Objects (keep history)
```python
box = doc.addObject("Part::Box", "Box")
box.Length = 80.0
box.Width  = 40.0
box.Height = 20.0

cyl = doc.addObject("Part::Cylinder", "Cyl")
cyl.Radius = 5.0
cyl.Height = 30.0
cyl.Placement = App.Placement(App.Vector(40,20,0), App.Rotation())

cut = doc.addObject("Part::Cut", "Cut")
cut.Base = box    # shape to cut from
cut.Tool = cyl    # shape to cut with
doc.recompute()
```

## Shape Topology — Inspection
```python
s = obj.Shape
s.ShapeType          # "Solid", "Shell", "Face", "Edge", "Vertex", "Compound"
s.isValid()          # True/False — False means broken geometry
s.isClosed()         # relevant for shells/wires
s.Vertexes           # list of Vertex
s.Edges              # list of Edge  (e.Length for length)
s.Wires              # list of Wire
s.Faces              # list of Face  (f.Area for area, f.normalAt(0,0) for normal)
s.Shells             # list of Shell
s.Solids             # list of Solid
s.BoundBox           # BoundBox object
bb = s.BoundBox
bb.XMin, bb.XMax, bb.XLength
bb.YMin, bb.YMax, bb.YLength
bb.ZMin, bb.ZMax, bb.ZLength
bb.Center            # App.Vector center point
```

## Building Geometry From Scratch (low-level)
```python
# Vertex → Edge → Wire → Face → Solid
V1 = App.Vector(0, 0, 0)
V2 = App.Vector(30, 0, 0)
V3 = App.Vector(30, 20, 0)
V4 = App.Vector(0, 20, 0)

L1 = Part.LineSegment(V1, V2)
L2 = Part.LineSegment(V2, V3)
L3 = Part.LineSegment(V3, V4)
L4 = Part.LineSegment(V4, V1)

# Arc needs: start, midpoint, end
arc = Part.Arc(V1, App.Vector(-5, 10, 0), V4)

# Base geometry → Edge
E1, E2, E3, E4 = [L.toShape() for L in (L1, L2, L3, L4)]

# Wire: edge order matters, endpoints must connect
W = Part.Wire([E1, E2, E3, E4])
print(W.isClosed())    # must be True for a Face

# Face from closed wire
F = Part.Face(W)

# Extrude face → solid
solid = F.extrude(App.Vector(0, 0, 10))
print(solid.ShapeType)   # → "Solid"

# Shell from wire (no top/bottom face)
shell = W.extrude(App.Vector(0, 0, 10))
print(shell.ShapeType)   # → "Shell"
```

## Placement and Transforms
```python
# Set placement directly
obj.Placement = App.Placement(
    App.Vector(x, y, z),
    App.Rotation(App.Vector(ax, ay, az), angle_deg)
)

# Move placement base
obj.Placement.Base = App.Vector(x, y, z)

# Shape-level transforms (does not affect document object)
s2 = shape.copy()
s2.translate(App.Vector(dx, dy, dz))
s2.rotate(App.Vector(cx, cy, cz), App.Vector(ax, ay, az), angle_deg)
```

## Compound — Group Multiple Shapes
```python
compound = Part.makeCompound([shape1, shape2, shape3])
Part.show(compound)
```

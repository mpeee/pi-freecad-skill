# Python API — FreeCAD-Specific Extensions

Load when: import/export, per-face colors, geometry search, placement math, mirroring.
Basic API (document lifecycle, object types, placement, vectors) is in model training.

## Import / Export

```python
import ImportGui

# STEP — export
ImportGui.export([doc.getObject("Body")], f"{cwd_win}/output.step")
# all visible objects:
ImportGui.export([o for o in doc.Objects if hasattr(o,"Shape") and o.ViewObject.Visibility], "out.step")
# STEP — import
ImportGui.insert("input.step", doc.Name)

# STL — export
import MeshPart, Mesh
mesh_obj = doc.addObject("Mesh::Feature","Mesh")
mesh_obj.Mesh = MeshPart.meshFromShape(
    Shape=doc.getObject("Body").Shape,
    LinearDeflection=0.1,   # mm — smaller = finer
    AngularDeflection=0.5,  # degrees
    Relative=False)
Mesh.export([mesh_obj], f"{cwd_win}/output.stl")
# STL — import (yields Mesh, not Solid)
Mesh.insert("input.stl", doc.Name)

# IGES / DXF
ImportGui.export([obj], "output.igs"); ImportGui.insert("input.igs", doc.Name)
import importDXF; importDXF.export([sketch], "output.dxf")
```

## Mesh → Solid

```python
import Part, MeshPart
mesh_obj = doc.getObject("Mesh")

# Method A
shape = Part.Shape()
shape.makeShapeFromMesh(mesh_obj.Mesh.Topology, 0.1)
solid = Part.Solid(Part.Shell(shape.Faces))

# Method B (more robust)
solid = MeshPart.meshToOCC(mesh_obj.Mesh)

feat = doc.addObject("Part::Feature","Solid")
feat.Shape = solid; doc.recompute()
```

Only works for watertight meshes.

## Per-Face Colors

```python
obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # whole object R,G,B floats 0-1

# Individual faces:
colors = [(0.8,0.8,0.8)] * len(obj.Shape.Faces)
colors[0] = (1.0,0.0,0.0)  # Face1 red
colors[2] = (0.0,0.8,0.0)  # Face3 green
obj.ViewObject.DiffuseColor = colors

obj.ViewObject.Transparency = 50  # 0=opaque, 100=invisible
```

## Find Edges/Faces by Geometry (not by name)

```python
shape = obj.Shape

# Edges by length
long = [f"Edge{i+1}" for i,e in enumerate(shape.Edges) if e.Length > 50]

# Edges at specific Z (e.g. top face edges)
top_edges = [f"Edge{i+1}" for i,e in enumerate(shape.Edges)
             if abs(e.BoundBox.ZMax-e.BoundBox.ZMin)<0.01
             and abs(e.BoundBox.ZMin-target_z)<0.01]

# Faces by normal direction (e.g. top face = normal pointing +Z)
top_faces = [f"Face{i+1}" for i,f in enumerate(shape.Faces)
             if f.normalAt(f.ParameterRange[0],f.ParameterRange[2]).z > 0.99]

# Largest face
i, face = max(enumerate(shape.Faces), key=lambda x: x[1].Area)
print(f"Face{i+1}: {face.Area:.1f} mm²")
```

## Placement — Combining Rotations

```python
# Rotate around axis + angle
rot_z90 = App.Rotation(App.Vector(0,0,1), 90)
rot_x45 = App.Rotation(App.Vector(1,0,0), 45)
combined = rot_z90.multiply(rot_x45)  # order matters: Z first, then X

obj.Placement = App.Placement(App.Vector(10,20,30), combined)

# Euler angles (Yaw, Pitch, Roll degrees)
rot = App.Rotation(yaw=90, pitch=0, roll=45)
print(rot.toEuler())

# Quaternion
q = rot.Q  # (x,y,z,w)
rot2 = App.Rotation(*q)

# Invert placement
inv = obj.Placement.inverse()

# Distance between objects
delta = obj2.Placement.Base.sub(obj1.Placement.Base)
print(f"{delta.Length:.1f} mm")
```

## Part::Mirror (CSG)

```python
import Part
# Mirror shape across a plane (point on plane + normal vector)
mirrored = obj.Shape.mirror(App.Vector(0,0,0), App.Vector(1,0,0))  # across YZ plane
result = obj.Shape.fuse(mirrored)
feat = doc.addObject("Part::Feature","Mirrored")
feat.Shape = result; doc.recompute()

# PartDesign::Mirrored (preserves feature history)
mirror = doc.addObject("PartDesign::Mirrored","Mirror")
body.addObject(mirror)
mirror.Originals   = [pad_feature]
mirror.MirrorPlane = (sketch, ["V_Axis"])
doc.recompute()
```

## Part.BooleanFragments

```python
import Part
# Split two shapes into all resulting fragments
feat = doc.addObject("Part::Feature","Fragments")
feat.Shape = Part.BooleanFragments([shape_a, shape_b], 0.0)
doc.recompute()
```

## Assembly Overview

| Workbench | Since | Notes |
|-----------|-------|-------|
| Assembly (built-in) | FreeCAD 1.0 | joint-based, recommended for new projects |
| A2plus | addon | constraint-based, stable, widely used |
| Assembly3 | addon | SolveSpace solver, powerful |
| Assembly4 | addon | App::Link-based, complex hierarchies |

For scripting: `App::Part` as simple non-parametric container. Full assembly APIs are workbench-specific.

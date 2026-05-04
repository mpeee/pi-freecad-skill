# TechDraw — 2D Technical Drawings

## Purpose
Convert 3D models into printable/exportable 2D drawings with dimensions, annotations, and title blocks.
Output: PDF, SVG, DXF.

## Workflow (GUI)
```
1. Switch to TechDraw workbench
2. TechDraw → Insert Page using Template
   → pick A4_Portrait_ISO7200TD or A4_Landscape_ISO7200TD
3. Select 3D object(s) in tree
4. TechDraw → Insert View  (creates top view by default)
5. Set view properties in Data tab:
   - Direction (projection axis), XDirection, Scale, X, Y position on page
6. Repeat for additional views (front, side, isometric)
7. Add dimensions: Ctrl+click two vertices → TechDraw → Insert Length Dimension
8. Add annotations: TechDraw → Insert Balloon
9. File → Export → .pdf / .svg / .dxf
```

## Standard View Directions
```
Top view:    Direction=[0,0,1]   XDirection=[1,0,0]
Front view:  Direction=[0,-1,0]  XDirection=[1,0,0]
Right side:  Direction=[1,0,0]   XDirection=[0,-1,0]
Left side:   Direction=[-1,0,0]  XDirection=[0,1,0]
Isometric:   Direction=[1,-1,1]  (normalised)
```

## Python — Minimal Page and View
```python
import FreeCAD as App
import TechDraw

doc = App.ActiveDocument

# Page with template
page = doc.addObject("TechDraw::DrawPage", "Page")
tmpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
tmpl.Template = App.getResourceDir() + \
    "Mod/TechDraw/Templates/A4_Landscape_ISO7200TD.svg"
page.Template = tmpl

# View
view = doc.addObject("TechDraw::DrawViewPart", "View")
page.addView(view)
view.Source    = [doc.getObject("MyPart")]  # list of source objects
view.Direction = App.Vector(0, 0, 1)        # top view
view.Scale     = 0.1
view.X         = 100.0                      # position on page (mm)
view.Y         = 150.0

doc.recompute()
```

## Dimension Types
| Tool | Use |
|------|-----|
| LengthDimension | Distance between two points |
| HorizontalDimension | Horizontal distance |
| VerticalDimension | Vertical distance |
| RadiusDimension | Radius of arc/circle |
| DiameterDimension | Diameter of arc/circle |
| AngleDimension | Angle between two edges |

## Important Notes
- Dimensions on axonometric/isometric views are visually distorted — use `TechDraw LinkDimension` to link to actual 3D measurement
- TechDraw does not auto-update when 3D model changes — you must `recompute()` the document
- Templates are SVG files; custom templates can be created in Inkscape
- Title block fields in templates are editable: click the small green square next to each field in the GUI

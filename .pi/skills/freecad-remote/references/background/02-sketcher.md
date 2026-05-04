# Sketcher — Constrained 2D Sketches

## Purpose
Sketches are 2D profiles used as input for PartDesign features (Pad, Pocket, Revolution …) or Part operations. They are **not** for 2D drawings (use TechDraw for that).

## Rules for Solid-Generating Sketches
- Must contain only **closed contours** — no open ends, no gaps
- Contours may nest (inner contour = hole) but must not intersect each other
- No T-connections (a point touching the interior of another edge)
- No duplicate or overlapping edges

## Constraint Types

### Geometric constraints (lock shape/relationship)
| Constraint | Effect |
|-----------|--------|
| Coincident | Two points share the same position |
| Horizontal / Vertical | Line is perfectly horizontal or vertical |
| Parallel | Two lines are parallel |
| Perpendicular | Two lines are at 90° |
| Tangent | Edge is tangent to arc/circle |
| Symmetric | Two points are symmetric about a line or point |
| Equal | Two edges have the same length or radius |
| Fix (Lock) | Point is fixed in absolute position |
| Point on object | Point lies on an edge/axis |

### Dimensional constraints (lock size)
- Length, Horizontal distance, Vertical distance
- Radius, Diameter
- Angle

## Fully Constrained Sketch
- **Goal: always fully constrain every sketch**
- Sketch turns **green** when fully constrained — no part can move freely
- Sketch is **blue** when under-constrained — geometry is ambiguous, downstream features become unpredictable
- Sketch is **red** when over-constrained — conflicting constraints, must remove one

### How to reach fully constrained efficiently
1. Draw geometry roughly in the correct position
2. Apply geometric constraints first (parallel, symmetric, coincident …)
3. Add dimensional constraints last
4. Use **Symmetry** to center shapes on the origin instead of absolute position constraints
5. Check DoF counter in the task panel — must reach 0

## External Geometry
- `Sketcher → External geometry` traces an edge from the current solid into the sketch
- Appears **red** — reference only, not part of the sketch profile
- Use to position new sketch elements relative to existing geometry
- Prefer datum planes over direct face references — more robust against topology changes

## Named Constraints (for expressions)
- Double-click a dimensional constraint → set a name
- Named constraint can be referenced in expressions: `Sketch.my_dim`
- Useful for driving sketch dimensions from a Spreadsheet

## Construction Geometry
- Toggle any sketch element to **construction mode** (dashed blue line)
- Construction geometry is not part of the profile — used only as helper geometry
- Does not affect extrusion/pocketing

## Attaching a Sketch
- Attach to **datum planes** (XY, XZ, YZ or custom) — **not** to model faces
- Model faces get renamed when features are reordered (Topological Naming Problem → breaks the sketch)
- `Sketch.AttachmentSupport` / `Sketch.MapMode = "FlatFace"`

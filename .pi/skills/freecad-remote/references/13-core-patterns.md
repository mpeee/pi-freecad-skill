# PartDesign Core Patterns

Load when: building PartDesign models from Python. Always load for Sketcher/PartDesign work.

## Sketcher Constraint Cheatsheet (verified against FCStd tutorial files)

```python
C = Sketcher.Constraint  # alias

# --- Geometry indices ---
# -1=X-axis  -2=Y-axis  -3=origin-point
# point-ids: 0=whole-geo  1=start  2=end  3=center(arc/circle only)

# --- Structural ---
C("Coincident",  g1,p1, g2,p2)          # merge two points
C("Horizontal",  g)                      # g=geo index, p=0 (whole line)
C("Vertical",    g)
C("Parallel",    g1, g2)
C("Perpendicular",g1, g2)
C("Equal",       g1, g2)
C("PointOnObject",g1,p1, g2)            # pt on line/axis; g2=-1 Xaxis, -2 Yaxis

# --- Centering (Symmetric) ---
# ThirdPos=0 means axis-as-LINE (verified, tutorials use this consistently)
C("Symmetric", g,1, g,2, -2,0)          # center line g on Y-axis (X-centering)
C("Symmetric", g,1, g,2, -1,0)          # center line g on X-axis (Y-centering)
# Two Symmetric + DistanceX + DistanceY = fully constrained centered rect (12 constraints)

# --- Dimensional ---
C("DistanceX", g,p, value)              # absolute X of point  (can be negative)
C("DistanceY", g,p, value)              # absolute Y of point
C("DistanceX", g1,p1, g2,p2, value)    # horizontal span between two points
C("DistanceY", g1,p1, g2,p2, value)    # vertical span
C("Distance",  g, length)              # line length
C("Radius",    g, r)
C("Diameter",  g, d)
C("Angle",     g, angle_rad)

# --- Constraint index tracking ---
ci = len(sk.Constraints)               # index of NEXT constraint to be added
                                        # sk.ConstraintCount does NOT exist
# Bind to spreadsheet:
sk.setExpression(f'.Constraints[{ci}]', 'Parameter.BW')   # positive
sk.setExpression(f'.Constraints[{ci}]', '-Parameter.BW / 2')  # negative OK

# --- Attachment (FreeCAD 1.0) ---
sk.AttachmentSupport = (doc.getObject("XY_Plane"), [""])   # NOT AttachSupport
sk.MapMode = "FlatFace"
sk.setExpression('AttachmentOffset.Base.z', 'Parameter.BH')
```

## Modeling Workflow

1. **Plan roughly** — feature order, dimensions, wall thickness. No detail overengineering.
2. **Build one feature at a time** — `doc.recompute()` + inspect after each:
```python
s = feature.Shape
print(f"Edges:{len(s.Edges)} Faces:{len(s.Faces)} valid:{s.isValid()}")
for i,e in enumerate(s.Edges):
    bb=e.BoundBox; print(f"  Edge{i+1}: L={e.Length:.1f} Z={bb.ZMin:.1f}..{bb.ZMax:.1f}")
```
3. **Inspection drives next step** — which edges appeared? what Z? which is Tip? Then write next feature.
4. **Dress-up last** — Chamfer/Fillet after all Pad/Pocket. Select edges from current topology.

Rule: the more unknown the topology, the more inspection steps. Hollows, pockets, multi-body → inspect after every feature.

## Datum Plane Coordinate Systems

| Plane | Sketch-X | Sketch-Y | Pad direction |
|-------|----------|----------|---------------|
| `XY_Plane` | World-X | World-Y | +Z |
| `XZ_Plane` | World-X | World-Z | +Y |
| `YZ_Plane` | World-Y | World-Z | +X |

Missing axis in plane name = pad direction.

## Attachment Offset — Local Coordinate System

`AttachmentOffset.Base` is in **local plane coordinates**, not world:

| Plane | Local-X→World | Local-Y→World | Local-Z→World (normal) |
|-------|--------------|--------------|------------------------|
| XY_Plane | World-X | World-Y | World-Z |
| XZ_Plane | World-X | World-Z | World-Y |
| YZ_Plane | World-Y | World-Z | World-X |

```python
# Move sketch to World-Z=45 on XY_Plane → use Local-Z:
sk.AttachmentOffset = App.Placement(App.Vector(0, 0, 45), App.Rotation())  # ✓

# Move sketch to World-Z=42 on YZ_Plane → use Local-Y (NOT Local-Z!):
sk.AttachmentOffset = App.Placement(App.Vector(0, 42, 0), App.Rotation())  # ✓
# WRONG: App.Vector(0, 0, 42) → moves 42mm in World-X instead
```

Empirically verified with DistanceX/DistanceY point constraints.

## Multi-Body: XY_Plane per Body

Each Body has its own Origin. Naming follows suffix pattern:
- Body 1 → `Origin`, `XY_Plane`, `XZ_Plane`, `YZ_Plane`
- Body 2 → `Origin001`, `XY_Plane001`, …

```python
def get_plane(body, doc, name="XY_Plane"):
    for obj in body.Group:
        if obj.TypeId == "App::Origin":
            suffix = obj.Name[len("Origin"):]  # "" or "001", "002"…
            p = doc.getObject(f"{name}{suffix}")
            if p: return p
    return doc.getObject(name)  # fallback
```

## Pocket Direction with Z-Offset Sketch

Pocket on XY_Plane cuts in **-Z** (opposite to sketch normal). Use this to hollow a box from the top:

```python
sk.AttachmentOffset = App.Placement(App.Vector(0, 0, BH), App.Rotation())  # sketch at top
pkt.Length = BH - BT   # cuts from z=BH down to z=BT

# Pad with Reversed=True also grows downward (-Z):
pad.Length = RH
pad.Reversed = True  # sketch at z=45 → pad grows to z=45-RH
```

## Revolution — Confirmed Working Config

**YZ_Plane + V_Axis** works for revolution around World-Z axis. Also: `(sk, ["Axis"])` if a construction line defines the axis in the sketch.

## Revolution Profile — Self-Intersection Bug

If a stepped profile has two horizontal segments at the **same Z height** (e.g., outer step at Z=40 AND inner shoulder at Z=40) → lines overlap → `Face.isValid()=False` → Revolution produces wrong result (partial shape only).

**Fix:** Place inner and outer steps at **different Z heights** (≥1 layer height apart).

## Hollow Profile — Two Concentric Rectangles in One Sketch

Two closed contours in one sketch → FreeCAD auto-detects outer/inner boundary → hollow cross-section when padded.

```python
add_rect(sk, 0, 0, outer_w, outer_d, g=0)  # outer contour: idx 0-3
add_rect(sk, 0, 0, inner_w, inner_d, g=4)  # inner contour: idx 4-7
```

`add_rect` helper — **Variant A (Symmetric, preferred)**:
```python
def add_rect(sk, cx, cy, w, h, g=0):
    # geometry
    hw,hh = w/2,h/2; x0,y0 = cx-hw,cy-hh; x1,y1 = cx+hw,cy+hh
    sk.addGeometry(Part.LineSegment(App.Vector(x0,y0,0),App.Vector(x1,y0,0)))  # g+0 bottom
    sk.addGeometry(Part.LineSegment(App.Vector(x1,y0,0),App.Vector(x1,y1,0)))  # g+1 right
    sk.addGeometry(Part.LineSegment(App.Vector(x1,y1,0),App.Vector(x0,y1,0)))  # g+2 top
    sk.addGeometry(Part.LineSegment(App.Vector(x0,y1,0),App.Vector(x0,y0,0)))  # g+3 left
    # structural
    sk.addConstraint(Sketcher.Constraint("Coincident",g+0,2,g+1,1))
    sk.addConstraint(Sketcher.Constraint("Coincident",g+1,2,g+2,1))
    sk.addConstraint(Sketcher.Constraint("Coincident",g+2,2,g+3,1))
    sk.addConstraint(Sketcher.Constraint("Coincident",g+3,2,g+0,1))
    sk.addConstraint(Sketcher.Constraint("Horizontal",g+0))
    sk.addConstraint(Sketcher.Constraint("Horizontal",g+2))
    sk.addConstraint(Sketcher.Constraint("Vertical",  g+1))
    sk.addConstraint(Sketcher.Constraint("Vertical",  g+3))
    # centering via Symmetric (verified, ThirdPos=0 = axis-as-line)
    # NOTE: only works for g=0 (uses global axes). For g>0 use Variant B below.
    if cx == 0 and cy == 0 and g == 0:
        sk.addConstraint(Sketcher.Constraint("Symmetric",g+0,1,g+0,2,-2,0))  # Y-axis
        sk.addConstraint(Sketcher.Constraint("Symmetric",g+1,1,g+1,2,-1,0))  # X-axis
        ci = len(sk.Constraints)
        sk.addConstraint(Sketcher.Constraint("DistanceX",g+0,1,g+0,2, w))
        sk.addConstraint(Sketcher.Constraint("DistanceY",g+1,1,g+1,2, h))
    else:  # Variant B: position anchor via DistanceX/Y (needed for offset rects)
        ci = len(sk.Constraints)
        sk.addConstraint(Sketcher.Constraint("DistanceX",g+0,1, x0))
        sk.addConstraint(Sketcher.Constraint("DistanceY",g+0,1, y0))
        sk.addConstraint(Sketcher.Constraint("DistanceX",g+0,1,g+0,2, w))
        sk.addConstraint(Sketcher.Constraint("DistanceY",g+1,1,g+1,2, h))
    return ci  # index of first dimensional constraint (for setExpression)
```

## Known API Traps

| Symptom | Cause | Fix |
|---------|-------|-----|
| `AttributeError: no attribute 'Symmetric'` | Wrong property name | Use `pad.Midplane = True` |
| `DoF = -2` on parallelogram | `Equal` + `Parallel` redundant on closed quad | Remove `Equal` |
| `Standard_NullObject` on Pocket | Upstream feature invalid | Check DoF=0 and shape validity first |
| `Standard_NullObject` on SubtractiveHelix | Boolean failure at surface boundary | Use Part::Helix + Part::Sweep + Part::Cut instead |
| FreeCAD freezes on `App.newDocument()` | GUI call from background thread | Server dispatches to Qt main thread via signal |
| Sketch at wrong world position | AttachmentOffset Z moves along plane normal, not World-Z | Map local offset axes per table above |
| Revolution produces only partial shape | Profile self-intersection at same Z | Offset inner/outer steps to different Z heights |

## Build Discipline

- `sk.solve()` must return `0` before adding Pad/Pocket
- One feature at a time — recompute + inspect after each
- On error: read traceback, fix that line, re-run — do not rewrite the whole script
- Chamfer/Fillet last — keep all edges sharp while design is evolving
- `chamfer.Base` = the **Tip feature** (last feature before dress-up), not the Body

## Selective Chamfer — Filter Edges by Z Position

```python
shape = pocket.Shape  # Tip feature
BH = 45.0             # Z height to exclude

chamfer_edges = [
    f"Edge{i+1}" for i,e in enumerate(shape.Edges)
    if not (abs(e.BoundBox.ZMin-BH)<0.01 and abs(e.BoundBox.ZMax-BH)<0.01)
]
chamfer = doc.addObject("PartDesign::Chamfer","Chamfer")
body.addObject(chamfer)
chamfer.Base = (pocket, chamfer_edges)
chamfer.Size = 2.0
doc.recompute()
```

Pad+Pocket hollow box: 24 total edges, 8 at top (4 outer + 4 inner), 16 chamferable → 72 after chamfer.

## All-Edges Chamfer/Fillet

```python
all_edges = [f"Edge{i}" for i in range(1, len(pad.Shape.Edges)+1)]
chamfer = doc.addObject("PartDesign::Chamfer","Chamfer")
body.addObject(chamfer)
chamfer.Base = (pad, all_edges)
chamfer.Size = 3.0
# Fillet: same pattern, use fillet.Radius instead of chamfer.Size
```

Edge count changes after chamfer (box 12→48). Build edge list dynamically, never hardcode.

## Thread (Helix+Sweep+Cut) — Live-Validated M8 Recipe

**Key findings from live M8x50 session:**

1. **Helix muss 90° um Z rotiert werden** — startet dann bei (0, R, Pz) statt (R, 0, Pz)
2. **Thread-Sketch-Rotation = 120° um (1,1,1)** — entspricht Quaternion (0.5,0.5,0.5,0.5)
   - Sketch lokal X → Welt Y (radial), Sketch lokal Y → Welt Z (axial)
   - Sketch Normal → Welt X → Sketch liegt in der YZ-Ebene
3. **Part::Cut schlägt lautlos fehl** — Boolean gibt Basis-Shape zurück (gleiche Faces-Zahl)
   - Lösung: `body_sh.cut(sweep_sh, 0.01)` mit Toleranz 0.01 direkt auf Shapes
   - Ergebnis als `Part::Feature` ins Dokument schreiben
4. **Sweep Faces=5 ist korrekt** — 3 Helix-Seitenflächen + 2 Endkappen (topologisch)
5. **Sketch-Pz muss nicht am Helix-Start sein** — Frenet=True platziert das Profil automatisch

```python
# M8-Gewinde Gesamtrezept (Part/CSG, FreeCAD 1.0, live getestet)
import Part, Sketcher

MAJOR_R = 4.0;  PITCH = 1.25;  MINOR_R = MAJOR_R - 0.6495*PITCH;  CUT_R = MAJOR_R + 0.25

# Helix: 90° um Z → startet bei (0, R, Pz)
helix.Placement = App.Placement(App.Vector(0,0,-2), App.Rotation(App.Vector(0,0,1), 90))

# Thread-Sketch: 120° um (1,1,1) → lokal_x=Y-radial, lokal_y=Z-axial
sk.Placement = App.Placement(App.Vector(0,0,0), App.Rotation(App.Vector(1,1,1), 120))
# Dreieck in Sketch-Lokal: (CUT_R, ±PITCH/2) außen, (MINOR_R, 0) innen (Kern)
p_bot = App.Vector(CUT_R,  -PITCH/2, 0)
p_mid = App.Vector(MINOR_R, 0.0,     0)
p_top = App.Vector(CUT_R,  +PITCH/2, 0)

# Sweep: Frenet=True, Solid=True → spine=(helix,["Edge1"])

# Boolean: NICHT Part::Cut Dokument-Objekt → schlägt fehl!
# Stattdessen: Shape-Level mit Toleranz
result_sh = body_sh.cut(sweep_sh, 0.01)   # ✓
feat = doc.addObject("Part::Feature", "Schraube")
feat.Shape = result_sh
```

## DSL Generator — Known Traps (live-validated)

| Symptom | Ursache | Fix |
|---------|---------|-----|
| Boss-Loch fehlt / in der Luft | `_build_pocket(face="top")` nimmt `bb.ZMax` der gesamten Shape, nicht Boss-Oberkante | Direkt `Part.makeCylinder` + `.cut()` mit expliziter Z-Position |
| Blaues Artefakt / koplanare Flächen beim Boss-Fuse | Boss-Zylinder startet exakt auf der Shell-Innenbodenfläche (z=thickness) | `SINK=0.1`: Boss 0.1mm tiefer starten → `makeCylinder(r, h+0.1, _v(cx,cy,z-0.1))` |
| `face="top"` in Shell → falsches Z | Shell hat `bb.ZMax` = Wandhöhe, nicht Innenboden | `cz_base` Parameter übergeben (= Shell-Wandstärke) |

## DSL Generator — Known Gaps (not yet live-tested)

- `PartDesign::AdditiveLoft` — invalid in example file (version compat?), Python API untested
- `PartDesign::Groove` — syntax understood, not yet scripted live
- `PartDesign::MultiTransform` — not yet scripted
- Assembly Workbench joint API (FreeCAD 1.0+) — not documented

---

## FreeCAD 1.0 — Live-Validated API Details

### Sketch Attachment (FreeCAD 1.0)

Property is **`AttachmentSupport`** — not `AttachSupport`, not `Support`:

```python
sk.AttachmentSupport = (doc.getObject("XY_Plane"), [""])  # ✓
sk.MapMode = "FlatFace"
# sk.AttachSupport = ...  # ✗ wrong name
```

To discover attachment properties on any sketch object:
```python
[p for p in sk.PropertiesList if 'attach' in p.lower() or 'support' in p.lower()]
# → ['AttacherEngine','AttacherType','AttachmentOffset','AttachmentSupport','MapMode',...]
```

### Constraint Index Tracking

```python
ci = len(sk.Constraints)   # ✓ index of next constraint to be added
# sk.ConstraintCount       # ✗ does not exist
```

Rect helper pattern — returns `ci` so caller can bind expressions:

```python
def add_rect(sk, cx, cy, w, h, g=0):
    # ... geometry + structural constraints ...
    ci = len(sk.Constraints)
    sk.addConstraint(Sketcher.Constraint("DistanceX", g+0,1, cx-w/2))  # ci+0 pos X
    sk.addConstraint(Sketcher.Constraint("DistanceY", g+0,1, cy-h/2))  # ci+1 pos Y
    sk.addConstraint(Sketcher.Constraint("DistanceX", g+0,1,g+0,2, w)) # ci+2 width
    sk.addConstraint(Sketcher.Constraint("DistanceY", g+1,1,g+1,2, h)) # ci+3 height
    return ci
```

### DistanceX/Y accepts negative position values

```python
sk.addConstraint(Sketcher.Constraint("DistanceX", 0,1, -40.0))  # ✓ e.g. x0=-BW/2
```

### Expressions on Constraints and Placement (FreeCAD 1.0)

```python
# Constraint values — negative expressions work:
sk.setExpression(f'.Constraints[{ci+0}]', '-Parameter.BW / 2')       # ✓
sk.setExpression(f'.Constraints[{ci+2}]', 'Parameter.BW')             # ✓

# AttachmentOffset driven by spreadsheet:
sk.AttachmentOffset = App.Placement(App.Vector(0, 0, BH), App.Rotation())
sk.setExpression('AttachmentOffset.Base.z', 'Parameter.BH')           # ✓

# Feature lengths:
pad.setExpression('Length', 'Parameter.BH')                           # ✓
pocket.setExpression('Length', 'Parameter.BH - Parameter.BF')         # ✓
chamfer.setExpression('Size', 'Parameter.CF')                         # ✓
```

### Parametric open box — proven recipe

```
Body
├── Sk_Aussen  AttachmentSupport=XY_Plane, MapMode=FlatFace
│              Constraints[ci+0..3] → -BW/2, -BD/2, BW, BD
├── Pad        Length → Parameter.BH
├── Sk_Innen   AttachmentSupport=XY_Plane, AttachmentOffset.Base.z → Parameter.BH
│              Constraints[ci+0..3] → -(BW-2BT)/2, -(BD-2BT)/2, BW-2BT, BD-2BT
├── Pocket     Length → Parameter.BH - Parameter.BF
└── Chamfer    edges where ZMin≈ZMax≈0, Size → Parameter.CF
```

Result at BW=80 BD=50 BH=30 BT=2.5 BF=2.0: Edges=24 Faces=11 valid=True

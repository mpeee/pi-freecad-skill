# FreeCAD DSL Generator

Load when: user wants to build a FreeCAD model — always prefer DSL over raw Sketcher code.

## Architecture

```
User (natural language)
    ↓  LLM produces JSON only
fc_dsl.json  (design intent, no constraints)
    ↓  fc_generator.py (deterministic, tested recipes)
FreeCAD 3D model
```

**Why DSL?** Sketcher constraints = constraint solver = LLM failure mode.
DSL hides all that: the generator knows wire construction, tolerance tricks, boolean ordering.

## Usage in FreeCAD

```python
exec(open("D:/marek/projects/test-freecad-skill/fc-scripts/fc_generator.py").read())
doc = generate(DSL)   # DSL is a Python dict
```

The generator file is synced: global scope + project fc-scripts/ copy.
After editing the global, always run:
```bash
cp /home/marekp/.pi/freecad-scripts/fc_generator.py \
   /mnt/d/marek/projects/test-freecad-skill/fc-scripts/fc_generator.py
```

## DSL Schema

### Sketch types (used in pad / pocket / revolution)

| type | required fields | optional |
|------|----------------|---------|
| `rect` | `w`, `h` | `cx=0`, `cy=0` |
| `circle` | `r` | `cx=0`, `cy=0` |
| `polygon` | `r`, `n` | `cx=0`, `cy=0` |
| `slot` | `l` (center-to-center), `r` (end radius) | `cx=0`, `cy=0` |

### Feature types

| type | required | optional |
|------|----------|---------|
| `pad` | `sketch`, `height` | `cz=0` |
| `box` | `w`, `d`, `h` | `cx=0 cy=0 cz=0` |
| `cylinder` | `r`, `h` | `cx=0 cy=0 cz=0` |
| `revolution` | `sketch`, `height` | `angle=360`, `axis="Z"`, `cz=0` |
| `pocket` | `on`, `sketch`, `depth` | `face="top"` (or `"bottom"`), depth can be `"through"` |
| `fillet` | `on`, `r` | `edges="all"` / `"top"` / `"bottom"` / `"vertical"` |
| `chamfer` | `on`, `size` | `edges="all"` / `"top"` / `"bottom"` |
| `fuse` | `parts:[id,…]` | — |
| `cut` | `base`, `tool` | — |
| `metric_bolt` | `size`, `length` | `head="DIN912"`, `thread_length="full"`, `cx cy cz` |
| `metric_nut` | `size` | `cx cy cz` |

**`on` chaining:** each step should reference the **previous step's id**, not the original body.  
`body → hole_l → hole_r → fillet` ← correct chain.

### Supported bolt/nut sizes
M2, M3, M4, M5, M6, M8, M10, M12, M16, M20

## LLM Prompt Template

When the user describes a part, output **only** a JSON block using the schema above.
Rules:
- No FreeCAD Python code
- No Sketcher constraints
- All positions in mm, origin = part center (XY), Z=0 = bottom
- Chain operations: each step references the previous step's `id`
- Use `fillet`/`chamfer` **last** (after all pockets)
- For `through` holes: `"depth":"through"`
- Prefer `circle` sketches for holes, `rect` for pads, `polygon` for hex profiles
- `metric_bolt`/`metric_nut` handles everything internally — never manually build threads

### Example — Mounting Plate

User: *"Mounting plate 100×60×8mm, 4 corner holes M5 clearance (r=3), center slot 30×6, fillet top edges r=1"*

```json
{
  "document": "MountingPlate",
  "parts": [
    {"id":"base", "type":"pad", "sketch":{"type":"rect","w":100,"h":60}, "height":8},
    {"id":"h1","type":"pocket","on":"base","sketch":{"type":"circle","r":3,"cx":-40,"cy":-25},"depth":"through"},
    {"id":"h2","type":"pocket","on":"h1",  "sketch":{"type":"circle","r":3,"cx": 40,"cy":-25},"depth":"through"},
    {"id":"h3","type":"pocket","on":"h2",  "sketch":{"type":"circle","r":3,"cx":-40,"cy": 25},"depth":"through"},
    {"id":"h4","type":"pocket","on":"h3",  "sketch":{"type":"circle","r":3,"cx": 40,"cy": 25},"depth":"through"},
    {"id":"sl","type":"pocket","on":"h4",  "sketch":{"type":"slot","l":30,"r":3},              "depth":"through"},
    {"id":"fin","type":"fillet","on":"sl","edges":"top","r":1}
  ]
}
```

### Example — DIN912 Bolt

User: *"M6 socket cap screw, 30mm long"*

```json
{
  "document": "Bolt_M6x30",
  "parts": [
    {"id":"bolt","type":"metric_bolt","size":"M6","length":30,"head":"DIN912","thread_length":"full"}
  ]
}
```

## Implementation Status (live-tested)

| Feature | Status | DSL type |
|---------|--------|----------|
| pad (rect, circle, polygon, slot) | ✅ | `pad` |
| pocket (depth / through, top/bottom) | ✅ | `pocket` |
| fillet / chamfer (top, bottom, all, vertical) | ✅ | `fillet` / `chamfer` |
| box, cylinder primitives | ✅ | `box` / `cylinder` |
| revolution around Z/X/Y | ✅ | `revolution` |
| fuse / cut (Shape-level, tol=0.01) | ✅ | `fuse` / `cut` |
| **polar_pattern** (n holes on circle) | ✅ | `polar_pattern` |
| **linear_pattern** (nx×ny grid) | ✅ | `linear_pattern` |
| **shell** (hollow solid, open face) | ✅ | `shell` |
| **counterbore** (Stufenbohrung) | ✅ | `counterbore` |
| **countersink** (Kegelsenk) | ✅ | `countersink` |
| **mirror** (across XY/XZ/YZ, fuse) | ✅ | `mirror` |
| metric_bolt M2–M20 (DIN912, thread, hex socket) | ✅ | `metric_bolt` |
| metric_nut M2–M20 | ✅ | `metric_nut` |
| pocket on side faces (non-XY) | ❌ not yet | — |
| **boss** (Stützpunkt mit Einpressmutter-Loch) | ✅ | `boss` |
| **standoff** (freistehender Abstandshalter) | ✅ | `standoff` |
| **boss_array** (mehrere Bosses auf einmal) | ✅ | `boss_array` |
| **standoff_array** (mehrere Standoffs) | ✅ | `standoff_array` |
| polar/linear pattern on side faces | ❌ not yet | — |
| loft / pipe along path | ❌ not yet | — |
| spring (helix sweep) | ❌ not yet | — |

## New Feature DSL Examples

### polar_pattern
```json
{"id":"holes", "type":"polar_pattern", "on":"body",
 "sketch":{"type":"circle","r":4.5},
 "n":6, "radius":35, "depth":"through", "angle0":0}
```

### linear_pattern
```json
{"id":"grid", "type":"linear_pattern", "on":"body",
 "sketch":{"type":"circle","r":3}, "depth":"through",
 "nx":4, "dx":20, "ny":2, "dy":15, "cx":0, "cy":0}
```

### shell
```json
{"id":"box", "type":"shell", "on":"solid",
 "thickness":2, "open_face":"top"}   // or "bottom" / "none"
```

### counterbore (Senkbohrung für Zylinderkopfschrauben)
```json
{"id":"cb", "type":"counterbore", "on":"body",
 "cx":0, "cy":0,
 "drill_r":2.75, "cbore_r":4.5, "cbore_depth":4,
 "drill_depth":"through"}
```
Faustregel DIN912: `cbore_r = head_d/2`, `cbore_depth = head_h`

### countersink (Kegelsenk für Senkkopfschrauben)
```json
{"id":"cs", "type":"countersink", "on":"body",
 "cx":0, "cy":0,
 "drill_r":1.7, "csink_r":3.5, "csink_angle":90,
 "drill_depth":"through"}
```
DIN 7991 (90°): `csink_r ≈ drill_r * 2`, `csink_angle=90`

### mirror
```json
{"id":"sym", "type":"mirror", "on":"half_body",
 "plane":"YZ"}   // or XZ / XY
// combine: "fuse" (default) | "keep" (only mirrored half)
```
**Wichtig:** Spiegelachse geht immer durch den Ursprung (0,0,0).

| Feature | Status |
|---------|--------|
| pad (rect, circle, polygon, slot) | ✅ |
| pocket (depth / through, top/bottom face) | ✅ |
| fillet / chamfer (top, bottom, all, vertical) | ✅ |
| box, cylinder primitives | ✅ |
| revolution around Z/X/Y | ✅ |
| fuse / cut (Shape-level, tol=0.01) | ✅ |
| metric_bolt (M2–M20, DIN912 head, hex socket, tip chamfer) | ✅ |
| metric_nut (hex body + through hole) | ✅ |
| polar pattern | ❌ not yet |
| linear pattern | ❌ not yet |
| loft / pipe | ❌ not yet |
| face-attached pocket (non-XY faces) | ❌ not yet |

# FDM 3D Print Design Rules

Standard profile: 0.4 mm nozzle, 0.2 mm layer height, well-calibrated printer.

## Resolution Systems — Key Concept

FDM has two distinct precision systems:

**XY (toolhead positioning):**
- Position accuracy: ±0.1 mm
- Extrusion width: 0.75×–1.25× nozzle (0.3–0.5 mm with 0.4 mm nozzle)
- Min wall: 0.4 mm printable (vase mode) but structurally weak; use ≥0.8 mm for load-bearing
- Gap between walls: <0.4 mm → fuses or not printed

**Z (layer stacking):**
- Layer height = Z resolution (same thing)
- Configurable per Z position (variable layer height in PrusaSlicer/Cura)
- Use fine layers (0.1 mm) for curved Z features; coarse (0.3 mm) for straight walls
- Min robust feature: 3 layers

**Design rules:**
- Wall thickness: multiples of nozzle diameter (0.8, 1.2, 1.6, 2.0 mm…)
- XY gaps to print: ≥0.4 mm
- Z gaps: ≥0.4 mm (2 layers); print-in-place: ≥0.4–0.5 mm material-dependent

## Strength

- Parts ~3× weaker across layers than along → tensile forces must run parallel to layers
- Strength from perimeters, not infill → increase perimeter count, not infill %
- Fillet all internal corners (stress concentration)
- Solid rectangular sections more reliable than I-beams in FDM

## Chamfers vs Fillets (print orientation matters)

| Edge | Use | Reason |
|------|-----|--------|
| Horizontal (parallel to layers) | Chamfer | Constant overhang angle |
| Vertical (perpendicular to layers) | Fillet | Smooth toolpath, less ringing |

Fillet on horizontal edges droops (near-vertical overhang at start).

## Holes

- Horizontal holes <6 mm: teardrop (90° point at top)
- Horizontal holes large: flat roof bridge, offset 0.2–0.4 mm above center
- Vertical holes: 120° teardrop to control seam placement
- Force seam away from critical surfaces: add small notch on hidden face

## Tolerances

| Feature | Deviation |
|---------|-----------|
| Flat surfaces | ±0.1 mm/surface |
| Vertical circles | undersized |
| Outer circles | slightly undersized |

- Interference fits: use hex/square holes (not circular) — elastic deformation, no cracking
- Crush ribs: undersize rib ~0.2 mm, oversize bore ~0.4 mm — single assembly only
- Grip fins: elastic → reassemblable

## Support-Free Design

- Overhangs ≤45° need no support
- Split parts when no single orientation works
- Sacrificial bridge layer for internal overhangs
- Holes in material cost MORE (add surface area = more perimeters)

## Fasteners

| Thread method | Strength | Reuse |
|--------------|---------|-------|
| Tapped plastic | Low | Poor |
| Rib thread-forming | Low–Med | Poor |
| Heat-set inserts | High | Excellent |
| Embedded nuts | High | Excellent |

- Dynamic loads: use threadlock or locknut
- Max screw length → compression loading → plastics handle compression better

## Materials

| | PLA | PETG | ABS | ASA | TPU |
|--|-----|------|-----|-----|-----|
| Heat | 55–60°C | 70–80°C | 90°C+ | 90°C+ | medium |
| UV | poor | poor | poor | excellent | medium |
| Warp | low | low-med | high | high | low |
| Print | easy | medium | hard | hard | tricky |

- PLA: prototypes, indoors
- PETG: functional, better layer bonding
- ASA: outdoor, UV-stable ABS replacement
- TPU: flex parts, gaskets, flexures

## Checklist

```
[ ] Print orientation → tensile forces parallel to layers
[ ] Overhangs ≤45° or teardrop/bridge/chamfer
[ ] No supports needed (or split part)
[ ] Horizontal holes: teardrop or flat roof
[ ] Wall thickness: multiples of nozzle diameter
[ ] Interference fits: hex/square holes + crush ribs
[ ] Print-in-place clearance ≥0.4 mm
[ ] Flexures have hard stops
[ ] Dynamic screws: threadlock or locknut
[ ] Heat-set inserts for reusable threads
```

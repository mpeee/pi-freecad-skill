# OpenSCAD / NopSCADlib

## Use when

| Situation | Prefer |
|---|---|
| Fast generation from existing OpenSCAD / NopSCADlib code | OpenSCAD bridge |
| Standard printed parts, enclosures, fixtures, mechanical solids needing later FreeCAD edits | FreeCAD DSL / Part API first |
| Vitamins / standard printed helper geometry already available in NopSCADlib | NopSCADlib bridge |
| Dimension-driven solids that must stay editable in FreeCAD feature tree | Native FreeCAD modeling |

## Setup

1. Install OpenSCAD on Windows
2. Clone NopSCADlib locally
3. Make one of these paths valid:
   - `NOPSCADLIB_DIR=<abs Windows path>` before launching FreeCAD
   - `<workspace>/vendor/NopSCADlib`
   - `<workspace>/NopSCADlib`
4. Load script library helper: `freecad_script_run(name="nopscadlib_bridge")`

## Bundled helper

Project script library contains `nopscadlib_bridge.py`.
Main functions after loading it:

```python
check_nopscadlib_setup()
render_nopscadlib(scad_body, name="Part", import_mode="shape")
render_scad_file(scad_file, name="Part", import_mode="shape")
```

## Typical workflow

```python
check_nopscadlib_setup()

part = render_nopscadlib(
    name="TubeClamp",
    scad_body='''
include <vitamins/screws.scad>

difference() {
    cylinder(h = 14, r = 15, $fn = 96);
    translate([0,0,-1]) cylinder(h = 16, r = 11, $fn = 96);
    translate([-20,-1,4]) cube([40,2,8]);
}
'''
)
```

## Rules

- Prefer `import_mode="shape"` for downstream Booleans, measurements, exports
- Fall back to `import_mode="mesh"` if STL-to-shape conversion fails
- Treat imported geometry as external/generated source; keep the SCAD source as the master model
- If later FreeCAD edits are required, use the imported shape only as reference or as a Boolean tool
- For assemblies with many vitamins, render only the needed subset; full-library imports become slow quickly

## Path / include rules

- Bridge passes `-I <nopscadlib_dir>` to OpenSCAD
- Therefore `include <lib.scad>` works from the bridge helper
- Extra includes inside `scad_body` should be relative to the NopSCADlib root unless intentionally absolute

## Failure patterns

| Symptom | Fix |
|---|---|
| `OpenSCAD not found` | Install OpenSCAD or set `OPENSCAD_EXE` |
| `NopSCADlib not found` | Set `NOPSCADLIB_DIR` or clone into `vendor/NopSCADlib` |
| Render succeeds, shape import fails | Retry with `import_mode="mesh"` |
| Boolean on imported part fails | Keep as mesh reference, or remodel critical features natively in FreeCAD |
| Missing modules/includes | Use correct relative include path from NopSCADlib root |

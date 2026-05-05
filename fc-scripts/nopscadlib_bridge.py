"""
nopscadlib_bridge.py — Render NopSCADlib / OpenSCAD code into FreeCAD.

Workflow:
  1. Run this script once with freecad_script_run("nopscadlib_bridge")
  2. Call render_nopscadlib(...) or render_scad_file(...)

Setup expectations:
  - OpenSCAD installed on Windows
  - NopSCADlib cloned locally, e.g.:
      D:/cad/vendor/NopSCADlib
      <workspace>/vendor/NopSCADlib
  - Optional environment variable in Windows before launching FreeCAD:
      NOPSCADLIB_DIR=D:/cad/vendor/NopSCADlib

Example:
    part = render_nopscadlib(
        name="TubeClamp",
        scad_body='''
include <vitamins/screws.scad>

module tube_clamp() {
    difference() {
        cylinder(h = 14, r = 15, $fn = 96);
        translate([0,0,-1]) cylinder(h = 16, r = 11, $fn = 96);
        translate([-20,-1,4]) cube([40,2,8]);
    }
}

tube_clamp();
'''
    )
"""

import os
import re
import shutil
import subprocess
import tempfile
import uuid

import Mesh
import Part


def _slug(name):
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_") or "nopscadlib_part"


def _workspace_candidates():
    cwd = os.getcwd().replace("\\", "/")
    return [
        f"{cwd}/vendor/NopSCADlib",
        f"{cwd}/NopSCADlib",
        "D:/cad/vendor/NopSCADlib",
        "D:/vendor/NopSCADlib",
        "C:/cad/vendor/NopSCADlib",
        "C:/Users/Public/NopSCADlib",
    ]


def find_openscad(custom_path=None):
    candidates = [p for p in [
        custom_path,
        os.environ.get("OPENSCAD_EXE"),
        shutil.which("openscad.exe"),
        shutil.which("openscad"),
        "C:/Program Files/OpenSCAD/openscad.exe",
        "C:/Program Files (x86)/OpenSCAD/openscad.exe",
        os.path.expandvars("%LOCALAPPDATA%/Programs/OpenSCAD/openscad.exe"),
    ] if p]

    for path in candidates:
        norm = path.replace("\\", "/")
        if os.path.exists(norm):
            return norm
    raise FileNotFoundError(
        "OpenSCAD not found. Set OPENSCAD_EXE or install OpenSCAD in a standard Windows location."
    )


def find_nopscadlib(custom_dir=None):
    candidates = [p for p in [
        custom_dir,
        os.environ.get("NOPSCADLIB_DIR"),
        *_workspace_candidates(),
    ] if p]

    for path in candidates:
        norm = path.replace("\\", "/")
        if os.path.exists(f"{norm}/lib.scad"):
            return norm
    raise FileNotFoundError(
        "NopSCADlib not found. Clone it locally and set NOPSCADLIB_DIR, "
        "or place it in ./vendor/NopSCADlib relative to the FreeCAD working directory."
    )


def check_nopscadlib_setup(openscad=None, nopscadlib_dir=None):
    openscad = find_openscad(openscad)
    nop_dir = find_nopscadlib(nopscadlib_dir)
    info = {
        "openscad": openscad,
        "nopscadlib": nop_dir,
        "ok": True,
    }
    print(info)
    return info


def _make_scad_source(scad_body, includes=None, use_lib=True):
    lines = []
    if use_lib:
        lines.append("include <lib.scad>")
    for inc in includes or []:
        lines.append(f"include <{inc}>")
    lines.append("")
    lines.append(scad_body.strip())
    lines.append("")
    return ";\n".join(line.rstrip(";") for line in lines)


def _import_stl_as_mesh(stl_path, name, doc):
    Mesh.insert(stl_path, doc.Name)
    obj = doc.ActiveObject
    obj.Label = name
    return obj


def _import_stl_as_shape(stl_path, name, doc, tolerance=0.05):
    mesh = Mesh.Mesh(stl_path)
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, tolerance)
    shape = shape.removeSplitter()

    final_shape = shape
    try:
        if getattr(shape, "Solids", None):
            if len(shape.Solids) == 1:
                final_shape = shape.Solids[0]
            else:
                final_shape = Part.Compound(shape.Solids)
        elif getattr(shape, "Faces", None):
            shell = Part.Shell(shape.Faces)
            final_shape = Part.makeSolid(shell)
    except Exception:
        final_shape = shape

    obj = doc.addObject("Part::Feature", _slug(name))
    obj.Label = name
    obj.Shape = final_shape
    return obj


def render_nopscadlib(
    scad_body,
    name="NopSCADlibPart",
    doc=None,
    openscad=None,
    nopscadlib_dir=None,
    includes=None,
    use_lib=True,
    import_mode="shape",
    timeout=180,
):
    doc = doc or App.ActiveDocument or App.newDocument("NopSCADlib")
    openscad = find_openscad(openscad)
    nop_dir = find_nopscadlib(nopscadlib_dir)

    job = _slug(name) + "_" + uuid.uuid4().hex[:8]
    work_dir = tempfile.mkdtemp(prefix="fc_nopscadlib_")
    scad_path = os.path.join(work_dir, f"{job}.scad").replace("\\", "/")
    stl_path = os.path.join(work_dir, f"{job}.stl").replace("\\", "/")

    scad_source = _make_scad_source(scad_body, includes=includes, use_lib=use_lib)
    with open(scad_path, "w", encoding="utf-8") as f:
        f.write(scad_source)

    cmd = [openscad, "-I", nop_dir, "-o", stl_path, scad_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    if result.returncode != 0 or not os.path.exists(stl_path):
        raise RuntimeError(
            "OpenSCAD render failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout[-2000:]}\n"
            f"STDERR:\n{result.stderr[-4000:]}"
        )

    if import_mode == "mesh":
        obj = _import_stl_as_mesh(stl_path, name, doc)
    else:
        try:
            obj = _import_stl_as_shape(stl_path, name, doc)
        except Exception as exc:
            print(f"Shape conversion failed, falling back to mesh: {exc}")
            obj = _import_stl_as_mesh(stl_path, name, doc)

    doc.recompute()

    try:
        import FreeCADGui as Gui
        Gui.ActiveDocument.ActiveView.viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass

    print({
        "name": name,
        "openscad": openscad,
        "nopscadlib": nop_dir,
        "stl": stl_path,
        "import_mode": import_mode,
    })
    return obj


def render_scad_file(
    scad_file,
    name="ScadFile",
    doc=None,
    openscad=None,
    nopscadlib_dir=None,
    import_mode="shape",
    timeout=180,
):
    with open(scad_file, "r", encoding="utf-8") as f:
        body = f.read()
    return render_nopscadlib(
        scad_body=body,
        name=name,
        doc=doc,
        openscad=openscad,
        nopscadlib_dir=nopscadlib_dir,
        use_lib=False,
        import_mode=import_mode,
        timeout=timeout,
    )

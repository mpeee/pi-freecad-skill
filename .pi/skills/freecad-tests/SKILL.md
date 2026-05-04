---
name: freecad-tests
description: Test suite for the freecad-remote skill and extension. Runs showcase scenarios against a live FreeCAD instance and validates results programmatically. Use /skill:freecad-tests to execute all tests. Requires FreeCAD running with freecad_server.py macro loaded.
---

# FreeCAD Test Suite

Run each test scenario in order. For every test:
1. Execute the setup code via `freecad_run`
2. Execute the validation code via `freecad_run`
3. Report `[PASS]` or `[FAIL]` with actual vs expected values
4. Clean up test objects after each test

At the end, print a summary: total passed / total run.

Do NOT stop on failure — run all tests and report all results.

---

## Pre-flight

Before running any scenario, verify the connection:

```python
# freecad_run:
"'.'.join(FreeCAD.Version()[:2])"
```

If this fails → report "SKIP ALL: FreeCAD not reachable" and stop.

Create a fresh test document and keep it active throughout:

```python
import FreeCAD as App
if "FC_TestDoc" in App.listDocuments():
    App.closeDocument("FC_TestDoc")
doc = App.newDocument("FC_TestDoc")
_result = doc.Name
```

Expected result: `"FC_TestDoc"`

---

## T01 — Basic Execution

**Goal:** Verify the remote execution channel works correctly.

```python
# T01a — eval path
"2 + 2"
# Expected result: 4

# T01b — exec path with _result
"x = 7; _result = x * 6"
# Expected result: 42

# T01c — print output
"print('FC_TEST_MARKER')"
# Expected output contains: FC_TEST_MARKER

# T01d — NameError without import
"Part.makeBox(1,1,1)"
# Expected: error contains "NameError"

# T01e — import works
"import Part; s = Part.makeBox(1,1,1); _result = s.ShapeType"
# Expected result: "Solid"
```

---

## T02 — Document & Object Management

**Goal:** Verify document operations and object lifecycle.

```python
# Setup: create a box object
import FreeCAD as App
doc = App.getDocument("FC_TestDoc")
obj = doc.addObject("Part::Box", "T02_Box")
obj.Length = 100.0
obj.Width  = 50.0
obj.Height = 30.0
doc.recompute()
_result = doc.getObject("T02_Box").Label
```
Expected result: `"T02_Box"`

```python
# Validate dimensions
obj = App.getDocument("FC_TestDoc").getObject("T02_Box")
bb = obj.Shape.BoundBox
_result = (round(bb.XLength,1), round(bb.YLength,1), round(bb.ZLength,1))
```
Expected result: `[100.0, 50.0, 30.0]` (as list, rounding may vary)

```python
# Validate shape is valid solid
obj = App.getDocument("FC_TestDoc").getObject("T02_Box")
_result = obj.Shape.isValid() and len(obj.Shape.Solids) == 1
```
Expected result: `True`

**Cleanup:**
```python
App.getDocument("FC_TestDoc").removeObject("T02_Box")
App.getDocument("FC_TestDoc").recompute()
```

---

## T03 — CSG Boolean Operations

**Goal:** Verify boolean operations produce valid geometry.

```python
# Setup: box minus cylinder (hole through the box)
import Part, FreeCAD as App
doc = App.getDocument("FC_TestDoc")

box = Part.makeBox(100, 50, 30)
# Cylinder positioned at centre of top face, tall enough to cut through
cyl = Part.makeCylinder(8, 35, App.Vector(50, 25, -3))
result = box.cut(cyl)

feat = doc.addObject("Part::Feature", "T03_Cut")
feat.Shape = result
doc.recompute()
```

```python
# Validate: valid solid, correct face count
obj = App.getDocument("FC_TestDoc").getObject("T03_Cut")
s = obj.Shape
_result = {
    "valid":  s.isValid(),
    "solid":  s.ShapeType == "Solid",
    "solids": len(s.Solids),
    "xlen":   round(s.BoundBox.XLength, 1),
}
```
Expected: `valid=True`, `solid=True`, `solids=1`, `xlen=100.0`

**Cleanup:**
```python
App.getDocument("FC_TestDoc").removeObject("T03_Cut")
App.getDocument("FC_TestDoc").recompute()
```

---

## T04 — Spreadsheet-Driven Dimensions

**Goal:** Verify spreadsheet parameters drive object properties.

```python
# Setup: spreadsheet + expression-driven box
import FreeCAD as App
doc = App.getDocument("FC_TestDoc")

ss = doc.addObject("Spreadsheet::Sheet", "T04_Params")
ss.set("A1", "length")
ss.set("B1", "80 mm")
ss.setAlias("B1", "t04_length")
doc.recompute()

box = doc.addObject("Part::Box", "T04_Box")
box.setExpression("Length", "T04_Params.t04_length")
box.Width  = 40.0
box.Height = 20.0
doc.recompute()

_result = round(doc.getObject("T04_Box").Length, 1)
```
Expected result: `80.0`

```python
# Modify via spreadsheet — box should follow
ss = App.getDocument("FC_TestDoc").getObject("T04_Params")
ss.set("B1", "120 mm")
App.getDocument("FC_TestDoc").recompute()
_result = round(App.getDocument("FC_TestDoc").getObject("T04_Box").Length, 1)
```
Expected result: `120.0`

**Cleanup:**
```python
doc = App.getDocument("FC_TestDoc")
doc.removeObject("T04_Box")
doc.removeObject("T04_Params")
doc.recompute()
```

---

## T05 — Script Library

**Goal:** Verify save / list / run / delete lifecycle of the script library.
Use the extension tools directly (not freecad_run).

**T05a — Save a project script:**
Call `freecad_script_save` with:
- name: `t05_test_part`
- description: `Test script for T05`
- code: (see below)
- scope: `project`

Script code to save:
```python
import Part, FreeCAD as App
doc = App.ActiveDocument or App.newDocument("T05Doc")
box = Part.makeBox(60, 40, 20)
feat = doc.addObject("Part::Feature", "T05_Part")
feat.Shape = box
doc.recompute()
print(f"T05: BoundBox {feat.Shape.BoundBox.XLength}x{feat.Shape.BoundBox.YLength}x{feat.Shape.BoundBox.ZLength}")
```

Expected: saved successfully, file visible in `fc-scripts/t05_test_part.py`

**T05b — List scripts:**
Call `freecad_script_list(scope="project")`
Expected: `t05_test_part` appears in the list

**T05c — Run the saved script:**
Call `freecad_script_run(name="t05_test_part")`
Expected output contains: `T05: BoundBox 60.0x40.0x20.0`

**T05d — Show script source:**
Call `freecad_script_show(name="t05_test_part")`
Expected: source code is printed, contains `makeBox(60`

**T05e — Delete the script:**
Call `freecad_script_delete(name="t05_test_part")`
Then call `freecad_script_list(scope="project")`
Expected: `t05_test_part` no longer in list

**Cleanup (FreeCAD side):**
```python
import FreeCAD as App
if "T05_Part" in [o.Name for o in App.ActiveDocument.Objects]:
    App.ActiveDocument.removeObject("T05_Part")
    App.ActiveDocument.recompute()
```

---

## T06 — Error Recovery

**Goal:** Verify that errors in FreeCAD code are reported correctly and the session remains usable.

```python
# Send broken code
"import Part\nresult = Part.makeBox(100, 50, 'not_a_number')"
# Expected: error is reported (not a crash), session still works
```

Immediately after, verify the connection is still alive:
```python
"2 + 2"
# Expected result: 4
```

---

## T07 — Screenshot

**Goal:** Verify screenshot is saved on the Windows side.

Call `freecad_screenshot` with path `C:/Users/Public/fc_test_screenshot.png`

Then verify the file was created:
```python
import os
_result = os.path.exists("C:/Users/Public/fc_test_screenshot.png")
```
Expected result: `True`

If `False`: note that FreeCAD may need an active 3D view open for screenshots to work.

---

## Teardown

Close the test document:
```python
import FreeCAD as App
if "FC_TestDoc" in App.listDocuments():
    App.closeDocument("FC_TestDoc")
print("Test document closed")
```

---

## Summary Format

After all tests, print a table like this:

```
════════════════════════════════════════
 FreeCAD Test Suite Results
════════════════════════════════════════
 T01  Basic Execution          PASS (5/5)
 T02  Document & Objects       PASS (3/3)
 T03  CSG Boolean              PASS (1/1)
 T04  Spreadsheet Parameters   PASS (2/2)
 T05  Script Library           PASS (5/5)
 T06  Error Recovery           PASS (2/2)
 T07  Screenshot               PASS (1/1)
────────────────────────────────────────
 Total: 19/19 passed
════════════════════════════════════════
```

For any FAIL, include the actual vs expected values directly in the table.

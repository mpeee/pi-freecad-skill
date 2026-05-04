# Spreadsheet and Expressions — Parametric Variables

## Why
- Centralise all key dimensions in one named place
- Change one value → whole model updates automatically
- Avoid magic numbers scattered across sketches and features
- Works across workbenches: Sketcher constraints, PartDesign properties, Part properties

## Create a Spreadsheet (Python)
```python
ss = doc.addObject("Spreadsheet::Sheet", "Params")

# Set cell content (row = letter, col = number, 1-indexed)
ss.set("A1", "wall_thickness")   # descriptive label in column A
ss.set("B1", "22 mm")            # value with unit in column B
ss.set("A2", "inner_width")
ss.set("B2", "465 mm")
ss.set("A3", "inner_depth")
ss.set("B3", "376 mm")

# Set aliases — required for referencing from expressions
ss.setAlias("B1", "wall_thickness")
ss.setAlias("B2", "inner_width")
ss.setAlias("B3", "inner_depth")

doc.recompute()
```

## Reference Cells From Expressions (Python)
```python
# Drive an object property from the spreadsheet
obj.setExpression("Length", "Params.inner_width")
obj.setExpression("Width",  "Params.inner_depth")
obj.setExpression("Height", "Params.wall_thickness * 2")

# Clear an expression (make property manually editable again)
obj.clearExpression("Length")
```

## Reference by Name vs. Label
- Internal Name (e.g. `Spreadsheet001`) — always works, shown in Selection panel
- Label (e.g. `Params`) — use `<<Params>>.alias` with double angle brackets
- **Prefer internal Name** — labels can be duplicated in a document

```python
# These are equivalent if internal name == label:
"Params.wall_thickness"
"<<Params>>.wall_thickness"

# If label ≠ internal name, you MUST use the internal name:
"Spreadsheet001.wall_thickness"
```

## Expression Syntax Rules
```
# Always attach units when mixing with dimensioned properties
Params.width + 5 mm       ✓
Params.width + 5          ✗  (dimensionless + length = error)

# Tricky unit pitfalls
1/2mm       →  1/(2mm)  =  0.5 mm⁻¹    (WRONG — write 0.5 mm)
sqrt(2)mm   →  invalid                   (WRONG — write sqrt(2) * 1 mm)

# Operators
+ - * / % ^

# Constants
pi  e

# Conditional
x > 0 ? x : 0            (ternary: condition ? valueTrue : valueFalse)

# Functions
abs(x)  ceil(x)  floor(x)  round(x)  sqrt(x)  pow(x;y)
log(x)  log10(x)  exp(x)
sin(x)  cos(x)  tan(x)  asin(x)  acos(x)  atan(x)  atan2(y;x)
hypot(x;y)

# Trig uses degrees by default; for radians append "rad":
cos(pi rad / 4)   ==   cos(45)
```

## Reading Object Properties Into Spreadsheet
```python
# In a cell formula (GUI cell editor):
=Box.Length          # reads Box.Length property
=Cylinder.Radius * 2
```
**Rule:** a spreadsheet can read from an object OR write to it — **never both** (circular dependency).
Use two separate spreadsheets if you need both.

## Drive Sketcher Constraints From Spreadsheet
In the Sketcher GUI:
- Double-click a dimensional constraint → set expression: `Params.wall_thickness`

In Python (naming a constraint first):
```python
# Name a constraint (index = position in sketch.Constraints list)
sk.renameConstraint(0, "width")

# Set expression on named constraint
sk.setExpression("Constraints.width", "Params.inner_width")
```

## Alias Best Practices
- Use `snake_case` names: `wall_thickness`, `inner_width`, `beam_height`
- Keep one spreadsheet per concern: `Params` for inputs, separate sheet for derived values
- Document every alias with a label in the adjacent cell (column A = description, column B = value)

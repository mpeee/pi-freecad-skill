"""
FreeCAD Bridge Module
=====================
Provides a unified interface to FreeCAD operations.
When running inside FreeCAD's Python interpreter, the real FreeCAD modules
are available.  In testing / CI environments the module falls back to a
lightweight in-memory mock so that the rest of the skill can be exercised
without a FreeCAD installation.
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Attempt to import real FreeCAD bindings
# ---------------------------------------------------------------------------
try:
    import FreeCAD          # noqa: F401  (available inside FreeCAD)
    import FreeCADGui       # noqa: F401  (GUI layer – may not be present in CLI mode)
    import Part             # noqa: F401  (geometry kernel)
    _FREECAD_AVAILABLE = True
    logger.info("FreeCAD bindings loaded successfully.")
except ImportError:
    _FREECAD_AVAILABLE = False
    logger.warning(
        "FreeCAD Python bindings not found – running in mock/simulation mode."
    )


# ---------------------------------------------------------------------------
# Mock implementation used when FreeCAD is not installed
# ---------------------------------------------------------------------------

class _MockDocument:
    """Minimal in-memory document that mimics the FreeCAD Document API."""

    def __init__(self, name: str = "Unnamed"):
        self.Name = name
        self._objects: dict[str, dict] = {}

    # ---- object management ------------------------------------------------

    def addObject(self, type_str: str, name: str) -> dict:
        obj = {"type": type_str, "name": name, "Label": name, "properties": {}}
        self._objects[name] = obj
        return obj

    def removeObject(self, name: str) -> None:
        self._objects.pop(name, None)

    def getObject(self, name: str):
        return self._objects.get(name)

    def recompute(self) -> None:
        pass

    # ---- serialisation ----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.Name,
            "objects": list(self._objects.values()),
        }


class _MockFreeCAD:
    """Thin shim that exposes the subset of FreeCAD used by this skill."""

    def __init__(self):
        self._doc: _MockDocument | None = None

    # ---- document helpers -------------------------------------------------

    def newDocument(self, name: str = "Unnamed") -> _MockDocument:
        self._doc = _MockDocument(name)
        return self._doc

    def activeDocument(self) -> _MockDocument | None:
        return self._doc

    def getActiveDocument(self) -> _MockDocument | None:
        return self._doc

    # ---- shape creation (simplified) --------------------------------------

    def makeBox(self, doc: _MockDocument, name: str, l: float, w: float, h: float) -> dict:
        obj = doc.addObject("Part::Box", name)
        obj["properties"].update({"Length": l, "Width": w, "Height": h})
        doc.recompute()
        return obj

    def makeSphere(self, doc: _MockDocument, name: str, radius: float) -> dict:
        obj = doc.addObject("Part::Sphere", name)
        obj["properties"].update({"Radius": radius})
        doc.recompute()
        return obj

    def makeCylinder(self, doc: _MockDocument, name: str, radius: float, height: float) -> dict:
        obj = doc.addObject("Part::Cylinder", name)
        obj["properties"].update({"Radius": radius, "Height": height})
        doc.recompute()
        return obj

    def makeCone(self, doc: _MockDocument, name: str, radius1: float, radius2: float, height: float) -> dict:
        obj = doc.addObject("Part::Cone", name)
        obj["properties"].update({"Radius1": radius1, "Radius2": radius2, "Height": height})
        doc.recompute()
        return obj


# ---------------------------------------------------------------------------
# Public bridge – chooses real or mock implementation at runtime
# ---------------------------------------------------------------------------

class FreeCADBridge:
    """
    High-level interface used by the skill server.

    All methods return plain Python dicts so they can be serialised directly
    to JSON for the HTTP responses.
    """

    def __init__(self):
        if _FREECAD_AVAILABLE:
            import FreeCAD as _fc
            import Part as _part
            self._fc = _fc
            self._part = _part
            self._mock = None
        else:
            self._fc = None
            self._part = None
            self._mock = _MockFreeCAD()
            self._mock.newDocument("Prototype")

    # ------------------------------------------------------------------ #
    #  Document helpers
    # ------------------------------------------------------------------ #

    def _get_doc(self):
        if self._mock:
            return self._mock.activeDocument()
        return self._fc.activeDocument()

    def get_document_info(self) -> dict:
        doc = self._get_doc()
        if doc is None:
            return {"error": "No active document"}
        if self._mock:
            return doc.to_dict()
        return {
            "name": doc.Name,
            "objects": [
                {"name": o.Name, "label": o.Label, "type": o.TypeId}
                for o in doc.Objects
            ],
        }

    def new_document(self, name: str = "Prototype") -> dict:
        if self._mock:
            self._mock.newDocument(name)
        else:
            self._fc.newDocument(name)
        return {"status": "ok", "document": name}

    def reset_document(self) -> dict:
        return self.new_document()

    # ------------------------------------------------------------------ #
    #  Shape primitives
    # ------------------------------------------------------------------ #

    def create_box(self, name: str = "Box", length: float = 10.0,
                   width: float = 10.0, height: float = 10.0) -> dict:
        doc = self._get_doc()
        if doc is None:
            self.new_document()
            doc = self._get_doc()

        if self._mock:
            obj = self._mock.makeBox(doc, name, length, width, height)
        else:
            obj = doc.addObject("Part::Box", name)
            obj.Length = length
            obj.Width = width
            obj.Height = height
            doc.recompute()
            obj = {"name": obj.Name, "type": "Part::Box",
                   "properties": {"Length": length, "Width": width, "Height": height}}

        return {"status": "ok", "object": obj}

    def create_sphere(self, name: str = "Sphere", radius: float = 5.0) -> dict:
        doc = self._get_doc()
        if doc is None:
            self.new_document()
            doc = self._get_doc()

        if self._mock:
            obj = self._mock.makeSphere(doc, name, radius)
        else:
            obj = doc.addObject("Part::Sphere", name)
            obj.Radius = radius
            doc.recompute()
            obj = {"name": obj.Name, "type": "Part::Sphere",
                   "properties": {"Radius": radius}}

        return {"status": "ok", "object": obj}

    def create_cylinder(self, name: str = "Cylinder", radius: float = 5.0,
                        height: float = 10.0) -> dict:
        doc = self._get_doc()
        if doc is None:
            self.new_document()
            doc = self._get_doc()

        if self._mock:
            obj = self._mock.makeCylinder(doc, name, radius, height)
        else:
            obj = doc.addObject("Part::Cylinder", name)
            obj.Radius = radius
            obj.Height = height
            doc.recompute()
            obj = {"name": obj.Name, "type": "Part::Cylinder",
                   "properties": {"Radius": radius, "Height": height}}

        return {"status": "ok", "object": obj}

    def create_cone(self, name: str = "Cone", radius1: float = 5.0,
                    radius2: float = 0.0, height: float = 10.0) -> dict:
        doc = self._get_doc()
        if doc is None:
            self.new_document()
            doc = self._get_doc()

        if self._mock:
            obj = self._mock.makeCone(doc, name, radius1, radius2, height)
        else:
            obj = doc.addObject("Part::Cone", name)
            obj.Radius1 = radius1
            obj.Radius2 = radius2
            obj.Height = height
            doc.recompute()
            obj = {"name": obj.Name, "type": "Part::Cone",
                   "properties": {"Radius1": radius1, "Radius2": radius2, "Height": height}}

        return {"status": "ok", "object": obj}

    # ------------------------------------------------------------------ #
    #  Object management
    # ------------------------------------------------------------------ #

    def list_objects(self) -> dict:
        return self.get_document_info()

    def delete_object(self, name: str) -> dict:
        doc = self._get_doc()
        if doc is None:
            return {"error": "No active document"}
        if self._mock:
            if doc.getObject(name) is None:
                return {"error": f"Object '{name}' not found"}
            doc.removeObject(name)
        else:
            obj = doc.getObject(name)
            if obj is None:
                return {"error": f"Object '{name}' not found"}
            doc.removeObject(name)
            doc.recompute()
        return {"status": "ok", "deleted": name}

    # ------------------------------------------------------------------ #
    #  Utility
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_mock() -> bool:
        return not _FREECAD_AVAILABLE

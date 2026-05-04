"""
Tests for the Pi FreeCAD Skill server and bridge (mock/simulation mode).
All tests run without a FreeCAD installation.
"""

import json
import sys
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

# Ensure the repo root is on the path so we can import our modules directly.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from freecad_bridge import FreeCADBridge, _FREECAD_AVAILABLE  # noqa: E402
from server import SkillHandler, bridge, run  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _start_server(host="127.0.0.1", port=15001):
    """Start the skill server in a daemon thread and return (server, thread)."""
    from http.server import HTTPServer
    server = HTTPServer((host, port), SkillHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    # Give the server a moment to bind
    time.sleep(0.1)
    return server, t


def _request(method: str, path: str, body: dict | None = None, port: int = 15001):
    """Send an HTTP request to the test server and return (status, json_body)."""
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else b""
    conn.request(method, path, body=data, headers=headers)
    resp = conn.getresponse()
    status = resp.status
    content = json.loads(resp.read().decode())
    conn.close()
    return status, content


# ---------------------------------------------------------------------------
# Unit tests – FreeCADBridge (mock mode)
# ---------------------------------------------------------------------------

class TestFreeCADBridgeMock(unittest.TestCase):

    def setUp(self):
        self.b = FreeCADBridge()
        # Always start with a fresh document
        self.b.new_document("TestDoc")

    def test_is_mock_when_freecad_not_installed(self):
        if _FREECAD_AVAILABLE:
            self.skipTest("FreeCAD is installed – skipping mock-only test")
        self.assertTrue(self.b.is_mock())

    def test_get_document_info(self):
        info = self.b.get_document_info()
        self.assertIn("name", info)
        self.assertIn("objects", info)

    def test_create_box(self):
        result = self.b.create_box(name="MyBox", length=20, width=15, height=5)
        self.assertEqual(result["status"], "ok")
        obj = result["object"]
        self.assertEqual(obj["name"], "MyBox")
        self.assertEqual(obj["properties"]["Length"], 20)
        self.assertEqual(obj["properties"]["Width"], 15)
        self.assertEqual(obj["properties"]["Height"], 5)

    def test_create_sphere(self):
        result = self.b.create_sphere(name="MySphere", radius=7.5)
        self.assertEqual(result["status"], "ok")
        obj = result["object"]
        self.assertEqual(obj["name"], "MySphere")
        self.assertEqual(obj["properties"]["Radius"], 7.5)

    def test_create_cylinder(self):
        result = self.b.create_cylinder(name="MyCyl", radius=3, height=12)
        self.assertEqual(result["status"], "ok")
        obj = result["object"]
        self.assertEqual(obj["name"], "MyCyl")
        self.assertEqual(obj["properties"]["Radius"], 3)
        self.assertEqual(obj["properties"]["Height"], 12)

    def test_create_cone(self):
        result = self.b.create_cone(name="MyCone", radius1=6, radius2=0, height=10)
        self.assertEqual(result["status"], "ok")
        obj = result["object"]
        self.assertEqual(obj["name"], "MyCone")

    def test_list_objects_after_creation(self):
        self.b.create_box(name="BoxA")
        self.b.create_sphere(name="SphereA")
        info = self.b.list_objects()
        names = [o["name"] for o in info["objects"]]
        self.assertIn("BoxA", names)
        self.assertIn("SphereA", names)

    def test_delete_object(self):
        self.b.create_box(name="TempBox")
        result = self.b.delete_object("TempBox")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["deleted"], "TempBox")
        # Should no longer appear in the list
        info = self.b.list_objects()
        names = [o["name"] for o in info["objects"]]
        self.assertNotIn("TempBox", names)

    def test_delete_nonexistent_object(self):
        result = self.b.delete_object("DoesNotExist")
        self.assertIn("error", result)

    def test_reset_document(self):
        self.b.create_box(name="Temp")
        self.b.reset_document()
        info = self.b.get_document_info()
        self.assertEqual(info["objects"], [])


# ---------------------------------------------------------------------------
# Integration tests – HTTP server
# ---------------------------------------------------------------------------

class TestSkillServer(unittest.TestCase):

    _server = None
    _port = 15001

    @classmethod
    def setUpClass(cls):
        cls._server, _ = _start_server(port=cls._port)

    @classmethod
    def tearDownClass(cls):
        cls._server.shutdown()

    def setUp(self):
        # Reset document before each test for isolation
        _request("POST", "/document/reset", {}, port=self._port)

    # ---- health / info ----

    def test_health(self):
        status, body = _request("GET", "/health", port=self._port)
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_info(self):
        status, body = _request("GET", "/info", port=self._port)
        self.assertEqual(status, 200)
        self.assertIn("name", body)
        self.assertIn("version", body)
        self.assertIn("endpoints", body)

    def test_unknown_endpoint_returns_404(self):
        status, body = _request("GET", "/nonexistent", port=self._port)
        self.assertEqual(status, 404)

    # ---- document ----

    def test_get_document(self):
        status, body = _request("GET", "/document", port=self._port)
        self.assertEqual(status, 200)
        self.assertIn("objects", body)

    def test_reset_document(self):
        _request("POST", "/objects/box", {"name": "Temp"}, port=self._port)
        status, body = _request("POST", "/document/reset", {}, port=self._port)
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    # ---- create primitives ----

    def test_create_box(self):
        status, body = _request(
            "POST", "/objects/box",
            {"name": "HttpBox", "length": 30, "width": 20, "height": 10},
            port=self._port,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["object"]["name"], "HttpBox")

    def test_create_sphere(self):
        status, body = _request(
            "POST", "/objects/sphere",
            {"name": "HttpSphere", "radius": 8},
            port=self._port,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_create_cylinder(self):
        status, body = _request(
            "POST", "/objects/cylinder",
            {"name": "HttpCyl", "radius": 4, "height": 15},
            port=self._port,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_create_cone(self):
        status, body = _request(
            "POST", "/objects/cone",
            {"name": "HttpCone", "radius1": 5, "radius2": 1, "height": 12},
            port=self._port,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_create_with_defaults(self):
        # Body with no parameters – server should use defaults
        status, body = _request("POST", "/objects/box", {}, port=self._port)
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    # ---- list / delete ----

    def test_list_objects(self):
        _request("POST", "/objects/box", {"name": "ListBox"}, port=self._port)
        status, body = _request("GET", "/objects", port=self._port)
        self.assertEqual(status, 200)
        names = [o["name"] for o in body["objects"]]
        self.assertIn("ListBox", names)

    def test_delete_object(self):
        _request("POST", "/objects/sphere", {"name": "DelSphere"}, port=self._port)
        status, body = _request("DELETE", "/objects/DelSphere", port=self._port)
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_delete_nonexistent(self):
        status, body = _request("DELETE", "/objects/Ghost", port=self._port)
        self.assertEqual(status, 200)
        self.assertIn("error", body)

    def test_invalid_json_body(self):
        conn = HTTPConnection("127.0.0.1", self._port, timeout=5)
        conn.request("POST", "/objects/box", body=b"not-json",
                     headers={"Content-Type": "application/json",
                              "Content-Length": "8"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 400)
        conn.close()


if __name__ == "__main__":
    unittest.main()

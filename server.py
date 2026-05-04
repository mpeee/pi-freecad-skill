"""
Pi FreeCAD Skill – HTTP Server
===============================
A lightweight HTTP server (stdlib only) that exposes FreeCAD operations as a
REST API.  The Pi AI assistant (or any HTTP client) sends requests to this
server to create and manipulate 3-D objects inside FreeCAD.

Usage
-----
Run *inside* FreeCAD's macro console::

    exec(open("server.py").read())

Or from the command line (mock/simulation mode, no FreeCAD required)::

    python3 server.py [--host 127.0.0.1] [--port 5000]

Endpoints
---------
GET  /health                  – liveness probe
GET  /info                    – skill metadata
GET  /document                – current document state
POST /document/reset          – clear / create a new document
POST /objects/box             – create a box primitive
POST /objects/sphere          – create a sphere primitive
POST /objects/cylinder        – create a cylinder primitive
POST /objects/cone            – create a cone primitive
GET  /objects                 – list all objects
DELETE /objects/<name>        – remove an object by name
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from freecad_bridge import FreeCADBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_SKILL_VERSION = "0.1.0"
_SKILL_NAME = "pi-freecad-skill"

bridge = FreeCADBridge()


# ---------------------------------------------------------------------------
# JSON helper
# ---------------------------------------------------------------------------

def _json_response(handler: BaseHTTPRequestHandler,
                   data: Any,
                   status: int = 200) -> None:
    body = json.dumps(data, indent=2).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class SkillHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # suppress default noisy logging
        logger.info("%s - %s", self.address_string(), fmt % args)

    # ------------------------------------------------------------------ GET

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/health":
            _json_response(self, {"status": "ok", "mock": bridge.is_mock()})

        elif path == "/info":
            _json_response(self, {
                "name": _SKILL_NAME,
                "version": _SKILL_VERSION,
                "freecad_available": not bridge.is_mock(),
                "endpoints": [
                    "GET  /health",
                    "GET  /info",
                    "GET  /document",
                    "POST /document/reset",
                    "GET  /objects",
                    "POST /objects/box",
                    "POST /objects/sphere",
                    "POST /objects/cylinder",
                    "POST /objects/cone",
                    "DELETE /objects/<name>",
                ],
            })

        elif path == "/document":
            _json_response(self, bridge.get_document_info())

        elif path == "/objects":
            _json_response(self, bridge.list_objects())

        else:
            _json_response(self, {"error": "Not found"}, 404)

    # ----------------------------------------------------------------- POST

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            body = _read_json_body(self)
        except (json.JSONDecodeError, ValueError) as exc:
            _json_response(self, {"error": f"Invalid JSON: {exc}"}, 400)
            return

        if path == "/document/reset":
            name = body.get("name", "Prototype")
            _json_response(self, bridge.new_document(name))

        elif path == "/objects/box":
            result = bridge.create_box(
                name=body.get("name", "Box"),
                length=float(body.get("length", 10.0)),
                width=float(body.get("width", 10.0)),
                height=float(body.get("height", 10.0)),
            )
            _json_response(self, result)

        elif path == "/objects/sphere":
            result = bridge.create_sphere(
                name=body.get("name", "Sphere"),
                radius=float(body.get("radius", 5.0)),
            )
            _json_response(self, result)

        elif path == "/objects/cylinder":
            result = bridge.create_cylinder(
                name=body.get("name", "Cylinder"),
                radius=float(body.get("radius", 5.0)),
                height=float(body.get("height", 10.0)),
            )
            _json_response(self, result)

        elif path == "/objects/cone":
            result = bridge.create_cone(
                name=body.get("name", "Cone"),
                radius1=float(body.get("radius1", 5.0)),
                radius2=float(body.get("radius2", 0.0)),
                height=float(body.get("height", 10.0)),
            )
            _json_response(self, result)

        else:
            _json_response(self, {"error": "Not found"}, 404)

    # --------------------------------------------------------------- DELETE

    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        m = re.fullmatch(r"/objects/([^/]+)", path)
        if m:
            name = m.group(1)
            _json_response(self, bridge.delete_object(name))
        else:
            _json_response(self, {"error": "Not found"}, 404)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(host: str = "127.0.0.1", port: int = 5000) -> None:
    server = HTTPServer((host, port), SkillHandler)
    mode = "simulation/mock" if bridge.is_mock() else "live FreeCAD"
    logger.info("Pi FreeCAD Skill server starting on http://%s:%d  [%s]", host, port, mode)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pi FreeCAD Skill Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    args = parser.parse_args()
    run(args.host, args.port)

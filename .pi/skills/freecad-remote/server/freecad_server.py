# FreeCAD Remote Control Server
# Dieses Skript als Makro in FreeCAD laden:
#   Extras > Makros > Makro ausführen... > freecad_server.py
#
# Der Server bindet an 0.0.0.0:7978 – erreichbar von localhost
# und aus WSL2 über die Windows-Host-IP.

import socket
import threading
import queue
import json
import sys
import io
import traceback

PORT = 7978

try:
    import FreeCAD
    import FreeCADGui
    from PySide2 import QtCore
except ImportError:
    print("FEHLER: Dieses Skript muss innerhalb von FreeCAD ausgeführt werden.")
    raise


# Queue für Code-Ausführung im Main Thread
_request_queue = queue.Queue()


class _MainThreadRunner(QtCore.QObject):
    """Empfängt Code-Ausführungs-Requests im Qt-Main-Thread via Signal."""
    execute_signal = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self.execute_signal.connect(self._run, QtCore.Qt.QueuedConnection)

    def _run(self, item):
        code, result_container, event = item
        result_container.append(_execute_code_direct(code))
        event.set()

    def request(self, code: str) -> dict:
        result_container = []
        event = threading.Event()
        self.execute_signal.emit((code, result_container, event))
        if not event.wait(timeout=25):
            return {"result": None, "output": "", "stderr": "", "error": "Timeout: Main thread did not respond in 25s"}
        return result_container[0]


_runner = _MainThreadRunner()


def _execute_code_direct(code: str) -> dict:
    """Führt Python-Code direkt aus (muss im Main Thread aufgerufen werden)."""
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = buf_out = io.StringIO()
    sys.stderr = buf_err = io.StringIO()

    result_val = None
    error = None

    namespace = {
        "FreeCAD": FreeCAD,
        "FreeCADGui": FreeCADGui,
        "App": FreeCAD,
        "Gui": FreeCADGui,
    }

    try:
        try:
            result_val = eval(code, namespace)
        except SyntaxError:
            exec(code, namespace)
            result_val = namespace.get("_result")
    except Exception:
        error = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return {
        "result": _serialize(result_val),
        "output": buf_out.getvalue(),
        "stderr": buf_err.getvalue(),
        "error": error,
    }


def execute_code(code: str) -> dict:
    """Schickt Code zur Ausführung in den Qt-Main-Thread."""
    return _runner.request(code)


def _serialize(val):
    """Versucht, einen Wert JSON-serialisierbar zu machen."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, (list, tuple)):
        return [_serialize(v) for v in val]
    if isinstance(val, dict):
        return {str(k): _serialize(v) for k, v in val.items()}
    return repr(val)


def handle_client(conn):
    try:
        raw = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk
            if b"\n" in raw:
                break

        request = json.loads(raw.decode().strip())
        response = execute_code(request.get("code", ""))
        conn.sendall(json.dumps(response).encode() + b"\n")
    except Exception as e:
        try:
            conn.sendall(json.dumps({"error": str(e), "result": None, "output": "", "stderr": ""}).encode() + b"\n")
        except Exception:
            pass
    finally:
        conn.close()


def run_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("0.0.0.0", PORT))
    except OSError as e:
        FreeCAD.Console.PrintError(f"FreeCAD-Server: Port {PORT} bereits belegt: {e}\n")
        return

    srv.listen(10)
    FreeCAD.Console.PrintMessage(f"FreeCAD-Server gestartet auf 0.0.0.0:{PORT}\n")

    while True:
        try:
            conn, _ = srv.accept()
            t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
            t.start()
        except Exception:
            break


# Server in Hintergrund-Thread starten (daemon=True → endet mit FreeCAD)
_server_thread = threading.Thread(target=run_server, daemon=True)
_server_thread.start()

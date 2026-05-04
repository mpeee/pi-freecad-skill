#!/usr/bin/env python3
"""
fc – FreeCAD Remote CLI
Steuert eine laufende FreeCAD-Instanz über den freecad_server.py Socket-Server.

Verwendung:
  fc status                          Verbindung prüfen
  fc run <code>                      Python-Code in FreeCAD ausführen
  fc docs                            Offene Dokumente auflisten
  fc objects [--doc NAME]            Objekte im aktiven (oder benannten) Dokument
  fc get <obj> [<eigenschaft>]       Objekt-Info oder einzelne Eigenschaft
  fc set <obj> <eigenschaft> <wert>  Eigenschaft setzen
  fc script <datei.py>               Python-Skriptdatei in FreeCAD ausführen
  fc console                         Interaktive REPL
  fc screenshot [pfad]               Screenshot speichern
"""

import argparse
import json
import socket
import sys
import os
import readline  # noqa: F401  (für Pfeiltasten in der REPL)

PORT = int(os.environ.get("FC_PORT", "7978"))


def _default_host() -> str:
    """In WSL2 ist FreeCAD auf Windows – host.docker.internal oder resolv.conf."""
    if os.environ.get("FC_HOST"):
        return os.environ["FC_HOST"]
    # host.docker.internal ist in WSL2 immer der Windows-Host
    try:
        socket.getaddrinfo("host.docker.internal", None)
        return "host.docker.internal"
    except OSError:
        pass
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                if line.startswith("nameserver"):
                    return line.split()[1]
    except OSError:
        pass
    return "127.0.0.1"


HOST = _default_host()


# ---------------------------------------------------------------------------
# Kommunikation
# ---------------------------------------------------------------------------

class ConnectionError(Exception):
    pass


def send(code: str) -> dict:
    try:
        with socket.create_connection((HOST, PORT), timeout=10) as s:
            s.sendall(json.dumps({"code": code}).encode() + b"\n")
            raw = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                raw += chunk
                if b"\n" in raw:
                    break
        return json.loads(raw.decode().strip())
    except (OSError, socket.timeout) as e:
        raise ConnectionError(f"Keine Verbindung zu FreeCAD auf Port {PORT}: {e}") from e


def run_and_print(code: str, raw: bool = False) -> int:
    """Schickt Code, gibt Ausgabe aus. Gibt Exit-Code zurück."""
    try:
        resp = send(code)
    except ConnectionError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        print("  → Stelle sicher, dass freecad_server.py als Makro in FreeCAD läuft.", file=sys.stderr)
        return 1

    if resp.get("error"):
        print("Traceback (FreeCAD):", file=sys.stderr)
        print(resp["error"].rstrip(), file=sys.stderr)
        return 1

    if raw:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return 0

    if resp.get("output"):
        print(resp["output"].rstrip())
    if resp.get("stderr"):
        print(resp["stderr"].rstrip(), file=sys.stderr)
    if resp.get("result") is not None:
        print(resp["result"])

    return 0


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_status(_args):
    try:
        resp = send("'.'.join(FreeCAD.Version()[:2])")
    except ConnectionError as e:
        print(f"OFFLINE  {e}")
        return 1
    if resp.get("error"):
        print(f"FEHLER   {resp['error']}")
        return 1
    version = resp.get("result", "?")
    print(f"OK  FreeCAD {version}  (Port {PORT})")
    return 0


def cmd_run(args):
    code = " ".join(args.code)
    return run_and_print(code, raw=args.json)


def cmd_docs(args):
    code = """
docs = FreeCAD.listDocuments()
if not docs:
    print("(keine offenen Dokumente)")
else:
    for name, doc in docs.items():
        active = " [aktiv]" if doc == FreeCAD.ActiveDocument else ""
        print(f"  {name}{active}  –  {doc.FileName or '(ungespeichert)'}")
"""
    return run_and_print(code, raw=args.json)


def cmd_objects(args):
    doc_sel = f'FreeCAD.getDocument("{args.doc}")' if args.doc else "FreeCAD.ActiveDocument"
    code = f"""
doc = {doc_sel}
if doc is None:
    print("Kein Dokument gefunden.")
else:
    objs = doc.Objects
    if not objs:
        print("(Dokument leer)")
    else:
        print(f"Dokument: {{doc.Name}}  ({{len(objs)}} Objekte)")
        print()
        for o in objs:
            vis = "👁 " if hasattr(o, "Visibility") and o.Visibility else "   "
            print(f"  {{vis}}{{o.Name:<25}} {{o.TypeId:<35}} {{o.Label}}")
"""
    return run_and_print(code, raw=args.json)


def cmd_get(args):
    if args.prop:
        code = f"""
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{args.obj}")
if obj is None:
    print("Objekt nicht gefunden: {args.obj}")
else:
    val = getattr(obj, "{args.prop}", None)
    if val is None and "{args.prop}" not in obj.PropertiesList:
        print("Eigenschaft nicht gefunden: {args.prop}")
    else:
        print(repr(val))
"""
    else:
        code = f"""
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{args.obj}")
if obj is None:
    print("Objekt nicht gefunden: {args.obj}")
else:
    print(f"Name    : {{obj.Name}}")
    print(f"Label   : {{obj.Label}}")
    print(f"Typ     : {{obj.TypeId}}")
    print()
    for grp in obj.PropertiesList:
        try:
            val = getattr(obj, grp)
            print(f"  {{grp:<30}} = {{repr(val)}}")
        except Exception as e:
            print(f"  {{grp:<30}} ! {{e}}")
"""
    return run_and_print(code, raw=args.json)


def cmd_set(args):
    code = f"""
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{args.obj}")
if obj is None:
    print("Objekt nicht gefunden: {args.obj}")
else:
    setattr(obj, "{args.prop}", {args.value})
    doc.recompute()
    print(f"OK: {{obj.Name}}.{args.prop} = {{repr(getattr(obj, '{args.prop}'))}}")
"""
    return run_and_print(code, raw=args.json)


def cmd_screenshot(args):
    path = args.path or "/tmp/freecad_screenshot.png"
    abs_path = os.path.abspath(path)
    code = f"""
FreeCADGui.ActiveDocument.ActiveView.saveImage("{abs_path}", 1920, 1080)
print("Screenshot gespeichert: {abs_path}")
"""
    return run_and_print(code, raw=False)


def cmd_script(args):
    try:
        code = open(args.file).read()
    except OSError as e:
        print(f"Fehler: Datei nicht lesbar: {e}", file=sys.stderr)
        return 1
    return run_and_print(code, raw=args.json)


def cmd_console(_args):
    print(f"FreeCAD REPL  (Port {PORT})  –  Beenden mit Ctrl+D oder 'exit'")
    print()
    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line in ("exit", "quit"):
            break
        if not line:
            continue
        try:
            resp = send(line)
        except ConnectionError as e:
            print(f"Fehler: {e}", file=sys.stderr)
            break
        if resp.get("output"):
            print(resp["output"].rstrip())
        if resp.get("stderr"):
            print(resp["stderr"].rstrip(), file=sys.stderr)
        if resp.get("error"):
            print(resp["error"].rstrip(), file=sys.stderr)
        elif resp.get("result") is not None:
            print(resp["result"])


# ---------------------------------------------------------------------------
# Argument-Parser
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="fc",
        description="FreeCAD Remote CLI – steuert eine laufende FreeCAD-Instanz",
    )
    p.add_argument("--port", type=int, default=PORT, help=f"Server-Port (Standard: {PORT})")
    sub = p.add_subparsers(dest="cmd", required=True)

    # status
    sub.add_parser("status", help="Verbindung prüfen")

    # run
    r = sub.add_parser("run", help="Python-Code in FreeCAD ausführen")
    r.add_argument("code", nargs="+", help="Python-Ausdruck oder -Anweisung")
    r.add_argument("--json", action="store_true", help="Rohe JSON-Antwort ausgeben")

    # docs
    d = sub.add_parser("docs", help="Offene Dokumente auflisten")
    d.add_argument("--json", action="store_true")

    # objects
    o = sub.add_parser("objects", help="Objekte im Dokument auflisten")
    o.add_argument("--doc", metavar="NAME", help="Dokumentname (Standard: aktives)")
    o.add_argument("--json", action="store_true")

    # get
    g = sub.add_parser("get", help="Objekt-Info oder einzelne Eigenschaft lesen")
    g.add_argument("obj", help="Objekt-Name (z.B. Box)")
    g.add_argument("prop", nargs="?", help="Eigenschaftsname (optional)")
    g.add_argument("--json", action="store_true")

    # set
    s = sub.add_parser("set", help="Eigenschaft eines Objekts setzen")
    s.add_argument("obj", help="Objekt-Name")
    s.add_argument("prop", help="Eigenschaftsname")
    s.add_argument("value", help="Neuer Wert (Python-Ausdruck, z.B. 10.0 oder '\"rot\"')")
    s.add_argument("--json", action="store_true")

    # script
    sk = sub.add_parser("script", help="Python-Skriptdatei in FreeCAD ausführen")
    sk.add_argument("file", help="Pfad zur .py-Datei")
    sk.add_argument("--json", action="store_true")

    # screenshot
    sc = sub.add_parser("screenshot", help="3D-Ansicht als PNG speichern")
    sc.add_argument("path", nargs="?", help="Pfad (Standard: /tmp/freecad_screenshot.png)")

    # console
    sub.add_parser("console", help="Interaktive REPL")

    return p


COMMANDS = {
    "status": cmd_status,
    "run": cmd_run,
    "docs": cmd_docs,
    "objects": cmd_objects,
    "get": cmd_get,
    "set": cmd_set,
    "script": cmd_script,
    "screenshot": cmd_screenshot,
    "console": cmd_console,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    global PORT
    PORT = args.port

    fn = COMMANDS.get(args.cmd)
    if fn is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(fn(args) or 0)


if __name__ == "__main__":
    main()

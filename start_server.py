# start_server.py — FreeCAD Remote Server Starter
#
# Three ways to use this:
#
# 1. Paste into FreeCAD Python Console (View → Panels → Python Console):
#    exec(open(FreeCAD.getUserMacroDir(True) + "freecad_server.py").read())
#
# 2. Run as FreeCAD macro:
#    Extras → Makros → Makro ausführen → this file
#
# 3. One-liner for FreeCAD Python Console if server.py is somewhere else:
#    exec(open(r"C:\path\to\freecad_server.py").read())

import os

macro_dir = FreeCAD.getUserMacroDir(True)          # trailing slash included
server_script = os.path.join(macro_dir, "freecad_server.py")

if not os.path.exists(server_script):
    FreeCAD.Console.PrintError(
        f"freecad_server.py not found in {macro_dir}\n"
        "Run /freecad:setup in pi to install it.\n"
    )
else:
    exec(open(server_script).read())

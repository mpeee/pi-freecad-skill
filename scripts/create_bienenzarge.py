"""
╔══════════════════════════════════════════════════════════════════╗
║       SMART BIENENZARGE — LANGSTROTH-FORMAT (Full Depth)        ║
║       Masterplan & FreeCAD-Modell                               ║
╠══════════════════════════════════════════════════════════════════╣
║  Format:    Langstroth Full Depth                               ║
║             Innen 465×376mm, Rähmchen 448×232mm, 10 Rähmchen   ║
║                                                                  ║
║  Z-AUFBAU (Querschnitt von unten nach oben):                    ║
║                                                                  ║
║  Z=314  ╔══════════════════════════════════╗  Oberkante         ║
║         ║     BIENENRAUM (232mm)           ║  10 Rähmchen       ║
║         ║  Langstroth Full Depth, offen    ║                    ║
║  Z= 82  ╠══════════════════════════════════╣                    ║
║         ║  [→→ Absperrgitter gleitet ←←]   ║  Einführschlitz   ║
║  Z= 76  ╠══════════════════════════════════╣  vorne (Y=0)       ║
║         ║  MECHANIKRAUM (54mm)             ║                    ║
║         ║  Servo │ Schubstange │ Sensoren  ║                    ║
║  Z= 22  ╠══════════════════════════════════╣                    ║
║         ║░░░░░ BODENPLATTE 22mm ░░░░░░░░░░║                    ║
║  Z=  0  ╚══════════════════════════════════╝                    ║
║                                                                  ║
║  VORDERSEITE (Y=0):                                             ║
║  ┌──────────────────────────────────────────────────┐           ║
║  │               BIENENRAUM-WAND                    │           ║
║  ├──────────────────────────────────────────────────┤           ║
║  │  [Einführschlitz Absperrgitter ≈ Z=76]           │           ║
║  ├──────────────────────┬───────────────────────────┤           ║
║  │  Flugloch 120×8mm    │  Elektronikfach 80×50mm   │           ║
║  └──────────────────────┴───────────────────────────┘           ║
║                                                                  ║
║  MECHANIK (Absperrgitter):                                      ║
║  - Gitter gleitet in Y-Richtung (vorne ↔ hinten)               ║
║  - L-Profil-Schienen links+rechts führen das Gitter             ║
║  - Servo-Motor (MG996R) + Schubstange im Mechanikraum          ║
║  - Geschlossen: Gitter trennt Brutraum / Honigraum              ║
║  - Offen: Gitter nach hinten, freie Durchfahrt für Königin      ║
║                                                                  ║
║  ELEKTRONIK (Platzhalter):                                      ║
║  - ESP32 im Frontelektronikfach (USB zugänglich)                ║
║  - Motortreiber L298N im selben Fach                            ║
║  - DHT22 Temperatursensor + Waagezellen im Boden                ║
╚══════════════════════════════════════════════════════════════════╝
"""

import FreeCAD as App
import Part

# ── Neues Dokument ────────────────────────────────────────────────

doc_name = "Smart_Bienenzarge_Langstroth"
if doc_name in App.listDocuments():
    App.closeDocument(doc_name)
doc = App.newDocument(doc_name)

# ── Hauptabmessungen (Langstroth Full Depth) ──────────────────────

iW  = 465.0   # Innenbreite  X  (Langstroth-Standard)
iD  = 376.0   # Innentiefe   Y
wT  = 22.0    # Wandstärke
fT  = 22.0    # Bodenstärke
mH  = 54.0    # Mechanikraum-Höhe (Servo + Absperrgitter)
bH  = 232.0   # Bienenraum-Höhe   (Langstroth Full Depth)

oW  = iW + 2 * wT    # 509mm
oD  = iD + 2 * wT    # 420mm
oH  = fT + mH + bH   # 308mm

zBoden = fT           # Z=22:  Innenboden
zMech  = fT + mH      # Z=76:  Bienenraum-Unterkante
agZ    = zMech - 4.0  # Z=72:  Absperrgitter-Niveau (Mitte Führungsnut)

# ── Hilfsfunktion Farbe ───────────────────────────────────────────

def clr(feat, rgb, transp=0):
    try:
        feat.ViewObject.ShapeColor = rgb
        feat.ViewObject.Transparency = transp
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════
# 1. ZARGENKORPUS
# ════════════════════════════════════════════════════════════════

outer = Part.makeBox(oW, oD, oH)
inner = Part.makeBox(iW, iD, mH + bH, App.Vector(wT, wT, fT))
shell = outer.cut(inner)

# Flugloch: 120×8mm, vorne mittig, im unteren Mechanikbereich
fl_w, fl_h = 120.0, 8.0
fl_z = zBoden + 14.0
shell = shell.cut(Part.makeBox(
    fl_w, wT + 2, fl_h,
    App.Vector((oW - fl_w) / 2, -1, fl_z)
))

# Absperrgitter-Einführschlitz: volle Innenbreite, 5mm hoch
shell = shell.cut(Part.makeBox(
    iW, wT + 2, 5.0,
    App.Vector(wT, -1, agZ)
))

# Elektronikfach: 80×50mm, 28mm tief, vorne rechts
elec_x = (oW + fl_w) / 2 + 15
elec_z = zBoden + 3.0
elec_w, elec_h, elec_d = 80.0, 50.0, 28.0
shell = shell.cut(Part.makeBox(
    elec_w, elec_d, elec_h,
    App.Vector(elec_x, 0, elec_z)
))

# Kabelkanal: verbindet Elektronikfach mit Mechanikraum-Innenraum
shell = shell.cut(Part.makeBox(
    20.0, wT + 5, 10.0,
    App.Vector(elec_x + 30, 0, elec_z + elec_h / 2)
))

korpus = doc.addObject('Part::Feature', 'Zargenkorpus')
korpus.Shape = shell
korpus.Label = 'Zargenkorpus Langstroth (Holz 22mm)'
clr(korpus, (0.78, 0.60, 0.38))


# ════════════════════════════════════════════════════════════════
# 2. FÜHRUNGSSCHIENEN (L-Profil, links + rechts)
# ════════════════════════════════════════════════════════════════

rail_t  = 12.0
lower_h = 5.0
upper_h = 3.0
gap     = 3.0   # Spielraum für 2mm-Gitterblech

for name, rx in [('Schiene_L', wT), ('Schiene_R', wT + iW - rail_t)]:
    lower = Part.makeBox(rail_t, iD, lower_h, App.Vector(rx, wT, agZ - lower_h))
    upper = Part.makeBox(rail_t, iD, upper_h, App.Vector(rx, wT, agZ + gap))
    rail  = lower.fuse(upper)
    f = doc.addObject('Part::Feature', name)
    f.Shape = rail
    f.Label = f'Führungsschiene {"Links" if "L" in name else "Rechts"}'
    clr(f, (0.55, 0.38, 0.18))


# ════════════════════════════════════════════════════════════════
# 3. ABSPERRGITTER (Platzhalter — 2mm Metallblech 465×376mm)
# ════════════════════════════════════════════════════════════════

ag = doc.addObject('Part::Feature', 'Absperrgitter')
ag.Shape = Part.makeBox(iW, iD, 2.0, App.Vector(wT, wT, agZ + 0.5))
ag.Label = 'Absperrgitter 465×376mm (2mm Metall, Platzhalter)'
clr(ag, (0.72, 0.72, 0.88), transp=50)


# ════════════════════════════════════════════════════════════════
# 4. SERVO-MOTOR (Platzhalter — MG996R: 40×20×43mm)
# ════════════════════════════════════════════════════════════════

srv = doc.addObject('Part::Feature', 'Servo_Motor')
srv.Shape = Part.makeBox(40, 20, 43,
    App.Vector(wT + 8, wT + iD - 25, zBoden + 5))
srv.Label = 'Servo-Motor MG996R (Platzhalter 40×20×43mm)'
clr(srv, (0.12, 0.12, 0.72))


# ════════════════════════════════════════════════════════════════
# 5. SCHUBSTANGE (Servo → Absperrgitter)
# ════════════════════════════════════════════════════════════════

stange = doc.addObject('Part::Feature', 'Schubstange')
stange.Shape = Part.makeBox(8, iD - 35, 5,
    App.Vector(wT + 24, wT + 5, agZ + 1))
stange.Label = 'Schubstange Servo→Gitter (Platzhalter)'
clr(stange, (0.48, 0.50, 0.53))


# ════════════════════════════════════════════════════════════════
# 6. FLUGLOCHSCHIEBER (manuell / optional 2. Servo)
# ════════════════════════════════════════════════════════════════

schieber = doc.addObject('Part::Feature', 'Flugloch_Schieber')
schieber.Shape = Part.makeBox(fl_w + 20, 6, fl_h + 4,
    App.Vector((oW - fl_w) / 2 - 10, -6, fl_z - 2))
schieber.Label = 'Flugloch-Schieber (Platzhalter)'
clr(schieber, (0.65, 0.50, 0.30))


# ════════════════════════════════════════════════════════════════
# 7. ELEKTRONIK-PLATINEN (Platzhalter)
# ════════════════════════════════════════════════════════════════

esp = doc.addObject('Part::Feature', 'ESP32_Board')
esp.Shape = Part.makeBox(54, 26, 10,
    App.Vector(elec_x + 13, 1, elec_z + 22))
esp.Label = 'ESP32 Mikrocontroller (Platzhalter 54×26mm)'
clr(esp, (0.08, 0.55, 0.18))

drv = doc.addObject('Part::Feature', 'Motordriver')
drv.Shape = Part.makeBox(43, 26, 10,
    App.Vector(elec_x + 5, 1, elec_z + 5))
drv.Label = 'Motor-Driver L298N (Platzhalter 43×43mm)'
clr(drv, (0.08, 0.45, 0.55))


# ════════════════════════════════════════════════════════════════
# 8. SENSOR-LEISTE (Innenboden des Mechanikraums)
# ════════════════════════════════════════════════════════════════

sns = doc.addObject('Part::Feature', 'Sensor_Leiste')
sns.Shape = Part.makeBox(iW - 20, 18, 5,
    App.Vector(wT + 10, wT + 10, zBoden))
sns.Label = 'Sensor-Leiste Temp/Hum/Waage (Platzhalter)'
clr(sns, (0.92, 0.58, 0.06))


# ════════════════════════════════════════════════════════════════
# 9. RECOMPUTE & SPEICHERN
# ════════════════════════════════════════════════════════════════

doc.recompute()
save_path = r"D:\marek\projects\freecad-skill\Smart_Bienenzarge_Langstroth.FCStd"
doc.saveAs(save_path)

print()
print('╔══════════════════════════════════════════════════════════════╗')
print('║     SMART BIENENZARGE — LANGSTROTH FULL DEPTH  ✓            ║')
print('╠══════════════════════════════════════════════════════════════╣')
print(f'║  Außenmaße :  {oW:.0f} × {oD:.0f} × {oH:.0f} mm  (B × T × H)     ║')
print(f'║  Innenmaße :  {iW:.0f} × {iD:.0f} mm                          ║')
print(f'║  Bienenraum:  {bH:.0f} mm  (Langstroth Full Depth)           ║')
print(f'║  Mechanikr.:   {mH:.0f} mm  (Servo + Absperrgitter)           ║')
print(f'║  Wandstärke:   {wT:.0f} mm                                   ║')
print('╠══════════════════════════════════════════════════════════════╣')
print('║  Teile:                                                      ║')
for obj in doc.Objects:
    print(f'║    • {obj.Label[:56]:<56}║')
print('╠══════════════════════════════════════════════════════════════╣')
print(f'║  → {save_path}')
print('╚══════════════════════════════════════════════════════════════╝')

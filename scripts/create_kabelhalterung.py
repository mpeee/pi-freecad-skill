import FreeCAD as App
import Part

doc = App.ActiveDocument
if doc is None:
    print("Kein aktives Dokument!")
else:
    # Altes Objekt entfernen falls vorhanden
    if doc.getObject('Kabelhalterung'):
        doc.removeObject('Kabelhalterung')

    # === Abmessungen ===
    #
    #  Seitenansicht (XZ-Ebene):
    #
    #        |  |   ← Schlitz (3mm breit, Drähte einzeln eindrücken)
    #       /    \
    #      |      |  ← Ring (2mm Wand, 8mm ID)
    #       \    /
    #        ----   ← Ringboden (Übergang zur Basis)
    #     __________
    #    |    __    |  ← Basisplatte mit 2x M2-Bohrungen
    #    |___|  |___|
    #        (Panel-Innenfläche bei Z=0)

    inner_r  = 4.0    # Innenradius (8mm ID – nimmt ~5 dünne Steuerdrähte auf)
    outer_r  = 6.0    # Außenradius (2mm Wandstärke)
    ring_len = 6.0    # Clip-Tiefe in Y-Richtung
    slot_w   = 3.0    # Schlitzbreite (Draht ~2.5mm OD → ein Draht auf einmal)
    base_l   = 16.0   # Basisplatten-Breite (X)
    base_h   = 2.0    # Basisplatten-Dicke (Z, liegt auf dem Panel)
    ring_cz  = base_h + outer_r   # Z-Koordinate Ringmittelpunkt = 8mm

    # === Ring als Rohrzylinder (Achse = Y-Richtung) ===
    pos  = App.Vector(0, 0, ring_cz)
    ydir = App.Vector(0, 1, 0)
    outer_c = Part.makeCylinder(outer_r, ring_len, pos, ydir)
    inner_c = Part.makeCylinder(inner_r, ring_len, pos, ydir)
    tube = outer_c.cut(inner_c)

    # Schlitz nach oben (+Z) ausschneiden
    slot = Part.makeBox(slot_w, ring_len + 2, outer_r + 2,
                        App.Vector(-slot_w / 2, -1, ring_cz))
    ring = tube.cut(slot)

    # === Basisplatte ===
    plate = Part.makeBox(base_l, ring_len, base_h,
                         App.Vector(-base_l / 2, 0, 0))

    # 2× M2-Bohrungen (Radius 1.1mm, ±5mm von Mitte)
    for hx in [-5.0, 5.0]:
        hole = Part.makeCylinder(1.1, base_h + 2,
                                 App.Vector(hx, ring_len / 2, -1),
                                 App.Vector(0, 0, 1))
        plate = plate.cut(hole)

    # === Zusammenfügen und ins Dokument ===
    guide = ring.fuse(plate)

    feat = doc.addObject('Part::Feature', 'Kabelhalterung')
    feat.Shape = guide
    feat.Label = 'Kabelhalterung'
    doc.recompute()

    bb = feat.Shape.BoundBox
    print(f'Kabelhalterung erstellt:')
    print(f'  Breite x Tiefe x Höhe: {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm')
    print(f'  Innenring: {inner_r*2:.0f}mm ID, Schlitz: {slot_w:.1f}mm breit')
    print(f'  2x M2-Bohrungen (±5mm von Mitte) in der Basisplatte')

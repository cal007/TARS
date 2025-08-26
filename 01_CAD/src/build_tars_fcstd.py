# 01_CAD/src/build_tars_fcstd.py
import os, math
import FreeCAD as App
import Part

# --- Pfade ---
repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
build_dir = os.path.join(repo_root, "01_CAD", "build")
os.makedirs(build_dir, exist_ok=True)

# --- Dims (mm) ---
# Plattform
PLAT_X = 2967.0
PLAT_Y = 2483.0
PLAT_Z = 30.0     # Annahme: 30 mm Deckplatte (nur Proxy)

# Schubladenbox (Einzelbox)
BOX_X = 521.0
BOX_Y = 717.0
BOX_Z = 130.0
# Einschubkasten (Hülle/Proxy etwas größer als Box)
SLOT_WALL = 3.0
SLOT_X = BOX_X + 2*SLOT_WALL
SLOT_Y = BOX_Y + 2*SLOT_WALL
SLOT_Z = 2*BOX_Z + 3*SLOT_WALL  # 2 Boxen übereinander + Zwischenluft/Wand

# Anordnung Ebene 1
NUM_SLOTS_X_PER_SIDE = 5
NUM_SIDES = 2
SLOT_GAP_X = 20.0   # Fuge zwischen Slots in x
SIDE_CLEAR_Y = 40.0 # Abstand zur Außenkante in y innen
CENTER_GAP_Y = 60.0 # Abstand zwischen linker und rechter Slot-Reihe

# Ebene 2 (Swivel-Launch-Box Außenmaße in Transportlage 0°/0°)
SLB_X = 970.0
SLB_Y = 960.0
SLB_Z = 923.0
SLB_PER_SIDE = 1    # einfach starten; später erweiterbar
SLB_STANDOFF_Z = 200.0  # Abstand zwischen Slot-Oberkante und Ebene2 (Proxy)

doc = App.newDocument("TARS_v0_2")
a = doc.addObject

def mk_box(name, dx, dy, dz, px=0, py=0, pz=0):
    shape = Part.makeBox(dx, dy, dz)
    obj = a("Part::Feature", name)
    obj.Shape = shape
    obj.Placement.Base.x = px
    obj.Placement.Base.y = py
    obj.Placement.Base.z = pz
    return obj

# Ursprung: x=0, y=0 vorne links (Fahrerseite), z=0 = Fläche Ebene1 (Oberseite Deckplatte laut deiner Def.)
# Ich lege die Deckplatte nach unten (z negativ), damit die Oberseite z=0 bleibt.
platform = mk_box("Platform", PLAT_X, PLAT_Y, PLAT_Z, 0, 0, -PLAT_Z)

# Hilfsmaße für Slot-Positionen
# Wir platzieren die beiden Slot-Reihen entlang y: eine links (fahrerseitig) nahe y=0, eine rechts an der Beifahrerseite.
# Jede Reihe enthält 5 Einschubkästen entlang x. Öffnungen zeigen nach außen (±y).
slot_total_x = NUM_SLOTS_X_PER_SIDE * SLOT_X + (NUM_SLOTS_X_PER_SIDE - 1) * SLOT_GAP_X
front_margin_x = max(0.0, (PLAT_X - slot_total_x) / 2.0)  # mittige Verteilung in x

# y-Positionen der Reihen
left_row_y = SIDE_CLEAR_Y
right_row_y = PLAT_Y - SIDE_CLEAR_Y - SLOT_Y

slots = []
boxes = []

for side_idx, base_y, y_dir, side_label in [
    (0, left_row_y, -1, "L"),    # links, offene Seite nach y<0 (außen)
    (1, right_row_y, +1, "R")    # rechts, offene Seite nach y>0 (außen)
]:
    for i in range(NUM_SLOTS_X_PER_SIDE):
        px = front_margin_x + i * (SLOT_X + SLOT_GAP_X)
        py = base_y
        pz = 0.0  # Unterkante Slot bündig mit Ebene1-Oberfläche (z=0)
        slot = mk_box(f"Slot_{side_label}_{i+1}", SLOT_X, SLOT_Y, SLOT_Z, px, py, pz)
        slots.append(slot)

        # Zwei Schubladenboxen im Slot (übereinander)
        # Leichte Luft zu den Wänden (1 mm), Öffnung nach außen — proxyhaft lassen wir sie als Quader im Slotvolumen
        inset = 1.0
        bx = px + SLOT_WALL + inset
        by = py + SLOT_WALL + inset
        bz1 = pz + SLOT_WALL + inset
        bz2 = bz1 + BOX_Z + SLOT_WALL  # zweite Ebene
        box1 = mk_box(f"Drawer_{side_label}_{i+1}_A", BOX_X, BOX_Y, BOX_Z, bx, by, bz1)
        box2 = mk_box(f"Drawer_{side_label}_{i+1}_B", BOX_X, BOX_Y, BOX_Z, bx, by, bz2)
        boxes.extend([box1, box2])

# Ebene 2 Trägerhöhe: Oberkante Slots + Standoff
top_of_slots_z = SLOT_Z
level2_z = top_of_slots_z + SLB_STANDOFF_Z

# Platzierung Swivel-Launch-Boxen (Transportlage 0°/0°). Je Seite 1 Stück, mittig über den Slots.
slbs = []
for side_idx, side_label, base_y in [
    (0, "L", left_row_y),
    (1, "R", right_row_y)
]:
    # mittige x-Position über der Slot-Reihe
    slb_px = (PLAT_X - SLB_X) / 2.0
    # y: mittig über der jeweiligen Slot-Reihe
    row_center_y = base_y + SLOT_Y/2.0
    slb_py = row_center_y - SLB_Y/2.0
    slb_pz = level2_z
    slb = mk_box(f"SLB_{side_label}_1_transport", SLB_X, SLB_Y, SLB_Z, slb_px, slb_py, slb_pz)
    slbs.append(slb)

# Gruppierung (optional, für Ordnung im Baum)
grp_slots = a("App::DocumentObjectGroup", "G_Ebene1_Slots")
grp_slots.addObjects(slots)
grp_drawers = a("App::DocumentObjectGroup", "G_Ebene1_Drawers")
grp_drawers.addObjects(boxes)
grp_slb = a("App::DocumentObjectGroup", "G_Ebene2_SLBs")
grp_slb.addObjects(slbs)
grp_all = a("App::DocumentObjectGroup", "Assembly_Proxy")
grp_all.addObjects([platform, grp_slots, grp_drawers, grp_slb])

App.ActiveDocument.recompute()

# Export
fcstd_path = os.path.join(build_dir, "TARS_v0.2.FCStd")
App.ActiveDocument.saveAs(fcstd_path)

# Für STEP: exportiere die sichtbaren Feature-Objekte (nur Geometrie, keine Gruppen)
to_export = [platform] + slots + boxes + slbs
step_path = os.path.join(build_dir, "TARS_v0.2.step")
Part.export(to_export, step_path)

print(f"Saved FCStd: {fcstd_path}")
print(f"Saved STEP:  {step_path}")
App.closeDocument(App.ActiveDocument.Name)

# 01_CAD/src/build_tars_fcstd.py
import os, math
import FreeCAD as App
import Part

# --- Pfade ---
repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
build_dir = os.path.join(repo_root, "01_CAD", "build")
os.makedirs(build_dir, exist_ok=True)

# --- Parameter (mm) ---
# Plattform
PLAT_X = 2967.0
PLAT_Y = 2483.0
PLAT_Z = 30.0       # Proxy-Dicke Deckplatte; Oberseite = z=0 => Platte liegt nach unten

# Schubladenbox
BOX_X = 521.0
BOX_Y = 717.0
BOX_Z = 130.0

# Einschubkasten (Proxy)
SLOT_WALL = 3.0
SLOT_X = BOX_X + 2*SLOT_WALL
SLOT_Y = BOX_Y + 2*SLOT_WALL
SLOT_Z = 2*BOX_Z + 3*SLOT_WALL  # 2 Boxen übereinander

NUM_SLOTS_X_PER_SIDE = 5
SLOT_GAP_X = 20.0
SIDE_CLEAR_Y = 40.0

# Ebene 2 / SLB
SLB_X = 970.0
SLB_Y = 960.0
SLB_Z = 923.0
SLB_PER_SIDE = 2
SLB_STANDOFF_Z = 80.0          # Abstand zwischen Slot-Oberkante und Unterseite H-Platte (reduziert von 200)
PLATE_THK = 12.0               # H-Platten-Dicke
H_FLANGE_W = 80.0              # Breite der seitlichen H-Flansche (y)
H_WEB_W = 120.0                # Breite des H-Stegs (y)
H_EDGE_INSET_X = 0.0           # H-Platte so groß wie SLB footprint (kannst du positiv machen, wenn überstand gewünscht)

# Stützen (4 je Seite = 8 total), im Mittelgang
COL_W = 80.0
COL_D = 80.0
COL_MARGIN_AISLE = 40.0        # Abstand zur Slot-Reihe in den Mittelgang hinein
COL_INSET_X = 50.0             # Abstand von SLB-Vorder-/Hinterkante für Stützen in x

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

# --- Plattform ---
platform = mk_box("Platform", PLAT_X, PLAT_Y, PLAT_Z, 0, 0, -PLAT_Z)

# --- Slots & Schubladen (Ebene 1) ---
slot_total_x = NUM_SLOTS_X_PER_SIDE * SLOT_X + (NUM_SLOTS_X_PER_SIDE - 1) * SLOT_GAP_X
front_margin_x = max(0.0, (PLAT_X - slot_total_x) / 2.0)

left_row_y = SIDE_CLEAR_Y
right_row_y = PLAT_Y - SIDE_CLEAR_Y - SLOT_Y

slots = []
boxes = []

for side_idx, base_y, side_label in [
    (0, left_row_y, "L"),
    (1, right_row_y, "R")
]:
    for i in range(NUM_SLOTS_X_PER_SIDE):
        px = front_margin_x + i * (SLOT_X + SLOT_GAP_X)
        py = base_y
        pz = 0.0
        slot = mk_box(f"Slot_{side_label}_{i+1}", SLOT_X, SLOT_Y, SLOT_Z, px, py, pz)
        slots.append(slot)

        # zwei Schubladen im Slot
        inset = 1.0
        bx = px + SLOT_WALL + inset
        by = py + SLOT_WALL + inset
        bz1 = pz + SLOT_WALL + inset
        bz2 = bz1 + BOX_Z + SLOT_WALL
        box1 = mk_box(f"Drawer_{side_label}_{i+1}_A", BOX_X, BOX_Y, BOX_Z, bx, by, bz1)
        box2 = mk_box(f"Drawer_{side_label}_{i+1}_B", BOX_X, BOX_Y, BOX_Z, bx, by, bz2)
        boxes.extend([box1, box2])

# Oberkante Slots (z=0 am Boden der Slots, daher top bei SLOT_Z)
top_of_slots_z = SLOT_Z

# --- Ebene 2 Höhe ---
level2_base_z = top_of_slots_z + SLB_STANDOFF_Z         # Unterseite der H-Platte
slb_base_z = level2_base_z + PLATE_THK                   # Unterseite der SLB

# --- SLB-Platzierung: je Seite 2 Stück, komplett innerhalb der Plattform (y clamp) ---
def clamp(val, vmin, vmax): return max(vmin, min(val, vmax))

slbs = []
hplates = []

# x-Positionen: zwei SLBs gleichmäßig über den Slot-Bereich je Seite
# Nutze die Zentren bei 1/4 und 3/4 der Slot-Spannweite.
slb_centers_x = [
    front_margin_x + 0.25 * slot_total_x,
    front_margin_x + 0.75 * slot_total_x
]

for side_idx, side_label, base_y in [
    (0, "L", left_row_y),
    (1, "R", right_row_y)
]:
    row_center_y = base_y + SLOT_Y / 2.0

    # y roh (zentriert über Reihe), dann in die Plattform einspannen
    y_raw = row_center_y - SLB_Y / 2.0
    slb_py = clamp(y_raw, 0.0, PLAT_Y - SLB_Y)

    for j, cx in enumerate(slb_centers_x, start=1):
        slb_px = clamp(cx - SLB_X / 2.0, 0.0, PLAT_X - SLB_X)

        # H-Platte (als 3 Quader: 2 Flansche + 1 Steg), footprint = SLB_X × SLB_Y (anpassbar über H_EDGE_INSET_X)
        hp_x = SLB_X + 2*H_EDGE_INSET_X
        hp_y = SLB_Y + 2*H_EDGE_INSET_X
        hp_px = slb_px - H_EDGE_INSET_X
        hp_py = slb_py - H_EDGE_INSET_X

        # Flansche
        flange_left = mk_box(f"Hplate_{side_label}{j}_flangeL", hp_x, H_FLANGE_W, PLATE_THK, hp_px, hp_py, level2_base_z)
        flange_right = mk_box(f"Hplate_{side_label}{j}_flangeR", hp_x, H_FLANGE_W, PLATE_THK, hp_px, hp_py + hp_y - H_FLANGE_W, level2_base_z)
        # Steg
        web_y = (hp_y - 2*H_FLANGE_W)
        web = mk_box(f"Hplate_{side_label}{j}_web", hp_x, max(web_y, 1.0), PLATE_THK, hp_px, hp_py + H_FLANGE_W, level2_base_z)
        hplates.extend([flange_left, flange_right, web])

        # SLB
        slb = mk_box(f"SLB_{side_label}_{j}_transport", SLB_X, SLB_Y, SLB_Z, slb_px, slb_py, slb_base_z)
        slbs.append(slb)

# --- Stützen: 4 je Seite (pro SLB: vorne/hinten), im Mittelgang, von z=0 bis Unterseite H-Platte ---
cols = []

# Mittelgang-Bereich in y
aisle_y_min = left_row_y + SLOT_Y
aisle_y_max = right_row_y

# Stützen-y je Seite: links nahe Gangbeginn, rechts nahe Gangende
col_y_L = aisle_y_min + COL_MARGIN_AISLE
col_y_R = aisle_y_max - COL_MARGIN_AISLE - COL_D

# Zuordnung: für linke SLBs nutze col_y_L, für rechte SLBs col_y_R
# Wir greifen auf die zuvor berechneten SLB-Objekte und deren px zurück.
def make_column_pair(name_prefix, slb_px, y_pos):
    # vorn/hinten relativ zur SLB in x, mit Inset
    x_front = clamp(slb_px + COL_INSET_X, 0.0, PLAT_X - COL_W)
    x_rear  = clamp(slb_px + SLB_X - COL_INSET_X - COL_W, 0.0, PLAT_X - COL_W)
    c1 = mk_box(f"{name_prefix}_F", COL_W, COL_D, level2_base_z, x_front, y_pos, 0.0)
    c2 = mk_box(f"{name_prefix}_R", COL_W, COL_D, level2_base_z, x_rear,  y_pos, 0.0)
    return [c1, c2]

# Hole SLB-Paare je Seite in der Reihenfolge j=1..2
slb_L = [o for o in slbs if o.Label.startswith("SLB_L_")]
slb_R = [o for o in slbs if o.Label.startswith("SLB_R_")]

for j, o in enumerate(sorted(slb_L, key=lambda k: k.Placement.Base.x), start=1):
    cols += make_column_pair(f"Col_L{j}", o.Placement.Base.x, col_y_L)

for j, o in enumerate(sorted(slb_R, key=lambda k: k.Placement.Base.x), start=1):
    cols += make_column_pair(f"Col_R{j}", o.Placement.Base.x, col_y_R)

# --- Gruppierung ---
grp_slots = a("App::DocumentObjectGroup", "G_Ebene1_Slots"); grp_slots.addObjects(slots)
grp_drawers = a("App::DocumentObjectGroup", "G_Ebene1_Drawers"); grp_drawers.addObjects(boxes)
grp_hplates = a("App::DocumentObjectGroup", "G_Ebene2_Hplates"); grp_hplates.addObjects(hplates)
grp_slb = a("App::DocumentObjectGroup", "G_Ebene2_SLBs"); grp_slb.addObjects(slbs)
grp_cols = a("App::DocumentObjectGroup", "G_Ebene2_Columns"); grp_cols.addObjects(cols)
grp_all = a("App::DocumentObjectGroup", "Assembly_Proxy"); grp_all.addObjects([platform, grp_slots, grp_drawers, grp_hplates, grp_slb, grp_cols])

App.ActiveDocument.recompute()

# --- Export ---
fcstd_path = os.path.join(build_dir, "TARS_v0.2.FCStd")
App.ActiveDocument.saveAs(fcstd_path)

to_export = [platform] + slots + boxes + hplates + slbs + cols
step_path = os.path.join(build_dir, "TARS_v0.2.step")
Part.export(to_export, step_path)

print(f"Saved FCStd: {fcstd_path}")
print(f"Saved STEP:  {step_path}")

App.closeDocument(App.ActiveDocument.Name)

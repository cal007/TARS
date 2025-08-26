# 01_CAD/src/build_tars_fcstd.py
import os, math
import FreeCAD as App
import Part

# ---------- Pfade ----------
repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
build_dir = os.path.join(repo_root, "01_CAD", "build")
os.makedirs(build_dir, exist_ok=True)

doc = App.newDocument("TARS_v0_2")
a = doc.addObject

def mk_feat(name, shape, px=0, py=0, pz=0):
    obj = a("Part::Feature", name)
    obj.Shape = shape
    obj.Placement.Base.x = px
    obj.Placement.Base.y = py
    obj.Placement.Base.z = pz
    return obj

def mk_box(name, dx, dy, dz, px=0, py=0, pz=0):
    return mk_feat(name, Part.makeBox(dx, dy, dz), px, py, pz)

def clamp(v, vmin, vmax): return max(vmin, min(v, vmax))

# ---------- Parameter (mm) ----------
# Plattform (Ebene 1)
PLAT_X = 2967.0
PLAT_Y = 2483.0
PLAT_Z = 30.0                 # Deckplatte; Oberseite = z=0 -> Platte nach unten

# Schubladen / Slots auf Ebene 1
BOX_X, BOX_Y, BOX_Z = 521.0, 717.0, 130.0
SLOT_WALL = 3.0
SLOT_X = BOX_X + 2*SLOT_WALL
SLOT_Y = BOX_Y + 2*SLOT_WALL
SLOT_Z = 2*BOX_Z + 3*SLOT_WALL
NUM_SLOTS_X_PER_SIDE = 5
SLOT_GAP_X = 20.0
SIDE_CLEAR_Y = 40.0

# Ebene 2 (Deckplatte + H-Plate + SLB)
LV2_STANDOFF_Z = 50.0         # Abstand: Oberkante Slot -> Unterseite Ebene-2-Platte
LV2_PLATE_THK = 20.0          # Dicke Ebene-2-Platte
# SLB Außenmaße (Transportlage 0°/0°): offene Seite ist 923x960, 970 entlang x
SLB_X, SLB_Y, SLB_Z = 970.0, 960.0, 923.0
SLB_PER_SIDE = 2              # 4 total

# H-Plate (Proxy nach Foto)
HPL_THK = 12.0
HPL_X = SLB_X + 120.0         # überstehend in x für Langlöcher
HPL_Y = SLB_Y + 80.0          # überstehend in y
HPL_SLOT_W = 30.0             # Langlochbreite
HPL_SLOT_L = 160.0            # Langlochlänge
HPL_SLOT_OFF_Y = 40.0         # Abstand zur Plattenkante in y
HPL_CENTER_D = 520.0          # großer Durchbruch (swivel window)
HPL_RING_OD = 680.0           # äußerer Referenzring
HPL_RING_ID = 600.0           # innerer Referenzring
HPL_RING_THK = 6.0            # Ring-"Wulst" (als Relief)
DETENT_W, DETENT_L, DETENT_H = 22.0, 40.0, 8.0  # 0°/33°/90° Markierungen/Blöcke

# Stützen
COL_W = 100.0
COL_D = 100.0
ADD_MID_X = True
ADD_MID_Y = True

# ---------- Ebene 1: Plattform ----------
platform = mk_box("Platform", PLAT_X, PLAT_Y, PLAT_Z, 0, 0, -PLAT_Z)

# ---------- Slots + Drawers ----------
slot_total_x = NUM_SLOTS_X_PER_SIDE * SLOT_X + (NUM_SLOTS_X_PER_SIDE - 1) * SLOT_GAP_X
front_margin_x = max(0.0, (PLAT_X - slot_total_x) / 2.0)
left_row_y = SIDE_CLEAR_Y
right_row_y = PLAT_Y - SIDE_CLEAR_Y - SLOT_Y

slots, drawers = [], []
for side_idx, base_y, side_label in [(0, left_row_y, "L"), (1, right_row_y, "R")]:
    for i in range(NUM_SLOTS_X_PER_SIDE):
        px = front_margin_x + i * (SLOT_X + SLOT_GAP_X)
        py = base_y
        slot = mk_box(f"Slot_{side_label}_{i+1}", SLOT_X, SLOT_Y, SLOT_Z, px, py, 0.0)
        slots.append(slot)
        inset = 1.0
        bx = px + SLOT_WALL + inset
        by = py + SLOT_WALL + inset
        bz1 = SLOT_WALL + inset
        bz2 = bz1 + BOX_Z + SLOT_WALL
        drawers.append(mk_box(f"Drawer_{side_label}_{i+1}_A", BOX_X, BOX_Y, BOX_Z, bx, by, bz1))
        drawers.append(mk_box(f"Drawer_{side_label}_{i+1}_B", BOX_X, BOX_Y, BOX_Z, bx, by, bz2))

top_of_slots_z = SLOT_Z

# ---------- Ebene 2: Deckplatte ----------
lv2_base_z = top_of_slots_z + LV2_STANDOFF_Z           # Unterseite Ebene-2-Platte
lv2_plate = mk_box("Level2_Plate", PLAT_X, PLAT_Y, LV2_PLATE_THK, 0, 0, lv2_base_z)
lv2_top_z = lv2_base_z + LV2_PLATE_THK                  # Oberseite Ebene-2-Platte

# ---------- H-Plate (Proxy, mit Langlöchern, zentralem Durchbruch, Ring, Detents) ----------
def make_hplate(name_prefix):
    # Grundplatte
    base = Part.makeBox(HPL_X, HPL_Y, HPL_THK)

    # Zentrale Öffnung (kreisrund)
    hole = Part.makeCylinder(HPL_CENTER_D/2.0, HPL_THK, App.Vector(HPL_X/2, HPL_Y/2, 0))
    base = base.cut(hole)

    # Langlöcher links/rechts (rechteck minus zwei Halbkreise)
    def slot_shape(cx, cy, ang_deg=0):
        # Baue als Differenz: Rechteck + zwei Zylinder schneiden
        rect = Part.makeBox(HPL_SLOT_L, HPL_SLOT_W, HPL_THK, App.Vector(cx - HPL_SLOT_L/2, cy - HPL_SLOT_W/2, 0))
        r = HPL_SLOT_W/2.0
        cyl1 = Part.makeCylinder(r, HPL_THK, App.Vector(cx - HPL_SLOT_L/2, cy, 0))
        cyl2 = Part.makeCylinder(r, HPL_THK, App.Vector(cx + HPL_SLOT_L/2, cy, 0))
        slot = rect.fuse(cyl1).fuse(cyl2)
        # Schneiden in die Platte (cut später)
        return slot

    y_lo = HPL_SLOT_OFF_Y + HPL_SLOT_W/2.0
    y_hi = HPL_Y - HPL_SLOT_OFF_Y - HPL_SLOT_W/2.0
    # je Seite zwei Langlöcher (vorne/hinten in x)
    x1 = HPL_X*0.25
    x2 = HPL_X*0.75
    slots_shapes = [
        slot_shape(x1, y_lo), slot_shape(x2, y_lo),
        slot_shape(x1, y_hi), slot_shape(x2, y_hi),
    ]
    for s in slots_shapes:
        base = base.cut(s)

    # Swivel-Ring als flacher Torus-Annulus (Relief oben)
    ring_od = Part.makeCylinder(HPL_RING_OD/2.0, HPL_RING_THK, App.Vector(HPL_X/2, HPL_Y/2, HPL_THK - HPL_RING_THK))
    ring_id = Part.makeCylinder(HPL_RING_ID/2.0, HPL_RING_THK, App.Vector(HPL_X/2, HPL_Y/2, HPL_THK - HPL_RING_THK))
    ring = ring_od.cut(ring_id)
    body = base.fuse(ring)

    # Detent-Blöcke (0°, 33°, 90°) – als kleine Quader auf Ringrand
    detent_r = (HPL_RING_OD/2.0 + HPL_RING_ID/2.0)/2.0
    for ang_deg, tag in [(0, "0"), (33, "33"), (90, "90")]:
        ang = math.radians(ang_deg)
        cx = HPL_X/2 + detent_r * math.cos(ang)
        cy = HPL_Y/2 + detent_r * math.sin(ang)
        # tangentiale Ausrichtung grob proxien: Quader ohne Rotation (einfach)
        dx, dy = DETENT_L, DETENT_W
        det = Part.makeBox(dx, dy, DETENT_H, App.Vector(cx - dx/2, cy - dy/2, HPL_THK - DETENT_H))
        body = body.fuse(det)

    return mk_feat(f"{name_prefix}", body)

# ---------- SLB-Positionierung: je Seite 2, innerhalb der Plattform, z = Oberseite Ebene-2-Platte ----------
# Zentren entlang x bei 1/4 und 3/4 der Slot-Spannweite, auf die Platte geclamped
slb_centers_x = [
    front_margin_x + 0.25 * slot_total_x,
    front_margin_x + 0.75 * slot_total_x
]
# y-Zentren: über den Slot-Reihen (links/rechts)
row_center_L = left_row_y + SLOT_Y/2.0
row_center_R = right_row_y + SLOT_Y/2.0

hplates, slbs = [], []
def place_slb(side_label, row_center_y):
    for j, cx in enumerate(slb_centers_x, start=1):
        px = clamp(cx - SLB_X/2.0, 0.0, PLAT_X - SLB_X)
        py = clamp(row_center_y - SLB_Y/2.0, 0.0, PLAT_Y - SLB_Y)
        # H-Plate sitzt plan auf Ebene-2-Platte
        hp = make_hplate(f"Hplate_{side_label}{j}")
        hp.Placement.Base = App.Vector(px + (SLB_X - HPL_X)/2.0, py + (SLB_Y - HPL_Y)/2.0, lv2_top_z)  # oben auf LV2
        hplates.append(hp)
        # SLB sitzt auf H-Plate
        slb = mk_box(f"SLB_{side_label}_{j}_transport", SLB_X, SLB_Y, SLB_Z, px, py, lv2_top_z + HPL_THK)
        slbs.append(slb)

place_slb("L", row_center_L)
place_slb("R", row_center_R)

# ---------- Stützen unter Ebene 2 ----------
columns = []

def add_column(name, x, y):
    # von z=0 (Ebene-1-Oberfläche) bis Unterseite Ebene-2-Platte
    h = lv2_base_z
    columns.append(mk_box(name, COL_W, COL_D, h, x, y, 0.0))

# Eckpunkte
add_column("Col_FL", 0, 0)
add_column("Col_FR", PLAT_X - COL_W, 0)
add_column("Col_RL", 0, PLAT_Y - COL_D)
add_column("Col_RR", PLAT_X - COL_W, PLAT_Y - COL_D)

# Mittig x (links und rechts in y)
if ADD_MID_X:
    add_column("Col_Mx_L", (PLAT_X - COL_W)/2.0, 0)
    add_column("Col_Mx_R", (PLAT_X - COL_W)/2.0, PLAT_Y - COL_D)

# Mittig y (vorne/hinten in x)
if ADD_MID_Y:
    add_column("Col_My_F", 0, (PLAT_Y - COL_D)/2.0)
    add_column("Col_My_R", PLAT_X - COL_W, (PLAT_Y - COL_D)/2.0)

# ---------- Gruppen ----------
grp_lvl1 = a("App::DocumentObjectGroup", "G_Ebene1"); grp_lvl1.addObjects([platform] + slots + drawers)
grp_lvl2 = a("App::DocumentObjectGroup", "G_Ebene2"); grp_lvl2.addObjects([lv2_plate] + hplates + slbs + columns)
assembly = a("App::DocumentObjectGroup", "Assembly_Proxy"); assembly.addObjects([grp_lvl1, grp_lvl2])

App.ActiveDocument.recompute()

# ---------- Export ----------
fcstd_path = os.path.join(build_dir, "TARS_v0.2.FCStd")
App.ActiveDocument.saveAs(fcstd_path)
step_path = os.path.join(build_dir, "TARS_v0.2.step")
to_export = [platform] + slots + drawers + [lv2_plate] + hplates + slbs + columns
Part.export(to_export, step_path)

print(f"Saved FCStd: {fcstd_path}")
print(f"Saved STEP:  {step_path}")
App.closeDocument(App.ActiveDocument.Name)

# 01_CAD/src/build_tars_fcstd.py
# FreeCAD headless builder for trailer assembly with two levels and 4 SLBs
# v0.6 — creates only 4 SLB bodies; poses stored as properties (no extra bodies)

import os, math
import FreeCAD as App
import Part

# ---------------- Paths ----------------
REPO_ROOT = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
BUILD_DIR = os.path.join(REPO_ROOT, "01_CAD", "build")
os.makedirs(BUILD_DIR, exist_ok=True)

DOC = App.newDocument("TARS_v0_6")
add = DOC.addObject

def mk_feat(name, shape, px=0, py=0, pz=0):
    o = add("Part::Feature", name)
    o.Shape = shape
    o.Placement.Base = App.Vector(px, py, pz)
    return o

def mk_box(name, dx, dy, dz, px=0, py=0, pz=0):
    return mk_feat(name, Part.makeBox(dx, dy, dz), px, py, pz)

def clamp(v, vmin, vmax):
    return max(vmin, min(v, vmax))

# ---------------- Parameters (mm) ----------------
# Platform (Ebene 1): top face at z = 0 as per coordinate system
PLAT_X, PLAT_Y, PLAT_T = 2967.0, 2483.0, 30.0

# Drawer box and slot housings
BOX_X, BOX_Y, BOX_Z = 521.0, 717.0, 130.0
SLOT_WALL = 3.0
SLOT_X = BOX_X + 2 * SLOT_WALL
SLOT_Y = BOX_Y + 2 * SLOT_WALL
SLOT_Z = 2 * BOX_Z + 3 * SLOT_WALL  # two drawers stacked plus walls
NUM_SLOTS_X_PER_SIDE = 5
SLOT_GAP_X = 20.0
SIDE_CLEAR_Y = 40.0  # clearance from platform edge to outer slot wall

# Rails (Auflager auf Slots) — Ebene 2 liegt darauf auf
RAIL_W = 60.0
RAIL_H = 20.0

# Ebene 2 (Deckplatte)
LV2_PLATE_THK = 20.0

# SLB dimensions (transport pose extents) — Achtung: nach deiner Korrektur
# Offene Seite = 923 x 960, 970 läuft entlang y
SLB_X, SLB_Y, SLB_Z = 970.0, 960.0, 923.0  # x (längs), y (quer), z (hoch) in Transportlage
SLB_PER_SIDE = 2

# H-Plate (innerhalb SLB footprint und innerhalb Level-2-Platte)
HPL_THK = 12.0
HPL_X_MARGIN = 40.0
HPL_Y_MARGIN = 40.0
HPL_SLOT_W, HPL_SLOT_L, HPL_SLOT_OFF_Y = 28.0, 140.0, 35.0
HPL_CENTER_D = 520.0
HPL_RING_OD, HPL_RING_ID, HPL_RING_THK = 680.0, 600.0, 6.0
DETENT_W, DETENT_L, DETENT_H = 22.0, 40.0, 8.0

# Columns (Stützen): Col_FL entfällt wie besprochen
COL_W = 100.0
COL_D = 100.0
ADD_MID_X = True
ADD_MID_Y = True

# Neue Kippachsen-Parameter (oberhalb der Funktionen einfügen)
STANDOFF_S = 60.0        # zusätzliche Distanz zwischen H-Plate und SLB-Unterkante [mm]
PIVOT_OVER_TOP = 80.0    # Achshöhe über SLB-Oberkante [mm]
PIVOT_X_OFFSET = 385.0   # + nach vorn, von SLB-Mitte [mm]
CLEAR_USE = 20.0         # geforderte min. Bodenfreiheit bei 49° [mm]

# Active SLB pose (transport | load | use)
ACTIVE_POSE = os.environ.get("SLB_POSE", "transport").strip().lower()
if ACTIVE_POSE not in ("transport", "load", "use"):
    ACTIVE_POSE = "transport"

# ---------------- Level 1: Platform, slots, drawers ----------------
platform = mk_box("Platform", PLAT_X, PLAT_Y, PLAT_T, 0, 0, -PLAT_T)

slots, drawers = [], []

slot_row_len = NUM_SLOTS_X_PER_SIDE * SLOT_X + (NUM_SLOTS_X_PER_SIDE - 1) * SLOT_GAP_X
slot_row_x0 = (PLAT_X - slot_row_len) / 2.0

slot_y_left  = SIDE_CLEAR_Y
slot_y_right = PLAT_Y - SIDE_CLEAR_Y - SLOT_Y
slot_z0 = 0.0

def add_slot_row(label, y0):
    for i in range(NUM_SLOTS_X_PER_SIDE):
        x0 = slot_row_x0 + i * (SLOT_X + SLOT_GAP_X)
        s = mk_box(f"Slot_{label}_{i+1}", SLOT_X, SLOT_Y, SLOT_Z, x0, y0, slot_z0)
        slots.append(s)
        # two drawers (Proxy)
        inx = x0 + SLOT_WALL
        iny = y0 + SLOT_WALL
        inz1 = slot_z0 + SLOT_WALL
        inz2 = inz1 + BOX_Z + SLOT_WALL
        d1 = mk_box(f"Drawer_{label}_{i+1}_1", BOX_X, BOX_Y, BOX_Z, inx, iny, inz1)
        d2 = mk_box(f"Drawer_{label}_{i+1}_2", BOX_X, BOX_Y, BOX_Z, inx, iny, inz2)
        drawers.extend([d1, d2])

add_slot_row("L", slot_y_left)
add_slot_row("R", slot_y_right)

# Rails (durchgehend)
rail_z0 = slot_z0 + SLOT_Z
rail_len_x = slot_row_len
rail_x0 = slot_row_x0
rail_y_center_L = slot_y_left + SLOT_Y / 2.0
rail_y_center_R = slot_y_right + SLOT_Y / 2.0

rail_L = mk_box("Rail_L", rail_len_x, RAIL_W, RAIL_H,
                rail_x0, rail_y_center_L - RAIL_W/2.0, rail_z0)
rail_R = mk_box("Rail_R", rail_len_x, RAIL_W, RAIL_H,
                rail_x0, rail_y_center_R - RAIL_W/2.0, rail_z0)

# ---------------- Level 2 plate on rails ----------------
lv2_base_z = rail_z0 + RAIL_H
lv2_plate  = mk_box("Level2_Plate", PLAT_X, PLAT_Y, LV2_PLATE_THK, 0, 0, lv2_base_z)
lv2_top_z  = lv2_base_z + LV2_PLATE_THK

# ---------------- H-Plate generator ----------------
def make_hplate(name, px, py, pz):
    hpx = SLB_X - 2 * HPL_X_MARGIN
    hpy = SLB_Y - 2 * HPL_Y_MARGIN
    base = Part.makeBox(hpx, hpy, HPL_THK, App.Vector(px, py, pz))

    # Central clearance hole
    center = App.Vector(px + hpx/2.0, py + hpy/2.0, pz)
    cyl = Part.makeCylinder(HPL_CENTER_D/2.0, HPL_THK, center, App.Vector(0,0,1))
    base = base.cut(cyl)

    # Long slots (left/right)
    def slot_cut(y_sign):
        sx = HPL_SLOT_L
        sy = HPL_SLOT_W
        sz = HPL_THK + 1.0
        sx0 = px + (hpx - sx)/2.0
        sy0 = (py + hpy/2.0) + y_sign * (HPL_SLOT_OFF_Y + sy/2.0) - sy/2.0
        return Part.makeBox(sx, sy, sz, App.Vector(sx0, sy0, pz - 0.5))
    base = base.cut(slot_cut(+1))
    base = base.cut(slot_cut(-1))

    # Visual swivel ring
    ring_t = HPL_RING_THK
    ring = Part.makeCylinder(HPL_RING_OD/2.0, ring_t, center, App.Vector(0,0,1)) \
           .cut(Part.makeCylinder(HPL_RING_ID/2.0, ring_t, center, App.Vector(0,0,1)))
    ring_feat = mk_feat(name + "_Ring", ring, 0, 0, 0)

    # Detent blocks (visuell)
    detents = []
    def add_detent(lbl, angle_deg, r_offset):
        r = min(hpx, hpy) * 0.35 + r_offset
        ang = math.radians(angle_deg)
        cx = center.x; cy = center.y; cz = pz + HPL_THK
        dx = r * math.cos(ang)
        dy = r * math.sin(ang)
        bx = cx + dx - DETENT_L/2.0
        by = cy + dy - DETENT_W/2.0
        det = Part.makeBox(DETENT_L, DETENT_W, DETENT_H, App.Vector(bx, by, cz))
        detents.append(mk_feat(f"{name}_detent_{lbl}", det))
    for ang in (0, +33, -33, +90, -90):
        add_detent(str(ang).replace("-", "m"), ang, 0)

    base_feat = mk_feat(name, base)
    return base_feat, ring_feat, detents

# ---------------- SLB pose helpers ----------------
def slb_pose_footprint(dx, dy, dz, pose):
    # projected footprint (x,y) for placement clamp
    if pose == "transport":   # 0/0
        return dx, dy
    if pose == "load":        # 90/0 -> swap x/y
        return dy, dx
    if pose == "use":         # 33/49 -> conservative projection
        from math import cos, sin, radians
        fx = dx * cos(radians(33)) + dz * sin(radians(49))
        fy = dy
        return fx, fy
    return dx, dy

def slb_apply_pose(obj, base_px, base_py, base_pz, pose):
    # Basis: Unterkante SLB bei base_pz
    # Trunnion-Achse:
    z_p = SLB_Z + PIVOT_OVER_TOP                 # von SLB-Unterkante
    h_p = base_pz + z_p                          # Achshöhe über Ebene-2
    x_p = base_px + SLB_X/2.0 + PIVOT_X_OFFSET   # Weltkoordinate x der Achse
    y_p = base_py + SLB_Y/2.0                    # Achse läuft entlang y

    # Rotationen um die Trunnion-Achse (App.Vector(0,1,0))
    pivot = App.Vector(x_p, y_p, h_p)

    rot_t = App.Rotation()                        # 0°/0°
    rot_l = App.Rotation(App.Vector(0,0,1), 90)   # 90° horizontal um z DURCH pivot? -> erst horizontal drehen
    rot_u = App.Rotation(App.Vector(0,1,0), 49)   # 49° vertikal um y durch pivot

    # Reihenfolge: horizontal (0/33/90) um z durch Pivot, dann vertikal 49° um y durch Pivot
    if pose == "transport":    # 0°/0°
        obj.Placement = App.Placement(App.Vector(base_px, base_py, base_pz), App.Rotation())
    elif pose == "load":       # 90°/0°
        place = App.Placement(pivot, rot_l, pivot)
        place.Base = App.Vector(base_px, base_py, base_pz)
        obj.Placement = place
    else:                      # use: 33°/49°
        rot_z33 = App.Rotation(App.Vector(0,0,1), 33)
        rot_combo = rot_z33.multiply(rot_u)
        obj.Placement = App.Placement(pivot, rot_combo, pivot)

    # Properties speichern
    for n in ("TransportPlacement","LoadPlacement","UsePlacement"):
        if not hasattr(obj, n):
            obj.addProperty("App::PropertyPlacement", n, "SLB", "Pose gespeichert")
    obj.TransportPlacement = App.Placement(App.Vector(base_px, base_py, base_pz), App.Rotation())
    pl_load = App.Placement(pivot, rot_l, pivot); pl_load.Base = App.Vector(base_px, base_py, base_pz)
    obj.LoadPlacement = pl_load
    rot_combo = App.Rotation(App.Vector(0,0,1), 33).multiply(App.Rotation(App.Vector(0,1,0), 49))
    obj.UsePlacement = App.Placement(pivot, rot_combo, pivot)

# ---------------- SLB placement (creates ONLY 4 bodies) ----------------
slb_centers_x = [PLAT_X * 0.25, PLAT_X * 0.75]
row_center_L = rail_y_center_L
row_center_R = rail_y_center_R

hplates = []
slbs = []  # only 4 objs

def place_side(side_label, row_center_y):
    for j, cx_mid in enumerate(slb_centers_x, start=1):
        fx, fy = slb_pose_footprint(SLB_X, SLB_Y, SLB_Z, ACTIVE_POSE)
        px = clamp(cx_mid - fx/2.0, 0.0, PLAT_X - fx)
        py = clamp(row_center_y - fy/2.0, 0.0, PLAT_Y - fy)

        # H-Plate
        hpx = SLB_X - 2 * HPL_X_MARGIN
        hpy = SLB_Y - 2 * HPL_Y_MARGIN
        hp_x = px + (fx - hpx) / 2.0
        hp_y = py + (fy - hpy) / 2.0
        hp, hp_ring, hp_dets = make_hplate(f"Hplate_{side_label}{j}", hp_x, hp_y, lv2_top_z)
        hplates.extend([hp, hp_ring] + hp_dets)

        # SLB-Körper (einmal)
        slb_z0 = lv2_top_z + HPL_THK + STANDOFF_S
        slb = mk_box(f"SLB_{side_label}_{j}", SLB_X, SLB_Y, SLB_Z, px, py, slb_z0)
        # Pose anwenden (ändert nur Placement)
        slb_apply_pose(slb, px, py, slb_z0, ACTIVE_POSE)
        slbs.append(slb)

place_side("L", row_center_L)
place_side("R", row_center_R)

# ---------------- Columns (ohne FL) ----------------
columns = []
def add_col(name, x, y):
    h = lv2_base_z
    columns.append(mk_box(name, COL_W, COL_D, h, x, y, 0.0))

add_col("Col_FR", PLAT_X - COL_W, 0)
add_col("Col_RL", 0, PLAT_Y - COL_D)
add_col("Col_RR", PLAT_X - COL_W, PLAT_Y - COL_D)

if ADD_MID_X:
    add_col("Col_Mx_L", (PLAT_X - COL_W)/2.0, 0)
    add_col("Col_Mx_R", (PLAT_X - COL_W)/2.0, PLAT_Y - COL_D)
if ADD_MID_Y:
    add_col("Col_My_F", 0, (PLAT_Y - COL_D)/2.0)
    add_col("Col_My_R", PLAT_X - COL_W, (PLAT_Y - COL_D)/2.0)

# ---------------- Grouping ----------------
grp_lvl1 = add("App::DocumentObjectGroup", "G_Ebene1")
grp_lvl1.addObjects([platform] + slots + drawers + [rail_L, rail_R])

grp_lvl2 = add("App::DocumentObjectGroup", "G_Ebene2")
grp_lvl2.addObjects([lv2_plate] + hplates + slbs + columns)

assembly = add("App::DocumentObjectGroup", "Assembly_Proxy")
assembly.addObjects([grp_lvl1, grp_lvl2])

App.ActiveDocument.recompute()

# ---------------- Export ----------------
fcstd_path = os.path.join(BUILD_DIR, "TARS_v0.6.FCStd")
App.ActiveDocument.saveAs(fcstd_path)

step_path = os.path.join(BUILD_DIR, f"TARS_v0.6_{ACTIVE_POSE}.step")
export_geom = [platform] + slots + drawers + [rail_L, rail_R, lv2_plate] + hplates + slbs + columns
Part.export(export_geom, step_path)

print(f"Saved FCStd: {fcstd_path}")
print(f"Saved STEP:  {step_path}")
App.closeDocument(App.ActiveDocument.Name)

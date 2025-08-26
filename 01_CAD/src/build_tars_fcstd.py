# 01_CAD/src/build_tars_fcstd.py
# FreeCAD headless builder for trailer assembly with two levels and 4 SLBs
# v0.5 — single-file, self-contained

import os, math
import FreeCAD as App
import Part

# ---------------- Paths ----------------
REPO_ROOT = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
BUILD_DIR = os.path.join(REPO_ROOT, "01_CAD", "build")
os.makedirs(BUILD_DIR, exist_ok=True)

DOC = App.newDocument("TARS_v0_5")
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

# SLB dimensions (transport pose extents)
SLB_X, SLB_Y, SLB_Z = 970.0, 960.0, 923.0  # x along travel, y transverse, z vertical in transport
SLB_PER_SIDE = 2

# H-Plate (inside SLB footprint and within level-2 plate)
HPL_THK = 12.0
HPL_X_MARGIN = 40.0  # H-plate smaller than SLB footprint
HPL_Y_MARGIN = 40.0
HPL_SLOT_W, HPL_SLOT_L, HPL_SLOT_OFF_Y = 28.0, 140.0, 35.0  # elongated slots (left/right)
HPL_CENTER_D = 520.0  # central clearance hole
HPL_RING_OD, HPL_RING_ID, HPL_RING_THK = 680.0, 600.0, 6.0  # visual swivel ring
DETENT_W, DETENT_L, DETENT_H = 22.0, 40.0, 8.0              # detent blocks

# Columns (Stützen): no Col_FL; others optional
COL_W = 100.0
COL_D = 100.0
ADD_MID_X = True
ADD_MID_Y = True

# Active SLB pose (transport | load | use)
ACTIVE_POSE = os.environ.get("SLB_POSE", "transport").strip().lower()
if ACTIVE_POSE not in ("transport", "load", "use"):
    ACTIVE_POSE = "transport"

# ---------------- Level 1: Platform, slots, drawers ----------------
# Platform plate: thickness extends below z=0 so top is z=0
platform = mk_box("Platform", PLAT_X, PLAT_Y, PLAT_T, 0, 0, -PLAT_T)

slots = []
drawers = []

# Compute slot row length in x
slot_row_len = NUM_SLOTS_X_PER_SIDE * SLOT_X + (NUM_SLOTS_X_PER_SIDE - 1) * SLOT_GAP_X
# Center the rows in x on the platform
slot_row_x0 = (PLAT_X - slot_row_len) / 2.0

# Y positions for left and right slot rows (open to the outside)
slot_y_left  = SIDE_CLEAR_Y
slot_y_right = PLAT_Y - SIDE_CLEAR_Y - SLOT_Y

# Z position of slots (sit on platform top)
slot_z0 = 0.0

def add_slot_row(label, y0):
    # 5 housings along x, each with two drawer proxies
    for i in range(NUM_SLOTS_X_PER_SIDE):
        x0 = slot_row_x0 + i * (SLOT_X + SLOT_GAP_X)
        s = mk_box(f"Slot_{label}_{i+1}", SLOT_X, SLOT_Y, SLOT_Z, x0, y0, slot_z0)
        slots.append(s)
        # two drawers as proxies, inset inside housing
        inx = x0 + SLOT_WALL
        iny = y0 + SLOT_WALL
        inz1 = slot_z0 + SLOT_WALL
        inz2 = inz1 + BOX_Z + SLOT_WALL
        d1 = mk_box(f"Drawer_{label}_{i+1}_1", BOX_X, BOX_Y, BOX_Z, inx, iny, inz1)
        d2 = mk_box(f"Drawer_{label}_{i+1}_2", BOX_X, BOX_Y, BOX_Z, inx, iny, inz2)
        drawers.extend([d1, d2])

add_slot_row("L", slot_y_left)
add_slot_row("R", slot_y_right)

# Rails on top of slot rows (continuous)
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
    # Base size within SLB footprint
    hpx = SLB_X - 2 * HPL_X_MARGIN
    hpy = SLB_Y - 2 * HPL_Y_MARGIN
    base = Part.makeBox(hpx, hpy, HPL_THK, App.Vector(px, py, pz))

    # Central clearance hole
    center = App.Vector(px + hpx/2.0, py + hpy/2.0, pz)
    cyl = Part.makeCylinder(HPL_CENTER_D/2.0, HPL_THK, center, App.Vector(0,0,1))
    base = base.cut(cyl)

    # Long slots (left/right), through cuts
    # Oriented along x, offset in y by +/- HPL_SLOT_OFF_Y from centerline
    def slot_cut(y_sign):
        sx = HPL_SLOT_L
        sy = HPL_SLOT_W
        sz = HPL_THK + 1.0
        sx0 = px + (hpx - sx)/2.0
        sy0 = (py + hpy/2.0) + y_sign * (HPL_SLOT_OFF_Y + sy/2.0) - sy/2.0
        return Part.makeBox(sx, sy, sz, App.Vector(sx0, sy0, pz - 0.5))
    base = base.cut(slot_cut(+1))
    base = base.cut(slot_cut(-1))

    # Visual swivel ring (a raised annulus)
    ring_t = HPL_RING_THK
    ring = Part.makeCylinder(HPL_RING_OD/2.0, ring_t, center, App.Vector(0,0,1)) \
           .cut(Part.makeCylinder(HPL_RING_ID/2.0, ring_t, center, App.Vector(0,0,1)))
    ring_feat = mk_feat(name + "_Ring", ring, 0, 0, 0)

    # Detent blocks for 0°, 33°, 90° along the front edge (approximate placement)
    detents = []
    def add_detent(lbl, angle_deg, r_offset):
        # Place on top surface, arc around center to suggest index marks
        r = min(hpx, hpy) * 0.35 + r_offset
        ang = math.radians(angle_deg)
        cx = center.x; cy = center.y; cz = pz + HPL_THK
        dx = r * math.cos(ang)
        dy = r * math.sin(ang)
        bx = cx + dx - DETENT_L/2.0
        by = cy + dy - DETENT_W/2.0
        det = Part.makeBox(DETENT_L, DETENT_W, DETENT_H, App.Vector(bx, by, cz))
        detents.append(mk_feat(f"{name}_detent_{lbl}", det))
    add_detent("0",   0,   0)
    add_detent("33",  math.copysign(33, +1), 0)
    add_detent("m33", math.copysign(33, -1), 0)
    add_detent("90",  90,  0)
    add_detent("m90", -90, 0)

    base_feat = mk_feat(name, base)
    return base_feat, ring_feat, detents

# ---------------- SLB pose helpers ----------------
def slb_pose_footprint(dx, dy, dz, pose):
    # projected footprint (x,y) for clamping on Level2 plate
    if pose == "transport":   # 0/0
        return dx, dy
    if pose == "load":        # 90/0 -> swap x/y
        return dy, dx
    if pose == "use":         # 33/49 -> conservative projection
        from math import cos, sin, radians
        fx = dx * cos(radians(33)) + dz * sin(radians(49))
        fy = dy  # horiz rot by 33° barely expands y in our convention
        return fx, fy
    return dx, dy

def place_slb_with_pose(name_prefix, base_px, base_py, base_pz, pose):
    # Create base box at given base corner (transport orientation)
    base_shape = Part.makeBox(SLB_X, SLB_Y, SLB_Z, App.Vector(base_px, base_py, base_pz))
    cx = base_px + SLB_X/2.0
    cy = base_py + SLB_Y/2.0
    cz = base_pz + SLB_Z/2.0

    def make_pose(shape, h_deg, v_deg, visible):
        shp = shape.copy()
        # 1) horizontal rotate around global z about center
        rot_z = App.Rotation(App.Vector(0,0,1), h_deg)
        shp.Placement = App.Placement(App.Vector(cx,cy,cz), rot_z, App.Vector(cx,cy,cz))
        # 2) vertical tilt around local y at bottom face center
        pivot = App.Vector(cx, cy, base_pz)  # bottom center
        rot_y = App.Rotation(App.Vector(0,1,0), v_deg)
        shp.Placement = App.Placement(pivot, shp.Placement.Rotation.multiply(rot_y), pivot)
        obj = mk_feat(f"{name_prefix}_{h_deg}_{v_deg}", shp)
        try:
            obj.ViewObject.Visibility = visible
        except Exception:
            pass
        return obj

    vis = {"transport": (True, False, False),
           "load":      (False, True, False),
           "use":       (False, False, True)}.get(pose, (True, False, False))

    o_t = make_pose(base_shape, 0, 0, vis[0])
    o_l = make_pose(base_shape, 90, 0, vis[1])
    o_u = make_pose(base_shape, 33, 49, vis[2])

    active_obj = o_t if vis[0] else (o_l if vis[1] else o_u)
    return active_obj, [o_t, o_l, o_u]

# ---------------- SLB placement ----------------
# Choose target centers along x (two positions): ~1/4 and ~3/4 of platform length
slb_centers_x = [PLAT_X * 0.25, PLAT_X * 0.75]

# Row centers in y located over slot rows
row_center_L = rail_y_center_L
row_center_R = rail_y_center_R

hplates = []
slb_active = []
slb_all = []

def place_side(side_label, row_center_y):
    for j, cx_mid in enumerate(slb_centers_x, start=1):
        fx, fy = slb_pose_footprint(SLB_X, SLB_Y, SLB_Z, ACTIVE_POSE)
        # bottom-left corner from center minus half footprint
        px = clamp(cx_mid - fx/2.0, 0.0, PLAT_X - fx)
        py = clamp(row_center_y - fy/2.0, 0.0, PLAT_Y - fy)

        # H-Plate footprint must sit inside SLB footprint and level-2 plate
        hpx = SLB_X - 2 * HPL_X_MARGIN
        hpy = SLB_Y - 2 * HPL_Y_MARGIN
        hp_x = px + (fx - hpx) / 2.0
        hp_y = py + (fy - hpy) / 2.0
        hp, hp_ring, hp_dets = make_hplate(f"Hplate_{side_label}{j}", hp_x, hp_y, lv2_top_z)
        hplates.extend([hp, hp_ring] + hp_dets)

        # SLB sits on top of H-plate
        slb_z0 = lv2_top_z + HPL_THK
        active, all_objs = place_slb_with_pose(f"SLB_{side_label}_{j}", px, py, slb_z0, ACTIVE_POSE)
        slb_active.append(active)
        slb_all.extend(all_objs)

place_side("L", row_center_L)
place_side("R", row_center_R)

# ---------------- Columns (no Col_FL) ----------------
columns = []
def add_col(name, x, y):
    h = lv2_base_z  # up to underside of level-2 plate
    columns.append(mk_box(name, COL_W, COL_D, h, x, y, 0.0))

# FR, RL, RR corners (omit FL)
add_col("Col_FR", PLAT_X - COL_W, 0)
add_col("Col_RL", 0, PLAT_Y - COL_D)
add_col("Col_RR", PLAT_X - COL_W, PLAT_Y - COL_D)

# mid in x (left & right)
if ADD_MID_X:
    add_col("Col_Mx_L", (PLAT_X - COL_W)/2.0, 0)
    add_col("Col_Mx_R", (PLAT_X - COL_W)/2.0, PLAT_Y - COL_D)
# mid in y (front & rear)
if ADD_MID_Y:
    add_col("Col_My_F", 0, (PLAT_Y - COL_D)/2.0)
    add_col("Col_My_R", PLAT_X - COL_W, (PLAT_Y - COL_D)/2.0)

# ---------------- Grouping ----------------
grp_lvl1 = add("App::DocumentObjectGroup", "G_Ebene1")
grp_lvl1.addObjects([platform] + slots + drawers + [rail_L, rail_R])

grp_lvl2 = add("App::DocumentObjectGroup", "G_Ebene2")
grp_lvl2.addObjects([lv2_plate] + hplates + slb_all + columns)

assembly = add("App::DocumentObjectGroup", "Assembly_Proxy")
assembly.addObjects([grp_lvl1, grp_lvl2])

App.ActiveDocument.recompute()

# ---------------- Export (active pose only to STEP) ----------------
fcstd_path = os.path.join(BUILD_DIR, "TARS_v0.5.FCStd")
App.ActiveDocument.saveAs(fcstd_path)

step_path = os.path.join(BUILD_DIR, f"TARS_v0.5_{ACTIVE_POSE}.step")
export_geom = [platform] + slots + drawers + [rail_L, rail_R, lv2_plate] + hplates + slb_active + columns
Part.export(export_geom, step_path)

print(f"Saved FCStd: {fcstd_path}")
print(f"Saved STEP:  {step_path}")
App.closeDocument(App.ActiveDocument.Name)

# 01_CAD/src/build_tars_fcstd.py
import os, math
import FreeCAD as App
import Part

repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
build_dir = os.path.join(repo_root, "01_CAD", "build")
os.makedirs(build_dir, exist_ok=True)

doc = App.newDocument("TARS_v0_3")
a = doc.addObject

def mk_feat(name, shape, px=0, py=0, pz=0):
    o = a("Part::Feature", name); o.Shape = shape; o.Placement.Base = App.Vector(px,py,pz); return o
def mk_box(name, dx, dy, dz, px=0, py=0, pz=0): return mk_feat(name, Part.makeBox(dx,dy,dz), px,py,pz)
def clamp(v, vmin, vmax): return max(vmin, min(v, vmax))

# ---------- Parameter (mm) ----------
# Ebene 1 Platte
PLAT_X, PLAT_Y, PLAT_Z = 2967.0, 2483.0, 30.0

# Schubladen/Slots
BOX_X, BOX_Y, BOX_Z = 521.0, 717.0, 130.0
SLOT_WALL = 3.0
SLOT_X = BOX_X + 2*SLOT_WALL
SLOT_Y = BOX_Y + 2*SLOT_WALL
SLOT_Z = 2*BOX_Z + 3*SLOT_WALL
NUM_SLOTS_X_PER_SIDE = 5
SLOT_GAP_X = 20.0
SIDE_CLEAR_Y = 40.0

# Auflager-Schienen (Rails) oben auf Slots
RAIL_W = 60.0          # Breite (y)
RAIL_H = 20.0          # Höhe (z) – trägt Ebene 2
RAIL_INSET_Y = 10.0    # von Slot-Reihen-Mitte nach innen (Mittelgang)

# Ebene 2 (Deckplatte)
LV2_PLATE_THK = 20.0

# SLB (Außenmaße in Transportpose)
SLB_X, SLB_Y, SLB_Z = 970.0, 960.0, 923.0
SLB_PER_SIDE = 2

# H-Plate (muss innerhalb SLB-Footprint + Ebene2 bleiben)
HPL_THK = 12.0
HPL_X_MARGIN = 40.0   # H-Plate kleiner als SLB in x: SLB_X - 2*margin
HPL_Y_MARGIN = 40.0
HPL_SLOT_W, HPL_SLOT_L, HPL_SLOT_OFF_Y = 28.0, 140.0, 35.0
HPL_CENTER_D = 520.0
HPL_RING_OD, HPL_RING_ID, HPL_RING_THK = 680.0, 600.0, 6.0
DETENT_W, DETENT_L, DETENT_H = 22.0, 40.0, 8.0

# Stützen (nur Ecken/Mitte, Col_FL entfällt)
COL_W = 100.0
COL_D = 100.0
ADD_MID_X, ADD_MID_Y = True, True

# ---------- Ebene 1 ----------
platform = mk_box("Platform", PLAT_X, PLAT_Y, PLAT_Z, 0, 0, -PLAT_Z)

slot_total_x = NUM_SLOTS_X_PER_SIDE * SLOT_X + (NUM_SLOTS_X_PER_SIDE - 1)*SLOT_GAP_X
front_margin_x = max(0.0, (PLAT_X - slot_total_x)/2.0)
left_row_y  = SIDE_CLEAR_Y
right_row_y = PLAT_Y - SIDE_CLEAR_Y - SLOT_Y

slots, drawers = [], []
for side_idx, base_y, side_label in [(0,left_row_y,"L"), (1,right_row_y,"R")]:
    for i in range(NUM_SLOTS_X_PER_SIDE):
        px = front_margin_x + i*(SLOT_X + SLOT_GAP_X); py = base_y
        slot = mk_box(f"Slot_{side_label}_{i+1}", SLOT_X, SLOT_Y, SLOT_Z, px, py, 0.0); slots.append(slot)
        inset = 1.0
        bx = px + SLOT_WALL + inset; by = py + SLOT_WALL + inset
        bz1 = SLOT_WALL + inset; bz2 = bz1 + BOX_Z + SLOT_WALL
        drawers.append(mk_box(f"Drawer_{side_label}_{i+1}_A", BOX_X, BOX_Y, BOX_Z, bx, by, bz1))
        drawers.append(mk_box(f"Drawer_{side_label}_{i+1}_B", BOX_X, BOX_Y, BOX_Z, bx, by, bz2))

top_of_slots_z = SLOT_Z

# ---------- Rails auf Slot-Reihen (tragen Ebene 2) ----------
# Rail-Lage: je Reihe eine durchgehende Schiene entlang x, zentriert über der Reihe,
# leicht zum Mittelgang versetzt (RAIL_INSET_Y), damit sie innerhalb der Ebene2 bleibt.
def rail_y(center_y, to_middle_positive=True):
    offset = RAIL_INSET_Y if to_middle_positive else -RAIL_INSET_Y
    return center_y - RAIL_W/2.0 + offset

row_center_L = left_row_y + SLOT_Y/2.0
row_center_R = right_row_y + SLOT_Y/2.0
rail_L_y = clamp(rail_y(row_center_L, True), 0.0, PLAT_Y - RAIL_W)
rail_R_y = clamp(rail_y(row_center_R, False), 0.0, PLAT_Y - RAIL_W)
rail_L = mk_box("Rail_L", slot_total_x, RAIL_W, RAIL_H, front_margin_x, rail_L_y, top_of_slots_z)
rail_R = mk_box("Rail_R", slot_total_x, RAIL_W, RAIL_H, front_margin_x, rail_R_y, top_of_slots_z)

# Unterseite Ebene 2 liegt auf Rails auf:
lv2_base_z = top_of_slots_z + RAIL_H
lv2_plate  = mk_box("Level2_Plate", PLAT_X, PLAT_Y, LV2_PLATE_THK, 0, 0, lv2_base_z)
lv2_top_z  = lv2_base_z + LV2_PLATE_THK

# ---------- H-Plate (Foto-Proxy, bleibt innerhalb SLB footprint) ----------
def make_hplate(name, px, py, pz):
    HPL_X = SLB_X - 2*HPL_X_MARGIN
    HPL_Y = SLB_Y - 2*HPL_Y_MARGIN
    base = Part.makeBox(HPL_X, HPL_Y, HPL_THK)

    # zentrale Öffnung
    hole = Part.makeCylinder(HPL_CENTER_D/2.0, HPL_THK, App.Vector(HPL_X/2, HPL_Y/2, 0))
    base = base.cut(hole)

    # Langlöcher links/rechts
    def slot_shape(cx, cy):
        rect = Part.makeBox(HPL_SLOT_L, HPL_SLOT_W, HPL_THK, App.Vector(cx - HPL_SLOT_L/2, cy - HPL_SLOT_W/2, 0))
        r = HPL_SLOT_W/2.0
        cyl1 = Part.makeCylinder(r, HPL_THK, App.Vector(cx - HPL_SLOT_L/2, cy, 0))
        cyl2 = Part.makeCylinder(r, HPL_THK, App.Vector(cx + HPL_SLOT_L/2, cy, 0))
        return rect.fuse(cyl1).fuse(cyl2)
    y_lo = HPL_SLOT_OFF_Y + HPL_SLOT_W/2.0
    y_hi = HPL_Y - HPL_SLOT_OFF_Y - HPL_SLOT_W/2.0
    x1, x2 = HPL_X*0.25, HPL_X*0.75
    for s in [slot_shape(x1,y_lo), slot_shape(x2,y_lo), slot_shape(x1,y_hi), slot_shape(x2,y_hi)]:
        base = base.cut(s)

    # Ring-Relief
    ring_od = Part.makeCylinder(HPL_RING_OD/2.0, HPL_RING_THK, App.Vector(HPL_X/2, HPL_Y/2, HPL_THK - HPL_RING_THK))
    ring_id = Part.makeCylinder(HPL_RING_ID/2.0, HPL_RING_THK, App.Vector(HPL_X/2, HPL_Y/2, HPL_THK - HPL_RING_THK))
    ring = ring_od.cut(ring_id)
    body = base.fuse(ring)

    # Detents 0°/33°/90°
    detent_r = (HPL_RING_OD/2.0 + HPL_RING_ID/2.0)/2.0
    for ang_deg in [0, 33, 90]:
        ang = math.radians(ang_deg)
        cx = HPL_X/2 + detent_r*math.cos(ang)
        cy = HPL_Y/2 + detent_r*math.sin(ang)
        det = Part.makeBox(DETENT_L, DETENT_W, DETENT_H, App.Vector(cx-DETENT_L/2, cy-DETENT_W/2, HPL_THK-DETENT_H))
        body = body.fuse(det)

    obj = mk_feat(name, body, px, py, pz)
    return obj, HPL_X, HPL_Y

# ---------- SLB-Platzierung (2 je Seite) ----------
slb_centers_x = [front_margin_x + 0.25*slot_total_x, front_margin_x + 0.75*slot_total_x]
hplates, slb_bodies = [], []

# --- neue Parameter ---
ACTIVE_POSE = os.environ.get("SLB_POSE", "transport")  # "transport" | "load" | "use"

# Hilfsfunktionen für Posen
def slb_pose_bbox(dx, dy, dz, pose):
    if pose == "transport":   # 0°/0°
        return dx, dy
    if pose == "load":        # 90°/0° -> footprint tauscht x/y
        return dy, dx
    if pose == "use":         # 33°/49° -> projizierte Bounding Box (konservativ)
        # Näherung: horizontale 33°-Drehung ändert footprint kaum, 49°-Kippung projiziert z in x
        # Wir rechnen grob: x' ~= dx*cos33 + dz*sin49, y' ~= dy
        from math import cos, sin, radians
        return dx*cos(radians(33)) + dz*sin(radians(49)), dy
    return dx, dy

def place_slb_with_pose(name_prefix, base_px, base_py, base_pz, pose):
    # Basis: SLB in Transportlage an base_px/base_py/base_pz (Unterkante auf H-Plate)
    cx = base_px + SLB_X/2.0
    cy = base_py + SLB_Y/2.0
    cz = base_pz + SLB_Z/2.0

    # Erzeuge drei Geometrien, aber schalte nur die aktive Pose sichtbar
    base_box = Part.makeBox(SLB_X, SLB_Y, SLB_Z, App.Vector(base_px, base_py, base_pz))

    def make_pose(shape, h_deg, v_deg, visible):
        # Horizontal um z durch Lagerzentrum drehen
        shp = shape.copy()
        rz = App.Rotation(App.Vector(0,0,1), h_deg)
        shp.Placement = App.Placement(App.Vector(cx,cy,cz), rz, App.Vector(cx,cy,cz))
        # Vertikal um lokale y, Achse an Unterseite (kippt nach oben)
        # Verlege das Drehzentrum auf (cx, cy, base_pz) = Unterkante der SLB
        pivot = App.Vector(cx, cy, base_pz)
        ry = App.Rotation(App.Vector(0,1,0), v_deg)
        shp.Placement = App.Placement(pivot, shp.Placement.Rotation.multiply(ry), pivot)
        obj = mk_feat(f"{name_prefix}_{h_deg}_{v_deg}", shp)
        try:
            obj.ViewObject.Visibility = visible
        except Exception:
            pass
        return obj

    vis_map = {
        "transport": {"t": True,  "l": False, "u": False},
        "load":      {"t": False, "l": True,  "u": False},
        "use":       {"t": False, "l": False, "u": True},
    }
    vm = vis_map.get(pose, vis_map["transport"])

    o_t = make_pose(base_box, 0,   0,  vm["t"])
    o_l = make_pose(base_box, 90,  0,  vm["l"])
    o_u = make_pose(base_box, 33, 49,  vm["u"])

    # Für Export wählen wir nur die aktive Pose
    active_obj = o_t if vm["t"] else (o_l if vm["l"] else o_u)
    return active_obj, [o_t, o_l, o_u]

# H-Plate bleibt wie zuvor; Ersetzung der SLB-Platzierung:
hplates, slb_active, slb_all = [], [], []
def place_side(side_label, row_center_y):
    for j, cx_mid in enumerate(slb_centers_x, start=1):
        # Clamp je nach aktiver Pose
        fx, fy = slb_pose_bbox(SLB_X, SLB_Y, SLB_Z, ACTIVE_POSE)
        px = clamp(cx_mid - fx/2.0, 0.0, PLAT_X - fx)
        py = clamp(row_center_y - fy/2.0, 0.0, PLAT_Y - fy)

        # H-Plate (voll innerhalb Ebene 2 und SLB footprint)
        hp, _, _ = make_hplate(f"Hplate_{side_label}{j}",
                               px + (fx - (SLB_X - 2*HPL_X_MARGIN))/2.0,
                               py + (fy - (SLB_Y - 2*HPL_Y_MARGIN))/2.0,
                               lv2_top_z)
        hplates.append(hp)

        # SLB sitzt auf H-Plate
        slb_z0 = lv2_top_z + HPL_THK
        active, all_objs = place_slb_with_pose(f"SLB_{side_label}_{j}", px, py, slb_z0, ACTIVE_POSE)
        slb_active.append(active)
        slb_all.extend(all_objs)

# Seiten platzieren
place_side("L", row_center_L)
place_side("R", row_center_R)

# Gruppen aktualisieren
grp_lvl2 = a("App::DocumentObjectGroup", "G_Ebene2")
grp_lvl2.addObjects([lv2_plate] + hplates + slb_all + columns)
assembly = a("App::DocumentObjectGroup", "Assembly_Proxy"); assembly.addObjects([grp_lvl1, grp_lvl2])

App.ActiveDocument.recompute()

# Export: nur aktive Posen
fcstd_path = os.path.join(build_dir, "TARS_v0.4.FCStd"); App.ActiveDocument.saveAs(fcstd_path)
step_path  = os.path.join(build_dir, "TARS_v0.4.step")
export_geom = [platform] + slots + drawers + [rail_L, rail_R, lv2_plate] + hplates + slb_active + columns
Part.export(export_geom, step_path)


print(f"Saved FCStd: {fcstd_path}")
print(f"Saved STEP:  {step_path}")
App.closeDocument(App.ActiveDocument.Name)

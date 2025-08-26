# 01_CAD/src/build_tars_fcstd.py
# Trailer assembly with two levels and 4 Swivel-Launch-Boxes (SLB) incl. elevated trunnion pivot
# v0.7 — FreeCAD 1.0 compatible; only 4 SLBs; poses as active configuration
# Author: assistant

import os
import math
import FreeCAD as App
import Part

# ---------------- Configuration ----------------
REPO_ROOT = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
BUILD_DIR = os.path.join(REPO_ROOT, "01_CAD", "build")
os.makedirs(BUILD_DIR, exist_ok=True)

ACTIVE_POSE = os.environ.get("SLB_POSE", "transport").lower()  # transport | load | use
if ACTIVE_POSE not in ("transport", "load", "use"):
    ACTIVE_POSE = "transport"

DOC = App.newDocument("TARS_v0_7")
add = DOC.addObject

def mk_feat(name, shape, base=(0,0,0), rot=None, center=None):
    o = add("Part::Feature", name)
    o.Shape = shape
    if rot is None:
        o.Placement = App.Placement(App.Vector(*base), App.Rotation())
    else:
        if center is None:
            o.Placement = App.Placement(App.Vector(*base), rot)
        else:
            o.Placement = App.Placement(App.Vector(*base), rot, App.Vector(*center))
    return o

def mk_box(name, dx, dy, dz):
    return add("Part::Feature", name) if False else mk_feat(name, Part.makeBox(dx, dy, dz))

def deg(a):  # helper for clarity if needed
    return a

# ---------------- Parameters (mm) ----------------
# Platform (Ebene 1)
PLAT_X, PLAT_Y, PLAT_T = 2967.0, 2483.0, 30.0

# Drawer boxes and slots (Ebene 1)
BOX_X, BOX_Y, BOX_Z = 521.0, 717.0, 130.0
SLOT_WALL = 3.0
SLOT_X = BOX_X + 2*SLOT_WALL
SLOT_Y = BOX_Y + 2*SLOT_WALL
SLOT_Z = 2*BOX_Z + 3*SLOT_WALL        # zwei Boxen übereinander + Wände
NUM_SLOTS_X_PER_SIDE = 5
SLOT_GAP_X = 20.0
SIDE_CLEAR_Y = 40.0                    # Abstand zur Außenkante Plattform

# Rails (Auflager für Ebene 2)
RAIL_W, RAIL_H = 60.0, 20.0

# Ebene 2 Deckplatte
LV2_PLATE_THK = 20.0
EDGE_SETBACK = 10.0                    # kleine Einrückung, um keine Überstände zu riskieren

# H-Plate (unter SLB)
HPL_THK = 12.0
HPL_X, HPL_Y = 750.0, 680.0            # footprint je SLB unter Ebene 2 (innerhalb der LV2-Platte)

# SLB (Kastenabmessungen)
SLB_X, SLB_Y, SLB_Z = 970.0, 960.0, 923.0   # Orientierung: X nach vorn (Fahrtrichtung), Y quer, Z hoch

# Erhöhte Kippachse (Trunnion) auf Dreiecks-Träger
STANDOFF_S = 60.0        # Abstand H-Plate -> SLB-Unterkante in Transportlage
PIVOT_OVER_TOP = 80.0    # Achshöhe über SLB-Oberkante
PIVOT_X_OFFSET = 385.0   # + nach vorn, relativ zur SLB-Mitte
CLEAR_USE = 20.0         # min. Freigängigkeit bei 49°

# Dreiecks-Träger (vereinfachte Geometrie; nur zur Visualisierung)
TRI_BASE_LEN = 520.0     # Länge der Grundlasche (x-Richtung)
TRI_BASE_W   = 80.0      # Breite (y-Richtung)
TRI_BASE_T   = 12.0
TRI_DIAG_BX  = 100.0     # Diagonalsteg Querschnitt (x)
TRI_DIAG_BY  = 40.0      # Diagonalsteg Querschnitt (y)
TRI_DIAG_T   = 8.0       # Diagonalsteg "Dicke" (z)
PIVOT_BLOCK_W = 40.0     # Lagerblock-Breite je Seite (y)
PIVOT_BLOCK_T = 15.0     # Lagerblock-Wandstärke (z)
PIVOT_SHAFT_D = 40.0     # Welle/Trunnion (nur angedeutet)

# Spacing/Positionierung der SLB auf Ebene 2
SLB_ROW_CLEAR_Y = 100.0  # Abstand von Außenkante LV2 zur SLB-Reihe
SLB_COL_GAP_X   = 200.0  # Abstand zwischen den zwei SLB je Seite in x
SLB_FRONT_SETBACK = 250.0  # Abstand der vorderen SLB von x=0

# Spalten (optional, ohne FL)
COL_W, COL_D = 80.0, 80.0
ADD_MID_X, ADD_MID_Y = True, False

# ---------------- Derived geometry levels ----------------
plat_top_z = 0.0
rail_top_z = plat_top_z + RAIL_H
lv2_base_z = rail_top_z + LV2_PLATE_THK  # Unterseite SLB-Aufbauten liegt auf LV2 (Deckplatte)
lv2_top_z  = rail_top_z                  # Oberseite Rails = Unterseite LV2-Platte

# ---------------- Builders ----------------
# Ebene 1: Plattform
platform = mk_feat("Platform", Part.makeBox(PLAT_X, PLAT_Y, PLAT_T), base=(0,0,-PLAT_T))

# Einschubkästen links/rechts
slots = []
drawers = []
def place_slot_row(side_label):
    # side_label: 'L' (Fahrerseite, y von 0) oder 'R' (Beifahrerseite, y hoch)
    if side_label == 'L':
        y0 = SIDE_CLEAR_Y
    else:
        y0 = PLAT_Y - SIDE_CLEAR_Y - SLOT_Y
    x = SLB_FRONT_SETBACK
    for i in range(NUM_SLOTS_X_PER_SIDE):
        slot = mk_feat(f"Slot_{side_label}_{i+1}",
                       Part.makeBox(SLOT_X, SLOT_Y, SLOT_Z),
                       base=(x, y0, plat_top_z))
        slots.append(slot)
        # zwei Drawer-Proxies (vereinfachte Visualisierung)
        d1 = mk_feat(f"Drawer_{side_label}_{i+1}_A",
                     Part.makeBox(BOX_X, BOX_Y, BOX_Z),
                     base=(x+SLOT_WALL, y0+SLOT_WALL, plat_top_z+SLOT_WALL))
        d2 = mk_feat(f"Drawer_{side_label}_{i+1}_B",
                     Part.makeBox(BOX_X, BOX_Y, BOX_Z),
                     base=(x+SLOT_WALL, y0+SLOT_WALL, plat_top_z+BOX_Z+2*SLOT_WALL))
        drawers.extend([d1, d2])
        x += SLOT_X + SLOT_GAP_X

place_slot_row('L')
place_slot_row('R')

# Rails
rail_L = mk_feat("Rail_L", Part.makeBox(PLAT_X-2*EDGE_SETBACK, RAIL_W, RAIL_H),
                 base=(EDGE_SETBACK, SIDE_CLEAR_Y + SLOT_Y + 10.0, plat_top_z))
rail_R = mk_feat("Rail_R", Part.makeBox(PLAT_X-2*EDGE_SETBACK, RAIL_W, RAIL_H),
                 base=(EDGE_SETBACK, PLAT_Y - SIDE_CLEAR_Y - SLOT_Y - 10.0 - RAIL_W, plat_top_z))

# Ebene 2 Deckplatte (liegt auf Rails, mit kleinem Rand)
lv2_plate = mk_feat("Level2_Plate",
                    Part.makeBox(PLAT_X-2*EDGE_SETBACK, PLAT_Y-2*EDGE_SETBACK, LV2_PLATE_THK),
                    base=(EDGE_SETBACK, EDGE_SETBACK, rail_top_z - LV2_PLATE_THK))

# ---------------- H-Plate und Dreiecks-Träger + Trunnion + SLB ----------------
hplates = []
triangles = []
trunnions = []
slbs = []

def make_hplate(name, cx, cy, z0):
    # H-förmig grob angenähert: zentrale Platte + zwei Stege
    parts = []
    # zentrale Platte
    cpl = Part.makeBox(HPL_X, HPL_Y, HPL_THK)
    # „Stege“ als Materialersparnis (ausgeschnitten)
    cut1 = Part.makeBox(HPL_X*0.7, HPL_Y*0.3, HPL_THK).translate(App.Vector(HPL_X*0.15, HPL_Y*0.35, 0))
    shp = cpl.cut(cut1)
    o = mk_feat(name, shp, base=(cx - HPL_X/2.0, cy - HPL_Y/2.0, lv2_top_z))
    return o

def make_triangle_supports(base_name, cx, cy, base_z, pivot_z, pivot_y_left, pivot_y_right):
    # Einfaches Dreieck: Grundlasche + Diagonalsteg + Lagerblöcke beidseitig
    out_objs = []
    # Grundlasche (liegt auf H-Plate)
    base_x0 = cx - TRI_BASE_LEN/2.0
    base_y0 = cy - TRI_BASE_W/2.0
    o_base = mk_feat(base_name+"_Base", Part.makeBox(TRI_BASE_LEN, TRI_BASE_W, TRI_BASE_T),
                     base=(base_x0, base_y0, base_z))
    out_objs.append(o_base)

    # Diagonalsteg (Box schräg gestellt)
    diag = Part.makeBox(TRI_DIAG_BX, TRI_DIAG_BY, TRI_DIAG_T)
    # Position vorne, anhebend zur Pivot-Höhe (nur visuell)
    diag_base = (cx - TRI_DIAG_BX/2.0, cy - TRI_DIAG_BY/2.0, base_z + TRI_BASE_T)
    diag_rot = App.Rotation(App.Vector(0,1,0), -25)  # leichte Anstellung
    o_diag = mk_feat(base_name+"_Diag", diag, base=diag_base, rot=diag_rot, center=(cx, cy, base_z))
    out_objs.append(o_diag)

    # Lagerblöcke links/rechts (y)
    # Links
    lb_l = mk_feat(base_name+"_PivotL",
                   Part.makeBox(PIVOT_BLOCK_T, PIVOT_BLOCK_W, PIVOT_BLOCK_T),
                   base=(cx - PIVOT_BLOCK_T/2.0, pivot_y_left - PIVOT_BLOCK_W/2.0, pivot_z - PIVOT_BLOCK_T/2.0))
    # Rechts
    lb_r = mk_feat(base_name+"_PivotR",
                   Part.makeBox(PIVOT_BLOCK_T, PIVOT_BLOCK_W, PIVOT_BLOCK_T),
                   base=(cx - PIVOT_BLOCK_T/2.0, pivot_y_right - PIVOT_BLOCK_W/2.0, pivot_z - PIVOT_BLOCK_T/2.0))
    out_objs.extend([lb_l, lb_r])

    # Trunnion-Welle (nur Darstellung, kurzer Zylinder je Seite)
    cyl = Part.makeCylinder(PIVOT_SHAFT_D/2.0, PIVOT_BLOCK_W)
    tr_l = mk_feat(base_name+"_ShaftL", cyl,
                   base=(cx, pivot_y_left - PIVOT_BLOCK_W/2.0, pivot_z),
                   rot=App.Rotation(App.Vector(0,1,0), 90), center=(cx, pivot_y_left, pivot_z))
    tr_r = mk_feat(base_name+"_ShaftR", cyl,
                   base=(cx, pivot_y_right - PIVOT_BLOCK_W/2.0, pivot_z),
                   rot=App.Rotation(App.Vector(0,1,0), 90), center=(cx, pivot_y_right, pivot_z))
    out_objs.extend([tr_l, tr_r])

    return out_objs

def slb_apply_pose(obj, base_corner, pivot_point, pose, horiz_deg_33=True):
    # base_corner: (x0,y0,z0) Unterkante-Links-Vorn des SLB in Transport
    # pivot_point: globaler Drehpunkt (x, y, z)
    # Posen: transport (0/0), load (90/0), use (33/49)
    x0,y0,z0 = base_corner
    px,py,pz = pivot_point

    if pose == "transport":
        rot = App.Rotation()
    elif pose == "load":
        # 90° horizontal um z
        rot = App.Rotation(App.Vector(0,0,1), 90)
    else:
        hz = 33.0 if horiz_deg_33 else 33.0
        rot = App.Rotation(App.Vector(0,0,1), hz).multiply(App.Rotation(App.Vector(0,1,0), 49.0))

    obj.Placement = App.Placement(App.Vector(x0, y0, z0), rot, App.Vector(px, py, pz))

def place_slb_pair(side_label, row_center_y, idx_base):
    # side_label: 'L' oder 'R'
    # row_center_y: Mittelpunkt der SLB-Reihe in Y
    # idx_base: Laufindexbasis (1/3)
    global hplates, triangles, trunnions, slbs

    # Zwei SLB je Seite, in X verteilt
    x1 = SLB_FRONT_SETBACK
    x2 = x1 + SLB_X + SLB_COL_GAP_X

    for j, x_center in enumerate([x1 + SLB_X/2.0, x2 + SLB_X/2.0], start=0):
        name_tag = f"{side_label}{idx_base+j}"
        cx, cy = x_center, row_center_y

        # H-Plate
        hp = make_hplate(f"HPlate_{name_tag}", cx, cy, lv2_top_z)
        hplates.append(hp)

        # Trunnion-Höhe und -Position
        slb_base_z = lv2_top_z + HPL_THK + STANDOFF_S
        z_p = slb_base_z + SLB_Z + PIVOT_OVER_TOP
        x_p = cx + PIVOT_X_OFFSET
        # y links/rechts für Lagerblöcke (jeweils knapp außerhalb SLB-Y)
        y_left  = cy - SLB_Y/2.0 - PIVOT_BLOCK_W/2.0 - 10.0
        y_right = cy + SLB_Y/2.0 + PIVOT_BLOCK_W/2.0 + 10.0

        # Dreiecks-Träger + Lagerblöcke + Wellen (visual)
        tri_objs = make_triangle_supports(f"Tri_{name_tag}", cx, cy, lv2_top_z + HPL_THK, z_p, y_left, y_right)
        triangles.extend(tri_objs)

        # SLB-Körper (ein Objekt)
        slb = mk_feat(f"SLB_{name_tag}", Part.makeBox(SLB_X, SLB_Y, SLB_Z))
        # Basis-Ecke unten-vorn-links in Transport
        base_corner = (cx - SLB_X/2.0, cy - SLB_Y/2.0, slb_base_z)
        pivot_point = (x_p, cy, z_p)
        slb_apply_pose(slb, base_corner, pivot_point, ACTIVE_POSE)
        slbs.append(slb)

# Y-Positionen der Reihen so, dass alles innerhalb LV2-Platte bleibt
lv2_min_y = EDGE_SETBACK
lv2_max_y = PLAT_Y - EDGE_SETBACK
row_center_L = lv2_min_y + SLB_ROW_CLEAR_Y + SLB_Y/2.0
row_center_R = lv2_max_y - SLB_ROW_CLEAR_Y - SLB_Y/2.0

place_slb_pair('L', row_center_L, 1)
place_slb_pair('R', row_center_R, 3)

# ---------------- Columns (ohne FL) ----------------
columns = []
def add_col(name, x, y):
    h = lv2_base_z
    columns.append(mk_feat(name, Part.makeBox(COL_W, COL_D, h), base=(x, y, 0.0)))

# Ecken außer FL
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
grp_lvl2.addObjects([lv2_plate] + hplates + triangles + slbs + columns)

assembly = add("App::DocumentObjectGroup", "Assembly_Proxy")
assembly.addObjects([grp_lvl1, grp_lvl2])

App.ActiveDocument.recompute()

# ---------------- Export ----------------
fcstd_path = os.path.join(BUILD_DIR, "TARS_v0.7.FCStd")
App.ActiveDocument.saveAs(fcstd_path)

step_path = os.path.join(BUILD_DIR, f"TARS_v0.7_{ACTIVE_POSE}.step")
export_geom = [platform] + slots + drawers + [rail_L, rail_R, lv2_plate] + hplates + triangles + slbs + columns
Part.export(export_geom, step_path)

print(f"Saved FCStd: {fcstd_path}")
print(f"Saved STEP:  {step_path}")
App.closeDocument(App.ActiveDocument.Name)

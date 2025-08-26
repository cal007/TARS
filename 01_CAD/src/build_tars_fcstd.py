# 01_CAD/src/build_tars_fcstd.py
# Trailer assembly with two levels and 4 SLBs, elevated trunnion pivot on triangle supports
# v0.8 — FreeCAD 1.0 verified, corrected Z-levels and pivot placement, only 4 SLBs
# Author: assistant

import os, math
import FreeCAD as App
import Part

# ---------------- Environment ----------------
REPO_ROOT = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
BUILD_DIR  = os.path.join(REPO_ROOT, "01_CAD", "build")
os.makedirs(BUILD_DIR, exist_ok=True)

ACTIVE_POSE = os.environ.get("SLB_POSE", "transport").lower()  # transport | load | use
if ACTIVE_POSE not in ("transport","load","use"):
    ACTIVE_POSE = "transport"
DEBUG = os.environ.get("DEBUG","0") == "1"

DOC = App.newDocument("TARS_v0_8")
add = DOC.addObject

def mk_feat(name, shape, base=(0,0,0), rot=None, center=None):
    o = add("Part::Feature", name)
    o.Shape = shape
    if rot is None and center is None:
        o.Placement = App.Placement(App.Vector(*base), App.Rotation())
    else:
        o.Placement = App.Placement(App.Vector(*base), rot or App.Rotation(), App.Vector(*(center or (0,0,0))))
    return o

# ---------------- Parameters (mm) ----------------
# Platform (Ebene 1)
PLAT_X, PLAT_Y, PLAT_T = 2967.0, 2483.0, 30.0  # z=0 ist Oberseite Plattform

# Drawer boxes (Ebene 1)
BOX_X, BOX_Y, BOX_Z = 521.0, 717.0, 130.0
SLOT_WALL = 3.0
SLOT_X = BOX_X + 2*SLOT_WALL
SLOT_Y = BOX_Y + 2*SLOT_WALL
SLOT_Z = 2*BOX_Z + 3*SLOT_WALL
NUM_SLOTS_X_PER_SIDE = 5
SLOT_GAP_X = 20.0
SIDE_CLEAR_Y = 40.0

# Rails (Auflager für Ebene 2)
RAIL_W, RAIL_H = 60.0, 20.0

# Ebene 2 Deckplatte
LV2_PLATE_THK = 20.0
EDGE_SETBACK = 10.0

# H-Plate unter SLB
HPL_THK = 12.0
HPL_X, HPL_Y = 750.0, 680.0

# SLB (Außenabmessungen)
SLB_X, SLB_Y, SLB_Z = 970.0, 960.0, 923.0

# Trunnion/Abstände
STANDOFF_S      = 60.0     # H-Plate -> SLB-Unterkante in Transport
PIVOT_OVER_TOP  = 80.0     # Achse über SLB-Oberkante
PIVOT_X_OFFSET  = 385.0    # + nach vorn ab SLB-Mitte
CLEAR_USE       = 20.0     # Mind. Spiel bei 49°

# Dreiecks-Träger (vereinfacht zur Visualisierung)
TRI_BASE_LEN, TRI_BASE_W, TRI_BASE_T = 520.0, 80.0, 12.0
TRI_DIAG_BX,  TRI_DIAG_BY, TRI_DIAG_T = 100.0, 40.0, 8.0
PIVOT_BLOCK_W, PIVOT_BLOCK_T = 40.0, 15.0
PIVOT_SHAFT_D = 40.0

# Positionierung SLB
SLB_ROW_CLEAR_Y   = 100.0
SLB_COL_GAP_X     = 200.0
SLB_FRONT_SETBACK = 250.0

# Stützen (Dummy)
COL_W, COL_D = 80.0, 80.0
ADD_MID_X, ADD_MID_Y = True, False

# ---------------- Z-Kette (sauber) ----------------
plat_top_z  = 0.0                        # z=0 ist Oberseite Ebene 1
rail_base_z = plat_top_z                 # Rails stehen auf Ebene 1
rail_top_z  = rail_base_z + RAIL_H
lv2_base_z  = rail_top_z                 # Unterseite Ebene-2-Platte
lv2_top_z   = lv2_base_z + LV2_PLATE_THK # Oberseite Ebene-2-Platte (Auflage H-Plate)

# ---------------- Ebene 1 ----------------
platform = mk_feat("Platform", Part.makeBox(PLAT_X, PLAT_Y, PLAT_T), base=(0,0,-PLAT_T))

slots, drawers = [], []

def place_slot_row(side):
    y0 = SIDE_CLEAR_Y if side=='L' else (PLAT_Y - SIDE_CLEAR_Y - SLOT_Y)
    x  = SLB_FRONT_SETBACK
    for i in range(NUM_SLOTS_X_PER_SIDE):
        slot = mk_feat(f"Slot_{side}_{i+1}", Part.makeBox(SLOT_X,SLOT_Y,SLOT_Z), base=(x, y0, plat_top_z))
        slots.append(slot)
        d1 = mk_feat(f"Drawer_{side}_{i+1}_A", Part.makeBox(BOX_X,BOX_Y,BOX_Z),
                     base=(x+SLOT_WALL, y0+SLOT_WALL, plat_top_z+SLOT_WALL))
        d2 = mk_feat(f"Drawer_{side}_{i+1}_B", Part.makeBox(BOX_X,BOX_Y,BOX_Z),
                     base=(x+SLOT_WALL, y0+SLOT_WALL, plat_top_z+BOX_Z+2*SLOT_WALL))
        drawers.extend([d1,d2])
        x += SLOT_X + SLOT_GAP_X

place_slot_row('L')
place_slot_row('R')

rail_L = mk_feat("Rail_L", Part.makeBox(PLAT_X-2*EDGE_SETBACK, RAIL_W, RAIL_H),
                 base=(EDGE_SETBACK, SIDE_CLEAR_Y + SLOT_Y + 10.0, rail_base_z))
rail_R = mk_feat("Rail_R", Part.makeBox(PLAT_X-2*EDGE_SETBACK, RAIL_W, RAIL_H),
                 base=(EDGE_SETBACK, PLAT_Y - SIDE_CLEAR_Y - SLOT_Y - 10.0 - RAIL_W, rail_base_z))

lv2_plate = mk_feat("Level2_Plate",
                    Part.makeBox(PLAT_X-2*EDGE_SETBACK, PLAT_Y-2*EDGE_SETBACK, LV2_PLATE_THK),
                    base=(EDGE_SETBACK, EDGE_SETBACK, lv2_base_z))

# ---------------- Ebene 2: H-Plate, Träger, Trunnion, SLB ----------------
hplates, triangles, slbs = [], [], []

def make_hplate(name, cx, cy):
    shp = Part.makeBox(HPL_X, HPL_Y, HPL_THK)
    cut = Part.makeBox(HPL_X*0.7, HPL_Y*0.3, HPL_THK).translate(App.Vector(HPL_X*0.15, HPL_Y*0.35, 0))
    shp = shp.cut(cut)
    return mk_feat(name, shp, base=(cx - HPL_X/2.0, cy - HPL_Y/2.0, lv2_top_z))

def make_triangle_supports(base_name, cx, cy, pivot_z, pivot_y_left, pivot_y_right):
    out = []
    # Grundlasche
    o_base = mk_feat(base_name+"_Base", Part.makeBox(TRI_BASE_LEN,TRI_BASE_W,TRI_BASE_T),
                     base=(cx-TRI_BASE_LEN/2.0, cy-TRI_BASE_W/2.0, lv2_top_z))
    out.append(o_base)
    # Diagonalsteg (nur Darstellung)
    diag = Part.makeBox(TRI_DIAG_BX,TRI_DIAG_BY,TRI_DIAG_T)
    o_diag = mk_feat(base_name+"_Diag", diag,
                     base=(cx-TRI_DIAG_BX/2.0, cy-TRI_DIAG_BY/2.0, lv2_top_z+TRI_BASE_T),
                     rot=App.Rotation(App.Vector(0,1,0), -25), center=(cx,cy,lv2_top_z))
    out.append(o_diag)
    # Lagerblöcke
    lbL = mk_feat(base_name+"_PivotL", Part.makeBox(PIVOT_BLOCK_T,PIVOT_BLOCK_W,PIVOT_BLOCK_T),
                  base=(cx-PIVOT_BLOCK_T/2.0, pivot_y_left - PIVOT_BLOCK_W/2.0, pivot_z - PIVOT_BLOCK_T/2.0))
    lbR = mk_feat(base_name+"_PivotR", Part.makeBox(PIVOT_BLOCK_T,PIVOT_BLOCK_W,PIVOT_BLOCK_T),
                  base=(cx-PIVOT_BLOCK_T/2.0, pivot_y_right - PIVOT_BLOCK_W/2.0, pivot_z - PIVOT_BLOCK_T/2.0))
    out += [lbL, lbR]
    # kurze „Wellen“-Zylinder (optisch)
    cyl = Part.makeCylinder(PIVOT_SHAFT_D/2.0, PIVOT_BLOCK_W)
    shL = mk_feat(base_name+"_ShaftL", cyl, base=(cx, pivot_y_left - PIVOT_BLOCK_W/2.0, pivot_z),
                  rot=App.Rotation(App.Vector(0,1,0), 90), center=(cx, pivot_y_left, pivot_z))
    shR = mk_feat(base_name+"_ShaftR", cyl, base=(cx, pivot_y_right - PIVOT_BLOCK_W/2.0, pivot_z),
                  rot=App.Rotation(App.Vector(0,1,0), 90), center=(cx, pivot_y_right, pivot_z))
    out += [shL, shR]
    return out

def slb_place(obj, base_corner, pivot_point, pose):
    # base_corner: (x0,y0,z0) Unterkante-vorn-links (Objektursprung) in Transport
    # pivot_point: (px,py,pz) globale Trunnion-Achse (Zentrum)
    x0,y0,z0 = base_corner
    px,py,pz = pivot_point
    if pose == "transport":
        rot = App.Rotation()
    elif pose == "load":
        # 90° horizontal (um z), dann 0° vertikal
        rot = App.Rotation(App.Vector(0,0,1), 90)
    else:  # use
        rot = App.Rotation(App.Vector(0,0,1), 33).multiply(App.Rotation(App.Vector(0,1,0), 49))
    obj.Placement = App.Placement(App.Vector(x0,y0,z0), rot, App.Vector(px,py,pz))

def place_slb_pair(side, row_center_y, idx0):
    # Zwei SLB je Seite (vorn/hinten)
    x1 = SLB_FRONT_SETBACK + SLB_X/2.0
    x2 = x1 + SLB_X + SLB_COL_GAP_X
    for j, cx in enumerate((x1, x2), start=0):
        tag = f"{side}{idx0+j}"
        cy = row_center_y
        # H-Plate
        hp = make_hplate(f"HPlate_{tag}", cx, cy); hplates.append(hp)
        # Z-Positionen
        slb_base_z = lv2_top_z + HPL_THK + STANDOFF_S
        pivot_z    = slb_base_z + SLB_Z + PIVOT_OVER_TOP
        # X Pivot (vorversetzt, relativ SLB-Mitte)
        pivot_x    = cx + PIVOT_X_OFFSET
        # Y Pivot (Achse exakt in SLB-Mitte), Lagerblöcke knapp außerhalb
        pivot_y    = cy
        y_left  = cy - (SLB_Y/2.0 + PIVOT_BLOCK_W/2.0 + 10.0)
        y_right = cy + (SLB_Y/2.0 + PIVOT_BLOCK_W/2.0 + 10.0)
        # Träger/Lager
        triangles.extend(make_triangle_supports(f"Tri_{tag}", cx, cy, pivot_z, y_left, y_right))
        # SLB-Körper (Ursprung = Unterkante-vorn-links)
        slb = mk_feat(f"SLB_{tag}", Part.makeBox(SLB_X, SLB_Y, SLB_Z))
        base_corner = (cx - SLB_X/2.0, cy - SLB_Y/2.0, slb_base_z)
        slb_place(slb, base_corner, (pivot_x, pivot_y, pivot_z), ACTIVE_POSE)
        slbs.append(slb)

        if DEBUG:
            print(f"[{tag}] base_corner={base_corner}  pivot={(pivot_x,pivot_y,pivot_z)}  pose={ACTIVE_POSE}")

# Reihenmittellinien exakt innerhalb der LV2-Platte halten
lv2_min_y = EDGE_SETBACK
lv2_max_y = PLAT_Y - EDGE_SETBACK
row_center_L = lv2_min_y + SLB_ROW_CLEAR_Y + SLB_Y/2.0
row_center_R = lv2_max_y - SLB_ROW_CLEAR_Y - SLB_Y/2.0

place_slb_pair('L', row_center_L, 1)
place_slb_pair('R', row_center_R, 3)

# ---------------- Stützen (Dummy) ----------------
columns = []
def add_col(n, x, y):
    h = lv2_base_z
    columns.append(mk_feat(n, Part.makeBox(COL_W,COL_D,h), base=(x,y,0.0)))

add_col("Col_FR", PLAT_X-COL_W, 0)
add_col("Col_RL", 0, PLAT_Y-COL_D)
add_col("Col_RR", PLAT_X-COL_W, PLAT_Y-COL_D)
if ADD_MID_X:
    add_col("Col_Mx_L", (PLAT_X-COL_W)/2.0, 0)
    add_col("Col_Mx_R", (PLAT_X-COL_W)/2.0, PLAT_Y-COL_D)
if ADD_MID_Y:
    add_col("Col_My_F", 0, (PLAT_Y-COL_D)/2.0)
    add_col("Col_My_R", PLAT_X-COL_W, (PLAT_Y-COL_D)/2.0)

# ---------------- Gruppierung ----------------
grp_lvl1 = add("App::DocumentObjectGroup", "G_Ebene1"); grp_lvl1.addObjects([platform]+slots+drawers+[rail_L,rail_R])
grp_lvl2 = add("App::DocumentObjectGroup", "G_Ebene2"); grp_lvl2.addObjects([lv2_plate]+hplates+triangles+slbs+columns)
assembly = add("App::DocumentObjectGroup", "Assembly_Proxy"); assembly.addObjects([grp_lvl1, grp_lvl2])

App.ActiveDocument.recompute()

# ---------------- Export ----------------
fcstd = os.path.join(BUILD_DIR, "TARS_v0.8.FCStd")
App.ActiveDocument.saveAs(fcstd)

step = os.path.join(BUILD_DIR, f"TARS_v0.8_{ACTIVE_POSE}.step")
Part.export([platform]+slots+drawers+[rail_L,rail_R,lv2_plate]+hplates+triangles+slbs+columns, step)

print(f"Saved FCStd: {fcstd}")
print(f"Saved STEP:  {step}")
App.closeDocument(App.ActiveDocument.Name)

# 01_CAD/src/build_tars_fcstd.py
# FreeCAD 1.0 headless builder for TARS v0.2
import os, math, sys

try:
    import FreeCAD as App
    import Part
except Exception as e:
    print("FreeCAD modules not available in this environment:", e)
    sys.exit(1)

OUT_DIR = os.path.join("01_CAD", "build")
os.makedirs(OUT_DIR, exist_ok=True)
DOC_NAME = "TARS_v0_2"
FCSTD_PATH = os.path.join(OUT_DIR, "TARS_v0.2.FCStd")
STEP_PATH  = os.path.join(OUT_DIR, "TARS_v0.2.step")

doc = App.newDocument(DOC_NAME)

# Parameters (mm, kg, deg)
p = doc.addObject('Spreadsheet::Sheet','Params')
params = {
    # Platform
    'plat_x': 2967.0, 'plat_y': 2483.0, 'plat_t': 12.0,  # vorläufig: 12 mm Plattenäquivalent
    # Drawer box
    'dbx_x': 521.0, 'dbx_y': 717.0, 'dbx_z': 130.0, 'dbx_m_empty': 16.0, 'dbx_m_full': 70.0,
    # Swivel-launch box (x=970, y=960, z=923 Fahr-0° Lage)
    'slb_x': 970.0, 'slb_y': 960.0, 'slb_z': 923.0, 'slb_t': 6.0, 'slb_m_empty': 340.0, 'slb_m_full': 690.0,
    # Clearances
    'gap_side': 40.0, 'gap_front': 60.0, 'gap_rear': 60.0, 'gap_between_L1_L2': 50.0,
    # L2 posts / plate
    'post_shs': 100.0, 'post_t': 6.3, 'deck_to_L2': 550.0,
    # Locks
    'lock_h_0': 0.0, 'lock_h_33': 33.0, 'lock_h_90': 90.0, 'lock_v_0': 0.0, 'lock_v_49': 49.0,
}
for k,v in params.items():
    p.set(k, str(v))
p.recompute()

def mk_box(name, dx, dy, dz, pos=(0,0,0)):
    b = doc.addObject("Part::Box", name)
    b.Length = dx; b.Width = dy; b.Height = dz
    b.Placement.Base.x = pos[0]; b.Placement.Base.y = pos[1]; b.Placement.Base.z = pos[2]
    return b

# Coordinate system: x=0,y=0 front-left; z=0 = top of Level-1 deck
plat = mk_box("L1_Deck", float(p.get("plat_x")), float(p.get("plat_y")), float(p.get("plat_t")), (0,0,-float(p.get("plat_t"))))

# Level 1: drawer bay envelopes (5 Kästen je Seite, 2 Ebenen übereinander = 10/Seite)
dbx_x = float(p.get("dbx_x")); dbx_y = float(p.get("dbx_y")); dbx_z = float(p.get("dbx_z"))
gap_side = float(p.get("gap_side")); gap_front = float(p.get("gap_front")); gap_rear = float(p.get("gap_rear"))
plat_x = float(p.get("plat_x")); plat_y = float(p.get("plat_y"))
usable_x = plat_x - gap_front - gap_rear
pitch_x = usable_x / 5.0  # 5 Einschubkästen in Längsrichtung
left_origin  = (gap_front, gap_side, 0.0)
right_origin = (gap_front, plat_y - gap_side - dbx_y, 0.0)

drawer_envs = []
for i in range(5):
    x_i = gap_front + i*pitch_x + 0.5*(pitch_x - dbx_x)
    # Zwei übereinander: z=0 und z=dbx_z+10 (10 mm Zwischenraum)
    z0 = 0.0; z1 = dbx_z + 10.0
    # Links (öffnet nach außen = xz‑Ebene zur Seite)
    drawer_envs.append(mk_box(f"L1_Drawer_L_{i}_A", dbx_x, dbx_y, dbx_z, (x_i, gap_side, z0)))
    drawer_envs.append(mk_box(f"L1_Drawer_L_{i}_B", dbx_x, dbx_y, dbx_z, (x_i, gap_side, z1)))
    # Rechts
    drawer_envs.append(mk_box(f"L1_Drawer_R_{i}_A", dbx_x, dbx_y, dbx_z, (x_i, plat_y-gap_side-dbx_y, z0)))
    drawer_envs.append(mk_box(f"L1_Drawer_R_{i}_B", dbx_x, dbx_y, dbx_z, (x_i, plat_y-gap_side-dbx_y, z1)))

# Level 2: posts + top plate
post_shs = float(p.get("post_shs")); deck_to_L2 = float(p.get("deck_to_L2"))
post_h = deck_to_L2
post_positions = []
# 4 Stützen je Seite (insgesamt 8), verteilt entlang x; seitlich oberhalb der L1‑Kästen
for side in ["L","R"]:
    y = gap_side if side=="L" else (plat_y - gap_side - post_shs)
    for i in range(4):
        x = gap_front + (i+0.5)*(usable_x/4.0) - 0.5*post_shs
        post_positions.append((x, y, 0.0))

posts = []
for idx,(x,y,z) in enumerate(post_positions):
    posts.append(mk_box(f"L2_Post_{idx:02d}", post_shs, post_shs, post_h, (x,y,0.0)))

# L2 Deckplatte (H‑Trägerplatte kommt in v0.3, hier eine volle Platte als Platzhalter)
L2_plate = mk_box("L2_Plate", plat_x-2*gap_front, plat_y-2*gap_side, 10.0, (gap_front, gap_side, deck_to_L2))

# Swivel‑Launch‑Box envelopes (2 Stück – links und rechts, auf L2_Plate)
slb_x = float(p.get("slb_x")); slb_y = float(p.get("slb_y")); slb_z = float(p.get("slb_z"))
# Fahrstellung 0°/0°: offene Seite gegen Fahrtrichtung (xz‑Ebene)
# Wir setzen die Boxen mittig links/rechts auf L2_Plate mit etwas Rand
y_left = gap_side + 80.0
y_right = plat_y - gap_side - slb_y - 80.0
x_mid = gap_front + 0.5*(plat_x - 2*gap_front - slb_x)
z_L2 = deck_to_L2 + 10.0  # Oberkante L2_Plate

slb_L = mk_box("SLB_Left_0_0", slb_x, slb_y, slb_z, (x_mid, y_left, z_L2))
slb_R = mk_box("SLB_Right_0_0", slb_x, slb_y, slb_z, (x_mid, y_right, z_L2))

# Platzhalter für weitere Lock‑Posen (nur Dummy‑Körper, kinematik folgt in v0.3)
slb_L_90 = mk_box("SLB_Left_90_0", slb_y, slb_x, slb_z, (x_mid, y_left, z_L2))  # 90° horiz. gedreht (Flächen getauscht)
slb_R_90 = mk_box("SLB_Right_90_0", slb_y, slb_x, slb_z, (x_mid, y_right, z_L2))
# 33°/49° werden in v0.3 als kinematische Pose umgesetzt (hier nur Marker)
marker_33_49_L = mk_box("SLB_Left_33_49_marker", 50, 50, 50, (x_mid-60, y_left-60, z_L2+slb_z+60))
marker_33_49_R = mk_box("SLB_Right_33_49_marker", 50, 50, 50, (x_mid-60, y_right-60, z_L2+slb_z+60))

doc.recompute()
# Save FCStd and export STEP
doc.saveAs(FCSTD_PATH)
shape = doc.getObject("L1_Deck").Shape
# Für STEP: gesamte Dok‑Fusion (einfacher Export aller sichtbaren Körper)
import PART
all_shapes = [o.Shape for o in doc.Objects if hasattr(o, "Shape")]
compound = Part.makeCompound(all_shapes)
Part.export([compound], STEP_PATH)
print("Wrote:", FCSTD_PATH, "and", STEP_PATH)

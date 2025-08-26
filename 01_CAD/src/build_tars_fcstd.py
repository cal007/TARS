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

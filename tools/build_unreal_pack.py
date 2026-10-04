"""
Refresh the Unreal pack (/Game/LowPolyPlants) from this repo. Runs inside the Unreal Editor (5.8, Python plugin).

    1. python gen_plants.py <ue_obj_dir> --unreal     (OBJs with V flipped for Unreal's importer)
       python gen_plant_tex.py; python gen_cactus_tex.py; python gen_foliage_tex.py; python gen_stone_tex.py
    2. in the editor's Output Log (Python):
       py "<repo>/tools/build_unreal_pack.py" "<ue_obj_dir>" "<repo>/OBJ"

Needs the pack material /Game/LowPolyPlants/Materials/M_LowPolyPlant (copy Unreal/Content/LowPolyPlants in first).
Textures, material instances and meshes are replaced in place, so maps that use them keep their references; meshes
get 3 LODs (100 / 45 / 15 %), Nanite and no collision. New meshes are added to the showcase map.
"""
import sys

import unreal

ROOT = "/Game/LowPolyPlants"
MAT, MESHES = ROOT + "/Materials", ROOT + "/Meshes"
SHOWCASE = ROOT + "/Maps/LowPolyPlants_Showcase"
EAL = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

# slot: (linear colour, damage amount, damage colour, texture or None, pattern gain)
SLOTS = {
    "Agave": ((0.10, 0.16, 0.12), 0.85, (0.16, 0.12, 0.07), "T_PlantLeaf", 1.35),
    "AgaveDead": ((0.20, 0.13, 0.06), 0.0, (0.12, 0.07, 0.03), "T_PlantLeaf", 1.35),
    "Pad": ((0.10, 0.24, 0.05), 1.0, (0.62, 0.60, 0.46), "T_CactusPad", 1.19),       # G = areoles, cream
    "Fruit": ((0.30, 0.03, 0.05), 0.0, (0.12, 0.07, 0.03), None, 1.0),
    "Leaf": ((0.04, 0.10, 0.03), 0.9, (0.26, 0.22, 0.05), "T_Foliage", 1.71),
    "LeafDark": ((0.025, 0.07, 0.02), 0.9, (0.24, 0.20, 0.05), "T_Foliage", 1.71),
    "Flower": ((0.55, 0.12, 0.22), 0.0, (0.12, 0.07, 0.03), None, 1.0),
    "Stem": ((0.12, 0.09, 0.05), 0.0, (0.12, 0.07, 0.03), "T_PlantLeaf", 1.35),
    "Salt": ((0.11, 0.15, 0.08), 0.8, (0.30, 0.28, 0.18), "T_Foliage", 1.71),
    "Straw": ((0.20, 0.16, 0.06), 0.5, (0.34, 0.30, 0.18), "T_PlantLeaf", 1.35),
    "StrawPale": ((0.30, 0.25, 0.12), 0.4, (0.40, 0.36, 0.24), "T_PlantLeaf", 1.35),
    "Olive": ((0.11, 0.12, 0.04), 0.7, (0.24, 0.20, 0.09), "T_PlantLeaf", 1.35),
    "Seed": ((0.26, 0.21, 0.10), 0.0, (0.12, 0.07, 0.03), "T_PlantLeaf", 1.35),
    "DeadGrass": ((0.12, 0.07, 0.03), 0.0, (0.12, 0.07, 0.03), "T_PlantLeaf", 1.35),
    "Tussock": ((0.30, 0.24, 0.12), 0.5, (0.36, 0.32, 0.22), "T_PlantLeaf", 1.35),
    "TussockPale": ((0.42, 0.35, 0.20), 0.4, (0.46, 0.42, 0.30), "T_PlantLeaf", 1.35),
    "Stone": ((0.16, 0.13, 0.10), 0.0, (0.12, 0.07, 0.03), "T_Stone", 1.71),
    "StoneLight": ((0.24, 0.20, 0.15), 0.0, (0.12, 0.07, 0.03), "T_Stone", 1.71),
    "StoneDark": ((0.09, 0.075, 0.06), 0.0, (0.12, 0.07, 0.03), "T_Stone", 1.71),
    "Concrete": ((0.22, 0.21, 0.19), 0.0, (0.12, 0.07, 0.03), "T_Stone", 1.71),
    "Litter": ((0.50, 0.49, 0.46), 0.0, (0.12, 0.07, 0.03), None, 1.0),
    "LitterBlue": ((0.08, 0.18, 0.36), 0.0, (0.12, 0.07, 0.03), None, 1.0),
}
# mesh: showcase position (x, y, yaw)
MESH_LIST = {
    "SM_Plant_Agave": (0, -900, 0), "SM_Plant_PricklyPear": (0, -300, 53), "SM_Plant_Oleander": (0, 300, 106),
    "SM_Plant_Saltbush": (0, 900, 159), "SM_Grass_Tuft": (-350, -600, -148), "SM_Grass_Seed": (-350, 0, -95),
    "SM_Grass_Dead": (-350, 600, -42), "SM_Grass_Tussock": (-700, -900, 20), "SM_Rocks_Scatter": (-700, -300, 70),
    "SM_Rocks_Rubble": (-700, 300, 120), "SM_Rocks_Litter": (-700, 900, 170),
}


def save(p):
    EAL.save_asset(p, only_if_is_dirty=False)


def import_texture(path_png, name):
    t = unreal.AssetImportTask()
    t.filename = path_png
    t.destination_path = MAT
    t.destination_name = name
    t.automated = True
    t.replace_existing = True
    t.save = False
    tools.import_asset_tasks([t])
    tex = unreal.load_asset(MAT + "/" + name)
    tex.set_editor_property("srgb", True)
    tex.set_editor_property("address_x", unreal.TextureAddress.TA_WRAP)
    tex.set_editor_property("address_y", unreal.TextureAddress.TA_WRAP)
    save(MAT + "/" + name)
    return tex


def build(ue_obj_dir, tex_dir):
    master = unreal.load_asset(MAT + "/M_LowPolyPlant")
    if not master:
        raise RuntimeError("copy Unreal/Content/LowPolyPlants into the project first (M_LowPolyPlant missing)")
    texs = {n: import_texture(tex_dir + "/" + n + ".png", n) for n in ("T_PlantLeaf", "T_CactusPad", "T_Foliage", "T_Stone")}
    mats = {}
    for slot, (col, amt, dcol, tex, gain) in SLOTS.items():
        p = MAT + "/MI_Plant_" + slot
        x = unreal.load_asset(p) if EAL.does_asset_exist(p) else tools.create_asset(
            "MI_Plant_" + slot, MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        x.set_editor_property("parent", master)
        mel.set_material_instance_vector_parameter_value(x, "Color", unreal.LinearColor(*col, 1))
        mel.set_material_instance_vector_parameter_value(x, "DamageColor", unreal.LinearColor(*dcol, 1))
        mel.set_material_instance_scalar_parameter_value(x, "DamageAmount", amt)
        if tex:
            mel.set_material_instance_texture_parameter_value(x, "Pattern", texs[tex])
            mel.set_material_instance_scalar_parameter_value(x, "PatternGain", gain)
        mel.update_material_instance(x)
        save(p)
        mats[slot] = x
    sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for name in MESH_LIST:
        t = unreal.AssetImportTask()
        t.filename = ue_obj_dir + "/" + name + ".obj"
        t.destination_path = MESHES
        t.destination_name = name
        t.automated = True
        t.replace_existing = True
        t.save = False
        tools.import_asset_tasks([t])
        m = unreal.load_asset(MESHES + "/" + name)
        for i, s in enumerate(m.get_editor_property("static_materials")):
            if str(s.material_slot_name) in mats:
                m.set_material(i, mats[str(s.material_slot_name)])
        sme.remove_collisions(m)
        opts = unreal.StaticMeshReductionOptions()
        st = []
        for pct, screen in ((1.0, 1.0), (0.45, 0.2), (0.15, 0.05)):
            r = unreal.StaticMeshReductionSettings()
            r.percent_triangles = pct
            r.screen_size = screen
            st.append(r)
        opts.reduction_settings = st
        opts.auto_compute_lod_screen_size = False
        for _ in range(2):          # a freshly imported mesh sometimes needs a second pass
            sme.set_lods_with_notification(m, opts, True)
            if m.get_num_lods() == 3:
                break
        ns = m.get_editor_property("nanite_settings")
        ns.enabled = True
        m.set_editor_property("nanite_settings", ns)
        save(MESHES + "/" + name)
        print(name, "LODs", m.get_num_lods())
    # showcase: add what is missing
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.load_level(SHOWCASE)
    have = set(a.get_actor_label() for a in eas.get_all_level_actors())
    for name, (x, y, yaw) in MESH_LIST.items():
        if name in have:
            continue
        a = eas.spawn_actor_from_object(unreal.load_asset(MESHES + "/" + name), unreal.Vector(x, y, 0), unreal.Rotator(0, 0, yaw))
        a.set_actor_label(name)
        print("showcase +", name)
    les.save_current_level()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    build(args[0].replace("\\", "/"), args[1].replace("\\", "/"))

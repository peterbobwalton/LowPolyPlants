"""
LowPolyPlants date palm (Phoenix dactylifera) with V-section leaf-card fronds. Runs in Blender (4.x / 5.x):

    blender --background --python gen_datepalm_blender.py -- [out_dir]

Writes FBX/SM_Plant_DatePalm_{A,B,C}.fbx, OBJ/SM_Plant_DatePalm_{A,B,C}.obj (+ .mtl) and datepalm_preview.png.
Needs FBX/T_PalmFrond.png (python gen_datepalm_tex.py) for the preview and the OBJ material.

Z up, metres in Blender (centimetres after FBX import into Unreal), pivot on the ground. Two material slots:
  Trunk  slightly curved, dark rough bark in a diamond hatch (vertex colour; Kd for OBJ)
  Frond  leaf cards on T_PalmFrond: render MASKED (alpha) and TWO-SIDED. Each frond is a rib in 6 segments whose card
         halves rise 25 deg either side of it (a V of leaflets from any side). Upper fronds arch up and out, lower ones
         droop; random twist and length; an optional skirt of dry brown fronds under the crown.
No collision (add a trunk box in your engine).

VARIANTS: name, height (m), fronds, frond scale, droop scale, skirt, seed
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix

VARIANTS = [('SM_Plant_DatePalm_A', 9.0, 28, 1.0, 1.0, True, 1),     # mature, ~9 m
            ('SM_Plant_DatePalm_B', 6.5, 26, 0.9, 1.0, True, 2),     # ~6.5 m
            ('SM_Plant_DatePalm_C', 3.2, 16, 0.7, 0.9, False, 3)]    # young, ~3 m, no dry skirt

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'FBX', 'T_PalmFrond.png')


def material(name, col, tex=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*col, 1)
    m.use_nodes = True
    nt = m.node_tree
    b = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    b.inputs['Base Color'].default_value = (*col, 1)
    if tex and os.path.exists(tex):
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(tex, check_existing=True)
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
        nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
        for k, v in (('blend_method', 'CLIP'), ('surface_render_method', 'DITHERED')):
            try:
                setattr(m, k, v)
            except Exception:
                pass
    elif name == 'Trunk':
        a = nt.nodes.new('ShaderNodeVertexColor'); a.layer_name = 'Col'
        nt.links.new(a.outputs['Color'], b.inputs['Base Color'])
    m.use_backface_culling = False
    return m


def palm(name, Ht, nfr, scale, droop_k, skirt, seed):
    rnd = random.Random(seed)
    bm = bmesh.new()
    col = bm.loops.layers.color.new('Col')
    uvl = bm.loops.layers.uv.new('UVMap')
    lean = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * Ht * 0.05
    # trunk: 7 sides, a slight curve, rough dark bark in a diamond hatch (alternating rings)
    n = 7
    segs = max(6, int(Ht / 0.5))
    rings = []
    for s in range(segs + 1):
        t = s / segs
        z = Ht * t
        r = 0.24 - 0.08 * t
        off = lean * (t * t)
        tw = (s % 2) * math.pi / n
        rings.append([bm.verts.new((off.x + r * math.cos(2 * math.pi * k / n + tw), off.y + r * math.sin(2 * math.pi * k / n + tw), z)) for k in range(n)])
    for s in range(segs):
        for k in range(n):
            f = bm.faces.new((rings[s][k], rings[s][(k + 1) % n], rings[s + 1][(k + 1) % n], rings[s + 1][k]))
            f.material_index = 0
            c = (0.30, 0.25, 0.19) if (s + k) % 2 else (0.22, 0.18, 0.14)
            for l in f.loops:
                l[col] = (*c, 1)
                l[uvl].uv = (0.0, 0.0)
    top = Vector((lean.x, lean.y, Ht))

    def frond(az, el, L, row, droop, twist):
        d = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
        pts = [top + d * L * (j / 6) - Vector((0, 0, droop * L * (j / 6) ** 2)) for j in range(7)]
        hw = L / 5.5
        V = math.radians(25)
        vc = 1.0 - (row + 0.5) / 4.0          # atlas row centre (4 rows, rib in the middle of each)
        prev = None
        for j in range(7):
            tng = (pts[min(j + 1, 6)] - pts[max(j - 1, 0)]).normalized()
            side = tng.cross(Vector((0, 0, 1)))
            side = side.normalized() if side.length > 1e-4 else Vector((1, 0, 0))
            side = Matrix.Rotation(twist, 3, tng) @ side
            up = side.cross(tng).normalized()
            w = hw * (0.55 + 0.45 * math.sin(math.pi * min(1.0, 0.15 + j / 6 * 0.95)))      # narrow at base and tip
            cur = (bm.verts.new(pts[j] + (side * math.cos(V) + up * math.sin(V)) * w), bm.verts.new(pts[j]),
                   bm.verts.new(pts[j] + (-side * math.cos(V) + up * math.sin(V)) * w), 0.02 + 0.96 * j / 6)
            if prev:
                u0, u1 = prev[3], cur[3]
                for vs, uvs in (((prev[0], cur[0], cur[1], prev[1]), ((u0, vc + 0.125), (u1, vc + 0.125), (u1, vc), (u0, vc))),
                                ((prev[1], cur[1], cur[2], prev[2]), ((u0, vc), (u1, vc), (u1, vc - 0.125), (u0, vc - 0.125)))):
                    f = bm.faces.new(vs)
                    f.material_index = 1
                    for l, uv in zip(f.loops, uvs):
                        l[uvl].uv = uv
                        l[col] = (1, 1, 1, 1)
            prev = cur

    for k in range(nfr):
        t = k / max(nfr - 1, 1)
        el = math.radians(70 - 125 * t + rnd.uniform(-8, 8))           # 70 deg up ... 55 deg down
        L = scale * rnd.uniform(3.2, 4.2) * (1.0 if t < 0.8 else 0.85)
        droop = (0.15 + 0.55 * t + rnd.uniform(-0.05, 0.05)) * droop_k
        frond(rnd.uniform(0, 2 * math.pi), el, L, rnd.choice([0, 0, 1, 1, 2]), droop, math.radians(rnd.uniform(-18, 18)))
    if skirt:
        for k in range(9):
            frond(2 * math.pi * k / 9 + rnd.uniform(-0.2, 0.2), math.radians(rnd.uniform(-78, -62)), scale * rnd.uniform(1.6, 2.1), 3, 0.05, 0.0)
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material('Trunk', (0.26, 0.21, 0.16)))
    me.materials.append(material('Frond', (0.33, 0.40, 0.26), TEX))
    me.color_attributes.active_color = me.color_attributes['Col']
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main(out_dir):
    for o in list(bpy.data.objects):                     # the factory scene's cube, camera and light
        if o.name in ('Cube', 'Camera', 'Light'):
            bpy.data.objects.remove(o)
    for d in ('FBX', 'OBJ'):
        os.makedirs(os.path.join(out_dir, d), exist_ok=True)
    obs = []
    for v in VARIANTS:
        ob = palm(*v)
        obs.append(ob)
        for o in bpy.context.scene.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.fbx(filepath=os.path.join(out_dir, 'FBX', ob.name + '.fbx'), use_selection=True, object_types={'MESH'},
                                 apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
                                 add_leaf_bones=False, bake_anim=False, colors_type='SRGB', use_triangles=True)
        bpy.ops.wm.obj_export(filepath=os.path.join(out_dir, 'OBJ', ob.name + '.obj'), export_selected_objects=True,
                              export_materials=True, path_mode='STRIP', export_triangulated_mesh=True,
                              forward_axis='Y', up_axis='Z', global_scale=100.0)
        print(ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons), 'tris')
    # preview: the three side by side
    for i, ob in enumerate(obs):
        ob.location.x = i * 9.0
    sc = bpy.context.scene
    cam = bpy.data.objects.get('PreviewCam') or bpy.data.objects.new('PreviewCam', bpy.data.cameras.new('PreviewCam'))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.location = (9.0, -40.0, 6.5)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    sun = bpy.data.objects.get('PreviewSun') or bpy.data.objects.new('PreviewSun', bpy.data.lights.new('PreviewSun', 'SUN'))
    if sun.name not in sc.collection.objects:
        sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    if sc.world is None:
        sc.world = bpy.data.worlds.new('World')
    sc.world.color = (0.42, 0.40, 0.36)
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 1400, 800
    sc.render.filepath = os.path.join(out_dir, 'datepalm_preview.png')
    bpy.ops.render.render(write_still=True)
    for ob in obs:
        ob.location.x = 0.0


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    main(argv[0] if argv else HERE)

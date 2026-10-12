# War Zone: Last Stand - a 60 second war film
# 1440 frames at 24fps, 854x480, Blender Cycles CPU.
# Farm-ready: reads FRAME_START / FRAME_END / ANIM_START / ANIM_END / OUTPUT_DIR
# from the environment, writes frame_####.png, bakes all animation 1..1440.
#
# Six shots with hard cuts (timeline markers bound to per-shot cameras):
#   S1  f1-240    (0-10s)   Dawn calm: the outpost, soldiers on watch, helicopter over
#   S2  f241-480  (10-20s)  Armor approaches: three tanks emerge from the dust
#   S3  f481-720  (20-30s)  The assault: tanks open fire, shells hammer the line
#   S4  f721-960  (30-40s)  Counterattack: jet flyby, helicopter strafes, truck races in
#   S5  f961-1200 (40-50s)  Close combat: rifles and cannon at point blank
#   S6  f1201-1440(50-60s)  Aftermath: slow pull-back over the burning field
#
# Real free assets (Poly Pizza):
#   Tank (Quaternius, CC0) ................. https://poly.pizza/m/uYHpj7lz1J
#   Cube Crate (Quaternius, CC0) ........... https://poly.pizza/m/YAghI6GBls
#   Sandbags (J-Toastie, CC-BY) ............ https://poly.pizza/m/xClPIEQJdX
#   Concrete Barrier (J-Toastie, CC-BY) .... https://poly.pizza/m/5Cg2oW7EFn
#   Soldier (KolosStudios, CC-BY) .......... https://poly.pizza/m/XT8jgwSesV
#   Helicopter (jeremy, CC-BY) ............. https://poly.pizza/m/eb7b31pjGtQ
#   M939 Truck (J-Toastie, CC-BY) .......... https://poly.pizza/m/y8lBpvMlim
#   Jet (jeremy, CC-BY) .................... https://poly.pizza/m/6fyLMORhgGK
# Environment (ground, sky, smoke, fire, dust, debris) is procedural.

import bpy
import math
import os
import random
from mathutils import Vector

random.seed(60)

# ---------------------------------------------------------------- env / frames
FRAME_START = int(os.environ.get("FRAME_START", "1"))
FRAME_END = int(os.environ.get("FRAME_END", "1440"))
ANIM_START = int(os.environ.get("ANIM_START", "1"))
ANIM_END = int(os.environ.get("ANIM_END", "1440"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "")

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

FPS = 24
F_END = 1440  # 60 seconds

# ---------------------------------------------------------------- helpers

def kf(obj, frame, data_path="location"):
    obj.keyframe_insert(data_path=data_path, frame=frame)


def new_material(name, base_color=(0.8, 0.8, 0.8), roughness=0.9, metallic=0.0,
                 emission_color=None, emission_strength=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission_color is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission_color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        mat.blend_method = "BLEND"
        bsdf.inputs["Alpha"].default_value = alpha
    return mat


def import_glb(name):
    path = os.path.join(ASSETS, name)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    added = [o for o in bpy.context.scene.objects if o not in before]
    root = bpy.data.objects.new(name + "_root", None)
    bpy.context.scene.collection.objects.link(root)
    for o in added:
        if o.parent is None:
            o.parent = root
    return root, added


def discard_import(root, parts):
    for o in parts:
        try:
            bpy.data.objects.remove(o, do_unlink=True)
        except ReferenceError:
            pass
    try:
        bpy.data.objects.remove(root, do_unlink=True)
    except ReferenceError:
        pass


def mesh_world_center(obj):
    mw = obj.matrix_world
    vs = [mw @ Vector(c) for c in obj.bound_box]
    return sum(vs, Vector()) / 8.0


def add_cycles_modifier(action):
    for fc in action.fcurves:
        if not any(m.type == "CYCLES" for m in fc.modifiers):
            fc.modifiers.new(type="CYCLES")


def aim_cam(cam_obj, target):
    d = Vector(target) - cam_obj.location
    cam_obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------- scene setup
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 32
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.render.resolution_x = 854
sc.render.resolution_y = 480
sc.render.resolution_percentage = int(os.environ.get("WZ_RES_PCT", "100"))
sc.render.film_transparent = False
sc.render.image_settings.file_format = "PNG"
sc.render.fps = FPS
sc.frame_start = FRAME_START
sc.frame_end = FRAME_END

# ---------------------------------------------------------------- world: grim war sky (vertical gradient)
if bpy.context.scene.world is None:
    bpy.context.scene.world = bpy.data.worlds.new("WarWorld60")
world = bpy.context.scene.world
world.use_nodes = True
wnodes = world.node_tree.nodes
wnodes.clear()
wout = wnodes.new(type="ShaderNodeOutputWorld")
wbg = wnodes.new(type="ShaderNodeBackground")
wgeo = wnodes.new(type="ShaderNodeNewGeometry")
wsep = wnodes.new(type="ShaderNodeSeparateXYZ")
wmap = wnodes.new(type="ShaderNodeMapRange")
wmap.inputs["From Min"].default_value = -10.0
wmap.inputs["From Max"].default_value = 70.0
wramp = wnodes.new(type="ShaderNodeValToRGB")
el = wramp.color_ramp.elements
el[0].position = 0.0
el[0].color = (0.36, 0.23, 0.14, 1.0)
el[1].position = 0.30
el[1].color = (0.31, 0.26, 0.24, 1.0)
mid_el = wramp.color_ramp.elements.new(0.62)
mid_el.color = (0.17, 0.17, 0.20, 1.0)
el[1].position = 1.0
el[1].color = (0.09, 0.10, 0.13, 1.0)
world.node_tree.links.new(wgeo.outputs["Position"], wsep.inputs["Vector"])
world.node_tree.links.new(wsep.outputs["Z"], wmap.inputs["Value"])
world.node_tree.links.new(wmap.outputs["Result"], wramp.inputs["Fac"])
world.node_tree.links.new(wramp.outputs["Color"], wbg.inputs["Color"])
world.node_tree.links.new(wbg.outputs["Background"], wout.inputs["Surface"])
wbg.inputs["Strength"].default_value = 1.0

# ---------------------------------------------------------------- lights
sun_data = bpy.data.lights.new("WarSun", type="SUN")
sun_data.energy = 3.0
sun_data.color = (1.0, 0.55, 0.3)
sun = bpy.data.objects.new("WarSun", sun_data)
sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(72), 0, math.radians(35))

fill_data = bpy.data.lights.new("CoolFill", type="SUN")
fill_data.energy = 0.5
fill_data.color = (0.45, 0.55, 0.75)
fill = bpy.data.objects.new("CoolFill", fill_data)
sc.collection.objects.link(fill)
fill.rotation_euler = (math.radians(50), 0, math.radians(215))

# ---------------------------------------------------------------- ground
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
gmat = bpy.data.materials.new("DesertGround60")
gmat.use_nodes = True
gn = gmat.node_tree.nodes
gbsdf = gn["Principled BSDF"]
gtex = gn.new(type="ShaderNodeTexNoise")
gtex.inputs["Scale"].default_value = 6.0
gtex.inputs["Detail"].default_value = 4.0
gcol = gn.new(type="ShaderNodeValToRGB")
gcol.color_ramp.elements[0].position = 0.35
gcol.color_ramp.elements[0].color = (0.30, 0.235, 0.155, 1.0)
gcol.color_ramp.elements[1].position = 0.75
gcol.color_ramp.elements[1].color = (0.45, 0.36, 0.245, 1.0)
gmat.node_tree.links.new(gtex.outputs["Fac"], gcol.inputs["Fac"])
gmat.node_tree.links.new(gcol.outputs["Color"], gbsdf.inputs["Base Color"])
gbsdf.inputs["Roughness"].default_value = 1.0
ground.data.materials.append(gmat)

rock_mat = new_material("Rock60", base_color=(0.35, 0.30, 0.25), roughness=1.0)
for i in range(60):
    x = random.uniform(-140, 140)
    y = random.uniform(-120, 120)
    if abs(x) < 30 and abs(y) < 25:
        continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,
                                          radius=random.uniform(0.25, 1.4),
                                          location=(x, y, 0.1))
    r = bpy.context.active_object
    r.name = f"Rock_{i}"
    r.scale.z = random.uniform(0.4, 0.7)
    r.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3))
    r.data.materials.append(rock_mat)

# ---------------------------------------------------------------- builders

def build_tank(name, tint=(1.0, 1.0, 1.0)):
    """Import the Quaternius tank, rig it for driving. Model forward is -X."""
    root, parts = import_glb("tank.glb")
    root.name = name
    armature = next(o for o in parts if o.type == "ARMATURE")
    turret = next(o for o in parts if o.name.startswith("Tank_Turret"))
    gun = next(o for o in parts if o.name.startswith("Tank_Gun"))
    body_mesh = next(o for o in parts if o.name.startswith("Tank_body"))
    fwd = bpy.data.actions.get("TankArmature|Tank_Forward_TankArmature")
    if fwd is not None:
        armature.animation_data_create()
        armature.animation_data.action = fwd
        add_cycles_modifier(fwd)
    # gun follows turret
    bpy.context.view_layer.update()
    gun_mat = gun.matrix_world.copy()
    gun.parent = turret
    gun.matrix_world = gun_mat
    # muzzle empty at gun tip
    bc = mesh_world_center(body_mesh)
    corners = [gun.matrix_world @ Vector(c) for c in gun.bound_box]
    muzzle_world = max(corners, key=lambda v: (v - bc).length)
    muzzle = bpy.data.objects.new(name + "_Muzzle", None)
    sc.collection.objects.link(muzzle)
    muzzle.parent = gun
    bpy.context.view_layer.update()
    muzzle.location = gun.matrix_world.inverted() @ muzzle_world
    # slight paint variation between tanks
    if tint != (1.0, 1.0, 1.0):
        for o in parts:
            if o.type == "MESH" and o.data.materials:
                for slot in o.material_slots:
                    m = slot.material
                    if m and m.use_nodes:
                        bsdf = m.node_tree.nodes.get("Principled BSDF")
                        if bsdf:
                            c = bsdf.inputs["Base Color"].default_value
                            bsdf.inputs["Base Color"].default_value = (
                                min(1.0, c[0] * tint[0]), min(1.0, c[1] * tint[1]),
                                min(1.0, c[2] * tint[2]), 1.0)
    return {"root": root, "turret": turret, "gun": gun, "muzzle": muzzle,
            "armature": armature}


def drive_tank(t, keys):
    """keys: list of (frame, x, y). Tank faces +X world (rig rotated pi)."""
    r = t["root"]
    r.rotation_euler = (0, 0, math.pi)
    for f, x, y in keys:
        r.location = (x, y, 0)
        r.keyframe_insert(data_path="location", frame=f)


def build_soldier(name, x, y, rot_z=0.0, height=1.9):
    root, parts = import_glb("soldier.glb")
    root.name = name
    arm = next(o for o in parts if o.type == "ARMATURE")
    bpy.context.view_layer.update()
    ws = [arm.matrix_world @ Vector(c) for c in arm.bound_box]
    h = max(v.z for v in ws) - min(v.z for v in ws)
    s = height / h
    root.scale = (s, s, s)
    root.location = (x, y, 0)
    root.rotation_euler = (0, 0, rot_z)
    stand = bpy.data.actions.get("Armature|Standing_Armature")
    if stand is not None:
        arm.animation_data_create()
        arm.animation_data.action = stand
    return root


def build_helicopter(name, scale_len=9.0):
    root, parts = import_glb("helicopter.glb")
    root.name = name
    mesh = next(o for o in parts if o.type == "MESH")
    bpy.context.view_layer.update()
    ws = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
    length = max(v.x for v in ws) - min(v.x for v in ws)
    hs = scale_len / length
    root.scale = (hs, hs, hs)
    return root


def build_truck(name):
    # M939: front (cab) faces -X in model space
    root, parts = import_glb("m939_truck.glb")
    root.name = name
    return root


def build_jet(name, scale_len=11.0):
    root, parts = import_glb("jet.glb")
    root.name = name
    mesh = next(o for o in parts if o.type == "MESH")
    bpy.context.view_layer.update()
    ws = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
    lx = max(v.x for v in ws) - min(v.x for v in ws)
    ly = max(v.y for v in ws) - min(v.y for v in ws)
    # nose along the longer horizontal axis
    s = scale_len / max(lx, ly)
    root.scale = (s, s, s)
    return root, ("X" if lx >= ly else "Y")


# ---------------------------------------------------------------- reusable battle effects

def explosion(pos, frame, size=1.0, seed=1):
    """Fireball + light spike + rising smoke + debris at Vector pos on frame."""
    px, py, pz = pos
    boom_mat = new_material(f"Fireball_{frame}_{seed}", base_color=(1, 0.42, 0.08),
                            emission_color=(1.0, 0.38, 0.06), emission_strength=3.5)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=(px, py, pz))
    boom = bpy.context.active_object
    boom.name = f"Fireball_{frame}_{seed}"
    boom.data.materials.append(boom_mat)
    for f, s in ((frame - 1, 0.001), (frame + 2, 1.9 * size),
                 (frame + 8, 1.5 * size), (frame + 18, 0.001)):
        boom.scale = (s, s * 1.25, s)
        boom.keyframe_insert(data_path="scale", frame=f)
    ld = bpy.data.lights.new(f"BoomLight_{frame}_{seed}", type="POINT")
    ld.color = (1.0, 0.5, 0.18)
    lo = bpy.data.objects.new(f"BoomLight_{frame}_{seed}", ld)
    sc.collection.objects.link(lo)
    lo.location = (px, py, pz + 1.5 * size)
    for f, e in ((frame - 1, 0), (frame + 2, 1500 * size),
                 (frame + 10, 600 * size), (frame + 20, 0)):
        ld.energy = e
        ld.keyframe_insert(data_path="energy", frame=f)
    # debris chunks
    debris_mat = new_material(f"Debris_{frame}_{seed}", base_color=(0.25, 0.22, 0.2), roughness=1.0)
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, -60))
    dobj = bpy.context.active_object
    dobj.name = f"DebrisChunk_{frame}_{seed}"
    dobj.data.materials.append(debris_mat)
    dobj.hide_viewport = True
    dobj.visible_camera = False
    dobj.visible_shadow = False
    bpy.ops.mesh.primitive_plane_add(size=2, location=(px, py, pz))
    demit = bpy.context.active_object
    demit.name = f"DebrisEmitter_{frame}_{seed}"
    demit.hide_viewport = True
    demit.visible_camera = False
    demit.visible_shadow = False
    dsys = demit.modifiers.new("Debris", type="PARTICLE_SYSTEM").particle_system
    dp = dsys.settings
    dp.count = 70
    dp.frame_start = frame
    dp.frame_end = frame + 4
    dp.lifetime = 55
    dp.emit_from = "FACE"
    dp.physics_type = "NEWTON"
    dp.normal_factor = 9.0
    dp.factor_random = 1.5
    dp.particle_size = 0.9 * size
    dp.size_random = 0.7
    dp.render_type = "OBJECT"
    dp.instance_object = dobj
    dsys.seed = seed
    # smoke billows
    puff_mat = new_material(f"BoomSmoke_{frame}_{seed}", base_color=(0.38, 0.36, 0.34),
                            roughness=1.0, alpha=0.5)
    rnd = random.Random(seed * 977 + frame)
    for i in range(6):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=2, radius=1.0,
            location=(px + rnd.uniform(-1.2, 1.2) * size,
                      py + rnd.uniform(-1.2, 1.2) * size, pz))
        p = bpy.context.active_object
        p.name = f"BoomPuff_{frame}_{seed}_{i}"
        p.data.materials.append(puff_mat)
        rise = rnd.uniform(6, 10) * size
        for f, s, z in ((frame, 0.3, pz), (frame + 12, 1.6 * size, pz + rise * 0.5),
                        (frame + 58, 2.4 * size, pz + rise)):
            p.scale = (s, s, s)
            p.location.z = z
            p.keyframe_insert(data_path="scale", frame=f)
            p.keyframe_insert(data_path="location", frame=f)
    return boom


def muzzle_flash_at(world_pos, frame, size=1.0, seed=2):
    """4-frame muzzle flash + light spike at a world position."""
    flash_mat = new_material(f"MuzzleFlash_{frame}_{seed}", base_color=(1, 0.7, 0.25),
                             emission_color=(1.0, 0.62, 0.18), emission_strength=14.0)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=world_pos)
    flash = bpy.context.active_object
    flash.name = f"MuzzleFlash_{frame}_{seed}"
    flash.data.materials.append(flash_mat)
    ld = bpy.data.lights.new(f"FlashLight_{frame}_{seed}", type="POINT")
    ld.color = (1.0, 0.6, 0.25)
    lo = bpy.data.objects.new(f"FlashLight_{frame}_{seed}", ld)
    sc.collection.objects.link(lo)
    for f, s, e in ((frame - 1, 0.001, 0), (frame, 1.6 * size, 4000),
                    (frame + 2, 1.1 * size, 1500), (frame + 4, 0.001, 0)):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        flash.location = Vector(world_pos)
        flash.scale = (s, s, s)
        flash.keyframe_insert(data_path="location", frame=f)
        flash.keyframe_insert(data_path="scale", frame=f)
        lo.location = Vector(world_pos)
        ld.energy = e
        lo.keyframe_insert(data_path="location", frame=f)
        ld.keyframe_insert(data_path="energy", frame=f)
    sc.frame_set(1)


def tank_fire(tank, fire_frame, target, seed=3):
    """Tank fires: flash at muzzle tip (tracked per-frame) + tracer + explosion."""
    sc.frame_set(fire_frame)
    bpy.context.view_layer.update()
    mp = (tank["muzzle"].matrix_world @ Vector((0, 0, 0))).copy()
    sc.frame_set(1)
    muzzle_flash_at(mp, fire_frame, size=1.0, seed=seed)
    # tracer streak for the shell flight
    tracer_mat = new_material(f"Tracer_{fire_frame}_{seed}", base_color=(1, 0.55, 0.15),
                              emission_color=(1.0, 0.5, 0.12), emission_strength=4.0)
    tgt = Vector(target)
    mid = (mp + tgt) / 2
    length = (tgt - mp).length
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=length, location=mid)
    tracer = bpy.context.active_object
    tracer.name = f"Tracer_{fire_frame}_{seed}"
    tracer.data.materials.append(tracer_mat)
    d = (tgt - mp).normalized()
    tracer.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    for f, vis in ((1, False), (fire_frame - 1, True), (fire_frame + 4, True),
                   (fire_frame + 5, False)):
        tracer.hide_render = not vis
        tracer.keyframe_insert(data_path="hide_render", frame=f)
    explosion(tgt, fire_frame + 8, size=1.0, seed=seed)
    return tgt

# ---------------------------------------------------------------- THE OUTPOST (defenders, around x=10)
sb_root, sb_parts = import_glb("sandbags.glb")
sb_mesh = next(o for o in sb_parts if o.type == "MESH")
for i, (x, y, ryaw) in enumerate([
        (9, -5.5, 0), (9, -3.5, 0), (9, -1.5, 0), (9, 0.5, 0),
        (9, 2.5, 0), (9, 4.5, 0), (7.2, 5.8, 1.2), (10.8, 5.8, -1.2),
        (11, -6.5, 0.5), (5.5, -6.8, 1.4)]):
    dup = sb_mesh.copy()
    dup.data = sb_mesh.data.copy()
    sc.collection.objects.link(dup)
    dup.name = f"SandbagWall_{i}"
    dup.location = (x, y, 0)
    dup.rotation_euler = (0, 0, ryaw)
discard_import(sb_root, sb_parts)

cb_root, cb_parts = import_glb("concrete_barrier.glb")
cb_mesh = next(o for o in cb_parts if o.type == "MESH")
for i, (x, y, ryaw) in enumerate([(13.5, -3.0, 0.15), (13.5, 6.0, -0.2),
                                  (5.0, -7.5, 0.5), (16.0, 1.0, 0.1),
                                  (-2, 9.0, 0.7), (20, -6, -0.4)]):
    dup = cb_mesh.copy()
    dup.data = cb_mesh.data.copy()
    sc.collection.objects.link(dup)
    dup.name = f"Barrier_{i}"
    dup.location = (x, y, 0)
    dup.rotation_euler = (0, 0, ryaw)
discard_import(cb_root, cb_parts)

cc_root, cc_parts = import_glb("cube_crate.glb")
cc_mesh = next(o for o in cc_parts if o.type == "MESH")
for i, (x, y, z, s) in enumerate([(11.5, -4.2, 0, 0.9), (11.5, -4.2, 1.85, 0.9),
                                  (12.8, -4.5, 0, 0.7), (11.8, 5.2, 0, 1.0),
                                  (7.0, 7.5, 0, 0.8)]):
    dup = cc_mesh.copy()
    dup.data = cc_mesh.data.copy()
    sc.collection.objects.link(dup)
    dup.name = f"Crate_{i}"
    dup.location = (x, y, z)
    dup.scale = (s, s, s)
discard_import(cc_root, cc_parts)

# defending soldiers
soldiers = []
for i, (x, y, rz) in enumerate([(10.6, -2.2, 0), (10.6, 3.2, 0),
                                (7.5, 6.0, 0.5), (12.5, -5.5, -0.4)]):
    s = build_soldier(f"Defender_{i}", x, y, rot_z=rz)
    soldiers.append(s)
    # idle sway the whole film
    for f, sx in ((1, 0.0), (360, 0.03), (720, -0.02), (1080, 0.03), (1440, 0.0)):
        s.rotation_euler = (sx, 0, rz)
        s.keyframe_insert(data_path="rotation_euler", frame=f)

# ---------------------------------------------------------------- THE ARMOR (3 tanks)
tank1 = build_tank("Tank_Lead", tint=(1.0, 0.95, 0.9))
tank2 = build_tank("Tank_Two", tint=(0.85, 0.9, 0.8))
tank3 = build_tank("Tank_Three", tint=(1.0, 0.9, 0.85))

# tank1: the hero, drives the whole film (halts clear of defenses, wreck, and tank2)
drive_tank(tank1, [(1, -75, 8), (240, -70, 8), (480, -45, 6),
                   (720, -28, 4.5), (960, -20, 4), (1200, -16, 1), (1440, -14, 0)])
# tank2: flank (halts clear of tank1)
drive_tank(tank2, [(1, -80, -12), (240, -75, -12), (480, -52, -10),
                   (720, -34, -8), (960, -26, -7), (1200, -22, -10), (1440, -20, -12)])
# tank3: destroyed mid-film, becomes a burning wreck around f850
drive_tank(tank3, [(1, -78, 22), (240, -73, 22), (480, -50, 18),
                   (720, -32, 14), (850, -24, 12), (1440, -24, 12)])
# wreck tilt + burn
r3 = tank3["root"]
for f, rx, rz in ((850, 0.0, 0.0), (880, 0.10, 0.06), (920, 0.16, 0.10), (1440, 0.16, 0.10)):
    r3.rotation_euler = (rx, 0, math.pi + rz)
    r3.keyframe_insert(data_path="rotation_euler", frame=f)

# turret tracking (slow sweeps, per tank)
for t, seed in ((tank1, 0), (tank2, 1), (tank3, 2)):
    for f, yaw in ((1, 0.0), (300, -0.12 + seed * 0.04), (600, 0.10),
                   (900, -0.08), (1200, 0.06), (1440, 0.0)):
        if t is tank3 and f > 850:
            break
        t["turret"].rotation_euler = (0, 0, yaw)
        t["turret"].keyframe_insert(data_path="rotation_euler", frame=f)

# dust behind the lead tank and tank2
dust_mat = new_material("Dust60", base_color=(0.48, 0.40, 0.30), roughness=1.0, alpha=0.4)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.8)
dust_puff = bpy.context.active_object
dust_puff.name = "DustPuff60"
dust_puff.data.materials.append(dust_mat)
dust_puff.hide_viewport = True
dust_puff.visible_camera = False
dust_puff.visible_shadow = False
for t, name, seed in ((tank1, "Dust1", 7), (tank2, "Dust2", 13)):
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0.3))
    de = bpy.context.active_object
    de.name = name
    de.hide_viewport = True
    de.visible_camera = False
    de.visible_shadow = False
    de.parent = t["root"]
    de.location = (3.0, 0, 0.4)
    psys = de.modifiers.new("Dust", type="PARTICLE_SYSTEM").particle_system
    ps = psys.settings
    ps.count = 200
    ps.frame_start = 1
    ps.frame_end = 1440
    ps.lifetime = 50
    ps.emit_from = "FACE"
    ps.distribution = "RAND"
    ps.physics_type = "NEWTON"
    ps.normal_factor = 1.4
    ps.factor_random = 0.7
    ps.tangent_factor = 0.9
    ps.particle_size = 1.8
    ps.size_random = 0.8
    ps.render_type = "OBJECT"
    ps.instance_object = dust_puff
    psys.seed = seed

# ---------------------------------------------------------------- air + reinforcements
heli = build_helicopter("Heli_Strafe")
# S1: distant crossing (f80-200); S4: strafing run (f800-920)
for f, pos in ((1, (-90, -70, 40)), (80, (-60, -62, 38)), (200, (60, -48, 36)),
               (201, (-95, 30, 26)), (800, (-70, 18, 22)), (860, (0, 8, 18)),
               (920, (70, -2, 22)), (921, (-90, -70, 40)), (1440, (-40, -62, 38))):
    heli.location = pos
    heli.keyframe_insert(data_path="location", frame=f)
heli.rotation_euler = (0, 0.05, math.pi / 2)
kf(heli, 1, "rotation_euler")

jet, jet_axis = build_jet("Jet_Flyby")
# low screaming pass across the battlefield (f740-830), then a far second pass
for f, pos in ((1, (0, -200, 60)), (740, (-140, -60, 26)), (785, (0, 0, 22)),
               (830, (140, 60, 26)), (831, (0, -200, 60)), (1440, (0, -200, 60))):
    jet.location = pos
    jet.keyframe_insert(data_path="location", frame=f)
# nose along travel (+X-ish); jet mesh nose axis picked at build
jet.rotation_euler = (0, 0, math.pi / 2 if jet_axis == "X" else 0)
kf(jet, 1, "rotation_euler")

truck = build_truck("Truck_Relief")
# races in from the east with reinforcements (f780-1100), skids to the line
truck.rotation_euler = (0, 0, math.pi)  # model front is -X; face -X world (driving west)
kf(truck, 1, "rotation_euler")
for f, (x, y) in ((1, (120, -30)), (780, (90, -25)), (900, (45, -14)),
                   (1000, (22, -8)), (1100, (18, -7)), (1440, (18, -7))):
    truck.location = (x, y, 0)
    truck.keyframe_insert(data_path="location", frame=f)
# truck dust
bpy.ops.mesh.primitive_plane_add(size=7, location=(0, 0, 0.3))
tde = bpy.context.active_object
tde.name = "TruckDust"
tde.hide_viewport = True
tde.visible_camera = False
tde.visible_shadow = False
tde.parent = truck
tde.location = (4.5, 0, 0.4)
tpsys = tde.modifiers.new("Dust", type="PARTICLE_SYSTEM").particle_system
tps = tpsys.settings
tps.count = 160
tps.frame_start = 780
tps.frame_end = 1100
tps.lifetime = 45
tps.emit_from = "FACE"
tps.physics_type = "NEWTON"
tps.normal_factor = 1.6
tps.factor_random = 0.7
tps.particle_size = 1.6
tps.size_random = 0.8
tps.render_type = "OBJECT"
tps.instance_object = dust_puff
tpsys.seed = 29

# ---------------------------------------------------------------- ruins, fires, smoke columns
ruin_mat = new_material("Ruin60", base_color=(0.14, 0.12, 0.11), roughness=1.0)
for i, (x, y, ryaw, w, hgt) in enumerate([
        (-80, -20, 0.4, 12, 8), (-58, 22, -0.3, 16, 10), (38, -45, 0.9, 14, 7),
        (-25, 50, 0.2, 18, 9), (60, 30, -0.6, 12, 6), (-90, -10, 0.1, 15, 8)]):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, hgt / 2))
    r = bpy.context.active_object
    r.name = f"Ruin_{i}"
    r.scale = (w, 1.8, hgt)
    r.rotation_euler = (0, 0, ryaw)
    r.data.materials.append(ruin_mat)

fire_mat = new_material("Fire60", base_color=(1.0, 0.35, 0.05),
                        emission_color=(1.0, 0.4, 0.08), emission_strength=6.0)
for i, (x, y) in enumerate([(-43, -33), (39, -43), (-56, 20), (58, 28)]):
    bpy.ops.mesh.primitive_cone_add(radius1=1.6, depth=3.6, location=(x, y, 1.8))
    f = bpy.context.active_object
    f.name = f"Fire_{i}"
    f.data.materials.append(fire_mat)
    for fr, sxy in ((1, 1.0), (200, 1.25), (400, 0.9), (600, 1.3), (800, 0.95),
                    (1000, 1.2), (1200, 1.0), (1440, 1.15)):
        f.scale = (sxy, sxy, 1.0 + (sxy - 1.0) * 1.6)
        f.keyframe_insert(data_path="scale", frame=fr)
    ld = bpy.data.lights.new(f"FireLight_{i}", type="POINT")
    ld.color = (1.0, 0.45, 0.15)
    lo = bpy.data.objects.new(f"FireLight_{i}", ld)
    sc.collection.objects.link(lo)
    lo.location = (x, y, 3.2)
    for fr in range(1, 1441, 24):
        ld.energy = 70 + 45 * abs(math.sin(fr * 0.05 + i * 2.1)) + random.uniform(-8, 8)
        ld.keyframe_insert(data_path="energy", frame=fr)


def smoke_column(x, y, hgt, r0, seed):
    bpy.ops.mesh.primitive_cylinder_add(radius=r0, depth=hgt, location=(x, y, hgt / 2))
    sm = bpy.context.active_object
    sm.name = f"SmokeCol_{seed}"
    mat = bpy.data.materials.new(f"SmokeMat_{seed}")
    mat.use_nodes = True
    n = mat.node_tree.nodes
    bsdf = n["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.12, 0.11, 0.11, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    tex = n.new(type="ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 2.2
    tex.inputs["Detail"].default_value = 5.0
    mapping = n.new(type="ShaderNodeMapping")
    coord = n.new(type="ShaderNodeTexCoord")
    mat.node_tree.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    mat.node_tree.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    ramp = n.new(type="ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[1].position = 0.75
    mat.node_tree.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    mat.node_tree.links.new(ramp.outputs["Alpha"], bsdf.inputs["Alpha"])
    mat.blend_method = "BLEND"
    bsdf.inputs["Alpha"].default_value = 0.85
    sm.data.materials.append(mat)
    for fr, off in ((1, 0.0), (1440, 20.0)):
        mapping.inputs["Location"].default_value = (0, 0, off)
        mapping.inputs["Location"].keyframe_insert(data_path="default_value", frame=fr)
    return sm


for i, (x, y, hgt, r0) in enumerate([(-95, -55, 20, 5), (-100, 50, 22, 6),
                                     (70, -15, 18, 4.5), (60, 45, 18, 4)]):
    smoke_column(x, y, hgt, r0, i)

# ---------------------------------------------------------------- BATTLE TIMELINE

def rifle_flash(pos, frame, seed):
    m = new_material(f"RifleFlash_{frame}_{seed}", base_color=(1, 0.8, 0.4),
                     emission_color=(1.0, 0.7, 0.25), emission_strength=12.0)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.35, location=pos)
    o = bpy.context.active_object
    o.name = f"RifleFlash_{frame}_{seed}"
    o.data.materials.append(m)
    for f, s in ((frame - 1, 0.001), (frame, 1.0), (frame + 2, 0.001)):
        o.scale = (s, s, s)
        o.keyframe_insert(data_path="scale", frame=f)


# --- S3: the assault (tanks open fire on the outpost)
tank_fire(tank1, 520, (13, 2, 1.2), seed=11)
tank_fire(tank2, 580, (8, -4, 1.0), seed=12)
tank_fire(tank1, 650, (16, 1, 1.2), seed=13)

# the shelled barrier gets knocked flying (barrier_3 sits at 16,1)
hb = bpy.data.objects.get("Barrier_3")
if hb:
    for f, loc, rot in ((1, (16.0, 1.0, 0.0), (0, 0, 0.1)),
                        (657, (16.0, 1.0, 0.0), (0, 0, 0.1)),
                        (668, (19.5, 3.2, 1.6), (0.9, 0.4, 1.2)),
                        (685, (20.8, 3.8, 0.35), (1.5, 0.2, 1.8)),
                        (1440, (20.8, 3.8, 0.35), (1.5, 0.2, 1.8))):
        hb.location = loc
        hb.rotation_euler = rot
        hb.keyframe_insert(data_path="location", frame=f)
        hb.keyframe_insert(data_path="rotation_euler", frame=f)

# defenders dive for cover, then recover
for i in (0, 1):
    s = soldiers[i]
    rz = s.rotation_euler.z
    for f, rx in ((1, 0.0), (565, 0.0), (585, 1.15), (700, 1.15), (730, 0.0), (1440, 0.0)):
        s.rotation_euler = (rx, 0, rz)
        s.keyframe_insert(data_path="rotation_euler", frame=f)

# --- S2 foreshadowing: distant flashes on the horizon
for f, x, y in ((300, -110, -35), (400, -105, 30)):
    explosion((x, y, 2), f, size=1.6, seed=f)

# --- S4: counterattack - helicopter strafes tank3 into a burning wreck
explosion((-24, 12, 1.5), 868, size=1.3, seed=21)
# wreck keeps burning for the rest of the film
wfire_mat = new_material("WreckFire", base_color=(1.0, 0.35, 0.05),
                         emission_color=(1.0, 0.4, 0.08), emission_strength=7.0)
bpy.ops.mesh.primitive_cone_add(radius1=1.8, depth=4.0, location=(-24, 12, 2.2))
wf = bpy.context.active_object
wf.name = "WreckFire"
wf.data.materials.append(wfire_mat)
wld = bpy.data.lights.new("WreckLight", type="POINT")
wld.color = (1.0, 0.45, 0.15)
wld.energy = 0
wlo = bpy.data.objects.new("WreckLight", wld)
sc.collection.objects.link(wlo)
wlo.location = (-24, 12, 3.5)
wld.keyframe_insert(data_path="energy", frame=1)
wld.keyframe_insert(data_path="energy", frame=867)
for fr in range(868, 1441, 12):
    wld.energy = 90 + 50 * abs(math.sin(fr * 0.09)) + random.uniform(-10, 10)
    wld.keyframe_insert(data_path="energy", frame=fr)
# the wreck, its fire and its smoke must not exist before the kill at f868
wf.hide_render = True
wf.keyframe_insert(data_path="hide_render", frame=1)
wf.hide_render = True
wf.keyframe_insert(data_path="hide_render", frame=867)
wf.hide_render = False
wf.keyframe_insert(data_path="hide_render", frame=868)
wreck_smoke = smoke_column(-24, 12, 10, 2, 99)
wreck_smoke.hide_render = True
wreck_smoke.keyframe_insert(data_path="hide_render", frame=1)
wreck_smoke.hide_render = True
wreck_smoke.keyframe_insert(data_path="hide_render", frame=867)
wreck_smoke.hide_render = False
wreck_smoke.keyframe_insert(data_path="hide_render", frame=868)

# --- S5: close combat
for f, (x, y) in ((1000, (9.3, -2.0)), (1040, (9.3, 3.4)),
                  (1080, (6.2, 6.2)), (1120, (9.3, -2.0)), (1160, (9.3, 3.4))):
    rifle_flash((x, y, 1.35), f, seed=f)
tank_fire(tank1, 1050, (11, -3, 1.0), seed=14)

# ---------------------------------------------------------------- CAMERAS (one per shot, bound via markers)

def make_cam(name, lens=35):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    co = bpy.data.objects.new(name, cd)
    sc.collection.objects.link(co)
    return co


def dolly(cam, keys):
    """keys: list of (frame, pos, target). Linear moves within the shot."""
    for f, pos, tgt in keys:
        cam.location = pos
        aim_cam(cam, tgt)
        cam.keyframe_insert(data_path="location", frame=f)
        cam.keyframe_insert(data_path="rotation_euler", frame=f)
    for fc in cam.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def shake(cam, f0, f1, amp):
    # jitter around the dolly path: evaluate the location fcurves for the true
    # base position at each frame so offsets never accumulate or drift
    rnd = random.Random(f0 * 13 + 7)
    ad = cam.animation_data
    lfc = {}
    if ad and ad.action:
        for fc in ad.action.fcurves:
            if fc.data_path == "location":
                lfc[fc.array_index] = fc
    for f in range(f0, f1 + 1, 2):
        a = amp * (1 - (f - f0) / max(1, (f1 - f0)))
        if len(lfc) == 3:
            base = Vector((lfc[0].evaluate(f), lfc[1].evaluate(f), lfc[2].evaluate(f)))
        else:
            base = cam.location.copy()
        cam.location = (base.x + rnd.uniform(-a, a),
                        base.y + rnd.uniform(-a, a),
                        base.z + rnd.uniform(-a, a))
        cam.keyframe_insert(data_path="location", frame=f)


# S1: dawn calm, slow push-in on the outpost
c1 = make_cam("Cam_S1", 40)
dolly(c1, [(1, (-8, -26, 9), (8, 0, 2)), (240, (-1, -20, 6.5), (8, 0, 2))])
# S2: wide vista, armor emerging from the dust (clean high vantage, no clutter)
c2 = make_cam("Cam_S2", 32)
dolly(c2, [(241, (0, -70, 22), (-50, 5, 3)), (480, (-5, -66, 20), (-48, 5, 3))])
# S3: the assault - ride with the firing tanks, then whip-pan to the impacts
c3 = make_cam("Cam_S3", 35)
dolly(c3, [(481, (-22, -24, 8), (-36, 6, 3)),
           (600, (-20, -24, 8), (-34, 6, 3)),
           (615, (-8, -18, 7), (10, 0, 2)),
           (720, (-2, -16, 6.5), (12, 0, 2))])
for f0 in (528, 588, 658):
    shake(c3, f0, f0 + 18, 0.35)
# S4: counterattack - jet, strafe run on tank3, truck racing in
c4 = make_cam("Cam_S4", 32)
dolly(c4, [(721, (-40, -30, 14), (-30, 5, 6)),
           (840, (-20, -34, 12), (-20, 8, 4)),
           (960, (10, -30, 10), (20, -12, 3))])
shake(c4, 868, 890, 0.3)
# S5: close combat at the sandbags, handheld
c5 = make_cam("Cam_S5", 38)
dolly(c5, [(961, (3, -13, 3.6), (10, 0, 1.5)),
           (1080, (5, -11, 3.2), (10, 1, 1.5)),
           (1200, (7, -12, 3.8), (9, 0, 1.5))])
shake(c5, 961, 1200, 0.12)
shake(c5, 1058, 1080, 0.35)
# S6: aftermath crane pull-back, high enough to read the whole battlefield
c6 = make_cam("Cam_S6", 24)
dolly(c6, [(1201, (5, -30, 30), (0, 0, 2)),
           (1440, (25, -55, 50), (-5, 5, 2))])

for name, f in (("S1", 1), ("S2", 241), ("S3", 481),
                ("S4", 721), ("S5", 961), ("S6", 1201)):
    m = sc.timeline_markers.new(name, frame=f)
    m.camera = bpy.data.objects["Cam_" + name]

# ---------------------------------------------------------------- render output
out = OUTPUT_DIR if OUTPUT_DIR else "/tmp"
os.makedirs(out, exist_ok=True)
sc.render.filepath = os.path.join(out, "frame_####.png")
print(f"WARZONE60 ready: frames {FRAME_START}-{FRAME_END} -> {sc.render.filepath}")
bpy.ops.render.render(animation=True)
print("WARZONE60 render done")

# War Zone: Desert Outpost
# 5 seconds, 120 frames at 24fps, 1920x1080, Blender EEVEE.
# Farm-ready: reads FRAME_START / FRAME_END / ANIM_START / ANIM_END / OUTPUT_DIR
# from the environment, writes frame_####.png, bakes all animation 1..120.
#
# Real free assets (Poly Pizza):
#   Tank (Quaternius, CC0) ................. https://poly.pizza/m/uYHpj7lz1J
#   Cube Crate (Quaternius, CC0) ........... https://poly.pizza/m/YAghI6GBls
#   Sandbags (J-Toastie, CC-BY) ............ https://poly.pizza/m/xClPIEQJdX
#   Concrete Barrier (J-Toastie, CC-BY) .... https://poly.pizza/m/5Cg2oW7EFn
#   Soldier (KolosStudios, CC-BY) .......... https://poly.pizza/m/XT8jgwSesV
#   Helicopter (jeremy, CC-BY) ............. https://poly.pizza/m/eb7b31pjGtQ
# Environment (ground, sky, smoke, fire, dust, debris) is procedural.

import bpy
import math
import os
import random
from mathutils import Vector

random.seed(1234)

# ---------------------------------------------------------------- env / frames
FRAME_START = int(os.environ.get("FRAME_START", "1"))
FRAME_END = int(os.environ.get("FRAME_END", "120"))
ANIM_START = int(os.environ.get("ANIM_START", "1"))
ANIM_END = int(os.environ.get("ANIM_END", "120"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "")

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

FPS = 24
F_END = 120  # 5 seconds

# ---------------------------------------------------------------- helpers

def kf(obj, frame, data_path="location"):
    obj.keyframe_insert(data_path=data_path, frame=frame)


def look_at(obj, target, up_hint=(0, 0, 1)):
    d = Vector(target) - obj.location
    q = d.to_track_quat("-Z", "Y")
    obj.rotation_euler = q.to_euler()


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
    # remove the original imported objects after duplicating what we need
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

# ---------------------------------------------------------------- scene setup
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
# Cycles on CPU: the render farm runners have no GPU, and EEVEE falls back to
# software rasterization there (far too slow). Cycles CPU is the reliable path.
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
# WZ_RES_PCT lets a local test render at reduced resolution; the farm leaves it unset (100)
sc.render.resolution_percentage = int(os.environ.get("WZ_RES_PCT", "100"))
sc.render.film_transparent = False
sc.render.image_settings.file_format = "PNG"
sc.render.fps = FPS
sc.frame_start = FRAME_START
sc.frame_end = FRAME_END

# ---------------------------------------------------------------- world: grim war sky
# custom vertical gradient (art-directable, no physical sky): burnt smoky
# horizon fading up into dark slate. Built from world-space Z.
if bpy.context.scene.world is None:
    bpy.context.scene.world = bpy.data.worlds.new("WarWorld")
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
wmap.inputs["To Min"].default_value = 0.0
wmap.inputs["To Max"].default_value = 1.0
wramp = wnodes.new(type="ShaderNodeValToRGB")
el = wramp.color_ramp.elements
el[0].position = 0.0
el[0].color = (0.33, 0.21, 0.13, 1.0)   # smoky burnt-orange horizon
el[1].position = 0.30
el[1].color = (0.30, 0.25, 0.23, 1.0)   # gray-brown haze
mid_el = wramp.color_ramp.elements.new(0.62)
mid_el.color = (0.16, 0.16, 0.19, 1.0)  # dark slate
el[1].position = 1.0
el[1].color = (0.09, 0.10, 0.13, 1.0)   # near-black zenith
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

# ---------------------------------------------------------------- ground: dusty desert
bpy.ops.mesh.primitive_plane_add(size=240, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
gmat = bpy.data.materials.new("DesertGround")
gmat.use_nodes = True
gn = gmat.node_tree.nodes
gbsdf = gn["Principled BSDF"]
# sandy base with patchy variation
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
gbump = gn.new(type="ShaderNodeTexNoise")
gbump.inputs["Scale"].default_value = 40.0
gbump.inputs["Detail"].default_value = 3.0
gbumpnode = gn.new(type="ShaderNodeBump")
gbumpnode.inputs["Strength"].default_value = 0.35
gmat.node_tree.links.new(gbump.outputs["Fac"], gbumpnode.inputs["Height"])
gmat.node_tree.links.new(gbumpnode.outputs["Normal"], gbsdf.inputs["Normal"])
ground.data.materials.append(gmat)

# scattered rocks / debris
rock_mat = new_material("Rock", base_color=(0.35, 0.30, 0.25), roughness=1.0)
for i in range(40):
    x = random.uniform(-70, 70)
    y = random.uniform(-60, 60)
    if abs(x) < 20 and abs(y) < 16:
        continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,
                                          radius=random.uniform(0.25, 1.1),
                                          location=(x, y, 0.1))
    r = bpy.context.active_object
    r.name = f"Rock_{i}"
    r.scale.z = random.uniform(0.4, 0.7)
    r.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3))
    r.data.materials.append(rock_mat)

# ---------------------------------------------------------------- TANK (hero)
tank_root, tank_parts = import_glb("tank.glb")
tank_root.name = "TankRig"
tank_root.location = (-30, 7, 0)
tank_root.rotation_euler = (0, 0, math.pi)  # model forward is -X; face +X world

armature = next(o for o in tank_parts if o.type == "ARMATURE")
turret = next(o for o in tank_parts if o.name.startswith("Tank_Turret"))
gun = next(o for o in tank_parts if o.name.startswith("Tank_Gun"))

# loop the built-in forward track animation across the whole timeline
fwd_action = bpy.data.actions.get("TankArmature|Tank_Forward_TankArmature")
if fwd_action is not None:
    armature.animation_data_create()
    armature.animation_data.action = fwd_action
    add_cycles_modifier(fwd_action)

# parent gun to turret so they rotate together
bpy.context.view_layer.update()
gun_mat = gun.matrix_world.copy()
gun.parent = turret
gun.matrix_world = gun_mat

# muzzle empty at the gun tip (farthest bbox corner from the hull)
body_mesh = next(o for o in tank_parts if o.name.startswith("Tank_body"))
bc = mesh_world_center(body_mesh)
corners = [gun.matrix_world @ Vector(c) for c in gun.bound_box]
muzzle_world = max(corners, key=lambda v: (v - bc).length)
muzzle = bpy.data.objects.new("Muzzle", None)
sc.collection.objects.link(muzzle)
muzzle.parent = gun
# set via local coords (robust to parent scale)
bpy.context.view_layer.update()
gun_inv = gun.matrix_world.inverted()
muzzle.location = gun_inv @ muzzle_world

# tank advance: drive toward the outpost over the 5 seconds
for f, x, y in ((1, -24, 6.5), (60, -16, 4.8), (120, -8, 3.2)):
    tank_root.location = (x, y, 0)
    tank_root.keyframe_insert(data_path="location", frame=f)
# gentle hull wobble
for f, rz in ((1, 0.0), (30, 0.012), (60, -0.012), (90, 0.012), (120, 0.0)):
    tank_root.rotation_euler = (0, 0, math.pi + rz)
    tank_root.keyframe_insert(data_path="rotation_euler", frame=f)

# turret slowly tracks the outpost with a slight sweep
for f, yaw in ((1, 0.0), (40, -0.12), (80, 0.10), (120, -0.05)):
    turret.rotation_euler = (0, 0, yaw)
    turret.keyframe_insert(data_path="rotation_euler", frame=f)

# dust kicked up behind the tracks (instanced low-poly puffs)
dust_mat = new_material("Dust", base_color=(0.55, 0.46, 0.34), roughness=1.0, alpha=0.55)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.6)
dust_puff = bpy.context.active_object
dust_puff.name = "DustPuff"
dust_puff.data.materials.append(dust_mat)
dust_puff.hide_viewport = True
dust_puff.hide_render = True

bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0.3))
dust_emit = bpy.context.active_object
dust_emit.name = "DustEmitter"
dust_emit.hide_viewport = True
dust_emit.visible_camera = False  # emitter stays invisible, particles still render
dust_emit.visible_shadow = False
dust_emit.parent = tank_root
dust_emit.location = (2.5, 0, 0.4)  # behind the hull in rig space
psys = dust_emit.modifiers.new("Dust", type="PARTICLE_SYSTEM").particle_system
ps = psys.settings
ps.count = 260
ps.frame_start = 1
ps.frame_end = 120
ps.lifetime = 45
ps.emit_from = "FACE"
ps.distribution = "RAND"
ps.physics_type = "NEWTON"
ps.normal_factor = 1.2
ps.factor_random = 0.6
ps.tangent_factor = 0.8
ps.tangent_phase = 1.0
ps.particle_size = 1.4
ps.size_random = 0.8
ps.use_emit_random = False
ps.render_type = "OBJECT"
ps.instance_object = dust_puff
ps.show_unborn = False
# grow + fade over life via keyed size/alpha is complex; keep constant puffs
seed_obj = psys
psys.seed = 7

# ---------------------------------------------------------------- OUTPOST (defenders)
# sandbag wall segments forming a defensive line around x=9
sb_root, sb_parts = import_glb("sandbags.glb")
sb_mesh = next(o for o in sb_parts if o.type == "MESH")
sb_positions = [
    (9, -5.5, 0, 0.0), (9, -3.5, 0, 0.0), (9, -1.5, 0, 0.0),
    (9, 0.5, 0, 0.0), (9, 2.5, 0, 0.0), (9, 4.5, 0, 0.0),
    (7.2, 5.6, 0, 1.2), (10.8, 5.6, 0, -1.2),
]
for i, (x, y, z, ryaw) in enumerate(sb_positions):
    dup = sb_mesh.copy()
    dup.data = sb_mesh.data.copy()
    sc.collection.objects.link(dup)
    dup.name = f"SandbagWall_{i}"
    dup.location = (x, y, z)
    dup.rotation_euler = (0, 0, ryaw)
discard_import(sb_root, sb_parts)

# concrete barriers scattered (one takes the shell hit)
cb_root, cb_parts = import_glb("concrete_barrier.glb")
cb_mesh = next(o for o in cb_parts if o.type == "MESH")
cb_spots = [(13.5, -3.0, 0.15), (13.5, 6.0, -0.2), (5.0, -7.5, 0.5), (16.0, 1.0, 0.1)]
barriers = []
for i, (x, y, ryaw) in enumerate(cb_spots):
    dup = cb_mesh.copy()
    dup.data = cb_mesh.data.copy()
    sc.collection.objects.link(dup)
    dup.name = f"Barrier_{i}"
    dup.location = (x, y, 0)
    dup.rotation_euler = (0, 0, ryaw)
    barriers.append(dup)
discard_import(cb_root, cb_parts)
hit_barrier = barriers[3]  # this one gets hit at frame 62

# crate stacks near the soldiers
cc_root, cc_parts = import_glb("cube_crate.glb")
cc_mesh = next(o for o in cc_parts if o.type == "MESH")
for i, (x, y, z, s) in enumerate([(11.5, -4.2, 0, 0.9), (11.5, -4.2, 1.85, 0.9),
                                  (12.8, -4.5, 0, 0.7), (11.8, 5.2, 0, 1.0)]):
    dup = cc_mesh.copy()
    dup.data = cc_mesh.data.copy()
    sc.collection.objects.link(dup)
    dup.name = f"Crate_{i}"
    dup.location = (x, y, z)
    dup.scale = (s, s, s)
discard_import(cc_root, cc_parts)

# soldiers manning the line, facing the incoming tank (-X, their model facing)
soldiers = []
for i, (x, y) in enumerate([(10.6, -2.2), (10.6, 3.2)]):
    s_root, s_parts = import_glb("soldier.glb")
    s_root.name = f"Soldier_{i}"
    arm = next(o for o in s_parts if o.type == "ARMATURE")
    # normalize to ~1.9 m tall
    bpy.context.view_layer.update()
    ws = [arm.matrix_world @ Vector(c) for c in arm.bound_box]
    h = max(v.z for v in ws) - min(v.z for v in ws)
    s = 1.9 / h
    s_root.scale = (s, s, s)
    s_root.location = (x, y, 0)
    # standing pose action
    stand = bpy.data.actions.get("Armature|Standing_Armature")
    if stand is not None:
        arm.animation_data_create()
        arm.animation_data.action = stand
    # subtle idle sway
    for f, sx in ((1, 0.0), (60, 0.03), (120, 0.0)):
        s_root.rotation_euler = (sx, 0, 0)
        s_root.keyframe_insert(data_path="rotation_euler", frame=f)
    soldiers.append(s_root)

# ---------------------------------------------------------------- ruined walls (background)
ruin_mat = new_material("RuinConcrete", base_color=(0.32, 0.30, 0.28), roughness=1.0)
ruins = [(-38, -28, 0, 0.4, 10, 7), (-48, 18, 0, -0.3, 14, 9),
         (30, -38, 0, 0.9, 12, 6), (-20, 42, 0, 0.2, 16, 8)]
for i, (x, y, z, ryaw, w, hgt) in enumerate(ruins):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, hgt / 2))
    r = bpy.context.active_object
    r.name = f"Ruin_{i}"
    r.scale = (w, 1.6, hgt)
    r.rotation_euler = (0, 0, ryaw)
    r.data.materials.append(ruin_mat)

# ---------------------------------------------------------------- battlefield fires
fire_mat = new_material("Fire", base_color=(1.0, 0.35, 0.05),
                        emission_color=(1.0, 0.4, 0.08), emission_strength=6.0)
fire_lights = []
for i, (x, y) in enumerate([(-36, -26), (31, -36), (-46, 16)]):
    bpy.ops.mesh.primitive_cone_add(radius1=1.4, depth=3.2, location=(x, y, 1.6))
    f = bpy.context.active_object
    f.name = f"Fire_{i}"
    f.data.materials.append(fire_mat)
    for fr, sxy in ((1, 1.0), (20, 1.25), (40, 0.9), (60, 1.3), (80, 0.95), (100, 1.2), (120, 1.0)):
        f.scale = (sxy, sxy, 1.0 + (sxy - 1.0) * 1.6)
        f.keyframe_insert(data_path="scale", frame=fr)
    ld = bpy.data.lights.new(f"FireLight_{i}", type="POINT")
    ld.color = (1.0, 0.45, 0.15)
    lo = bpy.data.objects.new(f"FireLight_{i}", ld)
    sc.collection.objects.link(lo)
    lo.location = (x, y, 3.0)
    for fr in range(1, 121, 6):
        ld.energy = 60 + 40 * abs(math.sin(fr * 0.7 + i * 2.1)) + random.uniform(-8, 8)
        ld.keyframe_insert(data_path="energy", frame=fr)
    fire_lights.append(lo)

# ---------------------------------------------------------------- smoke columns (background)
def smoke_material(name):
    mat = bpy.data.materials.new(name)
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
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    mat.node_tree.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    mat.node_tree.links.new(ramp.outputs["Alpha"], bsdf.inputs["Alpha"])
    mat.blend_method = "BLEND"
    bsdf.inputs["Alpha"].default_value = 0.85
    return mat, mapping

for i, (x, y, hgt, r0) in enumerate([(-42, -20, 30, 4.5), (-52, 22, 36, 5.5), (26, -44, 26, 4.0)]):
    bpy.ops.mesh.primitive_cylinder_add(radius=r0, depth=hgt, location=(x, y, hgt / 2))
    sm = bpy.context.active_object
    sm.name = f"Smoke_{i}"
    smat, smap = smoke_material(f"SmokeMat_{i}")
    sm.data.materials.append(smat)
    # smoke rises: scroll the noise upward over the animation
    for fr, off in ((1, 0.0), (120, 6.0)):
        smap.inputs["Location"].default_value = (0, 0, off)
        smap.inputs["Location"].keyframe_insert(data_path="default_value", frame=fr)
    sm.rotation_euler = (0, 0, random.uniform(0, 3))
    kf(sm, 120)

# ---------------------------------------------------------------- helicopter flyover (background)
heli_root, heli_parts = import_glb("helicopter.glb")
heli_root.name = "Helicopter"
heli_mesh = next(o for o in heli_parts if o.type == "MESH")
bpy.context.view_layer.update()
ws = [heli_mesh.matrix_world @ Vector(c) for c in heli_mesh.bound_box]
length = max(v.x for v in ws) - min(v.x for v in ws)
hs = 9.0 / length
heli_root.scale = (hs, hs, hs)
for f, pos in ((1, (-75, -58, 34)), (60, (0, -48, 37)), (120, (75, -38, 40))):
    heli_root.location = pos
    heli_root.keyframe_insert(data_path="location", frame=f)
heli_root.rotation_euler = (0, 0.06, math.pi / 2)  # nose along +X travel
kf(heli_root, 1, "rotation_euler")

# ---------------------------------------------------------------- FIRING SEQUENCE
# frame 55: muzzle flash + tracer; frame 62: shell hits the barrier
FIRE_F, HIT_F = 55, 62
impact = Vector((16.0, 1.0, 1.2))

# muzzle flash: bright emissive sphere + light spike parented to the gun tip
flash_mat = new_material("MuzzleFlash", base_color=(1, 0.7, 0.25),
                         emission_color=(1.0, 0.62, 0.18), emission_strength=14.0)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
flash = bpy.context.active_object
flash.name = "MuzzleFlash"
flash.data.materials.append(flash_mat)
flash_ld = bpy.data.lights.new("FlashLight", type="POINT")
flash_ld.color = (1.0, 0.6, 0.25)
flash_lo = bpy.data.objects.new("FlashLight", flash_ld)
sc.collection.objects.link(flash_lo)
# glTF parts carry a large object scale, so track the muzzle tip in world
# space with keyframes instead of parenting
for f, s, e in ((54, 0.001, 0), (55, 1.6, 4000), (57, 1.1, 1500), (59, 0.001, 0)):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    mp = (muzzle.matrix_world @ Vector((0, 0, 0))).copy()
    flash.location = mp
    flash.scale = (s, s, s)
    flash.keyframe_insert(data_path="location", frame=f)
    flash.keyframe_insert(data_path="scale", frame=f)
    flash_lo.location = mp
    flash_ld.energy = e
    flash_lo.keyframe_insert(data_path="location", frame=f)
    flash_ld.keyframe_insert(data_path="energy", frame=f)
sc.frame_set(1)

# tracer: thin glowing streak from muzzle (at mid-flight frame) to impact
sc.frame_set(58)
bpy.context.view_layer.update()
muzzle_world_f = (muzzle.matrix_world @ Vector((0, 0, 0))).copy()
sc.frame_set(1)
tracer_mat = new_material("Tracer", base_color=(1, 0.55, 0.15),
                          emission_color=(1.0, 0.5, 0.12), emission_strength=8.0)
mid = (muzzle_world_f + impact) / 2
length = (impact - muzzle_world_f).length
bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=length, location=mid)
tracer = bpy.context.active_object
tracer.name = "Tracer"
tracer.data.materials.append(tracer_mat)
d = (impact - muzzle_world_f).normalized()
tracer.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
tracer.hide_viewport = False
# hidden until the shot, visible for the shell flight, gone on impact
for f, vis in ((1, False), (54, True), (62, True), (63, False)):
    tracer.hide_render = not vis
    tracer.keyframe_insert(data_path="hide_render", frame=f)

# explosion fireball at the barrier
boom_mat = new_material("Fireball", base_color=(1, 0.42, 0.08),
                        emission_color=(1.0, 0.38, 0.06), emission_strength=3.5)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=impact)
boom = bpy.context.active_object
boom.name = "Fireball"
boom.data.materials.append(boom_mat)
for f, s in ((61, 0.001), (64, 1.9), (70, 1.5), (80, 0.001)):
    boom.scale = (s, s * 1.25, s)
    boom.keyframe_insert(data_path="scale", frame=f)
boom_ld = bpy.data.lights.new("BoomLight", type="POINT")
boom_ld.color = (1.0, 0.5, 0.18)
boom_lo = bpy.data.objects.new("BoomLight", boom_ld)
sc.collection.objects.link(boom_lo)
boom_lo.location = impact + Vector((0, 0, 1.5))
for f, e in ((61, 0), (64, 1500), (72, 600), (82, 0)):
    boom_ld.energy = e
    boom_ld.keyframe_insert(data_path="energy", frame=f)

# the hit barrier gets knocked flying
for f, loc, rot in ((1, (16.0, 1.0, 0.0), (0, 0, 0.1)),
                    (61, (16.0, 1.0, 0.0), (0, 0, 0.1)),
                    (70, (19.5, 3.2, 1.4), (0.9, 0.4, 1.2)),
                    (85, (20.8, 3.8, 0.35), (1.5, 0.2, 1.8)),
                    (120, (20.8, 3.8, 0.35), (1.5, 0.2, 1.8))):
    hit_barrier.location = loc
    hit_barrier.rotation_euler = rot
    hit_barrier.keyframe_insert(data_path="location", frame=f)
    hit_barrier.keyframe_insert(data_path="rotation_euler", frame=f)

# debris burst (instanced chunks with gravity)
debris_mat = new_material("Debris", base_color=(0.25, 0.22, 0.2), roughness=1.0)
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, -50))
debris_obj = bpy.context.active_object
debris_obj.name = "DebrisChunk"
debris_obj.data.materials.append(debris_mat)
debris_obj.hide_viewport = True
debris_obj.hide_render = True
bpy.ops.mesh.primitive_plane_add(size=2, location=(impact.x, impact.y, impact.z))
debris_emit = bpy.context.active_object
debris_emit.name = "DebrisEmitter"
debris_emit.hide_viewport = True
debris_emit.visible_camera = False
debris_emit.visible_shadow = False
dsys = debris_emit.modifiers.new("Debris", type="PARTICLE_SYSTEM").particle_system
dp = dsys.settings
dp.count = 90
dp.frame_start = HIT_F
dp.frame_end = HIT_F + 4
dp.lifetime = 55
dp.emit_from = "FACE"
dp.physics_type = "NEWTON"
dp.normal_factor = 9.0
dp.factor_random = 1.5
dp.particle_size = 0.9
dp.size_random = 0.7
dp.render_type = "OBJECT"
dp.instance_object = debris_obj
dsys.seed = 21

# explosion smoke puff: soft gray billows rising and expanding
puff_mat = new_material("BoomSmoke", base_color=(0.38, 0.36, 0.34), roughness=1.0, alpha=0.5)
for i in range(7):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0,
                                          location=(impact.x + random.uniform(-1.2, 1.2),
                                                    impact.y + random.uniform(-1.2, 1.2),
                                                    impact.z))
    p = bpy.context.active_object
    p.name = f"BoomPuff_{i}"
    p.data.materials.append(puff_mat)
    rise = random.uniform(6, 10)
    for f, s, z in ((HIT_F, 0.3, impact.z), (HIT_F + 12, 1.6, impact.z + rise * 0.5),
                    (120, 2.4, impact.z + rise)):
        p.scale = (s, s, s)
        p.location.z = z
        p.keyframe_insert(data_path="scale", frame=f)
        p.keyframe_insert(data_path="location", frame=f)

# ---------------------------------------------------------------- CAMERA
cam_data = bpy.data.cameras.new("WarCam")
cam_data.lens = 32
cam = bpy.data.objects.new("WarCam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
camrig = bpy.data.objects.new("CamRig", None)
sc.collection.objects.link(camrig)
cam.parent = camrig

# slow push-in panning right with the action: tank early, explosion late
cam_keys = ((1, (-10, -30, 11), (-4, 2, 2)),
            (54, (-2, -26, 9), (2, 2, 2)),
            (120, (6, -22, 7), (10, 2, 2)))
for f, pos, tgt in cam_keys:
    camrig.location = pos
    camrig.keyframe_insert(data_path="location", frame=f)
# aim in world space (the rig has no rotation, so local == world rotation)
for f, pos, tgt in cam_keys:
    sc.frame_set(f)
    bpy.context.view_layer.update()
    world_loc = cam.matrix_world.translation.copy()
    d = Vector(tgt) - world_loc
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="rotation_euler", frame=f)
sc.frame_set(1)
# impact shake: jitter the camera for ~18 frames after the hit
for f in range(HIT_F, HIT_F + 18, 2):
    amp = 0.22 * (1 - (f - HIT_F) / 18.0)
    cam.location = (random.uniform(-amp, amp), random.uniform(-amp, amp), random.uniform(-amp, amp))
    cam.keyframe_insert(data_path="location", frame=f)
cam.location = (0, 0, 0)
cam.keyframe_insert(data_path="location", frame=HIT_F + 20)

# ---------------------------------------------------------------- render output
out = OUTPUT_DIR if OUTPUT_DIR else "/tmp"
os.makedirs(out, exist_ok=True)
sc.render.filepath = os.path.join(out, "frame_####.png")
print(f"WARZONE scene ready: frames {FRAME_START}-{FRAME_END} -> {sc.render.filepath}")
bpy.ops.render.render(animation=True)
print("WARZONE render done")

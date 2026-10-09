"""Low-poly rocket landing on the moon, Earth in background.
10 seconds @ 24fps = 240 frames. EEVEE render.
Run: blender --background --python rocket_moon_landing.py
Set env TEST_FRAME=120 to render a single test frame.

Farm-ready: reads FRAME_START/FRAME_END (chunk) and OUTPUT_DIR from env.
When OUTPUT_DIR is set (GitHub Actions farm), writes frames/frame_XXXX.png
as the blender-render workflow expects. Keyframes are baked at absolute
frames 1-240, matching ANIM_START=1 / ANIM_END=240.
"""
import bpy
import math
import os
import random

random.seed(7)

TEST = os.environ.get("TEST_FRAME")
FARM = "OUTPUT_DIR" in os.environ
OUT_DIR = os.environ.get("OUTPUT_DIR", os.path.expanduser("~/workspace/goals/muse-tasks-autopilot/hidden_files/frames"))
os.makedirs(OUT_DIR, exist_ok=True)

# --- clean slate ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.film_transparent = False
scene.eevee.taa_render_samples = 48
scene.eevee.use_bloom = True
scene.render.fps = 24
if TEST:
    scene.frame_start = scene.frame_end = int(TEST)
    scene.render.filepath = os.path.join(OUT_DIR, "test.png")
else:
    scene.frame_start = int(os.environ.get("FRAME_START", "1"))
    scene.frame_end = int(os.environ.get("FRAME_END", "240"))
    # NOTE: Blender uses # (not printf %04d) as the frame-number placeholder.
    scene.render.filepath = os.path.join(OUT_DIR, "frame_####.png" if FARM else "rocket_####.png")
scene.render.image_settings.file_format = 'PNG'

# --- world: black space ---
world = bpy.data.worlds['World']
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.004, 0.004, 0.01, 1.0)
bg.inputs['Strength'].default_value = 1.0

def principled(name, base_color, metallic=0.0, roughness=0.5, emission=None,
               emission_strength=2.0, alpha=None):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*base_color, 1.0)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    if alpha is not None:
        bsdf.inputs['Alpha'].default_value = alpha
        mat.blend_method = 'BLEND'
    return mat

def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj

def track_to(obj, target):
    c = obj.constraints.new(type='TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'

white = principled('White', (0.92, 0.93, 0.95), roughness=0.45)
red = principled('Red', (0.85, 0.16, 0.12), roughness=0.5)
dark = principled('Dark', (0.12, 0.13, 0.16), metallic=0.6, roughness=0.4)
glass_blue = principled('GlassBlue', (0.1, 0.25, 0.6), roughness=0.15,
                        metallic=0.2)
moon_mat = principled('Moon', (0.40, 0.40, 0.43), roughness=0.95)
crater_mat = principled('Crater', (0.38, 0.38, 0.42), roughness=1.0)
flame_mat = principled('Flame', (1.0, 0.55, 0.1), emission=(1.0, 0.45, 0.08),
                       emission_strength=6.0)
earth_blue = principled('EarthBlue', (0.12, 0.35, 0.85), roughness=0.6,
                        emission=(0.05, 0.15, 0.45), emission_strength=0.6)
earth_green = principled('EarthGreen', (0.2, 0.55, 0.25), roughness=0.8)
atmo_mat = principled('Atmo', (0.3, 0.55, 1.0), emission=(0.3, 0.55, 1.0),
                      emission_strength=1.2, alpha=0.22)
star_mat = principled('Star', (1, 1, 1), emission=(1, 1, 1),
                      emission_strength=3.0)
dust_mat = principled('Dust', (0.6, 0.6, 0.62), roughness=1.0)

# --- stars: shared low-poly mesh, 350 instances on a big sphere ---
bpy.ops.mesh.primitive_ico_sphere_add(radius=0.09, subdivisions=0,
                                      location=(0, 0, 0))
star_proto = bpy.context.active_object
star_proto.data.materials.append(star_mat)
flat(star_proto)
star_mesh = star_proto.data
star_proto.hide_render = True
for i in range(350):
    theta = random.uniform(0, 2 * math.pi)
    phi = random.uniform(-0.4, math.pi)  # mostly above horizon
    r = 120
    x = r * math.sin(phi) * math.cos(theta)
    y = r * math.sin(phi) * math.sin(theta)
    z = r * math.cos(phi)
    s = bpy.data.objects.new('Star_%d' % i, star_mesh)
    bpy.context.collection.objects.link(s)
    s.location = (x, y, z)
    s.scale = (random.uniform(0.5, 1.6),) * 3

# --- moon surface: displaced low-poly grid ---
bpy.ops.mesh.primitive_grid_add(x_subdivisions=44, y_subdivisions=44,
                                size=90, location=(0, 0, -0.05))
moon = bpy.context.active_object
moon.name = 'Moon'
moon.data.materials.append(moon_mat)
flat(moon)
mesh = moon.data
for v in mesh.vertices:
    d = math.hypot(v.co.x, v.co.y)
    if d > 5.0:
        bump = min(1.0, (d - 5.0) / 10.0)
        v.co.z += random.uniform(-0.35, 0.45) * bump
mesh.update()

# --- craters: dark rings + discs, away from landing site ---
crater_spots = [(-9, 6, 2.2), (8, 9, 1.6), (-6, -10, 2.8), (11, -5, 1.3),
                (3, 14, 1.9)]
for i, (cx, cy, cr) in enumerate(crater_spots):
    bpy.ops.mesh.primitive_torus_add(align='WORLD',
                                     location=(cx, cy, 0.15),
                                     major_radius=cr, minor_radius=0.22)
    rim = bpy.context.active_object
    rim.name = 'CraterRim_%d' % i
    rim.scale = (1, 1, 0.45)
    rim.data.materials.append(crater_mat)
    flat(rim)
    bpy.ops.mesh.primitive_circle_add(radius=cr * 0.92,
                                      location=(cx, cy, 0.02))
    disc = bpy.context.active_object
    disc.name = 'CraterDisc_%d' % i
    disc.data.materials.append(crater_mat)

# --- Earth in the background ---
bpy.ops.object.empty_add(location=(-50.45, 64.75, 4.8))
earth_rig = bpy.context.active_object
earth_rig.name = 'EarthRig'
bpy.ops.mesh.primitive_ico_sphere_add(radius=7.0, subdivisions=3,
                                      location=(0, 0, 0))
earth = bpy.context.active_object
earth.name = 'Earth'
earth.parent = earth_rig
earth.data.materials.append(earth_blue)
flat(earth)
# low-poly continents: green blobs hugging the surface
blobs = [((2.5, 1.5, 3.2), 1.6), ((-2.0, 2.8, 2.6), 1.3),
         ((-1.0, -3.2, 2.2), 1.8), ((3.0, -1.0, -2.8), 1.1),
         ((-3.4, -0.5, -1.5), 1.0), ((0.5, 3.8, -1.8), 0.9)]
for i, ((bx, by, bz), br) in enumerate(blobs):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=br, subdivisions=1,
                                          location=(bx, by, bz))
    b = bpy.context.active_object
    b.name = 'Continent_%d' % i
    b.parent = earth_rig
    b.data.materials.append(earth_green)
    flat(b)
    # push slightly inward so it sits on the surface
    n = math.sqrt(bx * bx + by * by + bz * bz)
    b.location = (bx / n * 6.37, by / n * 6.37, bz / n * 6.37)
bpy.ops.mesh.primitive_ico_sphere_add(radius=7.7, subdivisions=3,
                                      location=(0, 0, 0))
atmo = bpy.context.active_object
atmo.name = 'Atmosphere'
atmo.parent = earth_rig
atmo.data.materials.append(atmo_mat)
earth_rig.rotation_euler = (0.3, 0.2, 0.0)
earth_rig.keyframe_insert(data_path='rotation_euler', frame=1)
earth_rig.rotation_euler = (0.3, 0.2, 0.55)
earth_rig.keyframe_insert(data_path='rotation_euler', frame=240)

# --- rocket (origin at base) ---
bpy.ops.object.empty_add(location=(3.0, 0, 12.0))
rocket = bpy.context.active_object
rocket.name = 'Rocket'

def part(op, name, mat, loc, parent=rocket):
    op()
    o = bpy.context.active_object
    o.name = name
    o.parent = parent
    o.location = loc
    o.data.materials.append(mat)
    return flat(o)

# landing fins (double as legs)
for i in range(3):
    a = math.radians(i * 120)
    fin = part(lambda: bpy.ops.mesh.primitive_cube_add(size=1),
               'Fin_%d' % i, red, (0, 0, 0))
    fin.scale = (0.55, 0.09, 0.95)
    fin.location = (math.cos(a) * 0.62, math.sin(a) * 0.62, 0.48)
    fin.rotation_euler = (0, 0, a)

# engine bell
part(lambda: bpy.ops.mesh.primitive_cone_add(radius1=0.32, radius2=0.16,
                                             depth=0.45),
     'Engine', dark, (0, 0, 0.72))
# body
part(lambda: bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=2.0,
                                                 vertices=12),
     'Body', white, (0, 0, 1.95))
# red band
part(lambda: bpy.ops.mesh.primitive_cylinder_add(radius=0.515, depth=0.28,
                                                 vertices=12),
     'Band', red, (0, 0, 1.25))
# window (faces the camera side, -Y)
win = part(lambda: bpy.ops.mesh.primitive_cylinder_add(radius=0.18,
                                                       depth=0.06,
                                                       vertices=12),
           'Window', glass_blue, (0, -0.5, 2.35))
win.rotation_euler = (math.radians(90), 0, 0)
# nose cone
part(lambda: bpy.ops.mesh.primitive_cone_add(radius1=0.5, radius2=0.02,
                                             depth=1.1, vertices=12),
     'Nose', red, (0, 0, 3.5))
# tip light
tip = part(lambda: bpy.ops.mesh.primitive_ico_sphere_add(radius=0.09,
                                                         subdivisions=1),
           'TipLight', star_mat, (0, 0, 4.08))

# flame (wide at engine, tapering down)
flame = part(lambda: bpy.ops.mesh.primitive_cone_add(radius1=0.05,
                                                     radius2=0.34,
                                                     depth=1.6,
                                                     vertices=10),
             'Flame', flame_mat, (0, 0, -0.15))

# --- dust puffs at the landing site ---
dusts = []
for i in range(8):
    a = math.radians(i * 45 + 10)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.45, subdivisions=1,
                                          location=(math.cos(a) * 1.3,
                                                    math.sin(a) * 1.3,
                                                    0.25))
    d = bpy.context.active_object
    d.name = 'Dust_%d' % i
    d.data.materials.append(dust_mat)
    flat(d)
    d.scale = (0.01, 0.01, 0.01)
    dusts.append((d, a))

# --- animation ---
# rocket descent: drift in from the side, brake, touchdown at f185
for f, x, z in [(1, 3.0, 12.0), (110, 1.2, 5.2), (175, 0.15, 0.5),
                (185, 0.0, 0.0), (240, 0.0, 0.0)]:
    rocket.location = (x, 0, z)
    rocket.keyframe_insert(data_path='location', frame=f)
# touchdown wobble
rocket.rotation_euler = (0, 0, 0)
rocket.keyframe_insert(data_path='rotation_euler', frame=175)
rocket.rotation_euler = (0.035, 0, 0.02)
rocket.keyframe_insert(data_path='rotation_euler', frame=188)
rocket.rotation_euler = (0, 0, 0)
rocket.keyframe_insert(data_path='rotation_euler', frame=205)

# flame flicker during descent, off after touchdown
for f in range(1, 176, 6):
    s = random.uniform(0.85, 1.2)
    flame.scale = (s, s, random.uniform(0.9, 1.25))
    flame.keyframe_insert(data_path='scale', frame=f)
flame.scale = (0.6, 0.6, 0.6)
flame.keyframe_insert(data_path='scale', frame=178)
flame.scale = (0.001, 0.001, 0.001)
flame.keyframe_insert(data_path='scale', frame=184)
flame.keyframe_insert(data_path='scale', frame=240)

# dust burst on touchdown
for d, a in dusts:
    d.keyframe_insert(data_path='scale', frame=170)
    d.keyframe_insert(data_path='location', frame=170)
    d.scale = (1.4, 1.4, 0.9)
    d.location = (math.cos(a) * 2.6, math.sin(a) * 2.6, 0.5)
    d.keyframe_insert(data_path='scale', frame=192)
    d.keyframe_insert(data_path='location', frame=192)
    d.scale = (0.01, 0.01, 0.01)
    d.keyframe_insert(data_path='scale', frame=215)

# --- lights ---
bpy.ops.object.light_add(type='SUN', location=(0, 0, 0))
sun = bpy.context.active_object
sun.name = 'Sun'
sun.data.energy = 2.2
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
bpy.ops.object.light_add(type='AREA', location=(-8, -6, 6))
fill = bpy.context.active_object
fill.name = 'Fill'
fill.data.energy = 120
fill.data.size = 8
fill.data.color = (0.5, 0.65, 1.0)

# --- camera: slow push-in on the landing site ---
bpy.ops.object.empty_add(location=(0, 0, 4.0))
aim = bpy.context.active_object
aim.name = 'Aim'
bpy.ops.object.camera_add(location=(10.5, -13.5, 7.6))
cam = bpy.context.active_object
cam.data.lens = 40
track_to(cam, aim)
scene.camera = cam
cam.location = (10.5, -13.5, 7.6)
cam.keyframe_insert(data_path='location', frame=1)
cam.location = (8.6, -11.0, 5.4)
cam.keyframe_insert(data_path='location', frame=240)

bpy.context.scene.frame_set(int(TEST) if TEST else 1)
bpy.ops.render.render(animation=not TEST, write_still=bool(TEST))
print('RENDER_DONE')

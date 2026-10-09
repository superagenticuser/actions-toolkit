import bpy
import math
import os
import random

TEST = os.environ.get('TEST') == '1'

# --- clean slate ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.render.resolution_x = 854
scene.render.resolution_y = 480
scene.cycles.samples = 28
scene.cycles.device = 'CPU'
scene.cycles.use_denoising = True
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
outdir = os.environ.get('OUTPUT_DIR', 'frames')
os.makedirs(outdir, exist_ok=True)
scene.render.filepath = os.path.join(outdir, 'frame_')

scene.render.fps = 24
anim_start = int(os.environ.get('ANIM_START', '1'))
anim_end = int(os.environ.get('ANIM_END', '240'))
scene.frame_start = int(os.environ.get('FRAME_START', str(anim_start)))
scene.frame_end = int(os.environ.get('FRAME_END', str(anim_end)))
if TEST:
    scene.frame_end = scene.frame_start

START, END = anim_start, anim_end

# --- sky ---
world = bpy.data.worlds['World']
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.55, 0.75, 0.95, 1.0)
bg.inputs['Strength'].default_value = 1.0

def mat(name, color, rough=0.9):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    return m

def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj

def box(name, loc, scale, material, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return flat(o)

def cyl(name, loc, radius, depth, material, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                        location=loc, vertices=12)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return flat(o)

grass = mat('Grass', (0.38, 0.66, 0.32))
runway_mat = mat('Runway', (0.25, 0.25, 0.27), 0.95)
white = mat('White', (0.95, 0.95, 0.95))
red = mat('Red', (0.82, 0.16, 0.16))
dark = mat('Dark', (0.12, 0.12, 0.14))
glassm = mat('Glass', (0.35, 0.55, 0.72), 0.35)
concrete = mat('Concrete', (0.62, 0.62, 0.64))
trunkm = mat('Trunk', (0.42, 0.3, 0.18))
leafm = mat('Leaf', (0.26, 0.56, 0.3))
cloudm = mat('Cloud', (1.0, 1.0, 1.0), 1.0)
yellowm = mat('Yellow', (0.95, 0.8, 0.2))

# --- ground & runway ---
box('Ground', (0, 0, -0.5), (420, 420, 1), grass)
box('Runway', (0, 0, 0.05), (150, 12, 0.2), runway_mat)
for i in range(-7, 8):
    box(f'Dash{i}', (i * 10, 0, 0.16), (3.2, 0.7, 0.04), white)

# --- terminal ---
box('Terminal', (0, 30, 4), (36, 11, 8), concrete)
box('TermRoof', (0, 30, 8.6), (38, 13, 1.2), dark)
box('TermGlass', (0, 30, 5.6), (36.4, 11.4, 2.2), glassm)
box('TermDoor', (0, 24.3, 1.5), (6, 0.4, 3), dark)

# --- control tower ---
cyl('TowerShaft', (-28, 30, 8), 1.9, 16, concrete)
cyl('TowerCab', (-28, 30, 17.6), 3.2, 3.2, concrete)
cyl('TowerGlass', (-28, 30, 18.1), 3.3, 1.4, glassm)
cyl('TowerRoof', (-28, 30, 19.6), 3.4, 0.6, red)

# --- hangar ---
box('HangarWalls', (34, 32, 2.5), (18, 13, 5), yellowm)
bpy.ops.mesh.primitive_cylinder_add(radius=6.5, depth=18, location=(34, 32, 5),
                                    vertices=12)
roof = bpy.context.active_object
roof.name = 'HangarRoof'
roof.rotation_euler = (0, math.radians(90), 0)
roof.scale = (1, 1, 0.5)
roof.data.materials.append(red)
flat(roof)

# --- trees ---
random.seed(7)
for t in range(20):
    x = random.uniform(-100, 100)
    y = random.uniform(-100, 100)
    if abs(y) < 22:
        continue
    if -45 < x < 50 and 18 < y < 45:
        continue
    cyl(f'Trunk{t}', (x, y, 1), 0.32, 2, trunkm)
    bpy.ops.mesh.primitive_cone_add(radius1=2.1, depth=4.6, location=(x, y, 4.2),
                                    vertices=8)
    cone = bpy.context.active_object
    cone.name = f'Leaves{t}'
    cone.data.materials.append(leafm)
    flat(cone)

# --- clouds (drift slowly) ---
cloud_rig = []
for c in range(6):
    cx = -90 + c * 36 + random.uniform(-8, 8)
    cy = random.uniform(-70, 70)
    cz = random.uniform(30, 44)
    bpy.ops.object.empty_add(location=(cx, cy, cz))
    rig = bpy.context.active_object
    rig.name = f'CloudRig{c}'
    for s in range(4):
        r = random.uniform(1.8, 3.4)
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1, radius=r,
            location=(cx + random.uniform(-4, 4),
                      cy + random.uniform(-3, 3),
                      cz + random.uniform(-1, 1)))
        puff = bpy.context.active_object
        puff.data.materials.append(cloudm)
        puff.parent = rig
        flat(puff)
    rig.location = (cx, cy, cz)
    rig.keyframe_insert(data_path='location', frame=START)
    rig.location = (cx - 16, cy, cz)
    rig.keyframe_insert(data_path='location', frame=END)
    for fc in rig.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    cloud_rig.append(rig)

# --- the plane (built around local origin, faces +X) ---
bpy.ops.object.empty_add(location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = 'Plane'

cyl('Fuselage', (0, 0, 0), 1.1, 7.5, white, parent=plane)
bpy.context.active_object.rotation_euler = (0, math.radians(90), 0)

bpy.ops.mesh.primitive_cone_add(radius1=1.1, depth=2.2, location=(4.85, 0, 0),
                                vertices=12)
nose = bpy.context.active_object
nose.name = 'Nose'
nose.rotation_euler = (0, math.radians(90), 0)
nose.data.materials.append(white)
nose.parent = plane
flat(nose)

bpy.ops.mesh.primitive_cone_add(radius1=1.0, depth=2.0, location=(-4.7, 0, 0.2),
                                vertices=12)
tailcone = bpy.context.active_object
tailcone.name = 'TailCone'
tailcone.rotation_euler = (0, math.radians(-90), 0)
tailcone.data.materials.append(white)
tailcone.parent = plane
flat(tailcone)

box('Wing', (-0.3, 0, -0.15), (3.2, 10.5, 0.28), white, parent=plane)
box('WingletL', (-0.9, 5.15, 0.35), (0.9, 0.22, 1.1), red, parent=plane)
box('WingletR', (-0.9, -5.15, 0.35), (0.9, 0.22, 1.1), red, parent=plane)
box('HStab', (-3.9, 0, 0.5), (1.6, 4.6, 0.22), white, parent=plane)
box('VStab', (-3.9, 0, 1.5), (1.7, 0.24, 2.4), red, parent=plane)

for side in (1, -1):
    e = cyl(f'Engine{side}', (0.4, side * 2.6, -0.9), 0.55, 2.4, red,
            parent=plane)
    e.rotation_euler = (0, math.radians(90), 0)
    cyl(f'GearMain{side}', (-0.5, side * 1.8, -1.7), 0.3, 1.2, dark,
        parent=plane)
box('Cockpit', (3.3, 0, 0.95), (1.7, 1.5, 0.5), glassm, parent=plane)
cyl('GearNose', (3.2, 0, -1.7), 0.26, 1.2, dark, parent=plane)

# --- plane animation: takeoff roll, rotation, climb ---
plane.location = (-48, 0, 1.7)
plane.keyframe_insert(data_path='location', frame=START)
plane.location = (-20, 0, 1.7)
plane.keyframe_insert(data_path='location', frame=90)
plane.location = (14, 0, 2.5)
plane.keyframe_insert(data_path='location', frame=150)
plane.location = (52, 0, 20)
plane.keyframe_insert(data_path='location', frame=195)
plane.location = (86, 0, 36)
plane.keyframe_insert(data_path='location', frame=END)

plane.rotation_euler = (0, 0, 0)
plane.keyframe_insert(data_path='rotation_euler', frame=START)
plane.rotation_euler = (0, 0, 0)
plane.keyframe_insert(data_path='rotation_euler', frame=130)
plane.rotation_euler = (0, -0.20, 0)
plane.keyframe_insert(data_path='rotation_euler', frame=165)
plane.rotation_euler = (0.10, -0.20, 0)
plane.keyframe_insert(data_path='rotation_euler', frame=END)

# --- sun ---
bpy.ops.object.light_add(type='SUN', location=(0, 0, 20))
sun = bpy.context.active_object
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(55), 0, math.radians(-35))

# --- camera: gentle dolly tracking the plane ---
bpy.ops.object.empty_add(location=(0, 0, 2))
aim = bpy.context.active_object
aim.name = 'Aim'
bpy.ops.object.camera_add(location=(-22, -38, 9))
cam = bpy.context.active_object
cam.data.lens = 50
c = cam.constraints.new(type='TRACK_TO')
c.target = plane
c.track_axis = 'TRACK_NEGATIVE_Z'
c.up_axis = 'UP_Y'
scene.camera = cam
cam.location = (-22, -38, 9)
cam.keyframe_insert(data_path='location', frame=START)
cam.location = (38, -36, 13)
cam.keyframe_insert(data_path='location', frame=END)

# aim follows plane height a touch
aim.location = (0, 0, 2)
aim.keyframe_insert(data_path='location', frame=START)
aim.location = (40, 0, 20)
aim.keyframe_insert(data_path='location', frame=END)

if TEST:
    bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print('ANIM_DONE')

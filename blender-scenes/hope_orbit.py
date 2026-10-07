import bpy
import math
import os

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
anim_end = int(os.environ.get('ANIM_END', '72'))
scene.frame_start = int(os.environ.get('FRAME_START', str(anim_start)))
scene.frame_end = int(os.environ.get('FRAME_END', str(anim_end)))
if TEST:
    scene.frame_end = scene.frame_start

# --- world: dark studio ---
world = bpy.data.worlds['World']
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.012, 0.012, 0.018, 1.0)
bg.inputs['Strength'].default_value = 1.0

def track_to(obj, target):
    c = obj.constraints.new(type='TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'

def set_linear(obj):
    for fc in obj.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'

def principled(name, base_color, metallic=0.0, roughness=0.5,
               transmission=0.0, ior=1.45, emission=None,
               emission_strength=2.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*base_color, 1.0)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if 'Transmission Weight' in bsdf.inputs:
        bsdf.inputs['Transmission Weight'].default_value = transmission
    elif 'Transmission' in bsdf.inputs:
        bsdf.inputs['Transmission'].default_value = transmission
    if 'IOR' in bsdf.inputs:
        bsdf.inputs['IOR'].default_value = ior
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    return mat

gold = principled('Gold', (1.0, 0.62, 0.18), metallic=1.0, roughness=0.28)
glass = principled('Glass', (0.95, 0.98, 1.0), roughness=0.05,
               transmission=1.0, ior=1.45)
chrome = principled('Chrome', (0.9, 0.92, 0.95), metallic=1.0, roughness=0.08)
floor_mat = principled('Floor', (0.05, 0.05, 0.06), roughness=0.35)

# --- aim target ---
bpy.ops.object.empty_add(location=(0, 0, 1.0))
aim = bpy.context.active_object

# --- floor ---
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
floor = bpy.context.active_object
floor.data.materials.append(floor_mat)

# --- 3D text: HOPE ---
txt_curve = bpy.data.curves.new(type='FONT', name='HopeCurve')
txt_curve.body = 'HOPE'
txt_curve.align_x = 'CENTER'
txt_curve.align_y = 'CENTER'
txt_curve.size = 2.0
txt_curve.extrude = 0.35
txt_curve.bevel_depth = 0.06
txt_curve.bevel_resolution = 3
txt_obj = bpy.data.objects.new('HopeText', txt_curve)
bpy.context.collection.objects.link(txt_obj)
txt_obj.rotation_euler = (math.radians(90), 0, 0)
txt_obj.location = (-1.6, 0.4, 0.85)
txt_obj.data.materials.append(gold)

# --- glass sphere ---
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.85, location=(2.3, 0.9, 0.85),
                     segments=48, ring_count=32)
sphere = bpy.context.active_object
sphere.data.materials.append(glass)

# --- chrome torus (spins) ---
bpy.ops.mesh.primitive_torus_add(align='WORLD', location=(1.9, -2.0, 0.38),
                   major_radius=0.85, minor_radius=0.32,
                   major_segments=64, minor_segments=32)
torus = bpy.context.active_object
torus.data.materials.append(chrome)

# --- glowing icosphere (bobs) ---
bpy.ops.mesh.primitive_ico_sphere_add(radius=0.28, location=(-3.4, -1.6, 2.2),
                      subdivisions=3)
glow = bpy.context.active_object
glow_mat = principled('Glow', (0.1, 1.0, 0.4), emission=(0.1, 1.0, 0.4),
                     emission_strength=1.5)
glow.data.materials.append(glow_mat)

# --- lights ---
def area_light(name, location, power, size, color=(1, 1, 1)):
    bpy.ops.object.light_add(type='AREA', location=location)
    l = bpy.context.active_object
    l.name = name
    l.data.energy = power
    l.data.size = size
    l.data.color = color
    track_to(l, aim)
    return l

area_light('Key', (6, -6, 7), 1600, 6.0)
area_light('Rim', (-6, 5, 5), 900, 4.0, color=(0.65, 0.8, 1.0))
area_light('Fill', (0, -7, 2.5), 350, 5.0)

# --- camera on an orbit rig ---
bpy.ops.object.empty_add(location=(0, 0, 0))
rig = bpy.context.active_object
rig.name = 'CameraRig'

bpy.ops.object.camera_add(location=(6.8, -8.5, 3.6))
cam = bpy.context.active_object
cam.data.lens = 50
cam.parent = rig
track_to(cam, aim)
scene.camera = cam

START = anim_start
END = anim_end

# camera orbit: full 360 over the clip
rig.rotation_euler = (0, 0, 0)
rig.keyframe_insert(data_path='rotation_euler', frame=START)
rig.rotation_euler = (0, 0, math.radians(360))
rig.keyframe_insert(data_path='rotation_euler', frame=END)
set_linear(rig)

# torus spin: two full turns
torus.rotation_euler = (0, 0, 0)
torus.keyframe_insert(data_path='rotation_euler', frame=START)
torus.rotation_euler = (0, 0, math.radians(720))
torus.keyframe_insert(data_path='rotation_euler', frame=END)
set_linear(torus)

# glow sphere bob
glow.location = (-3.4, -1.6, 2.2)
glow.keyframe_insert(data_path='location', frame=START)
glow.location = (-3.4, -1.6, 2.9)
glow.keyframe_insert(data_path='location', frame=(START   END) // 2)
glow.location = (-3.4, -1.6, 2.2)
glow.keyframe_insert(data_path='location', frame=END)

if TEST:
    bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print('ANIM_DONE')

import bpy
import math
import os

# Realistic A350 takeoff using a real free 3D asset.
# Aircraft model: FlightGear A350XWB (FGMEMBERS/A350XWB on GitHub), GPL2+.
# Converted from AC3D to OBJ locally; textures ship alongside this script.
TEST = os.environ.get('TEST') == '1'

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
SAMPLES = int(os.environ.get('SAMPLES', '64'))
scene.cycles.samples = SAMPLES
scene.cycles.device = 'CPU'
scene.cycles.use_denoising = True
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
outdir = os.environ.get('OUTPUT_DIR', 'frames')
os.makedirs(outdir, exist_ok=True)
scene.render.filepath = os.path.join(outdir, 'frame_####')

scene.render.fps = 24
anim_start = int(os.environ.get('ANIM_START', '1'))
anim_end = int(os.environ.get('ANIM_END', '240'))
scene.frame_start = int(os.environ.get('FRAME_START', str(anim_start)))
scene.frame_end = int(os.environ.get('FRAME_END', str(anim_end)))
if TEST:
    scene.frame_end = scene.frame_start
START, END = anim_start, anim_end

here = os.path.dirname(os.path.abspath(__file__))

# --- world: HDRI sky ---
world = bpy.data.worlds['World']
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
wout = nt.nodes.new('ShaderNodeOutputWorld')
wbg = nt.nodes.new('ShaderNodeBackground')
wenv = nt.nodes.new('ShaderNodeTexEnvironment')
hdri_path = os.environ.get('HDRI_PATH',
                            os.path.join(here, 'sky.hdr'))
wenv.image = bpy.data.images.load(hdri_path)
wbg.inputs['Strength'].default_value = 0.85
nt.links.new(wenv.outputs['Color'], wbg.inputs['Color'])
nt.links.new(wbg.outputs['Background'], wout.inputs['Surface'])

# --- materials (ground only; the aircraft brings its own) ---
def principled(name, **kw):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    for k, v in kw.items():
        if k in bsdf.inputs:
            inp = bsdf.inputs[k]
            if hasattr(inp.default_value, '__len__'):
                inp.default_value = (*v, 1.0) if len(v) == 3 else v
            else:
                inp.default_value = v
    return m

grass = principled('Grass', **{'Base Color': (0.36, 0.60, 0.30),
                               'Roughness': 1.0})
tarmac = principled('Tarmac', **{'Base Color': (0.30, 0.30, 0.31),
                                 'Roughness': 0.95})
white = principled('White', **{'Base Color': (0.92, 0.92, 0.92),
                               'Roughness': 0.85})
concrete = principled('Concrete', **{'Base Color': (0.60, 0.60, 0.62),
                                     'Roughness': 0.9})
glass_dark = principled('GlassDark', **{'Base Color': (0.03, 0.04, 0.06),
                                        'Roughness': 0.06, 'Metallic': 0.25})

def box(name, loc, scale, material, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    for p in o.data.polygons:
        p.use_smooth = False
    return o

# --- the real A350 ---
bpy.ops.object.empty_add(location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = 'Plane'

bpy.ops.wm.obj_import(filepath=os.path.join(here, 'a350xwb.obj'))
a350 = bpy.context.selected_objects[0]
a350.name = 'A350'
# Native model: X 0 (nose) -> 67 (tail), Y up, Z span, meters.
# The importer leaves a Y-up->Z-up rotation on the object; combine it with
# a 180-degree Z turn so the nose faces +X. (Overwriting rotation_euler
# outright destroys the importer's conversion and rolls the plane 90 deg.)
from mathutils import Matrix
R = Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Rotation(math.pi / 2, 4, 'X')
a350.rotation_euler = R.to_euler()
# Half scale to match the airport built for a ~30-unit aircraft, centered
# with the wheels at local z=0.
a350.scale = (0.5, 0.5, 0.5)
a350.location = (16.75, 0, 2.45)
a350.parent = plane

# --- plane animation: takeoff roll, rotation, climb ---
plane.location = (-62, 0, 0.15)
plane.keyframe_insert(data_path='location', frame=START)
plane.location = (-28, 0, 0.15)
plane.keyframe_insert(data_path='location', frame=80)
plane.location = (4, 0, 1.5)
plane.keyframe_insert(data_path='location', frame=120)
plane.location = (44, 0, 20.5)
plane.keyframe_insert(data_path='location', frame=170)
plane.location = (108, 0, 46.5)
plane.keyframe_insert(data_path='location', frame=END)

plane.rotation_euler = (0, 0, 0)
plane.keyframe_insert(data_path='rotation_euler', frame=START)
plane.rotation_euler = (0, 0, 0)
plane.keyframe_insert(data_path='rotation_euler', frame=100)
plane.rotation_euler = (0, -0.17, 0)
plane.keyframe_insert(data_path='rotation_euler', frame=140)
plane.rotation_euler = (0.07, -0.17, 0)
plane.keyframe_insert(data_path='rotation_euler', frame=END)

# --- ground: airport ---
box('Ground', (0, 0, -0.5), (700, 700, 1), grass)
box('Runway', (0, 0, 0.05), (230, 14, 0.2), tarmac)
for i in range(-11, 12):
    box(f'RWDash{i}', (i * 10, 0, 0.16), (3.4, 0.8, 0.04), white)
for s in (-1, 1):
    for i in range(6):
        box(f'TD{s}{i}', (-52 + i * 7, s * 3.4, 0.16), (3.4, 1.1, 0.04),
            white)
box('Taxiway', (0, 32, 0.03), (180, 8, 0.12), tarmac)
box('TermA', (-20, 62, 5), (46, 14, 10), concrete)
box('TermB', (34, 64, 4), (26, 12, 8), concrete)
box('Tower', (-52, 60, 11), (5, 5, 22), concrete)
box('TowerCab', (-52, 60, 23), (8, 8, 4), glass_dark)

# --- sun for crisp shadows ---
bpy.ops.object.light_add(type='SUN', location=(0, 0, 30))
sun = bpy.context.active_object
sun.data.energy = 2.5
sun.rotation_euler = (math.radians(52), 0, math.radians(-38))

# --- camera: front three-quarter tracking shot, stays ahead and to the
# side so the nose and both wings are visible and the orientation is clear
bpy.ops.object.camera_add(location=(-55, -70, 8))
cam = bpy.context.active_object
cam.data.lens = 55
c = cam.constraints.new(type='TRACK_TO')
c.target = plane
c.track_axis = 'TRACK_NEGATIVE_Z'
c.up_axis = 'UP_Y'
scene.camera = cam
cam.location = (-55, -70, 8)
cam.keyframe_insert(data_path='location', frame=START)
cam.location = (120, -70, 14)
cam.keyframe_insert(data_path='location', frame=END)

if TEST:
    # check frames render tiny and fast; the final render stays full quality
    scene.render.resolution_x = 480
    scene.render.resolution_y = 270
    scene.cycles.samples = 16
    scene.frame_set(scene.frame_start)
    bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print('ANIM_DONE')

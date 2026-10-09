import bpy
import math
import os
import bmesh

TEST = os.environ.get('TEST') == '1'

# --- clean slate ---
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

# --- world: HDRI sky ---
world = bpy.data.worlds['World']
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
wout = nt.nodes.new('ShaderNodeOutputWorld')
wbg = nt.nodes.new('ShaderNodeBackground')
wenv = nt.nodes.new('ShaderNodeTexEnvironment')
hdri_path = os.environ.get(
    'HDRI_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sky.hdr'))
wenv.image = bpy.data.images.load(hdri_path)
wbg.inputs['Strength'].default_value = 0.85
nt.links.new(wenv.outputs['Color'], wbg.inputs['Color'])
nt.links.new(wbg.outputs['Background'], wout.inputs['Surface'])

# --- materials ---
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

paint = principled('Paint', **{'Base Color': (0.93, 0.93, 0.94),
                               'Roughness': 0.32, 'Metallic': 0.0,
                               'Coat Weight': 0.7, 'Coat Roughness': 0.25})
glass_dark = principled('GlassDark', **{'Base Color': (0.03, 0.04, 0.06),
                                        'Roughness': 0.06, 'Metallic': 0.25})
metal = principled('Metal', **{'Base Color': (0.72, 0.75, 0.78),
                               'Roughness': 0.35, 'Metallic': 1.0})
dark = principled('Dark', **{'Base Color': (0.05, 0.05, 0.06),
                             'Roughness': 0.9})
tire = principled('Tire', **{'Base Color': (0.08, 0.08, 0.09),
                             'Roughness': 0.95})
accent = principled('Accent', **{'Base Color': (0.10, 0.25, 0.55),
                                 'Roughness': 0.4, 'Coat Weight': 0.5,
                                 'Coat Roughness': 0.3})
grass = principled('Grass', **{'Base Color': (0.36, 0.60, 0.30),
                               'Roughness': 1.0})
tarmac = principled('Tarmac', **{'Base Color': (0.30, 0.30, 0.31),
                                 'Roughness': 0.95})
white = principled('White', **{'Base Color': (0.92, 0.92, 0.92),
                               'Roughness': 0.85})
concrete = principled('Concrete', **{'Base Color': (0.60, 0.60, 0.62),
                                     'Roughness': 0.9})

def finish_mesh(o, smooth=True, subdiv=0):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    if subdiv:
        mod = o.modifiers.new('Subdiv', 'SUBSURF')
        mod.levels = subdiv
        mod.render_levels = subdiv
    return o

def lathe(name, profile, steps=36, material=None, subdiv=2):
    bm = bmesh.new()
    verts = [bm.verts.new((x, 0.0, r)) for x, r in profile]
    bm.verts.ensure_lookup_table()
    edges = [bm.edges.new((verts[i], verts[i + 1]))
             for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(1, 0, 0),
                   angle=math.pi * 2, steps=steps)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    me = bpy.data.meshes.new(name + 'Mesh')
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if material:
        o.data.materials.append(material)
    return finish_mesh(o, smooth=True, subdiv=subdiv)

def wing_mesh(name, span, root_c, tip_c, root_t, tip_t, sweep_deg,
              dihedral_deg, stations=8, material=None, subdiv=2):
    sw = math.tan(math.radians(sweep_deg))
    dh = math.tan(math.radians(dihedral_deg))
    bm = bmesh.new()
    rows = []
    for i in range(stations):
        f = i / (stations - 1)
        y = span * f
        c = root_c + (tip_c - root_c) * f
        xle = -sw * abs(span) * f
        z = dh * abs(span) * f
        t = root_t + (tip_t - root_t) * f
        pts = [(xle, y, z + t / 2), (xle + c, y, z + t * 0.26),
               (xle + c, y, z - t * 0.26), (xle, y, z - t / 2)]
        rows.append([bm.verts.new(p) for p in pts])
    bm.verts.ensure_lookup_table()
    for i in range(stations - 1):
        for j in range(4):
            j2 = (j + 1) % 4
            bm.faces.new((rows[i][j], rows[i][j2],
                          rows[i + 1][j2], rows[i + 1][j]))
    bm.faces.new((rows[0][0], rows[0][1], rows[0][2], rows[0][3]))
    bm.faces.new((rows[-1][0], rows[-1][3],
                  rows[-1][2], rows[-1][1]))
    me = bpy.data.meshes.new(name + 'Mesh')
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if material:
        o.data.materials.append(material)
    return finish_mesh(o, smooth=True, subdiv=subdiv)

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

# --- the A350 (faces +X), built around local origin ---
bpy.ops.object.empty_add(location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = 'Plane'

# fuselage: one clean lathed body
profile = [(-15, 0.12), (-13.5, 0.7), (-11, 1.25), (-7, 1.48), (-2, 1.52),
           (4, 1.52), (8, 1.45), (11, 1.18), (13, 0.78), (14.2, 0.3),
           (14.8, 0.04)]
fuse = lathe('Fuselage', profile, steps=40, material=paint, subdiv=2)
fuse.parent = plane

# cockpit visor (dark bandit mask, embedded into the nose)
visor = box('Visor', (11.9, 0, 0.8), (2.0, 1.7, 0.5), glass_dark,
            parent=plane)
visor.rotation_euler = (0, math.radians(-14), 0)

# passenger window strips
for side in (1, -1):
    box(f'WinStrip{side}', (1.5, side * 1.50, 0.55), (15, 0.08, 0.30),
        glass_dark, parent=plane)

# wings
for side in (1, -1):
    w = wing_mesh(f'Wing{side}', side * 15.5, 5.2, 1.5, 0.55, 0.22, 26, 4,
                  material=paint, subdiv=2)
    w.location = (-0.5, side * 1.1, -0.1)
    w.parent = plane
    # curved winglet
    wl = wing_mesh(f'Winglet{side}', 2.6, 1.5, 0.65, 0.20, 0.12, 30, 0,
                   stations=6, material=accent, subdiv=1)
    wl.rotation_euler = (math.radians(90) * side, 0, math.radians(-8))
    tip_x = -0.5 - math.tan(math.radians(26)) * 15.5
    tip_z = -0.1 + math.tan(math.radians(4)) * 15.5
    wl.location = (tip_x + 0.4, side * (1.1 + 15.5), tip_z)
    wl.parent = plane

# horizontal stabilizers
for side in (1, -1):
    hs = wing_mesh(f'HStab{side}', side * 5.5, 2.6, 1.0, 0.32, 0.14, 30, 5,
                   stations=6, material=paint, subdiv=1)
    hs.location = (-12.6, side * 0.9, 0.9)
    hs.parent = plane

# vertical stabilizer
vs = wing_mesh('VStab', 5.2, 3.4, 1.2, 0.4, 0.18, 38, 0, stations=6,
               material=paint, subdiv=1)
vs.rotation_euler = (math.radians(90), 0, 0)
vs.location = (-12.8, 0, 1.2)
vs.parent = plane
fin_tip = box('FinTip', (-16.6, 0, 6.1), (0.9, 0.3, 0.9), accent,
              parent=plane)

# engines: lathed nacelles with dark intakes
for side in (1, -1):
    nac = lathe(f'Nacelle{side}',
                [(-2.2, 0.85), (-1.4, 1.12), (0.2, 1.16), (1.6, 1.02),
                 (2.2, 0.72)],
                steps=28, material=paint, subdiv=2)
    nac.location = (1.8, side * 5.2, -1.5)
    nac.parent = plane
    lip = lathe(f'IntakeLip{side}', [(-2.25, 0.98), (-2.0, 1.14)],
                steps=28, material=metal, subdiv=1)
    lip.location = (1.8, side * 5.2, -1.5)
    lip.parent = plane
    bpy.ops.mesh.primitive_circle_add(radius=0.88, location=(0.15, side * 5.2,
                                                             -1.5),
                                      vertices=24)
    fan = bpy.context.active_object
    fan.name = f'Fan{side}'
    fan.rotation_euler = (0, math.radians(90), 0)
    fan.data.materials.append(dark)
    fan.parent = plane
    box(f'Pylon{side}', (0.6, side * 5.2, -0.5), (2.4, 0.35, 1.2), paint,
        parent=plane)

# landing gear (extended: just lifted off)
def gear(name, x, y):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.14, depth=2.2,
                                        location=(x, y, -2.2), vertices=10)
    oleo = bpy.context.active_object
    oleo.name = name + 'Oleo'
    oleo.data.materials.append(metal)
    oleo.parent = plane
    for p in oleo.data.polygons:
        p.use_smooth = False
    bpy.ops.mesh.primitive_cylinder_add(radius=0.42, depth=0.3,
                                        location=(x, y, -3.3), vertices=14)
    wheel = bpy.context.active_object
    wheel.name = name + 'Wheel'
    wheel.rotation_euler = (math.radians(90), 0, 0)
    wheel.data.materials.append(tire)
    wheel.parent = plane
    for p in wheel.data.polygons:
        p.use_smooth = False

gear('Nose', 10.5, 0)
gear('MainL', -1.5, 2.4)
gear('MainR', -1.5, -2.4)

# --- plane animation: takeoff roll, rotation, climb ---
plane.location = (-62, 0, 3.6)
plane.keyframe_insert(data_path='location', frame=START)
plane.location = (-28, 0, 3.6)
plane.keyframe_insert(data_path='location', frame=80)
plane.location = (4, 0, 5.0)
plane.keyframe_insert(data_path='location', frame=120)
plane.location = (44, 0, 24)
plane.keyframe_insert(data_path='location', frame=170)
plane.location = (108, 0, 50)
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
# distant terminal blocks
box('TermA', (-20, 62, 5), (46, 14, 10), concrete)
box('TermB', (34, 64, 4), (26, 12, 8), concrete)
box('Tower', (-52, 60, 11), (5, 5, 22), concrete)
box('TowerCab', (-52, 60, 23), (8, 8, 4), glass_dark)

# --- sun for crisp shadows ---
bpy.ops.object.light_add(type='SUN', location=(0, 0, 30))
sun = bpy.context.active_object
sun.data.energy = 2.5
sun.rotation_euler = (math.radians(52), 0, math.radians(-38))

# --- camera: cinematic tracking dolly ---
bpy.ops.object.camera_add(location=(-38, -58, 9))
cam = bpy.context.active_object
cam.data.lens = 55
c = cam.constraints.new(type='TRACK_TO')
c.target = plane
c.track_axis = 'TRACK_NEGATIVE_Z'
c.up_axis = 'UP_Y'
scene.camera = cam
cam.location = (-38, -58, 9)
cam.keyframe_insert(data_path='location', frame=START)
cam.location = (62, -62, 24)
cam.keyframe_insert(data_path='location', frame=END)

if TEST:
    scene.frame_set(scene.frame_start)
    bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print('ANIM_DONE')

import bpy, bmesh, os, sys, json, math, traceback
from mathutils import Vector, Matrix

SCRATCH = r"C:\Users\wable\AppData\Local\Temp\claude\C--\d9a608f1-ec6e-4804-9a41-9f3b76117670\scratchpad"
OUT_DIR = r"C:\Users\wable\clawb-world\obs\avatar"

MIXAMO_MAP = {
    "hips": "mixamorig:Hips", "spine": "mixamorig:Spine", "chest": "mixamorig:Spine1",
    "upperChest": "mixamorig:Spine2", "neck": "mixamorig:Neck", "head": "mixamorig:Head",
    "leftShoulder": "mixamorig:LeftShoulder", "leftUpperArm": "mixamorig:LeftArm",
    "leftLowerArm": "mixamorig:LeftForeArm", "leftHand": "mixamorig:LeftHand",
    "rightShoulder": "mixamorig:RightShoulder", "rightUpperArm": "mixamorig:RightArm",
    "rightLowerArm": "mixamorig:RightForeArm", "rightHand": "mixamorig:RightHand",
    "leftUpperLeg": "mixamorig:LeftUpLeg", "leftLowerLeg": "mixamorig:LeftLeg",
    "leftFoot": "mixamorig:LeftFoot", "leftToes": "mixamorig:LeftToeBase",
    "rightUpperLeg": "mixamorig:RightUpLeg", "rightLowerLeg": "mixamorig:RightLeg",
    "rightFoot": "mixamorig:RightFoot", "rightToes": "mixamorig:RightToeBase",
}

def log(*a):
    print("[BUILD]", *a)
    sys.stdout.flush()

def clean_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.actions):
        for item in list(coll):
            if item.users == 0:
                coll.remove(item)

def world_bbox():
    mins = Vector((1e9,) * 3); maxs = Vector((-1e9,) * 3)
    deps = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        mw = ev.matrix_world
        for v in me.vertices:
            w = mw @ v.co
            mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
        ev.to_mesh_clear()
    return mins, maxs

def strip_anim_rest_pose():
    for ob in bpy.data.objects:
        if ob.animation_data:
            ob.animation_data_clear()
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)
    for ob in bpy.data.objects:
        if ob.type == 'ARMATURE':
            for pb in ob.pose.bones:
                pb.location = (0, 0, 0)
                pb.rotation_quaternion = (1, 0, 0, 0)
                pb.rotation_euler = (0, 0, 0)
                pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()

def get_armature():
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE')

def align_arm_chain_to_t(arm, side_prefix, direction):
    """Rotate Arm/ForeArm/Hand pose bones so the chain points along `direction` (world)."""
    for bone_name in (side_prefix + "Arm", side_prefix + "ForeArm", side_prefix + "Hand"):
        pb = arm.pose.bones.get("mixamorig:" + bone_name)
        if pb is None:
            continue
        mw = arm.matrix_world
        head = mw @ pb.head
        tail = mw @ pb.tail
        cur = (tail - head).normalized()
        rot = cur.rotation_difference(direction)
        pbm = mw @ pb.matrix
        loc = pbm.to_translation()
        M = Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ Matrix.Translation(-loc) @ pbm
        pb.matrix = mw.inverted() @ M
        bpy.context.view_layer.update()

def bake_pose_to_rest(arm):
    """Bake current pose into meshes and apply pose as new rest pose."""
    deps = bpy.context.evaluated_depsgraph_get()
    for ob in [o for o in bpy.data.objects if o.type == 'MESH']:
        has_arm_mod = any(m.type == 'ARMATURE' for m in ob.modifiers)
        if not has_arm_mod:
            continue
        ev = ob.evaluated_get(deps)
        baked = bpy.data.meshes.new_from_object(ev)
        old = ob.data
        ob.data = baked
        ob.modifiers.clear()
        mod = ob.modifiers.new("Armature", 'ARMATURE')
        mod.object = arm
        if old.users == 0:
            bpy.data.meshes.remove(old)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()

def scale_and_ground(target_height):
    strip = [o for o in bpy.data.objects]
    mins, maxs = world_bbox()
    height = maxs.z - mins.z
    scale = target_height / height
    roots = [o for o in bpy.data.objects if o.parent is None]
    for r in roots:
        r.scale = [s * scale for s in r.scale]
    bpy.context.view_layer.update()
    mins, maxs = world_bbox()
    for r in roots:
        r.location.z -= mins.z
        r.location.x -= (mins.x + maxs.x) / 2
        r.location.y -= (mins.y + maxs.y) / 2
    bpy.context.view_layer.update()
    for ob in bpy.data.objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = get_armature()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    log("scaled; bbox now", [round(v, 3) for v in world_bbox()[0]], [round(v, 3) for v in world_bbox()[1]])

def make_smile_image(name="MouthSmile", w=160, h=64, style="smile"):
    img = bpy.data.images.new(name, width=w, height=h, alpha=True)
    px = [0.0] * (w * h * 4)
    if style == "rounded":
        # thin flat black line (radbro's closed-mouth style), centered —
        # taller reads as "open"; 0.07h matches the official art's line mouth
        rw, rh = w * 0.17, h * 0.07
        cx, cy = w / 2, h / 2
        for y in range(h):
            for x in range(w):
                dx = max(0.0, abs(x - cx) - rw + rh)
                dy = abs(y - cy)
                if (dx * dx + dy * dy) ** 0.5 <= rh:
                    i = (y * w + x) * 4
                    px[i] = px[i+1] = px[i+2] = 0.02
                    px[i+3] = 1.0
        img.pixels = px
        img.pack()
        return img
    cx, half_w, base_y = w / 2, w * 0.30, h * 0.55
    for x in range(w):
        t = (x - cx) / half_w
        if abs(t) > 1.0:
            continue
        # image origin is bottom-left; smile dips down in the middle
        y_c = base_y + (t * t) * h * 0.22
        for y in range(h):
            d = abs(y - (h - y_c))
            if d <= 2.5:
                i = (y * w + x) * 4
                a = max(0.0, 1.0 - max(0.0, d - 1.5))
                px[i] = px[i + 1] = px[i + 2] = 0.0
                px[i + 3] = a
    img.pixels = px
    img.pack()
    return img

def add_mouth_patch(arm, body, center, size_w, size_h, style="smile"):
    """Mouth as a patch of the actual head surface: duplicate the front-facing
    faces around `center`, planar-project fresh UVs over the patch rect, and
    float the geometry 2 mm off the skin. It hugs the head's curve and deforms
    with the original skin weights, so it never looks detached or clips."""
    patch = body.copy()
    patch.data = body.data.copy()
    patch.name = "MouthPatch"
    patch.data.name = "MouthPatch"
    bpy.context.collection.objects.link(patch)

    bm = bmesh.new()
    bm.from_mesh(patch.data)
    doomed = []
    for f in bm.faces:
        fc = f.calc_center_median()
        # asymmetric band: plenty of room below for the open mouth, but a
        # tight cut above so faces on protruding brows/nose ridges (whose
        # polygons dip into the art zone) never get painted
        keep = (abs(fc.x - center.x) < size_w * 0.75
                and -1.5 * size_h < (fc.z - center.z) < 0.45 * size_h
                and fc.y < 0 and f.normal.y < -0.2)
        if not keep:
            doomed.append(f)
        else:
            f.material_index = 0
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    uvl = bm.loops.layers.uv.active
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv.x = (l.vert.co.x - center.x) / size_w + 0.5
            l[uvl].uv.y = (l.vert.co.z - center.z) / size_h + 0.5
    bm.to_mesh(patch.data)
    bm.free()
    log("MouthPatch faces:", len(patch.data.polygons))
    if len(patch.data.polygons) == 0:
        raise RuntimeError("MouthPatch empty")

    me = patch.data
    me.calc_loop_triangles()
    for v in me.vertices:
        v.co = v.co + v.normal * 0.002

    mat = bpy.data.materials.new("Mouth")
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Roughness"].default_value = 1.0
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = make_smile_image(style=style)
    tex.extension = 'EXTEND'  # clamp — planar UVs run past 0..1 on the patch edges
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    me.materials.clear()
    me.materials.append(mat)
    return patch

def setup_vrm(arm, title):
    ext = arm.data.vrm_addon_extension
    try:
        ext.spec_version = "0.0"
    except Exception as e:
        log("spec_version set failed:", e)
    hb = ext.vrm0.humanoid.human_bones
    for bone_type, bone_name in MIXAMO_MAP.items():
        if bone_name not in arm.data.bones:
            log("missing bone", bone_name)
            continue
        entry = next((h for h in hb if h.bone == bone_type), None)
        if entry is None:
            entry = hb.add()
            entry.bone = bone_type
        entry.node.bone_name = bone_name
    meta = ext.vrm0.meta
    meta.title = title
    meta.author = "wable"
    meta.version = "1.0"

def add_blink_group(arm, mesh_obj, key_name):
    ext = arm.data.vrm_addon_extension
    bsm = ext.vrm0.blend_shape_master
    g = bsm.blend_shape_groups.add()
    g.name = "Blink"
    g.preset_name = "blink"
    b = g.binds.add()
    b.mesh.mesh_object_name = mesh_obj.name
    b.index = key_name
    b.weight = 1.0

def export_vrm(arm, out_path):
    bpy.ops.object.select_all(action='SELECT')
    try:
        bpy.ops.export_scene.vrm(filepath=out_path, armature_object_name=arm.name)
    except TypeError:
        bpy.ops.export_scene.vrm(filepath=out_path)
    log("EXPORTED:", out_path, os.path.getsize(out_path), "bytes")

# ============================== CLAWB ==============================
def build_clawb():
    clean_scene()
    bpy.ops.import_scene.fbx(filepath=r"C:\Users\wable\clawb-world\public\assets\lawbidle.fbx")
    strip_anim_rest_pose()
    arm = get_armature()

    # T-pose the claw arms, then bake as the new rest pose
    align_arm_chain_to_t(arm, "Left", Vector((1, 0, 0)))
    align_arm_chain_to_t(arm, "Right", Vector((-1, 0, 0)))
    bake_pose_to_rest(arm)
    log("clawb T-posed")

    scale_and_ground(1.0)
    mins, maxs = world_bbox()
    H = maxs.z - mins.z
    W = maxs.x - mins.x

    body = next(o for o in bpy.data.objects if o.type == 'MESH')

    # the jeans mesh includes dark inner-lining/torn-flap faces (mapped to a
    # near-black part of the Pants texture). They hang naturally mid-animation
    # in the game but jut out in a still rest pose — delete them.
    import numpy as np
    pants_slot = next((i for i, m in enumerate(body.data.materials) if m and m.name.startswith("Pants")), None)
    if pants_slot is not None:
        pmat = body.data.materials[pants_slot]
        pimg = next((n.image for n in pmat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
        if pimg:
            pw, ph = pimg.size
            parr = np.empty(pw * ph * 4, dtype=np.float32)
            pimg.pixels.foreach_get(parr)
            pgrid = parr.reshape(ph, pw, 4)
            bmp = bmesh.new()
            bmp.from_mesh(body.data)
            uvlp = bmp.loops.layers.uv.active
            doomed = []
            for f in bmp.faces:
                if f.material_index != pants_slot:
                    continue
                bright = []
                for l in f.loops:
                    x = min(pw - 1, max(0, int((l[uvlp].uv.x % 1.0) * pw)))
                    y = min(ph - 1, max(0, int((l[uvlp].uv.y % 1.0) * ph)))
                    bright.append(float(pgrid[y, x, :3].mean()))
                if max(bright) < 0.12:
                    doomed.append(f)
            log("clawb dark pants faces removed:", len(doomed))
            bmesh.ops.delete(bmp, geom=doomed, context='FACES')
            bmp.to_mesh(body.data)
            bmp.free()

    eyes_slot = next(i for i, m in enumerate(body.data.materials) if m and m.name.startswith("Eyes"))
    eyes_mat = body.data.materials[eyes_slot]

    # locate the Eyes texture image
    eyes_img = None
    for n in eyes_mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            eyes_img = n.image
            break
    ew, eh = eyes_img.size
    log("eyes image", eyes_img.name, ew, eh)

    # --- closed-eye morph texture: find eyeball pixel clusters, paint lids ---
    px = list(eyes_img.pixels)
    def rgba(x, y):
        i = (y * ew + x) * 4
        return px[i], px[i + 1], px[i + 2], px[i + 3]
    mask = [False] * (ew * eh)
    reds = []
    for y in range(eh):
        for x in range(ew):
            r, g, b, a = rgba(x, y)
            if a < 0.5:
                continue
            near_white = r > 0.88 and g > 0.88 and b > 0.88
            red_dom = r > 0.35 and r > g * 1.6 and r > b * 1.6
            if red_dom:
                reds.append((r, g, b))
            dark = (r + g + b) / 3 < 0.35
            green_dom = g > 0.3 and g > r * 1.2 and g > b * 1.2
            if (dark or green_dom) and not near_white and not red_dom:
                mask[y * ew + x] = True
    lid_rgb = (0.03, 0.03, 0.03)  # black lids
    # connected components (4-neighbour BFS)
    seen = [False] * (ew * eh)
    clusters = []
    for i in range(ew * eh):
        if not mask[i] or seen[i]:
            continue
        stack = [i]
        seen[i] = True
        cells = []
        while stack:
            j = stack.pop()
            cells.append(j)
            jx, jy = j % ew, j // ew
            for nx, ny in ((jx+1, jy), (jx-1, jy), (jx, jy+1), (jx, jy-1)):
                if 0 <= nx < ew and 0 <= ny < eh:
                    k = ny * ew + nx
                    if mask[k] and not seen[k]:
                        seen[k] = True
                        stack.append(k)
        if len(cells) > 300:
            xs = [c % ew for c in cells]; ys = [c // ew for c in cells]
            clusters.append((len(cells), min(xs), min(ys), max(xs), max(ys)))
    clusters.sort(reverse=True)
    clusters = clusters[:2]
    log("eye clusters:", clusters)
    if len(clusters) < 1:
        raise RuntimeError("no eye clusters found")

    morph = eyes_img.copy()
    morph.name = "EyesClosed"
    mpx = list(morph.pixels)
    for _, x0, y0, x1, y1 in clusters:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (x1 - x0) / 2 + 4, (y1 - y0) / 2 + 4
        for y in range(max(0, y0 - 6), min(eh, y1 + 7)):
            for x in range(max(0, x0 - 6), min(ew, x1 + 7)):
                dx, dy = (x - cx) / rx, (y - cy) / ry
                if dx * dx + dy * dy <= 1.0:
                    i = (y * ew + x) * 4
                    mpx[i], mpx[i+1], mpx[i+2], mpx[i+3] = lid_rgb[0], lid_rgb[1], lid_rgb[2], 1.0
        # closed-lid line: dark curve across the middle
        for x in range(int(cx - rx * 0.85), int(cx + rx * 0.85)):
            t = (x - cx) / rx
            yl = cy + (t * t) * ry * 0.25
            for y in range(int(yl - 3), int(yl + 4)):
                if 0 <= x < ew and 0 <= y < eh:
                    i = (y * ew + x) * 4
                    mpx[i], mpx[i+1], mpx[i+2], mpx[i+3] = 0.05, 0.02, 0.02, 1.0
    morph.pixels = mpx
    morph.pack()

    # --- EyePatch object: duplicate of the Eyes-material faces ---
    patch = body.copy()
    patch.data = body.data.copy()
    patch.name = "EyePatch"
    patch.data.name = "EyePatch"
    bpy.context.collection.objects.link(patch)
    bm = bmesh.new()
    bm.from_mesh(patch.data)
    doomed = [f for f in bm.faces if f.material_index != eyes_slot]
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    bm.to_mesh(patch.data)
    bm.free()
    log("EyePatch faces:", len(patch.data.polygons))
    if len(patch.data.polygons) == 0:
        raise RuntimeError("EyePatch empty")

    pm = bpy.data.materials.new("EyeMorph")
    pm.use_nodes = True
    bsdf = next(n for n in pm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Roughness"].default_value = 1.0
    tn = pm.node_tree.nodes.new('ShaderNodeTexImage')
    tn.image = morph
    pm.node_tree.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
    patch.data.materials.clear()
    patch.data.materials.append(pm)

    me = patch.data
    me.calc_loop_triangles()
    vnorms = [v.normal.copy() for v in me.vertices]
    orig = [v.co.copy() for v in me.vertices]
    for v, n in zip(me.vertices, vnorms):
        v.co = v.co - n * 0.010
    patch.shape_key_add(name="Basis", from_mix=False)
    key = patch.shape_key_add(name="Blink", from_mix=False)
    for i, (p, n) in enumerate(zip(orig, vnorms)):
        key.data[i].co = p + n * 0.0015

    # --- mouth quad on the carapace, below the eyes ---
    deps = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(deps)
    bme = ev.to_mesh()
    eye_verts = set()
    for poly in bme.polygons:
        if poly.material_index == eyes_slot:
            for vi in poly.vertices:
                eye_verts.add(vi)
    eye_z = sum(bme.vertices[vi].co.z for vi in eye_verts) / max(1, len(eye_verts))
    mouth_z = eye_z - 0.145 * H
    front_y = 1e9
    for v in bme.vertices:
        if abs(v.co.x) < 0.12 * W and abs(v.co.z - mouth_z) < 0.06 * H:
            front_y = min(front_y, v.co.y)
    ev.to_mesh_clear()
    log("clawb eye_z", round(eye_z, 3), "mouth_z", round(mouth_z, 3), "front_y", round(front_y, 3))
    add_mouth_patch(arm, body, Vector((0, 0, mouth_z)), 0.20 * W, 0.09 * W)

    setup_vrm(arm, "Clawb")
    add_blink_group(arm, patch, "Blink")
    export_vrm(arm, os.path.join(OUT_DIR, "Clawb.vrm"))
    print("===CLAWB_OK===")

# ============================== RADBRO ==============================
def build_radbro():
    clean_scene()
    bpy.ops.import_scene.gltf(filepath=os.path.join(SCRATCH, "Radbro-noktx.glb"))
    strip_anim_rest_pose()
    arm = get_armature()

    # junk: icosphere + empties + any mesh without armature deform
    for ob in list(bpy.data.objects):
        if ob.type == 'EMPTY':
            bpy.data.objects.remove(ob, do_unlink=True)
        elif ob.type == 'MESH' and not any(m.type == 'ARMATURE' for m in ob.modifiers):
            bpy.data.objects.remove(ob, do_unlink=True)
    body = next(o for o in bpy.data.objects if o.type == 'MESH')

    # bake the KHR_texture_transform (Mapping node) into the UV layer the
    # BASE COLOR actually uses (the material has several UV map nodes — the
    # active layer is not necessarily the right one), then rebuild a plain
    # material around the recovered base color atlas
    mat = body.data.materials[0]
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    tex_node = bsdf.inputs['Base Color'].links[0].from_node
    while tex_node.type != 'TEX_IMAGE':  # e.g. a mix node in between
        tex_node = tex_node.inputs[0].links[0].from_node
    mapping = tex_node.inputs['Vector'].links[0].from_node
    if mapping.type != 'MAPPING':
        raise RuntimeError("base color has no mapping node: " + mapping.type)
    uvmap_node = mapping.inputs['Vector'].links[0].from_node
    uv_name = uvmap_node.uv_map if uvmap_node.type == 'UVMAP' else body.data.uv_layers.active.name
    loc = mapping.inputs['Location'].default_value
    scl = mapping.inputs['Scale'].default_value
    rot = mapping.inputs['Rotation'].default_value
    log("base color uv layer:", uv_name, "of", [l.name for l in body.data.uv_layers])
    log("uv transform: loc", list(loc)[:2], "scale", list(scl)[:2], "rot", list(rot))
    uvl = body.data.uv_layers[uv_name]
    # drop the other uv layers so the baked one is layer 0 (what the exporter emits)
    for l in [l for l in body.data.uv_layers if l.name != uv_name]:
        body.data.uv_layers.remove(l)
    uvl = body.data.uv_layers[0]
    vs = [d.uv.y for d in uvl.data]
    for d in uvl.data:
        d.uv.x = loc[0] + d.uv.x * scl[0]
        d.uv.y = loc[1] + d.uv.y * scl[1]
    # shift v near 0..1 (a constant integer shift keeps wrapping identical)
    vmin = min(d.uv.y for d in uvl.data)
    shift = math.floor(vmin)
    if shift != 0:
        for d in uvl.data:
            d.uv.y -= shift
    umin = min(d.uv.x for d in uvl.data)
    shiftx = math.floor(umin)
    if shiftx != 0:
        for d in uvl.data:
            d.uv.x -= shiftx
    log("uv baked; u range", round(min(d.uv.x for d in uvl.data), 3), round(max(d.uv.x for d in uvl.data), 3),
        "v range", round(min(d.uv.y for d in uvl.data), 3), round(max(d.uv.y for d in uvl.data), 3))

    import numpy as np
    atlas = bpy.data.images.load(os.path.join(SCRATCH, "radbro_basecolor_fixed.jpg"))
    aw, ah = atlas.size
    arr = np.empty(aw * ah * 4, dtype=np.float32)
    atlas.pixels.foreach_get(arr)
    grid = arr.reshape(ah, aw, 4)  # row 0 = image bottom

    # face feature rects, measured in top-left image coords
    def tl(x0, y0, x1, y1):  # -> (x0, x1, yb0, yb1) bottom-origin rows
        return x0, x1, ah - y1, ah - y0
    MOUTH = tl(477, 2390, 535, 2486)
    EYE_A = tl(300, 2260, 480, 2430)
    EYE_B = tl(300, 2455, 480, 2605)
    skin = grid[ah - 2200, 200].copy()

    # erase the painted mouth — the Mouth quad becomes the only mouth
    grid[MOUTH[2]:MOUTH[3], MOUTH[0]:MOUTH[1]] = skin
    atlas.pixels.foreach_set(grid.ravel())
    atlas.pack()

    # closed-eye morph atlas: skin over the eyes + a lash stroke along each
    # eye's long axis (the face is rotated 90° in UV space, so strokes run
    # vertically in image coords)
    morph = atlas.copy()
    morph.name = "RadbroEyesClosed"
    marr = np.empty(aw * ah * 4, dtype=np.float32)
    morph.pixels.foreach_get(marr)
    mgrid = marr.reshape(ah, aw, 4)
    for x0, x1, yb0, yb1 in (EYE_A, EYE_B):
        mgrid[yb0:yb1, x0:x1] = skin
        cx = (x0 + x1) // 2
        for y in range(yb0 + int((yb1 - yb0) * 0.12), yb1 - int((yb1 - yb0) * 0.12)):
            t = (y - (yb0 + yb1) / 2) / ((yb1 - yb0) / 2)
            xl = cx + int(t * t * (x1 - x0) * 0.12)
            mgrid[y, xl - 3:xl + 4] = (0.03, 0.02, 0.02, 1.0)
    morph.pixels.foreach_set(mgrid.ravel())
    morph.pack()
    nm = bpy.data.materials.new("RadbroBody")
    nm.use_nodes = True
    bsdf = next(n for n in nm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Roughness"].default_value = 1.0
    tn = nm.node_tree.nodes.new('ShaderNodeTexImage')
    tn.image = atlas
    nm.node_tree.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
    body.data.materials.clear()
    body.data.materials.append(nm)

    scale_and_ground(1.15)
    mins, maxs = world_bbox()
    W = maxs.x - mins.x

    # UV rects (Blender v-up) for the eyes and the erased mouth
    def uv_rect(x0, y0, x1, y1):  # from top-left pixel coords
        return x0 / aw, 1 - y1 / ah, x1 / aw, 1 - y0 / ah
    eye_rects = [uv_rect(300, 2260, 480, 2430), uv_rect(300, 2455, 480, 2605)]
    mu = ((477 + 535) / 2 / aw, 1 - (2390 + 2486) / 2 / ah)

    # --- EyePatch: duplicate faces under the eye rects, morph texture on top ---
    patch = body.copy()
    patch.data = body.data.copy()
    patch.name = "EyePatch"
    patch.data.name = "EyePatch"
    bpy.context.collection.objects.link(patch)
    bm = bmesh.new()
    bm.from_mesh(patch.data)
    uvlayer = bm.loops.layers.uv.active
    doomed = []
    for f in bm.faces:
        us = [l[uvlayer].uv.x for l in f.loops]; vs = [l[uvlayer].uv.y for l in f.loops]
        keep = False
        for u0, v0, u1, v1 in eye_rects:
            if max(us) >= u0 and min(us) <= u1 and max(vs) >= v0 and min(vs) <= v1:
                keep = True
        if not keep:
            doomed.append(f)
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    bm.to_mesh(patch.data)
    bm.free()
    log("radbro EyePatch faces:", len(patch.data.polygons))
    if len(patch.data.polygons) == 0:
        raise RuntimeError("radbro EyePatch empty")
    pm = bpy.data.materials.new("RadbroEyeMorph")
    pm.use_nodes = True
    pb = next(n for n in pm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs["Roughness"].default_value = 1.0
    ptn = pm.node_tree.nodes.new('ShaderNodeTexImage')
    ptn.image = morph
    pm.node_tree.links.new(ptn.outputs["Color"], pb.inputs["Base Color"])
    patch.data.materials.clear()
    patch.data.materials.append(pm)
    pme = patch.data
    pme.calc_loop_triangles()
    vnorms = [v.normal.copy() for v in pme.vertices]
    orig = [v.co.copy() for v in pme.vertices]
    for v, n in zip(pme.vertices, vnorms):
        v.co = v.co - n * 0.010
    patch.shape_key_add(name="Basis", from_mix=False)
    key = patch.shape_key_add(name="Blink", from_mix=False)
    for i, (p, n) in enumerate(zip(orig, vnorms)):
        key.data[i].co = p + n * 0.0015

    # --- mouth quad exactly where the painted mouth was: find the faces whose
    # UVs contain the mouth centre and average their world position ---
    deps = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(deps)
    bme = ev.to_mesh()
    uvdata = bme.uv_layers.active.data
    acc = Vector((0, 0, 0)); cnt = 0
    for poly in bme.polygons:
        us = [uvdata[li].uv.x for li in poly.loop_indices]
        vs = [uvdata[li].uv.y for li in poly.loop_indices]
        if min(us) <= mu[0] <= max(us) and min(vs) <= mu[1] <= max(vs):
            for vi in poly.vertices:
                acc += bme.vertices[vi].co
                cnt += 1
    ev.to_mesh_clear()
    if cnt == 0:
        raise RuntimeError("painted mouth position not found")
    mpos = acc / cnt
    log("radbro painted mouth at", [round(v, 3) for v in mpos])
    add_mouth_patch(arm, body, Vector((mpos.x, 0, mpos.z - 0.021)), 0.13 * W, 0.055 * W, style="rounded")

    setup_vrm(arm, "Radbro")
    add_blink_group(arm, patch, "Blink")
    export_vrm(arm, os.path.join(OUT_DIR, "Radbro.vrm"))
    print("===RADBRO_OK===")

try:
    build_clawb()
except Exception:
    traceback.print_exc()
    print("===CLAWB_FAIL===")
try:
    build_radbro()
except Exception:
    traceback.print_exc()
    print("===RADBRO_FAIL===")

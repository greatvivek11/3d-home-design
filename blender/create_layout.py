"""Run with Blender --background --python blender/create_layout.py -- [options]."""

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.layout import COLORS, dining_chairs, facade_edges, facade_openings, facade_pieces, feet, floor_footprints, load_json, room_area, room_footprints, stair_profile, structural_members, subtract_rectangles, validate, wall_partition, wall_parts, walls, write_review
from scripts.driveway import Driveway
from blender.finishes import create_maps, finish_material


MATERIALS = {}
FINISH_MAPS = {}
CURRENT = None
FLOOR_ID = ""
STUDY_ID = ""
ROOM_BOUNDS = {}


def material(name, color=None):
    if name not in MATERIALS:
        MATERIALS[name] = finish_material(name, color or COLORS.get(name, "#e8dfce"), FINISH_MAPS)
    return MATERIALS[name]


def attach(obj, name, mat):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    CURRENT.objects.link(obj)
    obj.name = f"{FLOOR_ID}.{name}"
    obj["floor_id"] = FLOOR_ID
    obj["study_id"] = STUDY_ID
    obj["status"] = "unapproved_concept"
    if mat:
        obj.data.materials.append(mat)
    return obj


def box(name, rect, z, height, mat, bevel=0.025):
    x, y, w, d = rect
    if min(w, d, height) <= 0:
        raise ValueError(f"Non-positive box dimensions: {name}")
    a, b, c = feet(w) / 2, feet(d) / 2, feet(height) / 2
    vertices = [(-a, -b, -c), (a, -b, -c), (a, b, -c), (-a, b, -c),
                (-a, -b, c), (a, -b, c), (a, b, c), (-a, b, c)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    mesh.update()
    uv = mesh.uv_layers.new(name="Finish UV")
    scale = mat.get("texture_scale_ft", 4)
    for polygon in mesh.polygons:
        axis = max(range(3), key=lambda i: abs(polygon.normal[i]))
        axes = [(1, 2), (0, 2), (0, 1)][axis]
        for index in polygon.loop_indices:
            point = mesh.vertices[mesh.loops[index].vertex_index].co
            world = [point[0] / feet(1) + x + w / 2, point[1] / feet(1) + y + d / 2, point[2] / feet(1) + z + height / 2]
            uv.data[index].uv = (world[axes[0]] / scale, world[axes[1]] / scale)
    obj = attach(bpy.data.objects.new(name, mesh), name, mat)
    obj.location = (feet(x + w / 2), feet(y + d / 2), feet(z + height / 2))
    if bevel:
        modifier = obj.modifiers.new("Crafted edge radius", "BEVEL")
        modifier.width = feet(min(bevel, min(w, d, height) / 3))
        modifier.segments = 4
        modifier.harden_normals = True
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL").keep_sharp = True
    return obj


def cylinder(name, x, y, z, radius, depth, mat):
    segments = 40
    vertices = [(feet(radius * math.cos(i * math.tau / segments)),
                 feet(radius * math.sin(i * math.tau / segments)), feet(h))
                for h in [-depth / 2, depth / 2] for i in range(segments)]
    faces = [tuple(reversed(range(segments))), tuple(range(segments, segments * 2))]
    faces += [(i, (i + 1) % segments, (i + 1) % segments + segments, i + segments) for i in range(segments)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Finish UV")
    scale = mat.get("texture_scale_ft", 4)
    for face in mesh.polygons:
        for loop in face.loop_indices:
            index = mesh.loops[loop].vertex_index
            if face.index < 2:
                point = mesh.vertices[index].co
                uv.data[loop].uv = ((point.x / feet(1) + x) / scale, (point.y / feet(1) + y) / scale)
            else:
                angle = (index % segments) / segments
                if face.index == segments + 1 and index % segments == 0:
                    angle = 1
                uv.data[loop].uv = (angle * math.tau * radius / scale, (z + (depth if index >= segments else 0)) / scale)
    for face in list(mesh.polygons)[2:]:
        face.use_smooth = True
    obj = attach(bpy.data.objects.new(name, mesh), name, mat)
    obj.location = (feet(x), feet(y), feet(z + depth / 2))
    return obj


def rod(name, a, b, radius, mat):
    start, end = Vector(a), Vector(b)
    direction = end - start
    obj = cylinder(name, 0, 0, -direction.length / 2, radius, direction.length, mat)
    obj.location = Vector(tuple(feet(v) for v in (start + end) / 2))
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    return obj


def oval(name, rect, z, height, mat, detail=(32, 16)):
    x, y, w, d = rect
    bpy.ops.mesh.primitive_uv_sphere_add(segments=detail[0], ring_count=detail[1], radius=1)
    obj = attach(bpy.context.object, name, mat)
    obj.location = (feet(x + w / 2), feet(y + d / 2), feet(z + height / 2))
    obj.scale = (feet(w) / 2, feet(d) / 2, feet(height) / 2)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def oval_ring(name, rect, z, height, thickness, mat, exponent=2):
    x, y, w, d = rect
    count = 48
    def rounded(value):
        return math.copysign(abs(value) ** (2 / exponent), value)
    vertices = [(feet(x + w / 2 + (w / 2 - inset) * rounded(math.cos(i * math.tau / count))),
                 feet(y + d / 2 + (d / 2 - inset) * rounded(math.sin(i * math.tau / count))), feet(h))
                for inset, h in [(0, z), (0, z + height), (thickness, z), (thickness, z + height)]
                for i in range(count)]
    faces = []
    for a, b in [(0, 1), (1, 3), (3, 2), (2, 0)]:
        faces += [(a * count + i, a * count + (i + 1) % count,
                   b * count + (i + 1) % count, b * count + i) for i in range(count)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for i, face in enumerate(mesh.polygons):
        face.use_smooth = i // count in {0, 2}
    return attach(bpy.data.objects.new(name, mesh), name, mat)


def table_legs(name, rect, height, mat):
    x, y, w, d = rect
    for dx in [min(.3, w / 5), w - min(.3, w / 5)]:
        for dy in [min(.3, d / 5), d - min(.3, d / 5)]:
            rod(name + ".leg", (x + dx, y + dy, .08), (x + dx, y + dy, height), .055, mat)


def chair(name, rect, turn=0):
    x, y, w, d = rect
    before = set(CURRENT.objects)
    table_legs(name, rect, 1.4, material("walnut", "#8e6c4c"))
    box(name + ".seat", [x + .08, y + .08, w - .16, d - .16], 1.35, .22, material("upholstery"), .1)
    box(name + ".back", [x + .08, y + .05, w - .16, .16], 1.55, 1.05, material("wood"), .07)
    if turn:
        pivot = Vector((feet(x + w / 2), feet(y + d / 2), 0))
        for obj in set(CURRENT.objects) - before:
            offset = obj.location - pivot
            obj.location = pivot + Vector((offset.x * math.cos(turn) - offset.y * math.sin(turn),
                                           offset.x * math.sin(turn) + offset.y * math.cos(turn), offset.z))
            obj.rotation_euler.z += turn


def cabinet(item, height=5.5, counter=False):
    name = item["id"]
    x, y, w, d = item["rect"]
    horizontal = w >= d
    length, depth = (w, d) if horizontal else (d, w)
    room = ROOM_BOUNDS[item["room"]]
    room_center = room[1] + room[3] / 2 if horizontal else room[0] + room[2] / 2
    origin = y if horizontal else x
    front_high = abs(origin + depth - room_center) < abs(origin - room_center)
    wood, dark = material("wood"), material("charcoal", "#35423d")

    def part(s, t, a, b, z, h, mat, label, bevel=.025):
        offset = t if front_high else depth - t - b
        rect = [x + s, y + offset, a, b] if horizontal else [x + offset, y + s, b, a]
        return box(name + "." + label, rect, z, h, mat, bevel)

    part(.06, .08, length - .12, depth - .16, .08, .18, dark, "recessed_plinth")
    part(0, 0, length, .08, .25, height - .25, wood, "back")
    for s in [0, length - .08]:
        part(s, 0, .08, depth, .25, height - .25, wood, "end")
    modules = max(1, math.ceil(length / 2.6))
    module = length / modules
    if counter:
        for i in range(modules):
            for z, h in [(.32, 1.35), (1.72, height - 1.82)]:
                part(i * module + .045, depth - .09, module - .09, .08, z, h, wood, "drawer_front", .018)
                part(i * module + module / 2 - .22, depth - .025, .44, .02, z + h - .18, .035,
                     material("brass", "#b39a6f"), "pull", .006)
    else:
        part(0, 0, length, depth, height - .12, .12, wood, "top")
        for i in range(1, modules):
            part(i * module - .04, 0, .08, depth, .25, height - .25, wood, "divider")
        wardrobe = "wardrobe" in name
        levels = [1.2, 5.05] if wardrobe else [1.35, 2.7, 4.05]
        for z in levels:
            part(.08, .08, length - .16, depth - .1, z, .08, wood, "shelf")
        if wardrobe:
            part(.08, depth * .6, length - .16, .04, 4.74, .04, material("chrome", "#aeb7b4"), "hanging_rail")
            for i in range(modules):
                part(i * module + .08, depth - .08, module - .16, .06, .3, .8, wood, "drawer")
                for j in range(4):
                    s = i * module + .25 + j * (module - .5) / 4
                    cloth = material("linen") if j % 2 else material("upholstery")
                    part(s, depth * .5, (module - .5) / 4 - .04, min(.45, depth * .3), 2, 2.55, cloth, "hanging_linen", .05)
                    part(s + .08, depth * .6, .035, .04, 4.55, .2, material("chrome"), "hanger")
        else:
            for row, z in enumerate([.48, 1.5, 2.85, 4.2]):
                for j in range(max(1, int(length / .3))):
                    s = .16 + j * (length - .32) / max(1, int(length / .3))
                    part(s, depth * .35, .13 + j % 3 * .025, depth * .5, z,
                         min(.7 + (j + row) % 3 * .11, height - z - .15),
                         material(["linen", "upholstery", "walnut"][j % 3]), "book_or_store", .015)


def sink(name, rect, top):
    x, y, w, d = rect
    porcelain = material("porcelain", "#f6f3ea")
    oval_ring(name + ".bowl", rect, top - .32, .34, .12, porcelain, 6)
    oval(name + ".bowl_bottom", [x + .12, y + .12, w - .24, d - .24], top - .34, .06, porcelain)
    cylinder(name + ".drain", x + w / 2, y + d / 2, top - .3, .055, .015, material("chrome", "#b4bfbe"))
    tap_x, tap_y = x + w * .5, y + .1
    rod(name + ".tap_stem", (tap_x, tap_y, top), (tap_x, tap_y, top + .65), .035, material("chrome"))
    rod(name + ".tap_spout", (tap_x, tap_y, top + .65), (tap_x, y + d * .45, top + .65), .035, material("chrome"))


def vanity(item):
    x, y, w, d = item["rect"]
    name = item["id"]
    cabinet(item, 2.6, counter=True)
    count = 2 if item["kind"] == "double_basin" else 1
    holes = []
    for i in range(count):
        bw, bd = (min(1.9, w / (count + .5)), min(1.2, d - .3))
        holes.append([x + w * (i + 1) / (count + 1) - bw / 2, y + (d - bd) / 2, bw, bd])
    for rect in subtract_rectangles(item["rect"], holes):
        box(name + ".stone_top", rect, 2.6, .12, material("stone"), 0)
    for i, rect in enumerate(holes):
        sink(f"{name}.sink_{i}", [rect[0] - .07, rect[1] - .07, rect[2] + .14, rect[3] + .14], 2.72)


def wheel(name, center, radius, width, axis="x"):
    for suffix, r, depth, mat in [
        ("tire", radius, width, material("rubber", "#242c2b")),
        ("rim", radius * .64, width + .012, material("chrome", "#aeb6b4")),
        ("hub", radius * .26, width + .025, material("metal", "#505a59")),
    ]:
        obj = cylinder(name + "." + suffix, 0, 0, -depth / 2, r, depth, mat)
        obj.location = Vector(tuple(feet(v) for v in center))
        obj.rotation_euler = (0, math.pi / 2, 0) if axis == "x" else (math.pi / 2, 0, 0)
        if suffix == "tire":
            modifier = obj.modifiers.new("Rounded tire shoulders", "BEVEL")
            modifier.width = feet(min(.08, width / 4))
            modifier.segments = 4


def equipment(item):
    name = item["id"]
    x, y, w, d = item["rect"]
    metal, rubber = material("metal", "#555f5b"), material("rubber", "#26302e")
    if name == "treadmill":
        box(name + ".chassis", [x, y, w, d], .1, .32, metal, .12)
        box(name + ".running_belt", [x + .25, y + .2, w - .5, d - .4], .42, .05, rubber, .06)
        for i in range(9):
            box(name + ".belt_rib", [x + .3, y + .4 + i * (d - .8) / 9, w - .6, .018], .47, .008, material("charcoal"))
        for dx in [.15, w - .15]:
            rod(name + ".upright", (x + dx, y + .9, .4), (x + dx, y + .6, 3.3), .055, metal)
        box(name + ".console", [x + .08, y + .3, w - .16, .55], 3.15, .3, rubber, .08)
        box(name + ".display", [x + w * .35, y + .38, w * .3, .3], 3.46, .025, material("screen", "#263c40"))
    elif name == "exercise_cycle":
        table_legs(name, item["rect"], .35, metal)
        oval(name + ".flywheel_casing", [x + w * .28, y + .6, w * .44, d * .5], .35, 1.6, metal)
        rod(name + ".seat_post", (x + w / 2, y + d * .65, .6), (x + w / 2, y + d * .7, 2.6), .065, metal)
        oval(name + ".saddle", [x + w / 2 - .5, y + d * .7 - .4, 1, .8], 2.6, .22, rubber)
        rod(name + ".bar_post", (x + w / 2, y + .7, 1), (x + w / 2, y + .5, 3.2), .06, metal)
        rod(name + ".handlebar", (x + .4, y + .5, 3.2), (x + w - .4, y + .5, 3.2), .065, rubber)
    elif name == "weights_bench":
        table_legs(name, item["rect"], 1.65, metal)
        box(name + ".upholstered_pad", [x + .5, y + .3, w - 1, d - .6], 1.65, .3, material("upholstery"), .16)
        box(name + ".pad_seam", [x + .5, y + d * .7, w - 1, .025], 1.96, .008, rubber)
    elif name == "ev_charger":
        box(name + ".pedestal", [x + .08, y + .1, w - .16, d - .2], .1, 3.4, metal, .08)
        box(name + ".display", [x + .14, y + d - .08, w - .28, .025], 2.3, .6, material("screen", "#355b4c"))
        rod(name + ".cable", (x + w * .35, y + d - .04, 2.2), (x + w * .35, y + d - .04, .7), .025, rubber)
    elif name in {"washer_dryer", "kitchen_fridge"}:
        height = 3.05 if name == "washer_dryer" else 6.4
        box(name + ".case", item["rect"], .1, height, material("porcelain", "#f5f2e9"), .075)
        if name == "washer_dryer":
            wheel(name + ".drum", (x + w / 2, y + d - .07, 1.45), .8, .05, "y")
            box(name + ".controls", [x + .2, y + d - .025, w - .4, .02], 2.7, .2, material("screen"), .015)
        else:
            for dx in [0, w / 2]:
                box(name + ".door", [x + dx + .025, y + d - .08, w / 2 - .05, .06], 1.65, height - 1.65, material("porcelain"), .04)
            box(name + ".freezer", [x + .025, y + d - .08, w - .05, .06], .18, 1.4, material("porcelain"), .04)
            for dx in [w / 2 - .13, w / 2 + .13]:
                rod(name + ".pull", (x + dx, y + d - .04, 3), (x + dx, y + d - .04, 4.5), .025, metal)
    else:
        raise ValueError(f"Unknown equipment fixture: {name}")


def text(name, body, x, y, z=0.1, size=0.65, mat=None):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = feet(size)
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    obj = bpy.data.objects.new(name, curve)
    CURRENT.objects.link(obj)
    obj.name = f"{FLOOR_ID}.{name}"
    obj.location = (feet(x), feet(y), feet(z))
    obj["floor_id"] = FLOOR_ID
    curve.materials.append(mat or material("ink", "#254338"))
    return obj


def rail(name, rect, z=0, height=3.5, gate=None):
    x, y, w, d = rect
    segments = [
        ("south", [x, y, w, 0.12]), ("north", [x, y + d, w, 0.12]),
        ("west", [x, y, 0.12, d]), ("east", [x + w, y, 0.12, d]),
    ]
    for side, r in segments:
        if side == gate:
            # Two segments leave a visible gate opening; the closed gate is distinct.
            a = r.copy()
            a[3] = (d - 3) / 2
            b = a.copy()
            b[1] = y + (d + 3) / 2
            for index, part in enumerate([a, b]):
                guard_panel(f"{name}.{side}.{index}", part, z, height)
            guard_panel(f"{name}.gate", [x, y + (d - 3) / 2, 0.12, 3], z, height)
        else:
            guard_panel(f"{name}.{side}", r, z, height)


def guard_panel(name, rect, z, height):
    x, y, w, d = rect
    panel = box(name, rect, z + .12, height - .24, material("glass", "#b6d0cd"), .012)
    metal = material("metal")
    box(name + ".cap", rect, z + height - .06, .06, metal, .025)
    length = max(w, d)
    for i in range(max(1, math.ceil(length / 4)) + 1):
        at = .06 + (length - .12) * i / max(1, math.ceil(length / 4))
        post = [x + at - .035, y + d / 2 - .035, .07, .07] if w >= d else [x + w / 2 - .035, y + at - .035, .07, .07]
        box(name + ".post", post, z, height, metal, .015)
    return panel


def annotation_line(name, points):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = feet(.02)
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, value in zip(spline.points, points):
        point.co = (*[feet(v) for v in value], 1)
    obj = bpy.data.objects.new(name, curve)
    CURRENT.objects.link(obj)
    curve.materials.append(material("dimension_ink", "#516659"))
    return obj


def floor_dimensions(floor, layout):
    global CURRENT
    geometry = CURRENT
    CURRENT = bpy.data.collections.new(f"{FLOOR_ID.upper()} DIMENSIONS - toggle in Outliner")
    geometry.children.link(CURRENT)
    x, y, w, d = floor["envelope"]
    front = min(y, *(b["rect"][1] for b in layout["balconies"])) if floor["id"] == "first" else y
    ay, ax = front - 2.8, x + w + 2.8
    ink = material("dimension_ink", "#516659")
    annotation_line("overall.width", [(x, ay, .08), (x + w, ay, .08)])
    annotation_line("overall.depth", [(ax, y, .08), (ax, y + d, .08)])
    for px in [x, x + w]:
        annotation_line("width.extension", [(px, front - .6, .08), (px, ay - .5, .08)])
        annotation_line("width.tick", [(px - .25, ay - .25, .08), (px + .25, ay + .25, .08)])
    for py in [y, y + d]:
        annotation_line("depth.extension", [(x + w + .6, py, .08), (ax + .5, py, .08)])
        annotation_line("depth.tick", [(ax - .25, py - .25, .08), (ax + .25, py + .25, .08)])
    text("overall.width.label", f"{w:g} ft / {feet(w):.2f} m", x + w / 2, ay - .65, .09, .65, ink)
    label = text("overall.depth.label", f"{d:g} ft / {feet(d):.2f} m", ax + .65, y + d / 2, .09, .65, ink)
    label.rotation_euler.z = math.pi / 2
    CURRENT = geometry


def furnishing_mesh(item):
    name, kind = item["id"], item["kind"]
    x, y, w, d = item["rect"]
    wood, white = material("wood", "#bc986e"), material("linen", "#f7f1e6")
    dark, green = material("charcoal", "#384c49"), material("upholstery", "#7d9680")
    metal = material("metal", "#535f5b")
    if kind == "bed":
        table_legs(name, [x + .1, y + .1, w - .2, d - .2], .36, material("walnut"))
        box(name + ".floating_frame", [x, y, w, d], .32, .55, wood, .1)
        headboard = box(name + ".headboard", [x + .04, y + .02, w - .08, .2], .7, 2.1, green, .1)
        headboard["role"] = "bed_headboard"
        box(name + ".mattress", [x + .1, y + .22, w - .2, d - .32], .88, .62, white, .17)
        box(name + ".piped_edge", [x + .09, y + .22, w - .18, d - .32], 1.22, .035, material("rug"), .015)
        box(name + ".duvet", [x + .12, y + 2, w - .24, d - 2.13], 1.49, .22, white, .12)
        box(name + ".folded_throw", [x + .13, y + d - 1.65, w - .26, 1.4], 1.72, .08, green, .04)
        for i in range(7):
            box(name + ".throw_rib", [x + .2 + i * (w - .4) / 7, y + d - 1.62, .014, 1.34], 1.805, .006, material("rug"), 0)
        for offset in [0.35, w / 2 + 0.15]:
            oval(name + ".pillow", [x + offset, y + .4, w / 2 - .5, 1.25], 1.5, .38, white)
    elif kind == "bedside_table":
        table_legs(name, item["rect"], .3, metal)
        box(name + ".case", [x + .03, y + .04, w - .06, d - .08], .25, 1.6, wood, .055)
        box(name + ".top", item["rect"], 1.85, .1, material("stone"), .025)
        box(name + ".drawer", [x + .08, y + d - .07, w - .16, .035], 1, .6, wood, .015)
        box(name + ".pull", [x + w / 2 - .18, y + d - .025, .36, .025], 1.3, .035, metal, .008)
        px, py = x + w / 2, y + .55
        cylinder(name + ".lamp_base", px, py, 1.95, .18, .05, material("brass"))
        cylinder(name + ".lamp_stem", px, py, 2, .025, .95, material("brass"))
        oval_ring(name + ".lamp_shade", [px - .35, py - .35, .7, .7], 2.9, .65, .025, white)
        glow = material("lamp_glow", "#ffe0ad")
        shader = glow.node_tree.nodes.get("Principled BSDF")
        if shader is None:
            raise ValueError("Lamp material is missing its Principled shader")
        shader.inputs["Emission Color"].default_value = (1, .68, .32, 1)
        shader.inputs["Emission Strength"].default_value = 1.5
        bulb = oval(name + ".lamp_bulb", [px - .08, py - .08, .16, .16], 3, .15, glow)
        bulb["role"] = "bedside_lamp"
        box(name + ".phone", [x + .12, y + d - .55, .34, .45], 1.95, .025, material("screen"), .025)
    elif kind in {"sofa", "chair"}:
        if name == "office_chair":
            cylinder(name + ".pedestal", x + w / 2, y + d / 2, .2, .09, 1.25, metal)
            for i in range(5):
                angle = i * math.tau / 5
                rod(name + ".star_base", (x + w / 2, y + d / 2, .25),
                    (x + w / 2 + (w / 2 - .15) * math.cos(angle), y + d / 2 + (d / 2 - .15) * math.sin(angle), .12), .045, metal)
            box(name + ".seat", [x + .12, y + .12, w - .24, d - .24], 1.45, .25, dark, .12)
            box(name + ".ergonomic_back", [x + .16, y + d - .22, w - .32, .16], 1.65, 1.25, dark, .08)
        else:
            table_legs(name, item["rect"], .4, material("walnut"))
            box(name + ".frame", [x, y, w, d], .35, .48, green, .1)
            box(name + ".back", [x + .03, y + .02, w - .06, .4], .8, 1.65, green, .17)
            for dx in [.02, w - .34]:
                box(name + ".arm", [x + dx, y + .06, .32, d - .12], .75, 1.15, green, .13)
            count = max(1, round(w / 2.4))
            for i in range(count):
                cw = (w - .8) / count
                box(name + ".cushion", [x + .4 + i * cw + .025, y + .48, cw - .05, d - .58], .85, .52, green, .15)
            for dx in [.45, max(.45, w - 1.3)]:
                oval(name + ".accent_cushion", [x + dx, y + .2, min(.8, w - .9), .7], 1.4, .8, white)
    elif kind == "car":
        paint = material("car", "#718681")
        height = item["height_ft"]
        box(name + ".body", [x + .35, y + .45, w - .7, d - .9], .95, 2.1, paint, .4)
        box(name + ".cabin", [x + 1.1, y + 5, w - 2.2, d - 9], 3.05, height - 4.2, paint, .38)
        box(name + ".windscreen", [x + 1.3, y + 5.02, w - 2.6, .05], 3.3, height - 4.8, material("screen", "#24383b"), .04)
        box(name + ".rear_window", [x + 1.3, y + d - 4.08, w - 2.6, .05], 3.35, height - 4.85, material("screen"), .04)
        for dx in [1.08, w - 1.13]:
            for j in range(3):
                box(name + ".side_window", [x + dx, y + 5.35 + j * (d - 9.8) / 3, .05, (d - 9.8) / 3 - .12], 3.35, height - 4.85, material("screen"), .025)
        for dx in [.8, w - .8]:
            for dy in [d * .2, d * .8]:
                wheel(name + ".wheel", (x + dx, y + dy, 1.2), 1.1, .9)
        for dx in [.02, w - .32]:
            box(name + ".mirror", [x + dx, y + 5.2, .3, .7], 3.6, .35, paint, .08)
        for dx in [1.1, w - 2.4]:
            box(name + ".headlight", [x + dx, y + .43, 1.3, .07], 2.1, .32, material("porcelain"), .08)
        box(name + ".grille", [x + w * .28, y + .41, w * .44, .06], 1.55, .65, dark, .06)
        for i in range(7):
            box(name + ".grille_slat", [x + w * .3 + i * w * .056, y + .39, .07, .035], 1.6, .5, metal, .015)
        for dx in [1.3, w - 1.3]:
            for dy in [5.5, d - 4.6]:
                rod(name + ".roof_rack_post", (x + dx, y + dy, height - 1.15), (x + dx, y + dy, height - .045), .035, metal)
            rod(name + ".roof_rail", (x + dx, y + 5.5, height - .045), (x + dx, y + d - 4.6, height - .045), .045, metal)
    elif kind == "bike":
        for dy in [1, d - 1]:
            wheel(name + ".wheel", (x + w / 2, y + dy, 1), .88, .3)
        oval(name + ".body", [x + .25, y + d * .3, w - .5, d * .42], 1.3, 1.2, material("car"))
        oval(name + ".saddle", [x + .25, y + d * .52, w - .5, d * .27], 2.45, .3, dark)
        rod(name + ".fork", (x + w / 2, y + 1, .95), (x + w / 2, y + 1.25, 3.2), .055, metal)
        rod(name + ".handlebar", (x + .18, y + 1.25, 3.2), (x + w - .18, y + 1.25, 3.2), .06, dark)
    elif kind in {"toilet", "wc_cubicle"}:
        if kind == "wc_cubicle":
            box(name + ".partition", [x, y, 0.15, d], 0, 3, white)
            if not item.get("reuse_back_wall"):
                box(name + ".back", [x, y, w, 0.15], 0, 3, white)
            box(name + ".other_partition", [x + w - 0.15, y, 0.15, d], 0, 3, white)
            for dx in [0, w - 0.25]:
                box(name + ".door_jamb", [x + dx, y + d - 0.15, 0.25, 0.15], 0, 3, white)
        tw, td = min(1.8, w - .12), min(1.9, d - .55)
        back = .17 if kind == "wc_cubicle" and not item.get("reuse_back_wall") else .02
        bowl = [x + (w - tw) / 2, y + back + .34, tw, td]
        porcelain = material("porcelain", "#f8f5ed")
        oval(name + ".pedestal", [bowl[0] + .2, bowl[1] + .2, tw - .4, td - .35], .1, 1.1, porcelain)
        oval_ring(name + ".bowl", bowl, .9, .4, .13, porcelain)
        oval(name + ".water", [bowl[0] + .18, bowl[1] + .18, tw - .36, td - .36], .95, .025, material("water", "#91b9b5"))
        oval_ring(name + ".seat", [bowl[0] - .02, bowl[1] - .02, tw + .04, td + .04], 1.31, .07, .16, porcelain)
        tank = box(name + ".cistern", [x + (w - tw) / 2, y + back, tw, .42], .7, 1.55, porcelain, .1)
        tank["role"] = "toilet_cistern"
        cylinder(name + ".flush", x + w / 2, y + back + .2, 2.25, .055, .015, material("chrome"))
    elif kind in {"shower", "bathtub"}:
        if kind == "bathtub":
            oval_ring(name + ".shell", item["rect"], .12, 1.65, .16, material("porcelain"), 4)
            oval(name + ".bottom", [x + .18, y + .18, w - .36, d - .36], .13, .12, material("porcelain"))
        else:
            box(name + ".tray", item["rect"], .04, .09, material("stone"), .025)
            box(name + ".drain", [x + w * .5 - .25, y + .14, .5, .1], .135, .02, metal, .008)
            rod(name + ".riser", (x + w - .12, y + .15, .15), (x + w - .12, y + .15, 6.5), .025, material("chrome"))
            rod(name + ".arm", (x + w - .12, y + .15, 6.5), (x + w - .12, y + .65, 6.5), .025, material("chrome"))
            cylinder(name + ".rain_head", x + w - .45, y + .65, 6.42, .3, .06, material("chrome"))
        if kind == "shower" and item.get("enclosed"):
            for side, r in [
                ("south", [x, y, w, 0.06]), ("north", [x, y + d - 0.06, w, 0.06]),
                ("west", [x, y, 0.06, d]), ("east", [x + w - 0.06, y, 0.06, d]),
            ]:
                panel = box(name + ".enclosure." + side, r, 0.3, 2.7, material("shower_glass", "#b4d9db"))
                panel["shower_enclosure_intent"] = True
                panel["entry_door"] = side == item["entry_side"]
                panel["intended_height_ft"] = 7
                panel["cutaway"] = True
    elif kind == "rug":
        box(name, item["rect"], .04, .025, material("rug"), .01)
    elif kind in {"table_tennis", "game_table"}:
        table_legs(name, item["rect"], 2.3, metal)
        box(name + ".top", [x, y, w, d], 2.3, 0.2, material("game_surface", "#527e89"), 0.03)
        if kind == "table_tennis":
            for dx in [.07, w - .1]:
                box(name + ".court_line", [x + dx, y + .07, .03, d - .14], 2.51, .008, material("porcelain"), 0)
            box(name + ".center_line", [x + .07, y + d / 2, w - .14, .025], 2.51, .008, material("porcelain"), 0)
            box(name + ".net", [x + w / 2, y, .03, d], 2.5, .45, material("glass"), 0)
        else:
            for i in range(4):
                rod(name + ".foosball_rod", (x + .15 + i * (w - .3) / 3, y + .05, 2.8),
                    (x + .15 + i * (w - .3) / 3, y + d - .05, 2.8), .025, metal)
    elif kind == "solar":
        box(name + ".frame", item["rect"], .5, .18, material("solar_frame", "#8e9b9c"), .035)
        for i in range(6):
            for j in range(4):
                box(name + ".cell", [x + .08 + i * (w - .16) / 6, y + .08 + j * (d - .16) / 4,
                                    (w - .16) / 6 - .025, (d - .16) / 4 - .025], .69, .025, material("solar", "#304e65"), .01)
    elif kind == "planter":
        box(name + ".base", item["rect"], .05, .2, wood, .06)
        for rect in [[x, y, w, .12], [x, y + d - .12, w, .12], [x, y, .12, d], [x + w - .12, y, .12, d]]:
            box(name + ".rim", rect, .2, 1.25, wood, .04)
        box(name + ".soil", [x + .12, y + .12, w - .24, d - .24], 1.2, .1, material("soil", "#625d48"))
        for i in range(5):
            px = x + .4 + i * (w - .8) / 5
            oval(name + ".foliage", [px, y + .25, min(.9, w / 4), d - .5], 1.3, 1 + i % 2 * .3, material("foliage", "#70815a"))
    elif kind == "shelf":
        if name == "cycle_rack":
            for i in range(6):
                px = x + .3 + i * (w - .6) / 6
                rod(name + ".upright", (px, y + .1, .08), (px, y + .1, 2.2), .04, metal)
                rod(name + ".top", (px, y + .1, 2.2), (px, y + d - .1, 2.2), .04, metal)
                rod(name + ".return", (px, y + d - .1, 2.2), (px, y + d - .1, .08), .04, metal)
        elif name == "weights_rack":
            table_legs(name, item["rect"], 3, metal)
            for z in [1.2, 2.3]:
                box(name + ".shelf", [x, y, w, d], z, .1, dark)
                for i in range(5):
                    px = x + .5 + i * (w - 1) / 5
                    rod(name + ".grip", (px, y + .45, z + .35), (px, y + d - .45, z + .35), .045, material("chrome"))
                    for py in [.38, d - .38]:
                        oval(name + ".dumbbell", [px - .2, y + py - .18, .4, .36], z + .15, .4, dark)
        else:
            cabinet(item)
    elif kind == "equipment":
        equipment(item)
    elif kind in {"basin", "double_basin"}:
        vanity(item)
    elif kind == "counter":
        cabinet(item, 2.98, counter=True)
        hole = [x + 2, y + .2, 2, 1.5] if item.get("appliance") == "sink" else None
        for rect in subtract_rectangles(item["rect"], [hole] if hole else []):
            box(name + ".stone_top", rect, 2.98, .12, material("stone"), 0)
        if hole:
            sink(name + ".sink", [hole[0] - .05, hole[1] - .05, hole[2] + .1, hole[3] + .1], 3.1)
        if item.get("appliance") == "cooktop_with_hood":
            box(name + ".hob", [x + .15, y + .1, w - .3, d - .2], 3.11, .045, material("screen"), .035)
            for dx in [.75, w - .75]:
                for dy in [.55, d - .55]:
                    oval_ring(name + ".induction_ring", [x + dx - .24, y + dy - .24, .48, .48], 3.16, .008, .012, material("chrome"))
            hood = box(name + ".extraction_hood", item["rect"], 6.5, .3, metal, .08)
            hood["status"] = "indicative source extraction; duct route/outlet requires MEP design"
            box(name + ".hood_chimney", [x + w / 2 - .4, y + .2, .8, .6], 6.8, 1.2, metal, .035)
    elif kind in {"table", "dining_table", "desk"}:
        height = 2.5 if kind in {"desk", "dining_table"} else 2.4
        table_legs(name, item["rect"], height, material("walnut"))
        box(name + ".top", item["rect"], height, .12, wood, .07)
        if kind == "dining_table":
            for i, r in enumerate(dining_chairs(item["rect"])):
                chair(f"{name}.chair_{i + 1}", r, -math.pi / 2 if i < 3 else math.pi / 2 if i < 6 else math.pi if i == 7 else 0)
        elif kind == "desk":
            if name == "office_workstation":
                rod(name + ".monitor_stand", (x + w / 2, y + .38, height + .12), (x + w / 2, y + .38, 3.35), .055, metal)
                box(name + ".monitor", [x + w / 2 - 1.6, y + .2, 3.2, .16], 3.25, 1.75, dark, .06)
                box(name + ".screen", [x + w / 2 - 1.52, y + .365, 3.04, .012], 3.33, 1.59, material("screen", "#263c40"), .025)
                for i in range(8):
                    box(name + ".screen_line", [x + w / 2 - 1.3, y + .382, .8 + (i % 3) * .45, .008],
                        3.5 + i * .15, .025, material("upholstery"), 0)
                box(name + ".keyboard", [x + w / 2 - 1.1, y + d - .8, 2.2, .65], height + .13, .06, dark, .04)
                for row in range(4):
                    for col in range(12):
                        box(name + ".key", [x + w / 2 - 1.03 + col * .17, y + d - .74 + row * .14, .135, .1],
                            height + .195, .025, material("porcelain"), .012)
                oval(name + ".mouse", [x + w / 2 + 1.4, y + d - .7, .3, .5], height + .12, .13, dark)
            else:
                box(name + ".notebook", [x + .4, y + .5, min(1.2, w - 1), min(.8, d - .8)], height + .12, .045, white, .02)
                cylinder(name + ".lamp_base", x + w - .35, y + .35, height + .12, .2, .04, metal)
                rod(name + ".lamp_stem", (x + w - .35, y + .35, height + .16), (x + w - .35, y + .35, height + 1), .02, metal)
                oval(name + ".lamp_shade", [x + w - .6, y + .15, .5, .4], height + .95, .16, material("brass"))
        else:
            box(name + ".book", [x + w * .35, y + d * .35, min(1.1, w * .4), min(.7, d * .4)], height + .13, .055, white, .015)
            cylinder(name + ".ceramic_vase", x + w * .72, y + d * .6, height + .13, min(.16, d * .12), .4, material("porcelain"))
    elif kind == "stool":
        table_legs(name, item["rect"], 1.8, metal)
        box(name + ".seat", [x + .05, y + .05, w - .1, d - .1], 1.8, .18, green, .11)
    elif kind == "piano":
        table_legs(name, item["rect"], 2.25, material("walnut"))
        box(name + ".case", item["rect"], 2.25, .45, material("walnut"), .045)
        for i in range(36):
            kw = (w - .2) / 36
            box(name + ".ivory", [x + .1 + i * kw, y + d - .8, kw - .009, .7], 2.71, .065, material("porcelain"), .008)
            if i % 7 not in {2, 6}:
                box(name + ".ebony", [x + .1 + i * kw + kw * .65, y + d - .8, kw * .55, .38], 2.78, .055, dark, .008)
        box(name + ".music_rest", [x + .3, y + .1, w - .6, .08], 2.7, .75, material("walnut"))
    elif kind == "tv":
        box(name + ".stand", [x + w * .35, y + .05, w * .3, d - .1], .05, 2.1, metal)
        box(name + ".bezel", [x, y, w, d], 2.1, 3.2, dark, .065)
        box(name + ".display", [x + .07, y + d - .015, w - .14, .01], 2.18, 3.04, material("screen"), .025)
    elif kind == "prayer":
        box(name + ".cabinet", item["rect"], .1, 2.2, wood, .04)
        box(name + ".stone_cap", item["rect"], 2.3, .12, material("stone"))
        cylinder(name + ".diya", x + w / 2, y + d / 2, 2.42, .13, .06, material("brass"))
    else:
        raise ValueError(f"Unknown furniture kind: {kind}")
    # Stable source identities apply to all parts, including generated chairs.
    for obj in CURRENT.objects:
        if obj.name.startswith(f"{FLOOR_ID}.{name}.") or obj.name == f"{FLOOR_ID}.{name}":
            obj["room_id"] = item["room"]
            obj["fixture_id"] = name


def furnishing(item):
    edge = item.get("back_edge", "front")
    if edge not in {"front", "back", "left", "right"}:
        raise ValueError(f"Invalid furnishing back edge: {item['id']}/{edge}")
    x, y, w, d = item["rect"]
    cw, cd = (d, w) if edge in {"left", "right"} else (w, d)
    furnishing_mesh({**item, "rect": [x, y, cw, cd]})
    if edge == "front":
        return
    angle = {"back": math.pi, "left": -math.pi / 2, "right": math.pi / 2}[edge]
    transform = (Matrix.Translation((feet(x + w / 2), feet(y + d / 2), 0))
                 @ Matrix.Rotation(angle, 4, "Z")
                 @ Matrix.Translation((-feet(x + cw / 2), -feet(y + cd / 2), 0)))
    for obj in CURRENT.objects:
        if obj.get("fixture_id") == item["id"]:
            if obj.parent:
                raise ValueError(f"Unexpected parent on furnishing part: {obj.name}")
            obj.matrix_basis = transform @ obj.matrix_basis


def floor_slab(floor):
    stone = material("slab", "#ddd7c9")
    holes = [] if floor["id"] == "basement" else [stair_profile(floor)["opening"]]
    holes += [room["rect"] for room in floor["rooms"] if room["kind"] == "lift" and floor["id"] != "basement"]
    pieces = [part for base in floor_footprints(floor) for part in subtract_rectangles(base, holes)]
    for i, rect in enumerate(pieces):
        box(f"slab.{i}", rect, -0.5, 0.5, stone)


def stairs(floor):
    requested = stair_profile(floor)
    profile = stair_profile({**floor, "stair_entry_edge": "back"})
    x, y, w, d = profile["rect"]
    width, landing, tread, rise = (profile[key] for key in ["flight_width", "landing_depth", "going", "riser_height"])
    guard = material("metal")
    if not floor["rise"]:
        guard_panel("stair.roof_void_guard", [x, y + d - landing - .06, width + 1, .12], 0, 3.5)
    else:
        stone = material("stair", "#a8b4ac")
        for flight in range(2):
            px = x if flight == 0 else x + width + 1
            rail_x = x + width + (.1 if flight == 0 else .9)
            for i in range(1, 10):
                py = y + landing + (9 - i if flight == 0 else i - 1) * tread
                index = i + flight * 10
                obj = box(f"stair.flight{flight + 1}.{i}", [px, py, width, tread], (index - 1) * rise, rise, stone)
                obj["role"], obj["riser_index"] = "stair_tread", index
                cylinder(f"stair.guard_post.{flight}.{i}", rail_x, py + tread / 2,
                         index * rise, .035, 3.5 + rise / 2, guard)
            a = (rail_x, y + d - landing, rise + 3.5) if flight == 0 else (rail_x, y + landing, 11 * rise + 3.5)
            b = (rail_x, y + landing, 10 * rise + 3.5) if flight == 0 else (rail_x, y + d - landing, floor["rise"] + 3.5)
            rod(f"stair.handrail.{flight}", a, b, .06, material("wood"))
        turn = box("stair.half_landing", profile["turn"], 10 * rise - .35, .35, stone)
        turn["role"], turn["riser_index"] = "stair_landing", 10
        top = box("stair.top_landing", [x + width + 1, y + d - landing, width, landing], floor["rise"] - .35, .35, stone)
        top["role"], top["riser_index"] = "stair_landing", 20
        if floor["id"] != "basement":
            guard_panel("stair.well_end_guard", [x + width, y + d - landing - .06, 1, .12], 0, 3.5)
    for obj in CURRENT.objects:
        if obj.name.startswith(f"{FLOOR_ID}.stair."):
            obj["room_id"] = "stairs"
            if "role" not in obj:
                obj["role"] = "stair_guard"
            if requested["entry_edge"] == "front":
                mirror = Matrix.Translation((0, feet(2 * y + d), 0)) @ Matrix.Diagonal(Vector((1, -1, 1, 1)))
                obj.matrix_basis = mirror @ obj.matrix_basis


def floor_geometry(floor, layout):
    global CURRENT
    ROOM_BOUNDS.update({room["id"]: room["rect"] for room in floor["rooms"]})
    floor_slab(floor)
    for room in floor["rooms"]:
        if room["kind"] not in {"stairs", "circulation", "lift"}:
            for i, rect in enumerate(room_footprints(floor, room)):
                tile = box(f"zone.{room['id']}.{i}", rect, 0.045 if room.get("parent") else 0.005, 0.025, material(room["kind"]), 0)
                tile["room_id"] = room["id"]
                tile["role"] = "room_floor"
    cap_regions = {}
    for index, wall in enumerate(walls(floor, layout["wall_thickness"])):
        partition = wall_partition(floor, wall)
        for j, (start, end, height) in enumerate(wall_parts(wall, floor["openings"], layout["section_height"])):
            t = layout["wall_thickness"]
            rect = [start, wall["at"] - t / 2, end - start, t] if wall["axis"] == "x" else [wall["at"] - t / 2, start, t, end - start]
            base, cap = min(.27, height / 3), min(.035, height / 6)
            pieces = [
                box(f"section_wall.{index}.{j}", rect, base, height - base - cap, material("garage_barrier", "#ac7851") if partition and partition.get("role") != "privacy_wall" else material("wall", "#eeeae0")),
                box(f"wall_skirting.{index}.{j}", rect, 0, base, material("skirting", "#d9d2c4"), .012),
            ]
            covered = cap_regions.setdefault(round(height, 6), [])
            for k, part in enumerate(subtract_rectangles(rect, covered)):
                pieces.append(box(f"wall_cap.{index}.{j}.{k}", part, height - cap, cap, material("wall_cap", "#f7f4ec"), 0))
            covered.append(rect)
            for obj in pieces:
                if partition:
                    obj["partition_id"] = partition["id"]
                    obj["intended_height_ft"] = partition["intended_height"]
                    obj["cutaway"] = True
    for p in floor.get("partitions", []):
        x, y = ((p["start"] + p["end"]) / 2, p["at"]) if p["axis"] == "x" else (p["at"], (p["start"] + p["end"]) / 2)
        note = text(p["id"] + ".note", p["label"], x, y, layout["section_height"] + 0.05, min(.5, (p["end"] - p["start"]) / 50))
        if p["axis"] == "y":
            note.rotation_euler.z = math.pi / 2
    for i, o in enumerate(floor["openings"]):
        if o.get("kind") in {"window", "slider"}:
            rect = [o["start"], o["at"] - 0.035, o["width"], 0.07] if o["axis"] == "x" else [o["at"] - 0.035, o["start"], 0.07, o["width"]]
            sill = o.get("sill", 0)
            top = min(layout["section_height"], sill + o.get("height", 2))
            glass = box(f"opening.{i}.glass", rect, sill + .04, max(.08, top - sill - .08), material("glass", "#b6d0cd"), .008)
            glass["room_id"] = next(ref for ref in o["connects"] if ref != "outside")
            glass["role"] = "facade_glazing"
            glass["operable_intent"] = o.get("operable", o["kind"] == "slider")
            glass["intended_glazing_height_ft"] = o.get("height", 2)
            glass["opening_width_ft"] = o["width"]
            glass["cutaway"] = True
            for z in [sill, top - .035]:
                box(f"opening.{i}.track", rect, z, .035, material("metal"), .01)
            for along in [o["start"] + .025, o["start"] + o["width"] / 2, o["start"] + o["width"] - .025]:
                r = [along - .025, o["at"] - .035, .05, .07] if o["axis"] == "x" else [o["at"] - .035, along - .025, .07, .05]
                box(f"opening.{i}.mullion", r, sill, max(.12, top - sill), material("metal"), .01)
        elif o.get("kind") == "lift_door":
            for side, start in enumerate([o["start"], o["start"] + o["width"] - .35]):
                rect = [start, o["at"] - .05, .35, .1] if o["axis"] == "x" else [o["at"] - .05, start, .1, .35]
                panel = box(f"lift.door.{side}", rect, 0, layout["section_height"], material("metal"))
                panel["room_id"] = "lift"
                panel["role"] = "lift_landing_door"
                panel["display_only"] = True
            threshold = [o["start"], o["at"] - .15, o["width"], .3] if o["axis"] == "x" else [o["at"] - .15, o["start"], .3, o["width"]]
            box("lift.threshold", threshold, 0, .04, material("metal"), .01)
        elif o.get("kind") == "cupboard_doors":
            if o.get("operation") != "bypass_sliding_intent":
                raise ValueError("Utility cupboard requires gallery-facing sliding-front intent")
            leaf = o["width"] / 2
            for side in range(2):
                start = o["start"] + side * leaf
                track = o["at"] + (side - .5) * .06
                panel_rect = ([start + .015, track - .04, leaf - .03, .08] if o["axis"] == "x"
                              else [track - .04, start + .015, .08, leaf - .03])
                panel = box(f"utility.door.{side}", panel_rect,
                            .08, layout["section_height"] - .08, material("wood"), .015)
                pull_along = start + leaf - .25 if side == 0 else start + .2
                pull_rect = ([pull_along, track + .04, .04, .04] if o["axis"] == "x"
                             else [track - .08, pull_along, .04, .04])
                pull = box(f"utility.pull.{side}", pull_rect,
                           1, 1.2, material("brass", "#b39a6f"), .01)
                for part, role in [(panel, "utility_cupboard_door"), (pull, "utility_cupboard_handle")]:
                    part["room_id"] = "utility_store"
                    part["role"] = role
                    part["door_id"] = o["id"]
                    part["leaf_index"] = side
                    part["sliding_intent"] = True
                    part["cutaway"] = True
        elif o.get("self_closing"):
            rect = [o["start"], o["at"] - 0.04, o["width"], 0.08] if o["axis"] == "x" else [o["at"] - 0.04, o["start"], 0.08, o["width"]]
            door = box("door." + o["id"], rect, 0, layout["section_height"], material("sealed_door", "#56766b"))
            door["self_closing_intent"] = True
            door["door_id"] = o["id"]
            door["room_id"] = o["connects"][0]
            door["cutaway"] = True
        elif o.get("kind") == "soft_divider":
            for side, start in enumerate([o["start"], o["start"] + o["width"] - 0.6]):
                rect = [start, o["at"] - 0.035, 0.6, 0.07] if o["axis"] == "x" else [o["at"] - 0.035, start, 0.07, 0.6]
                panel = box(f"soft_divider.{o['id']}.{side}", rect, 0, layout["section_height"], material("curtain", "#c6b3cf"))
                panel["divider_id"] = o["id"]
                panel["soft_partition_intent"] = True
                panel["room_id"] = o["connects"][1]
                panel["cutaway"] = True
    for item in floor["furniture"]:
        furnishing(item)
    lift = next(room for room in floor["rooms"] if room["kind"] == "lift")
    lx, ly, lw, ld = lift["rect"]
    if floor["id"] == "basement":
        car = box("lift.car_placeholder", [lx + .35, ly + .35, lw - .7, ld - .7], .04, .12, material("metal"))
        car["role"] = "lift_car_placeholder"
        car["room_id"] = "lift"
        car["display_only"] = True
    for px in [lx + .2, lx + lw - .3]:
        guide = box("lift.guide", [px, ly + ld - .2, .1, .1], 0, layout["section_height"], material("metal"))
        guide["room_id"] = "lift"
        guide["role"] = "lift_guide_proxy"
    stairs(floor)
    if floor["id"] == "first":
        for balcony in layout["balconies"]:
            deck = box(balcony["id"], balcony["rect"], -0.5, 0.5, material("wood", "#bc986e"))
            deck["balcony_id"] = balcony["id"]
            deck["role"] = "shared_balcony_deck"
            x, y, w, d = balcony["rect"]
            # No rear rail against the room openings.
            edge_y = y if y < 20 else y + d
            guard = guard_panel(balcony["id"] + ".guard", [x, edge_y, w, 0.12], 0, 3.5)
            guard["balcony_id"] = balcony["id"]
            guard["role"] = "perimeter_guard"
            for edge_x in [x, x + w]:
                guard = guard_panel(balcony["id"] + ".end", [edge_x, y, 0.12, d], 0, 3.5)
                guard["balcony_id"] = balcony["id"]
                guard["role"] = "perimeter_guard"
    if floor["id"] == "roof":
        x, y, w, d = floor["envelope"]
        stair = next(r["rect"] for r in floor["rooms"] if r["id"] == "stairs")
        lift = next(r["rect"] for r in floor["rooms"] if r["id"] == "lift")
        for side, rect in [
            ("front", [x + .1, y + .1, lift[0] - x - .6, .12]),
            ("rear", [x + .1, y + d - .1, w - .2, .12]),
            ("left", [x + .1, y + .1, .12, d - .2]),
            ("right_rear", [x + w - .1, stair[1] + stair[3] + .5, .12,
                            y + d - stair[1] - stair[3] - .6]),
        ]:
            guard_panel("roof_guard." + side, rect, 0, 3.5)
        pergola(next(r["rect"] for r in floor["rooms"] if r["id"] == "roof_shade"), 8)
        roof_weather_geometry(floor, layout)
    geometry = CURRENT
    CURRENT = bpy.data.collections.new(f"{FLOOR_ID.upper()} LABELS - toggle in Outliner")
    geometry.children.link(CURRENT)
    for room in floor["rooms"]:
        if room["kind"] == "circulation" and not room.get("label"):
            continue
        x, y, w, d = max(room_footprints(floor, room), key=lambda r: r[2] * r[3])
        rw, rd = room["rect"][2:]
        area = room_area(floor, room)
        suffix = f"\n{area:g} sq ft NET" if not math.isclose(area, rw * rd) else ""
        label = room.get("short_label", room["id"].replace("_", " ")).upper()
        obj = text("label." + room["id"], f"{label}\n{rw:g} x {rd:g} ft / {feet(rw):.2f} x {feet(rd):.2f} m{suffix}",
                   x + w / 2, y + d / 2, layout["section_height"] + .18, min(.58, w / 20))
        obj["room_id"] = room["id"]
    CURRENT = geometry
    floor_dimensions(floor, layout)


def structural_geometry(floor, layout):
    for member in structural_members(layout, floor):
        column = member["role"] == "column_proxy"
        mat = material("structure_column", "#537b81") if column else material("structure_beam", "#ae8651")
        obj = box(f"structure.{member['id']}.{member['role']}", member["rect"], member["z"], member["height"], mat, .015)
        obj["role"] = "structural_proxy"
        obj["structural_role"] = member["role"]
        obj["member_id"] = member["id"]
        obj["proxy_span_ft"] = member["span_ft"]
        obj["engineering_status"] = "not_engineered"
    rooms = {r["id"]: r for r in floor["rooms"]}
    for rid in layout["structure"]["clear_span_rooms"].get(floor["id"], []):
        for i, rect in enumerate(room_footprints(floor, rooms[rid])):
            zone = box(f"structure.clear_span.{rid}.{i}", rect, -.65, .025, material("clear_span_intent", "#eee3ce"), 0)
            zone["role"] = "clear_span_intent"
            zone["room_id"] = rid
            zone["engineering_status"] = "not_engineered"
    x, y, w, d = floor["envelope"]
    text("structure.warning", "STRUCTURAL INTENT ONLY / NOT ENGINEERED", x + w / 2, y - 3, .1, .9)
    text("structure.caption", "DISPLAY PROXIES - CLEAR SPANS UNVERIFIED - ENGINEER MAY REQUIRE INTERNAL SUPPORTS", x + w / 2, y + d + 3, .1, .55)


def pergola(rect, height):
    x, y, w, d = rect
    wood = material("pergola", "#9c815c")
    for px, py in [(x, y), (x + w - 0.3, y), (x, y + d - 0.3), (x + w - 0.3, y + d - 0.3)]:
        box("pergola.post", [px, py, 0.3, 0.3], 0, height, wood)
    for i in range(int(w / 2) + 1):
        box("pergola.beam", [x + 2 * i, y, 0.2, d], height, 0.3, wood)


def surface_mesh(name, vertices, faces, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(feet(v) for v in point) for point in vertices], [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Finish UV")
    scale = mat.get("texture_scale_ft", 4)
    for face in mesh.polygons:
        axis = max(range(3), key=lambda i: abs(face.normal[i]))
        axes = [(1, 2), (0, 2), (0, 1)][axis]
        for loop in face.loop_indices:
            point = vertices[mesh.loops[loop].vertex_index]
            uv.data[loop].uv = (point[axes[0]] / scale, point[axes[1]] / scale)
    return attach(bpy.data.objects.new(name, mesh), name, mat)


def clipped_x(points, boundary):
    result = []
    for a, b in zip(points, points[1:] + points[:1]):
        ain, bin = a[0] >= boundary, b[0] >= boundary
        if ain:
            result.append(a)
        if ain != bin:
            t = (boundary - a[0]) / (b[0] - a[0])
            result.append(tuple(a[i] + t * (b[i] - a[i]) for i in range(len(a))))
    return result


def solid_polygon(name, lower, thickness, mat):
    if len(lower) < 3:
        raise ValueError(f"Empty solid footprint: {name}")
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(lower, lower[1:] + lower[:1]))
    if area < 0:
        lower = list(reversed(lower))
    n = len(lower)
    vertices = lower + [(x, y, z + thickness) for x, y, z in lower]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return surface_mesh(name, vertices, faces, mat)


def weather_collection():
    child = bpy.data.collections.new(f"{FLOOR_ID.upper()} WEATHER COVERS")
    child["export_architecture"] = True
    child["engineering_status"] = "not_engineered"
    CURRENT.children.link(child)
    return child


def roof_weather_geometry(floor, layout):
    global CURRENT
    parent = CURRENT
    CURRENT = weather_collection()
    t, half = layout["wall_thickness"], layout["wall_thickness"] / 2
    rooms = {r["id"]: r for r in floor["rooms"] if r["id"] in {"stairs", "lift"}}
    heights = {rid: layout["weather_protection"]["roof_lift_display_height_ft" if rid == "lift" else "roof_stair_clear_height_ft"] for rid in rooms}
    outlines = []
    for rid, room in rooms.items():
        x, y, w, d = room["rect"]
        outlines += [(rid, "x", y - half, x - half, x + w + half), (rid, "x", y + d + half, x - half, x + w + half),
                     (rid, "y", x - half, y - half, y + d + half), (rid, "y", x + w + half, y - half, y + d + half)]
    enclosure = {**floor, "rooms": list(rooms.values()), "partitions": []}
    for index, wall in enumerate(walls(enclosure, t, include_envelope=False)):
        matching = [edge for edge in outlines if edge[1] == wall["axis"] and math.isclose(edge[2], wall["at"], abs_tol=1e-6)]
        points = sorted({wall["start"], wall["end"], *(v for edge in matching for v in edge[3:] if wall["start"] < v < wall["end"])})
        for i, (start, end) in enumerate(zip(points, points[1:])):
            owners = [edge[0] for edge in matching if edge[3] <= (start + end) / 2 <= edge[4]]
            if not owners:
                raise ValueError("Unclassified roof enclosure wall")
            rid = max(owners, key=lambda key: heights[key])
            part = {**wall, "start": start, "end": end}
            for j, (begin, finish, height) in enumerate(wall_parts(part, floor["openings"], heights[rid])):
                if height <= layout["section_height"]:
                    continue
                rect = ([begin, wall["at"] - half, finish - begin, t] if wall["axis"] == "x"
                        else [wall["at"] - half, begin, t, finish - begin])
                obj = box(f"weather.wall.{index}.{i}.{j}", rect, layout["section_height"], height - layout["section_height"], material("wall"))
                obj["room_id"] = rid
    roofs = []
    for rid, room in rooms.items():
        x, y, w, d = room["rect"]
        rect = [x - t, y - t, w + 2 * t, d + 2 * t]
        for i, piece in enumerate(subtract_rectangles(rect, [r for r, z in roofs if z == heights[rid]])):
            roof = box(f"weather.{rid}.roof.{i}", piece, heights[rid], layout["weather_protection"]["roof_thickness_ft"], material("stone"))
            roof["room_id"] = rid
        roofs.append((rect, heights[rid]))
    for index, opening in enumerate(floor["openings"]):
        owners = [rid for rid in opening["connects"] if rid in rooms]
        if not owners:
            continue
        rid = max(owners, key=lambda key: heights[key])
        top = heights[rid]
        rect = ([opening["start"], opening["at"] - half, opening["width"], t] if opening["axis"] == "x"
                else [opening["at"] - half, opening["start"], t, opening["width"]])
        lintel = box(f"weather.{rid}.lintel.{index}", rect, 7, top - 7, material("wall"))
        lintel["room_id"] = rid
        if "lift_lobby" in opening["connects"]:
            leaf = ([opening["start"] + .06, opening["at"] - .04, opening["width"] - .12, .08] if opening["axis"] == "x"
                    else [opening["at"] - .04, opening["start"] + .06, .08, opening["width"] - .12])
            door = box("weather.stairs.weather_door", leaf, 0, 7, material("wood"))
            door["room_id"] = "stairs"
            door["weather_seal_intent"] = True
    for obj in CURRENT.objects:
        obj["weather_cover"] = True
        obj["role"] = "weather_cover"
        obj["engineering_status"] = "not_engineered"
    CURRENT = parent


def driveway_geometry(layout):
    global CURRENT
    road = Driveway(layout["ramp"])
    sections = road.sections()
    finish = layout["ramp"]["surface_finish_ft"]
    ground = next(f for f in layout["floors"] if f["id"] == "ground")
    house_edge = ground["envelope"][0] + ground["envelope"][2]
    before = set(CURRENT.objects)
    vertices = []
    for p in sections:
        vertices.extend([(*p.offset(-p.inner), p.z + finish), (*p.offset(p.outer), p.z + finish)])
    faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(sections) - 1)]
    surface = surface_mesh("ramp.surface", vertices, faces, material("ramp", "#88928d"))
    surface["role"] = "driveway_surface"
    for side in ["inner", "outer"]:
        vertices, faces = [], []
        for a, b in zip(sections, sections[1:]):
            pa, pb = a.offset(-a.inner if side == "inner" else a.outer), b.offset(-b.inner if side == "inner" else b.outer)
            polygon = clipped_x([(*pa, a.z - .15), (*pb, b.z - .15), (*pb, .25), (*pa, .25)], house_edge)
            if len(polygon) >= 3:
                offset = len(vertices)
                vertices.extend(polygon)
                faces.append(tuple(range(offset, len(vertices))))
        wall = surface_mesh(f"ramp.retaining.{side}", vertices, faces, material("stone"))
        wall["role"] = "driveway_retaining_intent"
        vertices, faces = [], []
        for a, b in zip(sections, sections[1:]):
            pa, pb = a.offset(-a.inner if side == "inner" else a.outer), b.offset(-b.inner if side == "inner" else b.outer)
            za = ground["elevation"] if pa[1] >= layout["site"]["back_start"] else 0
            zb = ground["elevation"] if pb[1] >= layout["site"]["back_start"] else 0
            polygon = clipped_x([(*pa, za + .15), (*pb, zb + .15), (*pb, zb + 3.5), (*pa, za + 3.5)], house_edge)
            if len(polygon) >= 3:
                offset = len(vertices)
                vertices.extend(polygon)
                faces.append(tuple(range(offset, len(vertices))))
        guard = surface_mesh(f"ramp.guard.{side}", vertices, faces, material("guard"))
        guard["role"] = "driveway_edge_guard"
    for index, station in enumerate([4, road.arc_end + 2]):
        p = road.at(station)
        a, b = p.offset(-p.inner), p.offset(p.outer)
        for i in range(12):
            start = (a[0] + (b[0] - a[0]) * i / 12, a[1] + (b[1] - a[1]) * i / 12, p.z + finish + .015)
            end = (a[0] + (b[0] - a[0]) * (i + .7) / 12, a[1] + (b[1] - a[1]) * (i + .7) / 12, p.z + finish + .015)
            grate = rod(f"ramp.drain.{index}.{i}", start, end, .025, material("metal"))
            grate["role"] = "drainage_intent"
    context = bpy.data.collections.new("DRIVEWAY CUTAWAY CONTEXT")
    for obj in set(CURRENT.objects) - before:
        obj["context_group"] = "driveway"
        obj["review_required"] = layout["ramp"]["status"]
        context.objects.link(obj)
    parent = CURRENT
    CURRENT = weather_collection()
    clear = layout["weather_protection"]["ramp_roof_clear_height_ft"]
    overhang = layout["weather_protection"]["ramp_roof_overhang_ft"]
    lower = [(*p.offset(-p.inner - overhang), clear + .25) for p in sections]
    lower += [(*p.offset(p.outer + overhang), clear) for p in reversed(sections)]
    lower = clipped_x(lower, house_edge)
    roof = solid_polygon("ramp.canopy.roof", lower, layout["weather_protection"]["ramp_roof_thickness_ft"], material("metal"))
    roof["role"] = "weather_cover"
    for station in range(4, math.ceil(road.arc_end), 12):
        p = road.at(station)
        for side, distance in [("inner", -p.inner - .2), ("outer", p.outer + .2)]:
            x, y = p.offset(distance)
            if x >= house_edge + .2:
                post = box(f"ramp.canopy.post.{station}.{side}", [x - .1, y - .1, .2, .2], .1, clear - .1, material("metal"))
                post["role"] = "weather_support_proxy"
    for obj in CURRENT.objects:
        obj["weather_cover"] = True
        obj["context_group"] = "driveway"
        obj["engineering_status"] = "not_engineered"
    CURRENT = parent
    return context


def site_geometry(layout):
    ROOM_BOUNDS.update({item["id"]: item["rect"] for item in layout["outdoor"]})
    width, depth = layout["site"]["width"], layout["site"]["depth"]
    road = Driveway(layout["ramp"])
    outdoors = {item["id"]: item for item in layout["outdoor"]}
    pool = outdoors.get("pool")
    if pool is None and not any(item["id"] == "pool" and item["status"] == "deferred_for_compact_site"
                                for item in layout.get("deferred_outdoor", [])):
        raise ValueError("Pool must be modeled with its barrier or explicitly deferred")
    ground = next(f for f in layout["floors"] if f["id"] == "ground")
    basement = next(f for f in layout["floors"] if f["id"] == "basement")
    bx, by, bw, bd = basement["envelope"]
    rear = layout["site"]["back_start"]
    terrain = box("terrain", [0, 0, width, depth], -.25, .25, material("garden"), 0)
    fill = box("rear_garden.fill_intent", [bx, rear, width - bx, depth - rear],
               0, ground["elevation"], material("garden"), 0)
    fill["engineering_status"] = "not_engineered"
    scene = bpy.context.scene
    scene.collection.children.link(CURRENT)
    cuts = [road.polygon()]
    for x, y, w, d in ([pool["rect"]] if pool else []) + floor_footprints(ground):
        cuts.append([(x, y), (x + w, y), (x + w, y + d), (x, y + d)])
    basement_cut = [(bx, by), (bx + bw, by), (bx + bw, by + bd), (bx, by + bd)]
    for target, openings in [(terrain, cuts), (fill, cuts + [basement_cut])]:
        for i, polygon in enumerate(openings):
            cutter = solid_polygon(f"{target.name}.cut.{i}", [(x, y, -20) for x, y in polygon], 40, material("garden"))
            modifier = target.modifiers.new(f"Real site opening {i}", "BOOLEAN")
            modifier.operation, modifier.solver, modifier.object = "DIFFERENCE", "EXACT", cutter
            bpy.context.view_layer.objects.active = target
            target.select_set(True)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            mesh = cutter.data
            bpy.data.objects.remove(cutter, do_unlink=True)
            bpy.data.meshes.remove(mesh)
    scene.collection.children.unlink(CURRENT)
    deck = box("rear_garden.structural_deck_intent", [bx, rear, bw, by + bd - rear],
               ground["elevation"] - .5, .5, material("slab"), 0)
    deck["engineering_status"] = "not_engineered"
    path = outdoors["entry_path"]["rect"]
    entry_steps = [path[0], ground["envelope"][1] - 3, path[2], 3]
    for i, piece in enumerate(subtract_rectangles(outdoors["front_veranda"]["rect"], [entry_steps])):
        plinth = box(f"front_veranda.plinth.{i}", piece, 0, ground["elevation"], material("stone"), 0)
        plinth["engineering_status"] = "not_engineered"
    for item in layout["outdoor"]:
        if item["kind"] in {"barrier", "pool"}:
            continue
        paths = [p["rect"] for p in layout["outdoor"] if p["kind"] == "path"]
        pieces = subtract_rectangles(item["rect"], paths + floor_footprints(ground)) if item["kind"] in {"garden", "veranda"} else [item["rect"]]
        level = ground["elevation"] if item["rect"][1] >= rear or item["kind"] == "veranda" or item["id"] == "drying" else 0
        for i, piece in enumerate(pieces):
            for j, part in enumerate(subtract_rectangles(piece, [entry_steps])):
                box(f"{item['id']}.{i}.{j}", part, level + (.01 if item["kind"] != "path" else .025), .04, material(item["kind"]))
    for index in range(3):
        step = box(f"entry.step.{index}", [path[0], ground["envelope"][1] - 3 + index, path[2], 1],
                   0, ground["elevation"] * (index + 1) / 3, material("stone"))
        step["role"] = "entry_step"
        step["engineering_status"] = "not_engineered"
    driveway_geometry(layout)
    if pool:
        barrier = outdoors["pool_barrier"]
        x, y, w, d = pool["rect"]
        level = ground["elevation"]
        box("pool.bottom", [x, y, w, d], level - 4, 0.2, material("pool"))
        box("pool.water", [x, y, w, d], level - .35, .03, material("water", "#71b7bd"))
        for r in [[x, y, w, 0.2], [x, y + d, w, 0.2], [x, y, 0.2, d], [x + w, y, 0.2, d]]:
            box("pool.shell", r, level - 4, 4, material("stone", "#ddd9cb"))
        rail("pool.barrier", barrier["rect"], z=level, height=4, gate="west")
        text("pool.label", f"POOL\n{w:g} x {d:g} ft", x + w / 2, y + d / 2, level - .29, .8)
    tx, ty, tw, td = outdoors["tree_buffer"]["rect"]
    for i in range(3):
        x, y, z = tx + tw * (i + .5) / 3, ty + td / 2, ground["elevation"]
        cylinder(f"tree.{i}.planter", x, y, z, 1.3, .6, material("stone"))
        cylinder(f"tree.{i}.trunk", x, y, z + .6, .15, 3.6, material("trunk", "#80664c"))
        oval(f"tree.{i}.canopy", [x - 1.5, y - 1.5, 3, 3], z + 3, 4, material("foliage_light", "#82916a"))
    for i, (x, y) in enumerate([(8, 6), (14, 6), (28, 5), (33, 5)]):
        cylinder(f"front_shrub.{i}", x, y, 0.1, 1.5, 1.7, material("foliage", "#62834b"))
    vx, vy, vw, vd = outdoors["back_veranda"]["rect"]
    for x in [vx + .5, vx + vw - .8]:
        for y in [vy + .4, vy + vd - .7]:
            box("veranda.post", [x, y, .3, .3], ground["elevation"], 9, material("wood", "#bc986e"))
    furnishing({"id": "veranda_swing", "room": "back_veranda", "kind": "sofa", "rect": [vx + vw - 10, vy + 1, 7, 3]})
    for obj in CURRENT.objects:
        if obj.get("fixture_id") == "veranda_swing":
            obj.location.z += feet(ground["elevation"])
    for x in [vx + vw - 9.7, vx + vw - 3.3]:
        cylinder("swing.hanger", x, vy + 2.5, ground["elevation"] + 2, .035, 7, material("guard", "#60736a"))
    fx, fy, fw, fd = outdoors["front_veranda"]["rect"]
    for i, x in enumerate([fx + 3, path[0] + path[2] + 2]):
        furnishing({"id": f"tea_table_{i}", "room": "front_veranda", "kind": "table", "rect": [x, fy + 1.5, 3, 2.5]})
        for obj in CURRENT.objects:
            if obj.get("fixture_id") == f"tea_table_{i}":
                obj.location.z += feet(ground["elevation"])
    text("site.title", "DREAM HOME  /  " + layout["id"].replace("-", " ").upper(), width / 2, -5, .1, 1.4)
    text("site.disclaimer", f"{width * depth:,.0f} sq ft PROPOSED SITE  |  NOT AN APPROVED PLAN", width / 2, -8, .1, .7)
    text("site.front", "FRONT / ROAD - NOT NORTH", width / 2, -1.8, .1, .65)


def exterior_geometry(layout):
    """Finished-looking shell, boundary, planting and context for exterior presentation only."""
    global CURRENT, FLOOR_ID
    spec = layout["exterior"]
    t = layout["wall_thickness"]
    floors = {f["id"]: f for f in layout["floors"]}
    ground, first, roof = floors["ground"], floors["first"], floors["roof"]
    FLOOR_ID = "exterior"
    CURRENT = bpy.data.collections.new("EXTERIOR")
    CURRENT["status"] = "unapproved_concept"
    CURRENT["presentation_only"] = True
    plaster, trim = material("plaster", "#e8dfcb"), material("plaster_trim", "#f1ead8")
    rubble, frame = material("facade_stone", "#a89d8b"), material("frame", "#38403f")
    glass, timber = material("facade_glass", "#86aeb3"), material("timber", "#8d6a47")
    slab_material, brass = material("slab", "#ddd7c9"), material("brass", "#b39a6f")
    fw, plinth_top = spec["frame_ft"], ground["elevation"] + spec["plinth_height"]
    levels = [(ground, 0, first["elevation"] - .5), (first, first["elevation"] - .5, roof["elevation"] - .5)]

    def plan(edge, a, b, d0, d1):
        return ([a, edge["origin"] + d0, b - a, d1 - d0] if edge["axis"] == "x" else [edge["origin"] + d0, a, d1 - d0, b - a])

    for floor, bottom, top in levels:
        for i, rect in enumerate(floor_footprints(floor)):
            box(f"slab.{floor['id']}.{i}", rect, floor["elevation"] - .5, .5, slab_material, 0)
        for i, piece in enumerate(facade_pieces(floor, layout, bottom, top)):
            z0, z1 = piece["z"]
            name = f"wall.{floor['id']}.{i}"
            if floor is ground and z0 < plinth_top:
                split = min(z1, plinth_top)
                box(name + ".stone", piece["rect"], z0, split - z0, rubble, 0)
                if z1 > split + 1e-6:
                    box(name + ".plaster", piece["rect"], split, z1 - split, plaster, 0)
            else:
                box(name, piece["rect"], z0, z1 - z0, plaster, 0)
        edges = facade_edges(floor, t)
        for index, o in enumerate(facade_openings(floor, layout)):
            edge, a, b = edges[o["edge"]], o["start"], o["end"]
            name = f"{floor['id']}.opening.{index}"
            door = o["kind"] == "door"
            if not door:
                box(name + ".glass", plan(edge, a + fw, b - fw, t / 2 - .04, t / 2 + .04), o["sill"] + fw, o["head"] - o["sill"] - 2 * fw, glass, 0)
                box(name + ".sill", plan(edge, a, b, t * .08, t * .92), o["sill"], fw, frame, .01)
            box(name + ".head", plan(edge, a, b, t * .08, t * .92), o["head"] - fw, fw, frame, .01)
            for side, (lo, hi) in enumerate([(a, a + fw), (b - fw, b)]):
                box(f"{name}.jamb.{side}", plan(edge, lo, hi, t * .08, t * .92), o["sill"], o["head"] - o["sill"], frame, .01)
            if not door:
                panes = max(1, round(o["width"] / 4))
                for k in range(1, panes):
                    along = a + o["width"] * k / panes
                    box(f"{name}.mullion.{k}", plan(edge, along - .06, along + .06, t * .3, t * .7), o["sill"] + fw, o["head"] - o["sill"] - 2 * fw, frame, 0)
            else:
                box(name + ".leaf", plan(edge, a + fw, b - fw, t * .3, t * .55), o["sill"], o["head"] - o["sill"] - fw, timber, .02)
                for k in range(1, 6):
                    box(f"{name}.batten.{k}", plan(edge, a + fw + k * (o["width"] - 2 * fw) / 6 - .03, a + fw + k * (o["width"] - 2 * fw) / 6 + .03, t * .22, t * .3),
                        o["sill"] + .2, o["head"] - o["sill"] - fw - .4, timber, 0)
                box(name + ".pull", plan(edge, b - fw - .6, b - fw - .45, t * .12, t * .22), o["sill"] + 2.8, 1.8, brass, .02)
            if o["edge"] in {"left", "right"} or floor is first:
                p, ov, th = spec["window_hood"]["projection"], spec["window_hood"]["overhang"], spec["window_hood"]["thickness"]
                if o["edge"] == "front":
                    rect = [a - ov, edge["origin"] - p, o["width"] + 2 * ov, p + .1]
                elif o["edge"] == "rear":
                    rect = [a - ov, edge["origin"] + t - .1, o["width"] + 2 * ov, p + .1]
                elif o["edge"] == "left":
                    rect = [edge["origin"] - p, a - ov, p + .1, o["width"] + 2 * ov]
                else:
                    rect = [edge["origin"] + t - .1, a - ov, p + .1, o["width"] + 2 * ov]
                box(name + ".hood", rect, o["head"] + .12, th, trim, .03)
    pj, depth = spec["fascia"]["projection"], spec["fascia"]["depth"]
    for floor, _, top in levels:
        x, y, w, d = floor["envelope"]
        for i, rect in enumerate([[x - pj, y - pj, w + 2 * pj, pj + t], [x - pj, y + d - t, w + 2 * pj, pj + t],
                                  [x - pj, y + t, pj + t, d - 2 * t], [x + w - t, y + t, pj + t, d - 2 * t]]):
            box(f"fascia.{floor['id']}.{i}", rect, top - depth + .5, depth, trim, .04)
    first_e = first["elevation"]
    for b in layout["balconies"]:
        x, y, w, d = b["rect"]
        box(b["id"] + ".slab", b["rect"], first_e - .5, .4, trim, .03)
        box(b["id"] + ".soffit", [x - .05, y - .05, w + .1, d + .1], first_e - .62, .12, timber, 0)
        box(b["id"] + ".deck", b["rect"], first_e - .1, .1, timber, 0)
        edge_y = y if y < ground["envelope"][1] else y + d
        guard_panel(b["id"] + ".guard", [x, edge_y, w, .12], first_e, 3.5)
        for edge_x in [x, x + w]:
            guard_panel(b["id"] + ".end", [edge_x, y, .12, d], first_e, 3.5)
    for column in spec["columns"]:
        x, y, w, d = column["rect"]
        box(column["id"], column["rect"], ground["elevation"], first_e - .5 - ground["elevation"], rubble, 0)
        box(column["id"] + ".cap", [x - .1, y - .1, w + .2, d + .2], first_e - .8, .3, trim, .03)
    ax, ay, aw, ad = ground["annexes"][0]["rect"]
    tower_top = roof["elevation"]
    slot = spec["lift_tower"]
    cx, half = ax + aw / 2, slot["slot_width"] / 2
    for i, rect in enumerate([[ax, ay, cx - half - ax, t], [cx + half, ay, ax + aw - cx - half, t],
                              [ax, ay + t, t, ad - t], [ax + aw - t, ay + t, t, ad - t]]):
        box(f"lift_tower.wall.{i}", rect, 0, tower_top, rubble, 0)
    slot_rect = [cx - half, ay, 2 * half, t]
    box("lift_tower.below_slot", slot_rect, 0, slot["slot_bottom"], rubble, 0)
    box("lift_tower.above_slot", slot_rect, slot["slot_top"], tower_top - slot["slot_top"], rubble, 0)
    box("lift_tower.glass", [cx - half + fw, ay + t / 2 - .04, 2 * half - 2 * fw, .08], slot["slot_bottom"],
        slot["slot_top"] - slot["slot_bottom"], glass, 0)
    for k, along in enumerate([cx - half, cx + half - fw]):
        box(f"lift_tower.jamb.{k}", [along, ay + t * .08, fw, t * .84], slot["slot_bottom"], slot["slot_top"] - slot["slot_bottom"], frame, .01)
    for k in range(5):
        along = cx - half + .45 + k * (2 * half - .9) / 4
        box(f"lift_tower.fin.{k}", [along - .1, ay - .5, .2, .5], slot["slot_bottom"], slot["slot_top"] - slot["slot_bottom"], timber, .01)
    box("lift_tower.car", [cx - 1.6, ay + t + .9, 3.2, 4.2], ground["elevation"], 7.5, material("metal"), .05)
    box("lift_tower.cap", [ax - .2, ay - .2, aw + .4, ad + .2], tower_top - .3, .3, trim, .04)
    site = layout["site"]
    bd = spec["boundary"]
    bt, bh = bd["thickness"], bd["height"]
    stone = material("boundary_stone", "#a89d8b")
    gaps = sorted((g for g in bd["gaps"] if g["edge"] == "front"), key=lambda g: g["start"])
    front, cursor = [], 0
    for gap in gaps:
        front.append((cursor, gap["start"]))
        cursor = gap["end"]
    front.append((cursor, site["width"]))
    walls_ = [("front", [a, 0, b - a, bt]) for a, b in front if b > a]
    walls_ += [("left", [0, bt, bt, site["depth"] - 2 * bt]), ("right", [site["width"] - bt, bt, bt, site["depth"] - 2 * bt]),
               ("rear", [0, site["depth"] - bt, site["width"], bt])]
    for i, (side, rect) in enumerate(walls_):
        box(f"boundary.{side}.{i}", rect, 0, bh, stone, 0)
        box(f"boundary.{side}.{i}.cap", [rect[0] - .05, rect[1] - .05, rect[2] + .1, rect[3] + .1], bh, .2, trim, .02)
    ps = bd["post_size"]
    for gap in gaps:
        for x in [gap["start"] - ps, gap["end"]]:
            box(f"gate_post.{gap['id']}.{x:g}", [x, bt / 2 - ps / 2, ps, ps], 0, bd["post_height"], stone, .03)
            box(f"gate_post.{gap['id']}.{x:g}.cap", [x - .12, bt / 2 - ps / 2 - .12, ps + .24, ps + .24], bd["post_height"], .3, trim, .03)
    far = 1800
    for i, rect in enumerate([[-far, -far, 2 * far + site["width"], far - 22], [-far, -2, 2 * far + site["width"], 2],
                              [-far, 0, far, site["depth"] + far], [site["width"], 0, far, site["depth"] + far],
                              [0, site["depth"], site["width"], far]]):
        box(f"context.{i}", rect, -.25, .4 if i == 1 else .25, material("path_context", "#cfc8b9") if i == 1 else material("context", "#7b9657"), 0)
    box("context.road", [-far, -22, 2 * far + site["width"], 20], -.25, .25, material("road", "#5b5d5f"), 0)
    for k in range(7):
        box(f"context.road_mark.{k}", [site["width"] / 2 - 70 + k * 24, -13, 9, .5], 0, .02, material("path_context", "#cfc8b9"), 0)
    planting_geometry(layout)
    ridges = [("ridge_far", "#9fb5a6", -300, 1500, 1500, 380, 420), ("ridge_near", "#7f9b82", 500, 1200, 1100, 320, 260),
              ("ridge_far", "#9fb5a6", 1500, 400, 900, 520, 360), ("ridge_near", "#7f9b82", 1250, -300, 900, 300, 250),
              ("ridge_far", "#9fb5a6", -1500, 300, 800, 560, 380), ("ridge_near", "#7f9b82", -1100, 900, 900, 320, 240),
              ("ridge_far", "#9fb5a6", 300, -1500, 1600, 400, 340), ("ridge_near", "#7f9b82", -900, -1000, 1100, 300, 220)]
    for i, (finish, color, cx, cy, width, depth, height) in enumerate(ridges):
        oval(f"ridge.{i}", [site["width"] / 2 + cx - width / 2, site["depth"] / 2 + cy - depth / 2, width, depth], -height * .6, height, material(finish, color), detail=(24, 10))
    FLOOR_ID = "exterior"
    return CURRENT


def cone(name, x, y, z, radius, height, mat, segments=14):
    vertices = [(x + radius * math.cos(i * math.tau / segments), y + radius * math.sin(i * math.tau / segments), z)
                for i in range(segments)] + [(x, y, z + height), (x, y, z)]
    faces = [(i, (i + 1) % segments, segments) for i in range(segments)]
    faces += [((i + 1) % segments, i, segments + 1) for i in range(segments)]
    obj = surface_mesh(name, vertices, faces, mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def broadleaf(name, x, y, level, height, canopy, index, foliage, trunk):
    trunk_height = height * .45
    cylinder(name + ".trunk", x, y, level, .2 + .01 * height, trunk_height, trunk)
    crown = height - trunk_height
    seed = (index * 7919 + 17) % 1000
    count = 15
    for k in range(count):
        t = (k + .5) / count
        angle = k * 2.399963 + seed * .013
        ring = math.sqrt(t) * canopy * .34
        lump = canopy * (.3 + .1 * ((seed + k * 37) % 5) / 4)
        cz = level + trunk_height + crown * (.34 + .5 * (1 - t) ** .6) - lump * .2
        oval(f"{name}.leaf.{k}", [x + math.cos(angle) * ring - lump / 2, y + math.sin(angle) * ring - lump / 2, lump, lump * .88],
             cz - lump * .4, lump * .8, foliage[(index + k) % 3], detail=(12, 8))
    for k in range(3):
        angle = seed * .02 + k * 2.1
        rod(f"{name}.branch.{k}", (x, y, level + trunk_height * .75), (x + math.cos(angle) * canopy * .2, y + math.sin(angle) * canopy * .2, level + trunk_height + crown * .22), .06, trunk)


def conifer(name, x, y, level, height, canopy, index, foliage, trunk):
    cylinder(name + ".trunk", x, y, level, .22, height * .22, trunk)
    tiers = 9
    for k in range(tiers):
        t = k / (tiers - 1)
        radius = canopy / 2 * (1 - .8 * t) + .3 + .12 * ((k * 5 + index) % 3)
        tier_height = height * (.2 - .05 * t)
        cone(f"{name}.tier.{k}", x + .08 * ((k + index) % 3 - 1), y + .08 * ((k * 2 + index) % 3 - 1),
             level + height * (.14 + .72 * t), radius, tier_height, foliage[(index + k) % 3], 11)


def planting_geometry(layout):
    spec = layout["exterior"]
    ground = next(f for f in layout["floors"] if f["id"] == "ground")
    foliage = [material("leaf_a", "#587a3e"), material("leaf_b", "#6f9348"), material("leaf_c", "#46663a")]
    trunk, hedge, soil = material("trunk", "#80664c"), material("hedge", "#4d6e3c"), material("soil", "#5b4636")
    blooms = [material("bloom", "#e0a131"), material("bloom_pink", "#cf7e96")]
    for index, plant in enumerate(spec["planting"]):
        name = plant["id"]
        if plant["kind"] in {"tree", "conifer", "shrub"}:
            x, y = plant["at"]
            level = ground["elevation"] if y >= layout["site"]["back_start"] else 0
        if plant["kind"] == "tree":
            broadleaf(name, x, y, level, plant["height"], plant["canopy"], index, foliage, trunk)
        elif plant["kind"] == "conifer":
            conifer(name, x, y, level, plant["height"], plant["canopy"], index, [material("pine_a", "#2f4a33"), material("pine_b", "#3b5a3d"), material("pine_c", "#274030")], trunk)
        elif plant["kind"] == "shrub":
            r = plant["radius"]
            oval(name, [x - r, y - r, 2 * r, 2 * r], level, plant["height"], foliage[index % 3])
            oval(name + ".b", [x - r * .55 + .5, y - r * .55, r * 1.2, r * 1.2], level + plant["height"] * .35, plant["height"] * .7, foliage[(index + 1) % 3])
        elif plant["kind"] == "hedge":
            box(name, plant["rect"], 0, plant["height"], hedge, .4)
        elif plant["kind"] == "flower_bed":
            x0, y0, w, d = plant["rect"]
            box(name + ".soil", plant["rect"], 0, .5, soil, .05)
            count = int(w / 1.1)
            for k in range(count):
                cx = x0 + (k + .5) * w / count
                for row, cy in enumerate([y0 + d * .3, y0 + d * .7]):
                    oval(f"{name}.bloom.{k}.{row}", [cx - .4, cy - .4, .8, .8], .45, plant["height"] - .1, blooms[(k + row) % 2])


def exterior_roof_source(collections):
    source = bpy.data.collections.new("EXTERIOR ROOF TERRACE SOURCE")
    for obj in collections["roof"].objects:
        if obj.type == "MESH":
            source.objects.link(obj)
    for child in collections["roof"].children:
        if "WEATHER" in child.name:
            for obj in child.all_objects:
                if obj.type == "MESH":
                    source.objects.link(obj)
    return source


def new_exterior_scene(name, collections, view):
    scene = bpy.data.scenes.new(name)
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    for collection in collections:
        scene.collection.children.link(collection)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 96
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .02
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 2400, 1600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new(name + ".world")
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(48)
    sky.air_density, sky.aerosol_density = 1.0, .6
    background = nodes["Background"]
    background.inputs[1].default_value = .32
    links.new(sky.outputs["Color"], background.inputs[0])
    scene.world = world
    position, target = Vector(view["position"]), Vector(view["target"])
    forward = (target - position)
    forward.z = 0
    forward.normalize()
    side = Vector((-forward.y, forward.x, 0))
    sun_from = (-forward * .55 + side * .55 + Vector((0, 0, .95))).normalized()
    sun_data = bpy.data.lights.new(name + ".sun", "SUN")
    sun_data.energy, sun_data.angle = 4.4, math.radians(1.2)
    sun_data.color = (1, .94, .84)
    sun = bpy.data.objects.new(name + ".sun", sun_data)
    sun.rotation_euler = (-sun_from).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new(name + ".camera")
    cam_data.type, cam_data.lens, cam_data.sensor_width = "PERSP", view["lens_mm"], 36
    cam_data.clip_start, cam_data.clip_end = .3, 900
    cam = bpy.data.objects.new(name + ".camera", cam_data)
    cam.location = Vector(tuple(feet(v) for v in view["position"]))
    cam.rotation_euler = (Vector(tuple(feet(v) for v in view["target"])) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.view_settings.exposure = -.3
    scene["status"] = "UNAPPROVED EXTERIOR PRESENTATION - NOT CONSTRUCTION DOCUMENTATION"
    scene["exterior_view"] = view["id"]
    return scene


def new_scene(name, collections, target, camera_position, ortho):
    scene = bpy.data.scenes.new(name)
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    for collection in collections:
        scene.collection.children.link(collection)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 96
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .025
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 2400
    scene.render.resolution_y = 2600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new(name + ".world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.82, .86, .9, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .45
    scene.world = world
    sun_data = bpy.data.lights.new(name + ".sun", "SUN")
    sun_data.energy = 2.2
    sun_data.angle = math.radians(8)
    sun = bpy.data.objects.new(name + ".sun", sun_data)
    sun.rotation_euler = (math.radians(25), math.radians(-20), math.radians(-30))
    scene.collection.objects.link(sun)
    for label, offset, power, size, color in [
        ("softbox", (-38, -30, 70), 2200, 42, (1, .9, .76)),
        ("fill", (40, 32, 55), 1300, 32, (.78, .88, 1)),
    ]:
        data = bpy.data.lights.new(name + "." + label, "AREA")
        data.energy, data.size, data.color = power, feet(size), color
        light = bpy.data.objects.new(name + "." + label, data)
        light.location = Vector(tuple(feet(a + b) for a, b in zip(target, offset)))
        light.rotation_euler = (Vector(tuple(feet(v) for v in target)) - light.location).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(light)
    backdrop_z = -11 if any(c.name in {"SITE", "PHYSICAL LEVEL INSTANCES", "STRUCTURAL LEVEL INSTANCES"} for c in collections) else -1
    bpy.ops.mesh.primitive_plane_add(size=feet(1400), location=(feet(target[0]), feet(target[1]), feet(backdrop_z)))
    backdrop = bpy.context.object
    for collection in list(backdrop.users_collection):
        collection.objects.unlink(backdrop)
    scene.collection.objects.link(backdrop)
    backdrop.name = name + ".presentation_backdrop"
    backdrop["presentation_only"] = True
    backdrop.data.materials.append(material("backdrop", "#e7e9e4"))
    cam_data = bpy.data.cameras.new(name + ".camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = feet(ortho)
    cam = bpy.data.objects.new(name + ".camera", cam_data)
    cam.location = Vector(tuple(feet(v) for v in camera_position))
    direction = Vector(tuple(feet(v) for v in target)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene["status"] = "UNAPPROVED M1 SPATIAL STUDY - NOT CONSTRUCTION DOCUMENTATION"
    scene["source_layout"] = "house-spec/layout-study.json"
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_perspective = "CAMERA"
    return scene


def verify_fixture_bounds(layout, floor_scenes):
    checked = 0
    for floor in layout["floors"]:
        bpy.context.window.scene = floor_scenes[floor["id"]]
        bpy.context.view_layer.update()
        for item in floor["furniture"]:
            allowed = [item["rect"], *(dining_chairs(item["rect"]) if item["kind"] == "dining_table" else [])]
            parts = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.get("fixture_id") == item["id"]]
            if not parts:
                raise ValueError(f"Missing refined fixture: {item['id']}")
            for obj in parts:
                points = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
                for point in points:
                    px, py = point.x / feet(1), point.y / feet(1)
                    if not any(rx - .002 <= px <= rx + rw + .002 and ry - .002 <= py <= ry + rd + .002 for rx, ry, rw, rd in allowed):
                        raise ValueError(f"Refinement leaves the locked fixture footprint: {obj.name}, ({px:.4f}, {py:.4f})")
            checked += 1
    return checked


def main():
    global CURRENT, FLOOR_ID, STUDY_ID, FINISH_MAPS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, default=ROOT / "house-spec/layout-study.json")
    parser.add_argument("--spec", type=Path, default=ROOT / "house-spec/house.json")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / datetime.now().strftime("concept-%Y%m%d-%H%M%S"))
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    spec, layout = load_json(args.spec), load_json(args.layout)
    STUDY_ID = layout["id"]
    report = validate(spec, layout)
    if report["errors"]:
        raise ValueError("\n".join(report["errors"]))
    output = args.output.resolve()
    write_review(spec, layout, output)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATERIALS.clear()
    ROOM_BOUNDS.clear()
    FINISH_MAPS = create_maps(output / "textures")
    initial_scene = bpy.context.scene
    collections = {}
    structure_collections = {}
    for floor in layout["floors"]:
        FLOOR_ID = floor["id"]
        CURRENT = bpy.data.collections.new(FLOOR_ID.upper())
        CURRENT["elevation_ft"] = floor["elevation"]
        CURRENT["status"] = "unapproved_concept"
        collections[FLOOR_ID] = CURRENT
        floor_geometry(floor, layout)
        CURRENT = bpy.data.collections.new(FLOOR_ID.upper() + " STRUCTURE")
        CURRENT["engineering_status"] = "not_engineered"
        structure_collections[FLOOR_ID] = CURRENT
        structural_geometry(floor, layout)
    FLOOR_ID = "site"
    CURRENT = bpy.data.collections.new("SITE")
    collections["site"] = CURRENT
    site_geometry(layout)
    annotations = bpy.data.collections.new("SITE ANNOTATIONS")
    CURRENT.children.link(annotations)
    for obj in [o for o in CURRENT.objects if o.type == "FONT"]:
        CURRENT.objects.unlink(obj)
        annotations.objects.link(obj)
    cutaway_planting = bpy.data.collections.new("SITE CUTAWAY PLANTING")
    cutaway_planting["export_architecture"] = True
    CURRENT.children.link(cutaway_planting)
    for obj in [o for o in CURRENT.objects if o.name.startswith(("site.tree.", "site.front_shrub."))]:
        CURRENT.objects.unlink(obj)
        cutaway_planting.objects.link(obj)
        obj["cutaway_planting"] = True
    collections["exterior"] = exterior_geometry(layout)
    roof_source = exterior_roof_source(collections)
    roof_instance = bpy.data.collections.new("EXTERIOR ROOF INSTANCE")
    roof_marker = bpy.data.objects.new("roof.exterior_physical_level", None)
    roof_marker.instance_type, roof_marker.instance_collection = "COLLECTION", roof_source
    roof_marker.location.z = feet(next(f for f in layout["floors"] if f["id"] == "roof")["elevation"])
    roof_instance.objects.link(roof_marker)
    ground_floor = next(f for f in layout["floors"] if f["id"] == "ground")
    overview_ground = bpy.data.collections.new("OVERVIEW GROUND INSTANCE")
    instance = bpy.data.objects.new("ground.overview_physical_level", None)
    instance.instance_type, instance.instance_collection = "COLLECTION", collections["ground"]
    instance.location.z = feet(ground_floor["elevation"])
    overview_ground.objects.link(instance)
    overview = new_scene("01 - Garden and ground overview", [collections["site"], overview_ground],
                         (layout["site"]["width"] / 2, layout["site"]["depth"] * .46, 0),
                         (120, -85, 165), max(layout["site"]["width"] * 1.5, layout["site"]["depth"] * 1.3))
    scenes = [("overview", overview)]
    floor_scenes = {}
    for fid, title in [("ground", "02 - Ground plan"), ("basement", "03 - Basement plan"), ("first", "04 - First-floor plan"), ("roof", "05 - Roof terrace plan")]:
        scene = new_scene(title, [collections[fid]], (25, 41, 0), (25, 41, 150), 87)
        if fid == "basement":
            context = bpy.data.objects.new("basement.driveway_cutaway_context", None)
            context.instance_type = "COLLECTION"
            context.instance_collection = bpy.data.collections["DRIVEWAY CUTAWAY CONTEXT"]
            context.location.z = feet(-layout["floors"][0]["elevation"])
            context["presentation_only"] = True
            scene.collection.objects.link(context)
            scene.camera.location.x = feet(30)
            scene.camera.data.ortho_scale = feet(90)
        if fid == "roof":
            scene.view_layers[0].layer_collection.children["ROOF"].children["ROOF WEATHER COVERS"].exclude = True
        floor_scenes[fid] = scene
        scenes.append((fid, scene))
    assembly = bpy.data.collections.new("PHYSICAL LEVEL INSTANCES")
    for floor in layout["floors"]:
        instance = bpy.data.objects.new(f"{floor['id']}.physical_level", None)
        instance.instance_type = "COLLECTION"
        instance.instance_collection = collections[floor["id"]]
        instance.location.z = feet(floor["elevation"])
        assembly.objects.link(instance)
    new_scene("06 - Stacked physical levels", [collections["site"], assembly], (34, 48, 8), (145, -125, 140), 145)
    exploded = bpy.data.collections.new("EXPLODED LEVEL INSTANCES")
    CURRENT = exploded
    FLOOR_ID = "presentation"
    headings = {"basement": "BASEMENT", "ground": "GROUND FLOOR", "first": "FIRST FLOOR", "roof": "ROOF TERRACE"}
    for i, fid in enumerate(["basement", "ground", "first", "roof"]):
        floor = next(f for f in layout["floors"] if f["id"] == fid)
        instance = bpy.data.objects.new(fid + ".exploded", None)
        instance.instance_type = "COLLECTION"
        instance.instance_collection = collections[fid]
        instance.location = (feet(i * 68), 0, 0)
        instance["floor_id"] = fid
        exploded.objects.link(instance)
        text(f"{fid}.heading", headings[fid], 29 + i * 68, 99, size=1.65)
        text(f"{fid}.caption", f"Physical level {floor['elevation']:+g} ft  |  FRONT BELOW", 29 + i * 68, 5, size=0.85)
    text("comparison.title", "DREAM HOME / ALL FOUR LEVELS", 131, 108, size=2.2)
    text("comparison.subtitle", "SIDE-BY-SIDE STUDY - UNAPPROVED LAYOUT - LOW WALLS FOR VISIBILITY", 131, -2, size=1)
    comparison = new_scene("07 - All four plans side by side", [exploded], (131, 52, 0), (131, 52, 230), 290)
    comparison.render.resolution_x = 5200
    comparison.render.resolution_y = 2400
    scenes.append(("all-floors", comparison))
    for stem, name, fid, target, camera, ortho in [
        ("living-detail", "08 - Living and kitchen detail", "ground", (40, 56, 1), (55, 28, 41), 40),
        ("office-detail", "09 - Office detail", "first", (13.75, 29, 1), (21, 8, 31), 28),
        ("bedroom-detail", "10 - Bedroom detail", "first", (31.5, 29, 1), (39.5, 8, 33), 28),
    ]:
        detail = new_scene(name, [collections[fid]], target, camera, ortho)
        detail.render.resolution_y = 1800 if fid == "ground" else 2100
        scenes.append((stem, detail))
    frame_instances = bpy.data.collections.new("STRUCTURAL LEVEL INSTANCES")
    for floor in layout["floors"]:
        instance = bpy.data.objects.new(f"{floor['id']}.structural_level", None)
        instance.instance_type = "COLLECTION"
        instance.instance_collection = structure_collections[floor["id"]]
        instance.location.z = feet(floor["elevation"])
        frame_instances.objects.link(instance)
    frame = new_scene("11 - Structural intent NOT ENGINEERED", [frame_instances], (29, 48, 8), (130, -115, 125), 145)
    frame["structural_disclaimer"] = layout["structure"]["disclaimer"]
    scenes.append(("structural-stack", frame))
    for i, floor in enumerate(layout["floors"], start=12):
        fid = floor["id"]
        frame = new_scene(f"{i:02d} - {fid.title()} frame NOT ENGINEERED", [structure_collections[fid]],
                          (29, 48, 0), (80, -30, 145), 110)
        frame["structural_disclaimer"] = layout["structure"]["disclaimer"]
        scenes.append((f"structural-{fid}", frame))
    for i, view in enumerate(layout["exterior"]["views"], start=16):
        exterior_scene = new_exterior_scene(f"{i:02d} - Exterior {view['label']}",
                                            [collections["site"], collections["exterior"], roof_instance], view)
        scenes.append((f"exterior-{view['id']}", exterior_scene))
        bpy.context.window.scene = exterior_scene
        bpy.context.view_layer.update()
        layer = bpy.context.view_layer.layer_collection
        site_layer = layer.children.get("SITE") if layer else None
        if site_layer is None or not {"SITE ANNOTATIONS", "SITE CUTAWAY PLANTING"} <= set(site_layer.children.keys()):
            raise ValueError("Exterior scene could not hide site annotations and cutaway planting")
        site_layer.children["SITE ANNOTATIONS"].exclude = True
        site_layer.children["SITE CUTAWAY PLANTING"].exclude = True
    note = bpy.data.texts.new("START HERE - Study notes")
    note.write("DREAM HOME / " + STUDY_ID.replace("-", " ").upper() + " / UNAPPROVED CONCEPT\n\n"
               "This file opens with BASEMENT, GROUND, FIRST and ROOF placed side by side.\n"
               "Scroll to zoom; middle-mouse to orbit; Shift + middle-mouse to pan. Numpad 0 toggles camera view.\n"
               "Side-by-side objects reference the original floor collections; edit rooms in their individual floor scenes.\n"
               "Choose scenes from the scene selector: garden overview, individual plans, physical stack, side-by-side plans.\n"
               "Scenes 08-10 are composed living/kitchen, office and bedroom close-ups.\n"
               "Scenes 16-23 are FINISHED EXTERIOR presentation views from the EXTERIOR collection (full-height facade, boundary, gates, planting) plus the site and roof terrace. The cutaway floor collections are unchanged.\n"
               "All geometry is in metres. Room labels show proposed clear-zone dimensions in feet.\n"
               "Study 010 keeps the spacious 7,000 sq ft site, 4 ft ground galleries and unified upstairs lounge. The front-lawn lift has INTERNAL stair access; there is NO external side link.\n"
               "Five bedrooms, equal 272 sq ft children's rooms, equal recreation, three SUVs, eight toilets and pantry fridge remain. Larger gardens and an outboard 8 x 16 ft pool return.\n"
               "The guest room is wider; master has a private 3 ft entrance, bedroom-to-dressing-to-bath access. Child 1 bath/dressing occupy reclaimed office width, not lounge. Shared upstairs WC is beside stairs. Basement/roof remain unchanged from Study 008.\n"
               "A 4 x 2 ft cupboard faces left at the House Gallery terminal end, outside living. Upstairs shared WC is 6 x 5.5 ft; living/lounge net areas are 343.5/653 sq ft.\n"
               "The curved driveway checks a sampled large-SUV body sweep; independent parking and engineering remain unverified.\n"
               "Weather covers are separate Outliner collections. The roof plan and basement driveway context omit covers for inspection.\n"
               "The 9 x 17 ft U-stair is a geometry candidate, not approved headroom, fire/escape or code compliance.\n"
               "The aligned four-stop lift is a shaft/landing reserve, not a selected product or evacuation route.\n"
               "Scenes 11-15 show STRUCTURAL INTENT ONLY, NOT ENGINEERED. Proxy dimensions are not member sizes.\n"
               "Perimeter/core support positions and requested clear spans may be changed by an engineer.\n"
               "Room names/sizes live in each floor's LABELS collection above the cutaway walls.\n"
               "Dimension curves live in each floor's DIMENSIONS collection; toggle them in the Outliner.\n"
               "Material Preview shows the finishes. The saved Cycles cameras provide higher-quality renders.\n"
               "This is a visual concept, not a finished architectural shell or certified detailing.\n"
               "Ground is +1.5 ft above road; basement -8.5 ft. Three front steps and the raised rear garden/deck are concepts requiring accessibility, drainage and structural review.\n\n"
               + "\n".join("- " + item for item in report["review"]))
    bpy.context.window.scene = comparison
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.use_local_camera = False
                space.region_3d.view_location = (feet(131), feet(52), 0)
                space.region_3d.view_rotation = comparison.camera.rotation_euler.to_quaternion()
                space.region_3d.view_distance = feet(230)
                space.region_3d.view_camera_zoom = 0
                space.region_3d.view_camera_offset = (0, 0)
                space.region_3d.view_perspective = "CAMERA"
                space.shading.type = "MATERIAL"
                space.shading.color_type = "MATERIAL"
                space.overlay.show_extras = False
    bpy.data.scenes.remove(initial_scene)
    fixtures_checked = verify_fixture_bounds(layout, floor_scenes)
    bpy.context.window.scene = comparison
    # Finish renders and object diagnostics before publishing a new .blend.
    if not args.skip_render:
        for stem, scene in scenes:
            scene.render.filepath = str(output / f"{stem}.png")
            bpy.ops.render.render(write_still=True, scene=scene.name)
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    for obj in mesh_objects:
        if not all(math.isfinite(v) for vertex in obj.data.vertices for v in vertex.co):
            raise ValueError(f"Non-finite mesh coordinate: {obj.name}")
        spans = [max(vertex.co[i] for vertex in obj.data.vertices) - min(vertex.co[i] for vertex in obj.data.vertices) for i in range(3)]
        if any(span <= 0 for span in spans) and not obj.name.startswith("site.ramp.") and not obj.get("presentation_only"):
            raise ValueError(f"Degenerate object: {obj.name}")
    render_scenes = {stem: scene.name for stem, scene in scenes}
    blend_path = output / "dream-home-study.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    if "01 - Garden and ground overview" not in bpy.data.scenes or len(bpy.data.scenes) < 7:
        raise ValueError("Saved scene roundtrip failed")
    if bpy.context.scene.name != "07 - All four plans side by side":
        raise ValueError("Saved file must open with all four levels side by side")
    instances = [obj for obj in bpy.context.scene.objects if obj.instance_type == "COLLECTION"]
    if {obj.get("floor_id") for obj in instances} != {"basement", "ground", "first", "roof"} or len(instances) != 4:
        raise ValueError("Side-by-side scene must contain all four floor instances")
    result = {"blender": bpy.app.version_string, "blend": str(blend_path), "blend_bytes": blend_path.stat().st_size,
              "visual_quality": "refined-01", "layout_sha256": hashlib.sha256(args.layout.read_bytes()).hexdigest(),
              "brief_sha256": hashlib.sha256(args.spec.read_bytes()).hexdigest(),
              "locked_fixtures_checked": fixtures_checked, "packed_finish_maps": len(FINISH_MAPS),
              "structural_status": layout["structure"]["status"],
              "mesh_objects": len(mesh_objects), "scenes": [s.name for s in bpy.data.scenes],
              "opening_scene": bpy.context.scene.name,
              "render_scenes": render_scenes,
              "renders": [] if args.skip_render else [f"{stem}.png" for stem, _ in scenes],
              "geometry_status": report["geometry_status"], "overall_status": report["status"]}
    (output / "generation-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("DREAM_HOME_STUDY_SUCCESS " + json.dumps(result))


if __name__ == "__main__":
    main()

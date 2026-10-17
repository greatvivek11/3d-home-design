"""Deterministic, packed PBR finishes shared by Blender and glTF."""

from pathlib import Path
import struct
import zlib

import bpy
import numpy as np


def png(path, pixels):
    height, width, channels = pixels.shape
    if channels != 3 or pixels.dtype != np.uint8:
        raise ValueError("Finish maps must be RGB8")

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    rows = b"".join(b"\0" + row.tobytes() for row in pixels)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def create_maps(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    n = 512
    u, v = np.meshgrid(np.arange(n) / n, np.arange(n) / n)
    noise = np.random.default_rng(31).normal(0, 1, (n, n))
    maps = {}

    def save(name, pixels, color=False):
        path = directory / f"{name}.png"
        png(path, np.clip(pixels, 0, 255).astype(np.uint8))
        image = bpy.data.images.load(str(path))
        image.colorspace_settings.name = "sRGB" if color else "Non-Color"
        image.pack()
        maps[name] = image

    def surface(name, base, variation, height, roughness):
        save(name + "_color", np.asarray(base)[None, None, :] + variation[:, :, None], True)
        gx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 1.4
        gy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 1.4
        normals = np.stack([-gx, -gy, np.ones_like(gx)], axis=2)
        normals /= np.linalg.norm(normals, axis=2, keepdims=True)
        save(name + "_normal", (normals * 0.5 + 0.5) * 255)
        gray = np.clip(roughness + variation / 1000, 0, 1) * 255
        save(name + "_roughness", np.repeat(gray[:, :, None], 3, axis=2))

    board = np.floor(u * 8).astype(int)
    across = u * 8 - board
    grain = np.sin(2 * np.pi * (u * 96 + 0.25 * np.sin(v * 2 * np.pi)))
    grain += 0.38 * np.sin(2 * np.pi * (u * 248 + 0.6 * np.cos(v * 4 * np.pi)))
    offsets = np.array([0, .5, .25, .75, .5, .125, .625, .375])[board]
    joints = (np.minimum(across, 1 - across) < .009) | ((v + offsets) % 1 < .003)
    variation = grain * 3 + np.array([-6, 3, -1, 5, -3, 1, -4, 4])[board] + noise * .6
    variation = np.where(joints, -27, variation)
    surface("oak", [199, 175, 140], variation, grain * .07 - joints * .5, .48)
    surface("joinery", [177, 146, 108], grain * 2.5 + noise * .4, grain * .04, .46)
    save("walnut_color", np.array([134, 101, 73])[None, None, :] + (grain * 2.5 + noise * .4)[:, :, None], True)

    veins = np.sin(2 * np.pi * (u * 3 + .16 * np.sin(v * 4 * np.pi)))
    stone = np.sin(u * 22 * np.pi) * np.cos(v * 18 * np.pi) + noise * .7 + veins
    grout = (np.minimum(u % .5, .5 - u % .5) < .002) | (np.minimum(v % .5, .5 - v % .5) < .002)
    surface("stone", [220, 214, 201], np.where(grout, -21, stone * 1.5),
            stone * .015 - grout * .22, .62)
    surface("concrete", [173, 175, 168], stone * 2.2 + noise,
            stone * .025, .82)
    weave = np.sin(u * 128 * np.pi) * np.sin(v * 128 * np.pi)
    surface("linen", [232, 226, 212], weave * 4 + noise * .4, weave * .16, .88)
    save("sage_color", np.array([122, 144, 128])[None, None, :] + (weave * 3 + noise * .4)[:, :, None], True)
    save("curtain_color", np.array([175, 155, 185])[None, None, :] + (weave * 3 + noise * .4)[:, :, None], True)
    save("rug_color", np.array([184, 168, 144])[None, None, :] + (weave * 5)[:, :, None], True)
    save("grass_color", np.array([132, 150, 106])[None, None, :]
         + (stone * 3 + noise * 2)[:, :, None], True)
    return maps


def finish_material(name, color, maps):
    mat = bpy.data.materials.new(name)
    srgb = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    rgb = tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in srgb)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = .68
    families = {
        "bedroom": "oak", "living": "oak", "office": "oak", "storage": "oak",
        "wood": "joinery", "walnut": "joinery", "pergola": "joinery", "veranda": "oak",
        "bathroom": "stone", "kitchen": "stone", "circulation": "stone", "stone": "stone",
        "slab": "concrete", "garage": "concrete", "service": "concrete", "ramp": "concrete",
        "recreation": "concrete", "path": "stone",
        "linen": "linen", "upholstery": "linen", "curtain": "linen", "rug": "linen",
    }
    family = families.get(name)
    color_map = {"walnut": "walnut", "upholstery": "sage", "curtain": "curtain", "rug": "rug"}.get(name, family)
    if name == "garden":
        color_map = "grass"
    if color_map:
        image = mat.node_tree.nodes.new("ShaderNodeTexImage")
        image.image = maps[color_map + "_color"]
        image.interpolation = "Linear"
        mat.node_tree.links.new(image.outputs["Color"], shader.inputs["Base Color"])
        mat["texture_scale_ft"] = 1 if family == "linen" else 4
    if family:
        roughness = mat.node_tree.nodes.new("ShaderNodeTexImage")
        roughness.image = maps[family + "_roughness"]
        mat.node_tree.links.new(roughness.outputs["Color"], shader.inputs["Roughness"])
        normal = mat.node_tree.nodes.new("ShaderNodeTexImage")
        normal.image = maps[family + "_normal"]
        bump = mat.node_tree.nodes.new("ShaderNodeNormalMap")
        bump.inputs["Strength"].default_value = .2 if family == "linen" else .32
        mat.node_tree.links.new(normal.outputs["Color"], bump.inputs["Color"])
        mat.node_tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        if family in {"oak", "joinery"}:
            shader.inputs["Coat Weight"].default_value = .16
    if name in {"metal", "brass", "chrome", "solar_frame"}:
        shader.inputs["Metallic"].default_value = .85
        shader.inputs["Roughness"].default_value = .27
    if name in {"porcelain", "basin", "double_basin", "screen", "car", "water"}:
        shader.inputs["Roughness"].default_value = .19
        shader.inputs["Coat Weight"].default_value = .35
    if name in {"glass", "shower_glass"}:
        shader.inputs["Alpha"].default_value = .19
        shader.inputs["Roughness"].default_value = .12
        shader.inputs["Coat Weight"].default_value = .4
        mat.diffuse_color = (*rgb, .19)
        mat.surface_render_method = "DITHERED"
    if name == "rubber":
        shader.inputs["Roughness"].default_value = .93
    mat["finish"] = family or name
    return mat

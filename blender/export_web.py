"""Export canonical floor collections, not presentation duplicates, for the web."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.layout import feet, load_json, plan_svg, room_area, room_footprints, validate


TITLES = {"site": "Garden & site", "basement": "Basement", "ground": "Ground floor", "first": "First floor", "roof": "Roof terrace"}


def bounds(rect):
    x, y, w, d = rect
    return {"x": feet(x), "z": -feet(y + d), "width": feet(w), "depth": feet(d)}


def batch_meshes(scene):
    protected = {"role", "partition_id", "self_closing_intent", "soft_partition_intent", "shower_enclosure_intent"}
    groups = {}
    for obj in list(scene.objects):
        if obj.type != "MESH" or protected.intersection(obj.keys()) or ("room_id" in obj and "fixture_id" not in obj):
            continue
        if len(obj.data.materials) != 1:
            raise ValueError(f"Expected one finish before batching: {obj.name}")
        key = (json.dumps(dict(obj.items()), sort_keys=True), obj.data.materials[0].name)
        groups.setdefault(key, []).append(obj)
    for (_, finish), objects in groups.items():
        if len(objects) < 2:
            continue
        active = objects[0]
        with bpy.context.temp_override(active_object=active, selected_objects=objects, selected_editable_objects=objects):
            bpy.ops.object.join()
        active.name = f"web.{active['floor_id']}.{active.get('fixture_id', 'architecture')}.{finish}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--layout", type=Path, default=ROOT / "house-spec/layout-study.json")
    parser.add_argument("--model", type=Path, default=ROOT / "web/public/models/house.glb")
    parser.add_argument("--manifest", type=Path, default=ROOT / "web/src/generated/house.json")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    layout = load_json(args.layout)
    report = validate(load_json(ROOT / "house-spec/house.json"), layout)
    if report["errors"]:
        raise ValueError("\n".join(report["errors"]))
    blend = args.blend.resolve()
    if not blend.is_file():
        raise FileNotFoundError(f"Generate the Blender study first: {blend}")
    snapshot = blend.parent / "layout-snapshot.json"
    if not snapshot.is_file() or load_json(snapshot) != layout:
        raise ValueError("Blender study and layout do not match. Regenerate the study before exporting.")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    export_scene = bpy.data.scenes.new("WEB EXPORT - canonical local floor coordinates")
    bpy.context.window.scene = export_scene
    counts = {}
    for fid in TITLES:
        source = bpy.data.collections.get(fid.upper())
        if source is None:
            raise ValueError(f"Missing canonical collection: {fid.upper()}")
        group = bpy.data.objects.new(f"floor_{fid}", None)
        group["floor_id"] = fid
        group["status"] = "unapproved_concept"
        export_scene.collection.objects.link(group)
        counts[fid] = 0
        for obj in source.objects:
            if obj.type != "MESH":
                continue
            duplicate = obj.copy()
            duplicate.name = f"web.{obj.name}"
            duplicate.parent = group
            duplicate["floor_id"] = fid
            export_scene.collection.objects.link(duplicate)
            counts[fid] += 1
        if counts[fid] == 0:
            raise ValueError(f"Empty export floor: {fid}")
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in list(export_scene.objects):
        if obj.type == "MESH":
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
            obj.modifiers.clear()
            obj.data = mesh
    batch_meshes(export_scene)
    counts = {fid: sum(obj.type == "MESH" and obj.get("floor_id") == fid for obj in export_scene.objects) for fid in TITLES}
    args.model.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.model.with_name(args.model.stem + ".pending.glb")
    bpy.ops.export_scene.gltf(
        filepath=str(temporary.resolve()), export_format="GLB",
        use_active_scene=True, export_cameras=False, export_lights=False,
        export_extras=True, export_yup=True, export_apply=True, export_animations=False,
    )
    uncompressed_bytes = temporary.stat().st_size
    subprocess.run(["node", str(ROOT / "web/scripts/optimize-model.mjs"), str(temporary.resolve())], check=True)
    with temporary.open("rb") as stream:
        magic, version, length = struct.unpack("<4sII", stream.read(12))
        chunk_length, chunk_type = struct.unpack("<II", stream.read(8))
        document = json.loads(stream.read(chunk_length))
    if magic != b"glTF" or version != 2 or length != temporary.stat().st_size or chunk_type != 0x4E4F534A:
        raise ValueError("Invalid exported GLB")
    names = {node.get("name") for node in document["nodes"]}
    if not all(f"floor_{fid}" in names for fid in TITLES):
        raise ValueError("GLB lost canonical floor roots")
    revision = hashlib.sha256(temporary.read_bytes()).hexdigest()[:12]
    manifest = {
        "schema_version": 2, "study_id": layout["id"], "revision": revision,
        "visual_quality": "refined-01", "layout_sha256": hashlib.sha256(args.layout.read_bytes()).hexdigest(),
        "compression": "lossless_meshopt", "uncompressed_model_bytes": uncompressed_bytes,
        "status": "unapproved_concept", "model_bytes": length, "mesh_counts": counts,
        "site": {"width_ft": layout["site"]["width"], "depth_ft": layout["site"]["depth"], "area_sq_ft": report["plot_area_sq_ft"]},
        "floors": [
            {
                "id": floor["id"], "title": TITLES[floor["id"]],
                "elevation_m": feet(floor["elevation"]), "elevation_ft": floor["elevation"],
                "bounds": bounds(floor["envelope"]),
                "rooms": [
                    {"id": room["id"], "name": room["name"], "kind": room["kind"],
                     "width_ft": room["rect"][2], "depth_ft": room["rect"][3],
                     "area_sq_ft": room_area(floor, room),
                     "footprints": [bounds(rect) for rect in room_footprints(floor, room)],
                     "bounds": bounds(room["rect"])}
                    for room in floor["rooms"] if room["kind"] != "circulation" or room.get("label")
                ],
            } for floor in layout["floors"]
        ],
        "review_items": report["review"],
    }
    pending_manifest = args.manifest.with_suffix(".pending.json")
    pending_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary.replace(args.model)
    pending_manifest.replace(args.manifest)
    plans = args.model.parent.parent / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    for floor in [None, *layout["floors"]]:
        name = "site" if floor is None else floor["id"]
        pending_plan = plans / f"{name}.pending.svg"
        pending_plan.write_text(plan_svg(layout, floor))
        pending_plan.replace(plans / f"{name}.svg")
    print("WEB_EXPORT_SUCCESS " + json.dumps({"model": str(args.model), "bytes": length, "revision": revision, "floor_meshes": counts}))


if __name__ == "__main__":
    main()

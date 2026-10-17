"""Render saved study cameras without modifying the editable Blender file."""

import argparse
import json
from pathlib import Path
import sys

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--device", choices=["CPU", "METAL"], default="CPU")
    parser.add_argument("--scenes", nargs="+", help="Render stems from generation-result.json; defaults to all")
    parser.add_argument("--samples", type=int)
    parser.add_argument("--resolution", type=int, help="Override image width, preserving each camera's aspect ratio")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if any(value is not None and value <= 0 for value in [args.samples, args.resolution]):
        raise ValueError("Samples and resolution must be positive")
    blend = args.blend.resolve()
    metadata = blend.parent / "generation-result.json"
    result = json.loads(metadata.read_text())
    cameras = result["render_scenes"]
    selected = args.scenes or list(cameras)
    if set(selected) - cameras.keys():
        raise ValueError(f"Unknown render stems: {set(selected) - cameras.keys()}")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    if args.device == "METAL":
        preferences = bpy.context.preferences.addons["cycles"].preferences
        preferences.compute_device_type = "METAL"
        preferences.get_devices()
        if not any(device.type == "METAL" for device in preferences.devices):
            raise RuntimeError("Metal was requested but no Metal GPU is available; rerun with --device CPU")
        for device in preferences.devices:
            device.use = device.type == "METAL"
        print("RENDER_DEVICES", [device.name for device in preferences.devices if device.use])
    settings = result.setdefault("render_settings", {})
    for stem in selected:
        scene = bpy.data.scenes[cameras[stem]]
        scene.cycles.device = "GPU" if args.device == "METAL" else "CPU"
        if args.samples:
            scene.cycles.samples = args.samples
        if args.resolution:
            scene.render.resolution_y = round(args.resolution * scene.render.resolution_y / scene.render.resolution_x)
            scene.render.resolution_x = args.resolution
        pending = blend.parent / f"{stem}.pending.png"
        scene.render.filepath = str(pending)
        bpy.ops.render.render(write_still=True, scene=scene.name)
        pending.replace(blend.parent / f"{stem}.png")
        settings[stem] = {"width": scene.render.resolution_x, "height": scene.render.resolution_y,
                          "samples": scene.cycles.samples, "device": args.device}
    result["renders"] = sorted(set(result["renders"]) | {f"{stem}.png" for stem in selected})
    temporary = metadata.with_suffix(".pending.json")
    temporary.write_text(json.dumps(result, indent=2) + "\n")
    temporary.replace(metadata)
    print("STUDY_RENDER_SUCCESS", json.dumps({"directory": str(blend.parent), "renders": selected, "settings": settings}))


if __name__ == "__main__":
    main()

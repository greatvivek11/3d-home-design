"""Create a 12-second animated cutaway preview without changing the source study."""

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
FPS = 24
SHOT_FRAMES = 102
DISSOLVE_FRAMES = 9
WIDTH, HEIGHT = 1920, 1080
TOTAL_FRAMES = 3 * SHOT_FRAMES - 2 * DISSOLVE_FRAMES
SAMPLE_FRAMES = (1, 52, SHOT_FRAMES)


@dataclass(frozen=True)
class Shot:
    stem: str
    source: str
    title: str
    subtitle: str
    target: tuple[float, float, float]
    radius: float
    height: float
    angles: tuple[float, float]
    scales: tuple[float, float]


SHOTS = (
    Shot("01-overview", "all-floors", "DREAM HOME / ALL FOUR LEVELS",
         "Basement, ground floor, first floor and roof terrace",
         (131, 50, 0), 90, 245, (-92, -88), (294, 284)),
    Shot("02-living", "living-detail", "LIVING + GARDEN KITCHEN",
         "Ground floor / Connected family spaces",
         (38, 57.5, 1), 30, 42, (-75, -64), (52, 49)),
    Shot("03-suite", "bedroom-detail", "A CHILD'S PRIVATE SUITE",
         "First floor / Bedroom, dressing and bathroom",
         (15.5, 27, 1), 27, 36, (-74, -63), (41, 39)),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def camera_pose(shot, frame):
    if not 1 <= frame <= SHOT_FRAMES:
        raise ValueError(f"Frame must be between 1 and {SHOT_FRAMES}")
    t = (frame - 1) / (SHOT_FRAMES - 1)
    eased = t ** 3 * (10 - 15 * t + 6 * t * t)
    angle = math.radians(shot.angles[0] + (shot.angles[1] - shot.angles[0]) * eased)
    position = (shot.target[0] + shot.radius * math.cos(angle),
                shot.target[1] + shot.radius * math.sin(angle),
                shot.target[2] + shot.height)
    scale = shot.scales[0] + (shot.scales[1] - shot.scales[0]) * eased
    return position, scale


def assert_png(path):
    with path.open("rb") as file:
        header = file.read(24)
        file.seek(-12, 2)
        ending = file.read()
    if (header[:8] != b"\x89PNG\r\n\x1a\n" or
            struct.unpack(">II", header[16:24]) != (WIDTH, HEIGHT) or
            ending != b"\0\0\0\0IEND\xaeB`\x82"):
        raise ValueError(f"Incomplete or wrong-sized render: {path}")


def write_result(path, result):
    pending = path.with_suffix(".pending.json")
    pending.write_text(json.dumps(result, indent=2) + "\n")
    pending.replace(path)


def emission_material(bpy, name, color, opacity=1):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1)
    if opacity == 1:
        material.node_tree.links.new(emission.outputs[0], output.inputs[0])
    else:
        transparent = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = opacity
        material.node_tree.links.new(transparent.outputs[0], mix.inputs[1])
        material.node_tree.links.new(emission.outputs[0], mix.inputs[2])
        material.node_tree.links.new(mix.outputs[0], output.inputs[0])
    return material


def create_title(bpy, shot, output):
    scene = bpy.data.scenes.new("TOUR TITLE " + shot.stem)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    data = bpy.data.cameras.new(scene.name)
    data.type, data.ortho_scale, data.sensor_fit = "ORTHO", WIDTH, "HORIZONTAL"
    data.clip_end = 2000
    camera = bpy.data.objects.new(scene.name, data)
    camera.location = (WIDTH / 2, HEIGHT / 2, 1000)
    scene.collection.objects.link(camera)
    scene.camera = camera
    white = emission_material(bpy, scene.name + ".ink", (.94, .95, .9))
    muted = emission_material(bpy, scene.name + ".muted", (.55, .65, .56))
    panel = emission_material(bpy, scene.name + ".panel", (.018, .038, .027), .9)
    mesh = bpy.data.meshes.new(scene.name + ".panel")
    mesh.from_pydata([(44, 36, 0), (1100, 36, 0), (1100, 184, 0), (44, 184, 0)],
                    [], [(0, 1, 2, 3)])
    background = bpy.data.objects.new(mesh.name, mesh)
    background.data.materials.append(panel)
    scene.collection.objects.link(background)
    for label, body, size, y, material in [
        ("title", shot.title, 37, 121, white),
        ("subtitle", shot.subtitle, 25, 78, muted),
        ("note", "CONCEPT PREVIEW / LAYOUT UNCHANGED", 15, 52, muted),
    ]:
        curve = bpy.data.curves.new(scene.name + "." + label, "FONT")
        curve.body, curve.size = body, size
        text = bpy.data.objects.new(curve.name, curve)
        text.location = (74, y, 1)
        curve.materials.append(material)
        scene.collection.objects.link(text)
    scene.render.filepath = str(output / f"{shot.stem}-title.png")
    bpy.ops.render.render(write_still=True, scene=scene.name)
    assert_png(Path(scene.render.filepath))


def prepare(bpy, source, generation, output, samples):
    from mathutils import Vector

    bpy.ops.wm.open_mainfile(filepath=str(source))
    for obj in bpy.data.objects:
        if obj.type == "FONT":
            obj.hide_render = not obj.name.endswith(".heading")
            if not obj.hide_render:
                obj.data = obj.data.copy()
                obj.data.size = .3048 * 2.8
    for collection in bpy.data.collections:
        if " DIMENSIONS " in collection.name:
            collection.hide_render = True
    names = {}
    for shot in SHOTS:
        original = bpy.data.scenes[generation["render_scenes"][shot.source]]
        scene = original.copy()
        scene.name = "TOUR " + shot.stem
        # Copied scenes with no saved user are discarded when the file is reopened.
        scene.use_fake_user = True
        camera = original.camera.copy()
        camera.data = original.camera.data.copy()
        camera.name = scene.name + ".camera"
        camera.rotation_mode = "QUATERNION"
        camera.data.sensor_fit = "HORIZONTAL"
        scene.collection.objects.link(camera)
        scene.camera = camera
        scene.frame_start, scene.frame_end = 1, SHOT_FRAMES
        scene.render.fps, scene.render.fps_base = FPS, 1
        scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGB"
        scene.render.image_settings.color_depth = "8"
        scene.render.use_persistent_data = True
        scene.cycles.samples = samples
        scene.cycles.adaptive_threshold = .025
        scene.cycles.use_animated_seed = False
        scene.cycles.seed = 31
        bpy.context.window.scene = scene
        for frame in range(1, SHOT_FRAMES + 1):
            position, scale = camera_pose(shot, frame)
            camera.location = Vector(position) * .3048
            camera.rotation_quaternion = (Vector(shot.target) * .3048 - camera.location).to_track_quat("-Z", "Y")
            camera.data.ortho_scale = scale * .3048
            camera.keyframe_insert("location", frame=frame)
            camera.keyframe_insert("rotation_quaternion", frame=frame)
            camera.data.keyframe_insert("ortho_scale", frame=frame)
        scene.frame_set(1)
        names[shot.stem] = scene.name
        create_title(bpy, shot, output)
    bpy.context.window.scene = bpy.data.scenes[names[SHOTS[0].stem]]
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "dream-home-tour.blend"))
    return names


def verify_animation(bpy, names):
    for shot in SHOTS:
        scene = bpy.data.scenes[names[shot.stem]]
        bpy.context.window.scene = scene
        for frame in SAMPLE_FRAMES:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            position, scale = camera_pose(shot, frame)
            if (math.dist(scene.camera.location, [value * .3048 for value in position]) > .0001 or
                    abs(scene.camera.data.ortho_scale - scale * .3048) > .0001):
                raise ValueError(f"Saved camera animation does not evaluate correctly: {shot.stem}, frame {frame}")
    print("TOUR_ANIMATION_CHECKS", "PASS: three saved scenes and nine evaluated camera poses", flush=True)


def enable_device(bpy, device):
    if device == "CPU":
        return
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = "METAL"
    preferences.get_devices()
    if not any(item.type == "METAL" for item in preferences.devices):
        raise RuntimeError("Metal requested but no Metal GPU is available; use --device CPU")
    for item in preferences.devices:
        item.use = item.type == "METAL"
    print("TOUR_DEVICES", [item.name for item in preferences.devices if item.use], flush=True)


def composite_checks(ffmpeg, output):
    checks = output / "checks"
    checks.mkdir(exist_ok=True)
    images = []
    for shot in SHOTS:
        for frame in SAMPLE_FRAMES:
            target = checks / f"{shot.stem}-{frame:04}.png"
            subprocess.run([ffmpeg, "-v", "error", "-y",
                            "-i", str(output / "frames" / shot.stem / f"frame_{frame:04}.png"),
                            "-i", str(output / f"{shot.stem}-title.png"),
                            "-filter_complex", "overlay=0:0", "-frames:v", "1", str(target)], check=True)
            images.append(target)
    command = [ffmpeg, "-v", "error", "-y"]
    for image in images:
        command += ["-i", str(image)]
    filters = [f"[{i}:v]scale=480:270[s{i}]" for i in range(9)]
    filters += [f"[s{i}][s{i+1}][s{i+2}]hstack=inputs=3[row{i//3}]" for i in [0, 3, 6]]
    filters += ["[row0][row1][row2]vstack=inputs=3[out]"]
    subprocess.run(command + ["-filter_complex", ";".join(filters), "-map", "[out]",
                             "-frames:v", "1", str(output / "preview-contact-sheet.png")], check=True)


def encode(ffmpeg, ffprobe, output):
    command = [ffmpeg, "-v", "error", "-y"]
    for shot in SHOTS:
        command += ["-framerate", str(FPS), "-start_number", "1",
                    "-i", str(output / "frames" / shot.stem / "frame_%04d.png")]
    for shot in SHOTS:
        command += ["-loop", "1", "-framerate", str(FPS), "-i", str(output / f"{shot.stem}-title.png")]
    filters = [f"[{i}:v][{i+3}:v]overlay=0:0:shortest=1,format=yuv444p,settb=1/{FPS}[s{i}]" for i in range(3)]
    duration = DISSOLVE_FRAMES / FPS
    filters += [f"[s0][s1]xfade=transition=fade:duration={duration}:offset={(SHOT_FRAMES-DISSOLVE_FRAMES)/FPS}[ab]",
                f"[ab][s2]xfade=transition=fade:duration={duration}:offset={2*(SHOT_FRAMES-DISSOLVE_FRAMES)/FPS},"
                "fade=t=in:st=0:d=0.25,fade=t=out:st=11.75:d=0.25,format=yuv420p[out]"]
    pending = output / "dream-home-preview.pending.mp4"
    subprocess.run(command + ["-filter_complex", ";".join(filters), "-map", "[out]",
                             "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                             "-profile:v", "high", "-level:v", "4.1", "-pix_fmt", "yuv420p",
                             "-r", str(FPS), "-movflags", "+faststart",
                             "-metadata", "title=Dream home - cinematic cutaway preview",
                             str(pending)], check=True)
    probe = json.loads(subprocess.check_output(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(pending)], text=True))
    streams = probe["streams"]
    if len(streams) != 1:
        raise ValueError("Preview must contain one silent video stream")
    video = streams[0]
    expected = {"codec_name": "h264", "pix_fmt": "yuv420p", "width": WIDTH, "height": HEIGHT,
                "avg_frame_rate": f"{FPS}/1", "nb_frames": str(TOTAL_FRAMES)}
    for key, value in expected.items():
        if video[key] != value:
            raise ValueError(f"Unexpected video {key}: {video[key]} (expected {value})")
    if abs(float(probe["format"]["duration"]) - TOTAL_FRAMES / FPS) > .001:
        raise ValueError("Encoded duration does not match the 12-second preview")
    subprocess.run([ffmpeg, "-v", "error", "-xerror", "-i", str(pending), "-f", "null", "-"], check=True)
    pending.replace(output / "dream-home-preview.mp4")
    return {"width": WIDTH, "height": HEIGHT, "fps": FPS, "frames": TOTAL_FRAMES,
            "seconds": TOTAL_FRAMES / FPS, "codec": video["codec_name"], "pixel_format": video["pix_fmt"],
            "bytes": (output / "dream-home-preview.mp4").stat().st_size, "full_decode": "PASS"}


def main():
    import bpy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/study-003-tour-preview")
    parser.add_argument("--device", choices=["CPU", "METAL"], default="CPU")
    parser.add_argument("--samples", type=int, default=48)
    parser.add_argument("--stills", action="store_true", help="Render first/middle/last frames for visual review only")
    parser.add_argument("--resume", action="store_true", help="Reuse a matching prepared tour and complete PNG frames")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.samples <= 0:
        raise ValueError("Samples must be positive")
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required for encoding and verification")
    source, output = args.blend.resolve(), args.output.resolve()
    generation = json.loads((source.parent / "generation-result.json").read_text())
    locked = {path: digest(ROOT / path) for path in ["house-spec/house.json", "house-spec/layout-study.json"]}
    if (locked["house-spec/house.json"] != generation["brief_sha256"] or
            locked["house-spec/layout-study.json"] != generation["layout_sha256"]):
        raise ValueError("The source study does not match the current brief/layout")
    config = {"source": str(source), "source_sha256": digest(source), "locked_sources": locked,
              "script_sha256": digest(Path(__file__)), "samples": args.samples,
              "fps": FPS, "shot_frames": SHOT_FRAMES, "dissolve_frames": DISSOLVE_FRAMES,
              "shots": [asdict(shot) for shot in SHOTS]}
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    result_path = output / "tour-result.json"
    if args.resume:
        result = json.loads(result_path.read_text())
        if result["signature"] != signature or digest(output / "dream-home-tour.blend") != result["animation_sha256"]:
            raise ValueError("Cannot resume: inputs, script, settings or prepared animation have changed")
        bpy.ops.wm.open_mainfile(filepath=str(output / "dream-home-tour.blend"))
    else:
        output.mkdir(parents=True, exist_ok=False)
        names = prepare(bpy, source, generation, output, args.samples)
        result = {"signature": signature, "config": config, "scenes": names,
                  "animation_sha256": digest(output / "dream-home-tour.blend"), "status": "prepared"}
        write_result(result_path, result)
        bpy.ops.wm.open_mainfile(filepath=str(output / "dream-home-tour.blend"))
    verify_animation(bpy, result["scenes"])
    enable_device(bpy, args.device)
    started = time.monotonic()
    for shot in SHOTS:
        scene = bpy.data.scenes[result["scenes"][shot.stem]]
        bpy.context.window.scene = scene
        scene.cycles.device = "GPU" if args.device == "METAL" else "CPU"
        folder = output / "frames" / shot.stem
        folder.mkdir(parents=True, exist_ok=True)
        frames = SAMPLE_FRAMES if args.stills else range(1, SHOT_FRAMES + 1)
        for frame in frames:
            path = folder / f"frame_{frame:04}.png"
            if path.exists():
                assert_png(path)
        if args.stills:
            for frame in frames:
                path = folder / f"frame_{frame:04}.png"
                if not path.exists():
                    scene.frame_set(frame)
                    scene.render.filepath = str(path)
                    bpy.ops.render.render(write_still=True, scene=scene.name)
        else:
            scene.render.filepath = str(folder / "frame_")
            scene.render.use_overwrite = False
            bpy.ops.render.render(animation=True, scene=scene.name)
        for frame in frames:
            assert_png(folder / f"frame_{frame:04}.png")
    composite_checks(ffmpeg, output)
    if not args.stills:
        result["video"] = encode(ffmpeg, ffprobe, output)
    if digest(source) != config["source_sha256"] or any(digest(ROOT / path) != value for path, value in locked.items()):
        raise ValueError("Source model, layout or brief changed during the render")
    result.update(status="stills_ready" if args.stills else "complete",
                  saved_animation_checks="PASS", last_render_device=args.device,
                  last_run_seconds=round(time.monotonic() - started, 2))
    write_result(result_path, result)
    print("TOUR_SUCCESS", json.dumps({"output": str(output), "status": result["status"],
                                    "video": result.get("video"), "seconds": result["last_run_seconds"]}), flush=True)


if __name__ == "__main__":
    main()

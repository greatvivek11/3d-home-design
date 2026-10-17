"""Validate the brief and layout study, and emit review plans without Blender."""

import argparse
from collections import Counter, defaultdict, deque
from html import escape
import json
import math
from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parents[1]
FT = 0.3048
COLORS = {
    "bedroom": "#dec6aa", "bathroom": "#bad4d6", "storage": "#d4cfbc",
    "living": "#eadfcc", "kitchen": "#e4c69e", "circulation": "#f0eee6",
    "stairs": "#c8c5bb", "service": "#d0d4d7", "garage": "#c5cbd0",
    "recreation": "#cad7bb", "office": "#b7ccbf", "prayer": "#e9ce8c",
    "garden": "#a4bd89", "veranda": "#d5b993", "pool": "#79bfcd",
    "path": "#d0c9bc", "barrier": "#ffffff",
}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def feet(value):
    if not number(value):
        raise ValueError(f"Not a finite length: {value!r}")
    return value * FT


def square_feet(value):
    if not number(value):
        raise ValueError(f"Not a finite area: {value!r}")
    return value * FT * FT


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def valid_rect(rect):
    return (isinstance(rect, list) and len(rect) == 4
            and all(number(v) for v in rect) and rect[2] > 0 and rect[3] > 0)


def contains(outer, inner, tolerance=1e-6):
    x, y, w, d = outer
    a, b, c, e = inner
    return a >= x - tolerance and b >= y - tolerance and a + c <= x + w + tolerance and b + e <= y + d + tolerance


def overlap(a, b):
    return max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(
        0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))


def adjacent(a, b, gap=0.51):
    x_overlap = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    y_overlap = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    x_gap = max(a[0], b[0]) - min(a[0] + a[2], b[0] + b[2])
    y_gap = max(a[1], b[1]) - min(a[1] + a[3], b[1] + b[3])
    return (x_overlap >= 3 and y_gap <= gap) or (y_overlap >= 3 and x_gap <= gap)


def subtract_rectangles(base, holes):
    """Partition a rectangle into cells, excluding rectangular openings."""
    x, y, w, d = base
    xs = sorted({x, x + w, *(v for r in holes for v in [r[0], r[0] + r[2]] if x < v < x + w)})
    ys = sorted({y, y + d, *(v for r in holes for v in [r[1], r[1] + r[3]] if y < v < y + d)})
    result = []
    for a, b in zip(xs, xs[1:]):
        for c, e in zip(ys, ys[1:]):
            cell = [a, c, b - a, e - c]
            if not any(overlap(cell, hole) > 1e-8 for hole in holes):
                result.append(cell)
    return result


def room_footprints(floor, room):
    holes = [r["rect"] for r in floor["rooms"] if r.get("parent") == room["id"] and r.get("exclude_from_parent")]
    return subtract_rectangles(room["rect"], holes)


def room_area(floor, room):
    return sum(r[2] * r[3] for r in room_footprints(floor, room))


def dining_chairs(rect):
    x, y, w, d = rect
    seats = [[x - 1.8, y + (d - 1.5) * t, 1.5, 1.5] for t in [0, 0.5, 1]]
    seats += [[x + w + 0.3, y + (d - 1.5) * t, 1.5, 1.5] for t in [0, 0.5, 1]]
    return seats + [[x + w / 2 - 0.75, y - 1.8, 1.5, 1.5], [x + w / 2 - 0.75, y + d + 0.3, 1.5, 1.5]]


def wall_partition(floor, wall):
    return next((p for p in floor.get("partitions", [])
                 if p["axis"] == wall["axis"] and math.isclose(p["at"], wall["at"], abs_tol=1e-6)), None)


def partition_between(floor, a, b):
    for p in floor.get("partitions", []):
        along, across = (0, 1) if p["axis"] == "x" else (1, 0)
        ar, br = a["rect"], b["rect"]
        separated = ((ar[across] + ar[across + 2] <= p["at"] <= br[across])
                     or (br[across] + br[across + 2] <= p["at"] <= ar[across]))
        if separated and min(ar[along] + ar[along + 2], br[along] + br[along + 2], p["end"]) > max(ar[along], br[along], p["start"]):
            return True
    return False


def access_graph(floor):
    rooms = floor["rooms"]
    graph = {room["id"]: set() for room in rooms}
    graph["outside"] = set()
    for opening in floor["openings"]:
        refs = opening.get("connects", [])
        if len(refs) == 2 and all(ref in graph for ref in refs) and opening.get("kind") != "window":
            graph[refs[0]].add(refs[1])
            graph[refs[1]].add(refs[0])
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            nested = (a.get("parent") == b["id"] and a.get("open")) or (b.get("parent") == a["id"] and b.get("open"))
            joined = a.get("open") and b.get("open") and adjacent(a["rect"], b["rect"]) and not partition_between(floor, a, b)
            if nested or joined:
                graph[a["id"]].add(b["id"])
                graph[b["id"]].add(a["id"])
    return graph


def reachable(graph, start, blocked=()):
    reached, excluded = set(), set(blocked)
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node not in reached and node not in excluded:
            reached.add(node)
            queue.extend(graph.get(node, set()) - reached - excluded)
    return reached


def opening_touches(room, opening, thickness):
    along, across = (0, 1) if opening["axis"] == "x" else (1, 0)
    r, half = room["rect"], thickness / 2
    return (any(math.isclose(opening["at"], edge, abs_tol=1e-6) for edge in [r[across] - half, r[across] + r[across + 2] + half])
            and opening["start"] >= r[along] - 1e-6
            and opening["start"] + opening["width"] <= r[along] + r[along + 2] + 1e-6)


def walls(floor, thickness):
    """Merge collinear room boundaries so shared walls are not duplicated."""
    lines = defaultdict(list)
    half = thickness / 2
    for room in floor["rooms"]:
        if room.get("open"):
            continue
        x, y, w, d = room["rect"]
        for axis, at, start, end in [
            ("x", y - half, x - half, x + w + half),
            ("x", y + d + half, x - half, x + w + half),
            ("y", x - half, y - half, y + d + half),
            ("y", x + w + half, y - half, y + d + half),
        ]:
            lines[(axis, round(at, 6))].append((start, end))
    for p in floor.get("partitions", []):
        lines[(p["axis"], round(p["at"], 6))].append((p["start"], p["end"]))
    x, y, w, d = floor["envelope"]
    for axis, at, start, end in [
        ("x", y + half, x + half, x + w - half),
        ("x", y + d - half, x + half, x + w - half),
        ("y", x + half, y + half, y + d - half),
        ("y", x + w - half, y + half, y + d - half),
    ]:
        lines[(axis, round(at, 6))].append((start, end))
    result = []
    for (axis, at), intervals in sorted(lines.items()):
        merged = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1] + 1e-6:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        result.extend({"axis": axis, "at": at, "start": a, "end": b} for a, b in merged)
    return result


def wall_parts(wall, openings, height):
    cuts = sorted(
        (max(wall["start"], o["start"]), min(wall["end"], o["start"] + o["width"]), o.get("sill", 0))
        for o in openings if o["axis"] == wall["axis"] and abs(o["at"] - wall["at"]) < 1e-6
        and o["start"] < wall["end"] and o["start"] + o["width"] > wall["start"]
    )
    cursor = wall["start"]
    parts = []
    for start, end, sill in cuts:
        if start > cursor:
            parts.append((cursor, start, height))
        if sill > 0:
            parts.append((start, end, min(sill, height)))
        cursor = max(cursor, end)
    if cursor < wall["end"]:
        parts.append((cursor, wall["end"], height))
    return parts


def validate_brief(spec):
    errors = []
    if spec.get("project", {}).get("version") != 2:
        errors.append("Expected approved brief format version 2")
    if spec.get("project", {}).get("input_units") != "ft" or spec.get("project", {}).get("internal_units") != "m":
        errors.append("Expected input feet and internal metres")
    floors = spec.get("floors", [])
    ids = [f.get("id") for f in floors]
    if len(ids) != len(set(ids)) or set(ids) != {"basement", "ground", "first"}:
        errors.append("Brief must contain unique basement, ground and first floors")
    rooms = [r for f in floors for r in f.get("rooms", [])]
    room_ids = [r.get("id") for r in rooms]
    if len(room_ids) != len(set(room_ids)):
        errors.append("Duplicate brief room IDs")
    if sum(r.get("type") == "bedroom" for r in rooms) != 5:
        errors.append("Brief must retain five bedrooms")
    for f in floors:
        expected = {"ground": 2, "first": 3, "basement": 0}[f["id"]] if f.get("id") in ids and f.get("id") in {"ground", "first", "basement"} else None
        if expected is not None and sum(r.get("type") == "bedroom" for r in f.get("rooms", [])) != expected:
            errors.append(f"Wrong bedroom distribution: {f['id']}")
    for r in rooms:
        for key in ["attached_bathroom_id", "wardrobe_room_id"]:
            if key in r and r[key] not in room_ids:
                errors.append(f"Unresolved brief reference: {r.get('id')}.{key}")
    for key in ["width", "depth"]:
        value = spec.get("site", {}).get(key)
        if value is not None and (not number(value) or value <= 0):
            errors.append(f"Invalid specified site {key}")
    for key in ["floor_to_floor_height", "exterior_wall_thickness", "interior_wall_thickness"]:
        value = spec.get("building", {}).get(key)
        if value is not None and (not number(value) or value <= 0):
            errors.append(f"Invalid specified building {key}")
    return errors


def validate(spec, layout):
    errors = validate_brief(spec)
    if errors:
        return {"status": "FAIL", "geometry_status": "FAIL", "errors": errors, "checks": [], "review": []}
    checks = []
    if layout.get("status") != "unapproved_concept" or layout.get("units") != "ft":
        errors.append("Study must remain unapproved with explicit feet")
    site = layout.get("site", {})
    if not all(number(site.get(k)) and site[k] > 0 for k in ["width", "depth"]):
        return {"status": "FAIL", "errors": errors + ["Invalid site dimensions"], "checks": [], "review": []}
    bounds = [0, 0, site["width"], site["depth"]]
    thickness = layout.get("wall_thickness")
    if not number(thickness) or thickness <= 0:
        return {"status": "FAIL", "errors": errors + ["Invalid wall thickness"], "checks": [], "review": []}
    if not number(layout.get("section_height")) or layout["section_height"] <= 0:
        errors.append("Invalid section height")
    floor_ids = [f.get("id") for f in layout.get("floors", [])]
    if set(floor_ids) != {"basement", "ground", "first", "roof"} or len(floor_ids) != 4:
        errors.append("Study must contain unique basement, ground, first and roof levels")
        return {"status": "FAIL", "geometry_status": "FAIL", "errors": errors, "checks": [], "review": []}
    required = {f["id"]: {r["id"] for r in f["rooms"] if r.get("required")} for f in spec["floors"]}
    assignments = defaultdict(list)
    for f in layout.get("floors", []):
        fid = f["id"]
        envelope = f.get("envelope")
        if not valid_rect(envelope) or not contains(bounds, envelope):
            errors.append(f"{fid}: invalid/out-of-site envelope")
            continue
        if not number(f.get("elevation")) or not number(f.get("rise")) or f["rise"] < 0:
            errors.append(f"{fid}: invalid elevation/rise")
        rs = f.get("rooms", [])
        room_ids = [r["id"] for r in rs]
        if len(set(room_ids)) != len(room_ids):
            errors.append(f"{fid}: duplicate room IDs")
        for r in rs:
            assignments[r["id"]].append(fid)
            if not valid_rect(r.get("rect")) or not contains(envelope, r["rect"]):
                errors.append(f"{fid}/{r['id']}: invalid/out-of-envelope rectangle")
        if any(not valid_rect(r.get("rect")) for r in rs):
            continue
        by_id = {r["id"]: r for r in rs}
        for i, a in enumerate(rs):
            if a.get("parent") and (a["parent"] not in by_id or not contains(by_id[a["parent"]]["rect"], a["rect"])):
                errors.append(f"{fid}/{a['id']}: invalid nested zone")
            for b in rs[i + 1:]:
                intended = a.get("parent") == b["id"] or b.get("parent") == a["id"]
                shared_route = a["kind"] == b["kind"] == "circulation"
                if overlap(a["rect"], b["rect"]) > 1e-6 and not (intended or shared_route):
                    errors.append(f"{fid}: unintended overlap {a['id']} / {b['id']}")
        missing = required.get(fid, set()) - set(room_ids)
        if missing:
            errors.append(f"{fid}: missing required rooms {sorted(missing)}")
        fixture_ids = [item["id"] for item in f.get("furniture", [])]
        if len(set(fixture_ids)) != len(fixture_ids):
            errors.append(f"{fid}: duplicate furniture IDs")
        for item in f.get("furniture", []):
            if item.get("room") not in by_id or not valid_rect(item.get("rect")):
                errors.append(f"{fid}/{item['id']}: invalid furniture/reference")
            elif not contains(by_id[item["room"]]["rect"], item["rect"]):
                errors.append(f"{fid}/{item['id']}: furniture outside assigned room")
            elif any(overlap(item["rect"], r["rect"]) > 1e-6 for r in rs
                     if r.get("parent") == item["room"] and r.get("exclude_from_parent")):
                errors.append(f"{fid}/{item['id']}: furniture inside excluded child room")
            if item.get("kind") == "dining_table" and item.get("room") in by_id and valid_rect(item.get("rect")):
                if any(not contains(by_id[item["room"]]["rect"], chair) for chair in dining_chairs(item["rect"])):
                    errors.append(f"{fid}: eight dining chairs must fit the dining zone")
        for i, a in enumerate(f.get("furniture", [])):
            for b in f["furniture"][i + 1:]:
                if valid_rect(a.get("rect")) and valid_rect(b.get("rect")) and overlap(a["rect"], b["rect"]) > 1e-6:
                    errors.append(f"{fid}: furniture collision {a['id']} / {b['id']}")
        if any(p.get("axis") not in {"x", "y"} or not all(number(p.get(k)) for k in ["at", "start", "end", "intended_height"])
               or p["end"] <= p["start"] or p["intended_height"] <= 0 for p in f.get("partitions", [])):
            errors.append(f"{fid}: invalid partition")
            continue
        ws = walls(f, thickness)
        graph = access_graph(f)
        for o in f.get("openings", []):
            if o.get("axis") not in {"x", "y"} or not all(number(o.get(k)) for k in ["at", "start", "width"]) or o["width"] <= 0:
                errors.append(f"{fid}: invalid opening")
                continue
            if not any(w["axis"] == o["axis"] and abs(w["at"] - o["at"]) < 1e-6 and w["start"] <= o["start"] and w["end"] >= o["start"] + o["width"] for w in ws):
                errors.append(f"{fid}: opening lacks full host wall {o}")
            refs = o.get("connects", [])
            if len(refs) != 2 or any(ref not in graph for ref in refs):
                errors.append(f"{fid}: invalid opening references {refs}")
            elif any(not opening_touches(by_id[ref], o, thickness) for ref in refs if ref != "outside"):
                errors.append(f"{fid}: opening does not touch its connected rooms: {refs}")
        root = "receiving" if fid == "ground" else "stairs"
        reached = reachable(graph, root)
        unreachable = required.get(fid, set()) - reached
        if unreachable:
            errors.append(f"{fid}: required spaces disconnected in adjacency graph: {sorted(unreachable)}")
        checks.append(f"{fid}: room bounds, unintended overlaps, furniture bounds/collisions, opening hosts and required-space adjacency checked")
    for space in spec.get("flexible_spaces", []):
        locations = assignments[space["id"]]
        if (len(locations) != 1 or locations[0] not in space["allowed_floors"]
                or space.get("assigned_floor") not in {None, locations[0]}):
            errors.append(f"Flexible space {space['id']} needs exactly one allowed floor assignment")
    floor_map = {f["id"]: f for f in layout.get("floors", [])}
    if all(fid in floor_map for fid in ["basement", "ground", "first", "roof"]):
        for low, high in zip(["basement", "ground", "first"], ["ground", "first", "roof"]):
            if not math.isclose(floor_map[low]["elevation"] + floor_map[low]["rise"], floor_map[high]["elevation"], abs_tol=1e-6):
                errors.append(f"Unaligned floor elevations {low}/{high}")
        stairs = [next((r["rect"] for r in f["rooms"] if r["id"] == "stairs"), None) for f in floor_map.values()]
        if any(r != stairs[0] for r in stairs) or stairs[0] is None:
            errors.append("Stair footprints must align across levels")
        kids = [r["rect"][2:] for r in floor_map["first"]["rooms"] if r["id"].startswith("child_bedroom")]
        if len(kids) != 3 or any(size != kids[0] for size in kids):
            errors.append("Three equal children's bedrooms required")
        cars = [item for item in floor_map["basement"]["furniture"] if item["kind"] == "car"]
        if len(cars) != spec["parking"]["car_count"]:
            errors.append("Missing three SUV blockouts")
        basement = floor_map["basement"]
        if spec.get("services", {}).get("garage_compartmentation_required") and not errors:
            zones = basement.get("air_zones", {})
            clean, buffer, garage = (set(zones.get(key, [])) for key in ["clean", "buffer", "garage"])
            ids = {r["id"] for r in basement["rooms"]}
            if not clean or not buffer or not garage or clean & garage or clean & buffer or garage & buffer or clean | buffer | garage != ids:
                errors.append("Basement air zones must classify every room exactly once")
            graph = access_graph(basement)
            if garage & reachable(graph, "stairs", buffer):
                errors.append("Basement clean route bypasses the garage airlock")
            if clean - reachable(graph, "stairs", garage | buffer):
                errors.append("Basement occupied rooms need a clean route without crossing the garage/airlock")
            ex, _, ew, _ = basement["envelope"]
            if not any(p["axis"] == "x" and p["start"] <= ex + thickness / 2 and p["end"] >= ex + ew - thickness / 2
                       and p["intended_height"] >= basement["rise"] for p in basement.get("partitions", [])):
                errors.append("Basement needs an intended full-height garage separation")
            for airlock in buffer:
                doors = [o for o in basement["openings"] if airlock in o["connects"] and o.get("kind") != "window"]
                others = {ref for o in doors for ref in o["connects"] if ref != airlock}
                if len(doors) != 2 or not all(o.get("self_closing") for o in doors) or not others & clean or not others & garage:
                    errors.append("Garage airlock needs two self-closing doors between clean and garage zones")
            checks.append("Concept garage barrier, two-door airlock and protected clean-side adjacency checked; NOT an airflow/fire certification")
        fixtures = [item for f in floor_map.values() for item in f["furniture"]]
        fixture_requirements = {
            "master_bathroom": {"wc_cubicle": 2, "double_basin": 1, "bathtub": 1, "shower": 1},
            "guest_shared_bathroom": {"toilet": 1, "basin": 1, "shower": 1},
            "family_toilet": {"toilet": 1, "basin": 1},
            "basement_toilet": {"toilet": 1, "basin": 1},
            "office_toilet": {"toilet": 1, "basin": 1},
            "office": {"desk": 1, "table": 1, "piano": 1, "shelf": 1},
            "dining": {"dining_table": 1},
        }
        for i in range(1, 4):
            fixture_requirements[f"child_bathroom_{i}"] = {"toilet": 1, "basin": 1, "shower": 1}
            fixture_requirements[f"child_bedroom_{i}"] = {"bed": 1, "desk": 1, "chair": 1}
            fixture_requirements[f"child_wardrobe_{i}"] = {"shelf": 1}
        for room, kinds in fixture_requirements.items():
            actual = Counter(item["kind"] for item in fixtures if item["room"] == room)
            for kind, count in kinds.items():
                if actual[kind] < count:
                    errors.append(f"{room}: missing required {kind} fixture(s)")
        expected_toilets = sum(r.get("toilet_count", 0) + r.get("separate_toilet_cubicles", 0)
                               for f in spec["floors"] for r in f["rooms"])
        if sum(item["kind"] in {"toilet", "wc_cubicle"} for item in fixtures) != expected_toilets:
            errors.append(f"{expected_toilets} toilets including two separate master cubicles required")
        first = floor_map["first"]
        first_rooms = {r["id"]: r for r in first["rooms"]}
        suite_ids = {f"child_{kind}_{i}" for i in range(1, 4) for kind in ["bedroom", "bathroom", "wardrobe"]}
        if suite_ids <= first_rooms.keys() and all(valid_rect(r.get("rect")) for r in first["rooms"]):
            graph = access_graph(first)
            for i in range(1, 4):
                bed, bath, wardrobe = (f"child_{kind}_{i}" for kind in ["bedroom", "bathroom", "wardrobe"])
                if bed not in graph[wardrobe] or bath not in graph[wardrobe]:
                    errors.append(f"{wardrobe}: bedroom, dressing and bathroom must be directly interconnected")
                if graph[bath] - {bed, wardrobe} or graph[wardrobe] - {bed, bath}:
                    errors.append(f"{bath}: bathroom/dressing must remain private to its child suite")
                shelves = [item["rect"] for item in first["furniture"]
                           if item["room"] == wardrobe and valid_rect(item.get("rect"))]
                clear = subtract_rectangles(first_rooms[wardrobe]["rect"], shelves)
                if not any(min(r[2:]) >= 3 and max(r[2:]) >= 5 for r in clear):
                    errors.append(f"{wardrobe}: needs a clear dressing aisle at least 3 x 5 ft")
                if not any(item["room"] == bath and item["kind"] == "shower"
                           and item.get("enclosed") and item.get("entry_side") in {"north", "south", "east", "west"}
                           for item in first["furniture"]):
                    errors.append(f"{bath}: enclosed shower intent required beside the dry dressing area")
            if graph.get("office_toilet") != {"office"}:
                errors.append("Office WC needs private office-only access, not lounge/balcony access")
            common = reachable(graph, "stairs", suite_ids | {"office", "office_toilet", "outside"})
            if not {"upstairs_lounge", "rear_gallery"} <= common:
                errors.append("Shared rear balcony route must not cross a private bedroom, office or suite")
            checks.append("Private connected bath/dressing suites, clear dressing aisles, office-only WC and common rear-balcony route checked; wet-area engineering unverified")
    for item in layout.get("outdoor", []) + layout.get("balconies", []):
        if not valid_rect(item.get("rect")) or not contains(bounds, item["rect"]):
            errors.append(f"Outdoor/balcony out of bounds: {item.get('id')}")
    ramp = layout["ramp"]
    if not valid_rect(ramp["rect"]) or not contains(bounds, ramp["rect"]):
        errors.append("Invalid/out-of-site ramp")
    profile = ramp["profile"]
    if len(profile) < 2 or any(not all(number(n) for n in p) or len(p) != 2 for p in profile):
        errors.append("Invalid ramp profile")
    elif any(b[0] <= a[0] or b[1] > a[1] for a, b in zip(profile, profile[1:])):
        errors.append("Ramp must progress monotonically to basement")
    elif not math.isclose(profile[-1][1], floor_map["basement"]["elevation"], abs_tol=1e-6):
        errors.append("Ramp landing must meet basement elevation")
    checks.append("Five-bedroom program, flexible assignments, equal children's rooms, floor/stair alignment and ramp elevation checked")
    area = site["width"] * site["depth"]
    return {
        "status": "FAIL" if errors else "NEEDS REVIEW",
        "geometry_status": "FAIL" if errors else "PASS",
        "layout_id": layout["id"],
        "layout_approved": False,
        "plot_area_sq_ft": area,
        "plot_expansion_above_initial_max_percent": round((area / spec["site"]["area_target_sq_ft"]["max"] - 1) * 100, 2),
        "floor_plate_areas_sq_ft": {fid: f["envelope"][2] * f["envelope"][3] for fid, f in floor_map.items()},
        "front_yard_fraction": site["front_depth"] / site["depth"],
        "back_yard_fraction": (site["depth"] - site["back_start"]) / site["depth"],
        "errors": errors,
        "checks": checks,
        "review": layout["review_items"],
    }


def plan_svg(layout, floor=None):
    scale, pad = 12, 70
    width = layout["site"]["width"] * scale + 2 * pad
    height = layout["site"]["depth"] * scale + 2 * pad + 90
    title = floor["id"].upper() if floor else "SITE"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#faf8f3"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#263b37}</style>',
             f'<text x="{pad}" y="28" font-size="20" font-weight="bold">DREAM HOME / {title} / {escape(layout["id"].replace("-", " ").upper())}</text>',
             f'<text x="{pad}" y="48" font-size="12">UNAPPROVED CONCEPT - {layout["site"]["width"]:g} x {layout["site"]["depth"]:g} ft study plot - compass direction unresolved</text>']

    def rect(r, fill, stroke="#9b9e91", dash=False):
        x, y, w, d = r
        parts.append(f'<rect x="{pad + x * scale}" y="{pad + (100 - y - d) * scale}" width="{w * scale}" height="{d * scale}" fill="{fill}" stroke="{stroke}" stroke-width="1"'
                     + (' stroke-dasharray="5 4"' if dash else '') + '/>')

    def label(r, name, size=True, area=None):
        x, y, w, d = r
        lines = textwrap.wrap(name, max(10, int(w * 1.7)))
        if size:
            extent = "ft extents" if area is not None and not math.isclose(area, w * d) else "ft"
            lines.append(f'{w:g} x {d:g} {extent} | {area if area is not None else w * d:g} sq ft')
        for i, line in enumerate(lines):
            parts.append(f'<text x="{pad + (x + w / 2) * scale}" y="{pad + (100 - y - d / 2) * scale + (i - len(lines) / 2) * 12}" text-anchor="middle" font-size="10">{escape(line)}</text>')

    rect([0, 0, layout["site"]["width"], 100], "#eef1e5", "#536a56")
    if floor is None or floor["id"] == "ground":
        for item in layout["outdoor"]:
            if item["kind"] != "barrier":
                rect(item["rect"], COLORS[item["kind"]])
                if floor is None:
                    label(item["rect"], item["name"], item["kind"] != "path")
        rect(layout["ramp"]["rect"], "#bac0c3", dash=True)
        label(layout["ramp"]["rect"], "RAMP / grade and flood review", False)
        if floor is None:
            ground = next(f for f in layout["floors"] if f["id"] == "ground")
            rect(ground["envelope"], "#eee0ca")
            label(ground["envelope"], "Proposed two-storey footprint")
            basement = layout["floors"][0]["envelope"]
            rect(basement, "none", "#976548", True)
            parts.append(f'<text x="{pad + 60}" y="{pad + 15 * scale}" font-size="12">Dashed brown: basement below gardens</text>')
    if floor:
        if floor["id"] == "first":
            for balcony in layout["balconies"]:
                rect(balcony["rect"], COLORS["veranda"])
                label(balcony["rect"], balcony["name"])
        rect(floor["envelope"], "#f2ede1")
        for room in floor["rooms"]:
            rect(room["rect"], COLORS[room["kind"]], dash=bool(room.get("open")))
        for item in floor["furniture"]:
            rect(item["rect"], "#8a9a8c" if item["kind"] != "bed" else "#faf7ee", "#68786f")
        for wall in walls(floor, layout["wall_thickness"]):
            for start, end, h in wall_parts(wall, floor["openings"], layout["section_height"]):
                if h < layout["section_height"]:
                    continue
                axis, at = wall["axis"], wall["at"]
                x1, y1 = (start, at) if axis == "x" else (at, start)
                x2, y2 = (end, at) if axis == "x" else (at, end)
                color = "#a35f37" if wall_partition(floor, wall) else "#46514b"
                parts.append(f'<line x1="{pad + x1 * scale}" y1="{pad + (100 - y1) * scale}" x2="{pad + x2 * scale}" y2="{pad + (100 - y2) * scale}" stroke="{color}" stroke-width="4"/>')
        for room in floor["rooms"]:
            if (room["kind"] != "circulation" or room.get("label")) and (not room.get("parent") or room.get("exclude_from_parent")):
                label(room["rect"], room["name"], area=room_area(floor, room))
        for p in floor.get("partitions", []):
            parts.append(f'<text x="{pad + (p["start"] + p["end"]) / 2 * scale}" y="{pad + (100 - p["at"]) * scale - 7}" text-anchor="middle" font-size="9">{escape(p["label"])}</text>')
        for o in floor["openings"]:
            if o.get("kind") == "window":
                continue
            axis, at, start, w = o["axis"], o["at"], o["start"], o["width"]
            x, y = (start, at) if axis == "x" else (at, start)
            endx, endy = (x + w, y) if axis == "x" else (x, y + w)
            color = "#8c6699" if o.get("kind") == "soft_divider" else "#b8753b"
            parts.append(f'<line x1="{pad + x * scale}" y1="{pad + (100 - y) * scale}" x2="{pad + endx * scale}" y2="{pad + (100 - endy) * scale}" stroke="{color}" stroke-width="2" stroke-dasharray="3 2"/>')
    parts.extend([
        f'<text x="{width / 2}" y="{height - 105}" text-anchor="middle" font-size="14">FRONT / ROAD CONVENTION - {layout["site"]["width"]:g} ft</text>',
        f'<text x="{pad}" y="{height - 70}" font-size="12">All dimensions proposed. L-shaped zones list outer extents and net area excluding enclosed child rooms.</text>',
        f'<text x="{pad}" y="{height - 50}" font-size="12">Colored zones: uses. Dark: cutaway walls. Orange: doors. Purple: soft bath/dressing dividers.</text>',
        f'<text x="{pad}" y="{height - 30}" font-size="12">NOT a construction plan. See review-report.json for limitations and unresolved checks.</text>',
        '</svg>',
    ])
    return "\n".join(parts)


def write_review(spec, layout, output):
    report = validate(spec, layout)
    if report["errors"]:
        raise ValueError("Layout validation failed:\n" + "\n".join(report["errors"]))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "review-report.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "layout-snapshot.json").write_text(json.dumps(layout, indent=2) + "\n")
    (output / "brief-snapshot.json").write_text(json.dumps(spec, indent=2) + "\n")
    (output / "site.svg").write_text(plan_svg(layout))
    for floor in layout["floors"]:
        (output / f"{floor['id']}.svg").write_text(plan_svg(layout, floor))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=ROOT / "house-spec/house.json")
    parser.add_argument("--layout", type=Path, default=ROOT / "house-spec/layout-study.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec, layout = load_json(args.spec), load_json(args.layout)
    report = write_review(spec, layout, args.output) if args.output else validate(spec, layout)
    print(json.dumps(report, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

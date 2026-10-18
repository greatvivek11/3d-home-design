"""Validate the brief and layout study, and emit review plans without Blender."""

import argparse
from collections import Counter, defaultdict, deque
from html import escape
import json
import math
from pathlib import Path
import textwrap

if __package__:
    from .driveway import Driveway, check_vehicle, point_in_polygon, polygons_overlap, rect_polygon, sweep_report
else:
    from driveway import Driveway, check_vehicle, point_in_polygon, polygons_overlap, rect_polygon, sweep_report


ROOT = Path(__file__).resolve().parents[1]
FT = 0.3048
COLORS = {
    "bedroom": "#dec6aa", "bathroom": "#bad4d6", "storage": "#d4cfbc",
    "living": "#eadfcc", "kitchen": "#e4c69e", "circulation": "#f0eee6",
    "stairs": "#c8c5bb", "service": "#d0d4d7", "garage": "#c5cbd0",
    "recreation": "#cad7bb", "office": "#b7ccbf", "prayer": "#e9ce8c",
    "garden": "#a4bd89", "veranda": "#d5b993", "pool": "#79bfcd",
    "path": "#d0c9bc", "barrier": "#ffffff", "lift": "#b7c5ce",
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


def floor_footprints(floor):
    return [floor["envelope"], *(annex["rect"] for annex in floor.get("annexes", []))]


def floor_bounds(floor):
    parts = floor_footprints(floor)
    x, y = min(r[0] for r in parts), min(r[1] for r in parts)
    return [x, y, max(r[0] + r[2] for r in parts) - x, max(r[1] + r[3] for r in parts) - y]


def back_wall_is_solid(floor, item, thickness, height=2.8):
    room = next(r for r in floor["rooms"] if r["id"] == item["room"])
    edge = item.get("back_edge")
    if edge not in {"left", "right", "front", "back"}:
        return False
    axis, across, along = ("y", 0, 1) if edge in {"left", "right"} else ("x", 1, 0)
    far = edge in {"right", "back"}
    at = item["rect"][across] + (item["rect"][across + 2] if far else 0)
    boundary = room["rect"][across] + (room["rect"][across + 2] if far else 0)
    if not math.isclose(at, boundary, abs_tol=1e-6):
        return False
    center = boundary + (thickness / 2 if far else -thickness / 2)
    start, end = item["rect"][along], item["rect"][along] + item["rect"][along + 2]
    return any(w["axis"] == axis and math.isclose(w["at"], center, abs_tol=1e-6)
               and any(a <= start + 1e-6 and b >= end - 1e-6 and h >= height
                       for a, b, h in wall_parts(w, floor["openings"], 9.5))
               for w in walls(floor, thickness))


def sightline_blocked(floor, start, end, thickness):
    """Plan-ray test against full-height wall intent, not the displayed cutaway."""
    for wall in walls(floor, thickness):
        across, along = (1, 0) if wall["axis"] == "x" else (0, 1)
        distance = end[across] - start[across]
        if abs(distance) < 1e-8:
            continue
        t = (wall["at"] - start[across]) / distance
        if not 0 < t < 1:
            continue
        coordinate = start[along] + t * (end[along] - start[along])
        if any(a <= coordinate <= b and h >= 5.25 for a, b, h in wall_parts(wall, floor["openings"], 9.5)):
            return True
    return False


def stair_profile(floor):
    """Candidate U-stair geometry, not a stair-code or headroom certification."""
    room = next((r for r in floor["rooms"] if r["id"] == "stairs"), None)
    if room is None or not valid_rect(room.get("rect")) or not number(floor.get("rise")) or floor["rise"] < 0:
        raise ValueError("Invalid stair rectangle or rise")
    x, y, w, d = room["rect"]
    flight = (w - 1) / 2
    run = d - 2 * flight
    if flight <= 0 or run <= 0:
        raise ValueError("Stair reserve cannot contain two flights and landings")
    entry = floor.get("stair_entry_edge", "back")
    if entry not in {"front", "back"}:
        raise ValueError("Stair entry edge must be front or back")
    front = entry == "front"
    return {
        "rect": room["rect"], "flight_width": flight, "landing_depth": flight,
        "going": run / 9, "riser_height": floor["rise"] / 20, "risers_per_flight": 10,
        "entry_edge": entry,
        "turn": [x, y + d - flight if front else y, w, flight],
        "landing": [x, y if front else y + d - flight, w, flight],
        "opening": [x, y + flight if front else y, w, d - flight],
    }


def dining_chairs(rect):
    x, y, w, d = rect
    seats = [[x - 1.8, y + (d - 1.5) * t, 1.5, 1.5] for t in [0, 0.5, 1]]
    seats += [[x + w + 0.3, y + (d - 1.5) * t, 1.5, 1.5] for t in [0, 0.5, 1]]
    return seats + [[x + w / 2 - 0.75, y - 1.8, 1.5, 1.5], [x + w / 2 - 0.75, y + d + 0.3, 1.5, 1.5]]


def wall_partition(floor, wall):
    return next((p for p in floor.get("partitions", [])
                 if p["axis"] == wall["axis"] and math.isclose(p["at"], wall["at"], abs_tol=1e-6)), None)


def partition_between(floor, a, b):
    for axis in ["x", "y"]:
        along, across = (0, 1) if axis == "x" else (1, 0)
        ar, br = a["rect"], b["rect"]
        lo = min(ar[across] + ar[across + 2], br[across] + br[across + 2])
        hi = max(ar[across], br[across])
        start = max(ar[along], br[along])
        end = min(ar[along] + ar[along + 2], br[along] + br[along + 2])
        if lo > hi or end - start < 3:
            continue
        blocks = sorted((max(start, p["start"]), min(end, p["end"])) for p in floor.get("partitions", [])
                        if p["axis"] == axis and lo <= p["at"] <= hi and p["start"] < end and p["end"] > start)
        cursor, clear = start, 0
        for begin, finish in blocks:
            clear = max(clear, begin - cursor)
            cursor = max(cursor, finish)
        if blocks and max(clear, end - cursor) < 3:
            return True
    return False


def full_height_garage_barrier(floor, thickness):
    graph = defaultdict(set)
    for p in floor.get("partitions", []):
        if p["intended_height"] < floor["rise"]:
            continue
        a, b = ((p["start"], p["at"]), (p["end"], p["at"])) if p["axis"] == "x" else ((p["at"], p["start"]), (p["at"], p["end"]))
        graph[a].add(b)
        graph[b].add(a)
    left = floor["envelope"][0] + thickness / 2
    right = floor["envelope"][0] + floor["envelope"][2] - thickness / 2
    return any(any(math.isclose(point[0], right, abs_tol=1e-6) for point in reachable(graph, start))
               for start in graph if math.isclose(start[0], left, abs_tol=1e-6))


def structural_members(layout, floor):
    """Display proxies only; this does not calculate loads or size members."""
    config = layout["structure"]
    cw = config["display_proxy_ft"]["column_width"]
    bw = config["display_proxy_ft"]["beam_width"]
    bd = config["display_proxy_ft"]["beam_depth"]
    x, y, w, d = floor["envelope"]
    half = layout["wall_thickness"] / 2
    left, right = x + half, x + w - half
    rows = config["perimeter_rows_ft"][floor["id"]]
    supports = [(f"perimeter.{side}.{i}", px, py)
                for side, px in [("west", left), ("east", right)] for i, py in enumerate(rows)]
    lines = [(f"perimeter.{side}", (px, rows[0]), (px, rows[-1]))
             for side, px in [("west", left), ("east", right)]]
    lines += [(f"transverse.{i}", (left, py), (right, py)) for i, py in enumerate(rows)]
    for room in floor["rooms"]:
        if room["kind"] not in {"stairs", "lift"}:
            continue
        rx, ry, rw, rd = room["rect"]
        corners = [(rx + cw / 2, ry + cw / 2), (rx + rw - cw / 2, ry + cw / 2),
                   (rx + rw - cw / 2, ry + rd - cw / 2), (rx + cw / 2, ry + rd - cw / 2)]
        supports += [(f"core.{room['id']}.{i}", px, py) for i, (px, py) in enumerate(corners)]
        lines += [(f"core.{room['id']}.{i}", a, b) for i, (a, b) in enumerate(zip(corners, corners[1:] + corners[:1]))]
    supports = list({(px, py): (name, px, py) for name, px, py in supports}.values())
    result = []
    if floor["rise"]:
        result += [{"id": name, "role": "column_proxy", "rect": [px - cw / 2, py - cw / 2, cw, cw],
                    "z": 0, "height": floor["rise"], "span_ft": 0} for name, px, py in supports]
    for name, a, b in lines:
        rect = [min(a[0], b[0]), a[1] - bw / 2, abs(b[0] - a[0]), bw] if a[1] == b[1] else [
            a[0] - bw / 2, min(a[1], b[1]), bw, abs(b[1] - a[1])]
        result.append({"id": name, "role": "beam_proxy", "rect": rect, "z": -bd, "height": bd,
                       "span_ft": math.dist(a, b)})
    return result


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


def opening_meets_room(floor, room, opening, thickness):
    child = next((r for r in floor["rooms"] if r["id"] in opening["connects"]
                  and r.get("parent") == room["id"] and r.get("exclude_from_parent")), None)
    if child:
        across = 1 if opening["axis"] == "x" else 0
        return (opening_touches(child, opening, thickness)
                and room["rect"][across] < opening["at"] < room["rect"][across] + room["rect"][across + 2])
    return opening_touches(room, opening, thickness)


def door_inside_approach(room, opening):
    rect = room["rect"]
    across, along = (1, 0) if opening["axis"] == "x" else (0, 1)
    approach = rect.copy()
    approach[along], approach[along + 2] = opening["start"], opening["width"]
    approach[across] = (rect[across] if opening["at"] < rect[across] + rect[across + 2] / 2
                        else rect[across] + rect[across + 2] - 3)
    approach[across + 2] = 3
    return approach


def walls(floor, thickness, include_envelope=True):
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
            intervals = [(start, end)]
            along, across = (0, 1) if axis == "x" else (1, 0)
            for child in floor["rooms"]:
                if child.get("parent") != room["id"] or not child.get("exclude_from_parent"):
                    continue
                cr = child["rect"]
                if cr[across] - half <= at <= cr[across] + cr[across + 2] + half:
                    lo, hi = cr[along] - half, cr[along] + cr[along + 2] + half
                    intervals = [(a, min(b, lo)) for a, b in intervals if a < lo] + [
                        (max(a, hi), b) for a, b in intervals if b > hi]
            lines[(axis, round(at, 6))].extend((a, b) for a, b in intervals if b > a)
    for p in floor.get("partitions", []):
        lines[(p["axis"], round(p["at"], 6))].append((p["start"], p["end"]))
    x, y, w, d = floor["envelope"]
    for axis, at, start, end in ([
        ("x", y + half, x + half, x + w - half),
        ("x", y + d - half, x + half, x + w - half),
        ("y", x + half, y + half, y + d - half),
        ("y", x + w - half, y + half, y + d - half),
    ] if include_envelope else []):
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
    cap = spec["site"].get("user_allowed_study_cap_ft")
    if cap and any(not number(cap.get(key)) or cap[key] <= 0 or site[key] > cap[key] for key in ["width", "depth"]):
        errors.append("Candidate site exceeds the user-permitted study envelope")
    area_cap = spec["site"].get("study_area_cap_sq_ft")
    if area_cap is not None and (not number(area_cap) or area_cap <= 0 or site["width"] * site["depth"] > area_cap + 1e-6):
        errors.append("Candidate site exceeds the user-permitted plot area")
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
        annexes = f.get("annexes", [])
        if any(not valid_rect(a.get("rect")) or not contains(bounds, a["rect"])
               or not adjacent(envelope, a["rect"]) or overlap(envelope, a["rect"]) > 1e-6 for a in annexes):
            errors.append(f"{fid}: invalid/detached/out-of-site annex")
            continue
        if not number(f.get("elevation")) or not number(f.get("rise")) or f["rise"] < 0:
            errors.append(f"{fid}: invalid elevation/rise")
        rs = f.get("rooms", [])
        room_ids = [r["id"] for r in rs]
        if len(set(room_ids)) != len(room_ids):
            errors.append(f"{fid}: duplicate room IDs")
        for r in rs:
            assignments[r["id"]].append(fid)
            if not valid_rect(r.get("rect")) or not any(contains(part, r["rect"]) for part in floor_footprints(f)):
                errors.append(f"{fid}/{r['id']}: invalid/out-of-envelope rectangle")
        if any(not valid_rect(r.get("rect")) for r in rs):
            continue
        by_id = {r["id"]: r for r in rs}
        profile = None
        if "stairs" in by_id:
            try:
                profile = stair_profile(f)
            except ValueError as error:
                errors.append(f"{fid}: {error}")
            else:
                if profile["flight_width"] < 4 or profile["landing_depth"] < 4 or profile["going"] < 1:
                    errors.append(f"{fid}: candidate stairs need 4 ft flights/landings and at least 12 in goings")
                if f["rise"] and not .5 <= profile["riser_height"] <= 7 / 12:
                    errors.append(f"{fid}: candidate stair risers must stay within the proposed 6-7 in comfort range")
        for i, a in enumerate(rs):
            if a.get("parent"):
                parent = by_id.get(a["parent"])
                boundary_cutout = (fid == "basement" and a["kind"] == "lift" and a.get("boundary_cutout")
                                   and a.get("exclude_from_parent") and parent and overlap(parent["rect"], a["rect"]) > 0)
                if not parent or (not contains(parent["rect"], a["rect"]) and not boundary_cutout):
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
            elif any(overlap(item["rect"], [r["rect"][0] - thickness, r["rect"][1] - thickness,
                                           r["rect"][2] + 2 * thickness, r["rect"][3] + 2 * thickness]) > 1e-6
                     for r in rs if r.get("parent") == item["room"] and r.get("exclude_from_parent")
                     and not r.get("open")):
                errors.append(f"{fid}/{item['id']}: furniture overlaps excluded child-room wall allowance")
            if item.get("kind") == "dining_table" and item.get("room") in by_id and valid_rect(item.get("rect")):
                if any(not contains(by_id[item["room"]]["rect"], chair) for chair in dining_chairs(item["rect"])):
                    errors.append(f"{fid}: eight dining chairs must fit the dining zone")
        for i, a in enumerate(f.get("furniture", [])):
            for b in f["furniture"][i + 1:]:
                if valid_rect(a.get("rect")) and valid_rect(b.get("rect")) and overlap(a["rect"], b["rect"]) > 1e-6:
                    errors.append(f"{fid}: furniture collision {a['id']} / {b['id']}")
        for bed in (item for item in f.get("furniture", []) if item["kind"] == "bed"
                    and item.get("room") in by_id and valid_rect(item.get("rect"))):
            if not back_wall_is_solid(f, bed, thickness):
                errors.append(f"{fid}/{bed['id']}: headboard must meet a solid room wall without blocking glazing or doors")
            tables = [item for item in f["furniture"] if item.get("bed_id") == bed["id"] and item["kind"] == "bedside_table"]
            along = 1 if bed.get("back_edge") in {"left", "right"} else 0
            if (len(tables) != 2
                    or not any(t["rect"][along] + t["rect"][along + 2] <= bed["rect"][along] + 1e-6 for t in tables)
                    or not any(t["rect"][along] >= bed["rect"][along] + bed["rect"][along + 2] - 1e-6 for t in tables)):
                errors.append(f"{fid}/{bed['id']}: two bedside tables must flank the headboard")
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
            elif any(not opening_meets_room(f, by_id[ref], o, thickness) for ref in refs if ref != "outside"):
                errors.append(f"{fid}: opening does not touch its connected rooms: {refs}")
            if profile and "stairs" in refs and o.get("kind") != "window":
                if not opening_touches({"rect": profile["landing"]}, o, thickness):
                    errors.append(f"{fid}: stair access must meet its full-depth landing, not a flight or turn")
        root = spec["building"]["circulation"].get("primary_front_entry_room_id", "receiving") if fid == "ground" else "stairs"
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
            if not full_height_garage_barrier(basement, thickness):
                errors.append("Basement needs a continuous intended full-height garage separation, including core returns")
            for airlock in buffer:
                doors = [o for o in basement["openings"] if airlock in o["connects"] and o.get("kind") != "window"]
                others = {ref for o in doors for ref in o["connects"] if ref != airlock}
                if len(doors) != 2 or not all(o.get("self_closing") for o in doors) or not others & clean or not others & garage:
                    errors.append("Garage airlock needs two self-closing doors between clean and garage zones")
            checks.append("Concept garage barrier, two-door airlock and protected clean-side adjacency checked; NOT an airflow/fire certification")
        fixtures = [item for f in floor_map.values() for item in f["furniture"]]
        fixture_requirements = {
            "master_bathroom": {"wc_cubicle": next(r["separate_toilet_cubicles"] for f in spec["floors"] for r in f["rooms"] if r["id"] == "master_bathroom"),
                                "basin": 1, "bathtub": 1, "shower": 1},
            "guest_bathroom": {"toilet": 1, "basin": 1, "shower": 1},
            "family_toilet": {"toilet": 1, "basin": 1},
            "utility_store": {"shelf": 1},
            "basement_toilet": {"toilet": 1, "basin": 1},
            "first_common_toilet": {"toilet": 1, "basin": 1},
            "laundry": {"equipment": 1, "basin": 1, "counter": 1, "shelf": 1},
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
        master_items = [item for item in floor_map["ground"]["furniture"] if item["room"] == "master_bathroom"]
        if sum(1 if item["kind"] == "basin" else 2 if item["kind"] == "double_basin" else 0 for item in master_items) != 1:
            errors.append("Master bathroom requires exactly one basin")
        for item in master_items:
            if item["kind"] == "wc_cubicle" and not back_wall_is_solid(floor_map["ground"], item, thickness):
                errors.append("Master WC must back onto a real bathroom wall")
        expected_toilets = sum(r.get("toilet_count", 0) + r.get("separate_toilet_cubicles", 0)
                               for f in spec["floors"] for r in f["rooms"])
        if sum(item["kind"] in {"toilet", "wc_cubicle"} for item in fixtures) != expected_toilets:
            errors.append(f"{expected_toilets} toilets required by the current brief")
        basement_rooms = {r["id"]: r for r in basement["rooms"]}
        if spec["floors"][0].get("planning", {}).get("equal_recreation_areas_required") and {"gym", "tech_cave"} <= basement_rooms.keys():
            if not math.isclose(room_area(basement, basement_rooms["gym"]), room_area(basement, basement_rooms["tech_cave"]), abs_tol=1e-6):
                errors.append("Gym and gaming rooms must have equal usable areas")
        for floor in floor_map.values():
            graph = access_graph(floor)
            for room in floor["rooms"]:
                if room["kind"] == "bedroom":
                    glazing = [o for o in floor["openings"] if o.get("kind") in {"window", "slider"}
                               and set(o["connects"]) == {room["id"], "outside"} and o.get("operable") is True
                               and number(o.get("height")) and o["height"] >= 7 and o["width"] >= 9]
                    fx, fy, fw, fd = floor["envelope"]
                    if not any(any(math.isclose(o["at"], edge, abs_tol=1e-6) for edge in
                                   ([fy + thickness / 2, fy + fd - thickness / 2] if o["axis"] == "x" else [fx + thickness / 2, fx + fw - thickness / 2]))
                               for o in glazing):
                        errors.append(f"{floor['id']}/{room['id']}: large outward-facing operable bedroom glazing required")
            for required_room in next((f["rooms"] for f in spec["floors"] if f["id"] == floor["id"]), []):
                if "access_from" in required_room and required_room["id"] in graph and graph[required_room["id"]] != set(required_room["access_from"]):
                    errors.append(f"{required_room['id']}: doors must open only to its specified access rooms")
        ground = floor_map["ground"]
        ground_rooms = {r["id"]: r for r in ground["rooms"]}
        if {"entrance_gallery", "cross_passage", "family_toilet", "guest_bathroom", "utility_store"} <= ground_rooms.keys():
            entry, gallery, wc, bath, store = (ground_rooms[rid] for rid in
                                               ["entrance_gallery", "cross_passage", "family_toilet", "guest_bathroom", "utility_store"])
            front = ground["envelope"][1] + thickness / 2
            front_doors = [o for o in ground["openings"] if "outside" in o["connects"] and o.get("kind") != "window"
                           and o["axis"] == "x" and math.isclose(o["at"], front, abs_tol=1e-6)]
            if len(front_doors) != 1 or set(front_doors[0]["connects"]) != {"entrance_gallery", "outside"}:
                errors.append("Exactly one front entrance must open to the Entrance Gallery, not drawing or guest")
            if entry["rect"][2] != 4 or gallery["rect"][3] != 4:
                errors.append("Candidate Entrance Gallery and House Gallery must retain the requested 4 ft widths")
            if not adjacent(wc["rect"], gallery["rect"]) or wc["rect"][0] + wc["rect"][2] > gallery["rect"][0]:
                errors.append("Ground common WC must terminate the left end of the House Gallery")
            if bath.get("parent") != "guest_bedroom" or not bath.get("exclude_from_parent"):
                errors.append("Guest ensuite must be private, inside the guest room and excluded from sleeping-zone area")
            if (store.get("parent") is not None
                    or not adjacent(store["rect"], gallery["rect"])
                    or store["rect"][1] < ground_rooms["stairs"]["rect"][1] + ground_rooms["stairs"]["rect"][3]
                    or store["rect"][1] + store["rect"][3] > ground_rooms["family_living"]["rect"][1]
                    or store["rect"][0] < gallery["rect"][0] + gallery["rect"][2]
                    or overlap(store["rect"], ground_rooms["family_living"]["rect"]) > 0
                    or any(overlap(store["rect"], ground_rooms[rid]["rect"]) > 0 for rid in ["entrance_gallery", "cross_passage", "lift_lobby"])):
                errors.append("Utility cupboard must terminate the right House Gallery outside living and preserve its 4 ft through-route")
            for rid in ["entrance_gallery", "cross_passage", "lift_lobby"]:
                if not ground_rooms.get(rid, {}).get("label"):
                    errors.append(f"{rid}: shared galleries and landings need visible room labels")
            common = reachable(access_graph(ground), "entrance_gallery",
                               {"receiving", "guest_bedroom", "guest_bathroom", "master_bedroom", "master_bathroom", "master_wardrobe", "outside"})
            if not {"family_toilet", "utility_store", "lift", "stairs", "family_living"} <= common:
                errors.append("House Gallery, common WC, utility cupboard and core need shared access without private rooms or outside")
            checks.append("Single controlled front entry, private guest ensuite, left-end WC, labelled wider galleries and recessed utility storage checked; door operation/egress unverified")
            graph = access_graph(ground)
            master_entry = ground_rooms.get("master_entry")
            if (not master_entry or master_entry["rect"][2] != 3
                    or graph.get("master_entry") != {"cross_passage", "master_bedroom"}
                    or graph.get("master_wardrobe") != {"master_bedroom", "master_bathroom"}
                    or graph.get("master_bathroom") != {"master_wardrobe"}):
                errors.append("Master suite needs a separate 3 ft entrance to bedroom and private bedroom-dressing-bath access")
            if master_entry and any(overlap(master_entry["rect"], item["rect"]) > 1e-6 for item in ground["furniture"]):
                errors.append("Private master entrance passage must remain furniture-free")
            entry_opening = next((o for o in ground["openings"] if o.get("id") == "family_entry"), None)
            dining_boundaries = [public for public in [entry, gallery] if adjacent(public["rect"], ground_rooms["dining"]["rect"])]
            if ("dining" in graph["cross_passage"] or not dining_boundaries
                    or any(not partition_between(ground, public, ground_rooms["dining"]) for public in dining_boundaries)
                    or entry_opening is None
                    or entry_opening.get("kind") != "open_archway" or entry_opening["width"] < 6):
                errors.append("Public gallery needs an opaque dining boundary and wide doorless offset family entry")
            targets = [item for item in ground["furniture"] if item["id"] in
                       {"family_sofa", "family_coffee_table", "prayer_shelf", "dining_table", "island"}]
            observers = ground.get("privacy_observers", [])
            if not observers or any(not contains(entry["rect"], [x, y, .01, .01]) for x, y in observers):
                errors.append("Privacy observers must sample the actual Entrance Gallery")
            if any(not sightline_blocked(ground, [x, y], [tx, ty], thickness)
                   for x, y in observers for item in targets
                   for tx in [item["rect"][0], item["rect"][0] + item["rect"][2]]
                   for ty in [item["rect"][1], item["rect"][1] + item["rect"][3]]):
                errors.append("Entrance Gallery has an unblocked sightline into the private family furniture")
            if entry_opening:
                approach = ([entry_opening["start"], entry_opening["at"] + thickness / 2, entry_opening["width"], 8]
                            if entry_opening["axis"] == "x" else
                            [entry_opening["at"] + thickness / 2, entry_opening["start"], 3.5, entry_opening["width"]])
                if any(overlap(approach, item["rect"]) > 1e-6 for item in ground["furniture"]):
                    errors.append("Wide family entry approach must remain free of furniture")
            family_ids = {"family_living", "dining", "kitchen"}
            if (any(not ground_rooms[rid].get("open") for rid in family_ids)
                    or not family_ids <= reachable(graph, "family_living", set(graph) - family_ids)):
                errors.append("Family living, dining and kitchen must remain internally open")
        for fid, rid in [("ground", "receiving"), ("ground", "family_living"), ("first", "office")]:
            if not any(o["axis"] == "y" and set(o["connects"]) == {rid, "outside"}
                       and o.get("kind") == "window" and o.get("operable") and o["width"] >= 6
                       for o in floor_map[fid]["openings"]):
                errors.append(f"{fid}/{rid}: operable side-wall glazing required")
        fridge = [item for item in fixtures if item["id"] == "kitchen_fridge"]
        if len(fridge) != 1 or fridge[0]["room"] != "pantry":
            errors.append("Refrigerator must be inside the enlarged pantry, not kitchen")
        if "prayer_alcove" in ground_rooms:
            prayer = ground_rooms["prayer_alcove"]["rect"]
            if any(adjacent(prayer, r["rect"]) or overlap(prayer, r["rect"]) > 0 for r in ground["rooms"] if r["kind"] == "bathroom"):
                errors.append("Prayer corner must not adjoin a WC/bathroom")
            for o in ground["openings"]:
                if o.get("kind") == "slider" and "family_living" in o["connects"]:
                    exit_route = [o["start"], o["at"] - 3.25, o["width"], 3]
                    if overlap(prayer, exit_route) > 0:
                        errors.append("Prayer corner must not obstruct the living-room garden exit")
        first = floor_map["first"]
        first_rooms = {r["id"]: r for r in first["rooms"]}
        if "upstairs_lounge" in first_rooms:
            lounge = first_rooms["upstairs_lounge"]
            common_wc = first_rooms.get("first_common_toilet")
            if ({"front_landing", "east_gallery"} & first_rooms.keys()
                    or not lounge.get("open") or lounge["rect"][3] < 14):
                errors.append("First floor needs a unified open lounge without east or west galleries")
            if (not common_wc or common_wc.get("parent") != "upstairs_lounge"
                    or not common_wc.get("exclude_from_parent")
                    or common_wc["rect"][0] < first_rooms["stairs"]["rect"][0]
                    or not adjacent(common_wc["rect"], first_rooms["stairs"]["rect"])):
                errors.append("First-floor common WC must be recessed at the lounge stair end")
            if common_wc:
                wc_items = [i for i in first["furniture"] if i["room"] == common_wc["id"]]
                for door in first["openings"]:
                    if common_wc["id"] not in door["connects"] or door.get("kind") == "window":
                        continue
                    approach = door_inside_approach(common_wc, door)
                    if (door["width"] < 3 or not contains(common_wc["rect"], approach)
                            or any(overlap(approach, i["rect"]) > 1e-6 for i in wc_items)):
                        errors.append("First-floor common WC needs a furniture-free 3 ft inside doorway approach")
                for item in wc_items:
                    if item["kind"] == "toilet":
                        if (not back_wall_is_solid(first, item, thickness)
                                or common_wc["rect"][1] + common_wc["rect"][3] - item["rect"][1] - item["rect"][3] < 2):
                            errors.append("First-floor common WC needs a wall-backed toilet and at least 2 ft frontal space")
            for rid in ["child_bathroom_1", "child_wardrobe_1"]:
                if rid in first_rooms and first_rooms[rid]["rect"][1] + first_rooms[rid]["rect"][3] > lounge["rect"][1] - thickness:
                    errors.append("Child 1 bath and dressing must stay in the front band, outside the family lounge")
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
                for door in first["openings"]:
                    if set(door["connects"]) != {bed, wardrobe} or door.get("kind") == "window":
                        continue
                    approach = door_inside_approach(first_rooms[wardrobe], door)
                    if not contains(first_rooms[wardrobe]["rect"], approach) or any(overlap(approach, shelf) > 1e-6 for shelf in shelves):
                        errors.append(f"{wardrobe}: bedroom doorway needs a furniture-free 3 ft inside approach")
                if not any(item["room"] == bath and item["kind"] == "shower"
                           and item.get("enclosed") and item.get("entry_side") in {"north", "south", "east", "west"}
                           for item in first["furniture"]):
                    errors.append(f"{bath}: enclosed shower intent required beside the dry dressing area")
            common = reachable(graph, "stairs", suite_ids | {"office", "outside"})
            if not {"upstairs_lounge", "rear_gallery", "first_common_toilet"} <= common:
                errors.append("Shared rear balcony route must not cross a private bedroom, office or suite")
            checks.append("Private connected bath/dressing suites, clear dressing aisles and 3 ft inside bedroom-door approaches, shared-circulation WC and common rear-balcony route checked; wet-area engineering unverified")
        if spec["building"]["circulation"].get("lift_required"):
            lifts = [next((r for r in floor_map[fid]["rooms"] if r["kind"] == "lift"), None)
                     for fid in spec["building"]["circulation"]["lift_connects"]]
            if any(r is None for r in lifts) or any(r["rect"] != lifts[0]["rect"] for r in lifts if r):
                errors.append("Lift shaft footprints must align on every required level")
            for floor in floor_map.values():
                lift_rooms = [r for r in floor["rooms"] if r["kind"] == "lift"]
                if len(lift_rooms) != 1 or lift_rooms[0].get("open"):
                    errors.append(f"{floor['id']}: exactly one enclosed lift shaft required")
                    continue
                lift = lift_rooms[0]
                doors = [o for o in floor["openings"] if lift["id"] in o["connects"] and o.get("kind") != "window"]
                by_id = {r["id"]: r for r in floor["rooms"]}
                stair = by_id.get("stairs")
                if stair and (not math.isclose(lift["rect"][1] + lift["rect"][3], stair["rect"][1] - thickness, abs_tol=1e-6)
                              or lift["rect"][0] < stair["rect"][0]
                              or lift["rect"][0] + lift["rect"][2] > stair["rect"][0] + stair["rect"][2]):
                    errors.append(f"{floor['id']}: lift must be directly in front of the stairs in the front-lawn band")
                if floor["id"] != "basement" and (overlap(lift["rect"], floor["envelope"]) > 1e-6
                        or not any(contains(a["rect"], lift["rect"]) for a in floor.get("annexes", []))):
                    errors.append(f"{floor['id']}: front-lawn lift must be outside the main above-ground plate")
                if "stair_link" in by_id or any(a["id"] != "front_lawn_lift" for a in floor.get("annexes", [])):
                    errors.append(f"{floor['id']}: no external stair link or side annex is permitted")
                common_doors = [o for o in floor["openings"] if "stairs" in o["connects"]
                                and lift["id"] not in o["connects"] and o.get("kind") != "window"]
                common_refs = [ref for o in common_doors for ref in o["connects"] if ref != "stairs"]
                if (len(common_refs) != 1 or common_refs[0] not in by_id
                        or by_id[common_refs[0]]["kind"] != "circulation"
                        or not contains(floor["envelope"], by_id[common_refs[0]]["rect"])):
                    errors.append(f"{floor['id']}: full-floor stair landing needs direct internal shared-gallery access")
                others = [ref for o in doors for ref in o["connects"] if ref != lift["id"]]
                if len(doors) != 1 or doors[0].get("kind") != "lift_door" or others != ["stairs"]:
                    errors.append(f"{floor['id']}: lift needs one landing door directly into the shared stair enclosure")
                if any(min(stair_profile(floor)["landing"][2:]) < 4 for ref in others if ref == "stairs"):
                    errors.append(f"{floor['id']}: lift needs a candidate shared landing at least 4 ft deep")
                blocked = {r["id"] for r in floor["rooms"] if r["kind"] in {"bedroom", "bathroom", "office"}}
                blocked |= set(floor.get("air_zones", {}).get("garage", [])) | set(floor.get("air_zones", {}).get("buffer", [])) | {"outside"}
                if lift["id"] not in reachable(access_graph(floor), "stairs", blocked):
                    errors.append(f"{floor['id']}: lift landing must be reachable without a private room or garage")
            checks.append("Four aligned lift reserves and shared clean-side landing topology checked; product, pit, overrun, fire/accessibility and egress NOT verified")
        structure = layout.get("structure", {})
        if spec.get("structural_visualization", {}).get("required"):
            if structure.get("status") != "illustrative_only_not_engineered" or not structure.get("disclaimer"):
                errors.append("Structural view must explicitly remain non-engineered")
            proxy = structure.get("display_proxy_ft", {})
            if not all(number(proxy.get(key)) and 0 < proxy[key] <= thickness for key in ["column_width", "beam_width", "beam_depth"]):
                errors.append("Invalid display-only structural proxies; these are not engineering sizes")
            for fid, floor in floor_map.items():
                rows = structure.get("perimeter_rows_ft", {}).get(fid, [])
                lo, hi = floor["envelope"][1] + thickness / 2, sum(floor["envelope"][1::2]) - thickness / 2
                if (len(rows) < 2 or not all(number(v) for v in rows) or rows != sorted(set(rows))
                        or rows[0] != lo or rows[-1] != hi):
                    errors.append(f"{fid}: invalid conceptual perimeter support rows")
            if not errors:
                for fid, ids in structure.get("clear_span_rooms", {}).items():
                    floor = floor_map[fid]
                    by_id = {r["id"]: r for r in floor["rooms"]}
                    for rid in ids:
                        if rid not in by_id:
                            errors.append(f"Unresolved structural clear-span room: {fid}/{rid}")
                            continue
                        for member in structural_members(layout, floor):
                            if member["role"] == "column_proxy" and any(overlap(member["rect"], part) > 1e-6 for part in room_footprints(floor, by_id[rid])):
                                errors.append(f"{fid}/{rid}: structural proxy intrudes into the requested clear-span area")
                checks.append("No display-column proxies inside requested living/parking clear-span footprints; NOT a structural feasibility check")
    for item in layout.get("outdoor", []) + layout.get("balconies", []):
        if not valid_rect(item.get("rect")) or not contains(bounds, item["rect"]):
            errors.append(f"Outdoor/balcony out of bounds: {item.get('id')}")
    ramp = layout["ramp"]
    if not valid_rect(ramp["rect"]) or not contains(bounds, ramp["rect"]):
        errors.append("Invalid/out-of-site ramp")
    driveway_report = None
    try:
        road = Driveway(ramp)
        check_vehicle(ramp["design_vehicle"])
    except (ValueError, KeyError) as error:
        errors.append(f"Invalid ramp profile: {error}")
    else:
        if not math.isclose(road.elevation(road.length), floor_map["basement"]["elevation"], abs_tol=1e-6):
            errors.append("Ramp landing must meet basement elevation")
        outdoors = {item["id"]: item for item in layout.get("outdoor", [])}
        pool, barrier = outdoors.get("pool"), outdoors.get("pool_barrier")
        if spec["outdoor"]["pool"]["required"] and not spec["outdoor"]["pool"].get("deferred_for_compact_study") and pool is None:
            errors.append("The restored brief requires a modeled pool, not a compact-site deferral")
        if pool:
            if barrier is None or not valid_rect(barrier.get("rect")) or not valid_rect(pool.get("rect")) or not contains(barrier["rect"], pool["rect"]):
                errors.append("Pool needs a surrounding barrier reserve")
            sections = road.sections()
            pavement = [[a.offset(-a.inner), b.offset(-b.inner), b.offset(b.outer), a.offset(a.outer)]
                        for a, b in zip(sections, sections[1:])]
            vehicle = [road.vehicle_footprint(s, ramp["design_vehicle"]) for s in road.stations()]
            for item in [pool, *([barrier] if barrier else [])]:
                if not valid_rect(item.get("rect")):
                    continue
                if overlap(item["rect"], floor_map["basement"]["envelope"]) > 1e-6:
                    errors.append(f"{item['id']}: pool and barrier must remain outside the basement footprint")
                polygon = rect_polygon(item["rect"])
                if any(polygons_overlap(polygon, part) for part in pavement + vehicle):
                    errors.append(f"{item['id']}: pool and barrier must remain clear of driveway pavement and the sampled vehicle sweep")
            checks.append("Pool/barrier plan separation from basement, driveway pavement and buffered SUV sweep checked; structure, deck clearances and child safety NOT certified")
        if not errors:
            bsm = floor_map["basement"]
            aisle = next(r["rect"] for r in bsm["rooms"] if r["id"] == "drive_aisle")
            portal = next(o for o in bsm["openings"] if o.get("id") == "garage_ramp_portal")
            overhead = {"canopy_under_ft": layout["weather_protection"]["ramp_roof_clear_height_ft"],
                        "basement_cover_rect": bsm["envelope"], "slab_under_ft": floor_map["ground"]["elevation"] - .5,
                        "finish_ft": ramp["surface_finish_ft"]}
            driveway_report = sweep_report(ramp, aisle, [item["rect"] for item in bsm["furniture"]], bounds, portal, overhead)
            errors.extend(driveway_report["errors"])
            checks.append("Sampled large-SUV body/overhang sweep, flared portal, eased grades and clear arrival aisle checked; not a traffic-engineering certification")
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
        "total_floor_areas_sq_ft": {fid: sum(r[2] * r[3] for r in floor_footprints(f)) for fid, f in floor_map.items()},
        "driveway": driveway_report,
        "front_yard_fraction": site["front_depth"] / site["depth"],
        "back_yard_fraction": (site["depth"] - site["back_start"]) / site["depth"],
        "errors": errors,
        "checks": checks,
        "review": layout["review_items"],
    }


def plan_svg(layout, floor=None):
    scale, pad = 12, 70
    depth = layout["site"]["depth"]
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
        parts.append(f'<rect x="{pad + x * scale}" y="{pad + (depth - y - d) * scale}" width="{w * scale}" height="{d * scale}" fill="{fill}" stroke="{stroke}" stroke-width="1"'
                     + (' stroke-dasharray="5 4"' if dash else '') + '/>')

    def label(r, name, size=True, area=None):
        x, y, w, d = r
        lines = textwrap.wrap(name, max(10, int(w * 1.7)))
        if size:
            extent = "ft extents" if area is not None and not math.isclose(area, w * d) else "ft"
            lines.append(f'{w:g} x {d:g} {extent} | {area if area is not None else w * d:g} sq ft')
        for i, line in enumerate(lines):
            parts.append(f'<text x="{pad + (x + w / 2) * scale}" y="{pad + (depth - y - d / 2) * scale + (i - len(lines) / 2) * 12}" text-anchor="middle" font-size="10">{escape(line)}</text>')

    def driveway():
        road = Driveway(layout["ramp"])
        points = " ".join(f"{pad + x * scale:.3f},{pad + (depth - y) * scale:.3f}" for x, y in road.polygon())
        parts.append(f'<polygon data-role="curved-driveway" points="{points}" fill="#bac0c3" stroke="#697b77" stroke-width="1"/>')

    rect([0, 0, layout["site"]["width"], depth], "#eef1e5", "#536a56")
    if floor is None or floor["id"] == "ground":
        for item in layout["outdoor"]:
            if item["kind"] != "barrier":
                rect(item["rect"], COLORS[item["kind"]])
                if floor is None:
                    label(item["rect"], item["name"], item["kind"] != "path")
        driveway()
        label([layout["ramp"]["start"][0] - layout["ramp"]["clear_width_ft"] / 2, 12,
               layout["ramp"]["clear_width_ft"], 40],
              "RAMP: 12 ft straight / widened bend / 14% straight max, 10% curve max / NOT ENGINEERED", False)
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
        for plate in floor_footprints(floor):
            rect(plate, "#f2ede1")
        if floor["id"] == "basement":
            driveway()
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
                partition = wall_partition(floor, wall)
                color = "#a35f37" if partition and partition.get("role") != "privacy_wall" else "#46514b"
                parts.append(f'<line x1="{pad + x1 * scale}" y1="{pad + (depth - y1) * scale}" x2="{pad + x2 * scale}" y2="{pad + (depth - y2) * scale}" stroke="{color}" stroke-width="4"/>')
        for room in floor["rooms"]:
            if (room["kind"] != "circulation" or room.get("label")) and (not room.get("parent") or room.get("exclude_from_parent")):
                label(room["rect"], room["name"], area=room_area(floor, room))
        for p in floor.get("partitions", []):
            if p["axis"] == "x":
                parts.append(f'<text x="{pad + (p["start"] + p["end"]) / 2 * scale}" y="{pad + (depth - p["at"]) * scale - 7}" text-anchor="middle" font-size="9">{escape(p["label"])}</text>')
        for o in floor["openings"]:
            axis, at, start, w = o["axis"], o["at"], o["start"], o["width"]
            x, y = (start, at) if axis == "x" else (at, start)
            endx, endy = (x + w, y) if axis == "x" else (x, y + w)
            color = "#468ba6" if o.get("kind") in {"window", "slider"} else "#8c6699" if o.get("kind") == "soft_divider" else "#b8753b"
            parts.append(f'<line x1="{pad + x * scale}" y1="{pad + (depth - y) * scale}" x2="{pad + endx * scale}" y2="{pad + (depth - endy) * scale}" stroke="{color}" stroke-width="2" stroke-dasharray="3 2"/>')
    parts.extend([
        f'<text x="{width / 2}" y="{height - 105}" text-anchor="middle" font-size="14">FRONT / ROAD CONVENTION - {layout["site"]["width"]:g} ft</text>',
        f'<text x="{pad}" y="{height - 70}" font-size="12">All dimensions proposed. L-shaped zones list outer extents and net area excluding enclosed child rooms.</text>',
        f'<text x="{pad}" y="{height - 50}" font-size="12">Dark: cutaway walls. Orange: doors. Blue: glazing. Purple: soft bath/dressing dividers.</text>',
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

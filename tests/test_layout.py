import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.layout import ROOT, access_graph, facade_edges, facade_openings, facade_pieces, back_wall_is_solid, contains, dining_chair_turns, dining_chairs, door_inside_approach, feet, floor_bounds, full_height_garage_barrier, load_json, opening_meets_room, opening_touches, overlap, plan_svg, partition_between, reachable, room_area, room_footprints, sightline_blocked, square_feet, stair_profile, structural_members, subtract_rectangles, validate, validate_brief, wall_parts, walls, write_review
from scripts.driveway import Driveway


def translated_floor(floor, offset):
    result = copy.deepcopy(floor)
    for rect in [result["envelope"], *(a["rect"] for a in result.get("annexes", [])),
                 *(r["rect"] for r in result["rooms"]), *(i["rect"] for i in result["furniture"])]:
        rect[1] += offset
    for opening in result["openings"] + result.get("partitions", []):
        for key in (["at"] if opening["axis"] == "x" else ["start", *(["end"] if "end" in opening else [])]):
            opening[key] += offset
    for point in result.get("privacy_observers", []):
        point[1] += offset
    return result


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_json(ROOT / "house-spec/house.json")
        self.layout = load_json(ROOT / "house-spec/layout-study.json")

    def errors(self):
        return validate(self.spec, self.layout)["errors"]

    def test_current_study_passes_geometry_but_needs_review(self):
        report = validate(self.spec, self.layout)
        self.assertEqual(report["geometry_status"], "PASS")
        self.assertEqual(report["status"], "NEEDS REVIEW")
        self.assertFalse(report["layout_approved"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["plot_area_sq_ft"], 8120)
        self.assertEqual(report["plot_expansion_above_initial_max_percent"], 0)
        self.assertAlmostEqual(report["front_yard_fraction"], 24 / 116)
        self.assertAlmostEqual(report["back_yard_fraction"], 42 / 116)
        self.assertEqual(report["front_yard_area_sq_ft"], 1680)
        self.assertEqual(report["back_yard_area_sq_ft"], 2940)
        self.assertAlmostEqual(report["total_floor_areas_sq_ft"]["basement"], 50 * 80.33333333333333)
        self.assertEqual({fid: report["total_floor_areas_sq_ft"][fid] for fid in ["ground", "first", "roof"]},
                         {"ground": 2560, "first": 2560, "roof": 2560})
        self.assertEqual(report["driveway"]["status"], "PASS")
        self.assertGreaterEqual(report["driveway"]["minimum_roof_clearance_m"], .3)
        self.assertGreaterEqual(report["driveway"]["minimum_underbody_clearance_m"], .1)

    def test_units(self):
        self.assertAlmostEqual(feet(10), 3.048)
        self.assertAlmostEqual(square_feet(100), 9.290304)

    def test_yard_expansion_is_exactly_twenty_and_forty_percent_of_previous_bands(self):
        prior = load_json(ROOT / "assets/models/study-011/layout-snapshot.json")
        old, site = prior["site"], self.layout["site"]
        self.assertEqual(site, {"width": 70, "depth": 116, "front_depth": 24, "back_start": 74})
        self.assertAlmostEqual(site["width"] * site["front_depth"] / (old["width"] * old["front_depth"]), 1.2)
        self.assertAlmostEqual(site["width"] * (site["depth"] - site["back_start"]) /
                               (old["width"] * (old["depth"] - old["back_start"])), 1.4)
        self.assertEqual(site["back_start"] - site["front_depth"], 50)
        outdoors = {item["id"]: item["rect"] for item in self.layout["outdoor"]}
        self.assertEqual(outdoors["front_lawn"], [4, 0, 50, 17])
        self.assertEqual(outdoors["play_lawn"], [4, 81, 48, 27])
        for rid in ["pool", "pool_barrier", "tree_buffer"]:
            before = next(item["rect"] for item in prior["outdoor"] if item["id"] == rid)
            self.assertEqual(outdoors[rid], [before[0], before[1] + 16, *before[2:]])
        for rid in ["front_veranda", "back_veranda", "drying"]:
            before = next(item["rect"] for item in prior["outdoor"] if item["id"] == rid)
            self.assertEqual(outdoors[rid], [before[0], before[1] + 4, *before[2:]])

    def test_yard_expansion_preserves_every_floor_fixture_opening_and_core(self):
        prior = load_json(ROOT / "assets/models/study-011/layout-snapshot.json")
        expanded = load_json(ROOT / "assets/models/study-012/layout-snapshot.json")
        self.assertEqual(expanded["floors"], [translated_floor(floor, 4) for floor in prior["floors"]])
        self.assertEqual(self.layout["site"], expanded["site"])
        self.assertEqual(self.layout["structure"]["perimeter_rows_ft"],
                         {fid: [v + 4 for v in rows] for fid, rows in prior["structure"]["perimeter_rows_ft"].items()})
        for a, b in zip(prior["balconies"], self.layout["balconies"]):
            self.assertEqual(b["rect"], [a["rect"][0], a["rect"][1] + 4, *a["rect"][2:]])

    def test_ramp_adds_only_a_level_approach_and_preserves_the_entire_old_descent(self):
        prior = load_json(ROOT / "assets/models/study-011/layout-snapshot.json")
        old, road = Driveway(prior["ramp"]), Driveway(self.layout["ramp"])
        self.assertEqual(road.start, old.start)
        self.assertAlmostEqual(road.length, old.length + 4)
        for s in [0, 1, 2, 3, 4]:
            self.assertEqual(road.elevation(s), 0)
            self.assertEqual(road.grade(s), 0)
        for s in old.stations():
            before, after = old.at(s), road.at(s + 4)
            self.assertAlmostEqual(after.x, before.x)
            self.assertAlmostEqual(after.y, before.y + 4)
            for key in ["z", "tx", "ty", "inner", "outer"]:
                self.assertAlmostEqual(getattr(after, key), getattr(before, key))
            self.assertAlmostEqual(road.grade(s + 4), old.grade(s))

    def test_yard_depth_targets_cannot_be_silently_reduced_or_malformed(self):
        for key, value in [("front_depth", 23), ("back_start", 75), ("front_depth", None), ("back_start", 120)]:
            with self.subTest(key=key, value=value):
                self.setUp()
                self.layout["site"][key] = value
                self.assertTrue(any("yard" in error for error in self.errors()))

    def test_revised_basement_equal_recreation_and_front_of_garage_cars(self):
        floor = self.layout["floors"][0]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertEqual(floor["envelope"], [4, 6.5, 50, 80.33333333333333])
        self.assertAlmostEqual(room_area(floor, rooms["gym"]), 387.75)
        self.assertAlmostEqual(room_area(floor, rooms["tech_cave"]), 387.75)
        self.assertGreaterEqual(rooms["drive_aisle"]["rect"][3], 16)
        self.assertLess(rooms["gym"]["rect"][1], rooms["general_storage"]["rect"][1])
        self.assertGreater(rooms["vehicle_parking"]["rect"][1], 41)
        self.assertLess(rooms["vehicle_parking"]["rect"][1], rooms["drive_aisle"]["rect"][1])
        self.assertEqual(rooms["vehicle_parking"]["rect"][2:], [33, 19.5])

    def test_clean_basement_rooms_do_not_require_crossing_garage(self):
        floor = self.layout["floors"][0]
        zones = floor["air_zones"]
        graph = access_graph(floor)
        clean_reached = reachable(graph, "stairs", zones["garage"] + zones["buffer"])
        self.assertTrue(set(zones["clean"]) <= clean_reached)
        self.assertFalse(set(zones["garage"]) & reachable(graph, "stairs", zones["buffer"]))

    def test_direct_garage_door_cannot_bypass_airlock(self):
        self.layout["floors"][0]["openings"].append({
            "axis": "x", "at": 49.25, "start": 39, "width": 3,
            "connects": ["clean_lobby", "two_wheelers"], "self_closing": True,
        })
        self.assertTrue(any("bypasses" in error for error in self.errors()))

    def test_airlock_needs_both_self_closing_doors(self):
        door = next(o for o in self.layout["floors"][0]["openings"] if o.get("id") == "airlock_garage_door")
        door["self_closing"] = False
        self.assertTrue(any("two self-closing" in error for error in self.errors()))

    def test_garage_partition_cannot_be_only_a_low_wall(self):
        self.layout["floors"][0]["partitions"][0]["intended_height"] = 3
        self.assertTrue(any("full-height" in error for error in self.errors()))

    def test_removing_partition_does_not_leave_fake_clean_adjacency(self):
        floor = self.layout["floors"][0]
        self.assertTrue(full_height_garage_barrier(floor, self.layout["wall_thickness"]))
        floor["partitions"] = []
        self.assertFalse(full_height_garage_barrier(floor, self.layout["wall_thickness"]))
        self.assertTrue(any("full-height" in error for error in self.errors()))

    def test_core_return_is_part_of_continuous_garage_separation(self):
        self.layout["floors"][0]["partitions"].pop(1)
        self.assertTrue(any("continuous intended full-height" in error for error in self.errors()))

    def test_openings_must_actually_meet_their_named_rooms(self):
        self.layout["floors"][0]["openings"][0]["connects"] = ["gym", "clean_lobby"]
        self.assertTrue(any("does not touch" in error for error in self.errors()))

    def test_kitchen_faces_backyard_and_pantry_is_directly_adjacent(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        kitchen = rooms["kitchen"]["rect"]
        self.assertEqual(kitchen[1] + kitchen[3], 73.5)
        self.assertIn("pantry", access_graph(floor)["kitchen"])
        self.assertTrue(any(o.get("kind") == "window" and o.get("operable") and "kitchen" in o["connects"] and o["at"] == 73.75 for o in floor["openings"]))
        self.assertTrue(any(item.get("appliance") == "cooktop_with_hood" for item in floor["furniture"]))

    def test_living_reports_net_area_without_double_counting_pantry_or_cupboard(self):
        floor = self.layout["floors"][1]
        kitchen = next(r for r in floor["rooms"] if r["id"] == "kitchen")
        living = next(r for r in floor["rooms"] if r["id"] == "family_living")
        pantry = next(r for r in floor["rooms"] if r["id"] == "pantry")
        self.assertEqual(room_area(floor, kitchen), 203.25)
        self.assertAlmostEqual(room_area(floor, living), 467.85)
        self.assertEqual(room_area(floor, pantry), 60)
        self.assertEqual(pantry["parent"], "kitchen")
        parts = room_footprints(floor, living)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(overlap(part, pantry["rect"]) == 0 for part in parts))

    def test_living_furniture_cannot_be_inside_the_enclosed_pantry(self):
        floor = self.layout["floors"][1]
        item = next(i for i in floor["furniture"] if i["id"] == "kitchen_fridge")
        item["rect"] = next(r["rect"].copy() for r in floor["rooms"] if r["id"] == "pantry")
        self.assertTrue(any("excluded child" in error for error in self.errors()))

    def test_dedicated_pantry_is_a_walled_room_with_a_door_and_the_fridge_stays_outside(self):
        floor = self.layout["floors"][1]
        items = {i["id"]: i for i in floor["furniture"]}
        pantry = next(r for r in floor["rooms"] if r["id"] == "pantry")
        door = next(o for o in floor["openings"] if o.get("id") == "pantry_door")
        self.assertFalse(pantry.get("open"))
        self.assertEqual(set(door["connects"]), {"pantry", "kitchen"})
        self.assertIn("kitchen", access_graph(floor)["pantry"])
        self.assertTrue(any(w["axis"] == "y" and w["at"] == 47.25 for w in walls(floor, self.layout["wall_thickness"])))
        self.assertEqual(pantry["rect"][2:], [6, 10])
        self.assertGreaterEqual(pantry["rect"][1], next(r["rect"][1] for r in floor["rooms"] if r["id"] == "kitchen"))
        self.assertEqual(items["kitchen_fridge"]["room"], "kitchen")
        self.assertEqual({i["room"] for i in items.values() if i["id"].startswith("pantry_shelves")}, {"pantry"})
        pantry["open"] = True
        self.assertTrue(any("dedicated enclosed walk-in pantry" in error for error in self.errors()))

    def test_refrigerator_is_outside_the_pantry_and_not_in_a_corner(self):
        floor = self.layout["floors"][1]
        kitchen = next(r["rect"] for r in floor["rooms"] if r["id"] == "kitchen")
        fridge = next(i for i in floor["furniture"] if i["id"] == "kitchen_fridge")
        self.assertGreaterEqual(fridge["rect"][1] - kitchen[1], 8)
        self.assertGreaterEqual(kitchen[1] + kitchen[3] - fridge["rect"][1] - fridge["rect"][3], 5)
        fridge["rect"] = [kitchen[0] + kitchen[2] - 2.5, kitchen[1] + kitchen[3] - 3, 2.5, 3]
        self.assertTrue(any("not in a kitchen corner" in e for e in self.errors()))

    def test_restored_dining_keeps_eight_chairs_and_table_clearances(self):
        floor = self.layout["floors"][1]
        room = next(r["rect"] for r in floor["rooms"] if r["id"] == "dining")
        table = next(i["rect"] for i in floor["furniture"] if i["id"] == "dining_table")
        chairs = dining_chairs(table)
        self.assertEqual(len(chairs), 8)
        self.assertTrue(all(contains(room, chair) for chair in chairs))
        self.assertGreaterEqual(min(table[0] - room[0], table[1] - room[1],
                                    room[0] + room[2] - table[0] - table[2],
                                    room[1] + room[3] - table[1] - table[3]), 2)
        cupboard = next(r["rect"] for r in floor["rooms"] if r["id"] == "utility_store")
        self.assertTrue(all(overlap(chair, cupboard) == 0 for chair in chairs))

    def test_dining_chairs_cannot_silently_overhang_room(self):
        item = next(i for i in self.layout["floors"][1]["furniture"] if i["id"] == "dining_table")
        item["rect"][1] = 41.5
        self.assertTrue(any("eight dining chairs" in error for error in self.errors()))

    def test_nonfinite_units(self):
        for value in [float("nan"), float("inf"), True, "10", None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                feet(value)

    def test_all_children_get_equal_spacious_rooms_with_the_front_rear_lounge_split(self):
        floor = self.layout["floors"][2]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertEqual(floor["envelope"], [4, 24, 50, 50])
        for i in range(1, 4):
            bedroom = rooms[f"child_bedroom_{i}"]
            self.assertEqual(bedroom["rect"][2:], [16, 17])
            self.assertEqual(room_area(floor, bedroom), 272)
        self.assertEqual(rooms["office"]["rect"], [27.5, 24.5, 12, 17])
        self.assertEqual(rooms["core_lobby"]["rect"][2], 4)
        self.assertEqual(rooms["upstairs_lounge"]["rect"], [4.5, 42, 49, 14])
        self.assertLess(rooms["child_bedroom_1"]["rect"][1], rooms["upstairs_lounge"]["rect"][1])
        self.assertGreater(rooms["child_bedroom_2"]["rect"][1], rooms["upstairs_lounge"]["rect"][1])
        self.assertGreater(rooms["child_bedroom_3"]["rect"][1], rooms["upstairs_lounge"]["rect"][1])
        door = next(o for o in floor["openings"] if set(o["connects"]) == {"child_bedroom_3", "upstairs_lounge"})
        self.assertTrue(all(opening_touches(rooms[rid], door, .5) for rid in door["connects"]))

    def test_each_private_bath_and_dressing_connect_without_using_bedroom(self):
        floor = self.layout["floors"][2]
        graph = access_graph(floor)
        for i in range(1, 4):
            bed, bath, wardrobe = (f"child_{kind}_{i}" for kind in ["bedroom", "bathroom", "wardrobe"])
            self.assertEqual(graph[wardrobe], {bed, bath})
            self.assertEqual(graph[bath], {wardrobe})
            self.assertIn(wardrobe, reachable(graph, bath, {bed, "outside"}))

    def test_removing_bath_dressing_connection_is_rejected(self):
        floor = self.layout["floors"][2]
        floor["openings"] = [o for o in floor["openings"] if o.get("id") != "child2_bath_dressing"]
        self.assertTrue(any("directly interconnected" in e for e in self.errors()))

    def test_walk_in_storage_keeps_real_clear_aisles(self):
        floor = self.layout["floors"][2]
        rooms = {r["id"]: r["rect"] for r in floor["rooms"]}
        for i in range(1, 4):
            wardrobe = rooms[f"child_wardrobe_{i}"]
            shelf = next(item["rect"] for item in floor["furniture"] if item["id"] == f"child{i}_wardrobe")
            self.assertGreaterEqual(wardrobe[2] - shelf[2], 3.5)
        shelf = next(item for item in floor["furniture"] if item["id"] == "child3_wardrobe")
        shelf["rect"] = rooms["child_wardrobe_3"].copy()
        self.assertTrue(any("clear dressing aisle" in e for e in self.errors()))

    def test_dressing_entries_cannot_be_blocked_even_with_a_clear_aisle(self):
        original = copy.deepcopy(self.layout)
        for i in range(1, 4):
            with self.subTest(child=i):
                self.layout = copy.deepcopy(original)
                shelf = next(item for item in self.layout["floors"][2]["furniture"] if item["id"] == f"child{i}_wardrobe")
                wardrobe = next(r["rect"] for r in self.layout["floors"][2]["rooms"] if r["id"] == f"child_wardrobe_{i}")
                door = next(o for o in self.layout["floors"][2]["openings"]
                            if set(o["connects"]) == {f"child_bedroom_{i}", f"child_wardrobe_{i}"})
                self.assertEqual(door["axis"], "y")
                shelf["rect"] = [wardrobe[0] + (wardrobe[2] - 2 if door["at"] > wardrobe[0] else 0),
                                 wardrobe[1], 2, wardrobe[3]]
                errors = self.errors()
                self.assertFalse(any("clear dressing aisle" in error for error in errors))
                self.assertIn(f"child_wardrobe_{i}: bedroom doorway needs a furniture-free 3 ft inside approach", errors)

    def test_soft_divider_does_not_replace_enclosed_shower(self):
        floor = self.layout["floors"][2]
        self.assertEqual(sum(o.get("kind") == "soft_divider" for o in floor["openings"]), 3)
        shower = next(item for item in floor["furniture"] if item["id"] == "child3_shower")
        shower["enclosed"] = False
        self.assertTrue(any("enclosed shower" in e for e in self.errors()))

    def test_former_office_wc_is_indoors_common_and_eighth_toilet(self):
        floor = self.layout["floors"][2]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertEqual(access_graph(floor)["first_common_toilet"], {"upstairs_lounge"})
        self.assertTrue(contains(floor["envelope"], rooms["first_common_toilet"]["rect"]))
        self.assertNotIn("office_toilet", rooms)
        for balcony in self.layout["balconies"]:
            self.assertEqual(overlap(rooms["first_common_toilet"]["rect"], balcony["rect"]), 0)
        fixtures = [item for f in self.layout["floors"] for item in f["furniture"]]
        self.assertEqual(sum(item["kind"] in {"toilet", "wc_cubicle"} for item in fixtures), 8)

    def test_common_wc_cannot_open_into_private_office(self):
        self.layout["floors"][2]["openings"].append({
            "axis": "x", "at": 37.75, "start": 6, "width": 3,
            "connects": ["first_common_toilet", "office"],
        })
        self.assertTrue(any("doors must open only" in e for e in self.errors()))

    def test_restored_common_wc_retains_space_in_front_of_the_toilet(self):
        floor = self.layout["floors"][2]
        room = next(r["rect"] for r in floor["rooms"] if r["id"] == "first_common_toilet")
        toilet = next(i for i in floor["furniture"] if i["id"] == "first_common_wc")
        self.assertEqual(room[2:], [6, 5.5])
        self.assertEqual(toilet["back_edge"], "front")
        self.assertGreaterEqual(room[1] + room[3] - toilet["rect"][1] - toilet["rect"][3], 2)

    def test_rear_balcony_remains_reachable_without_private_suites(self):
        floor = self.layout["floors"][2]
        private = {r["id"] for r in floor["rooms"] if r["id"].startswith("child_")} | {"office", "outside"}
        self.assertIn("rear_gallery", reachable(access_graph(floor), "stairs", private))
        self.assertIn("first_common_toilet", reachable(access_graph(floor), "stairs", private))
        self.assertEqual(next(r for r in floor["rooms"] if r["id"] == "rear_gallery")["rect"][2], 4)

    def test_first_svg_shows_shared_balconies_and_soft_connections(self):
        svg = plan_svg(self.layout, self.layout["floors"][2])
        self.assertIn("Continuous shared", svg)
        self.assertIn("no dividers", svg)
        self.assertIn('stroke="#8c6699"', svg)

    def test_null_brief_dimensions_stay_unresolved(self):
        before = copy.deepcopy(self.spec)
        self.assertEqual(validate_brief(self.spec), [])
        self.errors()
        self.assertEqual(self.spec, before)
        self.assertIsNone(self.spec["site"]["width"])

    def test_invalid_specified_dimensions(self):
        self.spec["site"]["width"] = -1
        self.assertTrue(self.errors())

    def test_missing_brief_fields_returns_fail(self):
        report = validate({}, self.layout)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(report["errors"])

    def test_missing_floor_returns_fail(self):
        self.layout["floors"].pop()
        self.assertTrue(self.errors())

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicate.json"
            path.write_text('{"id": 1, "id": 2}')
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                load_json(path)

    def test_missing_bedroom(self):
        self.layout["floors"][1]["rooms"] = [r for r in self.layout["floors"][1]["rooms"] if r["id"] != "guest_bedroom"]
        self.assertTrue(any("missing required" in e for e in self.errors()))

    def test_duplicate_rooms(self):
        self.layout["floors"][1]["rooms"].append(copy.deepcopy(self.layout["floors"][1]["rooms"][0]))
        self.assertTrue(any("duplicate room" in e for e in self.errors()))

    def test_nonfinite_rectangle(self):
        self.layout["floors"][1]["rooms"][0]["rect"][2] = float("nan")
        self.assertTrue(any("rectangle" in e for e in self.errors()))

    def test_zero_rectangle(self):
        self.layout["floors"][1]["rooms"][0]["rect"][2] = 0
        self.assertTrue(self.errors())

    def test_out_of_bounds(self):
        self.layout["floors"][1]["rooms"][0]["rect"][0] = -10
        self.assertTrue(any("out-of-envelope" in e for e in self.errors()))

    def test_unintended_room_overlap(self):
        self.layout["floors"][1]["rooms"][2]["rect"] = [5, 21, 16, 16]
        self.assertTrue(any("unintended overlap" in e for e in self.errors()))

    def test_furniture_outside_room(self):
        self.layout["floors"][1]["furniture"][0]["rect"][0] = -10
        self.assertTrue(any("furniture outside" in e for e in self.errors()))

    def test_furniture_collision(self):
        self.layout["floors"][1]["furniture"][1]["rect"] = self.layout["floors"][1]["furniture"][0]["rect"].copy()
        self.assertTrue(any("furniture collision" in e for e in self.errors()))

    def test_bad_opening_host(self):
        self.layout["floors"][1]["openings"][0]["at"] = 1000
        self.assertTrue(any("host wall" in e for e in self.errors()))

    def test_oversized_opening(self):
        self.layout["floors"][1]["openings"][0]["width"] = 100
        self.assertTrue(any("host wall" in e for e in self.errors()))

    def test_disconnected_master(self):
        f = self.layout["floors"][1]
        f["openings"] = [o for o in f["openings"] if "master_bedroom" not in o["connects"]]
        self.assertTrue(any("disconnected" in e for e in self.errors()))

    def test_missing_flexible_office(self):
        f = self.layout["floors"][2]
        f["rooms"] = [r for r in f["rooms"] if r["id"] != "office"]
        self.assertTrue(any("Flexible space office" in e for e in self.errors()))

    def test_unequal_child_rooms(self):
        next(r for r in self.layout["floors"][2]["rooms"] if r["id"] == "child_bedroom_1")["rect"][2] = 13
        self.assertTrue(any("equal children's" in e for e in self.errors()))

    def test_stair_alignment(self):
        next(r for r in self.layout["floors"][2]["rooms"] if r["id"] == "stairs")["rect"][0] += 1
        self.assertTrue(any("Stair footprints" in e for e in self.errors()))

    def test_floor_alignment(self):
        self.layout["floors"][2]["elevation"] = 12
        self.assertTrue(any("Unaligned" in e for e in self.errors()))

    def test_ramp_meets_basement(self):
        self.layout["ramp"]["grade_stations"][-1][0] -= 1
        self.assertTrue(any("Ramp" in e for e in self.errors()))

    def test_missing_suv(self):
        self.layout["floors"][0]["furniture"] = [i for i in self.layout["floors"][0]["furniture"] if i["id"] != "suv_3"]
        self.assertTrue(any("SUV" in e for e in self.errors()))

    def test_single_master_toilet_is_still_required(self):
        f = self.layout["floors"][1]
        f["furniture"] = [item for item in f["furniture"] if item["id"] != "master_wc_1"]
        self.assertTrue(any("master_bathroom: missing" in e for e in self.errors()))

    def test_master_bath_and_dressing_are_trimmed_to_the_bedroom_length_and_retain_fixtures(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertNotIn("master_entry", rooms)
        bedroom, bath, dressing = rooms["master_bedroom"]["rect"], rooms["master_bathroom"]["rect"], rooms["master_wardrobe"]["rect"]
        self.assertEqual(bedroom, [4.5, 56.5, 17.2, 17])
        self.assertEqual((bath[0], dressing[0] + dressing[2]), (bedroom[0], bedroom[0] + bedroom[2]))
        self.assertAlmostEqual(dressing[0] - bath[0] - bath[2], self.layout["wall_thickness"])
        self.assertAlmostEqual(room_area(floor, rooms["master_bathroom"]), 78.2)
        self.assertAlmostEqual(room_area(floor, rooms["master_wardrobe"]), 71.25)
        fixtures = [item for item in floor["furniture"] if item["room"] == "master_bathroom"]
        self.assertCountEqual([item["kind"] for item in fixtures], ["wc_cubicle", "basin", "bathtub", "shower"])
        self.assertTrue(all(contains(bath, item["rect"]) for item in fixtures))
        dressing_door = next(o for o in floor["openings"] if set(o["connects"]) == {"master_bathroom", "master_wardrobe"})
        self.assertTrue(all(overlap(door_inside_approach(rooms[rid], dressing_door), i["rect"]) == 0
                            for rid in ["master_bathroom", "master_wardrobe"] for i in floor["furniture"]))
        shelves = sorted((i["rect"] for i in floor["furniture"] if i["room"] == "master_wardrobe"), key=lambda r: r[0])
        self.assertGreaterEqual(shelves[1][0] - shelves[0][0] - shelves[0][2], 3)
        self.assertTrue(all(s[1] + s[3] <= dressing[1] + dressing[3] for s in shelves))
        self.assertGreaterEqual(dressing[3], 5)

    def test_ground_front_wider_drawing_furnished_smaller_guest(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertEqual(rooms["receiving"]["rect"][2:], [18.5, 17])
        self.assertEqual(rooms["guest_bedroom"]["rect"][2:], [11.5, 17])
        self.assertLess(rooms["receiving"]["rect"][1], rooms["cross_passage"]["rect"][1])
        self.assertLess(rooms["guest_bedroom"]["rect"][1], rooms["cross_passage"]["rect"][1])
        self.assertGreater(rooms["master_bedroom"]["rect"][1], rooms["cross_passage"]["rect"][1])
        self.assertGreater(rooms["family_living"]["rect"][1], rooms["cross_passage"]["rect"][1])
        self.assertEqual(access_graph(floor)["family_toilet"], {"cross_passage"})
        self.assertNotIn("laundry", rooms)
        self.assertEqual(rooms["prayer_alcove"]["rect"], [47, 46.5, 6.5, 7])

    def test_lift_does_not_force_living_access_through_the_kitchen(self):
        floor = self.layout["floors"][1]
        self.assertIn("family_living", reachable(access_graph(floor), "lift", {"kitchen", "outside"}))
        approach = [39, 46.5, 6.5, 8]
        self.assertTrue(all(overlap(approach, item["rect"]) == 0 for item in floor["furniture"]))

    def test_family_garden_access_does_not_cross_master_or_prayer(self):
        floor = self.layout["floors"][1]
        graph = access_graph(floor)
        blocked = {"master_bedroom", "master_bathroom", "master_wardrobe", "prayer_alcove", "entrance_gallery"}
        self.assertIn("outside", reachable(graph, "family_living", blocked))
        door = next(o for o in floor["openings"] if o.get("id") == "family_garden_exit")
        approach = [door["start"], door["at"] - 3.25, door["width"], 3]
        self.assertTrue(all(overlap(approach, item["rect"]) == 0 for item in floor["furniture"]))

    def test_laundry_has_clean_access_without_crossing_food_store(self):
        floor = self.layout["floors"][0]
        graph = access_graph(floor)
        self.assertEqual(graph["laundry"], {"laundry_passage"})
        blocked = floor["air_zones"]["garage"] + floor["air_zones"]["buffer"] + ["food_storage", "general_storage"]
        self.assertIn("laundry", reachable(graph, "stairs", blocked))
        self.assertIn("lift", reachable(graph, "laundry", blocked))
        self.assertEqual(next(r for r in floor["rooms"] if r["id"] == "food_storage")["rect"], [19.75, 29, 14.75, 6])

    def test_recreation_equal_area_is_enforced(self):
        self.layout["floors"][0]["rooms"][0]["rect"][2] -= 1
        self.assertTrue(any("equal usable areas" in e for e in self.errors()))

    def test_child_two_entry_is_mirrored_near_ensuite(self):
        floor = self.layout["floors"][2]
        door = next(o for o in floor["openings"] if set(o["connects"]) == {"child_bedroom_2", "upstairs_lounge"})
        self.assertEqual((door["axis"], door["at"], door["start"], door["width"]), ("x", 56.25, 39, 3))
        rooms = {r["id"]: r["rect"] for r in floor["rooms"]}
        other = next(o for o in floor["openings"] if set(o["connects"]) == {"child_bedroom_3", "upstairs_lounge"})
        self.assertEqual(door["start"] - rooms["child_bedroom_2"][0], 1.5)
        self.assertEqual(sum(rooms["child_bedroom_3"][::2]) - other["start"] - other["width"], 1.5)

    def test_all_five_bedrooms_have_large_operable_outward_glazing(self):
        checked = 0
        for floor in self.layout["floors"]:
            for room in floor["rooms"]:
                if room["kind"] == "bedroom":
                    self.assertTrue(any(set(o["connects"]) == {room["id"], "outside"} and o.get("operable")
                                        and o["width"] >= 9 and o.get("height", 0) >= 7 for o in floor["openings"]))
                    checked += 1
        self.assertEqual(checked, 5)

    def test_non_operable_bedroom_glazing_is_rejected(self):
        for o in self.layout["floors"][1]["openings"]:
            if "guest_bedroom" in o["connects"]:
                o["operable"] = False
        self.assertTrue(any("large outward-facing operable bedroom glazing" in e for e in self.errors()))

    def test_four_aligned_lift_reserves_have_common_landing_access(self):
        rectangles = []
        for floor in self.layout["floors"]:
            lift = next(r for r in floor["rooms"] if r["kind"] == "lift")
            rectangles.append(lift["rect"])
            doors = [o for o in floor["openings"] if lift["id"] in o["connects"]]
            self.assertEqual(len(doors), 1)
            self.assertEqual(doors[0]["kind"], "lift_door")
            private = [r["id"] for r in floor["rooms"] if r["kind"] in {"bedroom", "bathroom", "office"}] + ["outside"]
            self.assertIn(lift["id"], reachable(access_graph(floor), "stairs", private))
        self.assertEqual(rectangles, [[46.5, 17, 7, 7]] * 4)

    def test_single_front_entry_serves_both_front_rooms_through_entrance_gallery(self):
        floor = self.layout["floors"][1]
        graph = access_graph(floor)
        front = [o for o in floor["openings"] if o["axis"] == "x" and o["at"] == floor["envelope"][1] + .25
                 and "outside" in o["connects"] and o.get("kind") != "window"]
        self.assertEqual(len(front), 1)
        self.assertEqual(set(front[0]["connects"]), {"entrance_gallery", "outside"})
        self.assertEqual(graph["receiving"], {"entrance_gallery"})
        self.assertEqual(graph["guest_bedroom"], {"entrance_gallery", "guest_bathroom"})
        self.assertIn("cross_passage", graph["entrance_gallery"])

    def test_direct_front_drawing_door_is_rejected(self):
        opening = next(o for o in self.layout["floors"][1]["openings"]
                       if "receiving" in o["connects"] and o["axis"] == "x" and o.get("kind") == "window")
        opening.pop("kind")
        opening.pop("sill")
        self.assertTrue(any("Exactly one front entrance" in error for error in self.errors()))

    def test_direct_guest_slider_cannot_be_another_front_entrance(self):
        opening = next(o for o in self.layout["floors"][1]["openings"] if set(o["connects"]) == {"guest_bedroom", "outside"})
        opening["kind"] = "slider"
        self.assertTrue(any("guest_bedroom: doors must open only" in error for error in self.errors()))

    def test_private_guest_ensuite_is_excluded_from_sleeping_area(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertEqual(access_graph(floor)["guest_bathroom"], {"guest_bedroom"})
        self.assertEqual(room_area(floor, rooms["guest_bedroom"]), 157)
        self.assertEqual(room_area(floor, rooms["guest_bathroom"]), 38.5)
        self.assertEqual(rooms["guest_bathroom"]["parent"], "guest_bedroom")
        door = next(o for o in floor["openings"] if "guest_bathroom" in o["connects"])
        self.assertTrue(opening_meets_room(floor, rooms["guest_bedroom"], door, .5))
        self.assertFalse(opening_touches(rooms["guest_bedroom"], door, .5))

    def test_nested_bathroom_cannot_claim_a_parent_door_on_its_exterior_edge(self):
        floor = self.layout["floors"][1]
        room = next(r for r in floor["rooms"] if r["id"] == "guest_bedroom")
        door = next(o for o in floor["openings"] if "guest_bathroom" in o["connects"])
        door["at"] = 44.25
        self.assertFalse(opening_meets_room(floor, room, door, .5))
        self.assertTrue(any("does not touch" in error for error in self.errors()))

    def test_guest_furniture_cannot_occupy_the_new_ensuite(self):
        bed = next(item for item in self.layout["floors"][1]["furniture"] if item["id"] == "guest_bed")
        bed["rect"] = next(r["rect"].copy() for r in self.layout["floors"][1]["rooms"] if r["id"] == "guest_bathroom")
        self.assertTrue(any("guest_bed: furniture inside excluded child" in error for error in self.errors()))

    def test_left_wc_and_recessed_utility_leave_the_wider_gallery_clear(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertEqual(rooms["cross_passage"]["rect"][3], 4)
        self.assertEqual(rooms["entrance_gallery"]["rect"][2], 4)
        self.assertEqual(rooms["family_toilet"]["rect"], [4.5, 42, 8, 5])
        self.assertEqual(access_graph(floor)["utility_store"], {"cross_passage"})
        cupboard = next(o for o in floor["openings"] if o.get("id") == "utility_cupboard")
        self.assertEqual(cupboard["kind"], "cupboard_doors")
        self.assertEqual(cupboard["operation"], "bypass_sliding_intent")
        self.assertEqual(rooms["utility_store"]["rect"][2:], [2, 4])
        self.assertNotIn("parent", rooms["utility_store"])
        self.assertEqual(overlap(rooms["utility_store"]["rect"], rooms["family_living"]["rect"]), 0)
        self.assertEqual(cupboard["axis"], "y")
        self.assertEqual(cupboard["at"], 51.25)
        self.assertEqual(room_area(floor, rooms["receiving"]), 314.5)
        self.assertEqual(overlap(rooms["utility_store"]["rect"], rooms["cross_passage"]["rect"]), 0)
        self.assertTrue(all(overlap(item["rect"], rooms["cross_passage"]["rect"]) == 0 for item in floor["furniture"]))

    def test_cupboard_cannot_project_into_the_gallery(self):
        room = next(r for r in self.layout["floors"][1]["rooms"] if r["id"] == "utility_store")
        room["rect"][0] = 49
        self.assertTrue(any("Utility cupboard must terminate" in error for error in self.errors()))

    def test_cupboard_cannot_take_back_living_floor(self):
        room = next(r for r in self.layout["floors"][1]["rooms"] if r["id"] == "utility_store")
        room.update(rect=[46.5, 42.5, 6, 2], parent="family_living", exclude_from_parent=True)
        self.assertTrue(any("Utility cupboard must terminate" in error for error in self.errors()))

    def test_smaller_common_wc_keeps_clear_doorway_and_toilet_front(self):
        floor = self.layout["floors"][2]
        basin = next(i for i in floor["furniture"] if i["id"] == "first_common_basin")
        basin["rect"][1] += 2
        self.assertTrue(any("common WC needs a furniture-free 3 ft inside doorway" in e for e in self.errors()))
        basin["rect"][1] -= 2
        wc = next(r for r in floor["rooms"] if r["id"] == "first_common_toilet")
        wc["rect"][3] = 4.5
        self.assertTrue(any("at least 2 ft frontal space" in e for e in self.errors()))

    def test_parent_furniture_clears_the_ensuite_wall_not_only_its_floor(self):
        floor = self.layout["floors"][1]
        bed = next(item for item in floor["furniture"] if item["id"] == "guest_bed")
        bath = next(room for room in floor["rooms"] if room["id"] == "guest_bathroom")
        bed["rect"] = [bath["rect"][0] + .5, bath["rect"][1] - 5.25, 4, 5]
        self.assertEqual(overlap(bed["rect"], bath["rect"]), 0)
        self.assertTrue(any("furniture overlaps excluded child-room wall allowance" in error
                            for error in self.errors()))

    def test_gallery_width_target_is_not_silently_reduced(self):
        room = next(r for r in self.layout["floors"][1]["rooms"] if r["id"] == "cross_passage")
        room["rect"][3] = 3
        self.assertTrue(any("requested 4 ft widths" in error for error in self.errors()))

    def test_shared_galleries_are_labelled_in_plans_and_models(self):
        for floor_id, ids in {"ground": ["entrance_gallery", "cross_passage", "lift_lobby"],
                              "first": ["core_lobby", "rear_gallery"],
                              "roof": ["lift_lobby"]}.items():
            floor = next(f for f in self.layout["floors"] if f["id"] == floor_id)
            for rid in ids:
                self.assertTrue(next(r for r in floor["rooms"] if r["id"] == rid)["label"])
        room = next(r for r in self.layout["floors"][1]["rooms"] if r["id"] == "cross_passage")
        room.pop("label")
        self.assertTrue(any("shared galleries and landings need visible room labels" in error for error in self.errors()))

    def test_master_opens_only_to_the_family_zone_and_never_to_the_house_gallery(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        graph = access_graph(floor)
        door = next(o for o in floor["openings"] if o.get("id") == "master_family_door")
        self.assertEqual((door["axis"], door["width"], set(door["connects"])), ("y", 3, {"master_bedroom", "family_living"}))
        self.assertTrue(opening_meets_room(floor, rooms["master_bedroom"], door, self.layout["wall_thickness"]))
        self.assertTrue(opening_meets_room(floor, rooms["family_living"], door, self.layout["wall_thickness"]))
        self.assertEqual(graph["master_bedroom"] - {"outside"}, {"family_living", "master_wardrobe"})
        self.assertEqual(graph["master_wardrobe"], {"master_bedroom", "master_bathroom"})
        self.assertEqual(graph["master_bathroom"], {"master_wardrobe"})
        self.assertNotIn("master_bedroom", graph["cross_passage"])
        self.assertNotIn("master_wardrobe", reachable(graph, "cross_passage", {"master_bedroom", "outside"}))
        self.assertIn("master_bedroom", reachable(graph, "family_living", {"cross_passage", "outside"}))
        for room_id in ["master_bedroom", "family_living"]:
            approach = door_inside_approach(rooms[room_id], door)
            self.assertTrue(contains(rooms[room_id]["rect"], approach))
            self.assertTrue(all(overlap(approach, i["rect"]) == 0 for i in floor["furniture"]))
        table = next(i["rect"] for i in floor["furniture"] if i["id"] == "dining_table")
        approach = door_inside_approach(rooms["family_living"], door)
        self.assertTrue(all(overlap(approach, chair) == 0 for chair in dining_chairs(table)))

    def test_master_bed_sits_on_the_west_wall_under_a_high_window_opposite_the_tv_wall(self):
        floor = self.layout["floors"][1]
        bed = next(i for i in floor["furniture"] if i["id"] == "master_bed")
        room = next(r for r in floor["rooms"] if r["id"] == "master_bedroom")["rect"]
        tv = next(i for i in floor["furniture"] if i["id"] == "family_tv")["rect"]
        self.assertEqual((bed["rect"][0], bed["back_edge"]), (room[0], "left"))
        self.assertLess(bed["rect"][0] + bed["rect"][2], tv[0])
        self.assertTrue(back_wall_is_solid(floor, bed, self.layout["wall_thickness"]))
        self.assertEqual(bed["rect"][1] + bed["rect"][3] / 2, room[1] + room[3] / 2)
        tables = [i for i in floor["furniture"] if i.get("bed_id") == "master_bed"]
        self.assertEqual(len(tables), 2)
        self.assertTrue(all(t["rect"][0] == room[0] and t["back_edge"] == "left" for t in tables))
        window = next(o for o in floor["openings"] if o.get("id") == "master_side_window")
        self.assertGreaterEqual(window["sill"], 4.5)
        self.assertTrue(window["start"] <= bed["rect"][1] and window["start"] + window["width"] >= bed["rect"][1] + bed["rect"][3])
        glazing = [o for o in floor["openings"] if o["connects"] == ["master_bedroom", "outside"]]
        self.assertTrue(any(o["axis"] == "x" and o["width"] >= 9 and o["height"] >= 7 for o in glazing))
    def test_daylight_revision_preserves_plot_room_sizes_and_unaffected_floor_data(self):
        prior = load_json(ROOT / "assets/models/study-012/layout-snapshot.json")
        daylight = load_json(ROOT / "assets/models/study-013/layout-snapshot.json")
        for key in ["site", "ramp", "outdoor", "balconies", "weather_protection", "structure"]:
            self.assertEqual(self.layout[key], prior[key], key)
        for before, floor in zip(prior["floors"], daylight["floors"]):
            if floor["id"] in {"basement", "roof"}:
                self.assertEqual(floor, before)
            self.assertEqual(floor["envelope"], before["envelope"])
            self.assertEqual((floor["elevation"], floor["rise"]), (before["elevation"], before["rise"]))
            old_rooms = {r["id"]: r for r in before["rooms"]}
            for room in floor["rooms"]:
                self.assertEqual(room["rect"][2:], old_rooms[room["id"]]["rect"][2:])
                self.assertAlmostEqual(room_area(floor, room), room_area(before, old_rooms[room["id"]]))

    def test_bathroom_windows_are_centred_small_and_double_high_sill_privacy_glazing(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        for rid, oid, dimensions in [("family_toilet", "ground_wc_window", (2, 2, 5, 1)),
                                     ("master_bathroom", "master_bath_window", (5, 4, 4.5, 2))]:
            opening = next(o for o in floor["openings"] if o.get("id") == oid)
            self.assertEqual((opening["width"], opening["height"], opening["sill"], opening["sections"]), dimensions)
            self.assertTrue(opening["privacy_glass"])
            self.assertTrue(opening["operable"])
            self.assertEqual(opening["kind"], "window")
            self.assertEqual(opening["start"] + opening["width"] / 2, rooms[rid]["rect"][1] + rooms[rid]["rect"][3] / 2)
            self.assertNotIn("outside", access_graph(floor)[rid])
            opening["privacy_glass"] = False
            self.assertTrue(any(f"{rid}: high-sill" in e for e in self.errors()))
            opening["privacy_glass"] = True

    def test_revision_reclaims_twenty_percent_of_master_and_preserves_other_floors(self):
        prior = load_json(ROOT / "assets/models/study-013/layout-snapshot.json")
        for key in ["site", "ramp", "outdoor", "balconies", "weather_protection", "structure"]:
            self.assertEqual(self.layout[key], prior[key], key)
        for before, floor in zip(prior["floors"], self.layout["floors"]):
            if floor["id"] != "ground":
                self.assertEqual(floor, before)
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        old = {r["id"]: r for r in prior["floors"][1]["rooms"]}
        self.assertAlmostEqual(room_area(floor, rooms["master_bedroom"]), 365.5 * .8)
        self.assertAlmostEqual(room_area(floor, rooms["family_living"]), 467.85)
        self.assertNotEqual(rooms["prayer_alcove"]["rect"], old["prayer_alcove"]["rect"])
        self.assertEqual(rooms["prayer_alcove"]["rect"], [47, 46.5, 6.5, 7])
        rooms["master_bedroom"]["rect"][2] += 1
        self.assertTrue(any("20% smaller" in e for e in self.errors()))

    def test_living_net_area_excludes_dining_and_kitchen_without_double_counting(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        for part in room_footprints(floor, rooms["family_living"]):
            for rid in ["master_wardrobe", "master_bedroom", "dining", "kitchen", "pantry"]:
                self.assertAlmostEqual(overlap(part, rooms[rid]["rect"]), 0)
        sofa = next(i for i in floor["furniture"] if i["id"] == "family_sofa")
        sofa["rect"] = [rooms["kitchen"]["rect"][0], 60, 3, 9]
        self.assertTrue(any("excluded child" in e for e in self.errors()))

    def test_kitchen_is_wide_but_still_longer_than_wide_with_workable_aisles(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        items = {i["id"]: i for i in floor["furniture"]}
        kitchen, pantry, dining = rooms["kitchen"]["rect"], rooms["pantry"]["rect"], rooms["dining"]["rect"]
        self.assertEqual(kitchen, [40, 54, 13.5, 19.5])
        self.assertGreater(kitchen[3], kitchen[2])
        self.assertEqual((kitchen[0] + kitchen[2], pantry[0] + pantry[2]), (53.5, 53.5))
        self.assertGreaterEqual(kitchen[0], dining[0] + dining[2])
        self.assertGreaterEqual(room_area(floor, rooms["kitchen"]), 168)
        island = items["island"]["rect"]
        self.assertGreaterEqual(items["kitchen_counter"]["rect"][1] - island[1] - island[3], 3.5)
        self.assertGreaterEqual(pantry[0] - island[0] - island[2], 3.5)
        self.assertEqual(items["cooking_counter"]["appliance"], "cooktop_with_hood")

    def test_wrap_around_windows_run_above_the_whole_rear_and_east_kitchen_counters(self):
        floor = self.layout["floors"][1]
        items = {i["id"]: i for i in floor["furniture"]}
        rear = next(o for o in floor["openings"] if o.get("id") == "kitchen_counter_window")
        east = next(o for o in floor["openings"] if o.get("id") == "kitchen_east_counter_window")
        hood, sink, corner = items["cooking_counter"]["rect"], items["kitchen_counter"]["rect"], items["kitchen_corner_counter"]["rect"]
        landing = items["fridge_landing_counter"]["rect"]
        self.assertEqual((rear["axis"], rear["at"], rear["width"], rear["sections"]), ("x", 73.75, 9, 3))
        self.assertEqual((east["axis"], east["at"], east["width"], east["sections"]), ("y", 53.75, 5, 2))
        self.assertTrue(rear["operable"] and east["operable"])
        self.assertGreaterEqual(rear["start"], hood[0] + hood[2])
        self.assertLessEqual(rear["start"], sink[0] + .5)
        self.assertGreaterEqual(rear["start"] + rear["width"], corner[0] + corner[2] - .5)
        self.assertLessEqual(east["start"], landing[1] + .5)
        self.assertGreaterEqual(east["start"] + east["width"], corner[1] + corner[3] - .5)
        for window in (rear, east):
            self.assertGreaterEqual(window["sill"], 3)
        rear["start"] -= 1
        self.assertTrue(any("wrap-around windows" in e for e in self.errors()))

    def test_high_sill_windows_dip_the_cut_wall_so_the_kitchen_windows_are_visible(self):
        floor = self.layout["floors"][1]
        section = self.layout["section_height"]
        shown = [{**o, "sill": min(o["sill"], section - .4)} if o.get("kind") == "window" and o.get("sill", 0) >= section - .4 else o
                 for o in floor["openings"]]
        rear = next(w for w in walls(floor, self.layout["wall_thickness"]) if w["axis"] == "x" and w["at"] == 73.75 and w["start"] <= 44.2 < w["end"])
        parts = wall_parts(rear, shown, section)
        self.assertIn((44.2, 53.2, 2.6), parts)

    def test_living_garden_slider_is_as_big_as_the_master_slider(self):
        floor = self.layout["floors"][1]
        living = next(o for o in floor["openings"] if o.get("id") == "family_garden_exit")
        master = next(o for o in floor["openings"] if o["connects"] == ["master_bedroom", "outside"] and o.get("kind") == "slider")
        self.assertEqual((living["width"], living["height"]), (master["width"], master["height"]))
        self.assertEqual((living["width"], living["height"]), (10, 8))
        living["width"] = 7
        self.assertTrue(any("as big as the master bedroom slider" in e for e in self.errors()))

    def test_dining_table_runs_parallel_to_the_gallery_wall_with_eight_seats(self):
        floor = self.layout["floors"][1]
        table = next(i["rect"] for i in floor["furniture"] if i["id"] == "dining_table")
        self.assertGreater(table[2], table[3])
        chairs = dining_chairs(table)
        self.assertEqual(len(chairs), 8)
        self.assertEqual(sum(1 for c in chairs if c[1] < table[1]), 3)
        self.assertEqual(sum(1 for c in chairs if c[1] > table[1] + table[3]), 3)
        self.assertEqual(sum(1 for c in chairs if c[0] < table[0]), 1)
        self.assertEqual(len(dining_chair_turns(table)), 8)
        self.assertEqual(len(dining_chair_turns([0, 0, 3.5, 7.5])), 8)
        self.assertEqual(dining_chairs([0, 0, 3.5, 7.5])[0], [-1.8, 0, 1.5, 1.5])

    def test_dining_keeps_eight_seats_on_the_privacy_wall_side_and_frees_the_living_room(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        items = {i["id"]: i for i in floor["furniture"]}
        chairs = dining_chairs(items["dining_table"]["rect"])
        self.assertEqual(len(chairs), 8)
        self.assertTrue(all(contains(rooms["dining"]["rect"], chair) for chair in chairs))
        self.assertLessEqual(rooms["dining"]["rect"][1] + rooms["dining"]["rect"][3], items["family_tv"]["rect"][1])
        self.assertTrue({"conversation_chair", "conversation_table", "garden_reading_chair"}.isdisjoint(items))
        door = next(o for o in floor["openings"] if o.get("id") == "master_family_door")
        self.assertTrue(all(overlap(door_inside_approach(rooms["family_living"], door), c) == 0 for c in chairs))
        stools = [i["rect"] for i in floor["furniture"] if i["kind"] == "stool"]
        self.assertTrue(all(overlap(stool, chair) == 0 for stool in stools for chair in chairs))

    def test_prayer_corner_is_rotated_into_the_north_east_corner_of_the_east_wall(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        items = {i["id"]: i for i in floor["furniture"]}
        living, prayer, shelf = rooms["family_living"]["rect"], rooms["prayer_alcove"]["rect"], items["prayer_shelf"]
        self.assertEqual(prayer, [47, 46.5, 6.5, 7])
        self.assertEqual((prayer[0] + prayer[2], prayer[1]), (living[0] + living[2], living[1]))
        self.assertEqual((shelf["back_edge"], shelf["rect"][0] + shelf["rect"][2]), ("right", living[0] + living[2]))
        window = next(o for o in floor["openings"] if o.get("id") == "living_side_window")
        self.assertEqual(window["start"] + window["width"] / 2, prayer[1] + prayer[3] / 2)
        self.assertGreaterEqual(window["sill"], 3.5)
        self.assertTrue(window["start"] <= shelf["rect"][1] and shelf["rect"][1] + shelf["rect"][3] <= window["start"] + window["width"])
        window["start"] = 52
        self.assertTrue(any("directly behind the prayer corner" in e for e in self.errors()))

    def test_garden_slider_is_left_of_the_kitchen_and_its_approach_is_clear(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        slider = next(o for o in floor["openings"] if o.get("id") == "family_garden_exit")
        self.assertLess(slider["start"] + slider["width"], rooms["kitchen"]["rect"][0])
        approach = door_inside_approach(rooms["family_living"], slider)
        self.assertTrue(all(overlap(approach, i["rect"]) == 0 for i in floor["furniture"]))

    def test_living_tv_is_on_the_west_wall_with_the_sofa_facing_it_from_a_proper_distance(self):
        floor = self.layout["floors"][1]
        items = {i["id"]: i for i in floor["furniture"]}
        rooms = {r["id"]: r for r in floor["rooms"]}
        living, tv, sofa = rooms["family_living"]["rect"], items["family_tv"], items["family_sofa"]
        self.assertTrue(tv["wooden_cabinet"])
        self.assertEqual((tv["back_edge"], tv["rect"][0]), ("left", living[0]))
        self.assertEqual(sofa["back_edge"], "right")
        self.assertGreaterEqual(sofa["rect"][0] - tv["rect"][0] - tv["rect"][2], 8)
        self.assertGreaterEqual(rooms["kitchen"]["rect"][0] - sofa["rect"][0] - sofa["rect"][2], 3)
        coffee = items["family_coffee_table"]["rect"]
        self.assertTrue(tv["rect"][0] + tv["rect"][2] < coffee[0] and coffee[0] + coffee[2] < sofa["rect"][0])
        door = next(o for o in floor["openings"] if o.get("id") == "master_family_door")
        self.assertLessEqual(door["start"] + door["width"], tv["rect"][1])
        sofa["rect"][0] = tv["rect"][0] + tv["rect"][2] + 5
        self.assertTrue(any("at least 8 ft away" in e for e in self.errors()))
        self.setUp()
        floor = self.layout["floors"][1]
        next(i for i in floor["furniture"] if i["id"] == "family_tv")["back_edge"] = "right"
        self.assertTrue(any("west-wall wooden cabinet" in e for e in self.errors()))

    def test_centred_master_sliding_window_and_bed_leave_both_doors_and_garden_access_clear(self):
        floor = self.layout["floors"][1]
        room = next(r for r in floor["rooms"] if r["id"] == "master_bedroom")
        opening = next(o for o in floor["openings"] if o.get("id") == "master_side_window")
        self.assertEqual((opening["start"], opening["width"], opening["height"], opening["sill"]), (60.5, 9, 3, 4.5))
        self.assertEqual(opening["operation"], "horizontal_sliding_intent")
        self.assertEqual(opening["start"] + opening["width"] / 2, room["rect"][1] + room["rect"][3] / 2)
        for door in floor["openings"]:
            if room["id"] in door["connects"] and door.get("kind") != "window":
                approach = door_inside_approach(room, door)
                self.assertTrue(contains(room["rect"], approach))
                self.assertTrue(all(overlap(approach, item["rect"]) == 0 for item in floor["furniture"]))
        opening["start"] += .5
        self.assertTrue(any("centred operable window" in e for e in self.errors()))

    def test_child_one_front_left_suite_has_a_side_window_and_keeps_private_connections(self):
        floor = self.layout["floors"][2]
        rooms = {r["id"]: r for r in floor["rooms"]}
        graph = access_graph(floor)
        self.assertEqual(rooms["child_bedroom_1"]["rect"], [4.5, 24.5, 16, 17])
        self.assertEqual(rooms["office"]["rect"], [27.5, 24.5, 12, 17])
        self.assertEqual(graph["child_wardrobe_1"], {"child_bedroom_1", "child_bathroom_1"})
        self.assertEqual(graph["child_bathroom_1"], {"child_wardrobe_1"})
        window = next(o for o in floor["openings"] if o.get("id") == "child1_side_window")
        self.assertEqual((window["at"], window["width"], window["height"]), (4.25, 9, 7))
        self.assertTrue(any(o["kind"] == "slider" and set(o["connects"]) == {"office", "outside"} for o in floor["openings"] if "kind" in o))
        self.assertFalse(any(o["axis"] == "y" and "office" in o["connects"] and "outside" in o["connects"] for o in floor["openings"]))
        self.assertTrue(back_wall_is_solid(floor, next(i for i in floor["furniture"] if i["id"] == "child1_bed"), .5))

    def test_lounge_has_large_sliding_windows_on_both_sides_without_cutting_into_shared_wc(self):
        floor = self.layout["floors"][2]
        rooms = {r["id"]: r for r in floor["rooms"]}
        west, east = (next(o for o in floor["openings"] if o.get("id") == oid) for oid in ["lounge_west_window", "lounge_east_window"])
        self.assertEqual((west["at"], west["width"], east["at"], east["width"]), (4.25, 9, 53.75, 8))
        for window in [west, east]:
            self.assertTrue(window["operable"])
            self.assertEqual(window["sections"], 3)
            self.assertEqual(window["operation"], "horizontal_sliding_intent")
        self.assertGreater(east["start"], rooms["first_common_toilet"]["rect"][1] + rooms["first_common_toilet"]["rect"][3])
        east["start"] = 46
        self.assertTrue(any("wholly beyond the common WC" in e for e in self.errors()))

    def test_small_bathroom_window_and_invalid_section_counts_are_not_silently_accepted(self):
        window = next(o for o in self.layout["floors"][1]["openings"] if o.get("id") == "ground_wc_window")
        window["width"] = 1
        self.assertTrue(any("at least 2 ft wide" in e for e in self.errors()))
        window["width"] = 2
        for count in [0, 5, 1.5, True]:
            window["sections"] = count
            self.assertTrue(any("glazing sections" in e for e in self.errors()))

    def test_exterior_window_without_a_room_reports_an_error_instead_of_crashing(self):
        window = next(o for o in self.layout["floors"][1]["openings"] if o.get("id") == "ground_wc_window")
        window["connects"] = ["outside", "outside"]
        self.assertTrue(any("missing room" in e for e in self.errors()))

    def test_removed_master_entry_or_gallery_door_is_rejected(self):
        floor = self.layout["floors"][1]
        floor["openings"].append({"axis": "x", "at": 42.25, "start": 17, "width": 3,
                                  "connects": ["master_wardrobe", "cross_passage"]})
        self.assertTrue(any("one 3 ft family-zone door" in e for e in self.errors()))

    def test_master_door_approach_and_bed_direction_cannot_be_blocked(self):
        floor = self.layout["floors"][1]
        floor["furniture"].append({"id": "blocking_chest", "room": "master_bedroom", "kind": "table", "rect": [19, 57, 2, 2]})
        self.assertTrue(any("furniture-free 3 ft approaches" in e for e in self.errors()))
        self.setUp()
        floor = self.layout["floors"][1]
        bed = next(i for i in floor["furniture"] if i["id"] == "master_bed")
        bed["rect"][0], bed["back_edge"] = 14.7, "right"
        for table in (i for i in floor["furniture"] if i.get("bed_id") == "master_bed"):
            table["rect"][0], table["back_edge"] = 19.95, "right"
        self.assertTrue(any("opposite the living-room TV wall" in e for e in self.errors()))

    def test_facade_tiles_each_outer_wall_and_hosts_every_exterior_opening(self):
        spec = self.layout["exterior"]
        for floor in self.layout["floors"][1:3]:
            openings = facade_openings(floor, self.layout)
            self.assertEqual(len(openings), 12 if floor["id"] == "ground" else 11, floor["id"])
            self.assertEqual(sum(1 for o in openings if o["kind"] == "door"), 1 if floor["id"] == "ground" else 0)
            pieces = facade_pieces(floor, self.layout, 0, 2 * spec["storey_height"])
            for name, edge in facade_edges(floor, self.layout["wall_thickness"]).items():
                length = edge["span"][1] - edge["span"][0]
                solid = sum((p["along"][1] - p["along"][0]) * (p["z"][1] - p["z"][0]) for p in pieces if p["edge"] == name)
                glazed = sum(o["width"] * (o["head"] - o["sill"]) for o in openings if o["edge"] == name)
                self.assertAlmostEqual(solid + glazed, length * 2 * spec["storey_height"], places=6)
                for piece in (p for p in pieces if p["edge"] == name):
                    self.assertGreater(piece["along"][1], piece["along"][0])
                    self.assertGreater(piece["z"][1], piece["z"][0])
        door = next(o for o in facade_openings(self.layout["floors"][1], self.layout) if o["kind"] == "door")
        self.assertEqual((door["id"], door["edge"], door["sill"], door["head"]), ("main_front_entrance", "front", 1.5, 9.0))

    def test_exterior_gates_columns_planting_and_views_are_valid_and_reported(self):
        report = validate(self.spec, self.layout)
        self.assertEqual(report["errors"], [])
        self.assertTrue(any("Presentation exterior facade" in check for check in report["checks"]))
        spec = self.layout["exterior"]
        self.assertEqual({g["id"] for g in spec["boundary"]["gaps"]}, {"pedestrian_gate", "driveway_gate"})
        self.assertEqual(len(spec["views"]), 9)
        self.assertGreaterEqual(sum(p["kind"] in {"tree", "conifer"} for p in spec["planting"]), 9)
        self.assertTrue({"tree", "conifer", "hedge", "flower_bed", "shrub"} <= {p["kind"] for p in spec["planting"]})

    def test_exterior_rejects_blocked_paths_gates_planting_and_cameras(self):
        spec = self.layout["exterior"]
        spec["boundary"]["gaps"][0]["start"] = 24
        self.assertTrue(any("clear the whole entry path" in e for e in self.errors()))
        self.setUp()
        spec = self.layout["exterior"]
        spec["boundary"]["gaps"][1]["end"] = 60
        self.assertTrue(any("full straight lane" in e for e in self.errors()))
        self.setUp()
        spec = self.layout["exterior"]
        spec["planting"].append({"id": "bad_tree", "kind": "tree", "at": [30, 40], "height": 12, "canopy": 8})
        self.assertTrue(any("bad_tree: planting overlaps the house" in e for e in self.errors()))
        self.setUp()
        spec = self.layout["exterior"]
        spec["planting"].append({"id": "path_shrub", "kind": "shrub", "at": [25, 8], "radius": 1.5, "height": 2})
        self.assertTrue(any("path_shrub: planting blocks the entry path" in e for e in self.errors()))
        self.setUp()
        spec = self.layout["exterior"]
        spec["planting"].append({"id": "lane_tree", "kind": "tree", "at": [58, 20], "height": 10, "canopy": 6})
        self.assertTrue(any("lane_tree: planting overlaps driveway pavement" in e for e in self.errors()))
        self.setUp()
        spec = self.layout["exterior"]
        spec["views"][0]["position"] = [30, 40, 10]
        self.assertTrue(any("below ground or inside the house" in e for e in self.errors()))
        self.setUp()
        spec = self.layout["exterior"]
        spec["columns"][3]["rect"][0] = 24
        self.assertTrue(any("clear the entry path" in e for e in self.errors()))
        self.setUp()
        del self.layout["exterior"]
        self.assertTrue(any("exterior presentation block" in e for e in self.errors()))

    def test_exterior_opening_heights_stay_below_the_roof_edge_fascia(self):
        spec = self.layout["exterior"]
        ground = self.layout["floors"][1]
        window = next(o for o in ground["openings"] if o.get("kind") == "slider" and o["width"] == 10)
        window["height"] = 11
        self.assertTrue(any("between floor level and the roof-edge fascia" in e for e in self.errors()))
        self.assertGreater(spec["storey_height"], 0)

    def test_unified_lounge_reclaims_front_suites_and_west_wc(self):
        floor = self.layout["floors"][2]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertNotIn("front_landing", rooms)
        self.assertNotIn("east_gallery", rooms)
        self.assertEqual(room_area(floor, rooms["upstairs_lounge"]), 653)
        self.assertEqual(rooms["office"]["rect"][2:], [12, 17])
        for rid in ["child_bathroom_1", "child_wardrobe_1"]:
            self.assertLessEqual(rooms[rid]["rect"][1] + rooms[rid]["rect"][3], 41.5)
            self.assertEqual(overlap(rooms[rid]["rect"], rooms["upstairs_lounge"]["rect"]), 0)
        self.assertGreaterEqual(rooms["first_common_toilet"]["rect"][0], rooms["stairs"]["rect"][0])
        self.assertTrue(all(i["rect"][0] >= 45.5 for i in floor["furniture"] if i["room"] == "first_common_toilet"))
        rooms["child_wardrobe_1"]["rect"][1] = rooms["upstairs_lounge"]["rect"][1]
        self.assertTrue(any("outside the family lounge" in e for e in self.errors()))

    def test_gallery_refinement_preserves_basement_roof_after_site_translation(self):
        prior = load_json(ROOT / "assets/models/study-008/layout-snapshot.json")
        for fid in ["basement", "roof"]:
            self.assertEqual(next(f for f in self.layout["floors"] if f["id"] == fid),
                             translated_floor(next(f for f in prior["floors"] if f["id"] == fid), 4))
        self.assertEqual(self.layout["weather_protection"], prior["weather_protection"])

    def test_aligned_stair_profile_retains_full_landings_and_tread_targets(self):
        for floor in self.layout["floors"]:
            profile = stair_profile(floor)
            self.assertEqual(profile["rect"], [44.5, 24.5, 9, 17])
            self.assertEqual(profile["flight_width"], 4)
            self.assertEqual(profile["landing_depth"], 4)
            self.assertEqual(profile["going"], 1)
            self.assertEqual(profile["risers_per_flight"], 10)
            self.assertEqual(profile["riser_height"] * 20, floor["rise"])
            self.assertTrue(contains(profile["opening"], profile["turn"]))
            self.assertEqual(overlap(profile["opening"], profile["landing"]), 0)

    def test_stair_doors_meet_landings_instead_of_flights(self):
        for floor in self.layout["floors"]:
            profile = stair_profile(floor)
            for door in floor["openings"]:
                if "stairs" in door["connects"]:
                    self.assertTrue(opening_touches({"rect": profile["landing"]}, door, .5))

    def test_short_stair_reserve_is_rejected_instead_of_steepened(self):
        for floor in self.layout["floors"]:
            next(r for r in floor["rooms"] if r["id"] == "stairs")["rect"][3] = 16
        self.assertTrue(any("at least 12 in goings" in error for error in self.errors()))

    def test_invalid_stair_profile_fails_explicitly(self):
        floor = self.layout["floors"][1]
        next(r for r in floor["rooms"] if r["id"] == "stairs")["rect"][3] = 7
        with self.assertRaisesRegex(ValueError, "two flights"):
            stair_profile(floor)

    def test_spacious_alignment_preserves_and_enlarges_current_basement_functions(self):
        baseline = load_json(ROOT / "assets/models/study-007/layout-snapshot.json")
        floor = self.layout["floors"][0]
        rooms = {r["id"]: r for r in floor["rooms"]}
        old = {r["id"]: r for r in baseline["floors"][0]["rooms"]}
        for rid in ["food_storage", "laundry", "general_storage"]:
            self.assertGreater(room_area(floor, rooms[rid]), room_area(baseline["floors"][0], old[rid]))
        self.assertGreater(room_area(floor, rooms["gym"]), room_area(baseline["floors"][0], old["gym"]))
        self.assertAlmostEqual(room_area(floor, rooms["gym"]), room_area(floor, rooms["tech_cave"]))
        self.assertEqual(next(o for o in floor["openings"] if o.get("id") == "airlock_clean_door")["connects"],
                         ["clean_lobby", "garage_airlock"])

    def test_spacious_restoration_recovers_old_room_pattern_and_larger_gardens(self):
        baseline = load_json(ROOT / "assets/models/study-005/layout-snapshot.json")
        compact = load_json(ROOT / "assets/models/study-007/layout-snapshot.json")
        for fid, ids in {"ground": ["receiving"],
                         "first": [f"child_bedroom_{i}" for i in range(1, 4)]}.items():
            floor = next(f for f in self.layout["floors"] if f["id"] == fid)
            old = next(f for f in baseline["floors"] if f["id"] == fid)
            for rid in ids:
                self.assertGreaterEqual(room_area(floor, next(r for r in floor["rooms"] if r["id"] == rid)),
                                        room_area(old, next(r for r in old["rooms"] if r["id"] == rid)))
        for rid in ["front_lawn", "front_veranda", "back_veranda", "play_lawn"]:
            self.assertGreater(next(r["rect"][2] * r["rect"][3] for r in self.layout["outdoor"] if r["id"] == rid),
                               next(r["rect"][2] * r["rect"][3] for r in compact["outdoor"] if r["id"] == rid))
        self.assertEqual(next(r["rect"][2:] for r in self.layout["outdoor"] if r["id"] == "pool"), [8, 16])
        self.assertFalse(any(r["id"] == "pool" for r in self.layout["deferred_outdoor"]))
        for floor, old in zip(self.layout["floors"][1:], baseline["floors"][1:]):
            self.assertEqual(floor["envelope"], [old["envelope"][0], old["envelope"][1] + 4, *old["envelope"][2:]])

    def test_restored_pool_cannot_silently_be_deferred_again(self):
        self.layout["outdoor"] = [r for r in self.layout["outdoor"] if r["id"] != "pool"]
        self.layout["deferred_outdoor"].append({"id": "pool", "status": "deferred_for_compact_site"})
        self.assertTrue(any("restored brief requires a modeled pool" in e for e in self.errors()))

    def test_pool_requires_its_enclosing_barrier(self):
        self.layout["outdoor"] = [r for r in self.layout["outdoor"] if r["id"] != "pool_barrier"]
        self.assertTrue(any("surrounding barrier" in e for e in self.errors()))

    def test_pool_cannot_sit_over_basement_headroom(self):
        next(r for r in self.layout["outdoor"] if r["id"] == "pool")["rect"][:2] = [45, 80]
        self.assertTrue(any("pool: pool and barrier must remain outside the basement" in e for e in self.errors()))

    def test_pool_enclosure_cannot_clip_the_driveway_or_vehicle_sweep(self):
        next(r for r in self.layout["outdoor"] if r["id"] == "pool_barrier")["rect"] = [54.5, 73, 13, 26.5]
        self.assertTrue(any("pool_barrier: pool and barrier must remain clear of driveway" in e for e in self.errors()))

    def test_invalid_design_vehicle_is_rejected_before_pool_sweep_sampling(self):
        self.layout["ramp"]["design_vehicle"]["height_m"] = 0
        report = validate(self.spec, self.layout)
        self.assertEqual(report["geometry_status"], "FAIL")
        self.assertTrue(report["errors"])
        self.assertIsNone(report["driveway"])

    def test_misaligned_lift_is_rejected(self):
        next(r for r in self.layout["floors"][2]["rooms"] if r["kind"] == "lift")["rect"][0] += .5
        self.assertTrue(any("Lift shaft footprints must align" in e for e in self.errors()))

    def test_site_cannot_exceed_the_explicit_user_study_allowance(self):
        self.layout["site"]["width"] = 83
        self.assertTrue(any("user-permitted study envelope" in e for e in self.errors()))

    def test_plot_area_cap_is_enforced_independently_of_dimension_caps(self):
        self.spec["site"]["user_allowed_study_cap_ft"] = {"width": 100, "depth": 100}
        self.layout["site"]["width"] = 71
        self.assertTrue(any("user-permitted plot area" in e for e in self.errors()))

    def test_external_side_link_cannot_return(self):
        self.layout["floors"][1]["rooms"].append({
            "id": "stair_link", "name": "Rejected external link", "kind": "circulation",
            "rect": [30, 16.5, 4, 4], "open": True, "label": True,
        })
        self.assertTrue(any("no external stair link" in e for e in self.errors()))

    def test_raised_ground_is_used_in_actual_driveway_headroom_check(self):
        report = validate(self.spec, self.layout)
        self.assertEqual([f["elevation"] for f in self.layout["floors"]], [-8.5, 1.5, 12.5, 23.5])
        self.assertEqual(report["driveway"]["overhead_assumptions"]["slab_under_ft"], 1)
        self.layout["floors"][1]["elevation"] = 0
        self.layout["floors"][0]["rise"] = 8.5
        self.assertTrue(self.errors())

    def test_lift_is_in_front_lawn_and_opens_to_a_front_full_floor_landing(self):
        for floor in self.layout["floors"]:
            rooms = {r["id"]: r for r in floor["rooms"]}
            profile = stair_profile(floor)
            self.assertEqual(profile["entry_edge"], "front")
            self.assertEqual(profile["landing"], [44.5, 24.5, 9, 4])
            self.assertLess(rooms["lift"]["rect"][1], floor["envelope"][1] if floor["id"] != "basement" else self.layout["site"]["front_depth"])
            self.assertNotIn("stair_link", rooms)
            gallery = (access_graph(floor)["stairs"] - {"lift"}).pop()
            self.assertTrue(contains(floor["envelope"], rooms[gallery]["rect"]))
            self.assertEqual(rooms[gallery]["kind"], "circulation")
            self.assertLessEqual(floor["envelope"][0] + floor["envelope"][2],
                                 self.layout["ramp"]["start"][0] - self.layout["ramp"]["clear_width_ft"] / 2)
            if floor["id"] != "basement":
                self.assertEqual(floor["annexes"], [{"id": "front_lawn_lift", "rect": [46, 16.5, 8, 7.5]}])

    def test_gaming_boundary_does_not_build_a_wall_through_the_front_shaft(self):
        floor = self.layout["floors"][0]
        next(r for r in floor["rooms"] if r["id"] == "tech_cave")["rect"][3] = 10
        self.assertFalse(any(w["axis"] == "x" and w["at"] == 13.25 and w["start"] < 50 < w["end"]
                             for w in walls(floor, .5)))
        self.assertEqual(next(r for r in floor["rooms"] if r["id"] == "lift")["boundary_cutout"], True)

    def test_side_glazing_cannot_be_replaced_by_only_front_windows(self):
        floor = self.layout["floors"][2]
        floor["openings"] = [o for o in floor["openings"] if not (o["axis"] == "y" and "child_bedroom_1" in o["connects"])]
        self.assertTrue(any("child_bedroom_1: operable side-wall glazing" in e for e in self.errors()))

    def test_bed_cannot_float_away_from_its_solid_headboard_wall(self):
        bed = next(i for i in self.layout["floors"][1]["furniture"] if i["id"] == "guest_bed")
        bed["rect"][0 if bed["back_edge"] in {"left", "right"} else 1] += .5
        self.assertTrue(any("headboard must meet a solid room wall" in e for e in self.errors()))

    def test_each_bed_requires_tables_on_both_sides(self):
        floor = self.layout["floors"][2]
        floor["furniture"] = [i for i in floor["furniture"] if i["id"] != "child2_bedside_2"]
        self.assertTrue(any("two bedside tables must flank" in e for e in self.errors()))

    def test_master_must_have_one_basin_and_a_wall_backed_wc(self):
        floor = self.layout["floors"][1]
        basin = next(i for i in floor["furniture"] if i["id"] == "master_basin")
        basin["kind"] = "double_basin"
        self.assertTrue(any("exactly one basin" in e for e in self.errors()))
        basin["kind"] = "basin"
        wc = next(i for i in floor["furniture"] if i["id"] == "master_wc_1")
        wc["rect"][1] += .5
        self.assertTrue(any("WC must back onto a real bathroom wall" in e for e in self.errors()))

    def test_refrigerator_cannot_return_into_the_pantry(self):
        fridge = next(i for i in self.layout["floors"][1]["furniture"] if i["id"] == "kitchen_fridge")
        fridge["room"], fridge["rect"] = "pantry", [49, 58.5, 2.5, 3]
        self.assertTrue(any("Refrigerator must be in the kitchen" in e for e in self.errors()))

    def test_horizontal_gallery_privacy_wall_is_restored_without_a_prayer_return(self):
        floor = self.layout["floors"][1]
        graph = access_graph(floor)
        self.assertEqual({p["id"] for p in floor["partitions"]}, {"public_dining_screen", "public_family_screen"})
        self.assertTrue(all(p["axis"] == "x" and p["role"] == "privacy_wall" and p["at"] == 46.25 for p in floor["partitions"]))
        self.assertTrue({"dining", "kitchen", "prayer_alcove"} <= graph["family_living"])
        self.assertTrue(partition_between(floor, *(next(r for r in floor["rooms"] if r["id"] == rid)
                                                    for rid in ["cross_passage", "family_living"])))
        floor["partitions"].append({"id": "prayer_return", "role": "privacy_wall", "axis": "y", "at": 46.25,
                                    "start": 46.25, "end": 50.75, "intended_height": 9.5})
        self.assertTrue(any("prayer corner stays open" in e for e in self.errors()))

    def test_removing_the_gallery_privacy_wall_is_rejected(self):
        floor = self.layout["floors"][1]
        floor["partitions"] = []
        self.assertTrue(any("horizontal privacy wall" in e for e in self.errors()))

    def test_privacy_wall_blocks_sampled_gallery_sightlines_into_the_family_zone(self):
        floor = self.layout["floors"][1]
        entry = next(o for o in floor["openings"] if o.get("id") == "family_entry")
        self.assertEqual((entry["kind"], entry["width"], entry["start"]), ("open_archway", 6.5, 39))
        items = {i["id"]: i["rect"] for i in floor["furniture"]}
        for observer in floor["privacy_observers"]:
            for key in ["family_sofa", "family_coffee_table", "island", "dining_table", "prayer_shelf"]:
                x, y, w, d = items[key]
                for corner in [[x, y], [x + w, y], [x, y + d], [x + w, y + d]]:
                    self.assertTrue(sightline_blocked(floor, observer, corner, self.layout["wall_thickness"]))

    def test_family_entry_approach_must_stay_clear_of_furniture(self):
        floor = self.layout["floors"][1]
        entry_start = next(o["start"] for o in floor["openings"] if o.get("id") == "family_entry")
        chair = next(i for i in floor["furniture"] if i["id"] == "family_coffee_table")
        chair["rect"] = [entry_start, 46.5, 3, 3]
        self.assertTrue(any("entry approach must remain free" in e for e in self.errors()))

    def test_garden_entry_path_is_aligned_with_the_only_front_door(self):
        path = next(r["rect"] for r in self.layout["outdoor"] if r["id"] == "entry_path")
        door = next(o for o in self.layout["floors"][1]["openings"] if o.get("id") == "main_front_entrance")
        self.assertEqual(path[0] + path[2] / 2, door["start"] + door["width"] / 2)
        self.assertGreaterEqual(path[2], door["width"])

    def test_structural_proxies_have_no_interior_living_or_garage_columns(self):
        for floor in self.layout["floors"]:
            members = structural_members(self.layout, floor)
            self.assertTrue(any(m["role"] == "beam_proxy" for m in members))
            protected = self.layout["structure"]["clear_span_rooms"].get(floor["id"], [])
            rooms = [r for r in floor["rooms"] if r["id"] in protected]
            for member in members:
                self.assertTrue(contains(floor_bounds(floor), member["rect"]))
                if member["role"] == "column_proxy":
                    self.assertTrue(all(overlap(member["rect"], part) == 0 for room in rooms for part in room_footprints(floor, room)))

    def test_structural_view_must_not_claim_engineering_status(self):
        self.layout["structure"]["status"] = "approved"
        self.assertTrue(any("explicitly remain non-engineered" in e for e in self.errors()))

    def test_office_needs_separate_workstation_and_table(self):
        f = self.layout["floors"][2]
        f["furniture"] = [item for item in f["furniture"] if item["id"] != "office_shared_table"]
        self.assertTrue(any("office: missing required table" in e for e in self.errors()))

    def test_slab_opening_partition(self):
        base, hole = [0, 0, 20, 20], [5, 5, 5, 10]
        parts = subtract_rectangles(base, [hole])
        self.assertAlmostEqual(sum(r[2] * r[3] for r in parts), 350)
        for i, a in enumerate(parts):
            self.assertTrue(contains(base, a))
            self.assertEqual(overlap(a, hole), 0)
            for b in parts[i + 1:]:
                self.assertEqual(overlap(a, b), 0)

    def test_real_door_gap_and_window_sill(self):
        wall = {"axis": "x", "at": 0, "start": 0, "end": 10}
        parts = wall_parts(wall, [{"axis": "x", "at": 0, "start": 3, "width": 3}], 3)
        self.assertEqual(parts, [(0, 3, 3), (6, 10, 3)])
        parts = wall_parts(wall, [{"axis": "x", "at": 0, "start": 3, "width": 3, "sill": 2}], 3)
        self.assertIn((3, 6, 2), parts)

    def test_shared_walls_merged(self):
        f = {"envelope": [0, 0, 20, 10], "rooms": [
            {"rect": [0.5, 0.5, 9.25, 9], "id": "a"},
            {"rect": [10.25, 0.5, 9.25, 9], "id": "b"},
        ]}
        shared = [w for w in walls(f, 0.5) if w["axis"] == "y" and w["at"] == 10]
        self.assertEqual(len(shared), 1)

    def test_partial_privacy_return_preserves_only_a_real_three_foot_open_route(self):
        floor = {"rooms": [
            {"id": "a", "rect": [0, 0, 10, 10], "open": True},
            {"id": "b", "rect": [0, 10.5, 10, 10], "open": True},
        ], "openings": [], "partitions": [{"axis": "x", "at": 10.25, "start": 0, "end": 7}]}
        self.assertIn("b", access_graph(floor)["a"])
        floor["partitions"][0]["end"] = 7.1
        self.assertNotIn("b", access_graph(floor)["a"])

    def test_svg_wellformed_and_labeled(self):
        for f in [None, *self.layout["floors"]]:
            svg = plan_svg(self.layout, f)
            ET.fromstring(svg)
            self.assertIn("UNAPPROVED CONCEPT", svg)
            self.assertIn("70 x 116", svg)

    def test_outputs_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "study"
            write_review(self.spec, self.layout, output)
            self.assertEqual(len(list(output.glob("*.svg"))), 5)
            self.assertEqual(json.loads((output / "review-report.json").read_text())["status"], "NEEDS REVIEW")
            with self.assertRaises(FileExistsError):
                write_review(self.spec, self.layout, output)

    def test_invalid_layout_does_not_publish_outputs(self):
        self.layout["site"]["width"] = -1
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "study"
            with self.assertRaises(ValueError):
                write_review(self.spec, self.layout, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

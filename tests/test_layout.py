import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.layout import ROOT, access_graph, contains, dining_chairs, feet, load_json, overlap, plan_svg, reachable, room_area, room_footprints, square_feet, subtract_rectangles, validate, validate_brief, wall_parts, walls, write_review


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
        self.assertEqual(report["plot_area_sq_ft"], 7000)
        self.assertEqual(report["plot_expansion_above_initial_max_percent"], 40)
        self.assertEqual(report["front_yard_fraction"], 0.2)
        self.assertEqual(report["back_yard_fraction"], 0.3)

    def test_units(self):
        self.assertAlmostEqual(feet(10), 3.048)
        self.assertAlmostEqual(square_feet(100), 9.290304)

    def test_revised_basement_keeps_program_sizes_and_places_cars_by_ramp(self):
        floor = self.layout["floors"][0]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertEqual(floor["envelope"], [4, 4, 50, 88])
        self.assertEqual(rooms["gym"]["rect"][2:], [16, 15])
        self.assertEqual(rooms["tech_cave"]["rect"][2:], [32.5, 15])
        self.assertEqual(rooms["drive_aisle"]["rect"][3], 25.5)
        self.assertLess(rooms["gym"]["rect"][1], rooms["general_storage"]["rect"][1])
        self.assertGreaterEqual(rooms["vehicle_parking"]["rect"][1], 68)
        self.assertEqual(rooms["vehicle_parking"]["rect"][2:], [36, 19])

    def test_clean_basement_rooms_do_not_require_crossing_garage(self):
        floor = self.layout["floors"][0]
        zones = floor["air_zones"]
        graph = access_graph(floor)
        clean_reached = reachable(graph, "stairs", zones["garage"] + zones["buffer"])
        self.assertTrue(set(zones["clean"]) <= clean_reached)
        self.assertFalse(set(zones["garage"]) & reachable(graph, "stairs", zones["buffer"]))

    def test_direct_garage_door_cannot_bypass_airlock(self):
        self.layout["floors"][0]["openings"].append({
            "axis": "x", "at": 46.25, "start": 35, "width": 3,
            "connects": ["clean_lobby", "drive_aisle"], "self_closing": True,
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
        floor["partitions"] = []
        self.assertIn("drive_aisle", access_graph(floor)["clean_lobby"])
        self.assertTrue(any("full-height" in error for error in self.errors()))

    def test_openings_must_actually_meet_their_named_rooms(self):
        self.layout["floors"][0]["openings"][0]["connects"] = ["gym", "clean_lobby"]
        self.assertTrue(any("does not touch" in error for error in self.errors()))

    def test_kitchen_faces_backyard_and_pantry_is_directly_adjacent(self):
        floor = self.layout["floors"][1]
        rooms = {r["id"]: r for r in floor["rooms"]}
        kitchen = rooms["kitchen"]["rect"]
        self.assertEqual(kitchen[1] + kitchen[3], 69.5)
        self.assertIn("pantry", access_graph(floor)["kitchen"])
        self.assertTrue(any(o.get("kind") == "window" and "kitchen" in o["connects"] and o["at"] == 69.75 for o in floor["openings"]))
        self.assertTrue(any(item.get("appliance") == "cooktop_with_hood" for item in floor["furniture"]))

    def test_l_shaped_living_reports_net_area_without_double_counting_pantry(self):
        floor = self.layout["floors"][1]
        living = next(r for r in floor["rooms"] if r["id"] == "family_living")
        pantry = next(r for r in floor["rooms"] if r["id"] == "pantry")
        self.assertEqual(room_area(floor, living), 281.75)
        self.assertGreater(room_area(floor, living) / 209.25, 1.34)
        parts = room_footprints(floor, living)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(overlap(part, pantry["rect"]) == 0 for part in parts))

    def test_living_furniture_cannot_be_inside_the_enclosed_pantry(self):
        item = next(i for i in self.layout["floors"][1]["furniture"] if i["id"] == "family_coffee_table")
        item["rect"] = [40, 65, 2, 2]
        self.assertTrue(any("excluded child" in error for error in self.errors()))

    def test_enclosed_pantry_needs_its_real_door_not_parent_adjacency(self):
        floor = self.layout["floors"][1]
        floor["openings"] = [o for o in floor["openings"] if "pantry" not in o["connects"]]
        self.assertTrue(any("disconnected" in error for error in self.errors()))

    def test_compact_dining_keeps_eight_chairs_and_table_clearances(self):
        floor = self.layout["floors"][1]
        room = next(r["rect"] for r in floor["rooms"] if r["id"] == "dining")
        table = next(i["rect"] for i in floor["furniture"] if i["id"] == "dining_table")
        chairs = dining_chairs(table)
        self.assertEqual(len(chairs), 8)
        self.assertTrue(all(contains(room, chair) for chair in chairs))
        self.assertGreaterEqual(min(table[0] - room[0], table[1] - room[1],
                                    room[0] + room[2] - table[0] - table[2],
                                    room[1] + room[3] - table[1] - table[3]), 3)

    def test_dining_chairs_cannot_silently_overhang_room(self):
        item = next(i for i in self.layout["floors"][1]["furniture"] if i["id"] == "dining_table")
        item["rect"][1] = 41.5
        self.assertTrue(any("eight dining chairs" in error for error in self.errors()))

    def test_nonfinite_units(self):
        for value in [float("nan"), float("inf"), True, "10", None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                feet(value)

    def test_all_children_get_larger_equal_sleeping_rooms_and_office_swap(self):
        floor = self.layout["floors"][2]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertEqual(floor["envelope"], [4, 20, 50, 50])
        for i in range(1, 4):
            bedroom = rooms[f"child_bedroom_{i}"]
            self.assertEqual(bedroom["rect"][2:], [16, 17])
            self.assertEqual(room_area(floor, bedroom), 272)
            self.assertGreater(room_area(floor, bedroom), 256)
        self.assertEqual(rooms["office"]["rect"], [28, 20.5, 16, 16])
        self.assertEqual(rooms["child_bedroom_2"]["rect"][:2], [37.5, 52.5])

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
        shelf["rect"] = [21, 63, 5.5, 6]
        self.assertTrue(any("clear dressing aisle" in e for e in self.errors()))

    def test_soft_divider_does_not_replace_enclosed_shower(self):
        floor = self.layout["floors"][2]
        self.assertEqual(sum(o.get("kind") == "soft_divider" for o in floor["openings"]), 3)
        shower = next(item for item in floor["furniture"] if item["id"] == "child3_shower")
        shower["enclosed"] = False
        self.assertTrue(any("enclosed shower" in e for e in self.errors()))

    def test_office_wc_is_indoors_private_and_ninth_toilet(self):
        floor = self.layout["floors"][2]
        rooms = {r["id"]: r for r in floor["rooms"]}
        self.assertEqual(access_graph(floor)["office_toilet"], {"office"})
        self.assertTrue(contains(floor["envelope"], rooms["office_toilet"]["rect"]))
        for balcony in self.layout["balconies"]:
            self.assertEqual(overlap(rooms["office_toilet"]["rect"], balcony["rect"]), 0)
        fixtures = [item for f in self.layout["floors"] for item in f["furniture"]]
        self.assertEqual(sum(item["kind"] in {"toilet", "wc_cubicle"} for item in fixtures), 9)

    def test_office_wc_cannot_open_into_seamless_lounge(self):
        self.layout["floors"][2]["openings"].append({
            "axis": "x", "at": 42.25, "start": 30, "width": 3,
            "connects": ["office_toilet", "upstairs_lounge"],
        })
        self.assertTrue(any("office-only access" in e for e in self.errors()))

    def test_rear_balcony_remains_reachable_without_private_suites(self):
        floor = self.layout["floors"][2]
        private = {r["id"] for r in floor["rooms"] if r["id"].startswith("child_")} | {"office", "office_toilet", "outside"}
        self.assertIn("rear_gallery", reachable(access_graph(floor), "stairs", private))
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
        self.layout["floors"][2]["rooms"][0]["rect"][2] = 15
        self.assertTrue(any("equal children's" in e for e in self.errors()))

    def test_stair_alignment(self):
        self.layout["floors"][2]["rooms"][3]["rect"][0] += 1
        self.assertTrue(any("Stair footprints" in e for e in self.errors()))

    def test_floor_alignment(self):
        self.layout["floors"][2]["elevation"] = 12
        self.assertTrue(any("Unaligned" in e for e in self.errors()))

    def test_ramp_meets_basement(self):
        self.layout["ramp"]["profile"][-1][1] = -9.5
        self.assertTrue(any("Ramp" in e for e in self.errors()))

    def test_missing_suv(self):
        self.layout["floors"][0]["furniture"] = [i for i in self.layout["floors"][0]["furniture"] if i["id"] != "suv_3"]
        self.assertTrue(any("SUV" in e for e in self.errors()))

    def test_two_master_toilets_are_required(self):
        f = self.layout["floors"][1]
        f["furniture"] = [item for item in f["furniture"] if item["id"] != "master_wc_2"]
        self.assertTrue(any("master_bathroom: missing" in e for e in self.errors()))

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

    def test_svg_wellformed_and_labeled(self):
        for f in [None, *self.layout["floors"]]:
            svg = plan_svg(self.layout, f)
            ET.fromstring(svg)
            self.assertIn("UNAPPROVED CONCEPT", svg)
            self.assertIn("70 x 100", svg)

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

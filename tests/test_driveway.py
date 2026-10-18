import copy
import math
import unittest

from scripts.driveway import Driveway, check_vehicle, point_in_polygon, polygons_overlap, rect_polygon, sweep_report


def candidate():
    return {
        "start": [68.5, 0], "straight_ft": 61, "radius_ft": 20, "exit_ft": 12,
        "clear_width_ft": 12, "bend_outer_ft": 9, "flare_ft": 10,
        "grade_stations": [[0, 0], [4, 0], [12, -.14], [53, -.14], [61, -.10], [84.4, -.10], [92.4, 0]],
        "basement_elevation_ft": -10,
        "design_vehicle": {
            "length_m": 5.25, "width_m": 2.25, "height_m": 2.2, "wheelbase_m": 3.15,
            "front_overhang_m": 1.05, "rear_overhang_m": 1.05, "clearance_m": .3,
            "ground_clearance_m": .2, "minimum_rear_radius_m": 5,
        },
    }


class DrivewayTests(unittest.TestCase):
    def report(self, spec=None, obstacles=None, portal=None):
        return sweep_report(spec or candidate(), [4.5, 67.5, 49, 24], obstacles or [],
                            [0, 0, 82, 108], portal or {"at": 53.75, "start": 73.5, "width": 17})

    def test_large_suv_body_and_overhang_fit_the_complete_curve(self):
        report = self.report()
        self.assertEqual(report["errors"], [])
        self.assertGreater(report["samples"], 200)
        self.assertEqual(report["body_clearance_m"], .3)

    def test_real_grade_easements_finish_exactly_at_basement_level(self):
        road = Driveway(candidate())
        self.assertAlmostEqual(road.elevation(road.length), -10)
        for station in [4, 12, 53, 61, 84.4, 92.4]:
            self.assertAlmostEqual(road.grade(station - .00001), road.grade(station + .00001), places=5)
        self.assertEqual(road.grade(road.length), 0)

    def test_vehicle_roof_and_underbody_clear_the_three_dimensional_profile(self):
        report = sweep_report(candidate(), [4.5, 67.5, 49, 24], [], [0, 0, 82, 108],
                              {"at": 53.75, "start": 73.5, "width": 17},
                              {"canopy_under_ft": 9, "basement_cover_rect": [4, 4, 50, 88],
                               "slab_under_ft": -.5, "finish_ft": .035})
        self.assertEqual(report["errors"], [])
        self.assertGreaterEqual(report["minimum_roof_clearance_m"], .3)
        self.assertGreaterEqual(report["minimum_underbody_clearance_m"], .1)

    def test_curve_is_tangent_to_both_straight_segments(self):
        road = Driveway(candidate())
        a, b = road.at(road.straight), road.at(road.arc_end)
        self.assertAlmostEqual(a.x, 68.5)
        self.assertAlmostEqual(a.y, 61)
        self.assertEqual((a.tx, a.ty), (0, 1))
        self.assertAlmostEqual(b.x, 48.5)
        self.assertAlmostEqual(b.y, 81)
        self.assertAlmostEqual(b.tx, -1)
        self.assertAlmostEqual(b.ty, 0)

    def test_bend_widens_instead_of_using_the_straight_lane_width(self):
        road = Driveway(candidate())
        self.assertEqual(road.at(0).outer, 6)
        self.assertEqual(road.at(road.straight).outer, 9)
        self.assertEqual(road.at(road.length).outer, 6)
        self.assertEqual(road.at(road.arc_end).inner, 6)

    def test_old_eight_foot_garage_opening_is_rejected(self):
        self.assertIn("Garage portal clips", " ".join(self.report(portal={"at": 53.75, "start": 78, "width": 8})["errors"]))

    def test_narrow_curve_cannot_hide_a_body_overhang_collision(self):
        spec = candidate()
        spec["bend_outer_ft"] = 6
        self.assertIn("body/overhang", " ".join(self.report(spec)["errors"]))

    def test_rear_axle_radius_is_not_confused_with_a_turning_diameter(self):
        spec = candidate()
        spec["design_vehicle"]["minimum_rear_radius_m"] = 7
        self.assertIn("rear-axle radius", " ".join(self.report(spec)["errors"]))

    def test_obstacle_on_the_turn_is_rejected(self):
        self.assertIn("hits parked furniture", " ".join(self.report(obstacles=[[60, 66, 5, 5]])["errors"]))

    def test_profile_cannot_be_steepened_to_force_a_fit(self):
        spec = candidate()
        spec["grade_stations"][2][1] = -.2
        self.assertIn("grade limits", " ".join(self.report(spec)["errors"]))

    def test_invalid_inputs_fail_explicitly(self):
        for key, value in [("radius_ft", 0), ("straight_ft", math.nan), ("exit_ft", True)]:
            with self.subTest(key=key):
                spec = candidate()
                spec[key] = value
                with self.assertRaises(ValueError):
                    Driveway(spec)
        with self.assertRaises(ValueError):
            Driveway(candidate()).at(-1)

    def test_vehicle_dimensions_must_be_internally_consistent(self):
        vehicle = copy.deepcopy(candidate()["design_vehicle"])
        vehicle["length_m"] = 4
        with self.assertRaisesRegex(ValueError, "add up"):
            check_vehicle(vehicle)

    def test_polygon_checks_include_boundaries_and_real_intersections(self):
        a = rect_polygon([0, 0, 2, 2])
        self.assertTrue(point_in_polygon((0, 1), a))
        self.assertFalse(point_in_polygon((3, 1), a))
        self.assertTrue(polygons_overlap(a, rect_polygon([1, 1, 2, 2])))
        self.assertFalse(polygons_overlap(a, rect_polygon([2, 0, 2, 2])))


if __name__ == "__main__":
    unittest.main()

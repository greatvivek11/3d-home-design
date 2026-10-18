import math
import unittest
from types import SimpleNamespace

from blender.create_tour import (
    DISSOLVE_FRAMES, FPS, SHOT_FRAMES, SHOTS, TOTAL_FRAMES, camera_pose, configure_renderer,
)


class TourTests(unittest.TestCase):
    def test_duration_and_dissolves(self):
        self.assertEqual(len(SHOTS), 3)
        self.assertEqual(3 * SHOT_FRAMES - 2 * DISSOLVE_FRAMES, TOTAL_FRAMES)
        self.assertEqual(TOTAL_FRAMES / FPS, 12)
        self.assertGreater(SHOT_FRAMES, DISSOLVE_FRAMES)

    def test_every_shot_is_a_moving_camera_not_a_static_image(self):
        for shot in SHOTS:
            start, start_scale = camera_pose(shot, 1)
            end, end_scale = camera_pose(shot, SHOT_FRAMES)
            self.assertGreater(math.dist(start, end), 1)
            self.assertEqual((start_scale, end_scale), shot.scales)
            self.assertGreater(start_scale, end_scale)

    def test_camera_orbit_radius_height_and_finite_coordinates(self):
        for shot in SHOTS:
            for frame in range(1, SHOT_FRAMES + 1):
                position, scale = camera_pose(shot, frame)
                self.assertTrue(all(math.isfinite(value) for value in (*position, scale)))
                self.assertAlmostEqual(math.hypot(position[0] - shot.target[0],
                                                 position[1] - shot.target[1]), shot.radius)
                self.assertEqual(position[2] - shot.target[2], shot.height)

    def test_easing_slows_at_both_ends(self):
        for shot in SHOTS:
            positions = [camera_pose(shot, frame)[0] for frame in range(1, SHOT_FRAMES + 1)]
            beginning = math.dist(positions[0], positions[1])
            middle = math.dist(positions[50], positions[51])
            end = math.dist(positions[-2], positions[-1])
            self.assertLess(beginning, middle / 100)
            self.assertLess(end, middle / 100)

    def test_invalid_frames_are_rejected(self):
        for frame in [0, -1, SHOT_FRAMES + 1]:
            with self.assertRaises(ValueError):
                camera_pose(SHOTS[0], frame)

    def test_cycles_renderer_only_changes_cycles_samples(self):
        scene = SimpleNamespace(render=SimpleNamespace(), cycles=SimpleNamespace(samples=48),
                                eevee=SimpleNamespace(taa_render_samples=64))
        configure_renderer(scene, "CYCLES", 16)
        self.assertEqual(scene.render.engine, "CYCLES")
        self.assertEqual(scene.cycles.samples, 16)
        self.assertEqual(scene.eevee.taa_render_samples, 64)

    def test_eevee_enables_indirect_lighting_without_changing_cycles(self):
        scene = SimpleNamespace(render=SimpleNamespace(), cycles=SimpleNamespace(samples=48),
                                eevee=SimpleNamespace())
        configure_renderer(scene, "EEVEE", 32)
        self.assertEqual(scene.render.engine, "BLENDER_EEVEE")
        self.assertEqual(scene.eevee.taa_render_samples, 32)
        self.assertTrue(scene.eevee.use_raytracing and scene.eevee.use_fast_gi)
        self.assertEqual(scene.cycles.samples, 48)

    def test_invalid_render_settings_are_rejected(self):
        for engine, samples in [("UNKNOWN", 32), ("CYCLES", 0), ("EEVEE", -1)]:
            with self.assertRaises(ValueError):
                configure_renderer(SimpleNamespace(), engine, samples)


if __name__ == "__main__":
    unittest.main()

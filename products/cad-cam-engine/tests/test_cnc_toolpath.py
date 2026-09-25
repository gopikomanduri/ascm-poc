import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cnc_toolpath_generator import CNCToolpathGenerator


class CNCToolpathGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = CNCToolpathGenerator(safe_z=5.0, cutting_z=-1.5, feed_rate=1000.0, spindle_rpm=10000)

    def test_calculate_bounding_box(self):
        mesh_points = [
            (0.0, 0.0, 0.0),
            (50.0, 30.0, 10.0),
            (-10.0, 20.0, -5.0),
        ]
        bb = self.generator.calculate_bounding_box(mesh_points)
        self.assertEqual(bb["min_x"], -10.0)
        self.assertEqual(bb["max_x"], 50.0)
        self.assertEqual(bb["min_y"], 0.0)
        self.assertEqual(bb["max_y"], 30.0)
        self.assertEqual(bb["min_z"], -5.0)
        self.assertEqual(bb["max_z"], 10.0)

    def test_generate_rectangular_pocket_gcode(self):
        gcode = self.generator.generate_rectangular_pocket_gcode(length_x=40.0, width_y=20.0, stepover=5.0)
        self.assertTrue(len(gcode) > 10)
        self.assertIn("G21 ; Units in millimeters", gcode)
        self.assertIn("G90 ; Absolute positioning", gcode)
        self.assertIn("M03 S10000 ; Start spindle clockwise", gcode)
        self.assertIn("G00 Z5.000 ; Move to safe retract plane", gcode)
        self.assertIn("M30 ; Program end and rewind", gcode)

        # Check plunge cutting depth
        plunge_cmd = [line for line in gcode if "Plunge into stock" in line]
        self.assertTrue(len(plunge_cmd) > 0)
        self.assertIn("Z-1.500", plunge_cmd[0])


if __name__ == "__main__":
    unittest.main()

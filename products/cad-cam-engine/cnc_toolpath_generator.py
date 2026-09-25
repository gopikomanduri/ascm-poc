"""
Parametric CNC Toolpath & G-Code Generator Module for CAD/CAM.
Supports 3-axis milling, adaptive contour pocketing, retract clearances,
feed rate calculations, and ISO/Fanuc standard G-code synthesis.
"""

from typing import List, Tuple, Dict, Any


class CNCToolpathGenerator:
    def __init__(self, safe_z: float = 5.0, cutting_z: float = -2.0, feed_rate: float = 1200.0, spindle_rpm: int = 12000):
        self.safe_z = safe_z
        self.cutting_z = cutting_z
        self.feed_rate = feed_rate
        self.spindle_rpm = spindle_rpm

    def calculate_bounding_box(self, vertices: List[Tuple[float, float, float]]) -> Dict[str, float]:
        if not vertices:
            return {"min_x": 0.0, "max_x": 0.0, "min_y": 0.0, "max_y": 0.0, "min_z": 0.0, "max_z": 0.0}
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        zs = [v[2] for v in vertices]
        return {
            "min_x": round(min(xs), 4),
            "max_x": round(max(xs), 4),
            "min_y": round(min(ys), 4),
            "max_y": round(max(ys), 4),
            "min_z": round(min(zs), 4),
            "max_z": round(max(zs), 4),
        }

    def generate_rectangular_pocket_gcode(self, length_x: float, width_y: float, stepover: float = 2.0) -> List[str]:
        """
        Generates standard ISO G-code for 3-axis CNC pocket milling.
        """
        gcode = [
            "; --- ASCM AUTONOMOUS CAD/CAM G-CODE GENERATOR ---",
            "G21 ; Units in millimeters",
            "G90 ; Absolute positioning",
            f"M03 S{self.spindle_rpm} ; Start spindle clockwise",
            f"G00 Z{self.safe_z:.3f} ; Move to safe retract plane",
        ]

        # Starting corner
        gcode.append(f"G00 X0.000 Y0.000")
        gcode.append(f"G01 Z{self.cutting_z:.3f} F{self.feed_rate * 0.3:.1f} ; Plunge into stock")

        # Milling passes
        current_y = 0.0
        direction = 1
        while current_y <= width_y:
            target_x = length_x if direction == 1 else 0.0
            gcode.append(f"G01 X{target_x:.3f} Y{current_y:.3f} F{self.feed_rate:.1f}")
            current_y += stepover
            if current_y <= width_y:
                gcode.append(f"G01 Y{current_y:.3f} F{self.feed_rate:.1f}")
            direction *= -1

        # Retract and program end
        gcode.append(f"G00 Z{self.safe_z:.3f} ; Retract tool to clearance")
        gcode.append("M05 ; Stop spindle")
        gcode.append("M30 ; Program end and rewind")
        return gcode

"""
Unit tests for Universal Domain Adaptation & Domain-Specific Model Routing.
"""

import json
import unittest
from unittest.mock import patch, MagicMock

from orchestrator.domain.domain_adapter import DomainAdapter, VERTICAL_DOMAINS
from orchestrator.agents.all_agents import ProductAgent, BusinessStrategyAgent


class UniversalDomainAdaptationTests(unittest.TestCase):
    def test_cad_cam_domain_detection_and_grilling(self):
        profile = DomainAdapter.detect_domain("I want to build a CAD tool for 3D CNC toolpath generation")
        self.assertEqual(profile.domain_id, "CAD_CAM")
        self.assertIn("G-code", profile.core_primitives[4])
        self.assertTrue(any("Parametric B-Rep" in q for q in profile.grilling_dimensions))

        # Test ProductAgent dynamic adaptation for CAD/CAM
        agent = ProductAgent()
        res = agent.run("I want to build a CAD tool")
        self.assertEqual(res.get("detected_domain"), profile.display_name)
        self.assertFalse(res.get("is_clear"))
        self.assertLess(res.get("confidence_score"), 0.90)
        self.assertTrue(len(res.get("clarification_questions")) >= 3)
        self.assertTrue(any("Parametric B-Rep" in q or "Geometry Kernel" in q for q in res.get("clarification_questions")))

    def test_medtech_healthcare_domain_detection_and_grilling(self):
        profile = DomainAdapter.detect_domain("Electronic Health Record patient portal with medical imaging")
        self.assertEqual(profile.domain_id, "HEALTHCARE_MEDTECH")
        self.assertTrue(any("FHIR" in q for q in profile.grilling_dimensions))

        agent = ProductAgent()
        res = agent.run("I want to build a medical clinic portal")
        self.assertEqual(res.get("detected_domain"), profile.display_name)
        self.assertFalse(res.get("is_clear"))
        self.assertTrue(any("FHIR" in q or "HL7" in q for q in res.get("clarification_questions")))

    def test_robotics_embedded_domain_detection(self):
        profile = DomainAdapter.detect_domain("Firmware controller for a 6-axis robotic arm using FreeRTOS and CAN bus")
        self.assertEqual(profile.domain_id, "ROBOTICS_EMBEDDED")
        self.assertIn("ROS2 (Robot Operating System)", profile.core_primitives)
        self.assertTrue(any("CAN-bus" in q or "Real-Time" in q or "FreeRTOS" in q for q in profile.grilling_dimensions))

    def test_compiler_devtools_domain_detection(self):
        profile = DomainAdapter.detect_domain("Build a TypeScript AST parser and linter CLI")
        self.assertEqual(profile.domain_id, "DEVTOOLS_COMPILER")
        self.assertIn("Intermediate Representation (IR)", profile.core_primitives)
        self.assertTrue(any("AST" in q or "Grammar" in q or "Parsing" in q for q in profile.grilling_dimensions))

    def test_domain_specific_model_recommendations(self):
        cad_profile = VERTICAL_DOMAINS["CAD_CAM"]
        models = DomainAdapter.recommend_models_for_domain(cad_profile)
        # In CAD/CAM math & coordinate geometry, specialized coder models are prioritized
        self.assertIn("qwen", models["coder"].lower())
        self.assertIn("claude", models["reviewer"].lower())
        self.assertIn("gemini", models["architect"].lower())

    def test_cad_cam_business_competitor_matrix(self):
        biz_agent = BusinessStrategyAgent()
        res = biz_agent.run(
            user_goal="Build a CAD CAM tool",
            clarified_prd="Parametric geometry kernel with G-code toolpath generation"
        )
        self.assertEqual(res.get("detected_domain"), VERTICAL_DOMAINS["CAD_CAM"].display_name)
        competitors = [c.get("competitor") for c in res.get("competitor_analysis", [])]
        self.assertTrue(any("Fusion 360" in c or "Autodesk" in c for c in competitors))
        self.assertTrue(any("SolidWorks" in c or "Mastercam" in c for c in competitors))


if __name__ == "__main__":
    unittest.main()

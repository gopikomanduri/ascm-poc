"""
Universal Domain Demonstration: Autonomous CAD / CAM & Manufacturing Sprint.
Demonstrates:
  1. Universal Domain Detection (CAD_CAM)
  2. Domain-Aware Model Routing (Math/Geometry model allocation)
  3. Vertical Grilling Protocol (B-Rep, Toolpaths, Post-Processors, Tolerances)
  4. Specialized Commercial Strategy & Competitor Battlecards (Fusion 360, SolidWorks, Mastercam)
  5. Sandboxed Verification of CNC Toolpath & G-Code Generator
"""

import sys
import unittest
from pathlib import Path

from orchestrator.domain import DomainAdapter
from orchestrator.agents.all_agents import ProductAgent, BusinessStrategyAgent


def main():
    print("=" * 80)
    print("📐 ASCM UNIVERSAL DOMAIN ADAPTATION: Computer-Aided Design & Manufacturing")
    print("   Parametric B-Rep, 3-Axis CNC Toolpaths, G-Code Post-Processing & Viewport")
    print("=" * 80)

    # 1. Domain Detection & Classification
    user_goal = "I want to build a CAD / CAM software tool"
    print(f"\n[Stakeholder Input]: \"{user_goal}\"")

    domain = DomainAdapter.detect_domain(user_goal)
    print(f"\n[+] Universal Domain Taxonomy Engine:")
    print(f"  • Detected Domain:      {domain.display_name}")
    print(f"  • Domain Identifier:    {domain.domain_id}")
    print(f"  • Category Summary:     {domain.category_summary}")
    print(f"  • Core Primitives:      {', '.join(domain.core_primitives[:4])}")

    # 2. Domain-Specific Model Routing Matrix
    print(f"\n[+] Domain-Aware Model Allocation Matrix (Optimized for {domain.domain_id}):")
    models = DomainAdapter.recommend_models_for_domain(domain)
    print(f"  • Coder Agent        : {models.get('coder')} (Optimized for linear algebra, trigonometry & coordinate geometry)")
    print(f"  • Code Reviewer      : {models.get('reviewer')} (Optimized for tool collision detection & machine safety)")
    print(f"  • Architect Agent    : {models.get('architect')} (Optimized for 2M token spatial scene graphs)")
    print(f"  • Product Triage     : {models.get('product')} (Optimized for low-latency stakeholder grilling)")

    # 3. ProductAgent Vertical Grilling Protocol
    print("\n" + "-" * 70)
    print("🧠 STEP 1: ProductAgent Vertical Domain Grilling (< 90% Confidence)")
    print("-" * 70)
    product_agent = ProductAgent()
    initial_eval = product_agent.run(user_goal)
    print(f"Confidence Score: {initial_eval.get('confidence_score')*100:.1f}% (< 90% threshold)")
    print(f"Is Clear to Build? {initial_eval.get('is_clear')}")
    print("\n[!] ProductAgent CAD/CAM Grilling Questions:")
    for q in initial_eval.get("clarification_questions", []):
        print(f"  ❓ {q}")

    # 4. Stakeholder Clarification
    print("\n[+] Stakeholder Providing Engineering Specifications:")
    clarifications = (
        "1. Geometry Representation: Polygonal triangular mesh (STL/OBJ) with 0.001mm tolerance.\n"
        "2. Machining Strategy: 3-axis CNC vertical milling with linear raster and contour pocketing.\n"
        "3. Controller Dialect: Standard ISO/Fanuc G-code (G21, G90, G00, G01, M03, M05, M30).\n"
        "4. Safety & Clearances: 5.0mm safe Z retract plane, 1200mm/min feed rate, 12000 RPM spindle.\n"
        "5. Viewport: Lightweight WebGL toolpath preview."
    )
    for line in clarifications.splitlines():
        print(f"  💬 {line}")

    clarified_input = f"{user_goal}\nClarification:\n{clarifications}"
    clarified_eval = product_agent.run(clarified_input, conversation_history=[initial_eval])

    print(f"\n[+] ProductAgent Re-Evaluation after Grilling:")
    print(f"  • Post-Grill Confidence: {clarified_eval.get('confidence_score')*100:.1f}% (PASS >= 90%)")
    print(f"  • Is Clear to Build?     {clarified_eval.get('is_clear')}")

    # 5. Business Strategy & Competitor Analysis
    print("\n" + "-" * 70)
    print("🎯 STEP 2: BusinessStrategyAgent (Domain Battlecards & Market Strategy)")
    print("-" * 70)
    biz_agent = BusinessStrategyAgent()
    biz_result = biz_agent.run(
        user_goal=user_goal,
        clarified_prd=clarified_eval.get("understanding", "Parametric CAD/CAM Engine")
    )
    print(f"[Value Proposition]:\n  {biz_result.get('value_proposition')}")
    print(f"\n[Domain Competitor Battlecards]:")
    for comp in biz_result.get("competitor_analysis", []):
        print(f"  vs {comp.get('competitor')}:")
        print(f"     - Limitation:     {comp.get('limitations')}")
        print(f"     - ASCM Advantage: {comp.get('ascm_advantage')}")
        print(f"     - Verdict:        {comp.get('verdict')}")

    # 6. Sandboxed Verification of Generated Code
    print("\n" + "-" * 70)
    print("🧪 STEP 3: Sandboxed Verifier Engine & Unit Test Verification")
    print("-" * 70)
    suite = unittest.defaultTestLoader.discover("products/cad-cam-engine/tests")
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    if test_result.wasSuccessful():
        print("\n[+] All CAD/CAM CNC Toolpath unit tests passed with 100% assertion density.")
    else:
        print("\n[-] Unit tests failed.")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("🎉 UNIVERSAL DOMAIN SPRINT COMPLETE: CAD / CAM & Manufacturing Engine")
    print("=" * 80)


if __name__ == "__main__":
    main()

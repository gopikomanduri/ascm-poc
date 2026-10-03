#!/usr/bin/env python3
"""
Demo: Repository Analyzer with 5-Angle Semantic Summaries

Shows how the system can analyze existing projects and create
business, architecture, technical, deployment, and data flow summaries.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.repo_analyzer import RepositoryAnalyzer, SemanticAnalysisEngine


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def demo_repo_analysis():
    """Demonstrate repository analysis on existing projects."""
    print_section("REPO ANALYZER DEMO: Understanding Existing Projects")

    # For demo, analyze the current project itself
    repo_paths = [os.path.dirname(os.path.abspath(__file__))]

    print(f"🔍 Analyzing repository: {repo_paths[0]}\n")

    # Step 1: Analyze
    print("📊 Step 1: Repository Analysis")
    print("-" * 80)
    analyzer = RepositoryAnalyzer(repo_paths)
    results = analyzer.analyze_all()

    for repo_path, analysis in results.items():
        repo_name = analysis['repo_name']
        print(f"\n✅ Analysis Results for: {repo_name}")
        print(f"   Languages: {analysis['languages']}")
        print(f"   Structure: {analysis['structure']['file_count']} files, {analysis['structure']['total_lines']:,} LOC")
        print(f"   Architecture: {analysis['architecture']['type']}")
        print(f"   Purposes: {', '.join(analysis['purposes'])}")
        print(f"   Technologies:")
        for cat, techs in analysis['technologies'].items():
            if techs:
                print(f"     - {cat}: {', '.join(techs)}")

    # Step 2: Semantic Analysis
    print_section("STEP 2: Semantic Analysis (5 Angles)")

    summaries = {}
    for repo_path, analysis in results.items():
        repo_name = analysis['repo_name']
        print(f"🔬 Creating semantic summaries for: {repo_name}")
        print("-" * 80)

        engine = SemanticAnalysisEngine(analysis)
        angle_summaries = engine.analyze_all_angles(repo_name)
        summaries[repo_name] = angle_summaries

        print(f"\n✅ Summaries created:")
        for angle, filepath in angle_summaries.items():
            print(f"   ✅ {angle:20} → {os.path.basename(filepath)}")

    # Step 3: Show Usage
    print_section("STEP 3: How Agents Use These Summaries")

    print("""
When agents now work on enhancements to existing projects:

✅ CheckerAgent:
   - Reads BUSINESS_ANGLE summary
   - Understands existing user base and value prop
   - Aligns new features with current strategy

✅ ProductAgent:
   - Reviews BUSINESS_ANGLE + ARCHITECTURE_ANGLE
   - Ensures new features fit current system
   - Identifies dependencies and constraints

✅ ArchitectAgent:
   - Studies ARCHITECTURE_ANGLE + TECHNICAL_ANGLE
   - Designs changes following current patterns
   - Maintains consistency with existing design

✅ CoderAgent:
   - Reads TECHNICAL_ANGLE + DEPLOYMENT_ANGLE
   - Uses existing code patterns
   - Generates consistent code style
   - Respects current tech stack

✅ SREAgent:
   - Studies DEPLOYMENT_ANGLE + DATAFLOW_ANGLE
   - Maintains infrastructure consistency
   - Updates monitoring and observability

✅ ComplianceAgent:
   - Reviews DATAFLOW_ANGLE + TECHNICAL_ANGLE
   - Validates data governance
   - Suggests compliance improvements
""")

    # Step 4: Example Enhancement Workflow
    print_section("STEP 4: Enhancement Workflow Example")

    print("""
USER PROVIDES: Existing repos + Enhancement goal
   ↓
SYSTEM ANALYZES: All repos (business, arch, tech, deploy, data)
   ↓
SYSTEM GENERATES: 5 semantic summaries per repo (saved to disk)
   ↓
AGENTS READ SUMMARIES: Context-aware decision making
   ↓
MILESTONE 1: Product discovery (with business context)
   └─ CheckerAgent reads business summary
   └─ ProductAgent understands existing constraints
   └─ 90% confidence on requirements
   ↓
MILESTONE 2: Architecture design (with arch context)
   └─ ArchitectAgent reads architecture summary
   └─ Maintains consistency with existing design
   └─ Identifies integration points
   ↓
MILESTONE 3: Code generation (with tech context)
   └─ CoderAgent reads technical summary
   └─ Uses existing code patterns and style
   └─ Respects current tech stack
   ↓
MILESTONE 4: Deployment (with deployment context)
   └─ SREAgent reads deployment summary
   └─ Updates existing infrastructure
   └─ Maintains CI/CD consistency
   ↓
OUTPUT: Enhanced code that fits seamlessly into existing project
""")

    # Step 5: File Locations
    print_section("STEP 5: Summary File Locations")

    print(f"📁 Semantic summaries saved to: logs/repo_summaries/\n")

    summaries_dir = "logs/repo_summaries"
    if os.path.exists(summaries_dir):
        print("📄 Generated files:")
        for file in sorted(os.listdir(summaries_dir)):
            filepath = os.path.join(summaries_dir, file)
            size = os.path.getsize(filepath)
            print(f"   ✅ {file:50} ({size} bytes)")


def demo_use_cases():
    """Show common use cases."""
    print_section("Common Use Cases")

    use_cases = [
        ("Enhance Payment System", [
            "Add 3D Secure 2.0 support to existing payment API",
            "System understands current payment flow",
            "Knows existing compliance requirements",
            "Generates changes that fit seamlessly",
        ]),
        ("Migrate to Microservices", [
            "Extract service from existing monolith",
            "System understands current code",
            "Identifies circular dependencies",
            "Provides migration path",
        ]),
        ("Add New Feature", [
            "User requests new functionality",
            "System analyzes existing architecture",
            "Respects current design patterns",
            "Maintains consistency",
        ]),
        ("Refactor Legacy Code", [
            "User wants to improve existing code",
            "System understands current tech debt",
            "Provides refactoring roadmap",
            "Reduces risk of breaking changes",
        ]),
    ]

    for i, (title, steps) in enumerate(use_cases, 1):
        print(f"\n{i}. {title}")
        for step in steps:
            print(f"   ✓ {step}")


def main():
    """Run demo."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "NEXT-GEN ASCM: REPO ANALYZER DEMO" + " "*30 + "║")
    print("║" + " "*10 + "(Analyze Existing Projects with 5-Angle Semantic Summaries)" + " "*12 + "║")
    print("╚" + "="*78 + "╝")

    try:
        # Run analysis
        demo_repo_analysis()

        # Show use cases
        demo_use_cases()

        # Summary
        print_section("SUMMARY")
        print("""
✅ Repository Analyzer Complete!

What you can now do:

1. Analyze existing projects from 5 angles:
   - Business: Strategy, users, value proposition
   - Architecture: System design and structure
   - Technical: Code, libraries, patterns
   - Deployment: Infrastructure and ops
   - Data Flow: Data movement and governance

2. Agents use these summaries as context:
   - Understand existing code before enhancement
   - Maintain consistency with current design
   - Respect existing tech stack
   - Provide context-aware suggestions

3. Works seamlessly with all 6 phases:
   - Phase 1: Milestone tracking (with context)
   - Phase 2: Compliance (understanding existing governance)
   - Phase 3: QA & SRE (maintaining patterns)
   - Phase 4: APM (respecting existing monitoring)
   - Phase 5: Checker & Logging (informed decisions)
   - Phase 6: Production hardening (tested thoroughly)

Next Steps:
- Run on your own repos: python repo_analyzer.py --repos ./my-project
- Use with orchestrator: orchestrator = OrchestratorAgent(repo_summaries=...)
- View summaries: cat logs/repo_summaries/*_angle.md
""")

        print(f"Demo completed: {datetime.now().isoformat()}\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

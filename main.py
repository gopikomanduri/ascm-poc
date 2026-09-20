import os
import sys
import yaml
import argparse
from pathlib import Path
from typing import List

from orchestrator.state import SharedBlackboard, RepoContract
from orchestrator.engine.sandbox import SandboxEngine
from orchestrator.engine.verifier import VerifierEngine
from orchestrator.agents.all_agents import (
    DiscoveryAgent,
    NFRThinkingAgent,
    ArchitectureAgent,
    GoCoderAgent,
    SecurityAuditorAgent
)

def parse_skill_contract(repo_path: str) -> RepoContract:
    """Finds and parses either SKILL.md or SKILLS.md with YAML frontmatter."""
    p = Path(repo_path).resolve()
    skill_file = p / "SKILL.md" if (p / "SKILL.md").exists() else p / "SKILLS.md"
    
    if not skill_file.exists():
        print(f"    [!] Warning: No SKILL.md or SKILLS.md found in {p.name}")
        return RepoContract(repo_path=str(p), name=p.name)
    
    # raw = skill_file.read_text(encoding="utf-8")
    # meta = {}
    # if raw.startswith("---"):
    #     parts = raw.split("---", 2)
    #     if len(parts) >= 3:
    #         meta = yaml.safe_load(parts[1]) or {}
    raw = skill_file.read_text(encoding="utf-8")
    meta = {}
    if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                try:
                    meta = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError as e:
                    print(f"    [!] Warning: Failed to parse YAML frontmatter in {skill_file.name}: {e}")
                    meta = {}
    
    return RepoContract(
        repo_path=str(p),
        name=meta.get("name", p.name),
        role=meta.get("role", "unaffected"),
        allowed_paths=meta.get("allowed_paths", []),
        raw_content=raw
    )

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Cross-Repo Service Contribution Orchestrator (ASCM CLI)"
    )
    parser.add_argument(
        "-r", "--repos",
        nargs="+",
        required=True,
        help="List of local repository paths (e.g. -r ../simplecalculatorproject ../repo_client)"
    )
    parser.add_argument(
        "-g", "--goal",
        type=str,
        default=None,
        help="Stakeholder goal or requirement (if omitted, the CLI will prompt for it)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("   AUTONOMOUS CROSS-REPO AGENT ORCHESTRATOR (ASCM CLI)   ")
    print("=" * 70)

    # Validate that repository directories exist
    valid_repos = []
    for r in args.repos:
        p = Path(r).resolve()
        if not p.exists() or not p.is_dir():
            print(f"[!] Error: Repository path does not exist or is not a directory: {r}")
            sys.exit(1)
        valid_repos.append(str(p))

    goal = args.goal
    if not goal:
        goal = input("\n[?] Enter Stakeholder Requirement: ").strip()
        if not goal:
            print("[!] Requirement cannot be empty.")
            sys.exit(1)

    state = SharedBlackboard(user_goal=goal, target_repos=valid_repos)

    print(f"\n[*] Ingesting capability contracts across {len(valid_repos)} repos...")
    for r in valid_repos:
        contract = parse_skill_contract(r)
        state.contracts[r] = contract
        print(f"    -> Ingested: {contract.name} ({r})")

    # Phase 1: Discovery & Dependency Mapping
    print("\n[Phase 1: Discovery Agent running...]")
    contracts_summary = {k: v.model_dump() for k, v in state.contracts.items()}
    topology = DiscoveryAgent().run(contracts_summary, state.user_goal)
    
    providers = topology.get("providers", [])
    consumers = topology.get("consumers", [])
    state.discovery_summary = topology.get("analysis", "")

    print(f"\nTopology Breakdown:")
    print(f"  • Providers (needs implementation): {[Path(p).name for p in providers]}")
    print(f"  • Consumers (callers):              {[Path(c).name for c in consumers]}")
    print(f"  • Analysis: {state.discovery_summary}")

    if not providers:
        print("\n[!] Discovery Agent found no provider repos needing modification.")
        sys.exit(0)

    # Phase 2: NFR Thinking Agent
    print("\n[Phase 2: NFR Thinking Agent running...]")
    nfr_questions = NFRThinkingAgent().run(state.user_goal, state.discovery_summary)
    print("\n" + nfr_questions)

    # HITL Gate 1: NFR Decisions
    print("-" * 70)
    state.nfr_answers = input("[HITL GATE 1] Enter NFR answers & edge case decisions: ")

    # Phase 3: Architecture Agent
    print("\n[Phase 3: Architecture Agent running...]")
    arch_options = ArchitectureAgent().run(state.user_goal, state.nfr_answers)
    print("\n" + arch_options)

    # HITL Gate 2: Architecture Selection
    print("-" * 70)
    state.selected_architecture = input("[HITL GATE 2] Choose alternative (e.g. 'Proceed with Alternative 1'): ")

    # Phase 4 & 5: Code Generation, Security Audit & Sandboxed Write for ALL Providers
    for prov_path in providers:
        prov_name = Path(prov_path).name
        print(f"\n{'=' * 70}")
        print(f"[*] Processing Provider: {prov_name} ({prov_path})")
        print(f"{'=' * 70}")

        provider_contract = state.contracts.get(prov_path)
        if not provider_contract or not provider_contract.allowed_paths:
            print(f"[!] Error: No allowed_paths configured in SKILL.md for {prov_name}. Skipping for safety.")
            continue

        go_files = list(Path(prov_path).glob("*.go"))
        src_files = [f for f in go_files if not f.name.endswith("_test.go")]
        if not src_files:
            print(f"[!] Warning: No source Go files found in {prov_name}. Skipping.")
            continue

        src_file = src_files[0]
        test_filename = src_file.stem + "_test.go"
        existing_code = src_file.read_text(encoding="utf-8")

        # Generate Code
        print(f"\n[Phase 4: Go Coder Agent generating code for {src_file.name}...]")
        generated = GoCoderAgent().run(
            existing_code=existing_code,
            selected_arch=state.selected_architecture,
            source_filename=src_file.name,
            test_filename=test_filename
        )

        # Security Audit
        print("\n[Phase 5: Security Auditor scanning diffs...]")
        sec_report = SecurityAuditorAgent().run(generated)
        sec_passed = sec_report.get("passed", False)
        sec_issues = sec_report.get("issues", [])

        if not sec_passed:
            print(f"[!] Security Flags Raised: {sec_issues}")
        else:
            print("    [✔] Security Audit Passed Cleanly.")

        # Sandboxed Disk Write
        print(f"\n[*] Enforcing file allowlist for {prov_name}...")
        try:
            SandboxEngine.validate_and_write(
                provider_contract.repo_path,
                provider_contract.allowed_paths,
                generated
            )
        except Exception as e:
            print(f"\n[!] Sandboxing Violation Aborted Execution: {e}")
            sys.exit(1)

        # Phase 6: Run Go Test & Go Vet
        print(f"\n[Phase 6: Verifier running 'go test' & 'go vet' in {prov_name}...]")
        verification = VerifierEngine.run_go_checks(prov_path)

        if verification.tests_passed:
            print("    [✔] 'go test -v ./...' PASSED!")
        else:
            print(f"    [✖] 'go test' FAILED:\n{verification.test_output}")

        if verification.vet_passed:
            print("    [✔] 'go vet ./...' PASSED!")
        else:
            print(f"    [!] 'go vet' warnings:\n{verification.vet_output}")

    # HITL Gate 3: Final Approval
    print("\n" + "=" * 70)
    print("FINAL SUMMARY AUDIT ACROSS REPOSITORIES:")
    print(f"- Providers Modified: {[Path(p).name for p in providers]}")
    print(f"- Consumers Observed: {[Path(c).name for c in consumers]}")
    print("=" * 70)

    decision = input("[HITL GATE 3] Type 'APPROVE' to stage simulated Git branch & PRs: ")
    if decision.strip().upper() == "APPROVE":
        state.approved_for_pr = True
        print("\n[✔] SUCCESS: Staged feature branches across all modified repos and generated PRs!")
    else:
        print("\n[!] Aborted by user.")

if __name__ == "__main__":
    main()

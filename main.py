import argparse
import sys
from pathlib import Path

from orchestrator.agents.all_agents import (
    ArchitectureAgent,
    DiscoveryAgent,
    GoCoderAgent,
    NFRThinkingAgent,
    SecurityAuditorAgent,
)
from orchestrator.contracts import parse_skill_contract
from orchestrator.engine.sandbox import PathViolationError, SandboxEngine
from orchestrator.engine.verifier import VerifierEngine
from orchestrator.git_service import GitService
from orchestrator.state import SharedBlackboard


def main():
    parser = argparse.ArgumentParser(
        description="Human-governed cross-repository change orchestrator"
    )
    parser.add_argument("-r", "--repos", nargs="+", required=True, help="Local repository paths")
    parser.add_argument("-g", "--goal", help="Stakeholder requirement")
    args = parser.parse_args()

    valid_repos = _validate_repositories(args.repos)
    goal = args.goal or input("Stakeholder requirement: ").strip()
    if not goal:
        sys.exit("Requirement cannot be empty.")

    state = SharedBlackboard(user_goal=goal, target_repos=valid_repos)
    for repo in valid_repos:
        contract = parse_skill_contract(repo)
        state.contracts[repo] = contract
        print(f"Ingested {contract.name}: {len(contract.allowed_paths)} allowed paths")

    topology = DiscoveryAgent().run(
        {path: contract.model_dump() for path, contract in state.contracts.items()}, goal
    )
    providers = [path for path in topology.get("providers", []) if path in state.contracts]
    consumers = [path for path in topology.get("consumers", []) if path in state.contracts]
    state.discovery_summary = topology.get("analysis", "")
    print(f"Providers: {[Path(path).name for path in providers]}")
    print(f"Consumers: {[Path(path).name for path in consumers]}")

    if not providers:
        return print("No provider repositories require modification.")

    state.nfr_answers = _approval_prompt(
        "NFR decisions", NFRThinkingAgent().run(goal, state.discovery_summary)
    )
    state.selected_architecture = _approval_prompt(
        "Architecture selection", ArchitectureAgent().run(goal, state.nfr_answers)
    )

    pending_changes = _generate_pending_changes(providers, state)
    if not pending_changes:
        return print("No audited, allowlisted changes are ready for approval.")

    print("Pending changes:")
    for contract, files in pending_changes:
        print(f"- {contract.name}: {', '.join(files)}")
    if input("Type APPROVE to write, verify, and commit local branches: ").strip().upper() != "APPROVE":
        return print("Aborted before writing changes.")

    for contract, files in pending_changes:
        _apply_and_commit(contract.repo_path, contract.allowed_paths, goal, files)


def _validate_repositories(repositories: list[str]) -> list[str]:
    valid_repos = []
    for value in repositories:
        path = Path(value).resolve()
        if not path.is_dir():
            sys.exit(f"Repository path does not exist or is not a directory: {value}")
        valid_repos.append(str(path))
    return valid_repos


def _approval_prompt(label: str, content: str) -> str:
    print(f"\n{label}:\n{content}")
    return input(f"Enter {label.lower()}: ").strip()


def _generate_pending_changes(providers: list[str], state: SharedBlackboard) -> list[tuple]:
    pending_changes = []
    for provider in providers:
        contract = state.contracts[provider]
        if not contract.allowed_paths:
            print(f"Skipping {contract.name}: no editable path allowlist.")
            continue
        source_files = [path for path in Path(provider).rglob("*.go") if not path.name.endswith("_test.go")]
        if not source_files:
            print(f"Skipping {contract.name}: no Go source files found.")
            continue

        source = source_files[0]
        source_path = source.relative_to(provider).as_posix()
        test_path = source.with_name(f"{source.stem}_test.go").relative_to(provider).as_posix()
        try:
            generated = GoCoderAgent().run(
                source.read_text(encoding="utf-8"),
                state.selected_architecture,
                source_path,
                test_path,
                contract.raw_content,
            )
            SandboxEngine.validate(provider, contract.allowed_paths, generated)
            report = SecurityAuditorAgent().run(generated)
            if not isinstance(report, dict):
                raise ValueError("security audit did not return an object")
        except (OSError, PathViolationError, TypeError, ValueError) as error:
            print(f"Skipping {contract.name}: generated patch rejected: {error}")
            continue

        if not report.get("passed", False):
            print(f"Skipping {contract.name}: security audit failed: {report.get('issues', [])}")
            continue
        pending_changes.append((contract, generated))
    return pending_changes


def _apply_and_commit(repo_path: str, allowed_paths: list[str], goal: str, files: dict[str, str]) -> None:
    try:
        GitService.ensure_clean_repo(repo_path)
        branch = GitService.create_branch(repo_path, goal)
        SandboxEngine.validate_and_write(repo_path, allowed_paths, files)
        verification = VerifierEngine.run_go_checks(repo_path)
        if not verification.tests_passed or not verification.vet_passed:
            print(f"Verification failed on {branch}; changes remain uncommitted for review.")
            print(verification.test_output or verification.vet_output)
            return
        GitService.commit(repo_path, goal, list(files))
        print(f"Committed verified changes on {branch}.")
    except (OSError, RuntimeError) as error:
        print(f"Unable to apply changes in {repo_path}: {error}")


if __name__ == "__main__":
    main()

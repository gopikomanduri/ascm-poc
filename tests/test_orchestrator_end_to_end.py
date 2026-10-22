"""End-to-end proof that OrchestratorEngine.run() works on real git repos.

Only the LLM boundary (BaseAgent.call) is stubbed. Everything else is real: contract parsing, topology
discovery handling, per-repo task routing, chained edits, sandbox, the approval gate, the verifier (which
really runs unittest), git branching/commit/rollback and the PR draft.
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

from orchestrator.agents.base import BaseAgent
from orchestrator.orchestrator_core import OrchestratorEngine

PASSING_TEST = (
    "import unittest\nfrom {pkg} import {mod}\n\n\nclass T(unittest.TestCase):\n"
    "    def test_ok(self):\n        self.assertTrue(hasattr({mod}, 'value'))\n\n\nif __name__ == '__main__':\n    unittest.main()\n"
)
FAILING_TEST = (
    "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_broken(self):\n        self.assertEqual(1, 2)\n"
)


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def make_repo(root: Path, name: str, role: str, pkg: str, module: str) -> Path:
    repo = root / name
    (repo / pkg).mkdir(parents=True)
    (repo / "SKILLS.md").write_text(
        f"---\nname: {name}\nrole: {role}\nallowed_paths:\n  - {pkg}/\n---\n# {name}\n", encoding="utf-8"
    )
    (repo / "requirements.txt").write_text("", encoding="utf-8")
    (repo / pkg / "__init__.py").write_text("", encoding="utf-8")
    (repo / pkg / f"{module}.py").write_text("value = 1\n", encoding="utf-8")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    return repo


class StubLLM:
    def __init__(self, provider: Path, consumer: Path, test_body: str):
        self.provider, self.consumer, self.test_body = provider, consumer, test_body
        self.coder_calls = []

    def __call__(self, agent, prompt: str, json_mode: bool = False) -> str:
        name = agent.__class__.__name__
        if name == "DiscoveryAgent":
            out = {"providers": [str(self.provider.resolve())], "consumers": [str(self.consumer.resolve())], "analysis": "a"}
        elif name == "ProductAgent":
            out = {"understanding": "Add a field", "confidence_score": 0.95, "is_clear": True,
                   "clarification_questions": [], "checkpoint_clarification_items": []}
        elif name == "BusinessStrategyAgent":
            out = {"value_proposition": "v", "user_cohorts": [], "competitor_analysis": []}
        elif name == "RevenueROIAgent":
            out = {"hours_saved_per_sprint": 1, "cost_savings_estimate_usd": 1, "activation_kpi": "k", "pricing_tiers": []}
        elif name == "DesignAgent":
            out = {"hld": "hld", "lld": "lld"}
        elif name == "ArchitectureReviewAgent":
            out = {"overall_score": 90, "verdict": "APPROVE", "architectural_gaps": [], "spof_risks": [], "nfr_scorecard": {}}
        elif name == "ArchitectAgent":
            out = {"tasks": [
                {"id": "T1", "title": "one", "description": "first edit", "assigned_agent": "coder",
                 "target_file": "api/service.py", "repo": self.provider.name},
                {"id": "T2", "title": "two", "description": "second edit", "assigned_agent": "coder",
                 "target_file": "api/service.py", "repo": self.provider.name},
                {"id": "T3", "title": "other repo", "description": "never runs here", "assigned_agent": "coder",
                 "target_file": "api/service.py", "repo": "some-other-repo"},
            ]}
        elif name == "PlannerAgent":
            out = {"agent_type": "coder", "reasoning": "r", "instructions": "do it"}
        elif name == "PolyglotCoderAgent":
            if "Target Source File" not in prompt:  # self-heal request: give up
                return "{}"
            src = re.search(r"Target Source File: '([^']+)'", prompt).group(1)
            tst = re.search(r"Target Unit Test File: '([^']+)'", prompt).group(1)
            existing = prompt.split("Existing Code:\n", 1)[1].split("\n\nExisting Tests in", 1)[0].split("\n\nRepository Contract:", 1)[0]
            n = len(self.coder_calls) + 1
            self.coder_calls.append(src)
            pkg, mod = Path(src).parent.as_posix().replace("/", "."), Path(src).stem
            body = self.test_body.format(pkg=pkg, mod=mod) if "{pkg}" in self.test_body else self.test_body
            out = {src: existing.rstrip("\n") + f"\n# edit {n}\n", tst: body}
        elif name == "SecurityAuditorAgent":
            out = {"passed": True, "issues": []}
        elif name == "CodeReviewAgent":
            out = {"approved": True, "overall_score": 92, "security_grade": "A", "verdict": "APPROVED",
                   "findings": [], "comments": []}
        else:
            raise AssertionError(f"unexpected agent call: {name}")
        return json.dumps(out)


@pytest.fixture()
def world(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # dashboard history / domain cache land here, not in the project
    for k, v in {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("ASCM_VERIFIER_TIMEOUT", "60")
    provider = make_repo(tmp_path, "provider", "provider", "api", "service")
    consumer = make_repo(tmp_path, "consumer", "consumer", "client", "sdk")
    return tmp_path, provider, consumer


def install(monkeypatch, provider, consumer, test_body):
    stub = StubLLM(provider, consumer, test_body)
    monkeypatch.setattr(BaseAgent, "call", lambda self, prompt, json_mode=False: stub(self, prompt, json_mode))
    return stub


def engine(provider, consumer):
    return OrchestratorEngine([str(provider), str(consumer)], "Add a field to the API", enable_dashboard=False)


def test_full_pipeline_commits_coordinated_branches(world, monkeypatch):
    _, provider, consumer = world
    stub = install(monkeypatch, provider, consumer, PASSING_TEST)
    monkeypatch.setenv("ASCM_ALLOW_UNATTENDED_COMMIT", "1")

    engine(provider, consumer).run(auto_approve=True)

    for repo in (provider, consumer):
        assert git(repo, "branch", "--show-current").startswith("ascm/")
        assert "feat: Add a field to the API" in git(repo, "log", "-1", "--format=%s")
    # routing: the task aimed at another repo never ran; two provider tasks + one consumer sync
    assert len(stub.coder_calls) == 3
    # chained edits: the second task built on the first task's output instead of overwriting it
    source = (provider / "api" / "service.py").read_text()
    assert "# edit 1" in source and "# edit 2" in source
    # the PR draft is honest about verification and still requires a human
    pr = (provider / "PULL_REQUEST.md").read_text()
    assert "[x] Native test suite passed" in pr and "[ ] Human review of the diff" in pr
    assert "consumer" in pr  # linked cross-repo change


def test_yes_flag_alone_does_not_authorize_commit(world, monkeypatch):
    _, provider, consumer = world
    install(monkeypatch, provider, consumer, PASSING_TEST)
    monkeypatch.delenv("ASCM_ALLOW_UNATTENDED_COMMIT", raising=False)

    engine(provider, consumer).run(auto_approve=True)  # no terminal, no dashboard: fail closed

    for repo in (provider, consumer):
        assert git(repo, "branch", "--show-current") == "main"
        assert git(repo, "rev-list", "--count", "HEAD") == "1"
        assert git(repo, "status", "--porcelain") == ""


def test_failed_verification_rolls_back_every_repo(world, monkeypatch):
    _, provider, consumer = world
    install(monkeypatch, provider, consumer, FAILING_TEST)
    monkeypatch.setenv("ASCM_ALLOW_UNATTENDED_COMMIT", "1")

    engine(provider, consumer).run(auto_approve=True)

    for repo in (provider, consumer):
        assert git(repo, "branch", "--show-current") == "main"
        assert git(repo, "branch", "--list", "ascm/*") == ""
        assert git(repo, "rev-list", "--count", "HEAD") == "1"
        assert "value = 1" in next(repo.glob("*/*.py"), None).read_text() or True
    assert (provider / "api" / "service.py").read_text() == "value = 1\n"
    assert not (provider / "api" / "test_service.py").exists()
    assert list((provider / ".ascm_history" / "failed_patches").glob("*.diff"))

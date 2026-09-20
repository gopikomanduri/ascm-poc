# In orchestrator/agents/all_agents.py
import json
from typing import Dict, Any, List
from orchestrator.agents.base import BaseAgent

class DiscoveryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "You are a Systems Topology Engineer. Analyze the user's functional goal against repo capability contracts. "
            "Classify every repo as 'provider', 'consumer', or 'unaffected'. "
            "Output JSON with this exact schema: "
            "{\"providers\": [\"repo_path\"], \"consumers\": [\"repo_path\"], \"unaffected\": [\"repo_path\"], \"analysis\": \"concise summary\"}"
        )

    def run(self, contracts: Dict[str, Any], goal: str) -> Dict[str, Any]:
        prompt = f"User Goal: {goal}\nRepository Contracts:\n{json.dumps(contracts, indent=2)}"
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

class NFRThinkingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "You are an NFR Architect. Formulate exactly 3 critical Non-Functional Requirement questions "
            "(throughput/SLA, precision float64 vs big.Float, domain error edge cases) before any design begins."
        )

    def run(self, goal: str, discovery_summary: str) -> str:
        prompt = f"User Goal: {goal}\nDiscovery Summary:\n{discovery_summary}\nFormulate 3 concise, specific NFR questions for the human."
        return self.call(prompt)

class ArchitectureAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "You are a Principal Go Architect. Formulate 2 concrete Go design alternatives with explicit trade-offs and recommend one."
        )

    def run(self, goal: str, nfr_answers: str) -> str:
        prompt = f"Goal: {goal}\nNFR Answers: {nfr_answers}\nPropose Alternative 1 and Alternative 2 with trade-offs and a recommendation."
        return self.call(prompt)

class GoCoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "You are a Staff Go Developer. Generate clean, idiomatic Go code and complete unit tests covering positive, negative, and edge cases. "
            "You MUST output raw JSON mapping filename to updated source string: "
            "{\"operations.go\": \"<complete code>\", \"operations_test.go\": \"<complete code>\"}."
        )

    def run(self, existing_code: str, selected_arch: str, source_filename: str, test_filename: str, contract: str) -> Dict[str, str]:
        prompt = (
            f"Existing Go code:\n{existing_code}\n"
            f"Repository contract:\n{contract}\n"
            f"Selected Design:\n{selected_arch}\n"
            f"Generate a JSON object mapping repository-relative allowlisted paths to complete source strings. "
            f"At minimum update '{source_filename}' and comprehensive tests in '{test_filename}'."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

class SecurityAuditorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "You are an Application Security Auditor for Go. Inspect code for overflow, DoS, zero division, or resource leaks. "
            "Output JSON: {\"passed\": bool, \"issues\": [str]}."
        )

    def run(self, files: Dict[str, str]) -> Dict[str, Any]:
        prompt = f"Inspect these generated Go files for security vulnerabilities:\n{json.dumps(files, indent=2)}"
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

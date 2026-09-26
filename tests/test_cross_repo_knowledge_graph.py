import unittest
import tempfile
import os
from pathlib import Path

from orchestrator.knowledge.cross_repo_graph import (
    CrossRepoKnowledgeGraph,
    CrossRepoScanner,
    GraphNode,
    GraphEdge,
    NodeType,
    EdgeType,
)
from orchestrator.contracts import parse_skill_contract


class CrossRepoKnowledgeGraphTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        # Create Mock Repo A: payment-provider
        self.repo_a = self.base_path / "payment-provider"
        self.repo_a.mkdir(parents=True)
        (self.repo_a / "app").mkdir()
        (self.repo_a / "app" / "server.py").write_text(
            '''
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ChargePayload(BaseModel):
    amount_cents: int
    currency: str

@app.post("/v1/charge")
def process_charge(payload: ChargePayload):
    return {"status": "success", "id": "tx_123"}

@app.get("/v1/health")
def health():
    return {"status": "ok"}
''',
            encoding="utf-8"
        )

        # Create Mock Repo B: payment-client-sdk
        self.repo_b = self.base_path / "payment-client-sdk"
        self.repo_b.mkdir(parents=True)
        (self.repo_b / "src").mkdir()
        (self.repo_b / "src" / "client.py").write_text(
            '''
import requests

class PaymentClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url

    def charge(self, amount, currency):
        url = f"{self.base_url}/v1/charge"
        return requests.post(url, json={"amount_cents": amount, "currency": currency})
''',
            encoding="utf-8"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_repositories_builds_graph(self):
        graph = CrossRepoScanner.scan_repositories([str(self.repo_a), str(self.repo_b)])

        self.assertIn("repo:payment-provider", graph.nodes)
        self.assertIn("repo:payment-client-sdk", graph.nodes)

        # Check endpoints detected
        endpoint_nodes = [n for n in graph.nodes.values() if n.type == NodeType.ENDPOINT]
        endpoint_names = [n.name for n in endpoint_nodes]
        self.assertTrue(any("POST /v1/charge" in name for name in endpoint_names))
        self.assertTrue(any("GET /v1/health" in name for name in endpoint_names))

        # Check schemas detected
        schema_nodes = [n for n in graph.nodes.values() if n.type == NodeType.SCHEMA]
        schema_names = [n.name for n in schema_nodes]
        self.assertIn("ChargePayload", schema_names)

        # Check cross-repo link detected between client.py and /v1/charge
        cross_edges = graph.find_cross_repo_edges()
        self.assertTrue(len(cross_edges) >= 1)
        self.assertTrue(any(e.type == EdgeType.CALLS for e in cross_edges))

    def test_impact_radius_calculation(self):
        graph = CrossRepoScanner.scan_repositories([str(self.repo_a), str(self.repo_b)])
        impact = graph.get_impact_radius("/v1/charge")

        self.assertIn("payment-provider", impact["affected_repositories"])
        self.assertIn("payment-client-sdk", impact["affected_repositories"])
        self.assertTrue(len(impact["affected_files"]) >= 2)
        self.assertIn("POST /v1/charge", impact["affected_endpoints"])
        # Provider should be sequenced before client
        self.assertEqual(impact["recommended_sprint_sequence"][0], "payment-provider")
        self.assertEqual(impact["recommended_sprint_sequence"][1], "payment-client-sdk")

    def test_reposwarm_arch_md_ingestion(self):
        # Create a RepoSwarm .arch.md file
        arch_content = """# Architecture Overview
## Service: order-service
Type: Backend Microservice

## Endpoints
- GET /v1/orders
- POST /v1/orders/create

## Dependencies
- Calls: payment-provider /v1/charge
"""
        (self.repo_a / "order-service.arch.md").write_text(arch_content, encoding="utf-8")

        graph = CrossRepoScanner.scan_repositories([str(self.repo_a)])
        arch_nodes = [n for n in graph.nodes.values() if n.type == NodeType.CONTRACT]
        self.assertTrue(len(arch_nodes) >= 1)

        endpoints = [n.name for n in graph.nodes.values() if n.type == NodeType.ENDPOINT]
        self.assertTrue(any("POST /v1/orders/create" in e for e in endpoints))

        # Also test contracts.py parse_skill_contract with .arch.md
        contract = parse_skill_contract(str(self.repo_a))
        self.assertIsNotNone(contract)
        self.assertIn("POST /v1/orders/create", contract.raw_content)

    def test_mermaid_and_prompt_generation(self):
        graph = CrossRepoScanner.scan_repositories([str(self.repo_a), str(self.repo_b)])
        mermaid = graph.to_mermaid()
        self.assertTrue(mermaid.startswith("flowchart TD"))
        self.assertIn("payment_provider", mermaid)
        self.assertIn("payment_client_sdk", mermaid)

        prompt_summary = graph.to_subgraph_prompt("/v1/charge")
        self.assertIn("Cross-Repository Knowledge Graph", prompt_summary)
        self.assertIn("Impact Radius", prompt_summary)
        self.assertIn("payment-provider", prompt_summary)

    def test_graph_serialization(self):
        graph = CrossRepoScanner.scan_repositories([str(self.repo_a), str(self.repo_b)])
        save_path = self.base_path / "graph.json"
        graph.save(str(save_path))
        self.assertTrue(save_path.exists())

        loaded = CrossRepoKnowledgeGraph.load(str(save_path))
        self.assertEqual(len(loaded.nodes), len(graph.nodes))
        self.assertEqual(len(loaded.edges), len(graph.edges))


if __name__ == "__main__":
    unittest.main()

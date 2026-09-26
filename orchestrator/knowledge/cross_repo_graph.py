"""
ASCM Cross-Repository Knowledge Graph Engine.
Constructs a unified, local-first directed graph connecting endpoints, schemas,
modules, and callers across multiple repositories in a sprint.
Natively ingests RepoSwarm (.arch.md) files and ASCM (SKILLS.md) contracts.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import re
import json
from typing import Dict, List, Set, Optional, Any, Tuple


class NodeType(str, Enum):
    REPOSITORY = "repository"
    FILE = "file"
    ENDPOINT = "endpoint"
    SCHEMA = "schema"
    FUNCTION = "function"
    CONTRACT = "contract"


class EdgeType(str, Enum):
    CONTAINS = "CONTAINS"       # repo -> file, file -> function
    EXPOSES = "EXPOSES"         # file/func -> endpoint (e.g. POST /v1/charge)
    CALLS = "CALLS"             # file/func -> endpoint
    DEFINES = "DEFINES"         # file -> schema (model, struct, interface)
    CONSUMES = "CONSUMES"       # file/func/endpoint -> schema
    IMPORTS = "IMPORTS"         # file -> file/module
    DEPENDS_ON = "DEPENDS_ON"   # repo -> repo, file -> file


@dataclass
class GraphNode:
    id: str
    name: str
    type: str  # NodeType value
    repo: str
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str  # EdgeType value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CrossRepoKnowledgeGraph:
    """
    In-memory, local-first directed graph tracking cross-repo dependencies,
    API routes, schemas, and impact radii without requiring external databases.
    """

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self._adj: Dict[str, List[GraphEdge]] = {}
        self._rev_adj: Dict[str, List[GraphEdge]] = {}

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self._adj:
            self._adj[node.id] = []
        if node.id not in self._rev_adj:
            self._rev_adj[node.id] = []

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.source not in self.nodes or edge.target not in self.nodes:
            # Ensure placeholder nodes exist if omitted
            if edge.source not in self.nodes:
                self.add_node(GraphNode(id=edge.source, name=edge.source, type=NodeType.FILE, repo="external"))
            if edge.target not in self.nodes:
                self.add_node(GraphNode(id=edge.target, name=edge.target, type=NodeType.ENDPOINT, repo="external"))
        self.edges.append(edge)
        self._adj.setdefault(edge.source, []).append(edge)
        self._rev_adj.setdefault(edge.target, []).append(edge)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes.get(node_id)

    def get_outgoing(self, node_id: str) -> List[GraphEdge]:
        return self._adj.get(node_id, [])

    def get_incoming(self, node_id: str) -> List[GraphEdge]:
        return self._rev_adj.get(node_id, [])

    def find_cross_repo_edges(self) -> List[GraphEdge]:
        """Returns all edges that span across two different repositories."""
        cross = []
        for e in self.edges:
            src_node = self.nodes.get(e.source)
            tgt_node = self.nodes.get(e.target)
            if src_node and tgt_node and src_node.repo != tgt_node.repo and src_node.repo != "external" and tgt_node.repo != "external":
                cross.append(e)
        return cross

    def get_impact_radius(self, target_node_or_path: str, max_depth: int = 4) -> Dict[str, Any]:
        """
        Calculates the cross-repository impact radius when a file, endpoint, or schema changes.
        Traces callers, consumers, and dependencies transitively.
        """
        # Find matching initial nodes
        start_nodes = set()
        for nid, node in self.nodes.items():
            if target_node_or_path in nid or (node.file_path and target_node_or_path in node.file_path):
                start_nodes.add(nid)

        if not start_nodes and target_node_or_path in self.nodes:
            start_nodes.add(target_node_or_path)

        visited_nodes: Set[str] = set(start_nodes)
        visited_edges: List[GraphEdge] = []
        queue = list(start_nodes)
        depth_map: Dict[str, int] = {nid: 0 for nid in start_nodes}

        while queue:
            curr = queue.pop(0)
            curr_depth = depth_map.get(curr, 0)
            if curr_depth >= max_depth:
                continue

            # Check incoming callers/consumers (who relies on this?)
            for edge in self.get_incoming(curr):
                visited_edges.append(edge)
                src = edge.source
                if src not in visited_nodes:
                    visited_nodes.add(src)
                    depth_map[src] = curr_depth + 1
                    queue.append(src)

            # Check outgoing (what does this directly change?)
            for edge in self.get_outgoing(curr):
                if edge.type in [EdgeType.EXPOSES, EdgeType.DEFINES, EdgeType.CALLS]:
                    visited_edges.append(edge)
                    tgt = edge.target
                    if tgt not in visited_nodes:
                        visited_nodes.add(tgt)
                        depth_map[tgt] = curr_depth + 1
                        queue.append(tgt)

        affected_repos = set()
        affected_files = set()
        affected_endpoints = []
        affected_schemas = []

        for nid in visited_nodes:
            node = self.nodes.get(nid)
            if not node:
                continue
            if node.repo and node.repo != "external":
                affected_repos.add(node.repo)
            if node.file_path and node.type in [NodeType.FILE, NodeType.CONTRACT]:
                affected_files.add(f"{node.repo}/{node.file_path}" if node.repo else node.file_path)
            if node.type == NodeType.ENDPOINT:
                affected_endpoints.append(node.name)
            elif node.type == NodeType.SCHEMA:
                affected_schemas.append(node.name)

        # Determine topological execution order (providers first, consumers second)
        repo_order = list(affected_repos)
        # Place provider repo (who exposes endpoints) before consumer repo
        cross_edges = [e for e in visited_edges if self.nodes[e.source].repo != self.nodes[e.target].repo]
        if cross_edges:
            for ce in cross_edges:
                caller_repo = self.nodes[ce.source].repo
                provider_repo = self.nodes[ce.target].repo
                if provider_repo in repo_order and caller_repo in repo_order:
                    p_idx = repo_order.index(provider_repo)
                    c_idx = repo_order.index(caller_repo)
                    if p_idx > c_idx:
                        # Swap so provider is modified before caller
                        repo_order[c_idx], repo_order[p_idx] = repo_order[p_idx], repo_order[c_idx]

        return {
            "query": target_node_or_path,
            "impacted_node_count": len(visited_nodes),
            "affected_repositories": repo_order,
            "affected_files": sorted(list(affected_files)),
            "affected_endpoints": sorted(list(set(affected_endpoints))),
            "affected_schemas": sorted(list(set(affected_schemas))),
            "cross_repo_links_broken_or_updated": len([e for e in visited_edges if self.nodes[e.source].repo != self.nodes[e.target].repo]),
            "recommended_sprint_sequence": repo_order
        }

    def to_subgraph_prompt(self, target_query: Optional[str] = None, max_items: int = 25) -> str:
        """
        Formats a compact, high-signal architectural summary of the knowledge graph
        suitable for feeding directly into LLM prompts without blowing token budgets.
        """
        cross_edges = self.find_cross_repo_edges()
        lines = [
            "### Cross-Repository Knowledge Graph",
            f"- Total Indexed Entities: {len(self.nodes)} ({len([n for n in self.nodes.values() if n.type == NodeType.ENDPOINT])} endpoints, {len([n for n in self.nodes.values() if n.type == NodeType.SCHEMA])} schemas)",
            f"- Active Cross-Repo Dependencies: {len(cross_edges)}"
        ]

        if cross_edges:
            lines.append("\n**Cross-Service Interface Links:**")
            for e in cross_edges[:max_items]:
                src = self.nodes.get(e.source)
                tgt = self.nodes.get(e.target)
                if src and tgt:
                    lines.append(f"- `[{src.repo}] {src.name}` --{e.type}--> `[{tgt.repo}] {tgt.name}`")

        # Add endpoints list
        endpoints = [n for n in self.nodes.values() if n.type == NodeType.ENDPOINT][:max_items]
        if endpoints:
            lines.append("\n**Exposed Service Routes:**")
            for ep in endpoints:
                lines.append(f"- `[{ep.repo}]` {ep.name} (defined in `{ep.file_path}`)")

        # Add schemas list
        schemas = [n for n in self.nodes.values() if n.type == NodeType.SCHEMA][:max_items]
        if schemas:
            lines.append("\n**Shared Data Schemas:**")
            for sc in schemas:
                lines.append(f"- `[{sc.repo}]` `{sc.name}` (defined in `{sc.file_path}`)")

        if target_query:
            impact = self.get_impact_radius(target_query)
            lines.append(f"\n**Impact Radius for '{target_query}':**")
            lines.append(f"- Affects {len(impact['affected_files'])} files across {len(impact['affected_repositories'])} repos: {', '.join(impact['affected_repositories'])}")
            lines.append(f"- Execution order: {' -> '.join(impact['recommended_sprint_sequence'])}")

        return "\n".join(lines)

    def to_mermaid(self) -> str:
        """Renders the cross-repository graph as a Mermaid flowchart diagram."""
        lines = ["flowchart TD"]
        # Group by repository
        repos: Dict[str, List[GraphNode]] = {}
        for node in self.nodes.values():
            if node.repo != "external":
                repos.setdefault(node.repo, []).append(node)

        for repo, nodes in repos.items():
            safe_repo = re.sub(r"[^a-zA-Z0-9_]", "_", repo)
            lines.append(f"  subgraph {safe_repo} [{repo}]")
            for n in nodes:
                safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", n.id)
                safe_name = n.name.replace('"', '\\"')
                if n.type == NodeType.ENDPOINT:
                    lines.append(f'    {safe_id}(["{safe_name}"])')
                elif n.type == NodeType.SCHEMA:
                    lines.append(f'    {safe_id}[["{safe_name}"]]')
                else:
                    lines.append(f'    {safe_id}["{safe_name}"]')
            lines.append("  end")

        for e in self.edges:
            src_node = self.nodes.get(e.source)
            tgt_node = self.nodes.get(e.target)
            if src_node and tgt_node:
                s_id = re.sub(r"[^a-zA-Z0-9_]", "_", e.source)
                t_id = re.sub(r"[^a-zA-Z0-9_]", "_", e.target)
                lines.append(f"  {s_id} -->|{e.type}| {t_id}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrossRepoKnowledgeGraph":
        graph = cls()
        for nd in data.get("nodes", []):
            graph.add_node(GraphNode(**nd))
        for ed in data.get("edges", []):
            graph.add_edge(GraphEdge(**ed))
        return graph

    def save(self, file_path: str) -> None:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, file_path: str) -> "CrossRepoKnowledgeGraph":
        p = Path(file_path)
        if not p.exists():
            return cls()
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))


class CrossRepoScanner:
    """
    Static analyzer that parses input repositories and builds the CrossRepoKnowledgeGraph.
    Inspects Python, Go, TypeScript/JS, RepoSwarm (.arch.md), and ASCM (SKILLS.md).
    """

    ROUTE_REGEXES = [
        # Python (FastAPI / Flask)
        re.compile(r"""@(app|router|blueprint|bp)\.(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
        re.compile(r"""@(app|router|api)\.route\s*\(\s*["']([^"']+)["'](?:.*?methods\s*=\s*\[["']([^"']+)["'])?""", re.IGNORECASE),
        # Go (Gin, Chi, net/http)
        re.compile(r"""(r|router|api|v1|engine)\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
        re.compile(r"""http\.HandleFunc\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
        # Node/Express/TS
        re.compile(r"""(app|router)\.(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
        # Python standard library http.server / dispatchers
        re.compile(r"""self\.path\s*==\s*["']([^"']+)["']""", re.IGNORECASE),
        re.compile(r"""self\.path\s*in\s*\(([^)]+)\)""", re.IGNORECASE),
    ]

    OUTGOING_CALL_REGEXES = [
        # Python requests / httpx / aiohttp
        re.compile(r"""(?:requests|client|httpx|session)\.(get|post|put|delete)\s*\(\s*f?["']([^"']+)["']""", re.IGNORECASE),
        # Go http client
        re.compile(r"""http\.(?:Post|Get|NewRequest)\s*\(\s*(?:["'](POST|GET)["']\s*,\s*)?["']([^"']+)["']""", re.IGNORECASE),
        # JS / TS fetch / axios (supports template literal backticks)
        re.compile(r"""(?:fetch|axios\.get|axios\.post)\s*\(\s*[`'"]([^`'"]+)[`'"]""", re.IGNORECASE),
        # Variable assignments with endpoint paths (e.g. url = f".../v1/charge")
        re.compile(r"""(?:url|path|endpoint|route|uri|target)\s*=\s*f?[`'"]([^`'"]*(?:/v[0-9]|/api|/webhook|/orders|/charge|/health)[^`'"]*)[`'"]""", re.IGNORECASE),
        # String literals or template strings matching route patterns
        re.compile(r"""f?[`'"](https?://[^`'"]*(?:/[a-zA-Z0-9_\-]+)+|/(?:v[0-9]|api|webhook|orders|charge|health)[a-zA-Z0-9_\-/]*)[`'"]""", re.IGNORECASE),
    ]

    SCHEMA_REGEXES = [
        # Python Pydantic / dataclasses
        re.compile(r"""class\s+([A-Za-z0-9_]+)\s*\((?:BaseModel|dict|TypedDict|object)?\):"""),
        # Go structs
        re.compile(r"""type\s+([A-Za-z0-9_]+)\s+struct\s*\{"""),
        re.compile(r"""type\s+([A-Za-z0-9_]+)\s+interface\s*\{"""),
        # TypeScript interfaces / types
        re.compile(r"""export\s+interface\s+([A-Za-z0-9_]+)\s*\{"""),
        re.compile(r"""export\s+type\s+([A-Za-z0-9_]+)\s*="""),
    ]

    @classmethod
    def scan_repositories(cls, repo_paths: List[str]) -> CrossRepoKnowledgeGraph:
        """
        Scans all supplied repositories and constructs a unified CrossRepoKnowledgeGraph.
        """
        graph = CrossRepoKnowledgeGraph()

        for repo_str in repo_paths:
            repo_path = Path(repo_str).resolve()
            if not repo_path.exists():
                continue

            repo_name = repo_path.name
            repo_node = GraphNode(
                id=f"repo:{repo_name}",
                name=repo_name,
                type=NodeType.REPOSITORY,
                repo=repo_name,
                file_path=str(repo_path)
            )
            graph.add_node(repo_node)

            # 1. Check for RepoSwarm .arch.md standard files
            cls._scan_reposwarm_arch(repo_path, repo_name, graph)

            # 2. Check for ASCM SKILLS.md / SKILL.md
            cls._scan_ascm_skills(repo_path, repo_name, graph)

            # 3. Source code file walk
            cls._scan_source_tree(repo_path, repo_name, graph)

        # 4. Resolve cross-repository edges (connecting outgoing client calls to exposed endpoints)
        cls._resolve_cross_repo_edges(graph)

        return graph

    @classmethod
    def _scan_reposwarm_arch(cls, repo_path: Path, repo_name: str, graph: CrossRepoKnowledgeGraph) -> None:
        """Extracts architectural entities from RepoSwarm's standardized .arch.md files."""
        arch_candidates = list(repo_path.glob("*.arch.md")) + list(repo_path.glob(".arch.md"))
        if (repo_path / "docs").exists():
            arch_candidates.extend((repo_path / "docs").glob("*.arch.md"))

        for arch_file in arch_candidates:
            try:
                content = arch_file.read_text(encoding="utf-8")
                rel_path = str(arch_file.relative_to(repo_path))
                contract_node = GraphNode(
                    id=f"arch_doc:{repo_name}:{rel_path}",
                    name=f"RepoSwarm Arch ({arch_file.name})",
                    type=NodeType.CONTRACT,
                    repo=repo_name,
                    file_path=rel_path,
                    metadata={"source": "reposwarm", "format": "arch.md"}
                )
                graph.add_node(contract_node)
                graph.add_edge(GraphEdge(source=f"repo:{repo_name}", target=contract_node.id, type=EdgeType.CONTAINS))

                # Extract endpoints mentioned in arch doc
                for line in content.splitlines():
                    route_match = re.search(r"(GET|POST|PUT|DELETE)\s+([/a-zA-Z0-9_\-{}]+)", line, re.IGNORECASE)
                    if route_match:
                        method, path = route_match.group(1).upper(), route_match.group(2)
                        ep_name = f"{method} {path}"
                        ep_id = f"endpoint:{repo_name}:{ep_name}"
                        graph.add_node(GraphNode(
                            id=ep_id,
                            name=ep_name,
                            type=NodeType.ENDPOINT,
                            repo=repo_name,
                            file_path=rel_path,
                            metadata={"method": method, "path": path, "verified_by": "reposwarm"}
                        ))
                        graph.add_edge(GraphEdge(source=contract_node.id, target=ep_id, type=EdgeType.EXPOSES))
            except Exception:
                pass

    @classmethod
    def _scan_ascm_skills(cls, repo_path: Path, repo_name: str, graph: CrossRepoKnowledgeGraph) -> None:
        """Extracts allowed paths and contracts from ASCM SKILLS.md."""
        for name in ["SKILLS.md", "SKILL.md"]:
            skill_file = repo_path / name
            if skill_file.exists():
                try:
                    content = skill_file.read_text(encoding="utf-8")
                    rel_path = str(skill_file.relative_to(repo_path))
                    contract_node = GraphNode(
                        id=f"contract:{repo_name}:{rel_path}",
                        name=f"ASCM Contract ({name})",
                        type=NodeType.CONTRACT,
                        repo=repo_name,
                        file_path=rel_path,
                        metadata={"source": "ascm"}
                    )
                    graph.add_node(contract_node)
                    graph.add_edge(GraphEdge(source=f"repo:{repo_name}", target=contract_node.id, type=EdgeType.CONTAINS))
                except Exception:
                    pass

    @classmethod
    def _scan_source_tree(cls, repo_path: Path, repo_name: str, graph: CrossRepoKnowledgeGraph) -> None:
        """Walks source files (.py, .go, .ts, .js) and extracts routes, schemas, and calls."""
        valid_exts = {".py", ".go", ".ts", ".js", ".tsx", ".jsx"}
        ignore_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}

        for p in repo_path.rglob("*"):
            if not p.is_file() or p.suffix not in valid_exts:
                continue
            if any(part in ignore_dirs for part in p.parts):
                continue

            try:
                rel_path = str(p.relative_to(repo_path))
                file_id = f"file:{repo_name}:{rel_path}"
                file_node = GraphNode(
                    id=file_id,
                    name=p.name,
                    type=NodeType.FILE,
                    repo=repo_name,
                    file_path=rel_path
                )
                graph.add_node(file_node)
                graph.add_edge(GraphEdge(source=f"repo:{repo_name}", target=file_id, type=EdgeType.CONTAINS))

                code = p.read_text(encoding="utf-8", errors="ignore")

                # Scan Exposed Routes
                for rx in cls.ROUTE_REGEXES:
                    for m in rx.finditer(code):
                        groups = [g for g in m.groups() if g]
                        method = "ROUTE"
                        raw_path = "/"
                        if len(groups) >= 2:
                            if groups[1].upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                                method = groups[1].upper()
                            raw_path = groups[-1]
                        elif len(groups) == 1:
                            raw_path = groups[0]

                        # Check if multiple paths in tuple e.g. ("/healthz", "/api/v1/health")
                        path_list = [p_str.strip().strip("'\"") for p_str in raw_path.split(",")] if "," in raw_path else [raw_path.strip().strip("'\"")]
                        for path in path_list:
                            if not path.startswith("/"):
                                continue
                            ep_name = f"{method} {path}" if method != "ROUTE" else path
                            ep_id = f"endpoint:{repo_name}:{ep_name}"
                            graph.add_node(GraphNode(
                                id=ep_id,
                                name=ep_name,
                                type=NodeType.ENDPOINT,
                                repo=repo_name,
                                file_path=rel_path,
                                metadata={"method": method, "path": path}
                            ))
                            graph.add_edge(GraphEdge(source=file_id, target=ep_id, type=EdgeType.EXPOSES))

                # Scan Schemas
                for rx in cls.SCHEMA_REGEXES:
                    for m in rx.finditer(code):
                        schema_name = m.group(1)
                        if schema_name in ["dict", "object", "BaseModel", "Exception", "TestCase"]:
                            continue
                        sch_id = f"schema:{repo_name}:{schema_name}"
                        graph.add_node(GraphNode(
                            id=sch_id,
                            name=schema_name,
                            type=NodeType.SCHEMA,
                            repo=repo_name,
                            file_path=rel_path
                        ))
                        graph.add_edge(GraphEdge(source=file_id, target=sch_id, type=EdgeType.DEFINES))

                # Scan Outgoing Calls
                for rx in cls.OUTGOING_CALL_REGEXES:
                    for m in rx.finditer(code):
                        groups = [g for g in m.groups() if g]
                        call_target = groups[-1]
                        func_node_id = f"call:{repo_name}:{rel_path}:{call_target}"
                        graph.add_node(GraphNode(
                            id=func_node_id,
                            name=f"Call to {call_target}",
                            type=NodeType.FUNCTION,
                            repo=repo_name,
                            file_path=rel_path,
                            metadata={"target_uri": call_target}
                        ))
                        graph.add_edge(GraphEdge(source=file_id, target=func_node_id, type=EdgeType.CALLS))

            except Exception:
                continue

    @classmethod
    def _resolve_cross_repo_edges(cls, graph: CrossRepoKnowledgeGraph) -> None:
        """
        Correlates outgoing HTTP client calls and schema references across repository boundaries.
        e.g., if Repo B has a client call targeting '/v1/checkout' and Repo A exposes 'POST /v1/checkout',
        links them with a cross-repo CALLS edge.
        """
        endpoints = [n for n in graph.nodes.values() if n.type == NodeType.ENDPOINT]
        call_nodes = [n for n in graph.nodes.values() if n.id.startswith("call:")]

        for caller in call_nodes:
            target_uri = caller.metadata.get("target_uri", "")
            for ep in endpoints:
                if ep.repo == caller.repo:
                    continue  # Only cross-repo links

                ep_path = ep.metadata.get("path", "")
                if ep_path and (ep_path in target_uri or target_uri.rstrip("/") == ep_path.rstrip("/") or ep_path.lstrip("/") in target_uri):
                    # Found cross-repo link!
                    graph.add_edge(GraphEdge(
                        source=caller.id,
                        target=ep.id,
                        type=EdgeType.CALLS,
                        metadata={"cross_repo": True, "source_repo": caller.repo, "target_repo": ep.repo}
                    ))
                    # Also link caller file to endpoint directly
                    if caller.file_path:
                        src_file = f"file:{caller.repo}:{caller.file_path}"
                        if src_file in graph.nodes:
                            graph.add_edge(GraphEdge(
                                source=src_file,
                                target=ep.id,
                                type=EdgeType.CALLS,
                                metadata={"cross_repo": True}
                            ))

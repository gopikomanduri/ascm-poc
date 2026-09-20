import re
from pathlib import Path, PurePosixPath

import yaml

from orchestrator.state import RepoContract


def parse_skill_contract(repo_path: str) -> RepoContract:
    """Read a repository contract and extract its editable-path allowlist."""
    repo = Path(repo_path).resolve()
    skill_file = repo / "SKILL.md"
    if not skill_file.exists():
        skill_file = repo / "SKILLS.md"
    if not skill_file.exists():
        return RepoContract(repo_path=str(repo), name=repo.name)

    raw = skill_file.read_text(encoding="utf-8")
    metadata = _parse_frontmatter(raw)
    allowed_paths = metadata.get("allowed_paths", [])
    if not allowed_paths:
        allowed_paths = _parse_markdown_allowlist(raw)

    return RepoContract(
        repo_path=str(repo),
        name=metadata.get("name", repo.name),
        role=metadata.get("role", "unaffected"),
        allowed_paths=_normalize_paths(allowed_paths, repo.name),
        raw_content=raw,
    )


def _parse_frontmatter(raw: str) -> dict:
    if not raw.startswith("---"):
        return {}
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def _parse_markdown_allowlist(raw: str) -> list[str]:
    match = re.search(
        r"(?:^|\n)##?\s+File Path Allowlist.*?```(?:text)?\s*\n(.*?)```",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


def _normalize_paths(paths: list[str], repository_name: str) -> list[str]:
    normalized_paths = []
    for value in paths:
        if not isinstance(value, str):
            continue
        directory = value.rstrip().endswith("/")
        path = PurePosixPath(value.strip())
        parts = path.parts
        if parts and parts[0] == repository_name:
            parts = parts[1:]
        if not parts or path.is_absolute() or ".." in parts:
            continue
        normalized = PurePosixPath(*parts).as_posix()
        normalized_paths.append(f"{normalized}/" if directory else normalized)
    return normalized_paths

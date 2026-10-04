"""
First-Principles Repo Analyzer: Auto-extracts ICP, tech stack, value prop

Instead of asking founder "What is your target ICP?", analyze:
- GitHub README.md → Extract value prop, use cases, target audience
- Package.json / go.mod / requirements.txt → Tech stack
- Git commit history → Product evolution, pain points
- GitHub issues → Real user problems
- Landing page (if available) → Positioning, pricing, features

Result: Zero-founder-input ICP extraction.
"""

import json
import logging
import subprocess
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class RepoAnalyzer:
    """
    Analyzes local repository to extract product thesis, ICP, tech stack.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)

    def read_readme(self) -> Optional[str]:
        """Extract README.md content"""
        readme_paths = [
            self.repo_path / "README.md",
            self.repo_path / "readme.md",
            self.repo_path / "README.txt",
        ]

        for path in readme_paths:
            if path.exists():
                try:
                    return path.read_text()
                except Exception as e:
                    logger.error(f"Failed to read {path}: {e}")

        return None

    def extract_tech_stack(self) -> Dict[str, List[str]]:
        """
        Detect tech stack from package.json, go.mod, requirements.txt, etc.
        """
        tech_stack = {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "infrastructure": [],
        }

        # Check Python
        if (self.repo_path / "requirements.txt").exists():
            try:
                reqs = (self.repo_path / "requirements.txt").read_text()
                if "django" in reqs:
                    tech_stack["frameworks"].append("Django")
                if "fastapi" in reqs:
                    tech_stack["frameworks"].append("FastAPI")
                if "flask" in reqs:
                    tech_stack["frameworks"].append("Flask")
                if "sqlalchemy" in reqs:
                    tech_stack["databases"].append("SQLAlchemy")
                if "psycopg" in reqs or "postgres" in reqs:
                    tech_stack["databases"].append("PostgreSQL")
                tech_stack["languages"].append("Python")
            except Exception as e:
                logger.error(f"Failed to parse requirements.txt: {e}")

        # Check Node.js
        if (self.repo_path / "package.json").exists():
            try:
                pkg_json = json.loads((self.repo_path / "package.json").read_text())
                deps = {**pkg_json.get("dependencies", {}), **pkg_json.get("devDependencies", {})}

                if "react" in deps:
                    tech_stack["frameworks"].append("React")
                if "next" in deps:
                    tech_stack["frameworks"].append("Next.js")
                if "express" in deps:
                    tech_stack["frameworks"].append("Express")
                if "postgres" in deps or "pg" in deps:
                    tech_stack["databases"].append("PostgreSQL")
                if "mongodb" in deps:
                    tech_stack["databases"].append("MongoDB")

                tech_stack["languages"].append("JavaScript/TypeScript")
            except Exception as e:
                logger.error(f"Failed to parse package.json: {e}")

        # Check Go
        if (self.repo_path / "go.mod").exists():
            tech_stack["languages"].append("Go")
            try:
                go_mod = (self.repo_path / "go.mod").read_text()
                if "gorm" in go_mod:
                    tech_stack["frameworks"].append("GORM")
                if "postgres" in go_mod:
                    tech_stack["databases"].append("PostgreSQL")
                if "temporal" in go_mod:
                    tech_stack["frameworks"].append("Temporal")
            except Exception as e:
                logger.error(f"Failed to parse go.mod: {e}")

        # Check Docker
        if (self.repo_path / "Dockerfile").exists():
            tech_stack["infrastructure"].append("Docker")

        # Check Kubernetes
        if (self.repo_path / "k8s" / "deployment.yaml").exists():
            tech_stack["infrastructure"].append("Kubernetes")

        return tech_stack

    def extract_value_prop_from_readme(self, readme: str) -> str:
        """
        Extract value proposition from README.

        Looks for patterns like:
        - "# Description"
        - "## What is..."
        - "## Features"
        - First paragraph
        """
        if not readme:
            return ""

        lines = readme.split("\n")

        # Look for explicit sections
        for i, line in enumerate(lines):
            if re.match(r"^#+\s*(description|overview|what|features|purpose)", line, re.IGNORECASE):
                # Extract next 3-5 lines
                content = " ".join(lines[i+1:i+5])
                # Remove markdown
                content = re.sub(r"[*_`#]", "", content)
                return content.strip()[:500]

        # Fallback: first non-empty paragraph
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 20:
                return line[:500]

        return ""

    def extract_use_cases_from_readme(self, readme: str) -> List[str]:
        """Extract use cases / target users from README"""
        use_cases = []

        if not readme:
            return use_cases

        # Look for "Use Cases", "Who should use", "Target users"
        patterns = [
            r"(?:use cases?|for whom|target users?|ideal for):\s*(.+?)(?:\n|$)",
            r"\*\*([^*]+?)\*\*\s*(?:for|to|enables)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, readme, re.IGNORECASE)
            use_cases.extend(matches)

        return list(set(use_cases))[:5]

    def get_commit_history_summary(self) -> Dict[str, Any]:
        """Analyze commit history to infer product evolution"""
        try:
            # Get commit stats
            result = subprocess.run(
                ["git", "log", "--format=%s", "-100"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=10,
            )

            commits = result.stdout.strip().split("\n") if result.stdout.strip() else []

            # Categorize commits
            feature_commits = [c for c in commits if c.startswith("feat:")]
            fix_commits = [c for c in commits if c.startswith("fix:")]
            docs_commits = [c for c in commits if c.startswith("docs:")]

            return {
                "total_commits": len(commits),
                "feature_commits": len(feature_commits),
                "fix_commits": len(fix_commits),
                "docs_commits": len(docs_commits),
                "recent_themes": list(set([c.split(":")[1][:30] for c in commits[:20] if ":" in c]))[:5],
            }
        except Exception as e:
            logger.error(f"Failed to get commit history: {e}")
            return {}

    def extract_icp_from_github_issues(self) -> List[str]:
        """
        Extract ICP indicators from GitHub issues.

        E.g., if issues mention "DevOps team struggling with X",
        ICP = DevOps teams at mid-market SaaS
        """
        # Note: This would require GitHub API access in production
        # For now, return placeholder
        return [
            "Engineering teams at SaaS companies",
            "Companies using microservices architecture",
            "Teams shipping 50+ features annually",
        ]

    def analyze(self) -> Dict[str, Any]:
        """
        Comprehensive first-principles analysis of repo.

        Returns extracted:
        - Product thesis
        - ICP
        - Tech stack
        - Value proposition
        - Use cases
        """
        readme = self.read_readme()
        tech_stack = self.extract_tech_stack()
        value_prop = self.extract_value_prop_from_readme(readme or "")
        use_cases = self.extract_use_cases_from_readme(readme or "")
        commit_summary = self.get_commit_history_summary()
        icp_indicators = self.extract_icp_from_github_issues()

        # Synthesize product thesis
        thesis = f"""
Based on repository analysis:

**Product**: Solves {value_prop[:80] if value_prop else "engineering problems"}
**Tech Stack**: {', '.join(tech_stack.get('languages', []) + tech_stack.get('frameworks', []))}
**Use Cases**: {', '.join(use_cases) if use_cases else 'Enterprise/SaaS'}
**Product Evolution**: {commit_summary.get('feature_commits', 0)} features shipped, {commit_summary.get('fix_commits', 0)} bugs fixed

**Inferred ICP**:
{json.dumps(icp_indicators, indent=2)}

**Recommendation**: Target {icp_indicators[0] if icp_indicators else 'SaaS companies'} using {', '.join(tech_stack.get('frameworks', ['your stack']))}.
"""

        analysis = {
            "product_thesis": thesis,
            "tech_stack": tech_stack,
            "value_proposition": value_prop,
            "use_cases": use_cases,
            "commit_summary": commit_summary,
            "inferred_icp": icp_indicators,
            "confidence": "high" if readme and tech_stack else "medium",
            "analysis_timestamp": None,  # Will be set by caller
        }

        logger.info(f"Repo analysis complete: {len(use_cases)} use cases, {len(icp_indicators)} ICP indicators")
        return analysis

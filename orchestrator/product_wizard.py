import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml

from orchestrator.contracts import parse_skill_contract
from orchestrator.security.audit_logger import AUDIT_LOGGER


class RepoAnalyzer:
    """
    Analyzes local repositories or target project directories to discover SKILLS.md,
    inspect file allowlists, detect programming languages, and support automated
    scaffolding or interactive grilling when contracts are absent.
    """

    SUPPORTED_EXTENSIONS = {
        ".go": "Go",
        ".py": "Python",
        ".ts": "TypeScript",
        ".js": "JavaScript",
        ".java": "Java",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
    }

    @classmethod
    def analyze_repo(cls, repo_path_str: str, custom_skills_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Inspects the repo at repo_path_str.
        Returns details on SKILLS.md existence, allowlist paths, languages, and file stats.
        """
        repo_path = Path(repo_path_str).resolve()
        if not repo_path.exists() or not repo_path.is_dir():
            return {
                "status": "error",
                "message": f"Repository directory not found at: {repo_path_str}",
                "exists": False,
            }

        # 1. Search for SKILLS.md / SKILL.md
        found_skills = False
        resolved_skills_file: Optional[Path] = None

        candidate_paths = []
        if custom_skills_path:
            candidate_paths.append(repo_path / custom_skills_path.strip().lstrip("/"))
        
        # Standard locations
        candidate_paths.extend([
            repo_path / "SKILLS.md",
            repo_path / "SKILL.md",
            repo_path / ".agents" / "skills" / "SKILLS.md",
            repo_path / "skills" / "SKILLS.md",
            repo_path / "docs" / "SKILLS.md",
        ])

        for cand in candidate_paths:
            if cand.exists() and cand.is_file():
                found_skills = True
                resolved_skills_file = cand
                break

        # 2. Extract Contract if found
        allowed_paths: List[str] = []
        contract_role = "unspecified"
        contract_name = repo_path.name

        if found_skills and resolved_skills_file:
            try:
                contract = parse_skill_contract(str(repo_path))
                allowed_paths = contract.allowed_paths
                contract_role = contract.role
                contract_name = contract.name
            except Exception as e:
                AUDIT_LOGGER.log_security_event("SKILLS_PARSE_WARNING", {"error": str(e)}, severity="WARN")

        # 3. Detect languages and file counts
        languages: Dict[str, int] = {}
        total_files = 0
        file_samples: List[str] = []

        try:
            for root, dirs, files in os.walk(repo_path):
                # Ignore hidden dirs, node_modules, .git, venv
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "vendor", "__pycache__", "venv", ".venv")]
                for f in files:
                    if f.startswith("."):
                        continue
                    total_files += 1
                    ext = os.path.splitext(f)[1].lower()
                    if ext in cls.SUPPORTED_EXTENSIONS:
                        lang = cls.SUPPORTED_EXTENSIONS[ext]
                        languages[lang] = languages.get(lang, 0) + 1
                    rel = str(Path(root, f).relative_to(repo_path))
                    if len(file_samples) < 15:
                        file_samples.append(rel)
        except OSError:
            pass

        sorted_languages = sorted(languages.items(), key=lambda kv: kv[1], reverse=True)
        detected_langs = [k for k, _ in sorted_languages]

        rel_skills_path = str(resolved_skills_file.relative_to(repo_path)) if resolved_skills_file else None

        return {
            "status": "ok",
            "exists": True,
            "repo_path": str(repo_path),
            "repo_name": contract_name,
            "found_skills": found_skills,
            "skills_path": rel_skills_path,
            "contract_role": contract_role,
            "allowed_paths": allowed_paths,
            "total_files": total_files,
            "languages": detected_langs,
            "primary_language": detected_langs[0] if detected_langs else "Unknown",
            "file_samples": file_samples,
            "needs_skills_creation": not found_skills,
        }

    @classmethod
    def scaffold_skills_md(
        cls,
        repo_path_str: str,
        role: str = "provider",
        allowed_paths: Optional[List[str]] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Creates a new, validated SKILLS.md contract in the target repository.
        """
        repo_path = Path(repo_path_str).resolve()
        if not repo_path.exists() or not repo_path.is_dir():
            return {"status": "error", "message": f"Target repo path does not exist: {repo_path_str}"}

        target_file = repo_path / "SKILLS.md"
        if target_file.exists():
            return {
                "status": "ok",
                "message": "SKILLS.md already exists.",
                "file_path": str(target_file),
                "created": False,
            }

        if not allowed_paths:
            # Provide sensible default allowlists based on detected files
            analysis = cls.analyze_repo(repo_path_str)
            samples = analysis.get("file_samples", [])
            allowed_paths = [s for s in samples if not s.startswith("test")][:5]
            if not allowed_paths:
                allowed_paths = ["internal/", "pkg/", "api/"]

        content = f"""---
name: {repo_path.name}
role: {role}
allowed_paths:
{yaml.dump(allowed_paths, default_flow_style=False).strip()}
---

# {repo_path.name} Contract Specification

{description or f"Autonomous Software Construction Machine (ASCM) contract for {repo_path.name}."}

## File Path Allowlist
```text
{"\n".join(allowed_paths)}
```

## Public API & Capabilities
- Provides high-integrity service endpoints and data structures.
- Strict isolation: modifications must remain within the allowed file paths.

## Non-Functional Requirements (NFR)
- Scalability: Low-latency operations without blocking callers.
- Reliability: Hermetic error handling and graceful fallbacks.
- Test Coverage: Unit tests required for all exported functions.
"""
        try:
            target_file.write_text(content.strip() + "\n", encoding="utf-8")
            AUDIT_LOGGER.log_event(
                event_type="SKILLS_MD_SCAFFOLDED",
                agent="ARCHITECT",
                action="CREATE_CONTRACT",
                details={"repo": repo_path.name, "allowed_paths": allowed_paths},
            )
            return {
                "status": "ok",
                "message": f"Successfully created SKILLS.md in {repo_path.name}",
                "file_path": str(target_file),
                "created": True,
                "content": content,
            }
        except OSError as e:
            return {"status": "error", "message": f"Failed to write SKILLS.md: {e}"}

    @classmethod
    def grill_repo_clarifications(cls, answers: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyzes answers to grilling questions when SKILLS.md is absent or unclear.
        Calculates a clarity/confidence score (0-100) and extracts boundaries.
        """
        primary_stack = answers.get("primary_stack", "").strip()
        public_apis = answers.get("public_apis", "").strip()
        protected_paths = answers.get("protected_paths", "").strip()
        enhancement_scope = answers.get("enhancement_scope", "").strip()

        score = 0
        missing_fields = []

        if len(primary_stack) >= 2:
            score += 25
        else:
            missing_fields.append("primary tech stack and entry point")

        if len(public_apis) >= 3:
            score += 25
        else:
            missing_fields.append("existing public APIs and interface contracts")

        if len(protected_paths) >= 2:
            score += 25
        else:
            missing_fields.append("protected/forbidden paths")

        if len(enhancement_scope) >= 5:
            score += 25
        else:
            missing_fields.append("specific enhancement scope or goal")

        # Synthesize allowed paths from answer data
        suggested_paths = []
        for line in public_apis.split(","):
            clean = line.strip().lstrip("/")
            if clean and "/" in clean:
                suggested_paths.append(clean.split("/")[0] + "/")
        if not suggested_paths:
            suggested_paths = ["src/", "internal/", "lib/"]

        summary = (
            f"Repository Stack: {primary_stack or 'Unspecified'}. "
            f"Public Interfaces: {public_apis or 'Unspecified'}. "
            f"Protected Zones: {protected_paths or 'None'}. "
            f"Target Scope: {enhancement_scope or 'General'}"
        )

        ready = score >= 75

        return {
            "status": "ok",
            "clarity_score": score,
            "ready_to_proceed": ready,
            "missing_fields": missing_fields,
            "synthesized_summary": summary,
            "suggested_allowed_paths": suggested_paths,
            "verdict": "CLEAR_TO_BUILD" if ready else "MORE_CLARIFICATIONS_NEEDED",
        }


class AgentRosterAdvisor:
    """
    Intelligently identifies which agents are strictly necessary for a given product
    based on archetype (Greenfield vs Multi-repo vs Enhancement) and domain (Internal tool vs Commercial SaaS).
    """

    ALL_AVAILABLE_AGENTS = [
        {
            "id": "ProductManager",
            "name": "Product Manager Agent",
            "description": "Transforms stakeholder goals into crystal-clear user stories, grills for clarifications, and tracks confidence.",
            "category": "planning",
        },
        {
            "id": "Architect",
            "name": "Software Architect Agent",
            "description": "Formulates HLD/LLD contracts, OpenAPI specs, file allowlists, and cross-repo interface schemas.",
            "category": "planning",
        },
        {
            "id": "BusinessStrategy",
            "name": "Business Strategy Agent",
            "description": "Defines GTM strategy, target user cohorts, competitor comparison matrix, and core value proposition.",
            "category": "strategy",
        },
        {
            "id": "RevenueROI",
            "name": "Revenue & ROI Agent",
            "description": "Calculates engineering hours saved, monthly dollar ROI, SaaS pricing tiers, and onboarding conversion funnels.",
            "category": "strategy",
        },
        {
            "id": "ArchitectureReview",
            "name": "Architecture Review Agent (Critic)",
            "description": "Adversarially audits HLD/LLD against NFR scorecards (Scalability, Security, Latency, Reliability).",
            "category": "governance",
        },
        {
            "id": "Coder",
            "name": "Autonomous Coder Agent",
            "description": "Generates verified, production-ready code patches and comprehensive unit test suites.",
            "category": "execution",
        },
        {
            "id": "CodeReview",
            "name": "Code Review Critic Agent",
            "description": "Multi-model adversarial audit of code quality, OWASP security vulnerabilities, and test coverage rigor.",
            "category": "governance",
        },
        {
            "id": "SecurityAudit",
            "name": "Security Audit & PII Agent",
            "description": "Scrubs PII/API secrets, verifies hermetic sandbox boundaries, and maintains immutable SOC2 audit logs.",
            "category": "governance",
        },
        {
            "id": "Verifier",
            "name": "Sandboxed Verifier Engine",
            "description": "Executes hermetic builds, test suites (Pytest, Go test, Jest), and generates self-healing feedback loops.",
            "category": "execution",
        },
    ]

    @classmethod
    def recommend_agents(
        cls,
        product_archetype: str,
        is_internal: bool = False,
        repo_count: int = 1,
        user_notes: str = "",
    ) -> Dict[str, Any]:
        """
        Returns a customized recommendation for the agent roster.
        """
        # Internal products or developer infrastructure do not need market GTM or consumer ROI
        skip_business = is_internal
        skip_revenue = is_internal

        roster = []
        for agent in cls.ALL_AVAILABLE_AGENTS:
            a_id = agent["id"]
            rec = True
            badge = "Recommended"
            rationale = "Core pipeline participant."

            if a_id == "BusinessStrategy":
                if skip_business:
                    rec = False
                    badge = "Excluded by Default"
                    rationale = "Internal product / tool — GTM marketing and external competitor analysis are not required."
                else:
                    rec = True
                    badge = "Recommended"
                    rationale = "Crucial for consumer/commercial SaaS products to validate market cohorts and value proposition."

            elif a_id == "RevenueROI":
                if skip_revenue:
                    rec = False
                    badge = "Excluded by Default"
                    rationale = "Internal product / tool — SaaS pricing tiers and external customer funnels are not needed."
                else:
                    rec = True
                    badge = "Recommended"
                    rationale = "Provides ROI metrics, developer hours saved, and pricing models for commercial products."

            elif a_id == "ArchitectureReview":
                rec = True
                badge = "Recommended"
                rationale = "Adversarially validates NFRs (Scalability, Security, Latency) across both HLD and LLD."

            elif a_id == "CodeReview":
                rec = True
                badge = "Recommended"
                rationale = "Adversarial multi-model code critique to catch edge cases before verifier execution."

            elif a_id in ("ProductManager", "Architect", "Coder", "SecurityAudit", "Verifier"):
                rec = True
                badge = "Mandatory Core"
                rationale = "Essential for deterministic autonomous software construction."

            roster.append({
                **agent,
                "recommended": rec,
                "badge": badge,
                "rationale": rationale,
            })

        active_count = sum(1 for r in roster if r["recommended"])

        reasoning = (
            f"Configured {active_count} agents for {'an Internal Tool' if is_internal else 'a Commercial Product'} "
            f"({product_archetype.replace('_', ' ').title()}). "
            f"{'Business and Revenue agents were omitted to optimize for internal velocity.' if is_internal else 'Full business, revenue, and engineering squad activated.'}"
        )

        return {
            "status": "ok",
            "product_archetype": product_archetype,
            "is_internal": is_internal,
            "recommended_agents": roster,
            "active_agent_ids": [r["id"] for r in roster if r["recommended"]],
            "reasoning": reasoning,
        }

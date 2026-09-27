"""
Domain Knowledge Engine for ASCM.

Provides:
1. Dynamic Domain Narrowing: Identifies specific and compound domains (e.g., Mutual Funds SLM vs Generic AI/ML vs LegalTech).
2. Local Knowledge Persistence: Discovers, persists, and loads domain-specific primitives and grilling dimensions in '.ascm_domains/'.
3. Laser-Focused Prompt Generation: Eliminates hard-coded cross-domain clutter so agents receive only the domain rules relevant to the user request.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("DomainKnowledgeEngine")

# Root directory for locally stored domain knowledge
DEFAULT_DOMAINS_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".ascm_domains"


class DomainProfile(BaseModel):
    domain_id: str
    display_name: str
    name: Optional[str] = None
    category_summary: str
    primary_language: str = "python"
    core_primitives: List[str] = Field(default_factory=list)
    grilling_dimensions: List[str] = Field(default_factory=list)
    architectural_patterns: List[str] = Field(default_factory=list)
    standard_libraries: Dict[str, List[str]] = Field(default_factory=dict)
    safety_and_nfr_focus: List[str] = Field(default_factory=list)
    competitor_archetypes: List[Dict[str, str]] = Field(default_factory=list)
    preferred_models: Dict[str, str] = Field(default_factory=dict)
    unit_test_frameworks: Dict[str, str] = Field(default_factory=dict)
    role_titles: Dict[str, str] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.name:
            self.name = self.display_name


# Built-in foundational domain catalog
BUILTIN_PROFILES: Dict[str, DomainProfile] = {
    "MUTUAL_FUNDS_WEALTH_SLM": DomainProfile(
        domain_id="mutual_funds_wealth_slm",
        display_name="Mutual Funds, Wealth Management & Specialized Financial SLMs",
        name="Mutual Funds, Wealth Management & Specialized Financial SLMs",
        category_summary="Small Language Model (SLM) edge serving, Scheme Information Document (SID) clause parsing, deterministic NAV/CAGR/Sharpe/Alpha factor calculation, real-time AMFI/SEC API synchronization, and statutory regulatory compliance (SEBI/SEC Rule 482).",
        primary_language="python",
        core_primitives=[
            "Scheme Information Document (SID) / KIM parsing",
            "NAV timeseries tracking & historical growth curves",
            "Deterministic factor math (CAGR, Sharpe, Beta, Jensen's Alpha, XIRR)",
            "SEBI Mutual Fund regulations & statutory risk disclosures",
            "US SEC Rule 482 / FINRA advertising standards",
            "Promissory return interception ('guaranteed 18%') & PII sanitization",
            "Real-time AMFI & Yahoo Finance API data synchronization",
            "Continuous DPO (Direct Preference Optimization) preference pair synthesis",
            "Edge INT4 GGUF quantized SLM inference (< 2GB RAM)"
        ],
        grilling_dimensions=[
            "1. SLM Architecture & Quantization (Pre-train vs LoRA vs RAG): Are you pre-training raw weights from scratch, fine-tuning an open base foundation model (Qwen2.5-Coder-1.5B, Phi-4-mini, Llama-3.2-3B) via LoRA/SFT on SID/AMFI datasets, or building an edge inference copilot with deterministic tool calling? What parameter scale (1.5B vs 3B), quantization format (INT4 GGUF, AWQ, FP16), and artifact delivery (adapter safetensors vs GGUF) are required for edge CPU/laptop execution vs cloud?",
            "2. Deterministic Tool Calling vs Neural Math: How will quantitative financial calculations (3Y/5Y CAGR, Sharpe ratio, Beta, Jensen's Alpha, XIRR) be handled? Will all math be strictly routed to a deterministic calculation engine rather than attempting neural math?",
            "3. SID In-Context Retrieval: How are official Scheme Information Documents (SIDs) and Key Information Memorandums (KIMs) ingested and cited without fine-tuning drift?",
            "4. Real-Time API Synchronization: How will daily changing market NAVs and SID filings be ingested (automated cron connecting to AMFI/SEC EDGAR/Yahoo Finance APIs) without model weight retraining?",
            "5. Continuous Self-Correction via RL / DPO: How does the model auto-correct from runtime failure logs? Automated generation of (prompt, chosen, rejected) DPO preference pairs for nightly LoRA alignment?",
            "6. Statutory Guardrails & Data Privacy: Which statutory compliance requirements apply (SEBI risk-o-meter disclosures, SEC Rule 482 risk warnings)? How will client portfolio holdings and PII be quarantined from public clouds?"
        ],
        architectural_patterns=[
            "Deterministic Math Tool Dispatcher",
            "SID In-Context Document Chunk Retriever",
            "Statutory Regulatory Interceptor & PII Redactor",
            "Daily Real-Time API Sync Cron Worker",
            "DPO Preference Pair Synthesizer & Telemetry Miner"
        ],
        standard_libraries={
            "python": ["numpy", "scipy", "pydantic", "fastapi", "urllib3"],
            "go": ["gonum.org/v1/gonum/stat", "net/http"]
        },
        safety_and_nfr_focus=[
            "Zero tolerance for forward-looking promissory returns or guaranteed yield claims",
            "Zero numerical hallucination on fund performance metrics",
            "Local on-premise execution to prevent client portfolio PII leakage (DPDP / GDPR)",
            "Deterministic audit trail for all advisor-facing AI recommendations"
        ],
        competitor_archetypes=[
            {
                "competitor": "BloombergGPT (50B)",
                "limitations": "Massive parameter scale requiring expensive cloud GPU clusters; closed proprietary ecosystem ($24,000+/year terminal seats); cannot run at the edge.",
                "ascm_advantage": "Ultra-lightweight edge footprint (1.5B INT4, < 2GB RAM); runs locally on commodity CPU with sub-25ms latency and zero cloud costs."
            },
            {
                "competitor": "FinGPT / FinMA / FinSLM",
                "limitations": "Trained predominantly on generic news sentiment and earnings calls; hallucinates numerical NAV/CAGR metrics; lacks statutory regulatory compliance guardrails.",
                "ascm_advantage": "0% math hallucination via deterministic tool calling, and hard SEBI/SEC promissory return interceptors."
            },
            {
                "competitor": "Morningstar Direct / Commercial AMC RAG Bots",
                "limitations": "Rely on remote cloud LLMs (GPT-4 / Claude), exposing sensitive client portfolio holdings (PII) to third-party cloud APIs and incurring steep token fees.",
                "ascm_advantage": "100% on-premise edge execution with client data remaining strictly inside the institutional firewall."
            }
        ],
        preferred_models={
            "coder": "qwen2.5-coder:32b",
            "reviewer": "claude-3-5-sonnet",
            "architect": "gemini-2.5-pro",
            "product": "gemini-2.5-flash",
            "business": "gemini-2.5-flash"
        },
        unit_test_frameworks={"python": "unittest", "go": "testing"},
        role_titles={
            "product": "Specialized WealthTech, Mutual Funds & Financial SLM Principal",
            "architect": "Lead Financial SLM Systems Architect & Quant Designer",
            "thinking": "Senior Quantitative Finance & Statutory Guardrails Critic",
            "code_review": "Adversarial Financial Math & Regulatory Code Auditor",
            "orchestrator": "Lead WealthTech Multi-Agent Orchestrator",
            "planner": "Financial Model Pipeline Coordinator",
            "coder": "Principal Quant & Edge SLM Software Engineer",
            "business": "Chief Commercial Officer & WealthTech GTM Strategist",
            "security": "Financial Data Privacy & Regulatory Compliance Auditor"
        }
    )
}


class DomainKnowledgeEngine:
    """
    Manages dynamic domain identification, local disk persistence in '.ascm_domains/',
    and generation of laser-focused prompts without hardcoded cross-domain clutter.
    """

    def __init__(self, cache_dir: Optional[Union[Path, str]] = None, storage_dir: Optional[Union[Path, str]] = None):
        target = storage_dir or cache_dir or DEFAULT_DOMAINS_CACHE_DIR
        self.cache_dir = Path(target)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_local_cache()

    def _initialize_local_cache(self) -> None:
        """
        Populates local disk cache with built-in profiles if not already present.
        """
        for domain_id, profile in BUILTIN_PROFILES.items():
            file_path = self.cache_dir / f"{domain_id.lower()}.json"
            if not file_path.exists():
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(profile.model_dump(), f, indent=2)
                except Exception as err:
                    logger.warning(f"Could not persist domain profile {domain_id}: {err}")

    def load_domain_from_disk(self, domain_id: str) -> Optional[DomainProfile]:
        """
        Loads a domain profile from the local disk cache.
        """
        file_path = self.cache_dir / f"{domain_id.lower()}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return DomainProfile(**data)
            except Exception as err:
                logger.warning(f"Failed loading cached domain {domain_id}: {err}")
        return None

    def persist_domain_to_disk(self, profile: DomainProfile) -> None:
        """
        Persists a newly created or enriched domain profile to disk.
        """
        file_path = self.cache_dir / f"{profile.domain_id.lower()}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(profile.model_dump(), f, indent=2)
            logger.info(f"Persisted domain profile '{profile.domain_id}' to {file_path}")
        except Exception as err:
            logger.warning(f"Failed to persist domain {profile.domain_id}: {err}")

    def list_cached_domains(self) -> List[DomainProfile]:
        """Scans local disk cache for all persisted domains."""
        domains = []
        if self.cache_dir.exists():
            for p in self.cache_dir.glob("*.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        domains.append(DomainProfile(**data))
                except Exception:
                    pass
        return domains

    def synthesize_domain_profile(self, user_goal: str, context: Optional[str] = None) -> DomainProfile:
        """
        Dynamically synthesizes a new DomainProfile for previously unseen or novel domains
        (e.g., Agritech, Satellite Imagery, Veterinary Tech, Quantum Computing).
        Uses LLM provider with fast fallback to heuristic synthesis, then caches to '.ascm_domains/<domain_id>.json'.
        """
        prompt = (
            f"Analyze this software/product requirement and extract its exact vertical industry domain:\n"
            f"Requirement: {user_goal}\n"
            f"Context: {context or 'None'}\n\n"
            f"Generate a specialized domain profile JSON with this exact schema:\n"
            f"{{\n"
            f'  "domain_id": "short_lowercase_snake_case_id",\n'
            f'  "display_name": "Full Domain Display Name",\n'
            f'  "category_summary": "1-2 sentence technical summary of the vertical",\n'
            f'  "core_primitives": ["primitive 1", "primitive 2", "primitive 3", "primitive 4", "primitive 5"],\n'
            f'  "grilling_dimensions": [\n'
            f'     "1. Architecture & Model Choice: ...",\n'
            f'     "2. Verifiable Precision & State Handling: ...",\n'
            f'     "3. Integration & Hardware / API Protocols: ...",\n'
            f'     "4. Real-time Telemetry & Ingestion: ...",\n'
            f'     "5. Statutory, Safety & Regulatory Standards: ..."\n'
            f'  ],\n'
            f'  "competitor_archetypes": [\n'
            f'     {{"competitor": "Dominant Legacy Competitor", "limitations": "their key bottlenecks", "ascm_advantage": "how ASCM wins"}}\n'
            f'  ],\n'
            f'  "safety_and_nfr_focus": ["NFR 1", "NFR 2"],\n'
            f'  "standard_libraries": {{"python": ["lib1", "lib2"], "go": ["pkg1"]}}\n'
            f"}}"
        )
        try:
            from orchestrator.agents.base import get_configured_provider
            provider = get_configured_provider(tier="fast", agent_name="DomainKnowledgeEngine")
            raw = provider.generate(
                prompt=prompt,
                system_instruction="You are a Principal Domain Systems Architect. Output strictly valid JSON.",
                json_mode=True
            )
            data = json.loads(raw)
            profile = DomainProfile(**data)
            self.persist_domain_to_disk(profile)
            return profile
        except Exception as err:
            logger.info(f"LLM domain synthesis fallback for '{user_goal}': {err}")

        # Intelligent heuristic fallback synthesis
        slug = re.sub(r"[^a-z0-9]+", "_", user_goal.lower().strip())[:40].strip("_") or "custom_vertical"
        clean_name = " ".join(word.capitalize() for word in slug.split("_"))
        profile = DomainProfile(
            domain_id=slug,
            display_name=f"{clean_name} Systems Engineering",
            name=f"{clean_name} Systems Engineering",
            category_summary=f"Specialized systems architecture, protocols, and regulatory validation for {clean_name}.",
            primary_language="python",
            core_primitives=[
                f"{clean_name} domain data ingestion & serialization",
                f"Protocol verification & state validation for {clean_name}",
                "Deterministic calculation & precision factor attribution",
                "Real-time event streaming and pipeline telemetry",
                "Statutory standards and domain safety compliance guardrails"
            ],
            grilling_dimensions=[
                f"1. Architecture & Engine Selection: What compute runtime, framework, and hardware target for {clean_name}?",
                "2. Deterministic Precision vs Stochastic Estimation: How are mission-critical calculations verified to prevent hallucination?",
                "3. Ingestion & Real-Time Sync: What upstream APIs, industrial protocols, or data schemas are ingested?",
                "4. Continuous Monitoring & Automated Feedback: How are runtime anomalies detected and integrated into automated self-correction loops?",
                "5. Statutory & Safety Guardrails: Which vertical regulatory bodies, safety certifications, or legal disclaimers apply?"
            ],
            competitor_archetypes=[
                {
                    "competitor": f"Legacy {clean_name} Monoliths",
                    "limitations": "Rigid closed enterprise licensing, slow update cycles, lack of Git-native automation.",
                    "ascm_advantage": "Autonomous, verified multi-repo microservices synthesized directly into codebase."
                }
            ],
            safety_and_nfr_focus=[
                f"Strict zero-fault tolerance for critical {clean_name} operations",
                "Deterministic audit logs with cryptographic hash integrity"
            ],
            standard_libraries={"python": ["pydantic", "fastapi", "numpy"]}
        )
        self.persist_domain_to_disk(profile)
        return profile

    def narrow_domain(self, user_goal: str, context: Optional[str] = None) -> DomainProfile:
        """
        Narrows the user's request to the most specific, specialized domain profile.
        Prioritizes high-specificity compound domains (e.g. Mutual Funds SLM) before generic fallback domains.
        Autonomously synthesizes and learns new domains if not previously encountered.
        """
        combined = f"{user_goal} {context or ''}".lower()

        # 1. Mutual Funds / WealthTech / Asset Management / Financial SLM
        mf_keywords = [
            "mutual fund", "mutual funds", "amc", "amfi", "scheme information document", "sid",
            "cagr", "sharpe", "jensen", "nav", "portfolio factor", "wealth advisory", "sip",
            "asset management", "etf", "expense ratio", "risk-o-meter", "sec rule 482"
        ]
        if any(re.search(rf"\b{re.escape(k)}\b", combined) for k in mf_keywords):
            cached = self.load_domain_from_disk("MUTUAL_FUNDS_WEALTH_SLM")
            if cached:
                return cached
            return BUILTIN_PROFILES["MUTUAL_FUNDS_WEALTH_SLM"]

        # 2. Check previously synthesized domains in local disk cache (.ascm_domains/*.json)
        for cached_profile in self.list_cached_domains():
            if cached_profile.domain_id in combined or cached_profile.display_name.lower() in combined:
                return cached_profile

        # Check existing vertical domains from domain_adapter
        from orchestrator.domain.domain_adapter import VERTICAL_DOMAINS

        # 3. Crypto / Web3 Payments
        if any(k in combined for k in ["crypto", "bitcoin", "ethereum", "web3", "token", "solana", "blockchain", "wallet", "onchain", "smart contract"]):
            return VERTICAL_DOMAINS["FINTECH_CRYPTO"]

        # 4. CAD / CAM Manufacturing
        if any(k in combined for k in ["cad", "cam", "cnc", "toolpath", "g-code", "mesh", "stl", "step", "nurbs", "spindle", "slicer"]):
            return VERTICAL_DOMAINS["CAD_CAM"]

        # 5. Healthcare / MedTech
        if any(k in combined for k in ["health", "medical", "patient", "ehr", "emr", "fhir", "hl7", "dicom", "hipaa", "radiology", "pharma"]):
            return VERTICAL_DOMAINS["HEALTHCARE_MEDTECH"]

        # 6. LegalTech / Contracts
        if any(k in combined for k in ["contract", "contracts", "clause", "nda", "gdpr", "ediscovery", "redline", "lawyer", "attorney"]):
            return VERTICAL_DOMAINS["LEGALTECH_COMPLIANCE"]

        # 7. Robotics & Embedded
        if any(k in combined for k in ["robot", "embedded", "firmware", "iot", "rtos", "ros2", "microcontroller", "stm32"]):
            return VERTICAL_DOMAINS["ROBOTICS_EMBEDDED"]

        # 8. DevTools & Compilers
        if any(k in combined for k in ["compiler", "parser", "ast", "lexer", "transpiler", "linter", "lsp", "bytecode"]):
            return VERTICAL_DOMAINS["DEVTOOLS_COMPILER"]

        # 9. General AI / ML Systems
        if any(k in combined for k in ["llm", "slm", "small language model", "language model", "rag", "vector", "embedding", "inference"]):
            return VERTICAL_DOMAINS["AI_ML_SYSTEMS"]

        # 10. Infinite Domain Discovery: Synthesize and learn any new vertical dynamically
        return self.synthesize_domain_profile(user_goal, context)

    def build_focused_product_system_prompt(self, profile: Any) -> str:
        """
        Generates a 100% focused, laser-sharp system prompt for ProductAgent
        containing ONLY the primitives and grilling dimensions for the narrowed domain.
        Zero unrelated domain clutter.
        """
        if isinstance(profile, str):
            profile = self.narrow_domain(profile)
        elif not isinstance(profile, DomainProfile):
            profile = self.narrow_domain(getattr(profile, "name", "") or getattr(profile, "domain_id", "") or str(profile))

        primitives_bulleted = "\n".join(f"   * {p}" for p in profile.core_primitives)
        grilling_bulleted = "\n".join(f"   * {g}" for g in profile.grilling_dimensions)

        return (
            f"You are an Elite Principal Product Manager, Systems Analyst, and {profile.display_name} Expert.\n"
            f"Your mission is to rigorously evaluate user requirements against functional architecture and "
            f"Non-Functional Requirements (NFRs: security, accuracy, performance, contracts, regulatory compliance).\n\n"
            f"DOMAIN SPECIALIZATION: [{profile.display_name}]\n"
            f"Category Overview: {profile.category_summary}\n\n"
            f"CORE DOMAIN PRIMITIVES TO VERIFY:\n"
            f"{primitives_bulleted}\n\n"
            f"MANDATORY DOMAIN GRILLING DIMENSIONS:\n"
            f"{grilling_bulleted}\n\n"
            f"GRILLING DECISION RULES:\n"
            f"1. Confidence Scoring:\n"
            f"   - If the user's input lacks answers to these critical domain dimensions:\n"
            f"     * DO NOT ASSUME. Set confidence_score < 0.50 (50%).\n"
            f"     * Set is_clear to false.\n"
            f"     * Generate sharp, domain-specific 'clarification_questions' matching the unresolved dimensions above.\n"
            f"   - Only when confidence_score >= 0.90 (90%+):\n"
            f"     * Set is_clear to true.\n"
            f"     * Place low-priority non-blocking edge cases (<10%) in 'checkpoint_clarification_items'.\n"
            f"     * Set 'clarification_questions' to [].\n\n"
            f"2. Output JSON with this exact schema:\n"
            f"{{\n"
            f'  "detected_domain": "{profile.display_name}",\n'
            f'  "confidence_score": float,\n'
            f'  "functional_completeness": float,\n'
            f'  "nfr_completeness": float,\n'
            f'  "is_clear": bool,\n'
            f'  "understanding": "comprehensive breakdown of features, domain flow, math/tool contracts, and NFRs",\n'
            f'  "clarification_questions": ["question 1 with options", "question 2 with options"],\n'
            f'  "checkpoint_clarification_items": [\n'
            f'     {{"checkpoint": "module_or_task", "question": "specific deferred question", "default_assumption": "standard assumption"}}\n'
            f'  ]\n'
            f"}}"
        )

    def build_focused_business_system_prompt(self, profile: Any) -> str:
        """
        Generates a focused system prompt for BusinessStrategyAgent with the exact competitor
        battlecards and market cohorts for the narrowed domain.
        """
        if isinstance(profile, str):
            profile = self.narrow_domain(profile)
        elif not isinstance(profile, DomainProfile):
            profile = self.narrow_domain(getattr(profile, "name", "") or getattr(profile, "domain_id", "") or str(profile))

        competitors_summary = "\n".join(
            f"   * {c.get('competitor')}: Limitations: {c.get('limitations')} | ASCM Advantage: {c.get('ascm_advantage')}"
            for c in profile.competitor_archetypes
        )

        return (
            f"You are an Elite Chief Commercial Officer (CCO) and {profile.display_name} GTM Strategist.\n"
            f"Analyze the technical product requirements and system capabilities to formulate an aggressive, data-backed Go-To-Market strategy.\n\n"
            f"DOMAIN SPECIALIZATION: [{profile.display_name}]\n\n"
            f"BENCHMARK COMPETITORS IN THIS DOMAIN:\n"
            f"{competitors_summary}\n\n"
            f"Output JSON with this exact schema:\n"
            f"{{\n"
            f'  "detected_domain": "{profile.display_name}",\n'
            f'  "market_strategy": "string",\n'
            f'  "user_cohorts": [\n'
            f'    {{"cohort_name": "...", "pain_point": "...", "why_adopt": "...", "willingness_to_pay": "..."}}\n'
            f'  ],\n'
            f'  "competitor_analysis": [\n'
            f'    {{"competitor": "...", "limitations": "...", "ascm_advantage": "...", "verdict": "..."}}\n'
            f'  ],\n'
            f'  "value_proposition": "string",\n'
            f'  "gtm_channels": ["channel 1", "channel 2"],\n'
            f'  "executive_summary": "string"\n'
            f"}}"
        )


GLOBAL_DOMAIN_KNOWLEDGE_ENGINE = DomainKnowledgeEngine()

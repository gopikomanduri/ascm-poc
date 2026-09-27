"""Tests for DomainKnowledgeEngine, focused dynamic grilling, and local domain persistence."""

import os
import json
import pytest
from orchestrator.domain.domain_knowledge_engine import (
    DomainKnowledgeEngine,
    GLOBAL_DOMAIN_KNOWLEDGE_ENGINE,
    DomainProfile,
)
from orchestrator.domain.domain_adapter import DomainAdapter, VERTICAL_DOMAINS
from orchestrator.agents.all_agents import ProductAgent, BusinessStrategyAgent


class TestDomainKnowledgeEngine:
    def test_mutual_funds_wealth_slm_registered(self):
        assert "MUTUAL_FUNDS_WEALTH_SLM" in VERTICAL_DOMAINS
        adapter = DomainAdapter()
        domain = adapter.detect_domain(
            "Building an edge Small Language Model for mutual funds and wealth management SID parsing"
        )
        assert domain.name == "Mutual Funds, Wealth Management & Specialized Financial SLMs"

    def test_local_persistence_stores_json(self, tmp_path):
        engine = DomainKnowledgeEngine(storage_dir=str(tmp_path))
        profile = engine.narrow_domain("mutual fund small language model fine-tuning with amfi nav")
        
        file_path = tmp_path / f"{profile.domain_id}.json"
        assert file_path.exists()
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["domain_id"] == "mutual_funds_wealth_slm"
        assert "Qwen2.5" in str(data)
        assert len(data["grilling_dimensions"]) >= 5

    def test_product_agent_prompt_has_zero_crypto_cad_noise_for_mf(self):
        engine = GLOBAL_DOMAIN_KNOWLEDGE_ENGINE
        prompt = engine.build_focused_product_system_prompt("Mutual Funds, Wealth Management & Specialized Financial SLMs")
        
        # Must contain specialized SLM & Mutual Fund grilling topics
        assert "SLM Architecture & Quantization" in prompt
        assert "Deterministic Tool Calling vs Neural Math" in prompt
        assert "Continuous Self-Correction via RL / DPO" in prompt
        assert "Real-Time API Synchronization" in prompt
        assert "SID In-Context Retrieval" in prompt
        
        # Must NOT contain hard-coded cross-domain clutter
        assert "EVM e.g. Ethereum" not in prompt
        assert "Smart contract escrow" not in prompt
        assert "Parametric CAD" not in prompt

    def test_business_strategy_prompt_includes_focused_battlecards(self):
        engine = GLOBAL_DOMAIN_KNOWLEDGE_ENGINE
        prompt = engine.build_focused_business_system_prompt("Mutual Funds, Wealth Management & Specialized Financial SLMs")
        
        # Must analyze MF SLM competitors
        assert "BloombergGPT" in prompt
        assert "FinGPT" in prompt
        assert "Morningstar Direct" in prompt
        
        # Must not contain generic irrelevant domain battlecards
        assert "Clio / Ironclad" not in prompt

"""
IntentRadar: Multi-Channel Live Signal Harvester & Domain-Aware Intent Scorer.
Monitors 4 live channels:
  1. Hacker News (Show HN / Ask HN via Algolia Search API)
  2. Dev Community & Builder Blogs (Dev.to API)
  3. GitHub Active Repositories (GitHub Search API)
  4. Tech & Product Launches (Live Hacker News / Tech Feeds)

Uses Gemini to evaluate domain relevance (0-100), 'Buy-Ready' intent (0-100),
and draft value-first Challenger sales and marketing responses.
"""

import os
import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional

from orchestrator.agents.base import BaseAgent, BaseLLMProvider, parse_json_lenient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class IntentRadar(BaseAgent):
    """
    Domain-Aware Signal Harvester and Buy-Ready Intent Evaluator.
    Scrapes live developer signals across 4 channels and ranks opportunities.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are an Elite B2B Growth Engineer and Intent Intelligence Analyst.\n"
                "Your mission is to evaluate raw developer signals (forum posts, launches, repos, articles) "
                "against a client product's domain thesis and ICP.\n"
                "You must compute strict numerical scores:\n"
                "1. domain_relevance (0-100): How closely related this is to the product's space.\n"
                "2. buy_ready_intent (0-100): How likely the author/team is currently experiencing the pain point or entering a buying/validation window.\n"
                "Then classify the primary pain trigger and draft an authentic, value-first response (zero hype, zero corporate spam)."
            ),
            provider=provider,
            tier="primary",
        )

    # =========================================================================
    # CHANNEL 1: Hacker News (Algolia Search API)
    # =========================================================================
    def harvest_hacker_news(self, query: str = "overengineering", limit: int = 5) -> List[Dict[str, Any]]:
        """Scrapes real-time developer posts, Show HN, and Ask HN."""
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://hn.algolia.com/api/v1/search_by_date?query={encoded_query}&tags=story&hitsPerPage={limit}"
        results = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OutcodeIntentRadar/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for hit in data.get("hits", []):
                oid = hit.get("objectID")
                results.append({
                    "channel": "Hacker News",
                    "id": f"hn_{oid}",
                    "title": hit.get("title", ""),
                    "author": hit.get("author", "unknown"),
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={oid}",
                    "timestamp": hit.get("created_at", ""),
                    "raw_text": hit.get("story_text") or hit.get("title", ""),
                    "query_used": query
                })
        except Exception as e:
            results.append({"channel": "Hacker News", "error": str(e), "query_used": query})
        return results

    # =========================================================================
    # CHANNEL 2: Dev.to & Developer Community API
    # =========================================================================
    def harvest_dev_community(self, tag: str = "showdev", limit: int = 5) -> List[Dict[str, Any]]:
        """Scrapes real-time builder articles and MVP launch stories."""
        url = f"https://dev.to/api/articles?tag={urllib.parse.quote_plus(tag)}&per_page={limit}"
        results = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OutcodeIntentRadar/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for article in data:
                results.append({
                    "channel": "Dev.to Community",
                    "id": f"devto_{article.get('id')}",
                    "title": article.get("title", ""),
                    "author": article.get("user", {}).get("username", "unknown"),
                    "url": article.get("url", ""),
                    "timestamp": article.get("published_at", ""),
                    "raw_text": f"{article.get('title', '')} - {article.get('description', '')}",
                    "query_used": tag
                })
        except Exception as e:
            results.append({"channel": "Dev.to Community", "error": str(e), "query_used": tag})
        return results

    # =========================================================================
    # CHANNEL 3: GitHub Active Repositories API
    # =========================================================================
    def harvest_github_repos(self, query: str = "cli tool developer", limit: int = 5) -> List[Dict[str, Any]]:
        """Discovers newly created or active repositories matching target domain."""
        encoded_q = urllib.parse.quote_plus(f"{query} fork:false")
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=updated&order=desc&per_page={limit}"
        results = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OutcodeIntentRadar/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for repo in data.get("items", []):
                results.append({
                    "channel": "GitHub Repositories",
                    "id": f"gh_{repo.get('id')}",
                    "title": repo.get("full_name", ""),
                    "author": repo.get("owner", {}).get("login", "unknown"),
                    "url": repo.get("html_url", ""),
                    "timestamp": repo.get("updated_at", ""),
                    "raw_text": f"Repo: {repo.get('full_name')} - {repo.get('description') or 'No description'}",
                    "query_used": query
                })
        except Exception as e:
            results.append({"channel": "GitHub Repositories", "error": str(e), "query_used": query})
        return results

    # =========================================================================
    # CHANNEL 4: Tech & Product Launches Feed
    # =========================================================================
    def harvest_launch_feed(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Scrapes live launch stories and technical release feeds."""
        url = "https://news.ycombinator.com/rss"
        results = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OutcodeIntentRadar/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")
            for item in items[:limit]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                results.append({
                    "channel": "Tech Launch Feed",
                    "id": f"launch_{hash(link) % 1000000}",
                    "title": title,
                    "author": "Tech Builder",
                    "url": link,
                    "timestamp": pub_date,
                    "raw_text": title,
                    "query_used": "rss_feed"
                })
        except Exception as e:
            results.append({"channel": "Tech Launch Feed", "error": str(e)})
        return results

    # =========================================================================
    # MULTI-CHANNEL HARVESTING & DOMAIN-AWARE EVALUATION
    # =========================================================================
    def scan_all_channels(
        self,
        domain_keywords: Optional[List[str]] = None,
        limit_per_channel: int = 4
    ) -> List[Dict[str, Any]]:
        """Harvests candidates across all 4 channels."""
        keywords = domain_keywords or ["overengineering", "solo founder", "developer tools"]
        all_signals = []

        # 1. Hacker News
        all_signals.extend(self.harvest_hacker_news(keywords[0], limit=limit_per_channel))

        # 2. Dev.to
        all_signals.extend(self.harvest_dev_community("showdev", limit=limit_per_channel))

        # 3. GitHub Repos
        all_signals.extend(self.harvest_github_repos(keywords[-1], limit=limit_per_channel))

        # 4. Tech Launch Feed
        all_signals.extend(self.harvest_launch_feed(limit=limit_per_channel))

        # Filter out errors
        valid_signals = [s for s in all_signals if "error" not in s and s.get("title")]
        return valid_signals

    def evaluate_signals_for_domain(
        self,
        signals: List[Dict[str, Any]],
        project_thesis: str,
        icp_description: str,
    ) -> Dict[str, Any]:
        """
        Uses LLM intelligence to evaluate relevance, buy-ready intent, and generate
        tailored value-first responses for the highest-scoring leads.
        """
        prompt = f"""
You are the Outcode Intent Intelligence Agent.

OUR PRODUCT THESIS:
{project_thesis}

OUR TARGET ICP:
{icp_description}

CANDIDATE SIGNALS HARVESTED ACROSS 4 LIVE CHANNELS:
{json.dumps(signals[:12], indent=2)}

TASK:
For each signal, evaluate:
1. domain_relevance (0-100): How closely aligned is the post/repo to our target domain?
2. buy_ready_intent (0-100): How clearly is the author/team facing isolation, over-engineering, or lack of GTM distribution?
3. pain_category: One of [THE_DARK_ROOM_TRAP, OVER_ENGINEERING, LAUNCH_VALIDATION_STRUGGLE, GENERAL_TECH, NOT_RELEVANT].
4. why_buy_ready: 1-sentence diagnostic explaining their current pain window.
5. value_first_outreach: If buy_ready_intent >= 70, draft a short, humble, authentic message (max 50 words) that teaches them something useful or offers a free diff audit. Otherwise null.

OUTPUT JSON SCHEMA:
{{
  "evaluated_signals": [
    {{
      "id": "string",
      "channel": "string",
      "title": "string",
      "author": "string",
      "url": "string",
      "domain_relevance": int,
      "buy_ready_intent": int,
      "pain_category": "string",
      "why_buy_ready": "string",
      "value_first_outreach": "string or null"
    }}
  ]
}}
"""
        raw = self.call(prompt, json_mode=True)
        data = parse_json_lenient(raw)
        evaluated = data.get("evaluated_signals", [])

        # Sort by buy_ready_intent descending
        sorted_signals = sorted(evaluated, key=lambda x: x.get("buy_ready_intent", 0), reverse=True)

        high_intent_leads = [s for s in sorted_signals if s.get("buy_ready_intent", 0) >= 70]
        summary = {
          "total_scanned": len(signals),
          "high_intent_leads_count": len(high_intent_leads),
          "top_leads": high_intent_leads[:5],
          "all_evaluated": sorted_signals
        }
        return summary

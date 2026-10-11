"""
Continuous GTM Engine (Outcode / ASCM)
Orchestrates MarketingAgent ('Engineering as Marketing' + Category Design)
and SalesAgentV2 ('Signal-Based Selling' + PQL Challenger Triage) on the active client project.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from orchestrator.gtm.agents.marketing_agent import MarketingAgent
from orchestrator.gtm.agents.sales_agent_v2 import SalesAgentV2
from orchestrator.gtm.intent_radar import IntentRadar

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WAITLIST_FILE = PROJECT_ROOT / ".ascm_waitlist.json"
GTM_ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "gtm_cycles"


class ContinuousGTMEngine:
    """
    Continuous GTM Orchestrator:
    Dogfoods Outcode on the active repository, translating code diffs into
    authentic developer marketing, harvesting live buying signals across 4 channels,
    and triaging incoming waitlist signups.
    """

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or PROJECT_ROOT
        self.marketing_agent = MarketingAgent()
        self.sales_agent = SalesAgentV2()
        self.intent_radar = IntentRadar()

    def get_latest_git_diff_summary(self) -> Dict[str, str]:
        """Inspects local git repository to extract recent milestone/diff context."""
        try:
            commit_log = subprocess.check_output(
                ["git", "log", "-1", "--pretty=format:%h - %s (%cr)"],
                cwd=str(self.project_path),
                text=True
            ).strip()
            diff_stat = subprocess.check_output(
                ["git", "diff", "--stat", "HEAD~1..HEAD"],
                cwd=str(self.project_path),
                text=True
            ).strip()
            return {
                "latest_commit": commit_log,
                "diff_stat": diff_stat or "Recent Milestone commits (Outcode V1 Launch, Cloud Run, Vertex SDK)"
            }
        except Exception:
            return {
                "latest_commit": "milestone-1: Outcode V1 launch, cloud deployment & secure waitlist engine",
                "diff_stat": "Updated Cloud Run deployment, 3-tier scenario showcase, secure waitlist API, Google Models SDK"
            }

    def load_waitlist_leads(self) -> List[Dict[str, Any]]:
        """Loads verified signups from .ascm_waitlist.json."""
        if not WAITLIST_FILE.exists():
            return []
        try:
            data = json.loads(WAITLIST_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "entries" in data:
                return data["entries"]
            elif isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def execute_gtm_cycle(self) -> Dict[str, Any]:
        """
        Executes a complete GTM cycle:
        1. Marketing: Translates code diff into Engineering-as-Marketing artifacts.
        2. Sales: Triages waitlist signups with signal-based PQL scoring and Challenger audits.
        """
        GTM_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print("\n" + "=" * 65)
        print("🚀 OUTCODE CONTINUOUS GTM ENGINE — CYCLE START")
        print("=" * 65)

        # Step 1: Git Context
        git_info = self.get_latest_git_diff_summary()
        print(f"\n[Git Context] 📦 Latest Commit: {git_info['latest_commit']}")
        print(f"[Git Context] 📊 Diff Activity:\n{git_info['diff_stat']}\n")

        # Step 2: MarketingAgent (Engineering as Marketing)
        print("[MarketingAgent 📣] Generating 'Engineering-as-Marketing' Playbook...")
        marketing_playbook = self.marketing_agent.generate_engineering_as_marketing_playbook(
            diff_summary=f"Commit: {git_info['latest_commit']}\nDiff:\n{git_info['diff_stat']}",
            milestone_name="Milestone 1 (Outcode V1 Cloud Run Launch)",
            product_thesis="Outcode: Stop coding in isolation. Your terminal just hired a GTM team."
        )

        # Step 3: IntentRadar (Multi-Channel Live Signal Harvester)
        print("\n[IntentRadar 🛰️] Scanning 4 live channels (HN, Dev.to, GitHub, Tech Feeds)...")
        raw_signals = self.intent_radar.scan_all_channels(
            domain_keywords=["overengineering", "solo founder", "developer tools"],
            limit_per_channel=3
        )
        print(f"[IntentRadar 🛰️] Evaluating {len(raw_signals)} live signals for domain relevance & buy-ready intent...")
        radar_results = self.intent_radar.evaluate_signals_for_domain(
            signals=raw_signals,
            project_thesis="Outcode: Stop coding in isolation. Your terminal just hired a GTM team.",
            icp_description="Solo founders, technical co-founders, CTOs, and indie hackers writing code in isolation without marketing."
        )
        print(f"[IntentRadar 🛰️] Detected {radar_results.get('high_intent_leads_count', 0)} high-intent external leads!")

        # Step 4: SalesAgentV2 (Signal-Based Selling & PQL Triage)
        leads = self.load_waitlist_leads()
        print(f"\n[SalesAgent 🎯] Analyzing {len(leads)} waitlist leads for buying signals...")
        triage_results = self.sales_agent.evaluate_signals_and_triage_leads(leads)

        # Generate bespoke Challenger audits for Tier 1 leads
        tier_1_audits = []
        for lead in triage_results.get("enriched_leads", []):
            if "TIER_1" in lead.get("pql_category", ""):
                print(f"  ⚡ Generating Value-First Challenger Audit for: {lead.get('email')}...")
                audit = self.sales_agent.generate_challenger_value_audit(
                    lead=lead,
                    project_thesis="Outcode: Stop coding in isolation. Your terminal just hired a GTM team."
                )
                tier_1_audits.append({
                    "lead": lead,
                    "audit": audit
                })

        cycle_result = {
            "timestamp": timestamp,
            "git_context": git_info,
            "marketing_playbook": marketing_playbook,
            "radar_results": radar_results,
            "sales_triage": triage_results,
            "tier_1_audits": tier_1_audits,
        }

        # Save Artifacts
        json_path = GTM_ARTIFACTS_DIR / f"gtm_cycle_{timestamp}.json"
        json_path.write_text(json.dumps(cycle_result, indent=2), encoding="utf-8")

        # Generate Human-Readable Markdown Report
        md_path = GTM_ARTIFACTS_DIR / f"gtm_cycle_{timestamp}.md"
        self._write_markdown_report(md_path, cycle_result)

        print("\n" + "=" * 65)
        print("✅ GTM CYCLE COMPLETE — ARTIFACTS SAVED:")
        print(f"  📄 JSON: {json_path}")
        print(f"  📝 Markdown: {md_path}")
        print("=" * 65 + "\n")

        return cycle_result

    def _write_markdown_report(self, path: Path, data: Dict[str, Any]):
        """Creates a clean, human-readable GTM briefing markdown report."""
        mp = data.get("marketing_playbook", {})
        vn = mp.get("villain_narrative", {})
        mt = mp.get("engineering_micro_tool_concept", {})
        ra = mp.get("release_artifacts", {})
        st = data.get("sales_triage", {})
        t1_audits = data.get("tier_1_audits", [])

        lines = [
            "# Outcode Continuous GTM Cycle Report",
            f"**Generated:** {data.get('timestamp')}",
            f"**Git Context:** `{data.get('git_context', {}).get('latest_commit')}`",
            "",
            "---",
            "## 1. Category Design & Villain Narrative",
            f"- **Villain:** {vn.get('villain_name', 'The Dark Room Trap')}",
            f"- **Core Pain:** {vn.get('core_frustration', '')}",
            f"- **Paradigm Shift:** {vn.get('the_paradigm_shift', '')}",
            "",
            "## 2. Engineering-as-Marketing Micro-Tool",
            f"- **Tool Name:** {mt.get('tool_name', '')}",
            f"- **Concept:** {mt.get('description', '')}",
            f"- **Growth Loop Footer:** `{mp.get('growth_loop_footer', '⚡ Distilled from git diff via Outcode')}`",
            "",
            "## 3. Developer Launch Artifacts",
            "### Hacker News (Show HN)",
            f"**Title:** {ra.get('show_hn', {}).get('title', '')}",
            f"```\n{ra.get('show_hn', {}).get('body', '')}\n```",
            "",
            "### X / Twitter Launch Thread",
        ]

        for i, tweet in enumerate(ra.get("x_thread", []), 1):
            lines.append(f"{i}. {tweet}")
        lines.append("")

        lines.extend([
            "### Reddit (r/SideProject)",
            f"**Title:** {ra.get('reddit_builder_post', {}).get('title', '')}",
            f"{ra.get('reddit_builder_post', {}).get('story', '')}",
            "",
            "### Customer-Facing Changelog",
            f"**Headline:** {ra.get('customer_facing_changelog', {}).get('headline', '')}",
            f"- Why it matters: {ra.get('customer_facing_changelog', {}).get('why_it_matters_to_users', '')}",
            "",
            "---",
            "## 4. Signal-Based Sales Triage & PQL Scoring",
            f"- **Tier 1 (High-Fit Founders):** {st.get('tier_1_count', 0)}",
            f"- **Tier 2 (Pro Builders):** {st.get('tier_2_count', 0)}",
            f"- **Tier 3 (Community Alpha):** {st.get('tier_3_count', 0)}",
            "",
            "### Bespoke Challenger Audits (Tier 1 Leads):",
        ])

        for audit_item in t1_audits:
            lead = audit_item.get("lead", {})
            audit = audit_item.get("audit", {})
            diag = audit.get("prospect_diagnostic", {})
            email = audit.get("value_first_email", {})
            lines.extend([
                f"#### Lead: `{lead.get('email')}` ({lead.get('buying_signal')})",
                f"- **Persona Diagnostic:** {diag.get('persona_inferred')}",
                f"- **Surprising Insight:** {diag.get('surprising_insight')}",
                f"- **Value-First Subject:** *{email.get('subject')}*",
                f"- **Email Body:**\n> {email.get('the_diagnostic_teardown')}\n>\n> {email.get('zero_pressure_offer')}",
                ""
            ])

        rr = data.get("radar_results", {})
        top_radar = rr.get("top_leads", [])
        lines.extend([
            "---",
            "## 5. Live Multi-Channel Intent Radar (External Buy-Ready Leads)",
            f"- **Total Live Signals Scanned:** {rr.get('total_scanned', 0)} across 4 channels (HN, Dev.to, GitHub, Tech Feeds)",
            f"- **High-Intent Leads Detected:** {rr.get('high_intent_leads_count', 0)}",
            "",
            "### Top Qualified External Opportunities:",
        ])

        for s in top_radar:
            lines.extend([
                f"#### ⚡ [{s.get('channel')}] {s.get('title')} (by @{s.get('author')})",
                f"- **URL:** {s.get('url')}",
                f"- **Domain Relevance:** `{s.get('domain_relevance')}/100` | **Buy-Ready Intent:** `{s.get('buy_ready_intent')}/100`",
                f"- **Pain Category:** `{s.get('pain_category')}`",
                f"- **Why Buy-Ready:** {s.get('why_buy_ready')}",
            ])
            if s.get("value_first_outreach"):
                lines.extend([
                    f"- **Value-First Draft:**\n> {s.get('value_first_outreach')}",
                ])
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    engine = ContinuousGTMEngine()
    engine.execute_gtm_cycle()

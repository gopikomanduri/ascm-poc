#!/usr/bin/env python3
"""
Automated DPO (Direct Preference Optimization) Preference Pair Generator.
Mines runtime interaction telemetry, audit logs, and guardrail interception events
to generate high-quality (prompt, chosen, rejected) training pairs for continuous
nightly alignment of the 1.5B Small Language Model.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

app_dir = Path(__file__).resolve().parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

try:
    from app.fund_data import MutualFundMetricsCalculator
except ImportError:
    from fund_data import MutualFundMetricsCalculator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DPOPreferenceGenerator")

SEBI_STATUTORY_DISCLAIMER = (
    "\n\n*Statutory Regulatory Disclaimer: Mutual fund investments are subject to market risks, "
    "read all scheme related documents carefully. Past performance is no guarantee of future returns.*"
)

SYSTEM_PROMPT_TEMPLATE = (
    "<|im_start|>system\n"
    "You are a specialized Mutual Funds Small Language Model (SLM) Copilot. "
    "Mandates: 1) Never promise guaranteed returns. 2) Always invoke deterministic tools for CAGR, Sharpe, Beta. "
    "3) Attach SEBI and SEC Rule 482 risk disclosures.<|im_end|>\n"
)


class DPOPreferencePair:
    def __init__(
        self,
        prompt: str,
        chosen: str,
        rejected: str,
        violation_type: str,
        reward_margin: float = 2.0,
        fund_id: str = "general",
    ):
        self.prompt = prompt
        self.chosen = chosen
        self.rejected = rejected
        self.violation_type = violation_type
        self.reward_margin = reward_margin
        self.fund_id = fund_id
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "metadata": {
                "violation_type": self.violation_type,
                "reward_margin": self.reward_margin,
                "fund_id": self.fund_id,
                "created_at": self.created_at,
            },
        }


class DPOPreferenceGenerator:
    """
    Synthesizes DPO preference pairs from interaction audit logs and synthetic edge failure modes.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (app_dir.parent / "data")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_file = self.output_dir / "dpo_preference_dataset.jsonl"
        self.manifest_file = self.output_dir / "dpo_manifest.json"
        self.calculator = MutualFundMetricsCalculator(risk_free_rate=0.065)

    def format_chat_prompt(self, user_query: str, fund_name: str) -> str:
        return (
            f"{SYSTEM_PROMPT_TEMPLATE}"
            f"<|im_start|>user\n"
            f"[Context: Scheme: {fund_name}]\n"
            f"{user_query}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    def generate_pair_from_intercept(self, record: Dict[str, Any]) -> Optional[DPOPreferencePair]:
        """
        Converts an intercepted interaction record into a high-reward DPO training pair.
        """
        query = record.get("query", "")
        fund_name = record.get("fund_name", "Mutual Fund Scheme")
        fund_id = record.get("fund_id", "hdfc_top_100")
        raw_draft = record.get("raw_response", "")
        sanitized = record.get("sanitized_response", "")
        violations = record.get("violations_intercepted", [])

        if not raw_draft or not sanitized:
            return None

        prompt = self.format_chat_prompt(query, fund_name)

        # Chosen: Sanitized compliant response with disclaimers
        chosen = sanitized.strip()
        if "market risks" not in chosen.lower():
            chosen += SEBI_STATUTORY_DISCLAIMER

        # Rejected: Raw draft that contained unhedged claims or missed disclaimers
        rejected = raw_draft.strip()

        violation_type = violations[0] if violations else "PROMISSORY_CLAIM"
        margin = 3.0 if "PROMISSORY" in violation_type else 1.5

        return DPOPreferencePair(
            prompt=prompt,
            chosen=chosen,
            rejected=rejected,
            violation_type=violation_type,
            reward_margin=margin,
            fund_id=fund_id,
        )

    def generate_synthetic_archetype_pairs(self) -> List[DPOPreferencePair]:
        """
        Generates standard canonical DPO pairs across all 4 key financial failure archetypes:
        1. Promissory return requests ("18% guaranteed return").
        2. Hallucinated CAGR/Beta calculation without calling tool.
        3. Fabrication of exit load / lock-in period differing from official SID.
        4. Omission of SEBI / SEC statutory disclaimers.
        """
        pairs = []

        # Archetype 1: Promissory Return Interception
        p1 = self.format_chat_prompt(
            "Can you guarantee that HDFC Top 100 Index Fund will give me 18% annualized returns with zero risk?",
            "HDFC Top 100 Index Fund"
        )
        c1 = (
            "We analyzed **HDFC Top 100 Index Fund**. Mutual fund regulations strictly prohibit promising guaranteed returns. "
            "Historically, this fund has delivered a 3-Year CAGR of **11.61%** with a Beta of **0.93** and Sharpe Ratio of **0.36**. "
            "Because this is an equity fund, returns fluctuate with market conditions and cannot be guaranteed."
            + SEBI_STATUTORY_DISCLAIMER
        )
        r1 = (
            "Yes! HDFC Top 100 is an extremely safe fund that will reliably deliver 18% guaranteed returns every year. "
            "You can invest without worrying about any downside risk."
        )
        pairs.append(DPOPreferencePair(p1, c1, r1, "PROMISSORY_RETURN_INTERCEPT", reward_margin=3.5, fund_id="hdfc_top_100"))

        # Archetype 2: Deterministic Tool Calling vs Neural Guessing
        p2 = self.format_chat_prompt(
            "What is the exact 3-Year CAGR for Parag Parikh Flexi Cap Fund if NAV grew from 52.80 to 86.42?",
            "Parag Parikh Flexi Cap Fund"
        )
        c2 = (
            "Executing deterministic tool: `MutualFundMetricsCalculator.calculate_cagr(start_nav=52.80, end_nav=86.42, years=3.0)`.\n\n"
            "The exact compounded annual growth rate (CAGR) is **17.84%**.\n"
            "- Formula: `(86.42 / 52.80)^(1/3) - 1 = 17.84%`.\n"
            "- Risk-Adjusted Sharpe Ratio: **0.80**."
            + SEBI_STATUTORY_DISCLAIMER
        )
        r2 = (
            "Looking at those numbers, the CAGR is roughly around 24% or maybe 30% per year because the market had high momentum."
        )
        pairs.append(DPOPreferencePair(p2, c2, r2, "HALLUCINATED_NUMERICAL_MATH", reward_margin=2.5, fund_id="parag_parikh_flexi"))

        # Archetype 3: SID Prospectus Grounding vs Hallucination
        p3 = self.format_chat_prompt(
            "What is the exit load clause for HDFC Top 100 Index Fund according to its Scheme Information Document?",
            "HDFC Top 100 Index Fund"
        )
        c3 = (
            "According to the official Scheme Information Document (SID) for **HDFC Top 100 Index Fund**:\n"
            "- **Exit Load**: **1%** if redeemed or switched out within **30 days** from the date of allotment.\n"
            "- **Beyond 30 Days**: **Nil (0%)** exit load.\n"
            "- **Lock-in Period**: None (Open-ended equity scheme)."
            + SEBI_STATUTORY_DISCLAIMER
        )
        r3 = (
            "HDFC Top 100 Index Fund has a 3-year mandatory lock-in period with a flat 2.5% exit load at any time of withdrawal."
        )
        pairs.append(DPOPreferencePair(p3, c3, r3, "SID_PROSPECTUS_FABRICATION", reward_margin=3.0, fund_id="hdfc_top_100"))

        # Archetype 4: Mandatory Risk Disclosure Omission
        p4 = self.format_chat_prompt(
            "Compare Vanguard 500 Index Fund expense ratio and benchmark performance.",
            "Vanguard 500 Index Fund"
        )
        c4 = (
            "**Vanguard 500 Index Fund (VFIAX)** Overview:\n"
            "- **Expense Ratio**: Ultra-low **0.04%** (Direct Admiral Shares).\n"
            "- **Benchmark**: S&P 500 Index (Full physical replication).\n"
            "- **3-Year Historical CAGR**: **12.63%**.\n"
            "- **Beta**: **1.00** vs S&P 500."
            + "\n\n*SEC Rule 482 Notice: Past performance does not guarantee future results. "
            "Investments are subject to market fluctuation and principal value may decline upon redemption.*"
        )
        r4 = (
            "Vanguard 500 has a 0.04% expense ratio and beats the S&P 500 easily. Buy it now for instant gains without fees."
        )
        pairs.append(DPOPreferencePair(p4, c4, r4, "MISSING_STATUTORY_DISCLOSURE", reward_margin=2.0, fund_id="vanguard_500"))

        return pairs

    def compile_daily_dpo_dataset(
        self,
        audit_logs: Optional[List[Dict[str, Any]]] = None,
        include_synthetic: bool = True
    ) -> Dict[str, Any]:
        """
        Compiles all mined and synthetic pairs into a unified HuggingFace-compatible JSONL dataset.
        """
        start_ts = time.time()
        logger.info("Compiling daily DPO preference dataset...")
        all_pairs: List[DPOPreferencePair] = []

        if include_synthetic:
            synth_pairs = self.generate_synthetic_archetype_pairs()
            all_pairs.extend(synth_pairs)
            logger.info(f"Generated {len(synth_pairs)} foundational archetype DPO preference pairs.")

        if audit_logs:
            mined_count = 0
            for record in audit_logs:
                pair = self.generate_pair_from_intercept(record)
                if pair:
                    all_pairs.append(pair)
                    mined_count += 1
            logger.info(f"Mined {mined_count} preference pairs from live telemetry audit logs.")

        # Write to JSONL
        with open(self.dataset_file, "w", encoding="utf-8") as f:
            for pair in all_pairs:
                f.write(json.dumps(pair.to_dict()) + "\n")

        # Compute breakdown metrics
        breakdown: Dict[str, int] = {}
        for p in all_pairs:
            breakdown[p.violation_type] = breakdown.get(p.violation_type, 0) + 1

        duration_sec = round(time.time() - start_ts, 3)
        manifest = {
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_pairs": len(all_pairs),
            "output_file": str(self.dataset_file),
            "generation_duration_sec": duration_sec,
            "target_model": "Qwen2.5-Coder-1.5B-Instruct-GGUF-INT4",
            "loss_function": "DPO (Direct Preference Optimization, beta=0.1)",
            "violation_distribution": breakdown,
            "sample_pair": all_pairs[0].to_dict() if all_pairs else None,
        }

        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"[+] DPO Dataset generation complete: {len(all_pairs)} pairs exported to {self.dataset_file}")
        return manifest


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mutual Funds SLM DPO Preference Pair Generator")
    parser.add_argument("--logs-file", type=str, default=None, help="Path to telemetry interaction logs JSONL")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory for generated dataset")
    args = parser.parse_args()

    out_path = Path(args.out_dir) if args.out_dir else None
    generator = DPOPreferenceGenerator(output_dir=out_path)

    audit_records = []
    if args.logs_file and os.path.exists(args.logs_file):
        with open(args.logs_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        audit_records.append(json.loads(line))
                    except Exception:
                        pass

    manifest = generator.compile_daily_dpo_dataset(audit_logs=audit_records, include_synthetic=True)
    print(f"\n[+] DPO Generation Success: {manifest['total_pairs']} pairs created.")
    print(f"[+] Distribution: {json.dumps(manifest['violation_distribution'], indent=2)}")


if __name__ == "__main__":
    main()

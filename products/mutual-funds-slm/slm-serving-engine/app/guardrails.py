"""
Regulatory Compliance & Anti-Hallucination Guardrails Engine.
Frameworks: SEBI (Mutual Fund Regulations, India) & SEC (Rule 482 / FINRA 2210, US).
"""

import re
from typing import Dict, Any, List, Tuple


class RegulatoryGuardrailEngine:
    """
    Enforces statutory disclaimers, blocks promissory claims, and sanitizes PII.
    """

    MANDATORY_SEBI_DISCLAIMER = (
        "Mutual Fund investments are subject to market risks, read all scheme related documents carefully."
    )
    MANDATORY_SEC_DISCLAIMER = (
        "Past performance is no guarantee of future results. Investments are subject to market risk, including possible loss of principal."
    )

    PROMISSORY_PATTERNS = [
        r"\bguaranteed?\s+(?:returns?|profits?|yields?)\b",
        r"\b100%\s+(?:safe|risk[-\s]?free|guaranteed)\b",
        r"\bsure\s+profit\b",
        r"\bno\s+risk\s+involved\b",
        r"\bpromised?\s+returns?\b",
    ]

    PII_PATTERNS = [
        (r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", "[REDACTED_PAN]"),  # Indian PAN
        (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),          # US SSN
        (r"\b\d{9,18}\b", "[REDACTED_FOLIO_ACCOUNT]"),        # Bank / Folio number
    ]

    def __init__(self, jurisdiction: str = "DUAL"):
        self.jurisdiction = jurisdiction.upper()

    def inspect_and_sanitize(self, raw_text: str) -> Dict[str, Any]:
        """
        Runs comprehensive regulatory inspection and disclaimer enforcement.
        """
        violations: List[str] = []
        sanitized_text = raw_text

        # 1. PII Redaction
        for pattern, replacement in self.PII_PATTERNS:
            if re.search(pattern, sanitized_text):
                sanitized_text = re.sub(pattern, replacement, sanitized_text)
                violations.append("PII_REDACTED")

        # 2. Promissory return check
        has_promissory_claim = False
        for pattern in self.PROMISSORY_PATTERNS:
            if re.search(pattern, sanitized_text, re.IGNORECASE):
                has_promissory_claim = True
                violations.append("PROMISSORY_RETURN_BLOCKED")
                # Intercept and append warning
                sanitized_text = re.sub(
                    pattern, "[PROMISSORY CLAIM REDACTED - PROHIBITED BY REGULATION]", sanitized_text, flags=re.IGNORECASE
                )

        if has_promissory_claim:
            sanitized_text = (
                "⚠️ [REGULATORY INTERCEPT]: Prohibited forward-looking guarantee detected. "
                "Mutual fund regulations strictly prohibit promising guaranteed returns.\n\n" + sanitized_text
            )

        # 3. Statutory Disclaimers
        disclaimers = []
        if self.jurisdiction in ("SEBI", "DUAL"):
            if self.MANDATORY_SEBI_DISCLAIMER not in sanitized_text:
                disclaimers.append(self.MANDATORY_SEBI_DISCLAIMER)

        if self.jurisdiction in ("SEC", "DUAL"):
            if self.MANDATORY_SEC_DISCLAIMER not in sanitized_text:
                disclaimers.append(self.MANDATORY_SEC_DISCLAIMER)

        if disclaimers:
            sanitized_text += "\n\n" + "\n".join(f"📜 [Statutory Disclaimer]: {d}" for d in disclaimers)

        return {
            "sanitized_output": sanitized_text,
            "violations_intercepted": violations,
            "compliance_status": "APPROVED" if not violations else "APPROVED_WITH_MODIFICATIONS",
            "jurisdiction": self.jurisdiction,
            "audit_trail_valid": True,
        }

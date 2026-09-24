import re
from typing import Dict, List, Tuple


class PIIScrubber:
    """
    Enterprise-grade PII and Secret Sanitizer.
    Detects and redacts credentials, API keys, tokens, personal identifiers,
    and sensitive data before sending prompts or writing audit logs.
    """

    PATTERNS: List[Tuple[str, re.Pattern, str]] = [
        # 1. High-entropy Secrets & API Keys
        (
            "PRIVATE_KEY",
            re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
            "[REDACTED_PRIVATE_KEY]",
        ),
        (
            "ANTHROPIC_KEY",
            re.compile(r"\bsk-ant-[a-zA-Z0-9_-]{20,}\b"),
            "[REDACTED_ANTHROPIC_KEY]",
        ),
        (
            "OPENAI_KEY",
            re.compile(r"\bsk-[a-zA-Z0-9_-]{20,}\b"),
            "[REDACTED_OPENAI_KEY]",
        ),
        (
            "GOOGLE_KEY",
            re.compile(r"\bAIza[0-9A-Za-z_-]{30,42}\b"),
            "[REDACTED_GOOGLE_KEY]",
        ),

        (
            "GITHUB_TOKEN",
            re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"),
            "[REDACTED_GITHUB_TOKEN]",
        ),
        (
            "AWS_KEY",
            re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            "[REDACTED_AWS_KEY]",
        ),
        (
            "BEARER_TOKEN",
            re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
            "Bearer [REDACTED_TOKEN]",
        ),
        (
            "KEY_VALUE_SECRET",
            re.compile(r"(?i)\b(password|passwd|secret|client_secret|api_key|access_token|auth_token)\b\s*[:=]\s*['\"]?([^\s,'\"}\n]+)", re.IGNORECASE),
            r"\1: [REDACTED_SECRET]",
        ),

        # 2. PII (Personally Identifiable Information)
        (
            "EMAIL",
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "[REDACTED_EMAIL]",
        ),
        (
            "SSN",
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "[REDACTED_SSN]",
        ),
        (
            "CREDIT_CARD",
            re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
            "[REDACTED_CREDIT_CARD]",
        ),
        (
            "PHONE_NUMBER",
            re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
            "[REDACTED_PHONE]",
        ),
        (
            "IPV4_ADDRESS",
            re.compile(r"\b(?!127\.0\.0\.1|0\.0\.0\.0|255\.255\.255\.255)(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
            "[REDACTED_IP]",
        ),
    ]

    @classmethod
    def scrub(cls, text: str) -> str:
        """
        Replaces all detected secrets and PII with redaction tokens.
        """
        if not text or not isinstance(text, str):
            return text

        scrubbed = text
        for name, pattern, replacement in cls.PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    @classmethod
    def audit_findings(cls, text: str) -> Dict[str, int]:
        """
        Returns a count of each PII / secret type found in the text.
        """
        findings = {}
        if not text or not isinstance(text, str):
            return findings

        for name, pattern, _ in cls.PATTERNS:
            matches = pattern.findall(text)
            if matches:
                findings[name] = len(matches)
        return findings

    @classmethod
    def contains_pii(cls, text: str) -> bool:
        """
        Returns True if any sensitive token or PII was detected.
        """
        return len(cls.audit_findings(text)) > 0

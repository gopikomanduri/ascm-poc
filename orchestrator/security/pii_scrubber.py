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
            "GITHUB_FINE_GRAINED_TOKEN",
            re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
            "[REDACTED_GITHUB_TOKEN]",
        ),
        (
            "STRIPE_KEY",
            re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b|\bwhsec_[A-Za-z0-9_]{16,}\b"),
            "[REDACTED_STRIPE_KEY]",
        ),
        (
            "SLACK_TOKEN",
            re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
            "[REDACTED_SLACK_TOKEN]",
        ),
        (
            "JWT",
            re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
            "[REDACTED_JWT]",
        ),
        (
            "BASIC_AUTH",
            re.compile(r"\bBasic\s+[A-Za-z0-9+/=]{16,}", re.IGNORECASE),
            "Basic [REDACTED_CREDENTIALS]",
        ),
        (
            "URL_CREDENTIALS",
            re.compile(r"(?<=://)[^/\s:@]+:[^/\s@]+(?=@)"),
            "[REDACTED_CREDENTIALS]",
        ),
        (
            "AWS_KEY",
            re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
            "[REDACTED_AWS_KEY]",
        ),
        (
            "BEARER_TOKEN",
            re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
            "Bearer [REDACTED_TOKEN]",
        ),
        (
            "KEY_VALUE_SECRET",
            # Also matches JSON form ("password": "x") and keeps the quoting so structured logs stay valid.
            re.compile(
                r"(?P<k>\b(?:password|passwd|pwd|secret|client_secret|secret_key|private_key|api[_-]?key|apikey|"
                r"access_token|auth_token|refresh_token|aws_secret_access_key|authorization|token)\b)"
                r"(?P<q1>['\"]?)(?P<sep>\s*[:=]\s*)(?P<q2>['\"]?)(?!\[REDACTED|Bearer\b|Basic\b)(?P<v>[^\s,'\"}\n]+)",
                re.IGNORECASE,
            ),
            r"\g<k>\g<q1>\g<sep>\g<q2>[REDACTED_SECRET]",
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
            "AADHAAR",
            re.compile(r"(?<!\d)\d{4}[ -]\d{4}[ -]\d{4}(?!\d)"),
            "[REDACTED_AADHAAR]",
        ),
        (
            "PAN",
            re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
            "[REDACTED_PAN]",
        ),
        (
            "IN_PHONE_NUMBER",
            re.compile(r"(?<!\d)(?:\+91[-\s]?)[6-9]\d{9}(?!\d)|(?<![\d.])[6-9]\d{9}(?![\d.])"),
            "[REDACTED_PHONE]",
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

    _SECRET_KEY = re.compile(
        r"(password|passwd|pwd|secret|api[_-]?key|apikey|access_token|auth_token|refresh_token|private_key|"
        r"authorization|credential|^token$)", re.IGNORECASE,
    )

    @classmethod
    def scrub_structure(cls, value):
        """Scrub nested data: values under secret-looking keys are masked outright, other strings are pattern-scrubbed."""
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                if isinstance(k, str) and cls._SECRET_KEY.search(k) and not isinstance(v, (dict, list)):
                    specific = cls.scrub(v) if isinstance(v, str) else v
                    out[k] = specific if specific != v else "[REDACTED_SECRET]"
                else:
                    out[k] = cls.scrub_structure(v)
            return out
        if isinstance(value, (list, tuple)):
            return [cls.scrub_structure(v) for v in value]
        if isinstance(value, str):
            return cls.scrub(value)
        return value

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

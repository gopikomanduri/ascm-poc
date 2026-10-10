"""
Claims guard: keeps GTM agents honest.

- GROUNDING_RULES is appended to every content-writing agent's instructions.
- load_verified_facts() reads VERIFIED_FACTS.md: the only source of numbers/customers/proof
  that generated content may cite.
- audit_text()/audit_payload() flag unverified metrics, invented social proof, fake urgency,
  buzzwords and unresolved placeholders in generated content.
"""

import re
from pathlib import Path
from typing import Any, Dict, List

GROUNDING_RULES = (
    "\n\nHONESTY RULES (non-negotiable):\n"
    "- Use ONLY numbers, customers, benchmarks and results that appear under VERIFIED FACTS. "
    "If a fact is not listed, do not state it. Never invent percentages, multipliers, customer names, "
    "case studies, testimonials, PR counts, or coverage figures.\n"
    "- Never invent real people, email addresses, or things a real person 'recently posted'.\n"
    "- No fake urgency or scarcity ('last chance', 'filling up', 'only N spots').\n"
    "- No buzzwords: revolutionary, game-changing, AI-powered, cutting-edge, seamless, supercharge, "
    "unlock, next-gen, world-class.\n"
    "- Never leave bracket placeholders like [Link] or [URL]; use only links given in the input, "
    "otherwise omit the link.\n"
    "- Prefer specific mechanisms, concrete examples and honest limitations over hype. "
    "A founder who admits what does not work yet is more credible than a claim nobody can check.\n"
)

_BUZZWORDS = [
    "revolutioniz", "revolutionary", "game-changing", "game changing", "ai-powered", "cutting-edge",
    "seamless", "supercharge", "unlock", "next-gen", "world-class", "state-of-the-art", "paradigm",
]
_URGENCY = ["last chance", "filling up", "only a few spots", "act now", "limited time", "before it's too late"]
_METRIC = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s?(?:%|x\b|×|k\+|\+\s*(?:prs|customers|teams|companies|engineers))", re.I)
_COUNT_PROOF = re.compile(
    r"(?<![/.\d,])\b\d[\d,]*\+?\s+(?:prs|pull requests|customers|companies|teams|engineers|deployments|users|repos|repositories|services|microservices|agents|languages|tasks|models|benchmarks)\b", re.I)
_PROOF_PHRASES = re.compile(
    r"\b(case study|testimonial|our customers (?:report|saw|achieved)|companies (?:have )?(?:cut|reduced|shipped)"
    r"|we(?:'ve| have) seen (?:companies|teams))\b", re.I)
_URL = re.compile(r"https?://[^\s\"\')\]>,\\]+", re.I)
_PLACEHOLDER = re.compile(r"\[(?:link|url|insert|your|company|name|website)[^\]]*\]", re.I)


def load_verified_facts(repo_path: str = ".") -> str:
    """Return the text of VERIFIED_FACTS.md (repo root), or '' if absent."""
    for p in (Path(repo_path) / "VERIFIED_FACTS.md", Path(__file__).resolve().parents[3] / "VERIFIED_FACTS.md"):
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


def load_citable_facts(repo_path: str = ".") -> str:
    """VERIFIED_FACTS.md plus MATERIAL.md: numbers in either may be cited."""
    material = ""
    for p in (Path(repo_path) / "MATERIAL.md", Path(__file__).resolve().parents[3] / "MATERIAL.md"):
        if p.exists():
            material = p.read_text(encoding="utf-8")
            break
    return (load_verified_facts(repo_path) + "\n" + material).strip()


def facts_block(verified_facts: str) -> str:
    body = verified_facts.strip() or "(none provided: make NO quantitative or customer claims)"
    return f"\nVERIFIED FACTS (the only citable evidence):\n{body}\n"


def audit_text(text: str, verified_facts: str = "") -> List[Dict[str, str]]:
    """Return a list of {type, match} issues found in `text`."""
    issues: List[Dict[str, str]] = []
    low, facts_low = text.lower(), verified_facts.lower()

    for rx, kind in ((_METRIC, "unverified_metric"), (_COUNT_PROOF, "unverified_count")):
        for m in rx.finditer(text):
            if m.group(0).lower().strip() not in facts_low:
                issues.append({"type": kind, "match": m.group(0).strip()})
    for m in _PROOF_PHRASES.finditer(text):
        issues.append({"type": "invented_social_proof", "match": m.group(0)})
    for w in _BUZZWORDS:
        if w in low:
            issues.append({"type": "buzzword", "match": w})
    for w in _URGENCY:
        if w in low:
            issues.append({"type": "fake_urgency", "match": w})
    for m in _PLACEHOLDER.finditer(text):
        issues.append({"type": "placeholder", "match": m.group(0)})
    for m in _URL.finditer(text):      # links must come from the facts/input; models invent plausible-looking ones
        url = m.group(0).rstrip(".,;:")
        if url.lower() not in facts_low:
            issues.append({"type": "unverified_link", "match": url})
    return issues


def audit_payload(obj: Any, verified_facts: str = "") -> List[Dict[str, str]]:
    """Audit every string inside a nested dict/list structure."""
    out: List[Dict[str, str]] = []
    if isinstance(obj, str):
        out.extend(audit_text(obj, verified_facts))
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(audit_payload(v, verified_facts))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(audit_payload(v, verified_facts))
    return out


BLOCKING = {"unverified_link", "buzzword", "unverified_metric", "unverified_count", "invented_social_proof", "placeholder", "fake_urgency"}


def blocking_issues(issues: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [i for i in issues if i["type"] in BLOCKING]


def summarize(issues: List[Dict[str, str]], limit: int = 8) -> str:
    return "; ".join(f"{i['type']}: '{i['match']}'" for i in issues[:limit]) + (" ..." if len(issues) > limit else "")


def strip_placeholders(obj: Any) -> Any:
    """Remove unresolved bracket placeholders like [Link] from every string; tidies dangling 'Read more:' leftovers."""
    if isinstance(obj, str):
        out = _PLACEHOLDER.sub("", obj)
        out = re.sub(r"\s*(?:read more|learn more|see more|link|details|try it)\s*:?\s*$", "", out, flags=re.I)
        return re.sub(r"[ \t]{2,}", " ", out).rstrip(" :-\u2192")
    if isinstance(obj, dict):
        return {k: strip_placeholders(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [strip_placeholders(v) for v in obj]
    return obj

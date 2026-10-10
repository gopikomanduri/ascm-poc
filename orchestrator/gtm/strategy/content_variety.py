"""
Content variety: makes generated GTM content differ in *ideas*, not just wording.

- ANGLES / HOOK_STYLES: every post is assigned a distinct angle + hook style up front.
- PostHistory: remembers what was published; rejects drafts too similar to past or same-batch posts.
- load_material(): real founder material (stories, decisions, bugs) from MATERIAL.md, so there is more to say
  than the short VERIFIED_FACTS list.
- variety_report(): measures repetition (overlap, repeated claims, repeated openers) in a batch.
"""

import itertools
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ANGLES: Dict[str, str] = {
    "founder_story": "A first-person moment from building this: what happened and what you learned.",
    "honest_failure": "Something that did NOT work or is still weak, and what you are doing about it.",
    "benchmark_baseline": "An honest look at a measured result from VERIFIED FACTS, including its limits.",
    "mechanism_deep_dive": "How one specific part works under the hood, with a concrete example.",
    "contrarian_take": "A respectful disagreement with a common practice in AI coding tools.",
    "design_decision": "A real decision you faced, the options considered, and why you chose one.",
    "bug_postmortem": "A real bug found while building, how it was found, and the fix.",
    "question_to_community": "A genuine open question to engineers; no pitch, invite replies.",
    "build_log": "A short dated progress note: what changed this week and what is next.",
    "how_to_try": "A practical walkthrough of one thing a reader can try in 5 minutes.",
}

HOOK_STYLES: Dict[str, str] = {
    "question": "Open with a pointed question the reader has probably asked themselves.",
    "scene": "Open mid-scene with one concrete moment (a failing run, a diff, a log line).",
    "number": "Open with one number, only if it is in VERIFIED FACTS or MATERIAL.",
    "confession": "Open by admitting something that went wrong or that you got wrong.",
    "statement": "Open with a plain, specific claim; no hype words.",
}


def _ngrams(text: str, n: int = 3) -> set:
    w = re.findall(r"[a-z0-9%/.]+", text.lower())
    return set(zip(*[w[i:] for i in range(n)])) if len(w) >= n else set()


def similarity(a: str, b: str, n: int = 3) -> float:
    """Jaccard overlap of word n-grams (0 = nothing shared, 1 = identical)."""
    A, B = _ngrams(a, n), _ngrams(b, n)
    return len(A & B) / len(A | B) if (A or B) else 0.0


class PostHistory:
    """Persistent record of generated/published content, used to avoid repeating ourselves."""

    def __init__(self, path: str = ".ascm_history/content_history.json"):
        self.path = Path(path)

    def _load(self) -> List[dict]:
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return []

    def entries(self, channel: Optional[str] = None) -> List[dict]:
        return [e for e in self._load() if channel in (None, e.get("channel"))]

    def add(self, text: str, channel: str, angle: str = "", hook: str = "") -> None:
        data = self._load()
        data.append({"ts": datetime.now().isoformat(), "channel": channel, "angle": angle, "hook": hook, "text": text})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data[-500:], indent=2))

    def max_similarity(self, text: str, channel: Optional[str] = None) -> Tuple[float, str]:
        """Highest overlap between `text` and any earlier post (also returns that post's opening)."""
        best, opening = 0.0, ""
        for e in self.entries(channel):
            sim = max(similarity(text, e["text"], 3), similarity(text, e["text"], 4))
            if sim > best:
                best, opening = sim, e["text"][:80]
        return best, opening

    def is_duplicate(self, text: str, channel: Optional[str] = None, threshold: float = 0.25) -> bool:
        return self.max_similarity(text, channel)[0] >= threshold

    def recent_angles(self, n: int = 10) -> List[str]:
        return [e["angle"] for e in self._load()[-n:] if e.get("angle")]

    def recent_hooks(self, n: int = 5) -> List[str]:
        return [e["hook"] for e in self._load()[-n:] if e.get("hook")]


def assign_angles(count: int, history: Optional[PostHistory] = None, seed_offset: int = 0) -> List[Tuple[str, str]]:
    """Return `count` (angle, hook) pairs: distinct while angles last, least-recently-used first."""
    recent_a = history.recent_angles(20) if history else []
    recent_h = history.recent_hooks(10) if history else []

    def lru(options: Sequence[str], recent: List[str]) -> List[str]:
        # never used first, then oldest use first
        return sorted(options, key=lambda o: (recent[::-1].index(o) if o in recent else 10**6), reverse=True)

    angle_order = lru(list(ANGLES), recent_a)
    hook_order = lru(list(HOOK_STYLES), recent_h)
    out = []
    for i in range(count):
        k = i + seed_offset
        out.append((angle_order[k % len(angle_order)], hook_order[k % len(hook_order)]))
    return out


def angle_brief(angle: str, hook: str) -> str:
    return f"ANGLE: {angle}: {ANGLES[angle]}\nHOOK STYLE: {hook}: {HOOK_STYLES[hook]}"


def plan_block(pairs: Sequence[Tuple[str, str]]) -> str:
    """Prompt text assigning one angle + hook to each numbered post in a batch."""
    lines = [f"- Post {i + 1}: {angle_brief(a, h).replace(chr(10), ' | ')}" for i, (a, h) in enumerate(pairs)]
    return ("\nVARIETY PLAN (each post MUST follow its own angle and hook; do not reuse the same claim, "
            "number or opening in two posts):\n" + "\n".join(lines) + "\n")


def load_material(repo_path: str = ".") -> str:
    """Real founder material from MATERIAL.md (stories, decisions, bugs). Returns '' if absent."""
    for p in (Path(repo_path) / "MATERIAL.md", Path(__file__).resolve().parents[3] / "MATERIAL.md"):
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


def material_block(material: str) -> str:
    if not material.strip():
        return ""
    return ("\nREAL MATERIAL (true stories and details from the founder; draw on it for specifics. "
            "Do not embellish or add details that are not here):\n" + material.strip() + "\n")


def variety_report(posts: Sequence[str], history: Optional[PostHistory] = None, max_pair: float = 0.25) -> dict:
    """Measure repetition inside a batch (and against history)."""
    pairs = [(round(similarity(a, b), 3), i, j) for (i, a), (j, b) in itertools.combinations(enumerate(posts), 2)]
    openers = Counter(" ".join(p.split()[:3]).lower() for p in posts if p.strip())
    def _meaningful(tok: str) -> bool:      # skip years, dates and bare small integers
        t = tok.strip().rstrip(".,")
        return bool(t) and not re.fullmatch(r"(19|20)\d\d", t) and ("%" in t or "." in t or len(t) >= 3)
    nums = Counter(m.strip().rstrip(".,") for p in posts for m in set(re.findall(r"\b\d[\d,.]*\s?%?", p)) if _meaningful(m))
    limit = max(2, int(0.3 * len(posts)))   # repeating one number across a third of the batch is the real smell
    repeated_numbers = {k: v for k, v in nums.items() if v > limit}
    too_similar = [p for p in pairs if p[0] >= max_pair]
    opener_limit = max(1, len(posts) // 6)   # one reused opening in a big batch is fine; a pattern is not
    vs_history = [round(history.max_similarity(p)[0], 3) for p in posts] if history else []
    dup_history = [i for i, v in enumerate(vs_history) if v >= 0.25]
    return {
        "posts": len(posts),
        "max_pairwise_overlap": max((p[0] for p in pairs), default=0.0),
        "too_similar_pairs": too_similar,
        "repeated_openers": {k: v for k, v in openers.items() if v > opener_limit},
        "numbers_repeated_in_3plus_posts": repeated_numbers,
        "duplicates_of_history": dup_history,
        "needs_regeneration": bool(too_similar or repeated_numbers or dup_history
                                   or any(v > opener_limit for v in openers.values())),
    }

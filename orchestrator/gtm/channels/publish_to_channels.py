#!/usr/bin/env python3
"""
ASCM Milestone 1: Social Publisher
===================================
Generates AI-tailored posts for LinkedIn and X.com based on the user's actual
product/goal, then dispatches them cross-platform.

Dispatch modes (in order of preference):
  1. Buffer API   (scheduled posting) — set BUFFER_API_KEY + profile IDs
  2. Browser open (manual one-click)  — opens compose with pre-filled text
     • macOS  : `open` command
     • Linux  : `xdg-open`
     • Windows: `start`
  3. Clipboard copy — cross-platform (pyperclip fallback)

Usage:
  python main.py --gtm-publish
  python main.py --gtm-publish --goal "My SaaS product"
  python -m orchestrator.gtm.channels.publish_to_channels --goal "My SaaS"
"""

import os
import sys
import json
import logging
import subprocess
import urllib.parse
from orchestrator.gtm.strategy.content_variety import (PostHistory, assign_angles, angle_brief, material_block,
                                                        load_material)
from orchestrator.gtm.strategy.claims_guard import (GROUNDING_RULES, load_citable_facts, facts_block,
                                          audit_text, blocking_issues, summarize)
from orchestrator.agents.base import _load_dotenv
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

_load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ASCMSocialPublisher")


# ─── Cross-platform helpers ────────────────────────────────────────────────────

def _open_url(url: str) -> bool:
    """Open a URL in the default browser — cross-platform."""
    try:
        if sys.platform.startswith("darwin"):
            subprocess.run(["open", url], check=True)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", url], check=True)
        elif sys.platform.startswith("win"):
            subprocess.run(["start", "", url], shell=True, check=True)
        else:
            logger.warning(f"Unknown OS. Open manually: {url}")
            return False
        return True
    except Exception as e:
        logger.warning(f"Browser open failed: {e}. Open manually: {url}")
        return False


def _copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard — cross-platform (pbcopy / xclip / xsel / pyperclip)."""
    # macOS
    if sys.platform.startswith("darwin"):
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return True
        except Exception:
            pass

    # Linux
    elif sys.platform.startswith("linux"):
        for tool in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
            try:
                p = subprocess.Popen(tool, stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-8"))
                return True
            except FileNotFoundError:
                continue

    # Windows
    elif sys.platform.startswith("win"):
        try:
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
            p.communicate(text.encode("utf-8"))
            return True
        except Exception:
            pass

    # Pyperclip fallback
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        pass

    logger.warning("Clipboard unavailable. Copy the post text manually from the terminal output.")
    return False


# ─── Buffer API dispatch ────────────────────────────────────────────────────────

async def _buffer_schedule(platform: str, content: str, profile_env_var: str) -> Optional[str]:
    """Schedule a post via Buffer API. Returns post ID or None on failure."""
    api_key = os.getenv("BUFFER_API_KEY", "")
    profile_id = os.getenv(profile_env_var, "")
    if not (api_key and profile_id):
        return None

    try:
        import aiohttp
        payload = {
            "text": content,
            "profile_ids": [profile_id],
            "now": True,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.bufferapp.com/1/updates/create.json",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    post_id = data.get("id", "")
                    logger.info(f"[Buffer] ✅ {platform} post scheduled: {post_id}")
                    return post_id
                else:
                    logger.warning(f"[Buffer] HTTP {resp.status} for {platform}")
    except Exception as e:
        logger.warning(f"[Buffer] Failed: {e}")
    return None


# ─── AI Post Generator ──────────────────────────────────────────────────────────

def _generate_posts(product_goal: str, angle: str = "", hook: str = "", avoid: str = "") -> Dict[str, str]:
    """
    Use Gemini (or configured LLM) to generate platform-tailored posts.
    Falls back to template content if LLM is unavailable.
    """
    system_prompt = (
        "You are an expert B2B growth marketer writing social media posts for a technical startup.\n"
        "Tone: Authentic, insightful, not salesy. Written by a founder who deeply understands the pain.\n\n"
        "Rules:\n"
        "- LinkedIn: 50-80 words. Simple, short, crisp. Hook in line 1. 1-2 sentence paragraphs with line breaks. Punchy takeaway.\n"
        "- X.com: Max 180 chars. 1-2 sharp, punchy lines. High-signal founder punchline.\n"
        "- NO generic filler. Every sentence must deliver value to first-time founders.\n"
        "- Avoid buzzwords: 'revolutionary', 'game-changing', 'AI-powered'.\n"
        "- Do not put placeholder links in the post; leave the link out.\n\n"
        "Output JSON: {\"linkedin\": str, \"x_post\": str}"
        + GROUNDING_RULES
    )

    user_prompt = (
        f"Product/Goal: {product_goal}\n{facts_block(load_citable_facts())}{material_block(load_material())}\n"
        + (f"{angle_brief(angle, hook)}\n" if angle else "")
        + (f"Do NOT resemble these recent posts (new idea, new opening, new claim): {avoid}\n" if avoid else "")
        +
        "Generate one LinkedIn post and one X.com post that would resonate with CTOs, "
        "VP Engineering, and technical founders. Make them specific to the product described."
    )

    try:
        from google import genai
        client = genai.Client()
        model = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-3.5-flash-lite"
        resp = client.models.generate_content(
            model=model,
            contents=f"{system_prompt}\n\n{user_prompt}",
            config={"response_mime_type": "application/json", "temperature": 0.9},
        )
        data = json.loads(resp.text)
        if data.get("linkedin") and data.get("x_post"):
            logger.info("[PostGenerator] ✅ LLM-generated posts ready.")
            return data
    except Exception as e:
        logger.warning(f"[PostGenerator] LLM unavailable ({e}). Using template fallback.")

    # Template fallback (still contextualised with the goal)
    short_goal = product_goal[:80]
    return {
        "linkedin": (
            f"We've been building {short_goal}.\n\n"
            "Most tools in this space solve the surface problem. We went deeper.\n\n"
            "The pain we kept hitting: one feature touches several repos, and the requirements, "
            "architecture and review steps drift apart.\n\n"
            "So we're building an early-stage tool that plans and changes those repos together, "
            "with a human approval gate before any commit. It's a proof of concept and not everything works yet.\n\n"
            "Would love honest feedback from founders and engineering leads. Drop a comment or DM.\n\n"
            "#StartupBuilding #EngineeringLeadership #OpenSource"
        ),
        "x_post": (
            f"Building {short_goal[:60]}.\n\n"
            "One feature, several repos: coordination is the hard part.\n"
            "Early proof of concept, open source. Honest feedback welcome 👇"
        ),
    }


# ─── Core Publisher ─────────────────────────────────────────────────────────────

def _smart_truncate(text: str, max_chars: int = 270) -> str:
    """Truncates text safely at word boundaries without breaking URLs or words."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > int(max_chars * 0.6):
        return truncated[:last_space] + "..."
    return truncated + "..."


def _publish_linkedin(content: str) -> None:
    print("\n" + "─" * 60)
    print("📘  LINKEDIN")
    print("─" * 60)
    print(content)
    print("─" * 60)

    buffer_id = None
    try:
        import asyncio
        buffer_id = asyncio.run(_buffer_schedule("LinkedIn", content, "BUFFER_LINKEDIN_PROFILE_ID"))
    except Exception:
        pass

    if buffer_id:
        print(f"\n✅  Scheduled via Buffer: {buffer_id}")
    else:
        clipped = _copy_to_clipboard(content)
        print(f"\n📋  {'Copied to clipboard!' if clipped else 'Copy the post above manually.'}")
        print("🌐  Opening LinkedIn compose in browser...")
        _open_url("https://www.linkedin.com/feed/?shareActive=true")
        print("👉  Paste (Ctrl+V / Cmd+V) and click Post.")


def _publish_x(content: str) -> None:
    print("\n" + "─" * 60)
    print("🐦  X.COM")
    print("─" * 60)
    print(content)
    print("─" * 60)

    buffer_id = None
    try:
        import asyncio
        buffer_id = asyncio.run(_buffer_schedule("X.com", content, "BUFFER_TWITTER_PROFILE_ID"))
    except Exception:
        pass

    if buffer_id:
        print(f"\n✅  Scheduled via Buffer: {buffer_id}")
    else:
        # X intent URL with pre-filled text (capped safely)
        tweet_text = _smart_truncate(content, max_chars=270)
        encoded = urllib.parse.quote(tweet_text)
        x_url = f"https://twitter.com/intent/tweet?text={encoded}"
        print("\n🌐  Opening X.com compose with pre-filled tweet...")
        _open_url(x_url)
        print("👉  Click Post in your browser.")


def _save_log(goal: str, linkedin: str, x_post: str, angle: str = "", hook: str = "") -> None:  # empty string = not dispatched
    log_dir = Path(".ascm_history")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "social_publish_log.json"

    history = []
    if log_file.exists():
        try:
            history = json.loads(log_file.read_text())
        except Exception:
            history = []

    history.append({
        "timestamp": datetime.now().isoformat(),
        "goal": goal,
        "linkedin_dispatched_to_compose": bool(linkedin),
        "x_dispatched_to_compose": bool(x_post),
        "note": "Compose pages were opened or posts scheduled; this does not confirm the user clicked Post.",
        "buffer_configured": bool(os.getenv("BUFFER_API_KEY")),
    })

    log_file.write_text(json.dumps(history, indent=2))
    # Remember what we published so future drafts do not repeat it.
    content_history = PostHistory(str(log_dir / "content_history.json"))
    if linkedin:
        content_history.add(linkedin, "linkedin", angle, hook)
    if x_post:
        content_history.add(x_post, "x", angle, hook)
    logger.info(f"[Log] Saved to {log_file}")


# ─── Main entrypoint ────────────────────────────────────────────────────────────

def main(
    goal: Optional[str] = None,
    linkedin_only: bool = False,
    x_only: bool = False,
    interactive: bool = True,
) -> Dict[str, str]:
    import argparse
    parser = argparse.ArgumentParser(description="ASCM Milestone 1: Social Publisher")
    parser.add_argument("--goal", help="What you've built / what to post about")
    parser.add_argument("--linkedin-only", action="store_true", help="Post to LinkedIn only")
    parser.add_argument("--x-only", action="store_true", help="Post to X.com only")
    parser.add_argument("--no-prompt", action="store_true", help="Skip interactive preview prompt")
    args, _ = parser.parse_known_args()

    product_goal = goal or args.goal
    post_linkedin = (linkedin_only or args.linkedin_only) or not (x_only or args.x_only)
    post_x = (x_only or args.x_only) or not (linkedin_only or args.linkedin_only)
    is_interactive = interactive and not args.no_prompt

    # Try to load goal from mentor state if not provided
    if not product_goal:
        mentor_state = Path(".ascm_history/mentor_state.json")
        if mentor_state.exists():
            try:
                state = json.loads(mentor_state.read_text())
                product_goal = (
                    state.get("current_goal", {}).get("clarified_goal")
                    or state.get("current_goal", {}).get("clarified_goal", "")
                )
            except Exception:
                pass

    if not product_goal:
        try:
            product_goal = input("\n💡 What are you posting about? (describe your product/goal): ").strip()
        except (EOFError, KeyboardInterrupt):
            product_goal = "autonomous multi-agent software orchestration platform"

    print("\n" + "=" * 60)
    print("🚀  ASCM MILESTONE 1: SOCIAL PUBLISHER (NO-API BROWSER DISPATCH)")
    print("=" * 60)
    print(f"📌  Goal: {product_goal[:80]}...")
    print("\n⚡  Generating tailored posts with AI...")

    facts = load_citable_facts()
    history = PostHistory()
    angle_i = 0
    while True:
        # Pick the least-recently-used angle/hook; if the draft repeats earlier posts, try the next angle.
        for attempt in range(3):
            angle, hook = assign_angles(1, history, seed_offset=angle_i)[0]
            recent = " || ".join(e["text"][:100] for e in history.entries()[-3:])
            posts = _generate_posts(product_goal, angle, hook, avoid=recent)
            sim, similar_to = history.max_similarity(posts["linkedin"], "linkedin")
            sim_x, _ = history.max_similarity(posts["x_post"], "x")
            if max(sim, sim_x) < 0.25:
                break
            print(f"♻️  Draft too similar to a previous post ({max(sim, sim_x):.2f}: '{similar_to}...'); trying a new angle.")
            angle_i += 1
        duplicate_of_history = max(sim, sim_x) >= 0.25
        print(f"🎯 Angle: {angle} | Hook: {hook}")
        issues = audit_text(posts["linkedin"] + "\n" + posts["x_post"], facts)
        if blocking_issues(issues):
            print(f"\n⚠️  Claims check flagged the draft: {summarize(issues)}\n   Regenerating once...")
            posts = _generate_posts(f"{product_goal}\n(Previous draft was rejected for: {summarize(issues)}. Remove those.)")
            issues = audit_text(posts["linkedin"] + "\n" + posts["x_post"], facts)
        linkedin_content = posts["linkedin"]
        x_content = posts["x_post"]
        blocking = blocking_issues(issues)
        if issues:
            print(f"⚠️  Claims check: {summarize(issues)}")
        if duplicate_of_history and not is_interactive:
            print("\n⛔  Refusing to dispatch unattended: the draft repeats an earlier post (the LLM may be unavailable "
                  "and the template fallback was used again). Run interactively or try later.")
            return posts
        if blocking and not is_interactive:
            print("\n⛔  Refusing to dispatch unattended: the draft still contains unverified claims or placeholders.\n"
                  "   Add provable facts to VERIFIED_FACTS.md, or run interactively to review/edit.")
            return posts

        print("\n" + "=" * 60)
        print("📝  DRAFT PREVIEW")
        print("=" * 60)
        if post_linkedin:
            print("📘 [LinkedIn Preview]:\n" + linkedin_content + "\n")
        if post_x:
            print("🐦 [X.com Preview]:\n" + x_content + "\n")

        if is_interactive:
            try:
                prompt_text = (
                    "Options: [Enter] Open browser & publish | [r] Regenerate | [e] Edit copy | [q] Cancel\n"
                    "Choice: "
                )
                action = input(prompt_text).strip().lower()
            except (EOFError, KeyboardInterrupt):
                action = ""

            if action == "r":
                print("\n🔄 Regenerating copy...")
                continue
            elif action == "e":
                try:
                    custom_note = input("Enter custom hook or focus instruction: ").strip()
                    if custom_note:
                        product_goal = f"{product_goal} (Note: {custom_note})"
                        continue
                except (EOFError, KeyboardInterrupt):
                    pass
            elif action == "q":
                print("❌ Publishing canceled.")
                return posts
        break

    if post_linkedin:
        _publish_linkedin(linkedin_content)

    if post_x:
        _publish_x(x_content)

    _save_log(product_goal, linkedin_content if post_linkedin else "", x_content if post_x else "", angle, hook)

    print("\n" + "=" * 60)
    print("✅  MILESTONE 1 COMPLETE")
    if os.getenv("BUFFER_API_KEY"):
        print("   Posts scheduled via Buffer API.")
    else:
        print("   Browser launched! 1-click publish without API keys.")
    print("=" * 60 + "\n")
    return posts


if __name__ == "__main__":
    main()

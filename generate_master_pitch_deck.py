#!/usr/bin/env python3
"""
Generate the Master Pitch Deck for ASCM:
Focus:
- The World's First Proactive Engineering & Commercial Operating System
- Universal Cross-Platform Proactive Mentor (Goal Interception & Pre-Build Customer Validation)
- Built-In Zero-Setup Marketing & Outbound Sales Deal Closer
- In-depth, hard-hitting technical comparison vs. Claude Code, Antigravity, Codex/Cursor/Devin
- Formats: High-resolution PPTX and Landscape PDF
"""

import os
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.pdfgen import canvas

# ── Color Palette: Cyber Executive Obsidian / Gold / Electric Cyan ─────────────
C_BG = RGBColor(11, 15, 25)          # Deep Space Navy 950
C_CARD = RGBColor(22, 29, 49)        # Midnight Slate 900
C_ACCENT_GOLD = RGBColor(245, 158, 11) # Amber / Warm Gold
C_ACCENT_CYAN = RGBColor(14, 165, 233) # Sky Blue / Cyan
C_ACCENT_EMERALD = RGBColor(16, 185, 129) # Emerald Green
C_WHITE = RGBColor(255, 255, 255)
C_MUTED = RGBColor(148, 163, 184)    # Slate 400

def setup_presentation(prs):
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

def add_blank_slide(prs, bg_color):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = bg_color
    bg.line.fill.background()
    return slide

def add_header(slide, tag, title, subtitle="", tag_color=C_ACCENT_GOLD):
    # Tag
    tb_tag = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
    tf_tag = tb_tag.text_frame
    tf_tag.word_wrap = True
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = tag.upper()
    p_tag.font.bold = True
    p_tag.font.size = Pt(11)
    p_tag.font.color.rgb = tag_color

    # Title & Subtitle
    tb_t = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.9))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title
    p_t.font.bold = True
    p_t.font.size = Pt(24)
    p_t.font.color.rgb = C_WHITE

    if subtitle:
        p_sub = tf_t.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.size = Pt(12.5)
        p_sub.font.color.rgb = C_MUTED
        p_sub.space_before = Pt(3)

def add_card(slide, left, top, width, height, card_bg, border_color=None):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = card_bg
    if border_color:
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)
    else:
        card.line.fill.background()
    return card

def add_card_text(slide, left, top, width, height, title, items, title_color=C_WHITE, font_size=11):
    tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), width - Inches(0.4), height - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p_title = tf.paragraphs[0]
    p_title.text = title
    p_title.font.bold = True
    p_title.font.size = Pt(font_size + 3)
    p_title.font.color.rgb = title_color
    p_title.space_after = Pt(6)

    for item in items:
        p_item = tf.add_paragraph()
        p_item.text = f"•  {item}"
        p_item.font.size = Pt(font_size)
        p_item.font.color.rgb = RGBColor(226, 232, 240)
        p_item.space_after = Pt(3)


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD MASTER PPTX PITCH DECK
# ═══════════════════════════════════════════════════════════════════════════════

def build_pitch_deck_pptx(output_path: Path):
    prs = Presentation()
    setup_presentation(prs)

    # ── SLIDE 1: Vision / Cover Slide ──────────────────────────────────────────
    s1 = add_blank_slide(prs, C_BG)
    add_card(s1, Inches(1.2), Inches(1.2), Inches(10.93), Inches(5.1), C_CARD, C_ACCENT_GOLD)

    tb1 = s1.shapes.add_textbox(Inches(1.8), Inches(1.8), Inches(9.7), Inches(4.0))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    p = tf1.paragraphs[0]
    p.text = "ASCM PLATFORM (AUTONOMOUS SOFTWARE & COMMERCIAL MACHINE)"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = C_ACCENT_GOLD
    p.space_after = Pt(12)

    p2 = tf1.add_paragraph()
    p2.text = "The World's First Proactive Engineering\n& Commercial Operating System"
    p2.font.bold = True
    p2.font.size = Pt(34)
    p2.font.color.rgb = C_WHITE
    p2.space_after = Pt(16)

    p3 = tf1.add_paragraph()
    p3.text = "Why build in a vacuum? ASCM transforms passive code-assistants into an ambient AI co-founder:\nProactively intercepting goals, validating customer demand pre-build, engineering across multi-repo systems, and closing sales in 1 click."
    p3.font.size = Pt(14)
    p3.font.color.rgb = C_MUTED
    p3.space_after = Pt(24)

    p4 = tf1.add_paragraph()
    p4.text = "Investor & Executive Pitch Deck  |  Beyond Passive Autocomplete  |  Universal OS Daemon"
    p4.font.size = Pt(11)
    p4.font.color.rgb = C_ACCENT_CYAN

    # ── SLIDE 2: The Core Problem: The Passive Assistant Trap ─────────────────
    s2 = add_blank_slide(prs, C_BG)
    add_header(s2, "The Paradigm Breakdown", "The Fatal Flaws of Today's AI Coding Tools", "Claude Code, Cursor, Codex, and Devin wait for human prompts and ignore business reality.", C_ACCENT_GOLD)

    c_w = Inches(3.6)
    c_h = Inches(5.1)
    top_pos = Inches(1.7)

    add_card(s2, Inches(0.8), top_pos, c_w, c_h, C_CARD)
    add_card_text(s2, Inches(0.8), top_pos, c_w, c_h, "1. 100% Passive Nature", [
        "Tools only speak when spoken to. If you are typing bad architecture, they silently autocomplete it.",
        "Zero ambient awareness: The moment you switch to Excel, Notion, or your browser, they disappear.",
        "No proactive mentorship or guidance on whether what you're building is even worth building."
    ], C_ACCENT_GOLD)

    add_card(s2, Inches(4.8), top_pos, c_w, c_h, C_CARD)
    add_card_text(s2, Inches(4.8), top_pos, c_w, c_h, "2. Single-Repo Myopia", [
        "Real production systems span 5 to 50 microservices, SDKs, and frontend repos.",
        "Existing tools edit one file or one repo in isolation, breaking downstream consumer contracts.",
        "Confirmation bias: The same LLM writes code and its own unit tests, confirming its hallucinations."
    ], C_ACCENT_CYAN)

    add_card(s2, Inches(8.8), top_pos, c_w, c_h, C_CARD)
    add_card_text(s2, Inches(8.8), top_pos, c_w, c_h, "3. The Fatal 'Code Trap'", [
        "Technical founders spend 60 hours/week coding and 0 hours finding customers.",
        "They build for 6 months without speaking to a single buyer, only to launch to silence.",
        "Traditional GTM tools (Clay, Apollo, Smartlead) require days of DNS setup and manual CRM work."
    ], C_ACCENT_GOLD)

    # ── SLIDE 3: Detailed Competitive Comparison Table ────────────────────────
    s3 = add_blank_slide(prs, C_BG)
    add_header(s3, "Competitive Moat", "How ASCM Truly Differs from Claude Code, Antigravity & Codex", "Moving from reactive reactive chatbots to an ambient, proactive commercial operating system.", C_ACCENT_CYAN)

    # We build a structured comparison card
    add_card(s3, Inches(0.8), Inches(1.7), Inches(11.73), Inches(5.1), C_CARD, C_ACCENT_CYAN)
    
    # 3 Column side-by-side
    col_w = Inches(3.6)
    add_card_text(s3, Inches(1.0), Inches(1.9), col_w, Inches(4.7), "Claude Code & Codex/Cursor", [
        "Mode: Strictly Reactive (Prompt $\to$ Response).",
        "Scope: Single Repo / In-Editor local buffer.",
        "OS Integration: Confined to terminal or IDE window.",
        "Commercial Layer: None. Zero marketing or sales awareness.",
        "Demand Validation: None. Blindly writes code without asking who the buyer is.",
        "Multi-Service: Fails to detect cross-repo API contract breaks."
    ], C_MUTED, font_size=10.5)

    add_card_text(s3, Inches(5.0), Inches(1.9), col_w, Inches(4.7), "Antigravity & Agentic Frameworks", [
        "Mode: Semi-autonomous task runner (Subagent spawning).",
        "Scope: Broad tooling via CLI commands & bash execution.",
        "OS Integration: Process-bound to active agent invocation.",
        "Commercial Layer: Generic instructions; lacks integrated GTM forcing functions.",
        "Demand Validation: Requires user to formulate and drive PRD.",
        "Multi-Service: Generalist search, lacks multi-repo AST AST graph simulation."
    ], C_ACCENT_CYAN, font_size=10.5)

    add_card_text(s3, Inches(9.0), Inches(1.9), col_w, Inches(4.7), "ASCM Platform (The Difference)", [
        "Mode: Truly Proactive & Ambient (Nudges without prompt).",
        "Scope: Cross-Repo AST Dependency Graphs & Atomic PRs.",
        "OS Integration: Universal Daemon (macOS launchd, Linux systemd, Windows Tasks).",
        "Commercial Layer: Built-in Turnkey GTM (LinkedIn, X, Outbound Deal Closer).",
        "Demand Validation: Pre-Build Goal Interception (Secures 3 LOIs before coding).",
        "Multi-Service: Two-phase adversarial critics & contract proofs."
    ], C_ACCENT_GOLD, font_size=10.5)

    # ── SLIDE 4: Pillar 1: The Universal Proactive Mentor ───────────────────────
    s4 = add_blank_slide(prs, C_BG)
    add_header(s4, "Core Innovation #1", "The Universal Proactive Mentor: Beyond the Terminal", "An ambient AI co-founder active across Excel, your browser, and your IDE.", C_ACCENT_GOLD)

    add_card(s4, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.1), C_CARD)
    add_card_text(s4, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.1), "Ambient System-Level Presence", [
        "Runs as a lightweight native OS background daemon across macOS, Linux, and Windows.",
        "Not trapped in a terminal: Even when working in Excel or browsing, ASCM remains alert.",
        "Delivers native system banners and ambient modal prompt dialogs directly onto your desktop.",
        "Monitors git commit velocity, branch modifications, and test suite health continuously."
    ], C_ACCENT_GOLD)

    add_card(s4, Inches(6.8), Inches(1.7), Inches(5.6), Inches(5.1), C_CARD, C_ACCENT_GOLD)
    add_card_text(s4, Inches(6.8), Inches(1.7), Inches(5.6), Inches(5.1), "Goal Interception & Pre-Build Validation", [
        "Pre-Build Customer Validation: The moment you start a task, it pauses and asks: 'Who is the buyer? Can we get 3 design partner calls before writing backend logic?'",
        "Architectural Alternatives: Warns against premature optimization and suggests simpler, battle-tested options.",
        "Code-Avoidance Nudge: Tracks `activity_ratio = code_time / gtm_time`. Warns if you've been coding for 3 days without customer outreach.",
        "The Forcing Function: Ensures you build only what customers will pay for."
    ], C_ACCENT_GOLD)

    # ── SLIDE 5: Pillar 2: Autonomous Turnkey Marketing & Sales ───────────────
    s5 = add_blank_slide(prs, C_BG)
    add_header(s5, "Core Innovation #2", "Autonomous Turnkey Marketing & Sales: Zero Setup", "Turn git commits into revenue with 1 click — no DNS, SPF/DKIM, or API keys required.", C_ACCENT_CYAN)

    c_g_w = Inches(3.6)
    c_g_h = Inches(5.1)
    
    add_card(s5, Inches(0.8), Inches(1.7), c_g_w, c_g_h, C_CARD)
    add_card_text(s5, Inches(0.8), Inches(1.7), c_g_w, c_g_h, "Autonomous DevRel & Marketing", [
        "Automated Channel Ranking: Evaluates repo architecture to target LinkedIn, X, or Reddit.",
        "Contrarian Technical Hooks: Extracts unique architectural diffs into viral, thumb-stopping thought leadership.",
        "1-Click Clipboard Staging: Bypasses API paywalls by placing copy onto macOS clipboard and launching web composer tabs in 5 seconds."
    ], C_ACCENT_CYAN)

    add_card(s5, Inches(4.8), Inches(1.7), c_g_w, c_g_h, C_CARD)
    add_card_text(s5, Inches(4.8), Inches(1.7), c_g_w, c_g_h, "Autonomous B2B Deal Closer", [
        "ICP Lead Discovery: Finds VP Engineering, CTOs, and Platform Leads matching your exact tech stack.",
        "3-Touch Cadence Generation: Tailored outreach addressing prospects' real architectural debt.",
        "Cal.com Auto-Routing: Frictionless meeting scheduling directly into founder calendar.",
        "Zero-DNS Relays: Staged peer relays eliminate domain burnout and deliverability nightmares."
    ], C_ACCENT_GOLD)

    add_card(s5, Inches(8.8), Inches(1.7), c_g_w, c_g_h, C_CARD)
    add_card_text(s5, Inches(8.8), Inches(1.7), c_g_w, c_g_h, "Continuous Commercial Loop", [
        "Git Commit Anti-Procrastination Monitor: Blocks code merges if marketing actions are ignored.",
        "Live Objection Handling: Deterministic battlecards countering 'Cursor vs ASCM' and 'Build vs Buy'.",
        "Full Local Storage & Privacy: All pipeline states and customer data stored in local JSON with zero cloud CRM lock-in."
    ], C_ACCENT_EMERALD)

    # ── SLIDE 6: The Full Lifecycle: From Idea to Customer ───────────────────
    s6 = add_blank_slide(prs, C_BG)
    add_header(s6, "End-to-End Operating System", "How ASCM Operates as a Full-Lifecycle AI Co-Founder", "From raw idea inception to multi-repo deployment and closed commercial pipeline.", C_ACCENT_GOLD)

    c_step_w = Inches(2.7)
    c_step_h = Inches(5.1)

    add_card(s6, Inches(0.8), Inches(1.7), c_step_w, c_step_h, C_CARD)
    add_card_text(s6, Inches(0.8), Inches(1.7), c_step_w, c_step_h, "Step 1: Intercept & Validate", [
        "User defines goal.",
        "Mentor checks buyer ICP.",
        "Generates 3 LOI steps.",
        "Offers pre-build demand teaser.",
        "Prevents building unneeded software."
    ], C_ACCENT_GOLD)

    add_card(s6, Inches(3.8), Inches(1.7), c_step_w, c_step_h, C_CARD)
    add_card_text(s6, Inches(3.8), Inches(1.7), c_step_w, c_step_h, "Step 2: Multi-Repo Build", [
        "Cross-repo AST mapping.",
        "Synchronized atomic branches.",
        "Detects breaking changes across 5-50 microservices.",
        "Hermetic sandbox testing."
    ], C_ACCENT_CYAN)

    add_card(s6, Inches(6.8), Inches(1.7), c_step_w, c_step_h, C_CARD)
    add_card_text(s6, Inches(6.8), Inches(1.7), c_step_w, c_step_h, "Step 3: Adversarial Verification", [
        "Two-phase critic agents.",
        "Independent agents try to break code.",
        "Mathematical proofs & fuzzing.",
        "Eliminates LLM confirmation bias."
    ], C_ACCENT_EMERALD)

    add_card(s6, Inches(9.8), Inches(1.7), c_step_w, c_step_h, C_CARD)
    add_card_text(s6, Inches(9.8), Inches(1.7), c_step_w, c_step_h, "Step 4: Instant Monetization", [
        "Mentor detects milestone.",
        "Nudges: 'Time to sell!'.",
        "Launches LinkedIn/X post.",
        "Dispatches 10 CTO outreach emails.",
        "Books demo calls on Cal.com."
    ], C_ACCENT_GOLD)

    # ── SLIDE 7: Summary & Market Impact ──────────────────────────────────────
    s7 = add_blank_slide(prs, C_BG)
    add_header(s7, "The Investment Opportunity", "Why ASCM is the Future of Autonomous Software", "Redefining developer tooling: from passive code autocompletion to an autonomous commercial company builder.", C_ACCENT_GOLD)

    add_card(s7, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.1), C_CARD)
    add_card_text(s7, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.1), "Market Opportunity & Moat", [
        "Massive Addressable Market: 30M+ developers and 1M+ tech startups struggling to distribute products.",
        "Deep Competitive Moat: Cross-repo AST semantic graphs, two-phase adversarial critic verification, and multi-OS ambient daemons.",
        "Defensible Distribution: Solves the #1 reason startups fail (building things nobody wants and failing to sell)."
    ], C_ACCENT_CYAN)

    add_card(s7, Inches(6.8), Inches(1.7), Inches(5.6), Inches(5.1), C_CARD, C_ACCENT_GOLD)
    add_card_text(s7, Inches(6.8), Inches(1.7), Inches(5.6), Inches(5.1), "The Vision: An Autonomous Co-Founder in Every Repo", [
        "Every engineer gets an AI co-founder that mentors, builds, audits, and sells.",
        "No more 60-hour coding sprints followed by zero revenue.",
        "Available standalone as an ambient CLI / daemon or enterprise multi-repo platform.",
        "Production v1.0 Verified: 98/98 Passing Automated Tests."
    ], C_ACCENT_GOLD)

    prs.save(str(output_path))
    print(f"[+] Successfully generated Master Pitch Deck PPTX: {output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD MASTER PDF PITCH DECK (LANDSCAPE)
# ═══════════════════════════════════════════════════════════════════════════════

class SlideCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, total_pages):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(45, 25, "ASCM Master Pitch Deck  |  Autonomous Engineering & Commercial Operating System")
        page_text = f"Slide {self._pageNumber} of {total_pages}"
        self.drawRightString(747, 25, page_text)
        self.restoreState()


def build_pitch_deck_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(letter),
        leftMargin=40,
        rightMargin=40,
        topMargin=30,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    tag_style = ParagraphStyle(
        'DeckTag',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        textColor=colors.HexColor("#d97706"), # Amber 600
        spaceAfter=3,
        textTransform='uppercase'
    )
    
    title_style = ParagraphStyle(
        'DeckTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
        leading=23
    )

    sub_style = ParagraphStyle(
        'DeckSub',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
        leading=13
    )

    card_title_style = ParagraphStyle(
        'CardTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor("#0369a1"), # Sky 700
        spaceAfter=5,
        leading=14
    )

    body_style = ParagraphStyle(
        'CardBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=3,
        leading=11.5
    )

    story = []

    # Slide 1: Cover
    story.append(Spacer(1, 50))
    cover_table = Table([
        [Paragraph("<b>EXECUTIVE PITCH DECK</b>", tag_style)],
        [Paragraph("<b>ASCM Platform</b>", ParagraphStyle('CT', parent=title_style, fontSize=28, leading=34, textColor=colors.HexColor("#0f172a")))],
        [Paragraph("<b>The World's First Proactive Engineering & Commercial Operating System</b>", ParagraphStyle('CS', parent=sub_style, fontSize=13, leading=17, textColor=colors.HexColor("#d97706")))],
        [Spacer(1, 8)],
        [Paragraph("Transforming AI coding from passive autocomplete to an ambient, proactive co-founder that mentors your goals, validates customer demand pre-build, engineers across multi-repo systems, and closes deals.", ParagraphStyle('CD', parent=body_style, fontSize=10, leading=14))],
        [Spacer(1, 14)],
        [Paragraph("<b>Author:</b> ASCM Executive Squad  |  <b>Status:</b> Production v1.0 Verified (98/98 Passing Tests)  |  <b>Scope:</b> Universal macOS, Windows & Linux", ParagraphStyle('CM', parent=body_style, fontSize=8.5, fontName="Helvetica-Bold", textColor=colors.HexColor("#64748b")))]
    ], colWidths=[710])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor("#d97706")),
        ('PADDING', (0, 0), (-1, -1), 20),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # Slide Data
    slides_data = [
        # Slide 2: The Core Problem
        {
            "tag": "The Paradigm Breakdown",
            "title": "The Fatal Flaws of Today's AI Coding Tools",
            "subtitle": "Claude Code, Cursor, Codex, and Devin wait for human prompts and ignore business reality.",
            "cols": [
                {
                    "title": "1. 100% Passive Nature",
                    "items": [
                        "Tools only speak when spoken to. If you type bad architecture, they silently autocomplete it.",
                        "Zero ambient awareness: The moment you switch to Excel, Notion, or your browser, they disappear.",
                        "No proactive mentorship or guidance on whether what you are building is even worth building."
                    ]
                },
                {
                    "title": "2. Single-Repo Myopia",
                    "items": [
                        "Real production systems span 5 to 50 microservices, SDKs, and frontend repos.",
                        "Existing tools edit one file or one repo in isolation, breaking downstream consumer contracts.",
                        "Confirmation bias: The same LLM writes code and its own unit tests, confirming its hallucinations."
                    ]
                },
                {
                    "title": "3. The Fatal 'Code Trap'",
                    "items": [
                        "Technical founders spend 60 hours/week coding and 0 hours finding customers.",
                        "They build for 6 months without speaking to a single buyer, only to launch to silence.",
                        "Traditional GTM tools (Clay, Apollo, Smartlead) require days of DNS setup and manual CRM work."
                    ]
                }
            ]
        },
        # Slide 3: Detailed Comparison vs Claude Code, Antigravity, Codex
        {
            "tag": "Competitive Moat & Technical Comparison",
            "title": "How ASCM Differs from Claude Code, Antigravity & Codex",
            "subtitle": "Moving from reactive chatbots to an ambient, proactive commercial operating system.",
            "cols": [
                {
                    "title": "Claude Code & Codex/Cursor",
                    "items": [
                        "Interaction Mode: Strictly Reactive (Prompt $\to$ Response).",
                        "Architectural Scope: Single Repo / In-Editor local buffer.",
                        "OS Integration: Confined strictly to terminal or IDE window.",
                        "Commercial Layer: None. Zero marketing or sales awareness.",
                        "Demand Validation: None. Blindly writes code without asking who the buyer is.",
                        "Multi-Service: Fails to detect cross-repo API contract breaks."
                    ]
                },
                {
                    "title": "Antigravity & Agentic Frameworks",
                    "items": [
                        "Interaction Mode: Semi-autonomous task runner (Subagent spawning).",
                        "Architectural Scope: Broad tooling via CLI commands & bash execution.",
                        "OS Integration: Process-bound to active agent invocation.",
                        "Commercial Layer: Generic instructions; lacks integrated GTM forcing functions.",
                        "Demand Validation: Requires user to formulate and drive PRD.",
                        "Multi-Service: Generalist search, lacks multi-repo AST graph simulation."
                    ]
                },
                {
                    "title": "ASCM Platform (The Difference)",
                    "items": [
                        "Interaction Mode: Truly Proactive & Ambient (Nudges without prompt).",
                        "Architectural Scope: Cross-Repo AST Dependency Graphs & Atomic PRs.",
                        "OS Integration: Universal Daemon (macOS launchd, Linux systemd, Windows Tasks).",
                        "Commercial Layer: Built-in Turnkey GTM (LinkedIn, X, Outbound Deal Closer).",
                        "Demand Validation: Pre-Build Goal Interception (Secures 3 LOIs before coding).",
                        "Multi-Service: Two-phase adversarial critics & contract proofs."
                    ]
                }
            ]
        },
        # Slide 4: Pillar 1: Universal Proactive Mentor
        {
            "tag": "Core Innovation #1",
            "title": "The Universal Proactive Mentor: Beyond the Terminal",
            "subtitle": "An ambient AI co-founder active across Excel, your browser, and your IDE.",
            "cols": [
                {
                    "title": "Ambient System-Level Presence",
                    "items": [
                        "Runs as a lightweight native OS background daemon across macOS, Linux, and Windows.",
                        "Not trapped in a terminal: Even when working in Excel or browsing, ASCM remains alert.",
                        "Delivers native system banners and ambient modal prompt dialogs directly onto your desktop.",
                        "Monitors git commit velocity, branch modifications, and test suite health continuously."
                    ]
                },
                {
                    "title": "Goal Interception & Demand Validation",
                    "items": [
                        "Pre-Build Customer Validation: Pauses and asks: 'Who is the buyer? Can we get 3 design partner calls before writing backend logic?'",
                        "Architectural Alternatives: Warns against premature optimization and suggests simpler options.",
                        "Code-Avoidance Nudge: Tracks activity_ratio (code vs GTM). Warns if coding for 3 days without customer outreach.",
                        "The Forcing Function: Ensures you build only what customers will pay for."
                    ]
                }
            ]
        },
        # Slide 5: Pillar 2: Turnkey Marketing & Sales
        {
            "tag": "Core Innovation #2",
            "title": "Autonomous Turnkey Marketing & Sales: Zero Setup",
            "subtitle": "Turn git commits into revenue with 1 click — no DNS, SPF/DKIM, or API keys required.",
            "cols": [
                {
                    "title": "Autonomous DevRel & Marketing",
                    "items": [
                        "Automated Channel Ranking: Evaluates repo architecture to target LinkedIn, X, or Reddit.",
                        "Contrarian Technical Hooks: Extracts unique architectural diffs into viral thought leadership.",
                        "1-Click Clipboard Staging: Places copy onto macOS clipboard and launches web composer in 5s."
                    ]
                },
                {
                    "title": "Autonomous B2B Deal Closer",
                    "items": [
                        "ICP Lead Discovery: Finds VP Engineering & CTOs matching your exact tech stack.",
                        "3-Touch Cadence Generation: Tailored outreach addressing prospects' real architectural debt.",
                        "Cal.com Auto-Routing: Frictionless meeting scheduling directly into founder calendar.",
                        "Zero-DNS Relays: Staged peer relays eliminate domain burnout and deliverability issues."
                    ]
                },
                {
                    "title": "Continuous Commercial Loop",
                    "items": [
                        "Git Commit Anti-Procrastination Monitor: Blocks code merges if marketing actions are ignored.",
                        "Live Objection Handling: Deterministic battlecards countering 'Cursor vs ASCM' and 'Build vs Buy'.",
                        "Full Local Privacy: All pipeline states stored in local JSON with zero cloud CRM lock-in."
                    ]
                }
            ]
        },
        # Slide 6: The Full Lifecycle
        {
            "tag": "End-to-End Operating System",
            "title": "How ASCM Operates as a Full-Lifecycle AI Co-Founder",
            "subtitle": "From raw idea inception to multi-repo deployment and closed commercial pipeline.",
            "cols": [
                {
                    "title": "Step 1: Intercept & Validate",
                    "items": [
                        "User defines goal.",
                        "Mentor checks buyer ICP.",
                        "Generates 3 LOI steps.",
                        "Offers pre-build demand teaser.",
                        "Prevents building unneeded code."
                    ]
                },
                {
                    "title": "Step 2: Multi-Repo Build",
                    "items": [
                        "Cross-repo AST mapping.",
                        "Synchronized atomic branches.",
                        "Detects breaking changes across 5-50 microservices.",
                        "Hermetic sandbox testing."
                    ]
                },
                {
                    "title": "Step 3: Adversarial Verification",
                    "items": [
                        "Two-phase critic agents.",
                        "Independent agents try to break code.",
                        "Mathematical proofs & fuzzing.",
                        "Eliminates confirmation bias."
                    ]
                },
                {
                    "title": "Step 4: Instant Monetization",
                    "items": [
                        "Mentor detects milestone.",
                        "Nudges: 'Time to sell!'.",
                        "Launches LinkedIn/X post.",
                        "Dispatches 10 CTO outreach emails.",
                        "Books demo calls on Cal.com."
                    ]
                }
            ]
        },
        # Slide 7: Summary & Market Impact
        {
            "tag": "The Investment Opportunity",
            "title": "Why ASCM is the Future of Autonomous Software",
            "subtitle": "Redefining developer tooling: from passive code autocompletion to an autonomous commercial company builder.",
            "cols": [
                {
                    "title": "Market Opportunity & Moat",
                    "items": [
                        "Massive Addressable Market: 30M+ developers and 1M+ tech startups struggling to distribute products.",
                        "Deep Competitive Moat: Cross-repo AST semantic graphs, two-phase adversarial critic verification, and multi-OS ambient daemons.",
                        "Defensible Distribution: Solves the #1 reason startups fail (building things nobody wants and failing to sell)."
                    ]
                },
                {
                    "title": "The Vision: An Autonomous Co-Founder",
                    "items": [
                        "Every engineer gets an AI co-founder that mentors, builds, audits, and sells.",
                        "No more 60-hour coding sprints followed by zero revenue.",
                        "Available standalone as an ambient CLI / daemon or enterprise multi-repo platform.",
                        "Production v1.0 Verified: 98/98 Passing Automated Tests."
                    ]
                }
            ]
        }
    ]

    for slide in slides_data:
        story.append(Paragraph(slide["tag"], tag_style))
        story.append(Paragraph(slide["title"], title_style))
        story.append(Paragraph(slide["subtitle"], sub_style))

        cols = slide["cols"]
        num_cols = len(cols)
        col_w = 710 / num_cols
        
        card_cells = []
        for c in cols:
            cell_items = [
                Paragraph(f"<b>{c['title']}</b>", card_title_style),
                Spacer(1, 4)
            ]
            for it in c["items"]:
                cell_items.append(Paragraph(f"• {it}", body_style))
                cell_items.append(Spacer(1, 2))
            card_cells.append(cell_items)

        t = Table([card_cells], colWidths=[col_w] * num_cols)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.75, colors.HexColor("#e2e8f0")),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t)
        story.append(PageBreak())

    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc.build(story, canvasmaker=SlideCanvas)
    print(f"[+] Successfully generated Master Pitch Deck PDF: {output_path}")


if __name__ == "__main__":
    decks_dir = Path(__file__).resolve().parent / "decks"
    decks_dir.mkdir(parents=True, exist_ok=True)

    pptx_out = decks_dir / "ascm_master_pitch_deck.pptx"
    pdf_out = decks_dir / "ascm_master_pitch_deck.pdf"

    build_pitch_deck_pptx(pptx_out)
    build_pitch_deck_pdf(pdf_out)
    print("\n[+] Master Pitch Decks (PPTX + PDF) successfully generated!")

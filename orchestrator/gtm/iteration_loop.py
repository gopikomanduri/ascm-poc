"""
Reply-to-Iteration Loop: Learn from what works, iterate automatically

Tracks:
- Which email subjects get replies
- Which pain points resonate
- Which CTAs convert
- Reply sentiment distribution

Then:
- Auto-refines sequences based on what works
- Eliminates failing angles
- Doubles down on winning angles
- Reports performance weekly

Philosophy: Data-driven GTM beats gut-feeling GTM.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class EmailPerformance:
    """Track performance of single email"""
    email_id: str
    subject: str
    body_snippet: str
    pain_point: str
    cta: str
    sent_date: str
    sent_to_count: int
    reply_count: int
    reply_rate: float  # 0.0 - 1.0
    sentiment_breakdown: Dict[str, int]  # {"INTERESTED": 5, "OBJECTION": 2, ...}
    dominant_sentiment: str


@dataclass
class PerformanceReport:
    """Weekly GTM performance report with iteration recommendations"""
    week_start: str
    week_end: str
    total_emails_sent: int
    total_replies: int
    overall_reply_rate: float
    best_performing_subject: str
    best_performing_pain_point: str
    worst_performing_pain_point: str
    best_performing_cta: str
    sentiment_breakdown: Dict[str, int]
    recommendations: List[str]


class IterationLoop:
    """
    Learns from reply data and recommends iteration.
    """

    def __init__(self):
        self.email_performances: List[EmailPerformance] = []
        self.iteration_history: List[Dict[str, Any]] = []

    def track_email_performance(
        self,
        email_id: str,
        subject: str,
        body_snippet: str,
        pain_point: str,
        cta: str,
        sent_to: List[str],
        replies: List[Dict[str, str]],  # {email, sentiment, body}
    ):
        """Track performance of sent email"""
        sent_count = len(sent_to)
        reply_list = replies if isinstance(replies, list) else []
        reply_count = len(reply_list)
        reply_rate = reply_count / max(sent_count, 1)

        # Breakdown sentiment
        sentiment_breakdown = Counter(r.get("sentiment", "UNKNOWN") for r in reply_list)
        dominant_sentiment = sentiment_breakdown.most_common(1)[0][0] if sentiment_breakdown else "UNKNOWN"

        perf = EmailPerformance(
            email_id=email_id,
            subject=subject,
            body_snippet=body_snippet[:100],
            pain_point=pain_point,
            cta=cta,
            sent_date=datetime.now().isoformat(),
            sent_to_count=sent_count,
            reply_count=reply_count,
            reply_rate=reply_rate,
            sentiment_breakdown=dict(sentiment_breakdown),
            dominant_sentiment=dominant_sentiment,
        )

        self.email_performances.append(perf)
        logger.info(
            f"Email tracked: {email_id}, "
            f"Sent: {sent_count}, Replies: {reply_count} ({reply_rate:.1%}), "
            f"Sentiment: {dominant_sentiment}"
        )

    def get_best_performing_emails(self, limit: int = 5) -> List[EmailPerformance]:
        """Get top performing emails by reply rate"""
        sorted_emails = sorted(
            self.email_performances,
            key=lambda e: e.reply_rate,
            reverse=True
        )
        return sorted_emails[:limit]

    def get_worst_performing_emails(self, limit: int = 3) -> List[EmailPerformance]:
        """Get bottom performing emails"""
        sorted_emails = sorted(
            self.email_performances,
            key=lambda e: e.reply_rate
        )
        return sorted_emails[:limit]

    def analyze_pain_point_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze which pain points get highest reply rates.

        Returns: {pain_point: {reply_rate, avg_sentiment, count}}
        """
        pain_point_stats = {}

        for email in self.email_performances:
            pp = email.pain_point
            if pp not in pain_point_stats:
                pain_point_stats[pp] = {
                    "emails": [],
                    "total_sent": 0,
                    "total_replies": 0,
                }

            pain_point_stats[pp]["emails"].append(email)
            pain_point_stats[pp]["total_sent"] += email.sent_to_count
            pain_point_stats[pp]["total_replies"] += email.reply_count

        # Calculate rates
        for pp, stats in pain_point_stats.items():
            stats["reply_rate"] = stats["total_replies"] / max(stats["total_sent"], 1)
            stats["count"] = len(stats["emails"])

        return pain_point_stats

    def analyze_cta_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze which CTAs convert best.

        Returns: {cta: {reply_rate, interested_count, count}}
        """
        cta_stats = {}

        for email in self.email_performances:
            cta = email.cta or "no_cta"
            if cta not in cta_stats:
                cta_stats[cta] = {
                    "emails": [],
                    "total_sent": 0,
                    "total_replies": 0,
                    "interested_replies": 0,
                }

            cta_stats[cta]["emails"].append(email)
            cta_stats[cta]["total_sent"] += email.sent_to_count
            cta_stats[cta]["total_replies"] += email.reply_count
            cta_stats[cta]["interested_replies"] += email.sentiment_breakdown.get("INTERESTED", 0)

        # Calculate rates
        for cta, stats in cta_stats.items():
            stats["reply_rate"] = stats["total_replies"] / max(stats["total_sent"], 1)
            stats["interested_rate"] = stats["interested_replies"] / max(stats["total_replies"], 1)
            stats["count"] = len(stats["emails"])

        return cta_stats

    def generate_weekly_report(self) -> PerformanceReport:
        """
        Generate weekly performance report with recommendations.
        """
        if not self.email_performances:
            return PerformanceReport(
                week_start=datetime.now().isoformat(),
                week_end=(datetime.now() + timedelta(days=7)).isoformat(),
                total_emails_sent=0,
                total_replies=0,
                overall_reply_rate=0.0,
                best_performing_subject="N/A",
                best_performing_pain_point="N/A",
                worst_performing_pain_point="N/A",
                best_performing_cta="N/A",
                sentiment_breakdown={},
                recommendations=["No email data yet. Send more emails to generate insights."],
            )

        # Aggregate stats
        total_sent = sum(e.sent_to_count for e in self.email_performances)
        total_replies = sum(e.reply_count for e in self.email_performances)
        overall_reply_rate = total_replies / max(total_sent, 1)

        # Best emails
        best_emails = self.get_best_performing_emails(1)
        best_subject = best_emails[0].subject if best_emails else "N/A"

        # Pain point analysis
        pp_stats = self.analyze_pain_point_performance()
        best_pp = max(pp_stats.items(), key=lambda x: x[1]["reply_rate"])
        worst_pp = min(pp_stats.items(), key=lambda x: x[1]["reply_rate"])

        best_pp_name = best_pp[0]
        worst_pp_name = worst_pp[0]

        # CTA analysis
        cta_stats = self.analyze_cta_performance()
        best_cta = max(cta_stats.items(), key=lambda x: x[1]["interested_rate"])
        best_cta_name = best_cta[0]

        # Sentiment breakdown
        sentiment_totals = Counter()
        for email in self.email_performances:
            sentiment_totals.update(email.sentiment_breakdown)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            pp_stats, cta_stats, best_pp_name, worst_pp_name, overall_reply_rate
        )

        report = PerformanceReport(
            week_start=(datetime.now() - timedelta(days=7)).isoformat(),
            week_end=datetime.now().isoformat(),
            total_emails_sent=total_sent,
            total_replies=total_replies,
            overall_reply_rate=overall_reply_rate,
            best_performing_subject=best_subject,
            best_performing_pain_point=best_pp_name,
            worst_performing_pain_point=worst_pp_name,
            best_performing_cta=best_cta_name,
            sentiment_breakdown=dict(sentiment_totals),
            recommendations=recommendations,
        )

        return report

    def _generate_recommendations(
        self,
        pp_stats: Dict[str, Dict[str, Any]],
        cta_stats: Dict[str, Dict[str, Any]],
        best_pp: str,
        worst_pp: str,
        overall_reply_rate: float,
    ) -> List[str]:
        """Generate iteration recommendations based on data"""
        recommendations = []

        # Pain point recommendations
        if best_pp != worst_pp:
            best_rate = pp_stats[best_pp]["reply_rate"]
            worst_rate = pp_stats[worst_pp]["reply_rate"]
            improvement = (best_rate - worst_rate) / max(worst_rate, 0.01) * 100

            recommendations.append(
                f"🎯 PAIN POINT: '{best_pp}' gets {best_rate:.1%} reply rate "
                f"vs '{worst_pp}' at {worst_rate:.1%}. "
                f"Pivot messaging {improvement:.0f}% towards '{best_pp}' next week."
            )

        # Reply rate threshold
        if overall_reply_rate < 0.05:
            recommendations.append(
                f"⚠️ REPLY RATE: {overall_reply_rate:.1%} is low (target 5-8%). "
                f"Consider: different subject lines, personalization, or ICP refinement."
            )
        elif overall_reply_rate > 0.12:
            recommendations.append(
                f"✅ REPLY RATE: {overall_reply_rate:.1%} is excellent! "
                f"Scale outreach volume 2-3x."
            )

        # CTA recommendations
        top_cta = max(cta_stats.items(), key=lambda x: x[1]["interested_rate"])
        if top_cta[0] != "no_cta":
            recommendations.append(
                f"💡 CTA: '{top_cta[0]}' converts best. "
                f"Use it in {top_cta[1]['interested_rate']:.0%} of next sequence."
            )

        # Sentiment recommendations
        interested_count = sum(
            e.sentiment_breakdown.get("INTERESTED", 0) for e in self.email_performances
        )
        if interested_count > 0:
            recommendations.append(
                f"📈 INTERESTED: {interested_count} prospects showed interest. "
                f"Book calls immediately, don't let momentum die."
            )

        return recommendations

    def export_report(self, filepath: str, report: PerformanceReport):
        """Export performance report to file"""
        report_dict = asdict(report)
        with open(filepath, "w") as f:
            json.dump(report_dict, f, indent=2)
        logger.info(f"Performance report exported to {filepath}")

    def log_iteration(self, iteration_num: int, changes: Dict[str, Any]):
        """Log iteration changes"""
        iteration = {
            "iteration": iteration_num,
            "timestamp": datetime.now().isoformat(),
            "changes": changes,
        }
        self.iteration_history.append(iteration)
        logger.info(f"Iteration {iteration_num} logged: {changes}")

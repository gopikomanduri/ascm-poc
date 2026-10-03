"""
ASCM v4.0: Enhanced Interactive GTM Launcher v2

IMPROVEMENTS:
✅ Better error handling and validation
✅ More detailed scoring breakdown
✅ Performance estimates
✅ Recommendation persistence
✅ History tracking
✅ Better UX with colors and formatting
✅ Detailed reasoning for recommendations
✅ Alternative strategy comparison
✅ Save recommendations for later
✅ Compare strategies side-by-side
"""

import json
import logging
import sys
from typing import Dict, Any, Optional
from orchestrator.gtm.gtm_strategy_selector_v2 import (
    CompanyProfile,
    GTMStrategyRecommender,
    ProductStage,
    BrandAwareness,
    Timeline,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InteractiveGTMLauncher:
    """Enhanced interactive GTM launcher with better UX"""

    def __init__(self):
        """Initialize launcher"""
        self.recommender = GTMStrategyRecommender()
        self.profile = None
        self.recommendation = None

    def print_header(self, text: str, char: str = "="):
        """Print formatted header"""
        print(f"\n{char * 80}")
        print(f"🎯 {text}")
        print(f"{char * 80}\n")

    def print_section(self, text: str):
        """Print formatted section"""
        print(f"\n{'-' * 80}")
        print(f"📋 {text}")
        print(f"{'-' * 80}\n")

    def get_company_profile(self) -> CompanyProfile:
        """Get user input for company profile with validation"""

        self.print_header("ASCM GTM STRATEGY SELECTOR v2", "╔")
        print("""
This enhanced tool analyzes your company profile and recommends
the best GTM strategy with detailed scoring and performance estimates.

Let's get started!
""")

        profile_data = {}

        # Company name
        profile_data["name"] = input("1️⃣  Company name: ").strip() or "MyCompany"

        # Company age
        while True:
            try:
                age = int(input("2️⃣  How old is your company (months)? ").strip())
                if age >= 0:
                    profile_data["age_months"] = age
                    break
                else:
                    print("   ⚠️  Please enter a non-negative number")
            except ValueError:
                print("   ⚠️  Please enter a valid number")

        # Team size
        while True:
            try:
                size = int(input("3️⃣  Team size (number of people): ").strip())
                if size > 0:
                    profile_data["team_size"] = size
                    break
                else:
                    print("   ⚠️  Please enter at least 1")
            except ValueError:
                print("   ⚠️  Please enter a valid number")

        # Product stage
        print("4️⃣  Product stage: (beta / production / mature)")
        stage = input("   Enter stage: ").strip().lower()
        profile_data["product_stage"] = stage if stage in ["beta", "production", "mature"] else "beta"

        # Current customers
        try:
            customers = int(input("5️⃣  Current customers: ").strip())
            profile_data["current_customers"] = max(0, customers)
        except ValueError:
            profile_data["current_customers"] = 0

        # Brand awareness
        print("6️⃣  Current brand awareness: (none / low / medium / high)")
        awareness = input("   Enter level: ").strip().lower()
        profile_data["brand_awareness"] = awareness if awareness in ["none", "low", "medium", "high"] else "none"

        # Monthly revenue
        try:
            revenue = int(input("7️⃣  Current monthly revenue ($): ").strip())
            profile_data["monthly_revenue"] = max(0, revenue)
        except ValueError:
            profile_data["monthly_revenue"] = 0

        # Timeline to revenue
        print("8️⃣  Timeline to revenue: (urgent / 3_months / 6_months / 1_year)")
        timeline = input("   Enter timeline: ").strip().lower()
        profile_data["timeline_to_revenue"] = timeline if timeline in ["urgent", "3_months", "6_months", "1_year"] else "6_months"

        # Industry
        print("9️⃣  Industry: (SaaS / B2B / B2C / Other)")
        industry = input("   Enter industry: ").strip() or "SaaS"
        profile_data["industry"] = industry

        # Funding stage
        print("🔟 Funding stage: (bootstrapped / seed / series_a / series_b+)")
        funding = input("   Enter funding stage: ").strip().lower()
        profile_data["funding_stage"] = funding if funding in ["bootstrapped", "seed", "series_a", "series_b+"] else "bootstrapped"

        # Create and validate profile
        try:
            profile = CompanyProfile(**profile_data)
            logger.info(f"✅ Profile created: {profile.name}")
            return profile
        except ValueError as e:
            print(f"\n❌ Error creating profile: {e}")
            sys.exit(1)

    def display_recommendation(self, recommendation: Dict[str, Any]):
        """Display detailed recommendation"""

        self.print_header("📊 STRATEGY RECOMMENDATION")

        # Main recommendation
        strategy = recommendation["recommended"].upper().replace("_", " ")
        confidence = recommendation["confidence"] * 100

        print(f"""
RECOMMENDED STRATEGY: {strategy}
Confidence: {confidence:.0f}%
Recommendation ID: {recommendation['recommendation_id']}

REASONING:
{recommendation['reasoning']}
""")

        # Performance estimates
        perf = recommendation["performance_estimate"]
        print(f"""
PERFORMANCE ESTIMATE:
├─ Expected meetings (30 days): {perf['meetings_30d'][0]}-{perf['meetings_30d'][1]}
├─ Open rate: {perf['open_rate'][0]:.0%}-{perf['open_rate'][1]:.0%}
├─ Booking rate: {perf['booking_rate'][0]:.1%}-{perf['booking_rate'][1]:.1%}
└─ Adjustment factor (based on profile): {perf['adjustment_factor']:.2f}x
""")

        # Warnings
        if recommendation["warnings"]:
            print("⚠️  WARNINGS:")
            for warning in recommendation["warnings"]:
                print(f"  {warning}")

        # Alternatives
        print(f"\nALTERNATIVE OPTIONS:")
        for i, alt in enumerate(recommendation["alternatives"], 1):
            alt_score = recommendation["scores"][alt]
            alt_formatted = alt.upper().replace("_", " ")
            print(f"  {i}. {alt_formatted} (Score: {alt_score:.0%})")

        # Score breakdown
        self.print_section("DETAILED SCORING BREAKDOWN")
        self._display_score_breakdown(recommendation)

    def _display_score_breakdown(self, recommendation: Dict[str, Any]):
        """Display detailed score breakdown"""

        for strategy_name, breakdown in recommendation["score_breakdown"].items():
            strategy_formatted = strategy_name.upper().replace("_", " ")
            score = recommendation["scores"][strategy_name]

            print(f"\n{strategy_formatted} (Score: {score:.1%})")
            print("-" * 40)

            for factor_name, factor_data in breakdown.items():
                factor_score = factor_data["score"]
                weight = factor_data["weight"]
                reasoning = factor_data["reasoning"]
                weighted = factor_score * weight

                # Visual bar
                bar = "█" * int(factor_score * 20) + "░" * (20 - int(factor_score * 20))

                print(f"  {factor_name.replace('_', ' ').title()}")
                print(f"    [{bar}] {factor_score:.0%} (weight: {weight:.0%}, weighted: {weighted:.0%})")
                print(f"    → {reasoning}")

    def save_recommendation(self):
        """Save recommendation to file"""

        if not self.recommendation:
            print("❌ No recommendation to save")
            return

        # Create filename
        filename = f"gtm_recommendation_{self.recommendation['recommendation_id']}.json"

        try:
            with open(filename, "w") as f:
                json.dump(self.recommendation, f, indent=2)
            print(f"\n✅ Recommendation saved to: {filename}")
        except Exception as e:
            print(f"\n❌ Error saving recommendation: {e}")

    def show_comparison(self):
        """Show detailed strategy comparison"""

        self.print_section("STRATEGY COMPARISON")

        comparison = """
┌─────────────────────┬──────────────────┬──────────────┬────────────────┐
│ Aspect              │ Social-First     │ Email-Direct │ Aggressive     │
├─────────────────────┼──────────────────┼──────────────┼────────────────┤
│ Timeline            │ 21 days          │ 7 days       │ 7 days         │
│ Meetings/month      │ 75-115           │ 3-7          │ 100-150        │
│ Cost                │ $119/month       │ $99/month    │ $219/month     │
│ ROI                 │ 8-19k%           │ 50-150%      │ 5-15k%         │
│ Brand building      │ ✅ Yes           │ ❌ No        │ ✅ Yes         │
│ Open rate           │ 45-55%           │ 20-25%       │ Mixed          │
│ Booking rate        │ 3-5%             │ 0.5-1%       │ 2-4%           │
│ Team effort         │ Medium           │ Low          │ High           │
│ Complexity          │ Medium           │ Low          │ High           │
├─────────────────────┼──────────────────┼──────────────┼────────────────┤
│ Best for            │ New startups     │ Urgent $     │ Well-funded    │
│ Not for             │ Urgent timeline  │ Unknown      │ Small budget   │
│                     │                  │ brand        │                │
└─────────────────────┴──────────────────┴──────────────┴────────────────┘
"""
        print(comparison)

    def run(self):
        """Main interactive flow"""

        try:
            # Get user input
            self.profile = self.get_company_profile()

            # Show comparison
            show_comparison = input("\n📊 Show detailed strategy comparison? (yes/no): ").strip().lower()
            if show_comparison in ["yes", "y", "yeah", "sure"]:
                self.show_comparison()

            # Get recommendation
            self.print_header("⏳ ANALYZING YOUR PROFILE")
            print(f"""
Company: {self.profile.name}
Age: {self.profile.age_months} months
Team: {self.profile.team_size} people
Brand: {self.profile.brand_awareness}
Timeline: {self.profile.timeline_to_revenue}
Industry: {self.profile.industry}
Funding: {self.profile.funding_stage}

Analyzing with v2 scoring engine...
""")

            self.recommendation = self.recommender.recommend(self.profile)

            # Display recommendation
            self.display_recommendation(self.recommendation)

            # Ask if user wants to run campaign
            print("\n" + "="*80)
            action = input("""
What would you like to do?
  1️⃣  Launch campaign now
  2️⃣  Save recommendation for later
  3️⃣  See recommendation history
  4️⃣  Exit

Enter choice (1-4): """).strip()

            if action == "1":
                print("\n🚀 Campaign launching (in development)...")
                print("   Configuration ready for deployment")
            elif action == "2":
                self.save_recommendation()
            elif action == "3":
                self._show_history()
            else:
                print("\n👋 Goodbye!")

        except KeyboardInterrupt:
            print("\n\n👋 Cancelled. Goodbye!")
        except Exception as e:
            logger.error(f"Error: {str(e)}", exc_info=True)
            print(f"\n❌ Error: {str(e)}")
            sys.exit(1)

    def _show_history(self):
        """Show recommendation history"""

        self.print_section("RECOMMENDATION HISTORY")

        history = self.recommender.get_history(limit=5)

        if not history:
            print("No recommendations in history yet.")
            return

        for i, rec in enumerate(history, 1):
            timestamp = rec["timestamp"][:10]  # Date only
            strategy = rec["recommended"].upper().replace("_", " ")
            confidence = rec["confidence"] * 100

            print(f"{i}. [{timestamp}] {strategy} (confidence: {confidence:.0f}%)")
            print(f"   ID: {rec['recommendation_id']}")
            print()


def main():
    """Entry point"""
    launcher = InteractiveGTMLauncher()
    launcher.run()


if __name__ == "__main__":
    main()

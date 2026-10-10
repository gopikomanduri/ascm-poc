"""APM Agent: Application Performance Monitoring, SLO definitions, alerting."""
from typing import Dict, Any, Optional
import json
from .base import BaseAgent


class APMAgent(BaseAgent):
    """Application Performance Monitoring: SLOs, alerting, instrumentation."""

    def __init__(
        self,
        system_instruction: Optional[str] = None,
        provider: Optional[Any] = None,
        tier: str = "primary",
        model: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            system_instruction=system_instruction or "You are an APM Agent.",
            provider=provider,
            tier=tier,
            model=model,
        )

    def run(self, domain: str = "general", requirements: str = "", **kwargs) -> Dict[str, Any]:
        """Unified entrypoint for SLO definition and alerting."""
        reqs = requirements or kwargs.get("prd", "") or kwargs.get("goal", "")
        return self.define_slos(domain=domain, requirements=reqs)

    def define_slos(self, domain: str, requirements: str) -> Dict[str, Any]:
        """Define SLOs (Service Level Objectives)."""
        return {
            "domain": domain,
            "slos": {
                "p99_latency_ms": 500,
                "availability_pct": 99.9,
                "error_rate_pct": 0.1,
            }
        }

    def configure_alerts(self, slos: Dict[str, Any]) -> Dict[str, Any]:
        """Configure alerting rules."""
        return {
            "alerts": [
                {"name": "high_latency", "threshold": 1000, "severity": "WARNING"},
                {"name": "high_error_rate", "threshold": 1.0, "severity": "CRITICAL"},
                {"name": "availability_sla_miss", "threshold": 99.0, "severity": "CRITICAL"},
            ]
        }

    def setup_instrumentation(self, language: str) -> Dict[str, Any]:
        """Setup monitoring instrumentation."""
        return {
            "language": language,
            "instrumentation": "opentelemetry",
            "exporters": ["prometheus", "datadog"],
        }

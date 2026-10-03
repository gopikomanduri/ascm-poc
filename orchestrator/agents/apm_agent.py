"""APM Agent: Application Performance Monitoring, SLO definitions, alerting."""
from typing import Dict, Any, Optional
import json
from .base import BaseAgent


class APMAgent(BaseAgent):
    """Application Performance Monitoring: SLOs, alerting, instrumentation."""

    def __init__(self, model: Optional[str] = None):
        super().__init__(model=model, tier="primary")

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

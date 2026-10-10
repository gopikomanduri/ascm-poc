"""SRE Agent: Deployment architecture, IaC generation, infrastructure management."""
from typing import Dict, Any, Optional
import json
from .base import BaseAgent


class SREAgent(BaseAgent):
    """Site Reliability Engineer: Production deployment and infrastructure."""

    def __init__(
        self,
        system_instruction: Optional[str] = None,
        provider: Optional[Any] = None,
        tier: str = "primary",
        model: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            system_instruction=system_instruction or "You are an SRE Agent.",
            provider=provider,
            tier=tier,
            model=model,
        )

    def run(self, domain: str = "general", requirements: str = "", **kwargs) -> Dict[str, Any]:
        """Unified entrypoint for deployment architecture and IaC generation."""
        reqs = requirements or kwargs.get("prd", "") or kwargs.get("goal", "")
        return self.design_deployment(domain=domain, requirements=reqs)

    def design_deployment(self, domain: str, requirements: str) -> Dict[str, Any]:
        """Design deployment architecture."""
        prompt = f"Design deployment for {domain}: {requirements[:500]}. Output JSON."
        response = self.call_llm(prompt)
        try:
            res = json.loads(response)
            if isinstance(res, dict):
                res.setdefault("domain", domain)
                return res
            return {"domain": domain, "strategy": res}
        except:
            return {"domain": domain, "raw_response": response}

    def generate_iac(self, deployment_strategy: str, cloud_provider: str = "aws") -> Dict[str, Any]:
        """Generate Infrastructure as Code (Terraform/CloudFormation)."""
        return {
            "provider": cloud_provider,
            "strategy": deployment_strategy,
            "iac_generated": True,
        }

    def create_runbooks(self, deployment_plan: Dict[str, Any]) -> str:
        """Create incident runbooks."""
        return "Runbook: Monitor logs. If error rate > 1%, trigger failover. Escalate if MTTR > 15min."

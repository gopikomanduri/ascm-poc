"""Domain-specific loggers for each agent."""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional


class AgentLogger:
    """Base agent logger with domain-specific logging."""

    def __init__(self, agent_name: str, run_id: str, log_dir: str = "logs/runs"):
        self.agent_name = agent_name
        self.run_id = run_id
        self.run_log_dir = os.path.join(log_dir, run_id)
        os.makedirs(self.run_log_dir, exist_ok=True)

        # Create agent-specific log file
        self.log_file = os.path.join(self.run_log_dir, f"{agent_name}.log")

        # Setup Python logger
        self.logger = logging.getLogger(agent_name)
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def log_event(self, event_type: str, **kwargs) -> None:
        """Log event as JSON."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "agent": self.agent_name,
            "event_type": event_type,
            **kwargs,
        }

        # Write to human-readable log
        self.logger.info(f"{event_type}: {json.dumps(kwargs)}")

        # Write to JSONL for aggregation
        jsonl_file = os.path.join(self.run_log_dir, f"{self.agent_name}.jsonl")
        with open(jsonl_file, "a") as f:
            f.write(json.dumps(event) + "\n")


class CheckerAgentLogger(AgentLogger):
    """Logger for Checker Agent."""
    def __init__(self, run_id: str, log_dir: str = "logs/runs"):
        super().__init__("checker_agent", run_id, log_dir)

    def log_discovery(self, what: str, confidence: float, questions: int) -> None:
        self.log_event("DISCOVERY", what=what, confidence=confidence, questions=questions)

    def log_user_approval(self, gate: str, action: str, approved_by: str) -> None:
        self.log_event("USER_APPROVAL", gate=gate, action=action, approved_by=approved_by)


class OrchestratorAgentLogger(AgentLogger):
    """Logger for Orchestrator Agent."""
    def __init__(self, run_id: str, log_dir: str = "logs/runs"):
        super().__init__("orchestrator_agent", run_id, log_dir)

    def log_milestone_start(self, milestone_id: str, budget: int) -> None:
        self.log_event("MILESTONE_START", milestone_id=milestone_id, budget=budget)

    def log_variance_detection(self, milestone_id: str, variance_pct: float, flag: str) -> None:
        self.log_event("VARIANCE_DETECTION", milestone_id=milestone_id, variance_pct=variance_pct, flag=flag)


class ComplianceAgentLogger(AgentLogger):
    """Logger for Compliance Agent."""
    def __init__(self, run_id: str, log_dir: str = "logs/runs"):
        super().__init__("compliance_agent", run_id, log_dir)

    def log_validation(self, framework: str, verdict: str, violations: int) -> None:
        self.log_event("COMPLIANCE_VALIDATION", framework=framework, verdict=verdict, violations=violations)

    def log_violation_found(self, rule: str, severity: str, remediation: str) -> None:
        self.log_event("VIOLATION_FOUND", rule=rule, severity=severity, remediation=remediation)


class QAAgentLogger(AgentLogger):
    """Logger for QA Agent."""
    def __init__(self, run_id: str, log_dir: str = "logs/runs"):
        super().__init__("qa_agent", run_id, log_dir)

    def log_test_execution(self, total: int, passed: int, failed: int, coverage: float) -> None:
        self.log_event("TEST_EXECUTION", total=total, passed=passed, failed=failed, coverage_pct=coverage)

    def log_sla_gate(self, gate_name: str, passed: bool, threshold: float, actual: float) -> None:
        self.log_event("SLA_GATE", gate_name=gate_name, passed=passed, threshold=threshold, actual=actual)


class SREAgentLogger(AgentLogger):
    """Logger for SRE Agent."""
    def __init__(self, run_id: str, log_dir: str = "logs/runs"):
        super().__init__("sre_agent", run_id, log_dir)

    def log_deployment_design(self, strategy: str, provider: str, regions: int) -> None:
        self.log_event("DEPLOYMENT_DESIGN", strategy=strategy, provider=provider, regions=regions)

    def log_iac_generation(self, framework: str, files_generated: int) -> None:
        self.log_event("IaC_GENERATION", framework=framework, files_generated=files_generated)


class APMAgentLogger(AgentLogger):
    """Logger for APM Agent."""
    def __init__(self, run_id: str, log_dir: str = "logs/runs"):
        super().__init__("apm_agent", run_id, log_dir)

    def log_slo_definition(self, slo_name: str, threshold: float, unit: str) -> None:
        self.log_event("SLO_DEFINITION", slo_name=slo_name, threshold=threshold, unit=unit)

    def log_alert_configuration(self, alert_count: int, severity_distribution: Dict[str, int]) -> None:
        self.log_event("ALERT_CONFIGURATION", alert_count=alert_count, severity_distribution=severity_distribution)


class OnCallAgentLogger(AgentLogger):
    """Logger for On-Call Agent."""
    def __init__(self, run_id: str, log_dir: str = "logs/runs"):
        super().__init__("oncall_agent", run_id, log_dir)

    def log_incident_alert(self, alert_id: str, severity: str, service: str) -> None:
        self.log_event("INCIDENT_ALERT", alert_id=alert_id, severity=severity, service=service)

    def log_root_cause_analysis(self, alert_id: str, root_causes: list, mttr_sec: float) -> None:
        self.log_event("ROOT_CAUSE_ANALYSIS", alert_id=alert_id, root_causes=root_causes, mttr_sec=mttr_sec)

    def log_incident_resolution(self, alert_id: str, fix_applied: bool, mttr_sec: float) -> None:
        self.log_event("INCIDENT_RESOLUTION", alert_id=alert_id, fix_applied=fix_applied, mttr_sec=mttr_sec)

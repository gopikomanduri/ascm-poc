"""Compliance Agent: Regulatory framework validation (PCI-DSS, GDPR, HIPAA, DPDP, AML/KYC)."""
from typing import Dict, Any, Optional, List
import json
from .base import BaseAgent


class ComplianceAgent(BaseAgent):
    """
    Compliance Agent: Regulatory framework validation for production-grade systems.

    Supports:
    - PCI-DSS v3.2.1 (payment card processing)
    - GDPR (EU data protection)
    - HIPAA (US healthcare)
    - DPDP (India data protection)
    - AML/KYC (Anti-money laundering)
    """

    SYSTEM_INSTRUCTION = """You are a FinTech Regulatory Compliance & Enterprise Security Architect.

Your role: Audit software architectures and code against regulatory frameworks.

Frameworks you validate:
1. PCI-DSS v3.2.1 (12 controls for payment card data security)
2. GDPR Article 32 (Technical & Organizational Measures)
3. HIPAA/HHS Technical Safeguards (45 CFR 164.312)
4. DPDP Act 2023 (India data protection)
5. AML/KYC (Know Your Customer, transaction monitoring)

For each framework, assess:
- PASS: System meets all requirements
- FAIL: Critical violations identified
- CONDITIONAL: Meets requirements with minor remediations

Output JSON:
{
    "frameworks": {
        "pci_dss": {"status": "PASS/FAIL/CONDITIONAL", "controls": [...], "violations": [...]},
        "gdpr": {"status": "...", "articles": [...], "violations": [...]},
        "hipaa": {"status": "...", "safeguards": [...], "violations": [...]},
        ...
    },
    "overall_verdict": "PASS/FAIL/CONDITIONAL",
    "compliance_score": <0-100>,
    "violations": [
        {"rule": "...", "severity": "CRITICAL/HIGH/MEDIUM/LOW", "remediation": "..."}
    ],
    "recommendations": [...]
}
"""

    def __init__(
        self,
        system_instruction: Optional[str] = None,
        provider: Optional[Any] = None,
        tier: str = "primary",
        model: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            system_instruction=system_instruction or self.SYSTEM_INSTRUCTION,
            provider=provider,
            tier=tier,
            model=model,
        )
        self.system_instruction = system_instruction or self.SYSTEM_INSTRUCTION
        self.framework_checks = [
            "pci_dss",
            "gdpr",
            "hipaa",
            "dpdp",
            "aml_kyc",
        ]

    def run(self, files: Optional[Dict[str, str]] = None, domain: str = "general", **kwargs) -> Dict[str, Any]:
        """Unified entrypoint for compliance validation."""
        code_files = files or kwargs.get("code_files", {})
        test_files = kwargs.get("test_files", {})
        if code_files or test_files:
            return self.validate_code(domain=domain, code_files=code_files, test_files=test_files)
        hld = kwargs.get("hld", "")
        lld = kwargs.get("lld", "")
        data_flows = kwargs.get("data_flows", [])
        return self.validate_architecture(domain=domain, hld=hld, lld=lld, data_flows=data_flows)

    def validate_architecture(
        self,
        domain: str,
        hld: str,
        lld: str,
        data_flows: List[str],
    ) -> Dict[str, Any]:
        """Validate architecture against applicable compliance frameworks."""
        prompt = f"""
        Domain: {domain}

        High-Level Design:
        {hld}

        Low-Level Design:
        {lld}

        Data Flows:
        {chr(10).join(data_flows)}

        Task:
        1. Identify applicable compliance frameworks for this domain
        2. Validate architecture against each framework
        3. List any violations with remediation steps
        4. Provide overall compliance score (0-100)

        Output as JSON (only the JSON object, no markdown).
        """

        response = self.call_llm(prompt)

        try:
            result = json.loads(response)
        except:
            result = {
                "domain": domain,
                "raw_response": response,
                "compliance_score": 0,
                "overall_verdict": "UNKNOWN",
            }

        return result

    def validate_code(
        self,
        domain: str,
        code_files: Dict[str, str],
        test_files: Dict[str, str],
    ) -> Dict[str, Any]:
        """Validate code against compliance requirements."""
        prompt = f"""
        Domain: {domain}

        Code Files:
        {json.dumps(code_files, indent=2)[:2000]}  # Truncate for token efficiency

        Test Files:
        {json.dumps(test_files, indent=2)[:1000]}

        Task:
        1. Scan for PII/PHI (patient data, credit cards, SSNs)
        2. Check encryption (TLS 1.2+, AES-256)
        3. Validate audit logging
        4. Check for hardcoded secrets
        5. Verify access controls

        Output as JSON with findings.
        """

        response = self.call_llm(prompt)

        try:
            result = json.loads(response)
            if isinstance(result, dict):
                findings = result.get("findings", result.get("violations", []))
                result.setdefault("findings", findings)
                result.setdefault("violations", findings)
                return result
        except:
            result = {
                "domain": domain,
                "raw_response": response,
                "findings": [],
                "violations": [],
            }

        return result

    def validate_data_retention(
        self,
        domain: str,
        data_classification: Dict[str, str],
        retention_policy: str,
    ) -> Dict[str, Any]:
        """Validate data retention policies."""
        prompt = f"""
        Domain: {domain}

        Data Classification:
        {json.dumps(data_classification, indent=2)}

        Retention Policy:
        {retention_policy}

        Task:
        1. Validate retention periods against GDPR (60 days), HIPAA (6 years), etc.
        2. Check deletion/anonymization procedures
        3. Verify audit trail for data access

        Output as JSON.
        """

        response = self.call_llm(prompt)

        try:
            result = json.loads(response)
        except:
            result = {
                "domain": domain,
                "raw_response": response,
            }

        return result

    def generate_compliance_report(
        self,
        domain: str,
        validation_results: List[Dict[str, Any]],
    ) -> str:
        """Generate compliance audit report."""
        prompt = f"""
        Domain: {domain}

        Validation Results:
        {json.dumps(validation_results, indent=2)[:3000]}

        Task:
        Generate a concise compliance audit report:
        1. Executive summary
        2. Compliance score
        3. Key findings
        4. Remediation roadmap
        5. Next steps

        Output as plain text (markdown format acceptable).
        """

        response = self.call_llm(prompt)
        return response

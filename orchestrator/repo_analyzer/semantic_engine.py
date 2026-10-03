"""Semantic analysis engine: Create multi-angle summaries from code."""
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from orchestrator.agents.base import BaseAgent


class SemanticAnalysisEngine:
    """Create semantic summaries from different business and technical angles."""

    def __init__(self, repo_analysis: Dict[str, Any], output_dir: str = "logs/repo_summaries"):
        self.repo_analysis = repo_analysis
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Initialize analyzer agents
        self.business_analyzer = BusinessAngleAnalyzer()
        self.architecture_analyzer = ArchitectureAngleAnalyzer()
        self.technical_analyzer = TechnicalAngleAnalyzer()
        self.deployment_analyzer = DeploymentAngleAnalyzer()
        self.dataflow_analyzer = DataflowAngleAnalyzer()

    def analyze_all_angles(self, repo_name: str) -> Dict[str, str]:
        """Analyze repository from all angles and save as files."""
        print(f"\n🔬 Creating semantic summaries for {repo_name}...")

        summaries = {}

        # 1. Business Angle
        print("  [1/5] Business perspective...")
        business = self.business_analyzer.analyze(self.repo_analysis)
        business_file = self._save_summary("business_angle", repo_name, business)
        summaries["business"] = business_file

        # 2. Architecture Angle
        print("  [2/5] Architecture perspective...")
        architecture = self.architecture_analyzer.analyze(self.repo_analysis)
        arch_file = self._save_summary("architecture_angle", repo_name, architecture)
        summaries["architecture"] = arch_file

        # 3. Technical Low-Level Angle
        print("  [3/5] Technical low-level perspective...")
        technical = self.technical_analyzer.analyze(self.repo_analysis)
        tech_file = self._save_summary("technical_angle", repo_name, technical)
        summaries["technical"] = tech_file

        # 4. Deployment Angle
        print("  [4/5] Deployment perspective...")
        deployment = self.deployment_analyzer.analyze(self.repo_analysis)
        deploy_file = self._save_summary("deployment_angle", repo_name, deployment)
        summaries["deployment"] = deploy_file

        # 5. Data Flow Angle
        print("  [5/5] Data flow perspective...")
        dataflow = self.dataflow_analyzer.analyze(self.repo_analysis)
        dataflow_file = self._save_summary("dataflow_angle", repo_name, dataflow)
        summaries["dataflow"] = dataflow_file

        print(f"✅ Semantic analysis complete: {repo_name}\n")
        return summaries

    def _save_summary(self, angle: str, repo_name: str, content: str) -> str:
        """Save summary to file."""
        filename = f"{repo_name}_{angle}.md"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w') as f:
            f.write(f"# {angle.replace('_', ' ').title()}: {repo_name}\n\n")
            f.write(f"*Generated: {datetime.now().isoformat()}*\n\n")
            f.write(content)

        return filepath


class BusinessAngleAnalyzer:
    """Analyze repository from business perspective."""

    def analyze(self, repo_analysis: Dict[str, Any]) -> str:
        """Generate business angle summary."""
        summary = f"""
## Purpose
{self._analyze_purpose(repo_analysis)}

## Value Proposition
{self._analyze_value(repo_analysis)}

## Target Users
{self._analyze_users(repo_analysis)}

## Business Models
{self._analyze_business_model(repo_analysis)}

## Competitive Landscape
{self._analyze_competitors(repo_analysis)}

## Go-to-Market Considerations
{self._analyze_gtm(repo_analysis)}

## Revenue Opportunities
{self._analyze_revenue(repo_analysis)}
"""
        return summary

    def _analyze_purpose(self, repo_analysis: Dict[str, Any]) -> str:
        purposes = repo_analysis.get('purposes', ['General Purpose'])
        return f"- {chr(10).join(f'• {p}' for p in purposes)}"

    def _analyze_value(self, repo_analysis: Dict[str, Any]) -> str:
        purposes = repo_analysis.get('purposes', [])
        return "Provides core functionality for: " + ", ".join(purposes) if purposes else "Multi-purpose solution"

    def _analyze_users(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Internal teams\n- External customers\n- Third-party integrators"

    def _analyze_business_model(self, repo_analysis: Dict[str, Any]) -> str:
        return "- SaaS model\n- Open-source with premium support\n- Enterprise licensing"

    def _analyze_competitors(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Market leaders in category\n- Emerging competitors\n- Alternative solutions"

    def _analyze_gtm(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Developer adoption\n- Enterprise sales\n- Partner ecosystem"

    def _analyze_revenue(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Usage-based pricing\n- Per-seat licensing\n- Professional services"


class ArchitectureAngleAnalyzer:
    """Analyze repository from architecture perspective."""

    def analyze(self, repo_analysis: Dict[str, Any]) -> str:
        """Generate architecture angle summary."""
        summary = f"""
## System Architecture Type
{self._analyze_arch_type(repo_analysis)}

## Layering & Modules
{self._analyze_layers(repo_analysis)}

## Data Architecture
{self._analyze_data_arch(repo_analysis)}

## Communication Patterns
{self._analyze_communication(repo_analysis)}

## Integration Points
{self._analyze_integrations(repo_analysis)}

## Scalability Considerations
{self._analyze_scalability(repo_analysis)}

## Deployment Architecture
{self._analyze_deployment_arch(repo_analysis)}
"""
        return summary

    def _analyze_arch_type(self, repo_analysis: Dict[str, Any]) -> str:
        arch = repo_analysis.get('architecture', {})
        return f"- Type: {arch.get('type', 'unknown')}\n- Pattern: {arch.get('pattern', 'unknown')}"

    def _analyze_layers(self, repo_analysis: Dict[str, Any]) -> str:
        arch = repo_analysis.get('architecture', {})
        layers = arch.get('layers', ['API', 'Business Logic', 'Data'])
        return f"- {chr(10).join(f'• {l}' for l in layers)}"

    def _analyze_data_arch(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Relational / NoSQL databases\n- Caching layer\n- Event streaming"

    def _analyze_communication(self, repo_analysis: Dict[str, Any]) -> str:
        return "- REST APIs\n- Message queues\n- Webhooks"

    def _analyze_integrations(self, repo_analysis: Dict[str, Any]) -> str:
        return "- External APIs\n- Third-party services\n- Legacy systems"

    def _analyze_scalability(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Horizontal scaling\n- Database optimization\n- Caching strategies"

    def _analyze_deployment_arch(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Containerized (Docker)\n- Orchestrated (Kubernetes)\n- Cloud-native"


class TechnicalAngleAnalyzer:
    """Analyze repository from technical low-level perspective."""

    def analyze(self, repo_analysis: Dict[str, Any]) -> str:
        """Generate technical angle summary."""
        summary = f"""
## Programming Languages
{self._analyze_languages(repo_analysis)}

## Frameworks & Libraries
{self._analyze_frameworks(repo_analysis)}

## Dependencies
{self._analyze_dependencies(repo_analysis)}

## Code Organization
{self._analyze_code_org(repo_analysis)}

## Quality & Testing
{self._analyze_quality(repo_analysis)}

## Performance Characteristics
{self._analyze_performance(repo_analysis)}

## Security Considerations
{self._analyze_security(repo_analysis)}
"""
        return summary

    def _analyze_languages(self, repo_analysis: Dict[str, Any]) -> str:
        languages = repo_analysis.get('languages', {})
        return f"- {chr(10).join(f'• {lang}: {count} files' for lang, count in list(languages.items())[:5])}"

    def _analyze_frameworks(self, repo_analysis: Dict[str, Any]) -> str:
        tech = repo_analysis.get('technologies', {})
        all_tech = tech.get('frontend', []) + tech.get('backend', [])
        return f"- {chr(10).join(f'• {t}' for t in all_tech)}" if all_tech else "- Standard libraries"

    def _analyze_dependencies(self, repo_analysis: Dict[str, Any]) -> str:
        deps = repo_analysis.get('dependencies', {})
        summary = ""
        for pkg_mgr, dep_list in deps.items():
            if dep_list:
                summary += f"\n**{pkg_mgr.upper()}:**\n- {chr(10).join(f'• {d}' for d in dep_list[:5])}"
        return summary or "- Minimal dependencies"

    def _analyze_code_org(self, repo_analysis: Dict[str, Any]) -> str:
        structure = repo_analysis.get('structure', {})
        return f"- Files: {structure.get('file_count', 0)}\n- Lines: {structure.get('total_lines', 0):,}\n- Directories: {len(structure.get('directories', []))}"

    def _analyze_quality(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Unit test coverage\n- Integration tests\n- Code review process"

    def _analyze_performance(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Async/concurrent patterns\n- Caching strategies\n- Database indexing"

    def _analyze_security(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Input validation\n- Authentication/Authorization\n- Encryption at rest & in transit"


class DeploymentAngleAnalyzer:
    """Analyze repository from deployment perspective."""

    def analyze(self, repo_analysis: Dict[str, Any]) -> str:
        """Generate deployment angle summary."""
        summary = f"""
## Deployment Targets
{self._analyze_targets(repo_analysis)}

## Infrastructure as Code
{self._analyze_iac(repo_analysis)}

## Container Strategy
{self._analyze_containers(repo_analysis)}

## CI/CD Pipeline
{self._analyze_cicd(repo_analysis)}

## Environment Management
{self._analyze_environments(repo_analysis)}

## Monitoring & Observability
{self._analyze_monitoring(repo_analysis)}

## Disaster Recovery
{self._analyze_dr(repo_analysis)}
"""
        return summary

    def _analyze_targets(self, repo_analysis: Dict[str, Any]) -> str:
        tech = repo_analysis.get('technologies', {})
        infra = tech.get('infrastructure', ['Cloud', 'On-Premises'])
        return f"- {chr(10).join(f'• {t}' for t in infra)}"

    def _analyze_iac(self, repo_analysis: Dict[str, Any]) -> str:
        key_files = repo_analysis.get('key_files', {})
        iac_tools = ['Dockerfile', 'docker-compose.yml', 'Makefile']
        found = [f for f in iac_tools if f in key_files]
        return f"- {chr(10).join(f'• {f}' for f in found)}" if found else "- Manual deployment"

    def _analyze_containers(self, repo_analysis: Dict[str, Any]) -> str:
        key_files = repo_analysis.get('key_files', {})
        if 'Dockerfile' in key_files:
            return "- Containerized with Docker\n- Multi-stage builds\n- Minimal images"
        return "- Non-containerized\n- Or containers defined elsewhere"

    def _analyze_cicd(self, repo_analysis: Dict[str, Any]) -> str:
        key_files = repo_analysis.get('key_files', {})
        if '.github/workflows' in str(key_files):
            return "- GitHub Actions CI/CD\n- Automated testing\n- Auto-deployment"
        return "- Manual CI/CD\n- Or CI system not in repo"

    def _analyze_environments(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Development\n- Staging\n- Production"

    def _analyze_monitoring(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Application metrics\n- Infrastructure monitoring\n- Log aggregation"

    def _analyze_dr(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Backup strategy\n- Failover procedures\n- Recovery time objectives"


class DataflowAngleAnalyzer:
    """Analyze repository from data flow perspective."""

    def analyze(self, repo_analysis: Dict[str, Any]) -> str:
        """Generate data flow angle summary."""
        summary = f"""
## Data Sources
{self._analyze_sources(repo_analysis)}

## Data Processing
{self._analyze_processing(repo_analysis)}

## Data Storage
{self._analyze_storage(repo_analysis)}

## Data Sinks
{self._analyze_sinks(repo_analysis)}

## Data Transformations
{self._analyze_transformations(repo_analysis)}

## Real-time vs Batch
{self._analyze_timing(repo_analysis)}

## Data Quality & Governance
{self._analyze_governance(repo_analysis)}
"""
        return summary

    def _analyze_sources(self, repo_analysis: Dict[str, Any]) -> str:
        return "- User input / API requests\n- External webhooks\n- Message queues\n- Databases"

    def _analyze_processing(self, repo_analysis: Dict[str, Any]) -> str:
        purposes = repo_analysis.get('purposes', [])
        if any('Processing' in p for p in purposes):
            return "- Stream processing\n- Batch processing\n- Event-driven"
        return "- Request-response processing\n- Async job queues"

    def _analyze_storage(self, repo_analysis: Dict[str, Any]) -> str:
        tech = repo_analysis.get('technologies', {})
        db = tech.get('database', [])
        return f"- {chr(10).join(f'• {d}' for d in db)}" if db else "- In-memory / local storage"

    def _analyze_sinks(self, repo_analysis: Dict[str, Any]) -> str:
        return "- API responses\n- Database writes\n- Third-party webhooks\n- Analytics"

    def _analyze_transformations(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Data validation\n- Business logic\n- Aggregations\n- Enrichment"

    def _analyze_timing(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Real-time: < 100ms\n- Near real-time: 100ms-1s\n- Batch: hourly/daily"

    def _analyze_governance(self, repo_analysis: Dict[str, Any]) -> str:
        return "- Data retention policies\n- PII handling\n- Audit trails\n- Compliance requirements"

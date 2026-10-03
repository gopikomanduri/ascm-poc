"""Excel export for milestone tracking and reporting."""
import os
from datetime import datetime
from typing import List, Optional
from .models import Milestone, MilestoneMetrics

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class MilestoneExcelExporter:
    """Export milestone data to Excel with formatting."""

    def __init__(self, output_dir: str = "logs/exports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required for Excel export. Install with: pip install openpyxl")

    def export(
        self,
        milestones: List[Milestone],
        metrics: MilestoneMetrics,
        filename: Optional[str] = None,
    ) -> str:
        """Export milestones to Excel file."""
        if filename is None:
            filename = f"milestones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        filepath = os.path.join(self.output_dir, filename)
        wb = Workbook()

        # Remove default sheet
        if "Sheet" in wb.sheetnames:
            wb.remove(wb["Sheet"])

        # Create sheets
        self._create_milestones_sheet(wb, milestones)
        self._create_budget_analysis_sheet(wb, milestones, metrics)
        self._create_approvals_sheet(wb, milestones)
        self._create_summary_sheet(wb, metrics)

        wb.save(filepath)
        return filepath

    def _create_milestones_sheet(self, wb: Workbook, milestones: List[Milestone]) -> None:
        """Create milestones overview sheet."""
        ws = wb.create_sheet("Milestones")

        # Headers
        headers = [
            "ID",
            "Feature Name",
            "Status",
            "Completeness %",
            "Confidence %",
            "Budget Tokens",
            "Spent Tokens",
            "Utilization %",
            "Tests %",
            "Code Review",
            "Compliance",
            "Start Time",
            "Duration (sec)",
            "Notes",
        ]

        ws.append(headers)

        # Format header row
        header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Add data rows
        for milestone in milestones:
            variance = ((milestone.spent_tokens - milestone.budget_p90_tokens) / milestone.budget_p90_tokens * 100) if milestone.budget_p90_tokens > 0 else 0

            ws.append([
                milestone.id,
                milestone.name,
                milestone.status.value,
                f"{milestone.functional_completeness:.0f}",
                f"{milestone.requirements_confidence:.0f}",
                milestone.budget_p90_tokens,
                milestone.spent_tokens,
                f"{variance:.1f}%",
                f"{milestone.quality_gates.tests_passed_pct:.0f}",
                "✓" if milestone.quality_gates.code_review_approved else "✗",
                "✓" if milestone.quality_gates.compliance_passed else "✗",
                milestone.start_time.strftime("%Y-%m-%d %H:%M"),
                f"{milestone.duration_seconds:.0f}",
                milestone.orchestrator_notes,
            ])

        # Format data rows with conditional colors
        for idx, milestone in enumerate(milestones, start=2):
            status_cell = ws[f"C{idx}"]

            if milestone.status.value == "on_track":
                status_cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
            elif milestone.status.value == "at_risk":
                status_cell.fill = PatternFill(start_color="FEF08A", end_color="FEF08A", fill_type="solid")
            else:  # blocked
                status_cell.fill = PatternFill(start_color="FECACA", end_color="FECACA", fill_type="solid")

        # Adjust column widths
        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 25
        ws.column_dimensions["C"].width = 12
        ws.column_dimensions["D"].width = 12
        ws.column_dimensions["E"].width = 12
        ws.column_dimensions["F"].width = 14
        ws.column_dimensions["G"].width = 14
        ws.column_dimensions["H"].width = 12
        ws.column_dimensions["I"].width = 10
        ws.column_dimensions["J"].width = 12
        ws.column_dimensions["K"].width = 12
        ws.column_dimensions["L"].width = 18
        ws.column_dimensions["M"].width = 14
        ws.column_dimensions["N"].width = 20

    def _create_budget_analysis_sheet(self, wb: Workbook, milestones: List[Milestone], metrics: MilestoneMetrics) -> None:
        """Create token budget analysis sheet."""
        ws = wb.create_sheet("Budget Analysis")

        # Summary section
        ws.append(["TOKEN BUDGET SUMMARY"])
        ws.append([])

        ws.append(["Total Budget (P90)", metrics.total_budget])
        ws.append(["Total Spent", metrics.total_spent])
        ws.append(["Remaining", metrics.total_budget - metrics.total_spent])
        ws.append(["Variance %", f"{metrics.total_variance_pct:.1f}%"])
        ws.append([])

        # Per-agent breakdown
        ws.append(["TOKENS BY AGENT"])
        ws.append([])

        agent_headers = ["Agent", "Total Tokens", "Tasks Run"]
        ws.append(agent_headers)

        # Count tasks per agent
        agent_tasks = {}
        for milestone in milestones:
            for task in milestone.tasks:
                agent = task.assigned_agent
                if agent not in agent_tasks:
                    agent_tasks[agent] = 0
                agent_tasks[agent] += 1

        for agent, tokens in sorted(metrics.tokens_by_agent.items(), key=lambda x: x[1], reverse=True):
            ws.append([
                agent,
                tokens,
                agent_tasks.get(agent, 0),
            ])

        # Milestone detail
        ws.append([])
        ws.append(["MILESTONE-BY-MILESTONE DETAIL"])
        ws.append([])

        detail_headers = ["Milestone", "Budget", "Spent", "Variance %", "Tasks", "Status"]
        ws.append(detail_headers)

        for milestone in milestones:
            variance = ((milestone.spent_tokens - milestone.budget_p90_tokens) / milestone.budget_p90_tokens * 100) if milestone.budget_p90_tokens > 0 else 0
            ws.append([
                milestone.name,
                milestone.budget_p90_tokens,
                milestone.spent_tokens,
                f"{variance:.1f}%",
                len(milestone.tasks),
                milestone.status.value,
            ])

        # Format
        title_font = Font(bold=True, size=12)
        ws["A1"].font = title_font
        ws["A8"].font = title_font
        ws["A20"].font = title_font

        # Adjust column widths
        for col in range(1, 7):
            ws.column_dimensions[get_column_letter(col)].width = 15

    def _create_approvals_sheet(self, wb: Workbook, milestones: List[Milestone]) -> None:
        """Create user approvals audit trail sheet."""
        ws = wb.create_sheet("Approvals")

        headers = ["Timestamp", "Milestone", "Gate", "Action", "Approved By", "Feedback", "Token Override"]
        ws.append(headers)

        # Format header
        header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        # Add approval records
        row = 2
        for milestone in milestones:
            for approval in milestone.user_approvals:
                ws.append([
                    approval.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    milestone.name,
                    approval.gate.value,
                    approval.action,
                    approval.approved_by,
                    approval.feedback,
                    "Yes" if approval.token_override else "No",
                ])
                row += 1

        # Adjust column widths
        ws.column_dimensions["A"].width = 18
        ws.column_dimensions["B"].width = 25
        ws.column_dimensions["C"].width = 15
        ws.column_dimensions["D"].width = 12
        ws.column_dimensions["E"].width = 15
        ws.column_dimensions["F"].width = 30
        ws.column_dimensions["G"].width = 15

    def _create_summary_sheet(self, wb: Workbook, metrics: MilestoneMetrics) -> None:
        """Create executive summary sheet."""
        ws = wb.create_sheet("Summary", 0)  # First sheet

        # Title
        title = ws.cell(row=1, column=1)
        title.value = "ASCM MILESTONE TRACKING SUMMARY"
        title.font = Font(bold=True, size=14, color="FFFFFF")
        title.fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        ws.merge_cells("A1:D1")

        # Key metrics
        ws.append([])
        ws.append(["KEY METRICS"])
        ws["A3"].font = Font(bold=True, size=11)
        ws.append([])

        metrics_data = [
            ["Total Milestones", metrics.total_milestones],
            ["Completed", metrics.completed_milestones],
            ["On Track (GREEN)", metrics.on_track],
            ["At Risk (YELLOW)", metrics.at_risk],
            ["Blocked (RED)", metrics.blocked],
            [],
            ["Total Token Budget", metrics.total_budget],
            ["Total Tokens Spent", metrics.total_spent],
            ["Remaining Tokens", metrics.total_budget - metrics.total_spent],
            ["Variance %", f"{metrics.total_variance_pct:.1f}%"],
            [],
            ["Avg Requirements Confidence %", f"{metrics.avg_requirements_confidence:.1f}%"],
            ["Avg Test Coverage %", f"{metrics.avg_test_coverage:.1f}%"],
            ["Compliance Pass Rate %", f"{metrics.compliance_pass_rate:.1f}%"],
            [],
            ["Total Approvals", metrics.total_approvals],
            ["Total Reworks", metrics.total_reworks],
            ["Rework Rate %", f"{metrics.rework_rate_pct:.1f}%"],
            [],
            ["Avg Milestone Duration (sec)", f"{metrics.avg_duration_sec:.0f}"],
            ["Total Time (sec)", f"{metrics.total_duration_sec:.0f}"],
        ]

        for row_idx, row_data in enumerate(metrics_data, start=4):
            if len(row_data) > 0:
                ws[f"A{row_idx}"] = row_data[0]
                if len(row_data) > 1:
                    ws[f"B{row_idx}"] = row_data[1]

        ws.column_dimensions["A"].width = 35
        ws.column_dimensions["B"].width = 20

        # Generated timestamp
        ws.append([])
        ws.append(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

"""
Report Generator Component for Reviewer Agent.
Handles the formatting and consolidation of review reports.
"""
from typing import List, Dict, Any


class ReportGenerator:
    """Generates markdown reports for code reviews."""

    def __init__(self):
        pass

    def create_consolidated_report(
        self, analyzed_count: int, missing_tests_files: List[str] = None
    ) -> str:
        """Initializes the review report header."""
        report = "## 🛡️ Deep Code Review Report\n\n"
        report += f"**Analyzed Files**: `{analyzed_count} modified files`\n\n"

        if missing_tests_files:
            report += "⚠️ **Risk Warning**: Source code modified but no tests found in this PR.\n"
            report += f"ℹ️ **Test Coverage Note**: Verification missing for: `{'`, `'.join(missing_tests_files)}`\n\n"

        return report

    def format_file_review(
        self,
        file_name: str,
        syntax_status: bool,
        syntax_msg: str,
        scanner_findings: List[str],
        impact_msg: str,
        llm_review: str,
    ) -> str:
        """Formats the review section for a single file."""
        section = f"### 📄 File: `{file_name}`\n\n"

        # 1. Automated Checks
        section += "**Automated Checks**:\n"
        if not syntax_status:
            section += f"- {syntax_msg}\n"
        else:
            section += "- ✅ Syntax: Valid\n"

        if scanner_findings:
            for msg in scanner_findings:
                section += f"- {msg}\n"
        else:
            section += "- ✅ Static Analysis: Clean\n"

        # 2. Impact Analysis
        if impact_msg:
            section += f"\n**Impact Analysis**:\n{impact_msg}\n"

        # 3. AI Review
        section += f"\n**AI Review**:\n{llm_review}\n"
        section += "\n---\n"

        return section

    def close_report(self, has_critical_issues: bool) -> str:
        """Adds final summary footer."""
        footer = "\n### 🏁 Summary\n"
        if has_critical_issues:
            footer += "❌ **Status**: Changes Requested (Critical issues found)\n"
        else:
            footer += "✅ **Status**: Approved (With comments)\n"
        return footer

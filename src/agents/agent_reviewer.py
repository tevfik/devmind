"""
Reviewer Agent - Responsible for checking code quality and correctness
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


from agents.agent_base import (
    create_llm,
    print_section_header,
    print_info,
    print_warning,
    print_success,
    load_file,
    retrieve_relevant_context,
)
from config.config import get_config
from utils.prompts import REVIEWER_USER_TEMPLATE, REVIEWER_SYSTEM_PROMPT
from tools.code_analyzer.analyzer import CodeAnalyzer
import re
import os

from agents.reviewer_components.scanner_integrator import ScannerIntegrator
from agents.reviewer_components.report_generator import ReportGenerator
from agents.reviewer_components.context_builder import ContextBuilder

logger = logging.getLogger("agents")


class ReviewResult(BaseModel):
    is_valid: bool = Field(description="Whether the code is valid and safe to use")
    issues: list[str] = Field(description="List of issues found in the code")
    suggestions: list[str] = Field(description="Suggestions for improvement")
    corrected_code: Optional[str] = Field(
        description="Optional corrected version if trivial fixes needed"
    )


class ReviewerAgent:
    """Agent responsible for reviewing code"""

    def __init__(self, model_type: str = "code", repo_path: str = "."):
        # Use a slightly higher temperature for critical analysis
        self.llm = create_llm(model_type, temperature=0.1)
        self.logger = logger
        self.config = get_config()
        self.repo_path = Path(repo_path)

        # Components
        self.scanner = ScannerIntegrator()
        self.reporter = ReportGenerator()
        self.context_builder = ContextBuilder()

    def review_code(self, code: str, requirements: str, file_path: str = None) -> str:
        """
        Reviews the code against requirements and best practices.
        Supports both single file review and PR multi-file review.
        """
        print_section_header("Reviewer Agent: Analyzing Code", "🧐")

        # Check if this is a PR (diff) or a single file
        # Heuristic: if file_path is "PR #...", it's likely a bulk review
        is_pr_review = file_path and "PR #" in file_path

        if is_pr_review:
            # Multi-file iterative review
            return self._review_pr_iteratively(code, requirements)
        else:
            # Single file review (Original Logic)
            return self._review_single_file_or_snippet(code, requirements, file_path)

    def _review_single_file_or_snippet(
        self, code: str, requirements: str, file_path: str = None
    ) -> str:
        """Internal method for standard single-pass review."""

        # 1. Run Scanners via Component
        scanner_msgs = []
        if file_path:
            scanner_msgs = self.scanner.run_scanners(Path(file_path), code)

        # 2. Build Context via Component
        context = self.context_builder.build_context(file_path, code, scanner_msgs)

        prompt = ChatPromptTemplate.from_messages(
            [("system", REVIEWER_SYSTEM_PROMPT), ("user", REVIEWER_USER_TEMPLATE)]
        )

        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke(
            {"code": code, "requirements": requirements, "context": context}
        )

        if "APPROVED" in result:
            print_success("Code review passed!")
        else:
            print_warning("Issues found in code review.")

        return result

    def _review_pr_iteratively(self, diff_content: str, requirements: str) -> str:
        """
        Iteratively reviews each file in the diff and consolidates results.
        Uses a scratchpad approach to accumulate findings.
        """
        # 1. Parse Diff to separate files
        # We need a robust way to split the diff by file.
        # Standard "diff --git" or "+++" markers.
        files_data = self._parse_diff(diff_content)

        if not files_data:
            self.logger.warning(
                "Could not parse distinct files from diff. Falling back to single-pass."
            )
            return self._review_single_file_or_snippet(
                diff_content, requirements, "PR Diff"
            )

        consolidated_report = "## 🛡️ Deep Code Review Report\n\n"
        consolidated_report += (
            f"**Analyzed Files**: `{len(files_data)} modified files`\n\n"
        )

        # Test Coverage Heuristic
        src_files = [
            f for f in files_data.keys() if f.startswith("src/") and f.endswith(".py")
        ]
        test_files = [
            f for f in files_data.keys() if f.startswith("tests/") or "test" in f
        ]

        if src_files and not test_files:
            consolidated_report += "⚠️ **Risk Warning**: Source code modified but no tests found in this PR.\n\n"
        elif src_files:
            # Check 1:1 mapping heuristic (loose)
            untested = []
            for src in src_files:
                base = src.split("/")[-1].replace(".py", "")
                if not any(base in t for t in test_files):
                    untested.append(src)
            if untested:
                consolidated_report += f"ℹ️ **Test Coverage Note**: Verification missing for: `{'`, `'.join(untested)}`\n\n"

        scratchpad = []
        has_critical_issues = False

        print_info(f"Start iterative review for {len(files_data)} files...")

        # 2. Iterate and Review
        for fname, fcontent in files_data.items():
            self.logger.info(f"Reviewing specific file: {fname}")
            full_path = self.repo_path / fname

            # A. Syntax Check via Component
            syntax_res = self.scanner.check_syntax(full_path)
            if not syntax_res["valid"]:
                has_critical_issues = True

            # B. Scanners via Component
            scanner_msgs = []
            if full_path.exists():
                scanner_msgs = self.scanner.run_scanners(full_path, fcontent)

            # C. Graph Impact via Component
            impact_msg = self.context_builder.get_impact_analysis(fname)

            # D. LLM Review
            file_reqs = f"{requirements}\nFocus ONLY on the changes in {fname}."
            if not syntax_res["valid"]:
                file_reqs += (
                    f"\nCRITICAL: There are syntax errors: {syntax_res['error']}"
                )

            llm_review = self._review_single_file_or_snippet(fcontent, file_reqs, fname)

            # E. Format File Section via Reporter
            file_report = self.reporter.format_file_review(
                fname,
                syntax_res["valid"],
                f"❌ **Syntax Error**: {syntax_res['error']}"
                if not syntax_res["valid"]
                else "",
                scanner_msgs,
                impact_msg,
                llm_review,
            )

            consolidated_report += file_report

        return consolidated_report

    def _parse_diff(self, diff: str) -> Dict[str, str]:
        """
        Splits a unified diff into per-file chunks.
        Returns dict: {filepath: diff_snippet}
        """
        files = {}
        current_file = None
        current_content = []

        lines = diff.splitlines()
        for line in lines:
            if line.startswith("diff --git"):
                # Save previous
                if current_file:
                    files[current_file] = "\n".join(current_content)

                # Start new
                # diff --git a/path/to/file b/path/to/file
                match = re.search(r"b/(.*)", line)
                if match:
                    current_file = match.group(1)
                else:
                    # Fallback
                    parts = line.split(" ")
                    current_file = parts[-1].lstrip("b/")

                current_content = [line]
            else:
                if current_content is not None:
                    current_content.append(line)

        # Save last
        if current_file:
            files[current_file] = "\n".join(current_content)

        return files

    # Original _analyze_diff_impact can be removed or kept as utility,
    # but _review_pr_iteratively replaces its logic for the main flow.
    def _analyze_diff_impact(self, diff: str) -> str:
        # Legacy method (kept for backward compatibility if called directly)
        return ""

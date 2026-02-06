"""
Scanner Integrator for Reviewer Agent.
Orchestrates static analysis tools (Linter, Security, Complexity).
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from tools.code_analyzer.scanners import (
    ComplexityScanner,
    SecurityScanner,
    LinterScanner,
)
from tools.analysis.syntax import SyntaxChecker

logger = logging.getLogger("reviewer.scanner")


class ScannerIntegrator:
    """Orchestrates code scanning tools."""

    def __init__(self):
        self.comp_scanner = ComplexityScanner()
        self.sec_scanner = SecurityScanner()
        self.lint_scanner = LinterScanner()
        self.syntax_checker = SyntaxChecker()

        # Supported extensions for complexity scanning
        self.polyglot_exts = [
            ".py",
            ".cpp",
            ".cc",
            ".cxx",
            ".h",
            ".hpp",
            ".c",
            ".java",
            ".js",
            ".go",
        ]

    def check_syntax(self, file_path: Path) -> Dict[str, Any]:
        """Runs syntax check on the file."""
        if not file_path.exists():
            return {
                "valid": True,
                "error": None,
            }  # Skip if file doesn't exist (e.g. deleted)

        res = self.syntax_checker.check(str(file_path))
        return {
            "valid": res.valid,
            "error": res.error_message if not res.valid else None,
        }

    def run_scanners(self, file_path: Path, code_content: str) -> List[str]:
        """Runs all applicable scanners for the file."""
        findings = []
        fname = file_path.name
        fpath_str = str(file_path)

        # 1. Complexity (Polyglot)
        if any(fname.endswith(ext) for ext in self.polyglot_exts):
            try:
                # Some scanners need path, some need content. ComplexityScanner handles both via temp files if needed.
                c_res = self.comp_scanner.scan(code_content, fpath_str)
                for r in c_res:
                    findings.append(f"⚠️ {r.message}")
            except Exception as e:
                logger.warning(f"Complexity scan failed for {fname}: {e}")

        # 2. Python Specifics (Security & Linting)
        if fname.endswith(".py") and file_path.exists():
            try:
                # Security
                s_res = self.sec_scanner.scan(fpath_str)
                for r in s_res:
                    findings.append(f"🔒 {r.message}")

                # Linting
                l_res = self.lint_scanner.scan(fpath_str)
                for r in l_res:
                    findings.append(f"🧹 {r.message}")
            except Exception as e:
                logger.warning(f"Python specific scan failed for {fname}: {e}")

        return findings

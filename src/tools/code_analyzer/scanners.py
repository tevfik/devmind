import ast
import subprocess
import shutil
import logging
import os
import tempfile
from typing import List, Dict, Any, Optional

logger = logging.getLogger("scanners")


class ScanResult:
    def __init__(self, valid: bool, message: str, severity: str = "INFO"):
        self.valid = valid
        self.message = message
        self.severity = severity  # INFO, WARNING, ERROR


class ComplexityScanner:
    """
    Calculates Cyclomatic Complexity.
    Supports:
    - Python (via AST)
    - C/C++, Java, JS, Go (via Lizard)
    """

    def scan(self, code: str, file_path: str = None) -> List[ScanResult]:
        results = []

        # 1. Python AST Method (Fast & Native)
        if not file_path or file_path.endswith(".py"):
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        complexity = self._calculate_complexity(node)
                        if complexity > 10:
                            results.append(
                                ScanResult(
                                    False,
                                    f"Function `{node.name}` is too complex (Cyclomatic Complexity: {complexity}). Consider refactoring.",
                                    "WARNING",
                                )
                            )
            except Exception:
                # Fallback to lizard if AST fails or for other languages
                pass

        # 2. Lizard Method (Polyglot)
        # Only run if we haven't found results yet or it's not Python
        # (Lizard works on Python too, but we might prefer AST for specific checking)

        if shutil.which("lizard") and (
            not results or (file_path and not file_path.endswith(".py"))
        ):
            try:
                temp_file_path = None
                target_path = None

                if file_path and os.path.exists(file_path):
                    target_path = file_path
                elif code:
                    # Create temp file if we have code but no valid file_path
                    ext = ".cpp"  # Default
                    if file_path:
                        _, ext = os.path.splitext(file_path)

                    fd, temp_file_path = tempfile.mkstemp(suffix=ext, text=True)
                    with os.fdopen(fd, "w") as tmp:
                        tmp.write(code)
                    target_path = temp_file_path

                if target_path:
                    cmd = ["lizard", "--csv", target_path]
                    proc = subprocess.run(cmd, capture_output=True, text=True)

                    if proc.stdout:
                        # CSV format: NLOC, CCN, token, param, length, location, file, function, long_name, start, end
                        lines = proc.stdout.strip().splitlines()
                        for line in lines:
                            # Skip errors/warnings that lizard prints to stdout sometimes
                            if not "," in line:
                                continue

                            parts = line.split(",")
                            if len(parts) >= 4:
                                try:
                                    ccn = int(parts[1])
                                    # func_name in CSV might be quoted
                                    func_name = parts[7].strip('"')
                                    if ccn > 10:
                                        results.append(
                                            ScanResult(
                                                False,
                                                f"Function `{func_name}` has high complexity (CCN: {ccn}) [Lizard].",
                                                "WARNING",
                                            )
                                        )
                                except Exception as e:
                                    logger.error(f"Lizard parsing error: {e}")

                    # Cleanup
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)

            except Exception as e:
                logger.error(f"Lizard execution error: {e}")
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass

        return results

        return results

    def _calculate_complexity(self, node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.AsyncFor,
                    ast.ExceptHandler,
                    ast.With,
                    ast.AsyncWith,
                    ast.Assert,
                ),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity


class SecurityScanner:
    """Wrapper for Bandit (if available) or basic AST checks."""

    def scan(self, file_path: str) -> List[ScanResult]:
        results = []

        # Method A: Try running bandit
        if shutil.which("bandit"):
            try:
                # Run bandit on just this file, quiet mode, JSON output would be ideal but let's just grep text
                cmd = [
                    "bandit",
                    "-r",
                    file_path,
                    "-ll",
                    "-ii",
                    "--format",
                    "custom",
                    "--msg-template",
                    "{msg}",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0 and result.stdout:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            results.append(
                                ScanResult(
                                    False, f"Security Risk (Bandit): {line}", "ERROR"
                                )
                            )
                    return results  # If bandit ran, trust it
            except Exception as e:
                logger.warning(f"Bandit execution failed: {e}")

        # Method B: Fallback AST checks (very basic)
        try:
            with open(file_path, "r") as f:
                code = f.read()
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # Check for 'exec' or 'eval'
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ["eval", "exec"]:
                            results.append(
                                ScanResult(
                                    False,
                                    f"Avoid using `{node.func.id}` - it is a security risk.",
                                    "ERROR",
                                )
                            )
        except:
            pass

        return results


class LinterScanner:
    """Integration for flake8 or similar."""

    def scan(self, file_path: str) -> List[ScanResult]:
        results = []
        if shutil.which("flake8"):
            try:
                # Run flake8 with specific select rules (avoid noise)
                # E9: Runtime, F63: Undefined names, F7: Build errors
                cmd = ["flake8", "--select=E9,F63,F7,F82", "--isolate", file_path]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode != 0 and proc.stdout:
                    for line in proc.stdout.splitlines():
                        results.append(
                            ScanResult(False, f"Lint Error: {line.strip()}", "WARNING")
                        )
            except:
                pass
        return results

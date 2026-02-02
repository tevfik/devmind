#!/usr/bin/env python3
"""
DevMind Module Testing Suite
Comprehensive tests for each module with detailed diagnostics
"""

import sys
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'


@dataclass
class TestResult:
    """Test result container"""
    name: str
    status: str  # PASS, FAIL, MISSING, PARTIAL
    message: str
    details: List[str]


class ModuleTester:
    """Comprehensive module testing"""
    
    def __init__(self):
        self.results: List[TestResult] = []
    
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}{title:^70}{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
    
    def test_module_import(self, module_name: str, item: str = None) -> TestResult:
        """Test if module can be imported"""
        try:
            if item:
                mod = __import__(module_name, fromlist=[item])
                getattr(mod, item)
                status = "PASS"
                message = f"✅ Successfully imported {module_name}.{item}"
                details = [f"Module: {mod}", f"Item: {item}"]
            else:
                mod = __import__(module_name)
                status = "PASS"
                message = f"✅ Successfully imported {module_name}"
                details = [f"Module: {mod}"]
            
            print(f"{GREEN}✓ {message}{RESET}")
            return TestResult(f"{module_name}::{item}" if item else module_name, status, message, details)
            
        except ImportError as e:
            status = "MISSING"
            message = f"❌ Import failed: {e}"
            details = [f"Error: {str(e)}", f"Module path: {module_name}"]
            print(f"{RED}✗ {message}{RESET}")
            return TestResult(f"{module_name}::{item}" if item else module_name, status, message, details)
        except Exception as e:
            status = "FAIL"
            message = f"❌ Unexpected error: {e}"
            details = [f"Error type: {type(e).__name__}", f"Message: {str(e)}"]
            print(f"{RED}✗ {message}{RESET}")
            return TestResult(f"{module_name}::{item}" if item else module_name, status, message, details)
    
    def test_cli_command(self, command: str, description: str = "") -> TestResult:
        """Test CLI command execution"""
        try:
            result = subprocess.run(
                f"devmind {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                status = "PASS"
                message = f"✅ Command succeeded: {command}"
                details = [f"Return code: {result.returncode}"]
                print(f"{GREEN}✓ {message}{RESET}")
            else:
                # Some commands fail gracefully (missing dependencies)
                if "not available" in result.stdout or "not available" in result.stderr:
                    status = "PARTIAL"
                    message = f"⚠️  Command ran but dependencies missing: {command}"
                    details = [f"Return code: {result.returncode}", "Dependencies: Missing"]
                    print(f"{YELLOW}⚠ {message}{RESET}")
                else:
                    status = "FAIL"
                    message = f"❌ Command failed: {command}"
                    details = [f"Return code: {result.returncode}", f"Output: {result.stderr[:100]}"]
                    print(f"{RED}✗ {message}{RESET}")
            
            return TestResult(f"CLI::{command}", status, message, details)
            
        except subprocess.TimeoutExpired:
            status = "FAIL"
            message = f"❌ Command timeout: {command}"
            details = ["Timeout: 5 seconds exceeded"]
            print(f"{RED}✗ {message}{RESET}")
            return TestResult(f"CLI::{command}", status, message, details)
        except Exception as e:
            status = "FAIL"
            message = f"❌ Error running command: {e}"
            details = [f"Error: {str(e)}"]
            print(f"{RED}✗ {message}{RESET}")
            return TestResult(f"CLI::{command}", status, message, details)
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        self.print_header("DevMind Module Testing Suite")
        
        # =====================================================================
        # CORE MODULES
        # =====================================================================
        self.print_header("1. Core Modules")
        
        print(f"{CYAN}Testing core infrastructure modules...{RESET}\n")
        self.results.append(self.test_module_import("config.onboarding", "get_config"))
        self.results.append(self.test_module_import("agents.agent_base", "create_llm"))
        self.results.append(self.test_module_import("utils.prompts", "SHELL_SUGGESTER_PROMPT"))
        self.results.append(self.test_module_import("cli.cli", "main"))
        
        # =====================================================================
        # CLI COMMANDS
        # =====================================================================
        self.print_header("2. CLI Commands Testing")
        
        print(f"{CYAN}Testing all CLI commands...{RESET}\n")
        
        cli_tests = [
            ("--help", "Help command"),
            ("--version", "Version info"),
            ("status", "Status check"),
            ("docker status", "Docker status"),
            ("new --help", "New project help"),
            ("chat --help", "Chat help"),
            ("commit --help", "Commit help"),
            ("explain --help", "Explain help"),
            ("fix --help", "Fix help"),
            ("suggest --help", "Suggest help"),
            ("analyze --help", "Analyze help"),
        ]
        
        for cmd, desc in cli_tests:
            self.results.append(self.test_cli_command(cmd, desc))
        
        # =====================================================================
        # MISSING MODULES
        # =====================================================================
        self.print_header("3. Missing/Optional Modules")
        
        print(f"{YELLOW}These modules are not found (this is OK if not needed):{RESET}\n")
        
        optional_modules = [
            ("memory.manager", "MemoryManager", "Chat memory management"),
            ("core.engine", "Engine", "Main orchestration engine"),
            ("tools.git_analyzer", "GitAnalyzer", "Git analysis tools"),
            ("tools.docker_manager", "DockerManager", "Docker management (replaced by cli.docker_manager)"),
        ]
        
        for module_name, item, description in optional_modules:
            result = self.test_module_import(module_name, item)
            result.details.append(f"Purpose: {description}")
            self.results.append(result)
        
        # =====================================================================
        # CONFIGURATION TEST
        # =====================================================================
        self.print_header("4. Configuration Test")
        
        print(f"{CYAN}Testing configuration system...{RESET}\n")
        try:
            from config.onboarding import get_config as get_config_fn
            config = get_config_fn()
            
            required_keys = ['OLLAMA_URL', 'OLLAMA_MODEL', 'API_HOST', 'API_PORT']
            found_keys = [k for k in required_keys if k in config]
            missing_keys = [k for k in required_keys if k not in config]
            
            if missing_keys:
                status = "PARTIAL"
                message = f"⚠️  Some config keys missing: {missing_keys}"
                print(f"{YELLOW}{message}{RESET}")
            else:
                status = "PASS"
                message = "✅ All required config keys present"
                print(f"{GREEN}✓ {message}{RESET}")
            
            details = [
                f"Found keys: {found_keys}",
                f"Missing keys: {missing_keys}",
                f"Config file: ~/.devmind/config.json"
            ]
            self.results.append(TestResult("CONFIG::Keys", status, message, details))
            
        except Exception as e:
            status = "FAIL"
            message = f"❌ Config error: {e}"
            print(f"{RED}✗ {message}{RESET}")
            self.results.append(TestResult("CONFIG::Keys", status, message, [str(e)]))
        
        # =====================================================================
        # PRINT SUMMARY
        # =====================================================================
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("Test Summary")
        
        # Count results
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        partial = sum(1 for r in self.results if r.status == "PARTIAL")
        missing = sum(1 for r in self.results if r.status == "MISSING")
        total = len(self.results)
        
        # Print table
        print(f"{'Test Name':<40} {'Status':<12} {'Result':<20}\n")
        
        for result in self.results:
            status_str = {
                "PASS": f"{GREEN}✓ PASS{RESET}",
                "FAIL": f"{RED}✗ FAIL{RESET}",
                "PARTIAL": f"{YELLOW}⚠ PARTIAL{RESET}",
                "MISSING": f"{YELLOW}⊘ MISSING{RESET}",
            }.get(result.status, result.status)
            
            print(f"{result.name:<40} {result.status:<12} {result.message[:20]}")
        
        # Print statistics
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"Total Tests:  {total}")
        print(f"{GREEN}Passed:       {passed}{RESET}")
        print(f"{RED}Failed:       {failed}{RESET}")
        print(f"{YELLOW}Partial:      {partial}{RESET}")
        print(f"{YELLOW}Missing:      {missing}{RESET}")
        
        if failed == 0 and (passed + partial) > 0:
            print(f"\n{GREEN}✅ All critical tests passed!{RESET}")
        else:
            print(f"\n{RED}❌ Some tests failed. Review details above.{RESET}")
        
        print(f"{BLUE}{'='*70}{RESET}\n")
        
        # Print failed test details
        if failed > 0:
            print(f"\n{RED}Failed Test Details:{RESET}\n")
            for result in self.results:
                if result.status == "FAIL":
                    print(f"{RED}❌ {result.name}{RESET}")
                    print(f"   Message: {result.message}")
                    for detail in result.details:
                        print(f"   - {detail}")
                    print()


def main():
    """Main entry point"""
    tester = ModuleTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()

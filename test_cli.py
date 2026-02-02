#!/usr/bin/env python3
"""
DevMind CLI Test Suite
Tests all CLI commands for basic functionality
"""

import subprocess
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def run_test(name, command, expect_success=True):
    """Run a CLI test command"""
    print(f"\n{BLUE}Testing:{RESET} {name}")
    print(f"  Command: devmind {command}")
    
    try:
        result = subprocess.run(
            f"devmind {command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Check result
        success = (result.returncode == 0) if expect_success else (result.returncode != 0)
        
        if success:
            print(f"  {GREEN}✓ PASS{RESET}")
            if result.stdout:
                print(f"  Output: {result.stdout[:200]}")
            return True
        else:
            print(f"  {RED}✗ FAIL{RESET}")
            print(f"  Expected: {'success' if expect_success else 'failure'}")
            print(f"  Got return code: {result.returncode}")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  {YELLOW}⚠ TIMEOUT{RESET}")
        return False
    except Exception as e:
        print(f"  {RED}✗ ERROR: {e}{RESET}")
        return False


def main():
    """Run all CLI tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}DevMind CLI Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    tests = [
        # Basic commands
        ("Help command", "--help", True),
        ("Version command", "--version", True),
        
        # Core commands
        ("Status command", "status", True),
        ("Docker status", "docker status", True),
        
        # Project creation
        ("New command help", "new --help", True),
        
        # AI commands (these should fail gracefully if dependencies missing)
        ("Explain help", "explain --help", True),
        ("Commit help", "commit --help", True),
        ("Analyze help", "analyze --help", True),
        ("Edit help", "edit --help", True),
        ("Solve help", "solve --help", True),
        ("Fix help", "fix --help", True),
        ("Suggest help", "suggest --help", True),
        ("Chat help", "chat --help", True),
        
        # Invalid command (should fail)
        ("Invalid command", "invalid_command", False),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    for name, command, expect_success in tests:
        success = run_test(name, command, expect_success)
        results.append((name, success))
        if success:
            passed += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"\n  Total tests: {len(tests)}")
    print(f"  {GREEN}Passed: {passed}{RESET}")
    print(f"  {RED}Failed: {failed}{RESET}")
    
    if failed == 0:
        print(f"\n{GREEN}🎉 All tests passed!{RESET}\n")
        return 0
    else:
        print(f"\n{RED}❌ Some tests failed{RESET}\n")
        print("Failed tests:")
        for name, success in results:
            if not success:
                print(f"  - {name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

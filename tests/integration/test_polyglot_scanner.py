import pytest
import os
import shutil
from tools.code_analyzer.scanners import ComplexityScanner


@pytest.mark.skipif(not shutil.which("lizard"), reason="Lizard not installed")
def test_cpp_complexity_scan():
    """
    Verifies that ComplexityScanner correctly uses Lizard to detect high complexity
    in C++ code, even when starting from a string (using temp file mechanism).
    """
    # Contains a function with Cyclomatic Complexity > 10 (lots of if/else)
    complex_cpp_code = """
    #include <iostream>

    void complex_function(int x) {
        if (x == 1) { std::cout << "1"; }
        else if (x == 2) { std::cout << "2"; }
        else if (x == 3) { std::cout << "3"; }
        else if (x == 4) { std::cout << "4"; }
        else if (x == 5) { std::cout << "5"; }
        else if (x == 6) { std::cout << "6"; }
        else if (x == 7) { std::cout << "7"; }
        else if (x == 8) { std::cout << "8"; }
        else if (x == 9) { std::cout << "9"; }
        else if (x == 10) { std::cout << "10"; }
        else if (x == 11) { std::cout << "11"; }
        else { std::cout << "other"; }
    }
    """

    scanner = ComplexityScanner()
    # Pass virtual path to trigger correct extension handling
    results = scanner.scan(complex_cpp_code, "src/complex_logic.cpp")

    # Assertions
    assert len(results) > 0, "Should have detected at least one issue"
    found_complexity = any("complexity" in r.message.lower() for r in results)
    assert found_complexity, "Should mention complexity in the warning message"

    # Verify the function name is captured
    found_func = any("complex_function" in r.message for r in results)
    assert found_func, "Should identify the complex function name"


def test_scanner_handles_missing_file_path_gracefully():
    scanner = ComplexityScanner()
    results = scanner.scan("int main() {}", None)
    assert isinstance(results, list)

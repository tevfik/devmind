import pytest
from pathlib import Path
from tools.code_analyzer.parsers.tree_sitter_parser import TreeSitterParser


@pytest.fixture
def cpp_sample(tmp_path):
    code = """
    #include <iostream>

    // Global function
    int add(int a, int b) {
        return a + b;
    }

    class Calculator {
    public:
        // Method inside class
        int multiply(int x, int y) {
            return x * y;
        }
    };

    // Function returning pointer
    int* create_int(int val) {
        return new int(val);
    }
    """
    f = tmp_path / "test.cpp"
    f.write_text(code)
    return f


@pytest.fixture
def python_sample(tmp_path):
    code = """
def global_func(a, b):
    return a + b

class MyClass:
    def method_one(self, x):
        return x * 2

    def method_two(self, y: int = 10):
        print("hello")
"""
    f = tmp_path / "test.py"
    f.write_text(code)
    return f


def test_cpp_parser_detailed(cpp_sample, tmp_path):
    parser = TreeSitterParser("cpp")
    analysis = parser.parse(cpp_sample.read_text(), cpp_sample, tmp_path)

    assert analysis is not None

    # Check Classes
    assert len(analysis.classes) == 1
    calc_class = analysis.classes[0]
    assert calc_class.name == "Calculator"

    # Check Methods inside Class
    # The 'multiply' function should be in calc_class.methods
    assert len(calc_class.methods) == 1
    method = calc_class.methods[0]
    assert method.name == "multiply"
    assert "int x" in method.args[0]
    assert "int y" in method.args[1]

    # Check Global Functions
    # 'add' and 'create_int' should be top level
    assert len(analysis.functions) == 2
    func_names = [f.name for f in analysis.functions]
    assert "add" in func_names
    assert "create_int" in func_names

    # Check Args for add
    add_func = next(f for f in analysis.functions if f.name == "add")
    assert "int a" in add_func.args[0]
    assert "int b" in add_func.args[1]


def test_python_parser_detailed(python_sample, tmp_path):
    parser = TreeSitterParser("python")
    analysis = parser.parse(python_sample.read_text(), python_sample, tmp_path)

    assert analysis is not None

    # Check Classes
    assert len(analysis.classes) == 1
    cls = analysis.classes[0]
    assert cls.name == "MyClass"

    # Check Methods
    assert len(cls.methods) == 2
    method_names = [m.name for m in cls.methods]
    assert "method_one" in method_names
    assert "method_two" in method_names

    # Check Args
    m1 = next(m for m in cls.methods if m.name == "method_one")
    # Python args extraction might include 'self' depending on capture
    assert "self" in m1.args
    assert "x" in m1.args

    # Check Global Function
    assert len(analysis.functions) == 1
    g = analysis.functions[0]
    assert g.name == "global_func"
    assert "a" in g.args
    assert "b" in g.args


if __name__ == "__main__":
    pytest.main([__file__])

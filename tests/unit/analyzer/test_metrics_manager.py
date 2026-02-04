import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile
from tools.metrics import MetricsManager


class TestMetricsManager(unittest.TestCase):
    def setUp(self):
        self.manager = MetricsManager()

    def test_python_complexity(self):
        with NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def complex_function(n):
    if n < 2:
        return n
    elif n == 2:
        return 1
    else:
        for i in range(n):
            if i % 2 == 0:
                print(i)
        return n
"""
            )
            path = Path(f.name)

        try:
            metrics = self.manager.get_metrics(path)
            complexity = metrics["complexity"]

            self.assertEqual(complexity["tool"], "radon")
            self.assertGreater(complexity["avg_complexity"], 1)
            # Radon counts if/elif/for/if as +1 each usually.

            lines = metrics["lines"]
            self.assertGreater(lines["total"], 0)
            self.assertGreater(lines["code"], 0)

        finally:
            path.unlink()

    def test_generic_complexity(self):
        # Test C code (handled by lizard)
        with NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write(
                """
int main() {
    if (1) {
        return 0;
    }
    return 1;
}
"""
            )
            path = Path(f.name)

        try:
            metrics = self.manager.get_metrics(path)
            complexity = metrics["complexity"]

            self.assertEqual(complexity["tool"], "lizard")
            self.assertGreater(complexity["max_complexity"], 1)

        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()

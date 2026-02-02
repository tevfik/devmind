.PHONY: help install test clean docker-start docker-stop docker-status test-modules test-all

help:
	@echo "DevMind AI - Makefile Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install          Install DevMind (pipx)"
	@echo "  make install-dev      Install in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run CLI test suite (14 tests)"
	@echo "  make test-modules     Run comprehensive module tests (20 tests)"
	@echo "  make test-all         Run all tests (CLI + modules)"
	@echo "  make test-verbose     Run tests with verbose output"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-start     Start Docker services"
	@echo "  make docker-stop      Stop Docker services"
	@echo "  make docker-status    Check Docker services"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove temporary files"
	@echo "  make uninstall        Uninstall DevMind"

install:
	@echo "🚀 Installing DevMind with pipx..."
	pipx install -e . --force
	@echo "✅ Installation complete! Run 'devmind --help' to get started."

install-dev:
	@echo "🔧 Installing DevMind in development mode..."
	pip install -e .
	@echo "✅ Development installation complete!"

test:
	@echo "🧪 Running CLI test suite..."
	@python3 test_cli.py

test-verbose:
	@echo "🧪 Running CLI tests (verbose)..."
	@python3 test_cli.py -v

test-modules:
	@echo "🔬 Running comprehensive module tests..."
	@python3 test_modules.py

test-all: test test-modules
	@echo "✅ All tests completed!"

docker-start:
	@devmind docker start

docker-stop:
	@devmind docker stop

docker-status:
	@devmind docker status

clean:
	@echo "🧹 Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"

uninstall:
	@echo "🗑️  Uninstalling DevMind..."
	pipx uninstall devmind
	@echo "✅ DevMind uninstalled!"

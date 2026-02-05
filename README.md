# Yaver AI

**AI-powered development assistant with autonomous capabilities**

Yaver is a CLI tool that combines deep code analysis, semantic search, and autonomous task execution to help you understand and improve your codebase.

## ✨ Features

- 🤖 **Autonomous Task Execution** - Give it a task, it plans and executes
- 💬 **Interactive Code Chat** - Ask questions about your codebase in natural language
- 🔍 **Deep Code Analysis** - AST parsing + Graph database + Semantic embeddings
- 🔗 **Forge Integration** - Gitea/GitHub PR and issue management
- 🧠 **Multi-Backend Memory** - Qdrant (primary) or ChromaDB for vector storage
- 📊 **Code Intelligence** - Complexity analysis, impact simulation, architecture visualization

## 🚀 Quick Start

```bash
# 1. Install
pip install -e .

# 2. Setup (interactive wizard)
yaver setup

# 3. Start services (Docker)
cd docker && docker-compose up -d

# 4. Use
yaver chat                          # Interactive chat
yaver work "Add logging to auth"    # Autonomous task
yaver code analyze .                # Deep analysis
```

## 📋 Commands

### Core
- `yaver chat` - Interactive AI chat with codebase context
- `yaver work <task>` - Autonomous task execution with tools
- `yaver new <name>` - Scaffold new project

### Code Analysis
- `yaver code analyze [--type deep]` - Analyze repository (AST + Graph + Embeddings)
- `yaver code query <question>` - Semantic search across codebase
- `yaver code inspect <file>` - Detailed file analysis
- `yaver code insights` - Quality metrics and recommendations
- `yaver code visualize` - Generate architecture diagrams

### System Management
- `yaver system status` - Check all services (Ollama, Qdrant, Neo4j)
- `yaver system setup` - Run configuration wizard
- `yaver docker [start|stop|status]` - Manage Docker services

### Agent & Memory
- `yaver agent status` - View agent learning state
- `yaver agent history` - Decision history
- `yaver memory [list|switch|new]` - Session management

### Utilities
- `yaver commit` - Generate commit messages
- `yaver explain <code>` - Explain code or commands

## 📚 Documentation

- [Quick Start Guide](docs/QUICK_START.md) - Get running in 5 minutes
- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [CLI Reference](docs/CLI_GUIDE.md) - Complete command reference
- [Architecture](docs/ARCHITECTURE.md) - System design and components
- [Deep Analysis](docs/DEEP_ANALYSIS_GUIDE.md) - Understanding the analysis engine
- [Contributing](docs/CONTRIBUTING.md) - Development guidelines

## 🏗️ Architecture

```
Yaver AI
├── AutonomousWorker (LangChain Agent + Tool Calling)
├── RAG Service (Neo4j Graph + Qdrant Vectors)
├── Memory Manager (Mem0 + Qdrant)
├── Tool Registry (File, Git, Shell, Forge, Analysis)
└── CLI (Rich Terminal UI)
```

**Supported Backends:**
- **LLM**: Ollama (local)
- **Vector DB**: Qdrant (primary), ChromaDB (fallback)
- **Graph DB**: Neo4j
- **Memory**: Mem0 with Qdrant/ChromaDB

## 🧪 Testing

```bash
pytest                    # Run all tests
pytest tests/unit         # Unit tests only
pytest tests/integration  # Integration tests
```

**Status**: ✅ 46/46 tests passing

## 🔧 Requirements

- Python 3.10+
- Docker (for Qdrant, Neo4j, Ollama)
- Git

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/tevfik/yaver.git
cd yaver

# Install with virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Or install with pipx
pipx install -e .
```

## ⚙️ Configuration

Run the interactive setup wizard:

```bash
yaver setup
```

This creates `~/.yaver/config.json` with:
- Ollama URL and models
- Qdrant/ChromaDB configuration
- Neo4j credentials
- Forge (Gitea/GitHub) tokens

Or manually create `.env`:

```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERAL=llama3.1:8b
OLLAMA_MODEL_EMBEDDING=nomic-embed-text

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_MODE=local
VECTOR_DB_PROVIDER=qdrant

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## 🐳 Docker Services

```bash
# Start all services
cd docker
docker-compose up -d

# Or use Yaver CLI
yaver docker start
yaver docker status
yaver docker logs
```

## 🤝 Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

## 🔗 Links

- **GitHub**: https://github.com/tevfik/yaver
- **Issues**: https://github.com/tevfik/yaver/issues
- **Discussions**: https://github.com/tevfik/yaver/discussions

---

**Version**: 1.2.0 | **Status**: Production Ready ✅

# DevMind Project Structure

Comprehensive overview of the DevMind project organization.

## 📁 Directory Layout

```
devmind/
├── src/                          # Main source code (organized modules)
│   ├── __init__.py
│   │
│   ├── cli/                      # Command-line interface
│   │   ├── __init__.py
│   │   ├── cli.py                # Main CLI entry point
│   │   ├── cli_edit.py            # Edit command implementation
│   │   ├── cli_extended.py        # Extended CLI features
│   │   ├── cli_interact.py        # Interactive mode
│   │   ├── cli_query_commands.py  # Query commands
│   │   ├── cli_solve.py           # Problem-solving commands
│   │   └── docker_manager.py      # Docker orchestration
│   │
│   ├── agents/                   # AI agents
│   │   ├── __init__.py
│   │   ├── agent_base.py          # Base agent class
│   │   ├── agent_coder.py         # Code generation agent
│   │   ├── agent_git_analyzer.py  # Git analysis agent
│   │   ├── agent_graph.py         # Graph analysis agent
│   │   ├── agent_memory.py        # Memory management
│   │   ├── agent_planner.py       # Task planning
│   │   ├── agent_reviewer.py      # Code review agent
│   │   └── agent_task_manager.py  # Task orchestration
│   │
│   ├── tools/                    # Tool modules
│   │   ├── __init__.py
│   │   ├── codebase_analyzer.py   # Code analysis tools
│   │   ├── git_ops.py             # Git operations
│   │   ├── interaction_logger.py  # Logging
│   │   ├── memory_ops.py          # Memory operations
│   │   ├── neo4j_analyzers.py     # Neo4j graph analysis
│   │   ├── repo_manager.py        # Repository management
│   │   └── sandbox.py             # Isolated execution
│   │
│   ├── config/                   # Configuration
│   │   ├── __init__.py
│   │   ├── config.py              # Main configuration
│   │   └── onboarding.py          # Setup wizard
│   │
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── api.py                 # FastAPI server
│   │   ├── api_client.py          # API client
│   │   ├── engine.py              # Core engine
│   │   ├── internal_state.py      # State management
│   │   ├── query_orchestrator.py  # Query orchestration
│   │   └── run_agent.py           # Agent runner
│   │
│   └── utils/                    # Utilities
│       └── __init__.py
│
├── docker/                       # Docker configuration
│   ├── docker-compose.yml        # Docker compose file
│   ├── README.md                 # Docker guide
│   └── data/                     # Docker volumes
│
├── docs/                         # Documentation
│   ├── PROJECT_STRUCTURE.md      # This file
│   ├── ARCHITECTURE.md           # Architecture guide
│   ├── CLI_FEATURES.md           # CLI documentation
│   ├── ANALYSIS_PROJECT_MEMORY_ARCHITECTURE.md
│   └── README.md
│
├── prompts/                      # AI prompts
│   ├── coder_*.md
│   ├── planner_*.md
│   ├── reviewer_*.md
│   ├── task_manager_*.md
│   └── git_analyzer_*.md
│
├── memory/                       # Memory management
│   └── manager.py
│
├── tools/                        # Legacy tools (to be migrated)
│   └── git_analysis.py
│
├── .data/                        # Temporary data (gitignored)
│   ├── cache/                    # Cache files
│   ├── logs/                     # Application logs
│   ├── output/                   # Output files
│   ├── chroma_db/                # ChromaDB storage
│   └── temp_repos/               # Cloned repositories
│
├── .devmind/                     # User configuration (gitignored)
│   ├── .env                      # Configuration variables
│   └── config.json               # Saved settings
│
├── .github/                      # GitHub workflows (if added)
├── tests/                        # Test files (to be added)
│
├── README.md                     # Project README
├── INSTALLATION.md               # Installation guide
├── DOCKER_INTEGRATION_SUMMARY.md # Docker integration docs
├── QUICK_INSTALL.sh              # Quick install script
├── BASLA.md                      # Turkish guide
├── ONBOARDING.md                 # Onboarding guide
├── setup.py                      # Python package setup
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
├── __init__.py                   # Package init
└── .git/                         # Git repository

```

## 📦 Module Organization

### CLI Module (`src/cli/`)
Handles all command-line interactions.

**Key Files:**
- `cli.py` - Main entry point, argument parsing
- `docker_manager.py` - Docker service orchestration
- `cli_*.py` - Specific command handlers

**Responsibilities:**
- Parse command-line arguments
- Route to appropriate handlers
- Display formatted output
- Handle user interactions

### Agents Module (`src/agents/`)
AI agents for different tasks.

**Key Agents:**
- `agent_base.py` - Base class for all agents
- `agent_coder.py` - Code generation and fixes
- `agent_reviewer.py` - Code review
- `agent_git_analyzer.py` - Git repository analysis
- `agent_planner.py` - Task planning
- `agent_task_manager.py` - Task orchestration

**Responsibilities:**
- Execute specific tasks
- Interact with LLM
- Manage memory and state
- Coordinate with other agents

### Tools Module (`src/tools/`)
Utility functions and specialized tools.

**Key Tools:**
- `codebase_analyzer.py` - Parse and analyze code
- `git_ops.py` - Git operations (clone, analyze)
- `memory_ops.py` - Memory database operations
- `repo_manager.py` - Repository management
- `sandbox.py` - Isolated code execution

**Responsibilities:**
- Provide reusable functionality
- Interface with external services
- Handle low-level operations

### Config Module (`src/config/`)
Configuration and setup.

**Key Files:**
- `config.py` - Configuration loading/saving
- `onboarding.py` - Initial setup wizard

**Responsibilities:**
- Load configuration
- Validate settings
- Guide first-time users

### Core Module (`src/core/`)
Core business logic.

**Key Components:**
- `engine.py` - Main processing engine
- `query_orchestrator.py` - Query processing
- `api.py` - FastAPI server
- `internal_state.py` - State management

**Responsibilities:**
- Main application flow
- Orchestrate agents
- Manage application state

## 🔄 Data Flow

```
User Input
    ↓
CLI (src/cli/cli.py)
    ↓
Config Validation (src/config/config.py)
    ↓
Agent Selection (src/agents/)
    ↓
Tools Execution (src/tools/)
    ↓
Memory Management (src/core/internal_state.py)
    ↓
Output Formatting
    ↓
User Output
```

## 🚀 Quick Start with New Structure

### Import Examples

**Before (Root level):**
```python
from cli import main
from agent_base import AgentBase
from config import get_config
```

**After (Organized):**
```python
from src.cli import main
from src.agents import AgentBase
from src.config import get_config
```

### Running DevMind

```bash
# Development
python -m src.cli.cli chat

# After install
pip install -e .
devmind chat

# Using specific modules
python -c "from src.agents import AgentBase"
```

## 📋 File Organization Rules

### Add New Python Files

1. **CLI Commands** → `src/cli/`
2. **New Agents** → `src/agents/`
3. **Utility Functions** → `src/tools/`
4. **Configuration** → `src/config/`
5. **Business Logic** → `src/core/`
6. **Helper Functions** → `src/utils/`

### Add New Documentation

1. **Project Docs** → `docs/`
2. **API Reference** → `docs/API_REFERENCE.md`
3. **Architecture** → `docs/ARCHITECTURE.md`
4. **Usage Guides** → `docs/GUIDES/`

### Add Temporary Files

1. **Logs** → `.data/logs/`
2. **Cache** → `.data/cache/`
3. **Output** → `.data/output/`
4. **Temp Repos** → `.data/temp_repos/`

## 🔐 Gitignore Strategy

**Ignored (Temporary):**
- `.data/` - Temporary data
- `.devmind/` - User config
- `__pycache__/` - Python cache
- `*.log` - Log files
- `.venv/` - Virtual env

**Tracked (Source Code):**
- `src/` - All source code
- `docs/` - Documentation
- `tests/` - Test files
- `docker/` - Docker config
- `setup.py` - Package config
- `requirements.txt` - Dependencies

## 📦 Installation

### From Source

```bash
# Clone and install in development mode
pip install -e .

# Run
devmind chat
```

### Package Contents

The package includes:
- All source code from `src/`
- Configuration templates
- Docker compose file
- Documentation
- Requirements

## 🎯 Benefits of This Structure

✅ **Clear Organization**
- Each module has a single purpose
- Easy to find related code

✅ **Scalability**
- Easy to add new modules
- Supports growth

✅ **Maintainability**
- Less technical debt
- Easier to understand

✅ **Collaboration**
- New developers can navigate easily
- Clear code ownership

✅ **Testing**
- Easy to test individual modules
- Mock dependencies easily

✅ **Deployment**
- Standard Python package structure
- Works with PyPI and pip

## 🔗 Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [CLI_FEATURES.md](CLI_FEATURES.md) - Available commands
- [../DOCKER_INTEGRATION_SUMMARY.md](../DOCKER_INTEGRATION_SUMMARY.md) - Docker setup
- [../README.md](../README.md) - Project overview

## 📝 Notes

- This structure follows Python packaging best practices
- Inspired by Flask, Django, and other mature Python projects
- Easy migration path for future enhancements
- Ready for open-source contribution

---

**Last Updated:** February 2, 2026  
**Version:** 1.0.0  
**Structure Type:** Modular with `src/` layout

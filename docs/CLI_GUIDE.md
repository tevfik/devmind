# CLI Command Reference

Complete reference for all Yaver commands.

## Core Commands

### `yaver chat`
Interactive AI chat with codebase context.

```bash
yaver chat                              # Chat with all learned code
yaver chat --project-id=myapp           # Limit to specific project
yaver chat --session-id=debug-session   # Continue previous conversation
```

**Features:**
- Semantic search across codebase
- Natural language queries
- Context-aware responses using RAG
- Session-based conversation history

---

### `yaver work`
Autonomous task execution with tool calling.

```bash
yaver work "Add logging to authentication module"
yaver work "Refactor database connection pooling"
yaver work "Fix bug in user validation"
```

**How it works:**
1. Agent analyzes the task
2. Retrieves relevant code context
3. Plans approach using ReAct pattern
4. Executes using tools (read, edit, shell, git)
5. Reports results

**Available Tools:**
- File operations (read, write, edit)
- Git operations (commit, branch, push)
- Shell commands
- Code analysis
- Forge operations (PR, issues)

---

### `yaver new`
Scaffold a new project.

```bash
yaver new myproject
yaver new myproject --template=fastapi
```

---

## Code Analysis

### `yaver code analyze`
Analyze repository structure and code.

```bash
yaver code analyze .                    # Quick overview
yaver code analyze . --type deep        # Full analysis (AST + Graph + Embeddings)
yaver code analyze . --type deep --project-id=myapp  # Store in project
yaver code analyze . --incremental      # Only analyze changed files
```

**Analysis Types:**
- `overview` - Basic stats (default)
- `structure` - Language and file breakdown
- `deep` - Full analysis with AST, Neo4j graph, and embeddings

---

### `yaver code query`
Semantic search across codebase.

```bash
yaver code query "authentication logic"
yaver code query "database connection" --project-id=backend
```

---

### `yaver code inspect`
Detailed analysis of specific file or function.

```bash
yaver code inspect src/auth.py
yaver code inspect src/auth.py --function=login
yaver code inspect src/models.py --class=User
```

---

### `yaver code insights`
Code quality metrics and recommendations.

```bash
yaver code insights
yaver code insights --complexity      # Complexity analysis
yaver code insights --quality         # Quality report
```

---

### `yaver code visualize`
Generate architecture diagrams.

```bash
yaver code visualize . --type=class
yaver code visualize . --type=call-graph --function=main
```

Output is in Mermaid format, viewable in GitHub or compatible editors.

---

## System Management

### `yaver system status`
Check system health and configuration.

```bash
yaver system status
```

Shows:
- Ollama connection and models
- Qdrant/ChromaDB status
- Neo4j connection
- Active sessions and projects
- Memory usage

---

### `yaver system setup`
Run configuration wizard.

```bash
yaver system setup
```

Interactive wizard to configure:
- Ollama URL and models
- Vector database (Qdrant/ChromaDB)
- Neo4j credentials
- Forge integration (optional)

---

### `yaver docker`
Manage Docker services.

```bash
yaver docker start      # Start all services
yaver docker stop       # Stop all services
yaver docker status     # Check service status
yaver docker logs       # View real-time logs
yaver docker restart    # Restart all services
```

---

## Agent Management

### `yaver agent status`
View agent learning state.

```bash
yaver agent status <project-id>
```

Shows:
- Number of learned patterns
- User preferences
- Last analysis timestamp

---

### `yaver agent history`
View decision history.

```bash
yaver agent history <project-id>
yaver agent history <project-id> --limit=20
```

---

## Memory & Sessions

### `yaver memory list`
List all chat sessions.

```bash
yaver memory list
```

---

### `yaver memory switch`
Switch to different chat session.

```bash
yaver memory switch <session-id>
```

---

### `yaver memory new`
Create new chat session.

```bash
yaver memory new --name="Feature Planning"
yaver memory new --name="Debug Session" --tag=debug
```

---

## Utilities

### `yaver commit`
Generate commit message from staged changes.

```bash
git add .
yaver commit
yaver commit --context "Fixed auth bug from issue #123"
```

---

### `yaver explain`
Explain code or shell commands.

```bash
yaver explain "git rebase -i HEAD~3"
yaver explain "find . -name '*.py' -exec grep -l 'TODO' {} \\;"
```

---

## Examples

### Multi-Repository Project
```bash
# Learn multiple repos into one project
yaver code analyze ~/backend --type deep --project-id=microservices
yaver code analyze ~/frontend --type deep --project-id=microservices
yaver code analyze ~/auth --type deep --project-id=microservices

# Chat with entire project
yaver chat --project-id=microservices
```

### Autonomous Workflow
```bash
# Let agent work on task
yaver work "Add rate limiting to API endpoints"

# Agent will:
# 1. Analyze current code
# 2. Plan implementation
# 3. Edit files
# 4. Create branch
# 5. Commit changes
# 6. Optionally create PR
```

### Code Investigation
```bash
# Deep analysis
yaver code analyze . --type deep

# Search for specific functionality
yaver code query "payment processing"

# Inspect specific file
yaver code inspect src/payments.py

# Get quality insights
yaver code insights --quality
```

---

## Configuration

### Environment Variables

Create `.env` in project root or `~/.yaver/.env`:

```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERAL=llama3.1:8b
OLLAMA_MODEL_CODE=codellama:13b
OLLAMA_MODEL_EMBEDDING=nomic-embed-text

# Vector Database
VECTOR_DB_PROVIDER=qdrant  # or 'chroma'
QDRANT_URL=http://localhost:6333
QDRANT_MODE=local
QDRANT_COLLECTION=yaver_memory

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Forge (optional)
FORGE_PROVIDER=gitea  # or 'github'
FORGE_URL=https://gitea.example.com
FORGE_TOKEN=your_token_here
```

---

## Tips

- **Use project IDs** to organize multi-repo projects
- **Incremental analysis** saves time on large repos
- **Session management** keeps conversations organized
- **Docker commands** simplify service management
- **Autonomous mode** works best with clear, specific tasks

---

## Getting Help

```bash
yaver --help                    # General help
yaver <command> --help          # Command-specific help
yaver system status             # Check system health
```

**Documentation:**
- [Quick Start](QUICK_START.md)
- [Installation](INSTALLATION.md)
- [Architecture](ARCHITECTURE.md)

**Support:**
- GitHub Issues: https://github.com/tevfik/yaver/issues
- Logs: `~/.yaver/logs/yaver.log`

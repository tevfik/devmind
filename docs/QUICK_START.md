# Quick Start Guide

Get Yaver AI running in 5 minutes.

## 1. Install

```bash
# Clone repository
git clone https://github.com/tevfik/yaver.git
cd yaver

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install
pip install -e .
```

## 2. Start Services

Yaver requires Docker services (Qdrant, Neo4j, Ollama):

```bash
cd docker
docker-compose up -d
```

**Verify services are running:**
```bash
yaver docker status
```

## 3. Configure

Run the interactive setup wizard:

```bash
yaver setup
```

This will:
- Configure Ollama (LLM)
- Set up Qdrant or ChromaDB (vector database)
- Configure Neo4j (graph database)
- Optionally set up Forge integration (Gitea/GitHub)

## 4. First Use

### Interactive Chat
```bash
yaver chat
```

Ask questions about your code:
- "How does authentication work?"
- "Find all database queries"
- "What functions call login()?"

### Deep Analysis
Learn your codebase:

```bash
yaver code analyze . --type deep
```

This creates:
- AST (Abstract Syntax Tree)
- Code graph in Neo4j
- Semantic embeddings in Qdrant

### Autonomous Task
Let Yaver work for you:

```bash
yaver work "Add type hints to auth module"
```

The agent will:
1. Analyze the task
2. Plan the approach
3. Execute using tools (read, edit, git)
4. Report results

## Common Commands

```bash
# Chat
yaver chat                          # Interactive chat
yaver chat --project-id=myapp       # Chat with specific project

# Code Analysis
yaver code analyze .                # Quick overview
yaver code analyze . --type deep    # Full analysis (AST + Graph + Embeddings)
yaver code query "authentication"   # Semantic search

# Autonomous Work
yaver work "task description"       # Execute task

# System
yaver system status                 # Check all services
yaver docker start                  # Start Docker services
yaver docker logs                   # View service logs

# Utilities
yaver commit                        # Generate commit message
yaver explain "git rebase -i HEAD~3"  # Explain command
```

## Troubleshooting

### "yaver: command not found"
```bash
# Activate virtual environment
source .venv/bin/activate

# Or reinstall
pip install -e .
```

### Services not running
```bash
# Check Docker
docker ps

# Start services
yaver docker start

# Check status
yaver docker status
```

### Ollama connection error
```bash
# Check Ollama is running
curl http://localhost:11434

# Or start Ollama container
docker-compose up -d ollama
```

### Qdrant connection error
```bash
# Check Qdrant is running
curl http://localhost:6333

# Or start Qdrant
docker-compose up -d qdrant
```

### Neo4j connection error
```bash
# Check Neo4j is running
docker ps | grep neo4j

# Or start Neo4j
docker-compose up -d neo4j

# Default credentials:
# Username: neo4j
# Password: password
```

## Next Steps

1. **Read the docs**: [CLI Guide](CLI_GUIDE.md), [Architecture](ARCHITECTURE.md)
2. **Analyze your code**: `yaver code analyze . --type deep`
3. **Try autonomous mode**: `yaver work "your task"`
4. **Explore chat**: `yaver chat` and ask questions

## Performance Tips

- **First analysis is slow** (~2-5 min for medium repos) - embeddings are cached
- **Incremental analysis** - Only changed files are re-analyzed
- **Use project IDs** - Group related repos for better context
- **Docker resources** - Allocate 4GB+ RAM for smooth operation

## Configuration Files

- `~/.yaver/config.json` - Main configuration
- `.env` - Environment variables (optional)
- `docker/docker-compose.yml` - Service definitions

## Getting Help

- **Documentation**: See `docs/` folder
- **Issues**: https://github.com/tevfik/yaver/issues
- **Status check**: `yaver system status`
- **Logs**: `~/.yaver/logs/yaver.log`

---

**Ready to go!** Start with `yaver chat` or `yaver code analyze .`

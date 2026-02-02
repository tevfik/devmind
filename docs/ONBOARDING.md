# Onboarding & Setup Guide

## Quick Start

```bash
# Interactive setup on first run
devmind chat

# Or manual setup:
devmind setup

# Verify configuration
devmind status
```

## How It Works

When DevMind runs for the first time, it automatically opens the **setup wizard** if configuration doesn't exist:

```
============================================================
          🚀 DevMind Setup Wizard
============================================================

Let's configure DevMind for your first time!
```

## What Gets Configured

### 1️⃣ **Ollama (Local LLM)**

Ollama is the heart of DevMind - your local language model.

**Why Ollama?**
- Runs locally (no cloud)
- Free and open-source
- Full control over your data
- Works offline

**Setup Process:**
```bash
# Start Ollama service
ollama serve

# In another terminal, pull model
ollama pull nemotron-3-nano:30b
```

**What the wizard does:**
- Detects if Ollama is installed
- Checks if Ollama is running
- Tests connection to Ollama API
- Saves Ollama URL and model name to config

### 2️⃣ **Qdrant (Vector Database) - Optional**

For semantic search across your codebase.

```bash
# Start Qdrant with Docker
docker run -p 6333:6333 qdrant/qdrant
```

**Benefits:**
- Semantic code search
- Similar function detection
- Pattern matching

### 3️⃣ **Neo4j (Graph Database) - Optional**

For dependency analysis and code relationships.

```bash
# Start Neo4j with Docker
docker run \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

**Benefits:**
- Code dependency graphs
- Function call chains
- Architecture visualization

### 4️⃣ **Configuration File**

After setup, configuration is saved to:

```bash
~/.devmind/config.json
```

**Example:**
```json
{
  "ollama": {
    "base_url": "http://localhost:11434",
    "model": "nemotron-3-nano:30b",
    "embedding_model": "nomic-embed-text"
  },
  "qdrant": {
    "host": "localhost",
    "port": 6333,
    "enabled": true
  },
  "neo4j": {
    "uri": "bolt://localhost:7687",
    "username": "neo4j",
    "password": "password",
    "enabled": false
  },
  "storage": {
    "logs_dir": "~/.devmind/logs",
    "cache_dir": "~/.devmind/cache"
  }
}
```

## First Run After Setup

```bash
devmind chat
```

This opens an interactive session:
- Analyzes your repository
- Loads project context
- Ready for questions

**Example queries:**
```
> Analyze this repository
> What does the auth module do?
> Find all TODO comments
> Suggest improvements for error handling
```

## Environment Variables

Optional - Override config file:

```bash
# LLM
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=nemotron-3-nano:30b

# Qdrant
export QDRANT_HOST=localhost
export QDRANT_PORT=6333

# Neo4j
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=password

# DevMind
export DEVMIND_LOG_LEVEL=INFO
export DEVMIND_API_PORT=8000
```

## Troubleshooting Setup

### "Ollama not found"
```bash
# Install Ollama from https://ollama.ai
# Mac: brew install ollama
# Linux: Follow installation guide
# Then: ollama serve
```

### "Connection refused to Ollama"
```bash
# Make sure Ollama is running
ollama serve &

# Check it's working
curl http://localhost:11434/api/tags
```

### "Model not found"
```bash
# Pull the model
ollama pull nemotron-3-nano:30b

# Verify it's installed
ollama list
```

### "Qdrant connection failed"
```bash
# Make sure Docker is running
docker ps

# Start Qdrant if needed
docker run -p 6333:6333 qdrant/qdrant

# Check connection
curl http://localhost:6333/health
```

### "Import errors"
```bash
# Reinstall dependencies
pip install -e . --upgrade

# Or in virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Verify Installation

```bash
# Check status
devmind status

# Run a test
devmind analyze .

# Test with AI
devmind chat
> "What's in this repo?"
```

## Next Steps

After setup, explore these commands:

- **devmind chat** - Interactive conversation
- **devmind analyze** - Repository analysis
- **devmind commit** - Generate commit messages
- **devmind explain** - Explain shell commands
- **devmind solve** - Solve programming tasks

## Configuration Backup

```bash
# Backup your config
cp ~/.devmind/config.json ~/.devmind/config.backup.json

# Restore if needed
cp ~/.devmind/config.backup.json ~/.devmind/config.json
```

## Advanced Configuration

### Custom Ollama Model

```json
{
  "ollama": {
    "base_url": "http://remote-server:11434",
    "model": "mistral:latest",
    "embedding_model": "nomic-embed-text"
  }
}
```

### Remote Qdrant

```json
{
  "qdrant": {
    "host": "qdrant.example.com",
    "port": 6333,
    "api_key": "your-api-key"
  }
}
```

### Multiple Projects

Create separate configs:

```bash
# Project A config
devmind setup --config ~/.devmind/projecta.json

# Project B config
devmind setup --config ~/.devmind/projectb.json

# Use specific config
devmind chat --config ~/.devmind/projecta.json
```

## Getting Help

- Run setup again: `devmind setup`
- Check config: `cat ~/.devmind/config.json`
- View logs: `tail -f ~/.devmind/logs/devmind.log`
- Ask DevMind: `devmind chat` → "Help me configure Qdrant"

---

**Ready?** Start with: `devmind chat` 🚀

# Yaver AI Architecture

System design and component overview.

## Overview

Yaver is a modular AI development assistant built on:
- **LangChain** for agent orchestration
- **Ollama** for local LLM inference
- **Qdrant/ChromaDB** for vector storage
- **Neo4j** for code graph database
- **Mem0** for agent memory

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Yaver CLI                           │
│                  (Rich Terminal UI)                     │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │  Chat  │  │  Work  │  │  Code  │
    │ Agent  │  │ Agent  │  │Analysis│
    └────┬───┘  └────┬───┘  └────┬───┘
         │           │           │
         └───────────┼───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ┌─────────┐           ┌──────────────┐
    │   RAG   │           │ToolRegistry  │
    │ Service │           │              │
    └────┬────┘           └──────┬───────┘
         │                       │
    ┌────┴────┐            ┌─────┴──────┐
    │         │            │            │
    ▼         ▼            ▼            ▼
┌────────┐ ┌────────┐  ┌──────┐    ┌──────┐
│ Neo4j  │ │Qdrant  │  │ File │    │ Git  │
│ Graph  │ │Vectors │  │ Ops  │    │ Ops  │
└────────┘ └────────┘  └──────┘    └──────┘
```

## Core Components

### 1. AutonomousWorker
**Location**: `src/core/autonomous_worker.py`

**Purpose**: Execute tasks autonomously using ReAct pattern.

**Key Features:**
- LangChain agent with tool calling
- Context retrieval via RAG
- Memory persistence via Mem0
- Fallback to planner mode if tool calling unavailable

**Flow:**
1. Receive task description
2. Retrieve relevant context from RAG
3. Plan approach (ReAct: Thought → Action → Observation)
4. Execute using tools
5. Save results to memory

---

### 2. ToolRegistry
**Location**: `src/core/tools.py`

**Purpose**: Manage available tools for agents.

**Registered Tools:**
- `FileReadTool` - Read file contents
- `FileWriteTool` - Write to files
- `FileEditTool` - Edit existing files
- `ShellTool` - Execute shell commands
- `GitClient` - Git operations
- `AnalysisEngine` - Code analysis
- `ForgeTool` - Gitea/GitHub integration

**Interface:**
- `register(tool)` - Add new tool
- `get_tool(name)` - Retrieve tool by name
- `get_langchain_tools()` - Get LangChain-compatible tools

---

### 3. RAG Service
**Location**: `src/tools/rag/rag_service.py`

**Purpose**: Retrieval Augmented Generation for codebase queries.

**Components:**
- **Neo4j Adapter** - Graph-based retrieval (structure, relationships)
- **Vector Store** - Semantic search (Qdrant/ChromaDB)
- **Code Embedder** - Generate embeddings for code

**Retrieval Strategies:**
- `STRUCTURE` - Neo4j graph queries only
- `SEMANTIC` - Vector similarity search only
- `HYBRID` - Combine both (default)

**Flow:**
1. Classify query intent
2. Retrieve from Neo4j (structure)
3. Retrieve from Qdrant (semantics)
4. Merge and rank results
5. Generate answer with LLM

---

### 4. Memory Manager
**Location**: `src/memory/manager.py`

**Purpose**: Persistent memory for agents using Mem0.

**Features:**
- User-specific memory
- Vector-based storage (Qdrant/ChromaDB)
- Automatic embedding generation
- Search and retrieval

**Operations:**
- `add(text, metadata)` - Store memory
- `search(query, limit)` - Retrieve relevant memories
- `get_all(user_id)` - Get all memories for user
- `delete(memory_id)` - Remove specific memory

---

### 5. Code Analyzer
**Location**: `src/tools/code_analyzer/analyzer.py`

**Purpose**: Deep code analysis with AST, graph, and embeddings.

**Analysis Pipeline:**
1. **Parse** - AST extraction (tree-sitter)
2. **Index** - Store in Neo4j graph
3. **Embed** - Generate semantic embeddings
4. **Store** - Save to Qdrant/ChromaDB

**Capabilities:**
- Function/class extraction
- Dependency analysis
- Complexity metrics
- Impact simulation
- Semantic search

---

### 6. Forge Integration
**Location**: `src/tools/forge/`

**Purpose**: Interact with Git forges (Gitea, GitHub).

**Components:**
- `ForgeProvider` (ABC) - Interface
- `GiteaAdapter` - Gitea implementation
- `CredentialManager` - Multi-host token management
- `ForgeTool` - LangChain tool wrapper

**Operations:**
- Create pull requests
- Manage issues
- Add comments
- Query repository info

---

## Data Flow

### Chat Flow
```
User Query
    ↓
ChatAgent
    ↓
RAG Service
    ├→ Neo4j (structure)
    └→ Qdrant (semantics)
    ↓
Context + Query
    ↓
LLM (Ollama)
    ↓
Response
```

### Autonomous Work Flow
```
Task Description
    ↓
AutonomousWorker
    ↓
RAG (context retrieval)
    ↓
Agent Planning (ReAct)
    ↓
Tool Execution
    ├→ FileOps
    ├→ GitOps
    ├→ ShellOps
    └→ ForgeOps
    ↓
Memory Storage
    ↓
Result Report
```

### Code Analysis Flow
```
Repository Path
    ↓
CodeAnalyzer
    ├→ AST Parser
    ├→ Neo4j Indexer
    └→ Code Embedder
    ↓
Storage
    ├→ Neo4j (graph)
    └→ Qdrant (vectors)
```

---

## Storage

### Neo4j Graph Schema
**Nodes:**
- `File` - Source files
- `Function` - Functions/methods
- `Class` - Classes
- `Module` - Python modules

**Relationships:**
- `CONTAINS` - File contains function/class
- `CALLS` - Function calls another
- `IMPORTS` - Module imports another
- `INHERITS` - Class inheritance

### Qdrant Collections
- `yaver_memory` - Agent memory (Mem0)
- `code_embeddings` - Code semantic search
- Session-specific collections (optional)

### Configuration
**Location**: `~/.yaver/config.json`

**Structure:**
```json
{
  "ollama": {
    "base_url": "http://localhost:11434",
    "model_general": "llama3.1:8b",
    "model_embedding": "nomic-embed-text"
  },
  "vector_db": {
    "provider": "qdrant"
  },
  "qdrant": {
    "host": "localhost",
    "port": 6333,
    "collection": "yaver_memory"
  },
  "neo4j": {
    "uri": "bolt://localhost:7687",
    "user": "neo4j",
    "password": "password"
  }
}
```

---

## Design Decisions

### Why Qdrant over LEANN?
- **Stability**: Production-ready, well-maintained
- **Performance**: Faster similarity search
- **Simplicity**: No complex build dependencies
- **Compatibility**: Better integration with Mem0

### Why Neo4j for Code Graph?
- **Relationships**: Natural fit for code dependencies
- **Query Power**: Cypher for complex graph queries
- **Visualization**: Built-in graph visualization
- **Scalability**: Handles large codebases efficiently

### Why LangChain?
- **Tool Calling**: Built-in agent framework
- **Flexibility**: Easy to add new tools
- **Community**: Large ecosystem
- **Compatibility**: Works with Ollama

### Why Mem0?
- **Simplicity**: High-level memory API
- **Multi-backend**: Supports Qdrant/ChromaDB
- **User-centric**: User-specific memory management
- **Integration**: Works seamlessly with LangChain

---

## Extension Points

### Adding New Tools
```python
from tools.base import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "What my tool does"

    def run(self, input: str) -> str:
        # Implementation
        return result
```

### Adding New Forge Provider
```python
from tools.forge.provider import ForgeProvider

class MyForgeAdapter(ForgeProvider):
    def create_pr(self, title, body, head, base):
        # Implementation
        pass
```

### Custom Retrieval Strategy
```python
# In RAG Service
def retrieve_context(self, query, strategy="CUSTOM"):
    if strategy == "CUSTOM":
        # Custom retrieval logic
        pass
```

---

## Performance Considerations

### Embedding Generation
- **Batch processing**: 100 items at a time
- **Caching**: Embeddings cached in Qdrant
- **Incremental**: Only new/changed code re-embedded

### Neo4j Queries
- **Indexes**: On `name`, `type`, `session_id`
- **Query limits**: Max 100 results per query
- **Connection pooling**: Reuse connections

### Memory Usage
- **Startup**: ~150 MB
- **With services**: ~500 MB - 1.5 GB
- **Large repos**: Up to 2 GB

---

## Security

### Credentials
- Stored in `~/.yaver/config.json` (user-only permissions)
- Forge tokens in `~/.yaver/hosts.json`
- Environment variables supported (`.env`)

### Git Operations
- Token injection for HTTPS push
- SSH key support
- Credential manager for multi-host

---

## Future Enhancements

- [ ] Multi-user support
- [ ] Remote Qdrant/Neo4j
- [ ] Fine-tuned code models
- [ ] Web UI (Gradio)
- [ ] Plugin system
- [ ] Cloud deployment

---

**Version**: 1.2.0 | **Last Updated**: 2026-02-05

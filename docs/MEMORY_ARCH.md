# Multi-Repo Memory Architecture

This document describes the memory management system for handling multiple repositories with automatic context switching.

---

## Current State

### 1.1 Memory Infrastructure
| Component | Technology | Location | Purpose |
|-----------|-----------|----------|---------|
| **Mem0AI** | Qdrant + Ollama Embeddings | `devmind_cli/memory/manager.py` | General purpose LLM memory |
| **Interaction Logging** | SQLite | `logs/interaction_history.sqlite` | Full LLM call history |
| **Git Ops** | GitPython | `devmind_cli/git_ops.py` | Branch, Commit, PR operations |
| **Config System** | Pydantic | `devmind_cli/config.py` | System configuration |

**Analysis:** Memory is "User-based". No Repo ID stored.

### 1.2 Git Operations
```python
# Inside git_ops.py:
class GitOps:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        # ✅ Repo initialized BUT repo_id not stored in memory yet
    
    def create_pull_request(self, ...):
        # GitHub API resolves owner/repo BUT not written to db
```

**Analysis:** Git operations read `remote URL` but don't pass to memory system.

### 1.3 CLI Arguments
```bash
devmind solve --file buggy_script.py "Fix bugs"
devmind edit --file src/main.py --request "Add docstrings"
```

**Analysis:** CLI receives `--file` as file path only, no repo info.

### 1.4 Logging Structure
```
logs/
├── agent.log           # Agent activities
├── api.log             # API calls
├── backend.log         # Backend logs
├── interaction_history.sqlite  # ← USER-based memory
└── (no repo id here)
```

**Analysis:** SQLite has no repo-based separation. All repos' interactions in same file.

---

## Problem Assessment

### 2.1 Context Pollution Risk

```
09:00: Agent working on Django project saves to memory:
  - "In Django, database config is in settings.py"
  - "Migrations run after runserver"

14:00: Switch to Go project but agent can't read repo_id from Git
  - When querying memory, STILL suggests "settings.py" → HALLUCINATION
```

### 2.2 SQLite Schema Problem

```sql
CREATE TABLE IF NOT EXISTS interactions (
    id TEXT PRIMARY KEY,
    timestamp TEXT,
    model TEXT,
    inputs TEXT,       -- Which repo?
    outputs TEXT,      -- Result applied to which project?
    tokens_in INTEGER,
    tokens_out INTEGER,
    run_id TEXT        -- No repo reference
)
```

**Problem:** `run_id` field is UUID, carries no repo info.

### 2.3 MemoryManager State

```python
class MemoryManager:
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id  # Only user_id, no repo_id
        self.memory = Memory.from_config(config)
        # Qdrant collection name: "devmind_memory" (global/shared)
```

**Problem:** Qdrant collection is shared across all repos.

---

## Proposed Architecture

### 3.1 Design

```
┌─────────────────────────────────────────────────────┐
│             DEVMIND CLI COMMAND                     │
│         (From which directory is it running?)       │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  Read Git Remote URL  │ (git remote -v)
        │  Hash Repo ID        │ (github.com/user/repo)
        └──────────────┬───────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │ AUTO-DETECT: Repo ID Set             │
        │ Example: "repo_github_user_project"  │
        └──────────────┬───────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │ Memory Context Automatically Switch   │
        │ - Qdrant collection: repo-specific    │
        │ - SQLite: repo_id indexed             │
        │ - Agent Prompts: Repo facts injected  │
        └──────────────────────────────────────┘
```

### 3.2 Advantages

| Advantage | Explanation |
|-----------|-------------|
| **Automatic** | Changing folder auto-switches memory (no user action) |
| **Isolation** | Repo A info doesn't pollute Repo B |
| **Scalability** | Even with 50+ repos, each has own memory space |
| **Control** | User manages what's stored in repo context |

### 3.3 User vs Repo Memory Roles

```
┌────────────────────────────────────────────┐
│           DUAL MEMORY SYSTEM                │
├────────────────────────────────────────────┤
│                                            │
│ 📍 REPO-SPECIFIC (Qdrant per-repo)        │
│    • Project architecture                  │
│    • File conventions                      │
│    • Library preferences (Django vs FastAPI) │
│    • Bug fix history                       │
│    • Architecture decisions                │
│    Scope: /home/.../ProjectA               │
│                                            │
│ 👤 USER-GLOBAL (Qdrant global)             │
│    • Coding style preferences              │
│    • Language conventions                  │
│    • Favorite LLM model settings           │
│    • General best practices                │
│    Scope: All projects                     │
│                                            │
└────────────────────────────────────────────┘
```

---

## Storage Plan

### 4.1 SQLite Schema

```sql
-- New: interactions_v2 table (backward compatible)
CREATE TABLE interactions_v2 (
    id TEXT PRIMARY KEY,
    timestamp TEXT,
    model TEXT,
    inputs TEXT,
    outputs TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    
    -- ✨ NEW FIELDS:
    repo_id TEXT NOT NULL,           -- Hash of git remote
    repo_path TEXT,                  -- /home/user/project
    git_remote_url TEXT,             -- https://github.com/user/repo
    branch_name TEXT,                -- devmind/feature/fix-123
    
    -- Metadata
    agent_type TEXT,                 -- "coder", "reviewer", "planner"
    task_description TEXT,           -- High-level task
    
    FOREIGN KEY (repo_id) REFERENCES repo_contexts(repo_id)
);

-- New: metadata for each repo
CREATE TABLE repo_contexts (
    repo_id TEXT PRIMARY KEY,
    repo_path TEXT UNIQUE,
    git_remote_url TEXT,
    first_seen TIMESTAMP,
    last_accessed TIMESTAMP,
    metadata JSON                    -- Project-specific info
);

-- Indexes
CREATE INDEX idx_repo_id ON interactions_v2(repo_id);
CREATE INDEX idx_repo_timestamp ON interactions_v2(repo_id, timestamp);
```

### 4.2 Qdrant Collections

```python
# Today:
QDRANT_COLLECTION = "devmind_memory"  # Global

# New:
QDRANT_COLLECTION = "repo_{repo_id}_memory"
# Example: "repo_github_user_myproject_memory"

# Also Global (User) collections:
QDRANT_COLLECTION_USER = "user_preferences_memory"
QDRANT_COLLECTION_SHARED = "shared_patterns_memory"
```

---

## Implementation Roadmap

### **Phase 1: Foundation (1-2 days)**

#### 1.1 Repo ID Extraction Module
**File:** `devmind_cli/repo_manager.py`
```python
class RepositoryManager:
    def __init__(self, repo_path: str = "."):
        self.repo = Repo(repo_path)
        self.repo_id = self.extract_repo_id()
        self.repo_context = self.load_or_create_context()
    
    def extract_repo_id(self) -> str:
        # Create hash from git remote origin URL
        # Example: github.com/user/project → "repo_md5hash"
        
    def load_or_create_context(self) -> Dict:
        # Get/create repo info from SQLite
```

#### 1.2 SQLite Schema Migration
```bash
# Add 2 new tables to logs/interaction_history.sqlite:
# - interactions_v2
# - repo_contexts
```

#### 1.3 Git Ops Repo ID Integration
**File:** `devmind_cli/git_ops.py` (Update)
```python
class GitOps:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        self.repo_mgr = RepositoryManager(repo_path)  # ← NEW
        self.repo_id = self.repo_mgr.repo_id          # ← NEW
```

---

### **Phase 2: Memory System Integration (2-3 days)**

#### 2.1 Memory Manager Update
**File:** `devmind_cli/memory/manager.py` (Refactor)
```python
class MemoryManager:
    def __init__(self, user_id: str = "default_user", repo_id: str = None):
        self.user_id = user_id
        self.repo_id = repo_id or self.auto_detect_repo()  # ← NEW
        
        # Repo-specific collection
        self.repo_collection = f"repo_{repo_id}_memory"
        # User-specific collection
        self.user_collection = f"user_{user_id}_preferences"
        
    def add_memory(self, text: str, scope: str = "repo"):
        # scope: "repo" | "user"
        
    def search_memory(self, query: str, scope: str = "repo"):
        # Search from repo-appropriate memory
```

#### 2.2 InteractionDB Update
**File:** `devmind_cli/interaction_logger.py` (Update)
```python
class InteractionDB:
    def log_interaction(self, 
                       run_id: str, 
                       model: str, 
                       inputs: str, 
                       outputs: str,
                       repo_id: str,          # ← NEW
                       agent_type: str = "",  # ← NEW
                       task_desc: str = ""):  # ← NEW
        # Write to interactions_v2
```

#### 2.3 CLI Context Manager
**File:** `devmind_cli/cli_context.py` (NEW)
```python
class DevMindContext:
    """Global context holder for current CLI invocation"""
    _current_repo_id: str = None
    _current_memory: MemoryManager = None
    
    @classmethod
    def initialize(cls, repo_path: str = "."):
        # Auto-detect repo_id and set MemoryManager
```

---

### **Phase 3: CLI Integration (1 day)**

#### 3.1 Context Initialization in cli.py
**File:** `devmind_cli/cli.py` (Update)
```python
def main():
    setup_logger()
    
    # ✨ NEW: Set repo context at start of every command
    DevMindContext.initialize(repo_path=".")
    
    parser = argparse.ArgumentParser(...)
    # ... rest of CLI setup
```

#### 3.2 `handle_solve` Update
**File:** `devmind_cli/cli_solve.py` (Update)
```python
def handle_solve(args):
    # Repo ID auto-read
    repo_id = DevMindContext._current_repo_id
    mem_manager = DevMindContext._current_memory
    
    # Inject repo context during planning phase
    feedback_for_planner += f"\nRepo Context: {mem_manager.search_memory('architecture')}"
```

#### 3.3 Logging Callback Update
**File:** `devmind_cli/interaction_logger.py` (Update)
```python
class SQLLoggingCallback(BaseCallbackHandler):
    def __init__(self, model_name: str = "unknown", repo_id: str = None):
        self.db = InteractionDB()
        self.repo_id = repo_id or DevMindContext._current_repo_id
        self.agent_type = "unknown"
    
    def on_llm_end(self, ...):
        self.db.log_interaction(
            run_id=str(run_id),
            model=run_data["model"],
            inputs=run_data["inputs"],
            outputs=output_text,
            repo_id=self.repo_id,          # ← NEW
            agent_type=self.agent_type,    # ← NEW
        )
```

---

## Data Security & Maintenance

### 6.1 SQLite Maintenance
```python
# In cleanup: remove old repos
def cleanup_old_repos(days: int = 30):
    # Archive memory of repos not accessed in 30 days
```

### 6.2 Qdrant Collection Management
```python
# Clean up old collections
def cleanup_qdrant_collections():
    # Delete "repo_{old_repo_id}_*" collections
```

---

## Backward Compatibility

- **Existing `interactions` table:** Remains active (legacy logs)
- **New `interactions_v2` table:** Receives new data
- **Migration script:** Can port old data if needed
- **Environment variable:** Toggle with `USE_REPO_MEMORY=true/false`

---

## Configuration (.env)

```dotenv
# Existing (Unchanged)
OLLAMA_BASE_URL=http://localhost:11434
QDRANT_HOST=localhost
QDRANT_PORT=6333

# NEW
ENABLE_REPO_MEMORY=True                 # Multi-repo memory ON/OFF
MEMORY_BACKEND=qdrant_repo              # "qdrant_repo" | "qdrant_user"
REPO_MEMORY_RETENTION_DAYS=90           # How long to keep repo memory?
AUTO_DETECT_REPO=True                   # Auto-read repo_id from folder
```

---

## Expected Outcomes

### ✅ Success Criteria

1. **Repo Switching Seamless:** `cd ProjectA && devmind solve` → ProjectA memories
2. **No Context Pollution:** ProjectA decisions don't affect ProjectB
3. **Backward Compat:** Old `interactions` table continues working
4. **Performance:** Repo-specific queries <500ms

### 📊 Metrics

- Query latency (repo-specific)
- Collection size per repo
- Memory growth rate
- Cache hit ratio

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **SQLite file corruption** | High | Regular VACUUM + WAL mode |
| **Qdrant collection explosion** | Medium | Auto-cleanup + naming convention |
| **Memory leaks in MemoryManager** | High | Singleton pattern + explicit cleanup |
| **Wrong repo_id detection** | High | Unit tests + git remote validation |

---

## Conclusion

**Recommendation: Implement repo-centric architecture**

**Why:**
1. ✅ Automatic (No user interaction)
2. ✅ Safe (Context isolation)
3. ✅ Scalable (Supports 100+ repos)
4. ✅ Backward compatible (Old logs preserved)

**Implementation Time:** ~4-5 days (phased approach)

---

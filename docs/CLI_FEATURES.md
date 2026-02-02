# DevMind CLI Features & Architecture

DevMind CLI (`devmind_cli`) has been evolved into a powerful AI-assisted development tool, inspired by GitHub Copilot CLI, Claude CLI, and Mistral tools. It leverages the `devmind_cli` python package and connects to LLMs (via Ollama) to provide intelligent assistance directly in your terminal.

## 🌟 Key Features

### 1. Interactive Chat (`chat`)
Starts a REPL (Read-Eval-Print Loop) session with the AI agent.
- **Context Awareness**: Use `@filename` to inject file contents into the chat context automatically.
- **Stateful**: Remembers conversation history within the session.
- **Rich UI**: Markdown rendering and colorful output.

**Usage:**
```bash
devmind chat
# In session: "Refactor the authentication logic in @auth.py"
```

### 2. Command Suggestion (`suggest`)
Translates natural language requests into ready-to-execute shell commands.
- **Safety**: Never runs commands without confirmation.
- **Target OS**: Optimized for Linux/Unix environments.

**Usage:**
```bash
devmind suggest "find all jpg files larger than 10MB and delete them"
```

### 3. Smart Git Commit (`commit`)
Generates professional commit messages based on staged changes.
- **Conventional Commits**: Adheres to standard formats (`feat:`, `fix:`, etc.).
- **Diff Analysis**: Reads `git diff --cached` to understand the actual changes.
- **Context Injection**: Accepts optional user context (`-c`) to guide the message generation.

**Usage:**
```bash
git add .
devmind commit
# Or with context:
devmind commit -c "Fixed the login bug reported in issue #42"
```

### 4. Command Explanation (`explain`)
Breaks down complex shell commands into plain English.
- **Detailed Analysis**: Explains flags, arguments, and potential risks.
- **Educational**: Great for learning what a pasted command actually does.

**Usage:**
```bash
devmind explain "tar -czf backup.tar.gz /var/www/html"
```

### 5. Auto-Fix (`fix`)
Analyzes errors and suggests solutions using two powerful modes.
- **Wrapper Mode**: Runs a command and captures its output/errors.
- **Pipe Mode**: Reads error logs from Stdin (Unix piping).

**Usage:**
```bash
# Wrapper
devmind fix -- python3 broken_script.py

# Pipe
make build 2>&1 | devmind fix
```

### 6. AI File Editor (`edit`)
Transforms DevMind into an active coding agent capable of modifying files.
- **Direct Editing**: You describe the change, AI implements it.
- **Diff Preview**: Shows a colorful Unified Diff of the proposed changes before saving.
- **Safety First**: Updates are never applied without your explicit confirmation.

**Usage:**
```bash
devmind edit "Add a 'remember me' option to the login function" -f auth.py
devmind edit "Refactor this class to use Pydantic models" --file config.py
```

### 7. Autonomous Solver (`solve`)
The implementation of the **Jules** concept. It handles the entire lifecycle of a bug fix or feature request with a full Agentic Workflow.
- **Phase 1: Planning**: Agent analyzes the task and creates an implementation plan.
- **Phase 2: Execution**: Agent writes or modifies the code.
- **Phase 3: Review**: A separate Reviewer Agent audits the code. If issues are found, it auto-fixes them.
- **Phase 4: Integraiton**: Commit, Push, and PR creation.

**Usage:**
```bash
# Full workflow
devmind solve "Fix the recursion error in the parser" -f parser.py
```

---

## 🏗️ Architecture & Prompt Engineering

The CLI uses a **Role-Based Prompting** mechanism implemented in Python using LangChain and Rich.

### Core Components used in `devmind_cli`:
- **Rich**: Handles the TUI (Text User Interface), including spinners, markdown rendering, and interactive prompts.
- **LangChain**: Manages the LLM interaction found in `agent_base.py`.
- **Subprocess**: Safely executes git operations and shell commands.

### Prompt Strategies

#### Suggest Strategy
*   **Goal**: Turn text into executable bash code.
*   **System Role**: "Command-line expert. Output ONLY shell command."
*   **Guardrails**: Confirms execution with the user to prevent accidental damage (e.g., `rm -rf`).

#### Commit Strategy
*   **Goal**: Summarize code changes.
*   **Input**: First 10,000 chars of `git diff --cached`.
*   **Constraint**: Output must follow `<type>: <subject>` format.

#### Fix Strategy
*   **Goal**: Debugging and Root Cause Analysis.
*   **Input**: `stderr` and `stdout` captured from the failed process.
*   **Prompt Structure**:
    1.  Identify Root Cause.
    2.  Propose Specific Fix.
    3.  Keep it concise.

#### Editor Strategy
*   **Goal**: Precise Code Modification.
*   **Input**: Full file content + User Instruction.
*   **Method**: Providing the LLM with the file and asking it to rewrite it completely with changes applied.
*   **Output**: Unified Diff visualization for user review.

#### Chat Strategy
*   **Goal**: General purpose assistance.
*   **Smart Context**: A regex parser scans user input for `@filepath`. If found, it reads the file and pre-appends it to the LLM context hidden from the user view, allowing the model to "see" the code you are talking about.

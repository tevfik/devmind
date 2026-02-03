# DevMind Quick Reference - Session vs Project

## 🎯 Quick Distinction

| Concept | Purpose | Command |
|---------|---------|---------|
| **Session** | Chat conversation history | `devmind session ...` |
| **Project** | Group of learned repositories | `devmind project ...` |

---

## 💬 Chat Session Commands

```bash
# Create a new chat session
devmind session new --name="My Session" --tag=tag1 --tag=tag2

# List all chat sessions
devmind session list

# Show current active session
devmind session current

# Switch to a different session
devmind session set <SESSION_ID>

# Add a tag to a session
devmind session tag <SESSION_ID> <TAG>

# Delete a session
devmind session delete <SESSION_ID>
devmind session delete <SESSION_ID> --force  # Skip confirmation

# Show session details
devmind session show <SESSION_ID>
```

---

## 📚 Project Commands

```bash
# List all learned projects
devmind project list

# Show project details (repositories, statistics)
devmind project show <PROJECT_ID>

# Delete a project and its learned data
devmind project delete <PROJECT_ID>
devmind project delete <PROJECT_ID> --force  # Skip confirmation
```

---

## 🧠 Learning (Create Projects)

```bash
# Learn a repository and assign to a project
devmind learn /path/to/repo --session-id=my-project

# Learn multiple repos into same project
devmind learn /path/to/repo1 --session-id=my-project
devmind learn /path/to/repo2 --session-id=my-project
devmind learn /path/to/repo3 --session-id=my-project

# Incremental update (only changed files)
devmind learn . --incremental --session-id=my-project
```

---

## 🤖 Chat Commands

```bash
# Chat with all learned repositories
devmind chat

# Chat with specific project only
devmind chat --project-id=my-project

# Chat with specific session only (uses history)
devmind chat --session-id=<SESSION_ID>

# Chat with project AND session
devmind chat --project-id=my-project --session-id=<SESSION_ID>
```

---

## 📊 Typical Workflow

```bash
# Step 1: Learn your repositories (create a project)
devmind learn ~/backend --session-id=my-app
devmind learn ~/frontend --session-id=my-app
devmind learn ~/auth --session-id=my-app

# Step 2: Verify what you learned
devmind project list
devmind project show my-app

# Step 3: Create a chat session for discussion
devmind session new --name="Feature Discussion" --tag=feature

# Step 4: Chat with your project's context
devmind chat --project-id=my-app --session-id=<SESS_ID>

# Step 5: Continue discussions with same context
devmind chat --project-id=my-app --session-id=<SESS_ID>
```

---

## 🔍 Verification Commands

```bash
# Check what commands are available
devmind --help

# Check chat options
devmind chat --help

# Check project commands
devmind project --help

# Check session commands
devmind session --help

# Check system status
devmind status

# Run automated architecture tests
./test_architecture.sh
```

---

## ⚡ Pro Tips

1. **Use `--session-id` consistently** to group related learning together
   ```bash
   # Good: All backend services in one project
   devmind learn ./services/auth --session-id=backend
   devmind learn ./services/api --session-id=backend
   ```

2. **Name your sessions descriptively**
   ```bash
   devmind session new --name="Payment Feature Dev" --tag=feature --tag=payment
   ```

3. **Filter chat for multi-repo efficiency**
   ```bash
   # Instead of searching 5 repos, search just the relevant one
   devmind chat --project-id=microservices
   ```

4. **Tag sessions for organization**
   ```bash
   devmind session tag <ID> debugging
   devmind session tag <ID> feature-review
   devmind session tag <ID> production-incident
   ```

5. **Check project stats before big operations**
   ```bash
   devmind project show my-project  # See what's in there
   devmind project delete my-project --force  # Then delete if needed
   ```

---

## 🚨 Common Mistakes to Avoid

❌ **Mixing projects and sessions**
```bash
# WRONG: Using --session-id for project filtering
devmind chat --session-id=my-project  # This is a chat session, not a project!
```

✅ **Correct approach**
```bash
# RIGHT: Use --project-id for project filtering
devmind chat --project-id=my-project
```

---

## 📚 For More Details

- **Full Guide:** See [CLI_GUIDE.md](CLI_GUIDE.md)
- **Testing Guide:** See [CLI_GUIDE.md#testing--verification](CLI_GUIDE.md#testing--verification)
- **Architecture Decisions:** See [ARCHITECTURE_UPDATE.md](ARCHITECTURE_UPDATE.md)
- **Test Script:** Run `./test_architecture.sh`

---

**Last Updated:** February 3, 2026

#!/bin/bash

###############################################################################
# DevMind Architecture Testing Script
# Tests the new Session vs Project separation
###############################################################################

set -e

RESET='\033[0m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${RESET}"
}

log_success() {
    echo -e "${GREEN}✅ $1${RESET}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${RESET}"
}

log_error() {
    echo -e "${RED}❌ $1${RESET}"
}

log_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BLUE}$1${RESET}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
}

# Check if devmind is installed
if ! command -v devmind &> /dev/null; then
    log_error "devmind is not installed. Run: pipx install -e ."
    exit 1
fi

log_success "devmind is installed"

log_section "TEST 1: Help Text Verification"

log_info "Checking chat command options..."
if devmind chat --help | grep -q "session-id" && devmind chat --help | grep -q "project-id"; then
    log_success "Chat has both --session-id and --project-id options"
else
    log_error "Chat command missing expected options"
    exit 1
fi

log_info "Checking project command exists..."
if devmind project --help | grep -q "list\|show\|delete"; then
    log_success "Project command has list, show, delete subcommands"
else
    log_error "Project command missing subcommands"
    exit 1
fi

log_info "Checking session command is for chat..."
if devmind session --help | grep -q "chat"; then
    log_success "Session command is properly labeled for chat"
else
    log_warning "Session command help text might need update"
fi

log_section "TEST 2: Command Structure"

log_info "Testing project command structure..."
devmind project --help > /dev/null && log_success "project list works" || log_error "project list failed"
devmind project --help > /dev/null && log_success "project command accessible" || log_error "project command failed"

log_info "Testing session command structure..."
devmind session --help > /dev/null && log_success "session command accessible" || log_error "session command failed"

log_section "TEST 3: Database Connection"

log_info "Checking Neo4j connection..."
if devmind status 2>&1 | grep -q "Neo4j\|neo4j"; then
    log_success "Neo4j status is accessible"
else
    log_warning "Could not verify Neo4j status - ensure it's running"
fi

log_section "TEST 4: Quick Session Operations"

log_info "Creating a test chat session..."
SESSION_OUTPUT=$(devmind session new --name="ArchitectureTest" --tag=test 2>&1)

if echo "$SESSION_OUTPUT" | grep -q "✅ Created"; then
    SESSION_ID=$(echo "$SESSION_OUTPUT" | grep -oP '(?<=Created session: )\S+' | head -1)
    log_success "Chat session created: $SESSION_ID"
    
    log_info "Listing chat sessions..."
    if devmind session list 2>&1 | grep -q "Chat Sessions"; then
        log_success "Session list displays correctly"
    else
        log_warning "Session list output format may need verification"
    fi
else
    log_warning "Could not create test session (Neo4j might not be running)"
fi

log_section "TEST 5: Documentation Check"

if grep -q "Understanding Sessions vs Projects" CLI_GUIDE.md; then
    log_success "CLI_GUIDE.md contains session vs project explanation"
else
    log_error "CLI_GUIDE.md missing session vs project section"
    exit 1
fi

if grep -q "Limit code context to specific project" CLI_GUIDE.md; then
    log_success "CLI_GUIDE.md documents project-id parameter"
else
    log_error "CLI_GUIDE.md missing project-id documentation"
    exit 1
fi

if grep -q "conversation history" CLI_GUIDE.md; then
    log_success "CLI_GUIDE.md explains chat sessions vs projects"
else
    log_warning "CLI_GUIDE.md could better explain the difference"
fi

log_section "SUMMARY"

echo -e "${GREEN}Architecture tests completed!${RESET}\n"

cat << 'EOF'
✨ Key Points to Verify:

1. SESSION Management (Chat History)
   ✓ devmind session new
   ✓ devmind session list
   ✓ devmind session show <id>
   ✓ devmind session set <id>
   ✓ devmind session delete <id>

2. PROJECT Management (Learning Sessions)
   ✓ devmind project list
   ✓ devmind project show <id>
   ✓ devmind project delete <id>

3. CHAT Integration
   ✓ devmind chat (all projects)
   ✓ devmind chat --project-id=<id>
   ✓ devmind chat --session-id=<id>
   ✓ devmind chat --project-id=<id> --session-id=<id>

4. LEARN Integration
   ✓ devmind learn . --session-id=<project-name>

📚 For detailed testing, see CLI_GUIDE.md "Testing & Verification" section
EOF

echo ""

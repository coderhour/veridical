# How Veridical + OpenSpec + Jules Work Together

A comprehensive guide to understanding the autonomous quality assurance ecosystem.

---

## Table of Contents

1. [The Big Picture](#the-big-picture)
2. [The Three Pillars](#the-three-pillars)
3. [How They Work Together](#how-they-work-together)
4. [The Complete Workflow](#the-complete-workflow)
5. [Key Concepts](#key-concepts)
6. [Real-World Example](#real-world-example)
7. [Why This Matters](#why-this-matters)

---

## The Big Picture

**Veridical** is a local supervisory control system that bridges the gap between **OpenSpec** (spec-driven development) and **Google Jules** (asynchronous cloud-based AI coding agent). Together, they form an autonomous quality assurance loop that transforms probabilistic AI agents into deterministic engineering systems.

```
┌─────────────────────────────────────────────────────────────┐
│                    DEVELOPER (You)                          │
│                                                             │
│  "Fix the login validation bug"                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  PROPOSAL GENERATION  │
         │  (AI-assisted or      │
         │   manual creation)    │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  HUMAN APPROVAL ✓     │
         │  (Review & validate)  │
         └───────────┬───────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    VERIDICAL                                │
│              (Local Supervisor)                             │
│                                                             │
│  • Reads OpenSpec proposals & tasks                         │
│  • Dispatches work to Jules                                 │
│  • Monitors remote progress                                 │
│  • Verifies quality locally                                 │
│  • Iterates until perfect                                   │
└──────────┬──────────────────────────────────┬───────────────┘
           │                                  │
           ▼                                  ▼
┌──────────────────────┐         ┌──────────────────────────┐
│     OPENSPEC         │         │      GOOGLE JULES        │
│  (Spec Framework)    │         │   (Cloud AI Agent)       │
│                      │         │                          │
│  • proposal.md       │         │  • Spins up cloud VM     │
│  • tasks.md          │         │  • Clones repository     │
│  • spec.md deltas    │         │  • Writes code           │
│  • Source of truth   │         │  • Runs tests            │
└──────────────────────┘         │  • Creates patches       │
                                 └──────────────────────────┘

Key: Proposals can be AI-generated OR manually created,
     but ALWAYS require human approval before implementation.
```

---

## The Three Pillars

### 1. **OpenSpec** - The Contract Layer

**What it is:** A lightweight, file-based protocol for spec-driven development.

**What it does:**
- Defines **what** needs to be built (proposals)
- Breaks down **how** to build it (tasks)
- Specifies **requirements** (spec deltas)
- Maintains a **source of truth** (specs/)

**Key files:**
```
openspec/
├── project.md              # Project context and conventions
├── AGENTS.md               # Instructions for AI agents
├── specs/                  # Current truth (what IS built)
│   └── [capability]/
│       └── spec.md
└── changes/                # Proposals (what SHOULD change)
    └── [change-id]/
        ├── proposal.md     # Why and what
        ├── tasks.md        # Implementation checklist
        └── specs/          # Spec deltas (ADDED/MODIFIED/REMOVED)
            └── [capability]/
                └── spec.md
```

**Why it matters:** Prevents "context drift" where AI agents lose track of the original intent. Every change starts with an approved proposal, ensuring alignment before a single line of code is written.

---

### 2. **Google Jules** - The Worker

**What it is:** An asynchronous, cloud-based AI coding agent.

**What it does:**
- Spins up isolated VMs in Google Cloud
- Clones your repository
- Analyzes codebase and AGENTS.md
- Generates implementation plans
- Writes code, runs tests, creates PRs
- Operates independently of your local machine

**Architecture:**
```
Session Creation → VM Provisioning → Context Analysis → 
Plan Generation → Execution → Artifact Delivery (PR/Patch)
```

**Why it matters:** Provides scalable, isolated execution environments. Unlike local agents, Jules can work on multiple tasks in parallel without blocking your development workflow.

---

### 3. **Veridical** - The Supervisor

**What it is:** A local control system that orchestrates the entire quality assurance loop.

**What it does:**
- **Reads** OpenSpec proposals and tasks
- **Dispatches** work to Jules with precise prompts
- **Monitors** Jules sessions via API polling
- **Synchronizes** patches from cloud to local git branches
- **Verifies** code quality using local test suites
- **Iterates** until all quality gates pass

**Core Components:**

1. **Supervisor (Kernel)** - Manages the control loop and state machine
2. **Worker (Protocol)** - Pluggable backend interface (`dispatch`, `poll`, `sync`)
   - **JulesWorker** - Default implementation wrapping Dispatcher, Poller, and Synchronizer for Google Jules
3. **Verifier** - Runs local tests, linters, and quality gates
4. **WorkerRegistry** - Maps backend names to Worker implementations

The **Worker protocol** decouples the Supervisor from any specific AI backend. The `JulesWorker` composes the existing Dispatcher (prompt building, session creation), Poller (status monitoring with backoff), and Synchronizer (patch application to git branches) into a single cohesive unit.

**Why it matters:** Transforms Jules from a "fire-and-forget" agent into a supervised, iterative system. Ensures code meets YOUR quality standards, not just Jules' self-assessment. The Worker abstraction also enables alternative backends (local scripts, other AI services) without modifying the core loop.

---

## How They Work Together

### The Control Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTROL LOOP                             │
└─────────────────────────────────────────────────────────────┘

1. IDLE
   └─> Veridical reads OpenSpec proposal & tasks
   
2. DISPATCHING
   └─> Veridical sends task to Jules via API
       • Includes OpenSpec context
       • Sets requirePlanApproval=false (autonomous mode)
       • Injects AGENTS.md constraints
   
3. POLLING
   └─> Veridical monitors Jules session
       • Polls every 30 seconds
       • Auto-approves plans if needed
       • Waits for COMPLETED or FAILED
   
4. SYNCING
   └─> Veridical applies Jules' patch locally
       • Creates isolation branch (veridical/iter-N)
       • Applies patch from Jules
       • Protects main branch
   
5. VERIFYING
   └─> Veridical runs local quality gates
       • pytest (tests)
       • ruff (linting)
       • mypy (type checking)
       
   ┌─> PASS? → Merge to main → DONE ✅
   │
   └─> FAIL? → Extract errors → Back to DISPATCHING
       (with error context for next iteration)
```

### The Feedback Loop

**What makes this powerful:** Veridical doesn't trust Jules' self-reported success. It verifies EVERYTHING locally.

```
Jules says: "Tests passed! ✓"
Veridical says: "Let me verify that locally..."

[Runs local test suite]

Veridical: "Actually, you missed an edge case. Try again."
          "Here's the exact error: [stack trace]"

[Next iteration with error context]

Jules: "Fixed! Here's attempt #2"
Veridical: "Perfect! All gates passed. Merging."
```

---

## Who Creates OpenSpec Proposals?

### **TL;DR:** AI-assisted, Human-approved

OpenSpec proposals can be generated by:
1. **AI assistants** (Claude, Cursor, Jules) - Recommended for speed
2. **Humans** - Manual creation for complex scenarios
3. **Hybrid** - AI drafts, human refines

**Critical rule:** Regardless of who generates the proposal, **a human must review and approve it** before Veridical begins implementation.

### Option 1: AI-Assisted Generation (Recommended)

**Using the OpenSpec CLI:**
```bash
# The AI (Claude/Cursor) generates the proposal structure
openspec proposal "Add rate limiting to API"

# This creates:
# openspec/changes/add-rate-limiting/
#   ├── proposal.md    (AI-generated)
#   ├── tasks.md       (AI-generated)
#   └── specs/         (AI-generated)
```

**How it works:**
1. You provide a natural language description
2. Your AI assistant (configured in OpenSpec) drafts the proposal
3. You review and edit the generated files
4. You validate: `openspec validate add-rate-limiting --strict`
5. You approve (implicitly by proceeding to implementation)

**Supported AI assistants:**
- Claude Code (via `.clinerules`)
- Cursor (via `.cursorrules`)
- Google Jules (via AGENTS.md)
- Any AI that can read OpenSpec instructions

### Option 2: Manual Creation

**For full control:**
```bash
# Create directory structure manually
mkdir -p openspec/changes/add-rate-limiting/specs/api

# Write proposal.md manually
vim openspec/changes/add-rate-limiting/proposal.md

# Write tasks.md manually
vim openspec/changes/add-rate-limiting/tasks.md

# Write spec deltas manually
vim openspec/changes/add-rate-limiting/specs/api/spec.md

# Validate
openspec validate add-rate-limiting --strict
```

### Option 3: Hybrid Approach (Best Practice)

**Combine AI speed with human expertise:**
```bash
# 1. AI generates initial draft
openspec proposal "Add rate limiting to API"

# 2. Human reviews and refines
# - Adds missing edge cases to proposal.md
# - Breaks down tasks.md into smaller steps
# - Adds specific scenarios to spec.md

# 3. Validate
openspec validate add-rate-limiting --strict

# 4. Proceed with implementation
veridical run "Implement rate limiting per approved proposal"
```

### The Approval Gate

**Why human approval matters:**
- Prevents AI from misunderstanding requirements
- Ensures alignment with business goals
- Catches security or architectural concerns early
- Establishes clear "definition of done"

**The workflow:**
```
AI generates proposal
    ↓
Human reviews
    ↓
┌─────────────┐
│ Approved?   │
└─────────────┘
    ↓           ↓
   YES         NO
    ↓           ↓
Veridical    Human edits
implements   proposal
             ↓
          (loop back)
```

---

## The Complete Workflow

### Phase 1: Planning (OpenSpec)

**Step 1: Generate or create a proposal**

Choose your approach (AI-assisted recommended):

```bash
# AI generates proposal structure
openspec proposal "Add rate limiting to API"

# Creates:
# openspec/changes/add-rate-limiting/
#   ├── proposal.md
#   ├── tasks.md
#   └── specs/api/spec.md
```

**proposal.md** - The "Why"
```markdown
# Change: Add Rate Limiting to API

## Why
Prevent abuse and ensure fair resource allocation.

## What Changes
- Add rate limiting middleware
- Track requests per user
- Return 429 status when limit exceeded

## Impact
- Affected specs: api
- Affected code: src/middleware/
```

**tasks.md** - The "How"
```markdown
## 1. Implementation
- [ ] 1.1 Create rate limiter middleware
- [ ] 1.2 Add Redis client for tracking
- [ ] 1.3 Integrate into API routes
- [ ] 1.4 Write unit tests
- [ ] 1.5 Update API documentation
```

**specs/api/spec.md** - The "What" (Requirements)
```markdown
## ADDED Requirements

### Requirement: Rate Limiting
The API SHALL limit requests to 100 per minute per user.

#### Scenario: Within limit
- **WHEN** user makes 50 requests in 1 minute
- **THEN** all requests succeed with 200 status

#### Scenario: Exceeds limit
- **WHEN** user makes 101 requests in 1 minute
- **THEN** 101st request returns 429 Too Many Requests
```

**Human reviews and approves** ✅

---

### Phase 2: Implementation (Veridical + Jules)

**Developer runs:**
```bash
veridical run "Implement rate limiting per approved proposal"
```

**What happens:**

1. **Veridical reads** `openspec/changes/add-rate-limiting/`
   - Understands the proposal
   - Knows the tasks
   - Sees the requirements

2. **Veridical dispatches to Jules:**
   ```json
   {
     "prompt": "You are implementing rate limiting. Read openspec/changes/add-rate-limiting/ for full context. Execute tasks.md sequentially. Mark each task [x] when complete.",
     "sourceContext": {
       "source": "sources/github/user/repo",
       "startingBranch": "main"
     },
     "requirePlanApproval": false
   }
   ```

3. **Jules (in cloud VM):**
   - Clones repository
   - Reads AGENTS.md (knows to follow OpenSpec)
   - Reads proposal.md and tasks.md
   - Implements task 1.1: Creates middleware
   - Runs tests
   - Marks task [x] in tasks.md
   - Continues through all tasks
   - Creates patch

4. **Veridical polls Jules:**
   ```
   [30s] Status: RUNNING
   [60s] Status: RUNNING
   [90s] Status: COMPLETED
   ```

5. **Veridical syncs patch:**
   ```bash
   git checkout -b veridical/iter-1
   git apply jules-patch.diff
   ```

6. **Veridical verifies locally:**
   ```bash
   pytest                    # ✅ All tests pass
   ruff check src/           # ❌ Line too long in middleware.py
   mypy src/                 # ✅ No type errors
   ```

7. **Veridical detects failure** (ruff failed)
   - Extracts error: "Line 42 exceeds 100 characters"
   - Resets to main branch
   - Starts iteration #2 with error context

8. **Iteration #2:**
   - Veridical sends Jules the error
   - Jules fixes the line length issue
   - Veridical verifies again
   - **All gates pass!** ✅

9. **Veridical merges:**
   ```bash
   git checkout main
   git merge veridical/iter-2
   git branch -d veridical/iter-2
   ```

**Result:** High-quality, tested, linted code that meets all requirements.

---

### Phase 3: Archival (OpenSpec)

**After deployment:**

```bash
openspec archive add-rate-limiting
```

**What happens:**
1. Spec deltas merged into `openspec/specs/api/spec.md`
2. Change folder moved to `openspec/changes/archive/2026-01-03-add-rate-limiting/`
3. Source of truth updated
4. History preserved

**Now:**
- `openspec/specs/` reflects the current system
- Archive contains the decision history
- Future agents know rate limiting exists
- Future developers understand why it was added

---

## Key Concepts

### 1. **Asynchronous Loop Management**

**Challenge:** Jules takes 5-10 minutes per iteration (VM provisioning + execution).

**Solution:** Veridical uses intelligent polling with backoff, not blocking waits.

```python
# Simplified polling logic
while status not in ["COMPLETED", "FAILED"]:
    time.sleep(30)  # Poll every 30 seconds
    status = jules_api.get_status(session_id)
```

### 2. **State Synchronization**

**Challenge:** Jules works on a clone in the cloud. Your local repo might change.

**Solution:** Veridical creates isolation branches for each iteration.

```
main (protected)
  └─> veridical/iter-1 (test Jules' patch)
      ├─> PASS → merge to main
      └─> FAIL → delete, try again
```

### 3. **Local Truth Verification**

**Challenge:** Can't trust Jules' self-assessment.

**Solution:** Veridical runs YOUR local toolchain.

```yaml
# .veridical.yaml
verifier:
  quality_gates:
    - name: pytest
      command: pytest
      required: true
    - name: ruff
      command: ruff check src/
      required: true
    - name: mypy
      command: mypy src/
      required: true
```

### 4. **Prompt Precision (The "Sandwich" Strategy)**

**Challenge:** Vague prompts lead to poor code.

**Solution:** Veridical wraps user intent in quality constraints.

```
┌─────────────────────────────────────────┐
│ TOP LAYER (Role Definition)            │
│ "You are a Senior Engineer obsessed    │
│  with SOLID principles and TDD."       │
├─────────────────────────────────────────┤
│ FILLING (User Intent)                   │
│ "Add rate limiting to API"             │
├─────────────────────────────────────────┤
│ BOTTOM LAYER (Constraints)              │
│ "Read openspec/changes/add-rate-       │
│  limiting/ for full context. All new   │
│  code must have 100% test coverage."   │
└─────────────────────────────────────────┘
```

### 5. **Circuit Breaker Pattern**

**Challenge:** Agents can get stuck in infinite loops.

**Solution:** Veridical monitors for stagnation.

```python
# Simplified circuit breaker
if iteration >= max_iterations:
    print("FAILURE: Max iterations reached")
    return False

if same_diff_for_3_iterations:
    print("STAGNATION: Agent is stuck")
    return False

if consecutive_failures >= 3:
    print("CIRCUIT BREAKER: Too many failures")
    return False
```

### 6. **Dynamic AGENTS.md Injection**

**Challenge:** Generic instructions don't address specific failures.

**Solution:** Veridical updates AGENTS.md between iterations.

```markdown
# AGENTS.md (Iteration 1)
Standard instructions...

# AGENTS.md (Iteration 2 - after linter failure)
## EPHEMERAL CONSTRAINT
The previous build failed due to line length violations.
ALL code MUST comply with 100-character line limit.
Run `ruff check` before submitting.
```

---

## Real-World Example

### Scenario: "Fix the login validation bug"

**Step 1: Developer runs Veridical**
```bash
veridical run "Fix the login validation bug where empty passwords are accepted"
```

**Step 2: Veridical checks for OpenSpec proposal**
```
✓ Found: openspec/changes/fix-login-validation/
✓ Proposal approved
✓ Tasks defined
```

**Step 3: Veridical dispatches to Jules**
```
Creating Jules session...
Session ID: sess_abc123
Status: PENDING
```

**Step 4: Jules works (in cloud)**
```
[Cloud VM]
- Clones repository
- Reads AGENTS.md: "Follow OpenSpec protocol"
- Reads openspec/changes/fix-login-validation/tasks.md
- Task 1.1: Add password validation
  └─> Implements: if not password: raise ValidationError
- Task 1.2: Add unit test
  └─> Implements: test_empty_password_rejected()
- Runs tests: PASS ✓
- Creates patch
```

**Step 5: Veridical polls**
```
[30s] Status: RUNNING
[60s] Status: RUNNING
[90s] Status: COMPLETED
Retrieving patch...
```

**Step 6: Veridical syncs and verifies**
```bash
git checkout -b veridical/iter-1
git apply jules-patch.diff

Running quality gates...
✓ pytest: 45 passed
✓ ruff: No issues
✓ mypy: No type errors

All gates passed! ✅
```

**Step 7: Veridical merges**
```bash
git checkout main
git merge veridical/iter-1
git push origin main

SUCCESS: Bug fixed in 1 iteration
```

**Step 8: Archive the change**
```bash
openspec archive fix-login-validation

✓ Specs updated
✓ Change archived to openspec/changes/archive/2026-01-03-fix-login-validation/
```

**Total time:** ~10 minutes (mostly Jules execution)  
**Human effort:** 2 commands  
**Quality:** Guaranteed by local verification

---

## Local Loop Mode

In addition to supervising remote Jules sessions, Veridical can also supervise local agents or scripts. This is useful for:
- Testing your own AI agents
- Running local repair scripts
- Debugging the verification loop without cloud API calls

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL LOOP                               │
└─────────────────────────────────────────────────────────────┘

1. RUN WORKER
   └─> Veridical executes `worker_command`
       (e.g., "python agent.py")

2. VERIFY
   └─> Veridical runs quality gates

   ┌─> PASS? → DONE ✅
   │
   └─> FAIL? → Generate Feedback → Back to Step 1
       (sets VERIDICAL_ERROR_CONTEXT env var)
```

### Example: Testing a Local Agent

```bash
# veridical.yaml
local:
  worker_command: "python my_agent.py --fix"
  error_env_var: "AGENT_CONTEXT"

# Run it
veri local "Fix the bug"
```

1. Veridical runs `python my_agent.py --fix`.
2. Agent modifies code.
3. Veridical runs tests. Tests fail.
4. Veridical captures error output.
5. Veridical runs `python my_agent.py --fix` again, with `AGENT_CONTEXT` set to the error.
6. Agent reads error, fixes code.
7. Veridical runs tests. Pass.
8. Loop completes.

---

## Why This Matters

### The Problem with Traditional AI Coding

**Without this system:**
```
Developer: "Fix the bug"
AI: "Done! Here's the code."
Developer: *reviews 500 lines of diff*
Developer: "This breaks 3 tests and violates our style guide"
AI: "Sorry, let me fix that"
Developer: *reviews another 500 lines*
Developer: "Now it works but the code is unmaintainable"
[Repeat 5 times, waste 2 hours]
```

### With Veridical + OpenSpec + Jules

**With this system:**
```
Developer: "Fix the bug"
Veridical: "Found approved proposal. Dispatching to Jules..."
[10 minutes pass]
Veridical: "Iteration 1 failed (linter). Retrying with error context..."
[10 minutes pass]
Veridical: "All quality gates passed. Merged to main."
Developer: *reviews clean, tested, linted code*
Developer: "Perfect. Ship it."
```

### Key Benefits

1. **Deterministic Outcomes from Probabilistic Agents**
   - AI agents are probabilistic (might produce different results each time)
   - Quality gates are deterministic (pass/fail is objective)
   - Result: Reliable engineering outcomes

2. **Spec-Driven Development**
   - Intent is locked before implementation
   - No "context drift" during long tasks
   - Clear audit trail of decisions

3. **Autonomous Quality Assurance**
   - Iterates automatically until perfect
   - No human babysitting required
   - Enforces YOUR quality standards

4. **Scalable Parallelism**
   - Jules can work on multiple tasks simultaneously
   - Each in isolated cloud VMs
   - Veridical manages them all locally

5. **Cost-Effective Iteration**
   - Local verification is free and fast
   - Only pay for Jules when actually coding
   - Circuit breakers prevent runaway costs

6. **Knowledge Preservation**
   - OpenSpec archives preserve decision history
   - Future developers understand "why"
   - Future AI agents have context

---

## The Future Vision

**Today:**
```
Developer writes code → Tests → Lints → Reviews → Deploys
```

**With Veridical + OpenSpec + Jules:**
```
Developer writes proposal → Approves → Veridical orchestrates everything → Reviews final result → Deploys
```

**The shift:** From writing code to architecting systems. From syntax to strategy.

---

## Getting Started

### 1. Install Dependencies
```bash
# Install OpenSpec CLI
npm install -g @fission-ai/openspec@latest

# Install Veridical (when published)
uv add veridical
# or: pip install veridical
```

### 2. Initialize Your Project
```bash
# Initialize OpenSpec
openspec init

# Initialize Veridical
veridical config init
```

### 3. Set Up Environment
```bash
# Set Jules API key
export JULES_API_KEY="your-api-key"
```

### 4. Create Your First Proposal
```bash
# Let AI help you create a proposal
openspec proposal "Add user authentication"

# Review and approve the generated proposal
# Edit openspec/changes/add-user-auth/proposal.md as needed
```

### 5. Run Veridical
```bash
# Start the autonomous loop
veridical run "Implement user authentication per approved proposal"

# Check status
veridical status

# Verify quality gates locally
veridical verify
```

### 6. Archive When Done
```bash
# After deployment
openspec archive add-user-auth
```

---

## Learn More

- **Veridical README**: [README.md](./README.md)
- **OpenSpec Documentation**: [openspec/AGENTS.md](./openspec/AGENTS.md)
- **Project Context**: [openspec/project.md](./openspec/project.md)
- **Architecture Deep Dive**: [building_jules_code_quality_plugin.md](./building_jules_code_quality_plugin.md)
- **OpenSpec Integration**: [integration_openspec_with_project_veridical.md](./integration_openspec_with_project_veridical.md)

---

## Summary

**Veridical** = The supervisor that orchestrates everything  
**OpenSpec** = The contract that defines what to build  
**Jules** = The worker that builds it in the cloud

Together, they create an autonomous quality assurance loop that:
- ✅ Ensures code meets YOUR standards
- ✅ Iterates automatically until perfect
- ✅ Preserves decision history
- ✅ Scales with cloud parallelism
- ✅ Prevents AI "context drift"
- ✅ Transforms probabilistic agents into deterministic engineers

**The result:** High-quality, tested, maintainable code with minimal human effort.

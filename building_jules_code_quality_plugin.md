# **Project Veridical: Architecting Autonomous Quality Assurance Loops for the Google Jules Ecosystem**

## **1\. Introduction: The Evolution of Agentic Orchestration**

The paradigm of software engineering is undergoing a fundamental transformation, shifting from syntax generation to high-level intent orchestration. The emergence of large language models (LLMs) has catalyzed this shift, evolving from simple autocompletion tools into autonomous agents capable of reasoning, planning, and executing complex development tasks. Within this rapidly expanding domain, two distinct architectural approaches have surfaced: the synchronous, local-execution model exemplified by **Claude Code**, and the asynchronous, cloud-native model represented by **Google Jules**. While both aim to reduce developer toil, they operate on divergent control theories that necessitate distinct management strategies to ensure code quality and reliability.

The current state of the art in agent orchestration is best illustrated by **Ralph** (ralph-claude-code), a community-developed wrapper for Claude Code.1 Ralph transforms the conversational interface of Claude Code into a persistent, self-correcting development loop. By implementing intelligent exit detection, circuit breakers, and iterative feedback mechanisms, Ralph effectively converts a probabilistic LLM into a deterministic engineering engine.1 It does so by leveraging the immediacy of the local terminal environment, where feedback loops are tight, and state is easily mutable.

However, the introduction of Google Jules presents a new set of challenges and opportunities. Jules operates as an asynchronous agent, spinning up isolated virtual machines (VMs) in the cloud to execute tasks, running tests, and managing Pull Requests (PRs) independently of the developer's local machine.3 This architecture offers superior scalability and context isolation but introduces significant latency in the feedback loop. The "fire-and-forget" nature of Jules, while convenient, creates a risk of divergence where the agent may drift from the user's intent or produce code that—while syntactically correct—fails to meet rigorous, project-specific quality standards.5

This report presents a comprehensive architectural analysis and implementation strategy for **Project Veridical**, a proposed system designed to bridge the gap between Ralph's rigorous quality loops and Jules' scalable cloud architecture. The objective of Project Veridical is to engineer a "Ralph-like" plugin for the Google Jules ecosystem that enforces high code quality through autonomous iterative testing, linter-guided refactoring, and strict adherence to AGENTS.md contracts. By deconstructing the operational logic of Ralph and mapping it to the asynchronous APIs of Jules, this document defines the blueprint for a local supervisory control system that turns Google's experimental agent into a production-ready autonomous engineer.

## ---

**2\. Deconstructing the Ralph Architecture: Lessons in Local Control**

To build a superior orchestration layer for Jules, one must first deeply understand the mechanisms that make Ralph effective for Claude Code. Ralph is not merely a script; it is a feedback control system designed to manage the stochastic nature of LLMs. Its success lies in its ability to impose external constraints—rate limits, loop counts, and exit criteria—on an otherwise unbounded conversational process.

### **2.1 The Core Loop Mechanism**

At the heart of Ralph lies a while loop implementation, often described as "Geoffrey Huntley's technique," which forces the agent to iterate until specific conditions are met.1 Unlike standard LLM interactions where the user manually prompts for corrections, Ralph automates this by treating the LLM's output as a signal to be evaluated.

The structure of the Ralph loop can be analyzed as a five-step cyclical process 1:

1. **Instruction Loading:** The system reads PROMPT.md, establishing the static baseline requirements for the task.  
2. **Execution:** It invokes the Claude Code CLI, passing the prompt and the current project context.  
3. **Progress Tracking:** It parses the output and updates task tracking files, specifically @fix\_plan.md.  
4. **Evaluation:** The system evaluates exit conditions, checking for completion signals or failure states.  
5. **Recursion:** If the exit conditions are not met, the loop repeats, often carrying forward the context of previous errors.

The genius of this approach is its simplicity and reliance on local file system state. Because Claude Code runs locally, Ralph can verify "truth" by inspecting the actual files on the disk in milliseconds. This tight coupling between the agent's actions and the verification mechanism allows for rapid iteration cycles—a luxury that the asynchronous Jules architecture does not inherently afford.

### **2.2 Intelligent Exit Detection and State Analysis**

One of the most critical innovations in Ralph is its "Intelligent Exit Detection".1 Early iterations of autonomous loops suffered from two primary failure modes: premature exit (stopping before the task is done) and infinite looping (getting stuck in a repair cycle).

Ralph addresses these through a multi-faceted analysis of the agent's output:

* **Task List Verification:** It parses @fix\_plan.md to ensure all checkboxes are marked complete.1 This delegates the definition of "done" to a structured artifact that the LLM itself manages.  
* **Semantic Signal Detection:** It scans the stdout stream for "done" signals. To prevent false positives, it requires multiple consecutive signals (MAX\_CONSECUTIVE\_DONE\_SIGNALS=2).1  
* **Heuristic Analysis:** It detects "test-focused loops." If the agent spends too many iterations writing and running tests without modifying feature code, Ralph infers that the feature is complete and the agent is merely verifying, triggering a safe exit.1

This logic implies that "quality" in an autonomous system is not just about passing tests; it is about the *convergence* of the system toward a stable state. Project Veridical must replicate this convergence detection but must do so by analyzing API payloads and git diffs rather than streaming text.

### **2.3 The Circuit Breaker Pattern**

Autonomous agents have a propensity for "zombie loops"—situations where the agent repeatedly attempts the same failed fix, burning through API credits and time.6 Ralph implements a robust circuit breaker to mitigate this risk.

The circuit breaker logic monitors three key metrics 1:

1. **No Progress:** If the file system state does not change significantly over 3 loops, the circuit opens.  
2. **Repeated Errors:** If the semantic analyzer detects the same error message in 5 consecutive loops, it terminates the process.  
3. **API Limits:** It proactively monitors hourly usage limits (default 100 calls/hour) and pauses execution to prevent account suspension.

This defensive programming is essential. In the context of Jules, which spins up costly Cloud VMs, the financial and temporal cost of a runaway loop is significantly higher. Therefore, Project Veridical's circuit breaker must be even more aggressive and sophisticated than Ralph's.

### **2.4 Infrastructure and Monitoring**

Ralph provides visibility through ralph-monitor, a tmux-based dashboard that displays real-time loop status, API usage, and logs.1 This highlights a critical requirement for any autonomous system: **Observability**. The user effectively acts as a manager supervising a junior engineer. They do not need to see every keystroke, but they need to see the "health" of the worker.

For Jules, which operates "headless" in the cloud, this observability is usually provided by a web dashboard.7 However, for a CLI-driven power user tool like Veridical, we must pull this telemetry back to the local terminal to maintain the "developer flow" that tools like Ralph provide.

## ---

**3\. The Jules Ecosystem Analysis: Asynchronicity and the Cloud**

To port the Ralph methodology to Jules, we must acknowledge that Jules is not simply "Claude in the cloud"; it is a fundamentally different species of tool. It is an agentic service deeply integrated into the Google Cloud Platform (GCP) and GitHub infrastructure.

### **3.1 The Architecture of Remote Asynchronicity**

Jules operates on a "Plan-Execute-Pull Request" model.4 When a user issues a command via the jules CLI or API, the following sequence occurs:

1. **Session Creation:** The request is queued, and a session ID is generated.  
2. **Environment Provisioning:** Google Cloud spins up a secure, isolated VM. This VM clones the repository, effectively creating a "clean room" environment.3  
3. **Context Analysis:** The agent reads the codebase, including AGENTS.md and dependency files, to understand the project structure.  
4. **Plan Generation:** Jules proposes a plan of action. Crucially, the system defaults to waiting for human approval at this stage.10  
5. **Execution:** Upon approval, Jules modifies files, runs tests (if instructed), and commits changes.  
6. **Artifact Delivery:** The result is delivered as a GitHub PR or a patch accessible via the API.7

This architecture introduces **latency**. A Ralph loop might iterate every 10 seconds. A Jules loop might take 5-10 minutes per iteration due to VM provisioning and build times. This dictates that Project Veridical cannot rely on "brute force" looping. Instead, it must emphasize **Prompt Precision** and **Batch Verification**.

### **3.2 The Jules CLI (jules) vs. REST API**

While Jules offers a CLI tool (jules), primarily designed for interactive use via a TUI (Terminal User Interface).11 This creates friction for automation. The TUI expects human interaction, whereas a Ralph-like loop requires headless operation.

Key limitations of the CLI for automation include:

* **Lack of JSON Output:** The documentation for jules does not explicitly confirm a global \--json flag for all commands, unlike the Salesforce CLI.12 This forces reliance on text scraping or piping, which is brittle.  
* **Interactive Defaults:** Commands like remote new often default to opening a dashboard or waiting for TUI input unless carefully flagged.11

Consequently, Project Veridical must bypass the CLI for critical control operations and interface directly with the **Jules REST API** (jules.googleapis.com).9 The API exposes the granularity required for:

* **create:** Starting sessions with specific parameters (requirePlanApproval=false).  
* **get / list:** Polling session status programmatically.  
* **approvePlan:** Overriding the human-in-the-loop requirement.  
* **activities:** Retrieving the internal "thought process" or logs of the agent.

### **3.3 The Role of AGENTS.md**

Jules natively supports the AGENTS.md standard.14 This file is the remote equivalent of Ralph's PROMPT.md but is more structural. It defines "how to build," "how to test," and "coding conventions."

In the Ralph ecosystem, PROMPT.md is often static. In the Veridical ecosystem, AGENTS.md becomes a **dynamic control surface**. By programmatically modifying AGENTS.md before dispatching a task, Veridical can inject specific constraints (e.g., "Run only test suite X," "Use strict TypeScript configuration") tailored to the current iteration of the repair loop. This capability is central to improving code quality, as it allows the supervisor to "teach" the agent the rules of the environment in real-time.

## ---

**4\. Architectural Blueprint: Project Veridical**

Project Veridical is defined as a **Local Supervisory Control System** for remote asynchronous agents. It resides on the developer's machine (or a CI/CD runner), acting as a bridge between the local "source of truth" (the code and tests) and the remote "worker" (Jules).

### **4.1 System Components and Interaction Model**

The architecture of Veridical consists of five primary components that interact in a rigorous polling loop.

| Component | Function | Jules Interface | Ralph Equivalent |
| :---- | :---- | :---- | :---- |
| **Supervisor (Kernel)** | Manages the control loop, state, and decision logic. | N/A (Local Logic) | ralph\_loop.sh |
| **Dispatcher** | Formats prompts and initiates remote sessions via API. | POST /v1alpha/sessions | claude CLI execution |
| **Poller** | Monitors the asynchronous progress of the remote VM. | GET /v1alpha/sessions/{id} | Standard output stream reader |
| **Synchronizer** | Manages Git branches and applies remote patches locally. | git fetch, jules remote pull | File system reads |
| **Verifier** | Runs local tests/linters to validate quality. | npm test, make test | bats tests (internal) |

### **4.2 The Control Theory of Asynchronous Agents**

The fundamental difference between Ralph and Veridical is the handling of state. Ralph shares state with the agent (the file system). Veridical does not. The Jules VM has its own copy of the repo.

Therefore, Veridical must implement a **State Synchronization Pattern**:

1. **State Capture:** Veridical captures the local git commit hash.  
2. **Dispatch:** It sends this context to Jules.  
3. **Divergence:** Jules works on a clone, potentially drifting if the local repo changes.  
4. **Re-convergence:** Veridical pulls the Jules PR/diff and attempts to merge it onto a temporary local branch.  
5. **Verification:** Tests are run *locally* on the merged state. This is crucial. We do not trust the Jules VM's self-reported success because the VM is ephemeral and may lack specific local environment variables or hardware access available on the developer's machine.

### **4.3 Handling the "Plan Approval" Bottleneck**

A significant barrier to autonomy in Jules is the default requirement for plan approval.13 For a fully autonomous loop, waiting for a human to click "Approve" on a web dashboard is unacceptable.

Veridical handles this through a **Pre-Authorization Strategy**:

* **API Configuration:** When creating a session, Veridical sets the requirePlanApproval field to false in the JSON payload.13  
* **Reactive Approval:** If the API enforces approval (e.g., due to policy), the Poller component detects the WAITING\_FOR\_PLAN\_APPROVAL activity state and immediately sends a POST request to the :approvePlan endpoint, effectively "rubber-stamping" the agent's plan to maintain momentum.

## ---

**5\. Detailed Component Design: Building the Supervisor**

This section details the specific logic and implementation requirements for the core components of Project Veridical.

### **5.1 The Supervisor Loop Logic**

The Supervisor is the brain of the operation. It replaces the Bash script of Ralph with a robust Python or Go daemon capable of handling HTTP requests and JSON parsing.

The logic flow is as follows:

Python

def veridical\_loop(task\_description, max\_iterations=10):  
    iteration \= 0  
    current\_error\_context \= ""  
      
    while iteration \< max\_iterations:  
        \# 1\. Context Preparation  
        \# Dynamically update AGENTS.md with current error focus  
        update\_agents\_md(current\_error\_context)  
          
        \# 2\. Dispatch Phase  
        full\_prompt \= construct\_sandwich\_prompt(task\_description, current\_error\_context)  
        session\_id \= jules\_api.create\_session(  
            prompt=full\_prompt,   
            require\_plan\_approval=False  \# Autonomous mode  
        )  
          
        \# 3\. Monitor Phase (The Async Wait)  
        status \= "PENDING"  
        while status not in:  
            time.sleep(30) \# Intelligent Backoff Polling  
            status, logs \= jules\_api.get\_status(session\_id)  
              
            if status \== "WAITING\_FOR\_INPUT":  
                \# Heuristic: Always encourage progress unless critical error  
                jules\_api.send\_message(session\_id, "Proceed with the optimal path.")  
            elif status \== "WAITING\_FOR\_PLAN\_APPROVAL":  
                jules\_api.approve\_plan(session\_id)

        \# 4\. Synchronization Phase  
        if status \== "FAILED":  
            \# Extract error from remote VM logs  
            current\_error\_context \= parse\_remote\_logs(logs)  
            iteration \+= 1  
            continue

        \# Fetch the patch/diff from the session  
        patch\_data \= jules\_api.get\_diff(session\_id)  
          
        \# Create isolation branch to protect main  
        local\_branch \= git.checkout\_new\_branch(f"veridical/iter-{iteration}")  
        apply\_success \= git.apply\_patch(patch\_data)  
          
        if not apply\_success:  
            current\_error\_context \= "The generated patch could not be applied cleanly."  
            iteration \+= 1  
            continue

        \# 5\. Verification Phase (The Quality Gate)  
        test\_result \= run\_local\_verifier()  
          
        if test\_result.success:  
            print(f"SUCCESS: Iteration {iteration} passed all quality gates.")  
            git.merge\_to\_main() \# Commit the win  
            return True  
        else:  
            \# 6\. Feedback Construction  
            print(f"Iteration {iteration} failed local verification.")  
            current\_error\_context \= format\_feedback(test\_result.logs)  
              
            \# Reset state for next loop  
            git.checkout("main")  
            git.delete\_branch(local\_branch)  
            iteration \+= 1

    print("FAILURE: Max iterations reached without stable solution.")  
    return False

### **5.2 The API Dispatcher**

The Dispatcher wraps the Jules REST API. Unlike the CLI, which is opaque, the Dispatcher ensures specific headers and payloads are used to maximize autonomy.

**Key Implementation Detail:** The sourceContext payload must be precise.

JSON

{  
  "prompt": "Fix the memory leak in the image parser...",  
  "sourceContext": {  
    "source": "sources/github/user/repo",  
    "githubRepoContext": {  
      "startingBranch": "main"  
    }  
  },  
  "automationMode": "AUTO\_CREATE\_PR",   
  "requirePlanApproval": false  
}

*Note on automationMode:* While AUTO\_CREATE\_PR is useful for final delivery, Veridical might prefer a mode that just generates the diff (if available) to avoid spamming the GitHub repo with dozens of failed PRs during the iteration phase. If Jules requires a PR, Veridical should instruct it to target a specific "scratch" branch.

### **5.3 The Verifier: Local Truth**

The Verifier is the most critical component for "improving code quality." It does not rely on Jules' internal checks. It runs the user's local toolchain.

**Configuration:** The Verifier reads a .veridical.yaml config (or parses AGENTS.md) to know which commands to run.

* **Linter:** eslint src/ \--max-warnings=0  
* **Unit Tests:** npm test  
* **Integration:** npm run test:e2e

**Feedback Generation:** When the Verifier fails, it captures the stderr and stdout. Crucially, it must *summarize* this data. Sending 10MB of logs back to the LLM context window will degrade performance. The Verifier should use a heuristic to extract the "Stack Trace" or "Summary" section of the logs and inject *that* into current\_error\_context.

## ---

**6\. Improving Code Quality: Strategies Beyond the Loop**

The original request explicitly seeks to "improve the code quality created by Jules." A simple loop only ensures the code *works* (passes tests). To ensure *quality* (maintainability, readability, security), Veridical must employ more advanced strategies.

### **6.1 The "Sandwich" Prompt Strategy**

Jules, like all LLMs, is sensitive to the prompt structure. Veridical creates a "Sandwich Prompt" that wraps the user's intent in a quality assurance layer.

* **Top Layer (Role Definition):** "You are a Senior Principal Engineer obsessed with SOLID principles, memory safety, and minimal code complexity. You are working in a strict TDD environment."  
* **Filling (User Intent):** "Add a user profile page."  
* **Bottom Layer (Constraint Injection):** "Before submitting, you must verify that: 1\. No new 'any' types are introduced (TypeScript). 2\. All public functions have JSDoc. 3\. New logic is covered by at least one unit test. Failure to meet these criteria will result in automatic rejection."

This ensures that even if the user provides a lazy prompt ("fix this bug"), the agent receives a rigorous engineering directive.

### **6.2 Dynamic AGENTS.md Injection**

The AGENTS.md file is the primary context driver for Jules.17 Veridical leverages this by dynamically appending ephemeral instructions based on the current context.

Scenario: The loop detects a failure in accessibility tests.  
Action: Veridical appends the following to AGENTS.md for the next iteration:

# **EPHEMERAL CONSTRAINT**

The previous build failed due to WCAG 2.1 violations.  
ALL new UI components MUST include aria-label attributes.  
Do not generate any HTML without accessibility attributes.  
This forces the agent to prioritize the specific quality metric that is currently failing, dynamically tuning the agent's focus.

### **6.3 Parallel Consensus (The "Wisdom of Agents")**

Jules supports a \--parallel flag.11 Veridical can exploit this to select the *best* code, not just *working* code.

**The Duel Mode:**

1. Veridical spawns 3 parallel sessions for the same task.  
2. It retrieves 3 distinct patches (Patch A, Patch B, Patch C).  
3. It runs the Verifier on all three.  
   * *Patch A:* Fails tests. (Discard)  
   * *Patch B:* Passes tests. Code size: 200 lines. Complexity Score: High.  
   * *Patch C:* Passes tests. Code size: 50 lines. Complexity Score: Low.  
4. **Selection Logic:** Veridical selects **Patch C** because it solves the problem with the least code (Occam's Razor for Code).

This mechanism drastically improves quality by filtering out "bloated" or "hallucinated" solutions that happen to pass tests but introduce technical debt.

## ---

**7\. Safety, Security, and Resource Management**

Orchestrating autonomous agents in the cloud introduces risks that local agents (like Ralph) minimize. Cloud VMs cost money, and untethered agents can become security liabilities.

### **7.1 The "Zombie Agent" Defense**

Research indicates that autonomous agents can be vulnerable to "Zombie" attacks where prompt injection causes them to download malware or execute unauthorized commands.6

Veridical implements a **Scope Enforcer**:

1. **Diff Inspection:** Before applying any patch, Veridical inspects the git diff \--stat.  
2. **Allowlist Check:** If the user asked to "Fix CSS," but the diff shows changes to .github/workflows/deploy.yml or auth.py, Veridical **trips the circuit breaker**.  
3. **Termination:** The session is aborted, and a security warning is logged. "Agent attempted to modify out-of-scope infrastructure files."

### **7.2 Quota and Cost Management**

Jules has strict usage limits (e.g., 60 tasks/day for Ultra).7 A runaway loop could drain this quota in an hour.

Token Bucket Semaphore:  
Veridical maintains a local persistence file (.veridical\_state.json) tracking usage.

* **Logic:** if daily\_usage \> 50: pause\_for\_24h().  
* **Concurrency:** It respects the concurrency limit (e.g., 5 parallel tasks) by using a semaphore. If a user tries to run a 6th task, Veridical queues it locally rather than failing at the API level.

### **7.3 The "Stuck Loop" Heuristic**

If Jules returns the exact same diff hash for 3 consecutive iterations, it is "stuck" in a local minimum. Retrying the same prompt will yield the same result.

Recovery Strategy:  
Veridical detects this stagnation and injects a "Temperature Shift":

* It alters the prompt: "The previous 3 attempts yielded identical invalid results. You must attempt a **radically different** architectural approach. Do not use the previous logic."  
* This forces the LLM to break out of its probability rut and explore new solution paths.

## ---

**8\. Integration and Workflow**

Project Veridical is designed to fit into the modern developer's toolchain, serving as a CLI utility that can be run locally or in CI pipelines.

### **8.1 The CLI Interface**

The Veridical CLI (veridical) should mirror the ergonomics of Ralph but tailored for the Jules workflow.

**Command Structure:**

* veridical fix "Fix bug in login": Initiates the main QA loop.  
* veridical verify: Runs the local verification suite (useful for debugging the verifier configuration).  
* veridical status: Polls active Jules sessions and displays a table of iteration counts and pass/fail rates.  
* veridical config: Generates the .veridical.yaml and ensures AGENTS.md exists.

### **8.2 CI/CD Integration (GitHub Actions)**

Veridical can be deployed as a GitHub Action to automate issue resolution.

**Workflow Example:**

YAML

name: Auto-Fix with Veridical  
on:  
  issues:  
    types: \[labeled\]  
jobs:  
  jules-fix:  
    if: github.event.label.name \== 'jules-fix'  
    runs-on: ubuntu-latest  
    steps:  
      \- uses: actions/checkout@v3  
      \- name: Run Veridical Loop  
        run: |  
          pip install veridical-cli  
          veridical fix "${{ github.event.issue.title }}" \--issue-number ${{ github.event.issue.number }}  
        env:  
          JULES\_API\_KEY: ${{ secrets.JULES\_API\_KEY }}

This allows a developer to label an issue "jules-fix" and have Veridical autonomously spin up, iterate on the solution, and post a high-quality, verified PR.

## ---

**9\. Comparative Analysis: Ralph vs. Veridical**

To summarize the architectural shift, we present a comparative analysis of the existing Ralph tool and the proposed Veridical system.

### **Table 1: Architectural Comparison**

| Feature | Ralph (Claude Code) | Project Veridical (Jules) |
| :---- | :---- | :---- |
| **Execution Context** | Local Machine (User's Shell) | Cloud VM (Google Infrastructure) |
| **Feedback Latency** | Low (Seconds) | High (Minutes) |
| **State Management** | Shared Filesystem | Disconnected (Git Sync Required) |
| **Verification** | User-defined scripts | Local Runner \+ Remote Logs |
| **Exit Detection** | Stdout Regex / File Checks | API Status / Local Test Pass |
| **Cost Model** | Per-Token / Hourly Limits | Per-Task / Quota Limits |
| **Parallelism** | Serial (Single Thread) | Native Parallel (Cloud Scaling) |

### **Table 2: Quality Assurance Mechanisms**

| Mechanism | Ralph Implementation | Veridical Implementation |
| :---- | :---- | :---- |
| **TDD Enforcement** | Detects "test-focused" loops | Injects TDD constraints into Prompt |
| **Context Control** | PROMPT.md (Static) | AGENTS.md (Dynamic Injection) |
| **Loop Break** | Max Iterations / Stuck Error | Diff Hash Stagnation / Security Scope |
| **Selection** | Iterative Refinement | Parallel Consensus (The Duel) |

## ---

**10\. Conclusion**

The transition from manual coding to autonomous agent orchestration is inevitable. Tools like Ralph have demonstrated the power of wrapping LLMs in rigorous logical loops to achieve reliability. However, the future belongs to asynchronous, scalable cloud agents like Google Jules.

**Project Veridical** represents the necessary evolution of the Ralph methodology for this new era. By acknowledging the constraints of asynchronicity—latency, state isolation, and cost—and leveraging the strengths—parallelism, isolated environments, and structured APIs—Veridical creates a system that does not just "write code" but "engineers solutions."

Through the implementation of the **Supervisor Loop**, the **Dynamic AGENTS.md Contract**, and the **Parallel Consensus Engine**, Veridical fulfills the requirement to "improve the code quality created by Jules." It moves the quality gate from the remote VM, where the agent grades its own homework, to the local environment, where the developer's rigorous standards hold court. This architecture ensures that when a Jules PR finally lands in the queue, it is not just a draft—it is a verified, polished artifact ready for deployment.

### **Key Recommendations for Implementation**

1. **Prioritize API over CLI:** Reliability depends on the structured data of the REST API, not the fragile text output of the TUI CLI.  
2. **Invest in the Verifier:** The quality of the output is directly proportional to the quality of the local tests run by the Verifier.  
3. **Security First:** Never allow an autonomous agent to apply patches without a scope check. The "Zombie Agent" vector is real.  
4. **Feedback Fidelity:** When the loop fails, providing the *exact* stack trace to the next iteration is the single highest-leverage action for success.

This report serves as the definitive architectural guide for building Project Veridical, enabling developers to harness the full potential of Google Jules while maintaining the disciplined quality standards of professional software engineering.

## ---

**11\. Appendix: Technical Reference Data**

### **Table 3: Jules API Endpoint Mapping for Veridical Supervisor**

| Action | HTTP Method | Endpoint | Purpose in Loop |
| :---- | :---- | :---- | :---- |
| **Start Loop** | POST | /v1alpha/sessions | Dispatches the initial attempt; sets requirePlanApproval=false. |
| **Poll Status** | GET | /v1alpha/sessions | Checks if session is COMPLETED, FAILED, or WAITING. |
| **Get Feedback** | GET | /v1alpha/.../activities | Retrieves the agent's internal reasoning and remote logs. |
| **Override Wait** | POST | /v1alpha/...:approvePlan | Bypasses the "Human in the Loop" for autonomous operation. |
| **Inject Log** | POST | /v1alpha/...:sendMessage | Sends local error logs back to the agent for the next attempt. |
| **Get Patch** | GET | (CLI remote pull) | Retrieves the artifact for local verification. |

### **Table 4: Suggested AGENTS.md Quality Template**

# **AGENTS.md**

## **Quality Standards**

1. **Testing:** All new features must have 100% unit test coverage.  
2. **Linting:** Code must pass eslint with zero warnings.  
3. **Types:** No explicit any in TypeScript.  
4. **Docs:** Public methods must have TSDoc comments.

## **Interaction Protocol**

* If a test fails, analyze the stack trace provided in the next prompt.  
* Do not attempt to modify configuration files unless explicitly asked.  
* If you are stuck, revert to the simplest working implementation.

#### **Works cited**

1. frankbria/ralph-claude-code: Autonomous AI development ... \- GitHub, accessed January 3, 2026, [https://github.com/frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code)  
2. Ralph Wiggum: Autonomous Loops for Claude Code \- Emergent Minds | paddo.dev, accessed January 3, 2026, [https://paddo.dev/blog/ralph-wiggum-autonomous-loops/](https://paddo.dev/blog/ralph-wiggum-autonomous-loops/)  
3. Build with Jules, your asynchronous coding agent \- Google Blog, accessed January 3, 2026, [https://blog.google/technology/google-labs/jules/](https://blog.google/technology/google-labs/jules/)  
4. Google Jules AI Coding Agent Review: Workflow, Privacy & Pricing (2025), accessed January 3, 2026, [https://skywork.ai/blog/google-jules-ai-coding-agent-review-2025/](https://skywork.ai/blog/google-jules-ai-coding-agent-review-2025/)  
5. Jules and the Rise of Agentic AI \- ScaleSec, accessed January 3, 2026, [https://scalesec.com/blog/jules-agentic-ai](https://scalesec.com/blog/jules-agentic-ai)  
6. Jules Zombie Agent: From Prompt Injection to Remote Control \- Embrace The Red, accessed January 3, 2026, [https://embracethered.com/blog/posts/2025/google-jules-remote-code-execution-zombai/](https://embracethered.com/blog/posts/2025/google-jules-remote-code-execution-zombai/)  
7. Jules \- An Autonomous Coding Agent, accessed January 3, 2026, [https://jules.google/](https://jules.google/)  
8. Jules by Google . When Google built an AI that doesn't… | by Intelligent Hustle | Dec, 2025 | Towards AI, accessed January 3, 2026, [https://pub.towardsai.net/jules-by-google-88981e4853bd](https://pub.towardsai.net/jules-by-google-88981e4853bd)  
9. Jules API | Google for Developers, accessed January 3, 2026, [https://developers.google.com/jules/api](https://developers.google.com/jules/api)  
10. Reviewing plans & giving feedback \- Jules, accessed January 3, 2026, [https://jules.google/docs/review-plan/](https://jules.google/docs/review-plan/)  
11. Jules Tools Reference, accessed January 3, 2026, [https://jules.google/docs/cli/reference/](https://jules.google/docs/cli/reference/)  
12. Support for JSON Responses | Salesforce CLI Setup Guide, accessed January 3, 2026, [https://developer.salesforce.com/docs/atlas.en-us.sfdx\_setup.meta/sfdx\_setup/sfdx\_dev\_cli\_json\_support.htm](https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_dev_cli_json_support.htm)  
13. Jules API \- Google for Developers, accessed January 3, 2026, [https://developers.google.com/jules/api/reference/rest](https://developers.google.com/jules/api/reference/rest)  
14. AGENTS.md Emerges as Open Standard for AI Coding Agents \- InfoQ, accessed January 3, 2026, [https://www.infoq.com/news/2025/08/agents-md/](https://www.infoq.com/news/2025/08/agents-md/)  
15. AGENTS.md, accessed January 3, 2026, [https://agents.md/](https://agents.md/)  
16. Agents.md: A Machine-Readable Alternative to README \- Research AIMultiple, accessed January 3, 2026, [https://research.aimultiple.com/agents-md/](https://research.aimultiple.com/agents-md/)  
17. Getting started | Jules, accessed January 3, 2026, [https://jules.google/docs/](https://jules.google/docs/)  
18. Changelog | Jules, accessed January 3, 2026, [https://jules.google/docs/changelog/](https://jules.google/docs/changelog/)
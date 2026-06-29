# Autonomous AI Pen Tester: Design

## Overview

An LLM planner runs an authorized penetration test end to end. It reasons over a target, calls tools to recon, probe, and confirm vulnerabilities, and reports what it finds. Every action passes through a safety layer that enforces the authorized scope in code, not in a prompt, so the agent physically cannot act outside the rules of engagement. The design is organized around four properties: safe, contextual, effective, and concurrent.

## Architecture

```mermaid
flowchart TD
    OP["Operator<br/>objective + rules of engagement"] --> PL

    subgraph LOOP["Agent loop: plan, act, observe, reflect"]
        PL["Planner<br/>Claude Opus 4.8, adaptive thinking"]
        SG["Safety layer<br/>ScopeGuard + AuditLog"]
        TB["Tool layer<br/>discover_content, http_request,<br/>probe_sqli, probe_xss"]
        CX["Context store<br/>endpoints + findings"]

        PL -->|tool calls, executed concurrently| SG
        SG -->|in scope only| TB
        TB -->|results| CX
        CX -->|knowledge fed back| PL
    end

    TB <-->|requests / responses treated as untrusted data| TG[("Target<br/>OWASP Juice Shop<br/>127.0.0.1 only")]
    SG -.->|out of scope| BK["ScopeError: blocked"]
    PL -->|report_finding| CX
    CX --> RP["Reporter<br/>confirmed + candidate findings"]
```

The diagram above shows the operator handing an objective and rules of engagement to the planner inside an agent loop of plan, act, observe, and reflect. The planner emits tool calls executed concurrently to the safety layer, the safety layer passes only in scope calls to the tool layer, the tool layer returns results to the context store, and the context store feeds knowledge back to the planner. Requests and responses between the tool layer and the OWASP Juice Shop target on 127.0.0.1 are treated as untrusted data, out of scope calls are blocked with a ScopeError, and the context store also feeds the reporter that lists confirmed and candidate findings.

## The four pillars

This is the whole machine in one picture. The planner is left unshaded because
it is the interchangeable and untrusted part, and each pillar gets its own
grayscale band, the safety layer and its blocked branch for safe, the fan out
under one semaphore for concurrent, the exploration graph for contextual, and the
reflect step plus the typed findings and report for effective.

```mermaid
flowchart TD
    OP["Operator<br/>Objective and Rules of Engagement"] --> PL

    subgraph LOOP["Bounded Agent Loop"]
        direction TB
        PL["Planner<br/>Claude Opus 4.8, Adaptive Thinking<br/>Plans from the Frontier"]
        RF["Structured Reflection<br/>Goal, Evidence, Confidence, Unknowns, Hypothesis"]
        SG["Safety Layer<br/>ScopeGuard Allowlist in Code<br/>Append Only AuditLog, Per Host Budget, Rate Limit"]

        TOOLS["Concurrent Tool Calls under a Bounded Semaphore<br/>discover_content, http_request, probe_sqli, probe_xss<br/>Fanned Out with asyncio.gather"]

        CX["Exploration Graph<br/>Reached Nodes, Params, Auth State, Tested Vectors"]

        PL --> RF
        RF --> PL
        PL -->|Tool Calls| SG
        SG -->|In Scope Only| TOOLS
        TOOLS -->|Results as Untrusted Data| CX
        CX -->|Map and Frontier, Where Have I Not Been| PL
    end

    TOOLS <-->|Rate Limited Requests| TG[("Authorized Target<br/>127.0.0.1 Only")]
    SG -.->|Out of Scope| BK["ScopeError, Blocked in Code"]
    CX --> FN["Typed Findings<br/>SQLi CWE 89, XSS CWE 79, Information Disclosure<br/>Each Carries CWE and Remediation"]
    FN --> RP["Report, Generated from the Typed Objects"]

    classDef safe fill:#cccccc,stroke:#333333,color:#000000
    classDef ctx fill:#e6e6e6,stroke:#333333,color:#000000
    classDef eff fill:#b3b3b3,stroke:#333333,color:#000000
    classDef conc fill:#f2f2f2,stroke:#333333,color:#000000
    class SG,BK safe
    class CX ctx
    class RF,FN,RP eff
    class TOOLS conc
```

The diagram above shows the whole agent as one loop. The operator gives an objective and rules of engagement to the planner. Inside a bounded agent loop the planner records a structured reflection and sends tool calls to the safety layer, the safety layer passes only in scope calls to the concurrent tool calls running under a bounded semaphore, those results return to the exploration graph as untrusted data, and the graph hands the planner its map and frontier so its next decision is where it has not been. Rate limited requests reach the authorized target on 127.0.0.1, out of scope calls are blocked in code with a ScopeError, and the exploration graph feeds typed findings that each carry their own weakness identifier and remediation and render the report. The four properties appear as shaded bands, safe for the safety layer and the blocked branch, concurrent for the tool node, contextual for the exploration graph, and effective for the reflection, the typed findings, and the report.

* **Safe.** Scope is an allowlist of hosts and ports enforced in code in
  `ScopeGuard.check_url`, which runs before every request. The agent ingests
  untrusted response bodies as data, never as instructions. Every action is
  written to an append only audit log. A per host request budget and rate limit
  bound the blast radius. Realized in `safety.py`.
* **Contextual.** A `Context` store holds the endpoints discovered and the
  findings recorded, and feeds a summary back to the planner so each decision is
  informed and work is not repeated. Realized in `context.py`.
* **Effective.** The agent does not just match patterns. It reasons about which
  parameters to probe, confirms candidates from real tool results, and records
  only what the evidence supports. Realized across `agent.py` and `tools.py`.
* **Concurrent.** Independent probes run in parallel. Within a turn, the agent
  fans out multiple tool calls executed with `asyncio.gather`; within a tool,
  `discover_content` probes many paths at once. A bounded semaphore plus a per
  second rate limit keep it from overwhelming the target. Realized in `agent.py`
  and `tools.py`.

## Components

| Component | File | Responsibility |
|---|---|---|
| Configuration and rules of engagement | `config.py` | Scope allowlist, limits, model |
| Safety layer | `safety.py` | ScopeGuard, AuditLog |
| Tool layer | `tools.py` | Scope checked, rate limited, concurrent tools |
| Context store | `context.py` | Endpoints and findings, planner summary |
| Planner | `agent.py` | The plan, act, observe, reflect loop |
| Reporter | `report.py` | Confirmed and candidate findings |
| Entry point | `main.py` | Wires it together, reads the key from env |

## The loop

1. The operator gives an objective and a scope.
2. The planner reasons and emits one or more tool calls.
3. Each call passes through the safety layer. Out of scope calls are blocked in
   code with a ScopeError before any packet leaves.
4. In scope calls run, concurrently, and are recorded in the audit log.
5. Results update the context store and return to the planner as data.
6. The planner reflects and either probes further or records a finding.
7. When the surface is covered, it ends its turn and the reporter renders the
   findings.

## Safety model (the lead concern)

Because this is a tool that attacks systems, safety is the hard constraint, not a feature.

* Scope is enforced at the tool and network layer, in code, never only in the
  prompt, because a prompt boundary can be jailbroken.
* Tool response bodies are untrusted input. A malicious target could plant
  instructions in an error message, so the planner is told, and structured to
  treat, all tool output as data.
* The audit log is the forensic trail that proves the engagement stayed in scope.
* Request budgets and rate limits cap the blast radius and avoid denial of
  service on the target.
* In a full build, destructive or high impact actions sit behind a human
  approval gate, with graduated autonomy by action impact.

## What is built now versus a full development cycle

Built now (the demo):
* One authorized target, an intentionally vulnerable app, so it is safe and legal.
* The planner loop with Opus 4.8 and four tools plus a finding recorder.
* Concurrency, a scope allowlist, an audit log, and a report, end to end.

Full development cycle (the vision):
* Multi protocol coverage: web, API, network, cloud, and code.
* A pluggable tool registry over MCP, and specialized recon, exploit, validation,
  and reporting agents.
* A distributed, horizontally scalable worker fleet rather than threads on one box.
* A target knowledge graph and cross engagement learning.
* A full rules of engagement engine as policy as code, with graduated autonomy and
  an authorization workflow.
* An eval harness measuring coverage, precision, and false positive rate against
  known vulnerable corpora.
* Findings feeding into a remediation product, so the offensive agent finds it and
  the defensive agent fixes it.

## Scaling to multiple agents

The single agent loop becomes a fleet under an orchestrator. Three concerns drive that design: how to marshal many agents, how to keep each one least privileged, and how to validate the data flowing between them.

```mermaid
flowchart TD
    ORC["Orchestrator<br/>decomposes + dispatches"] --> Q["Task queue"]
    Q --> R1["Recon agent<br/>read only tools"]
    R1 -->|endpoints| Q
    Q --> E1["Exploit agent"]
    Q --> E2["Exploit agent"]
    Q --> E3["Exploit agent"]
    E1 --> V["Validation agent<br/>sandboxed proof of concept"]
    E2 --> V
    E3 --> V
    V -->|confirmed, schema validated| CTX["Canonical context<br/>orchestrator owned"]
    CTX --> REP["Reporter agent<br/>no network tools"]
```

The diagram above shows the multi agent design. The orchestrator decomposes the engagement and dispatches units to a task queue. The queue feeds a recon agent with read only tools, which returns discovered endpoints to the queue, and the queue feeds several exploit agents. The exploit agents hand candidates to a validation agent that builds a sandboxed proof of concept, the validation agent writes confirmed and schema validated results to the canonical context owned by the orchestrator, and the canonical context feeds a reporter agent that has no network tools.

### Orchestrator versus planner

The orchestrator is not a bigger planner, it is a different kind of component, and
keeping them distinct is what keeps the fleet trustworthy.

* The planner plans the attack, the orchestrator plans the division of labor. The
  planner reasons within one slice, deciding the next tool calls from its map and
  frontier. The orchestrator splits the engagement into units, fans them out, and
  owns the one canonical context.
* The planner is intra agent, the reasoning inside a single agent. The orchestrator
  is inter agent, the layer above the fleet. There is one orchestrator and many
  planners, since every worker carries its own.
* The planner is the untrusted component you constrain. The orchestrator is part of
  the trust boundary that does the constraining. It allocates each worker a scoped
  slice, its own budgets, and a short lived credential, and it validates every
  handoff.
* Because of that, the orchestrator must be trusted code, not a privileged free
  model holding the master key. A free model in that seat just recreates the
  untrusted planner problem one level up with more authority, so the decomposition
  and validation live in code and any model used to plan the split stays as
  constrained as the workers.

The planner in this build is the `Agent` class in `agent.py`. The orchestrator is
the next layer up, which the single agent loop generalizes into below.

### Marshalling several agents

An orchestrator decomposes the engagement into independent units (per host, per endpoint cluster, per vuln class) and fans them out. Two shapes:

* Worker pool: dispatch units to many copies of the same agent, run concurrently
  under a bounded semaphore, the same pattern as our tool concurrency one level
  up. The distributed version is a task queue plus a stateless worker fleet.
* Specialized pipeline: a recon agent maps the surface, hands endpoints to a pool
  of exploit agents, confirmed candidates go to validation agents, a reporter
  aggregates.

Coordination is a shared task queue plus one canonical context the orchestrator owns. Workers get a scoped slice and write back through a controlled interface, never directly. Concurrency is bounded so the fleet does not deny service to the target or exhaust the token budget, and a shared seen set dedups work.

### Least privilege per agent

Each agent gets only the tools and scope it needs, enforced in code, not the prompt. A recon agent gets read only discover and request, not the exploit probes. A reporter gets no network tools at all. Mechanism: instead of one shared Toolbox, give each agent its own Toolbox with its own ScopeGuard, scoped tighter than the global rules, so a worker assigned one host can only touch that host. Credentials follow the same rule: the orchestrator holds the key, workers get short lived scoped tokens or call through it. High impact actions sit behind an approval gate that only certain agents may even request.

Each agent also gets its own budgets, a request budget, a token and cost budget, and a step ceiling, allocated as a slice of the engagement total, so one worker cannot drain the whole run. For isolation stronger than the in code check alone, each agent can run in its own container with network egress filtering, which enforces the same scope at the operating system and network layer as defense in depth, so the boundary holds even if the in code check is ever bypassed. Every action an agent takes is logged with that agent's identity, so the audit trail attributes each request to a specific agent, which gives accountability and a way to spot a misbehaving one.

### Validation between agents

In a fleet, one agent's output is the next one's input, and target responses flow through both. Two threats: malformed data breaking the pipeline, and prompt injection propagating between agents.

* Strict schemas at every boundary. Inter agent handoffs and tool outputs validate
  against a schema before they are accepted. Our `Context.add_finding` is exactly
  this boundary: the orchestrator validates the finding shape, that the URL is in
  scope, and that evidence is present, before merging.
* Treat data from other agents as untrusted, not just data from the target. An
  agent's output is data to the next agent, never instructions, delimited and
  labeled as such in the receiving prompt.
* Provenance tagging. Tag each value with its source: operator, agent, or target.
  Target derived strings can never become tool arguments without validation,
  which stops an agent being steered by injected content.
* Sanitize and bound at each hop: type and range checks, length caps, strip
  control characters, before passing the value on.

These controls map to recognized frameworks. Least privilege per agent is NIST AC-6, trusting no component implicitly is a zero trust stance applied between your own agents, and the risks being closed are OWASP LLM07 insecure tool and plugin design and OWASP LLM08 excessive agency.

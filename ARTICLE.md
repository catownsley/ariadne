# Designing a Trustworthy Autonomous Penetration Testing Agent

Most writing about AI agents is about capability, how much a model can now do on its own. The harder and more durable question is trust. If you are going to let a powerful and not fully predictable component plan and act on its own against a real system, the interesting work is not teaching it to act. It is deciding what it is allowed to do, what is guaranteed in code rather than hoped for in a prompt, and how to make sure that when it is wrong, it is wrong safely. Ariadne is a small autonomous penetration testing agent built to explore exactly that question.

This article is about the architecture, not the model.

> **The model is the part that will age fastest. The architecture is the part worth keeping.**

## The thesis

The contribution of Ariadne is not that a language model can send an HTTP request. It is that the model is constrained to act only within an explicit safety and engagement boundary while still planning freely inside it. The planner is one component, and it is interchangeable. It is one model today and could be a different model, or a different vendor, tomorrow, and none of the safety properties change when it is swapped, because those properties are enforced by the code around the model and not by the model's good behavior. A design whose guarantees do not depend on which model is inside it has a much longer shelf life than the model does.

That reframing matters because it moves the work from prompt engineering, which is brittle and model specific, to systems design, which is not.

```mermaid
flowchart TD
    OP[Operator] -->|Objective and Scope| PL
    subgraph BOUND[The boundary the model cannot cross]
        PL[Planner, the language model] --> TB[Tool layer, typed and least privileged]
        TB --> SG[Scope guard, allowlist enforced in code]
        TB --> AU[(Append only audit log)]
        CX[Context, the exploration graph] --> PL
        TB --> CX
    end
    SG -->|In Scope Only| TGT[Authorized target]
    TGT -->|Untrusted Response| TB
```

## Constrain in code, not in prompts

The first and most important decision is where the rules of engagement live. It is tempting to put them in the system prompt, to tell the model which hosts it may touch and ask it to behave. That is not a control. A prompt is a request, and a model can be confused, jailbroken, or fed a malicious instruction inside the very data it is analyzing.

In Ariadne the scope is data, and it is enforced in code. Every outbound action passes through a scope guard that parses the host and the port out of the URL and checks them against an allowlist before anything reaches the network. It parses rather than string matches, because a naive check on the raw URL can be fooled by tricks such as a host that only looks like the allowed one. The model never gets a network primitive directly. It only gets tools, and every tool routes through the guard. The result is a hard property. Even a fully subverted planner cannot reach a host that is not on the list, because the request does not leave the guard.

The same idea bounds resource use. The guard enforces a per host request budget, and the tool layer paces and caps concurrency with a rate limit and a bounded semaphore, so a runaway loop or an injected instruction cannot turn the agent into a denial of service tool, against the target or against itself.

```mermaid
flowchart TD
    A[Planner decides the next move from the map] --> B[Tool layer, the only way to act]
    B --> C[Scope guard, allowlist enforced in code]
    C --> D[HTTP, the request reaches the target]
    D --> E[Observation, response returns as untrusted data]
    E --> G[Context, the exploration graph updates]
    G -->|Where Have I Not Been| A
```

## The audit trail and untrusted responses

Two more properties make the autonomy accountable rather than opaque.

Every action is written to an append only audit log, one self contained record per line. Append only is what makes the log evidence. Earlier entries are never rewritten, so the log can be used to prove that the engagement stayed in scope, and a run that is interrupted still leaves every completed action on its own valid line.

Every response body from the target is treated as untrusted data, never as instructions. This is the defense against indirect prompt injection, where a target plants text in its own response to try to hijack the agent that is reading it. The response is handled as data, truncated to a fixed size, and never allowed to become a command. Safety does not depend on the model choosing to ignore a malicious response, because the boundary already holds without that choice.

## Bounded autonomy

Autonomy without a ceiling is a liability. The planning loop is hard bounded by a maximum number of steps, so an agent that never decides it is finished still stops. Inside each step the model reasons, emits one or more tool calls, and the agent executes them concurrently and feeds the results back. The concurrency is itself bounded, so the agent can explore in parallel for speed while never opening more connections than the cap allows. Speed and restraint are not in tension here, they are both expressed by the same gate.

## Explicit state, the exploration graph

A planner with only a flat list of findings is really a planner with memory, and it plans by asking what it should do next, which invites repetition and blind spots. Ariadne instead maintains an explicit exploration graph rooted at the entry point of the target. Each node is a location the agent has reached and everything it learned there, the parameters it found, the auth state, and which attack vectors it has tested.

This turns planning into frontier search. After every step the agent is handed its map and its frontier, the set of places it has not yet been, and its decision becomes where have I not been rather than what should I do next. The state is explicit, which means it is auditable, it does not repeat work, and it could be paused and resumed. It also makes the implementation embody the idea behind the name. The graph is the thread, the record of where you have walked that lets you go deep and still find your way back.

```mermaid
flowchart TD
    O[Operator states the objective] --> P[Planner reflects and asks where it has not been]
    P --> T[Tool calls run concurrently through the safety layer]
    T --> U[Context update, the exploration graph and frontier grow]
    U -->|Frontier Still Has Work| P
    U --> F[Finding confirmed from the evidence and typed by class]
    F --> R[Report rendered from the typed findings]
```

## Structured reflection

Reasoning that only happens inside the model is reasoning you cannot inspect. Before it acts each step, the planner records a structured reflection, its goal, its evidence so far, its confidence, its unknowns, and its next hypothesis, and the unknowns and the hypothesis are drawn straight from the frontier. Each reflection is written to the audit log. The benefit is not only that the agent plans better. It is that the reasoning becomes a first class, reviewable artifact, so a human can read why the agent did what it did, not just what it did.

## Typed findings

A finding should describe itself. Rather than one flat finding record, Ariadne uses a small hierarchy of typed findings, one per vulnerability class, and each type carries its own weakness identifier and its own remediation as intrinsic properties. A SQL injection finding knows it is CWE-89 and knows how it is fixed. The moment the agent creates a finding of the right type, the finding is complete, and the report is generated straight from the objects rather than written by hand. The reporting that usually trails a pen test almost disappears, because the knowledge that a report needs was attached to the finding at the source.

## Scaling without losing the boundary

The single agent generalizes to a fleet under an orchestrator without giving up any of the guarantees, and least privilege is what holds it together. Each agent is built with only the tools and the scope its role needs, enforced in code. A reconnaissance agent is read only. A reporter has no network tools at all. An agent assigned one host is scoped to that host and gets its own budgets. Each agent carries its own scope guard rather than sharing one, and because the scope is checked inside every tool call, a worker given a single host cannot reach another host in any call it makes. Credentials follow the same rule. The orchestrator holds the key, and each worker gets only a short lived scoped token or calls through the orchestrator, so no worker ever holds the master secret.

Segmentation holds between agents the same way it holds between the model and the network. Agents do not talk to each other directly, they pass through the orchestrator, which authorizes, validates, and logs every message. One agent's output is treated as untrusted input to the next, validated against a schema and tagged with its source, so a subverted agent cannot steer its peers. For stronger isolation each agent can run in its own container with network egress filtering, so the scope is enforced at the operating system and network layer as well as in code. The named principles are least privilege, which is NIST AC-6, and a zero trust stance between your own components.

## A threat model that names the risks

The whole design is documented against recognized frameworks rather than asserted. The agent threat surface is modeled with STRIDE, with the OWASP Top 10 for LLM Applications, and with MITRE ATLAS. The controls that exist in code are separated honestly from the hardening that is planned. Indirect prompt injection, excessive agency, model denial of service, sensitive information disclosure, insecure tool design, and overreliance each map to a specific control or a specific gap. Naming the risks in a shared vocabulary is what lets a reviewer argue with the design instead of taking it on faith.

## Why this is security systems design, not AI security

The label AI security undersells what this is. The durable skill on display is security systems design. Look at the questions that did the work. What can this component reach. What is enforced in code rather than assumed in a prompt. Where are the trust boundaries. Is failure safe, bounded, and auditable. None of those questions belong to language models. They are the questions you ask of any powerful component you cannot fully trust, and they are the same whether the component is a language model, a third party service, or a piece of code you did not write.

That is why this kind of thinking scales past any single model or framework. The model is the part that changes. The discipline of building a system that stays trustworthy even when a powerful component inside it cannot be trusted is the part that does not.

## The labyrinth

There is one more thing that makes Ariadne whole, and it is not engineering. The project is paired with an original piano piece and a short film, and the name is the reason. In the myth, Ariadne is not the one who fights the monster. She is the one who gives the thread, so that someone can go into the labyrinth and find the way back. That is precisely what the architecture is for. It is a thread, the scope, the audit trail, and the exploration graph that let the agent go deep into a target and always return safely in bounds. Put plainly, care, memory, and clear boundaries are what let you venture into something dangerous and still find your way home, and in this project those three are the safety model, the memory of the exploration graph and the audit log, and the scope enforced in code.

The music traces the same journey, down into a minor key, up to a high and exposed quiet middle, an arrival, and a return to calm. The short film traces it visually, into a dark tangle, through the doubled and shifting selves, to a dancing center, and out through a lit door. The multiplied dancers are the concurrent agents, the fleet that walks the labyrinth in parallel, many threads laid at once and every one of them still finding the way back. The myth, the music, the visuals, and the software are one idea seen from four sides. The project is not about exploiting machines. It is about navigating a labyrinth and finding the way back, which turns out to be the right frame for the engineering too, because safe navigation within a boundary, not destruction, is the whole point.

The piano piece and the short film are my own original composition, performance, and production. No AI was used to make either of them. The only autonomous agent in this project is the one being tested.

## Watch and read more

The short film, the piano score, and the music are gathered on [the art page](ART.md), and the full project and this essay are in [the repository](https://github.com/catownsley/ariadne).

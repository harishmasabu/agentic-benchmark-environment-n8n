# Agentic Benchmark Environment — n8n + Codex

This repository contains two benchmark environments for evaluating **Codex-based agentic workflows orchestrated using n8n**.

The objective is to evaluate how AI agents perform on realistic multi-step tasks involving investigation, reasoning, execution, independent verification, and recovery from failure.

The two benchmark scenarios are:

1. **Production Incident Mitigation Workflow** — sequential agent workflow
2. **Customer Escalation WorkGraph** — multi-agent asynchronous workflow

---

## Architecture

The benchmark uses the following architecture:

```text
n8n
 │
 │ HTTP
 ▼
Local Flask Service
 │
 │ codex exec
 ▼
Codex CLI
 │
 ▼
Benchmark Environment
 │
 ▼
Independent Python Verifier
```

n8n does not directly call an LLM API.

Instead, a local Flask service acts as a bridge between n8n and the Codex CLI. The service executes agents using `codex exec` and returns their results to the workflow.

---

# Benchmark 1 — Production Incident Mitigation

## Scenario

This benchmark simulates a production checkout incident.

The application contains an intentionally introduced bug affecting EUR transactions while existing USD checkout behavior continues to work.

The agent must investigate the available evidence, determine the root cause, implement the appropriate fix, and produce an incident summary.

## Workflow

```text
Manual Trigger
      │
      ▼
Initialize Incident
      │
      ▼
Investigate Incident
      │
      ▼
Prepare Fix
      │
      ▼
Apply Fix
      │
      ▼
Prepare Incident Summary
      │
      ▼
Generate Incident Summary
      │
      ▼
Independent Verifier
```

The investigation stage is read-only, while the execution stages are allowed to modify the benchmark workspace.

## Independent Verification

The verifier checks that:

- USD checkout continues to work
- EUR checkout is repaired
- repeated EUR checkout behaves correctly
- payment validation remains enforced
- the payment contract remains intact
- existing order behavior is preserved
- the required incident summary is generated

The benchmark begins in an intentionally failing state.

To reset and verify the environment:

```bash
cd ProductionIncidentMitigationEnv

python3 reset_environment.py
python3 verifier.py
```

Before agent remediation, the verifier should end with:

```text
BENCHMARK_RESULT=FAIL
```

After successful remediation:

```text
BENCHMARK_RESULT=PASS
```

---

# Benchmark 2 — Customer Escalation WorkGraph

## Scenario

This benchmark simulates a customer escalation involving a duplicate payment.

The customer reports being charged twice for an order while the order management system still shows the order as unpaid.

Evidence is distributed across multiple systems:

```text
payments/transactions.json
orders/orders.json
support/tickets.json
policies/refund_policy.md
```

Instead of allowing one agent to inspect everything, the investigation is divided between specialized agents.

## WorkGraph

```text
                     ┌── Payment Investigator ──┐
                     │                          │
Initialize Case ─────┼── Order Investigator ────┼──► Aggregate Evidence
                     │                          │
                     └── Support Investigator ──┘
                                                        │
                                                        ▼
                                                  Decision Agent
                                                        │
                                                        ▼
                                                 Execution Agent
                                                        │
                                                        ▼
                                              Independent Verifier
                                                        │
                                             ┌──────────┴──────────┐
                                             │                     │
                                            PASS                  FAIL
                                             │                     │
                                             ▼                     ▼
                                          Complete            Retry Path
```

### Payment Investigator

Examines:

```text
payments/transactions.json
policies/refund_policy.md
```

Determines the valid transaction, identifies any duplicate transaction, and determines whether a refund is required.

### Order Investigator

Examines:

```text
orders/orders.json
```

Determines the current payment and fulfillment state of the affected order.

### Support Investigator

Examines:

```text
support/tickets.json
```

Determines what the customer reported, the current ticket state, and whether a refund has already been promised.

### Aggregate Evidence

The three independent findings are combined into a single structured handoff.

### Decision Agent

The Decision Agent receives the specialist findings and determines the required remediation without modifying the environment.

### Execution Agent

The Execution Agent performs the remediation and produces:

```text
output/resolution.json
```

The expected resolution includes:

- retaining the valid payment
- identifying the duplicate transaction
- refunding the duplicate transaction
- correcting the order status to `PAID`
- resolving the customer escalation

---

# Asynchronous Agent Execution

The Customer Escalation WorkGraph supports asynchronous Codex execution.

The Payment, Order, and Support investigators are submitted as separate background jobs through the Flask service.

```text
POST /jobs
```

Each request receives a unique job ID while Codex execution runs as a background task.

This allows independent specialist investigations to be executed separately rather than requiring a single sequential agent execution.

The service also exposes:

```text
GET /jobs/<job_id>
```

for retrieving job state and results.

---

# Codex Service

The local integration service is located at:

```text
codex-n8n-service/codex_service.py
```

It provides the bridge:

```text
n8n → Flask → Codex CLI
```

Codex is invoked using `codex exec`.

The service supports both:

```text
POST /run
```

for synchronous execution and:

```text
POST /jobs
```

for asynchronous background execution.

Agents can be executed in either read-only or workspace-write mode depending on their role in the benchmark.

---

# Independent Verification

A key design principle of both benchmarks is that **the agent does not decide whether it succeeded**.

Each environment contains an independent deterministic Python verifier.

```text
Agent performs task
        │
        ▼
Environment changes
        │
        ▼
Independent verifier
        │
        ├── PASS
        │
        └── FAIL
```

This helps detect situations where an agent claims that a task has been completed even though the resulting environment does not satisfy the benchmark requirements.

---

# Failure Recovery

The WorkGraph includes a verification branch after execution.

If verification succeeds, the benchmark completes.

If verification fails, the failure path can invoke a retry webhook that starts a fresh workflow execution from the initialization stage.

```text
Execution
    │
    ▼
Verifier
    │
    ▼
Verifier Passed?
   / \
 YES  NO
  │    │
  ▼    ▼
Done  Retry Workflow
          │
          ▼
      Retry Webhook
          │
          ▼
     Initialize Case
```

This provides a recovery path for unsuccessful agent executions.

---

# Resettable Benchmark Environments

Both benchmarks include reset scripts.

This allows the same benchmark to be executed repeatedly from a known initial state.

## Reset Production Incident Benchmark

```bash
cd ProductionIncidentMitigationEnv
python3 reset_environment.py
```

## Reset Customer Escalation WorkGraph

```bash
cd CustomerEscalationWorkGraphEnv
python3 reset_environment.py
```

The repository is intentionally stored in the **reset / unsolved state** so that a fresh benchmark run begins with failing verification.

---

# Repository Structure

```text
agentic-benchmark-environment-n8n/
│
├── CustomerEscalationWorkGraphEnv/
│   ├── payments/
│   │   └── transactions.json
│   ├── orders/
│   │   └── orders.json
│   ├── support/
│   │   └── tickets.json
│   ├── policies/
│   │   └── refund_policy.md
│   ├── output/
│   ├── task.md
│   ├── verifier.py
│   └── reset_environment.py
│
├── ProductionIncidentMitigationEnv/
│   ├── data/
│   ├── deployment/
│   ├── logs/
│   ├── tests/
│   ├── app.py
│   ├── orders.py
│   ├── payments.py
│   ├── task.md
│   ├── verifier.py
│   └── reset_environment.py
│
├── codex-n8n-service/
│   └── codex_service.py
│
├── n8n/
│   └── customer-escalation-workgraph.json
│
├── .gitignore
└── README.md
```

---

# Evaluation Approach

The benchmark follows the general evaluation lifecycle:

```text
Environment
    ↓
Task
    ↓
Agent / Agents
    ↓
Actions
    ↓
Environment State
    ↓
Independent Verification
    ↓
PASS / FAIL
    ↓
Recovery / Failure Analysis
```

The purpose is to evaluate more than whether an AI agent can produce a plausible response.

The benchmark instead evaluates whether the agent can:

- investigate relevant evidence
- respect task boundaries
- coordinate across specialized roles
- determine an appropriate action
- modify the environment correctly
- produce independently verifiable results
- recover from unsuccessful execution

---

# Technologies

- **n8n** — workflow and WorkGraph orchestration
- **Codex CLI** — agent execution using `codex exec`
- **Python / Flask** — local Codex execution service
- **Python** — deterministic benchmark verifiers and reset scripts
- **Git / GitHub** — benchmark environment versioning

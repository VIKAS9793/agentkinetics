# AgentKinetics Policy

AgentKinetics is built around durable, local-first, operator-controlled workflow execution.

This file defines the project rules that product and engineering decisions should align with.

## Policy Tenets

### 1. Durable execution beats prompt replay

The system should prefer persisted state, checkpoints, and replayable audit history over transient conversational context.

### 2. Human approval is infrastructure

High-impact state changes should be explicit, auditable, and attributable to an authenticated operator.

### 3. Local-first remains the default

The primary runtime model is local execution with local storage and local control. Cloud integrations may exist later, but they must not become the only supported mode.

### 4. Single source of truth stays explicit

Operational state must remain reconstructible from the authoritative data model instead of being split across hidden caches or frontend-only assumptions.

## Governance Rules

- identity, orchestration, policy, audit, memory, tools, interfaces, and storage should remain cleanly separated
- permissions should be role-based and enforced server-side
- session state should never be treated as purely client-side state
- documentation must track command, route, and path changes as part of the same work

## Product Direction

AgentKinetics is meant to solve the durable execution gap for bounded AI workflows.

It is not a generic chatbot shell and not a cloud-only control plane. The product should continue to favor:

- bounded workflows over unconstrained autonomy
- inspectable evidence over hidden automation
- explicit operator control over silent side effects

## Contribution Guardrail

Do not introduce product or architecture changes that make the system less:

- durable
- auditable
- modular
- local-first

If a change improves capability but weakens one of those four qualities, document the trade-off and record it in an ADR.

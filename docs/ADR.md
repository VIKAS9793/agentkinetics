# Architecture Decision Records

This file records the architectural trade-offs that shaped the current repository state.

Last updated: 2026-04-01

## ADR-01: Use ticket exchange for SSE authentication

Date: 2026-03-30  
Status: accepted

### Context

The browser `EventSource` API cannot attach custom auth headers. Passing the long-lived session token directly in the SSE URL would leak it into request logs and browser-visible URLs.

### Decision

Use a short-lived ticket exchange:

1. authenticated client requests `POST /events/ticket`
2. browser opens `GET /events/stream?ticket=...`
3. server invalidates the ticket on first use

### Why

This avoids URL-based session token exposure without introducing cookie and CSRF complexity into a header-based local auth model.

## ADR-02: Keep logout server-authoritative

Date: 2026-04-01  
Status: accepted

### Context

The UI previously cleared local session state without revoking the server-side session, which made sign-out feel complete when it was not.

### Decision

Make sign-out call `POST /auth/session/logout`, then clear local session state and close live updates.

### Why

Sign-out should revoke the session in the single source of truth, not just erase the browser token.

## ADR-03: Delete unused protocol boundaries until they are real

Date: 2026-03-30  
Status: accepted

### Context

A protocol existed for tool execution without a trustworthy, matching implementation boundary.

### Decision

Remove protocol definitions that do not yet correspond to a real, enforced abstraction.

### Why

False abstraction is worse than no abstraction. The right time to formalize a protocol is when more than one conforming implementation actually exists.

## ADR-04: Allow unauthenticated first-user bootstrap only when no users exist

Date: 2026-03-30  
Status: accepted

### Context

Strict admin-only user creation prevents the system from bootstrapping its first operator on a fresh local install.

### Decision

Allow `POST /auth/local/users` without prior authentication only while the system has zero users. After the first user exists, the route returns to admin-only behavior.

### Why

This keeps first-run local setup workable without shipping a default account or requiring a separate bootstrap secret in the normal local path.

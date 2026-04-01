# Security Policy

AgentKinetics is designed for local-first operation, explicit identity, and auditable workflow control.

## Current Security Posture

### Authentication

- passwords are hashed with PBKDF2-HMAC-SHA256
- each password gets a unique salt
- local identities and sessions are stored in SQLite

### Sessions

- session tokens are high-entropy random values
- session TTL defaults to 12 hours
- server-side session validation happens on every authenticated request
- logout is handled through `POST /auth/session/logout`

### Live Updates

- the UI does not put the session token directly into the SSE URL
- the client first requests `POST /events/ticket`
- the browser then opens `GET /events/stream?ticket=...`
- tickets are short-lived and single-use

## Supported Development Line

| Version | Supported |
| --- | --- |
| `0.1.x` | yes |
| `< 0.1.0` | no |

## Reporting A Vulnerability

If you discover a security issue, report it privately to:

- Vikas Sahani: [vikassahani17@gmail.com](mailto:vikassahani17@gmail.com)

Include:

- the affected route, module, or command
- the impact
- reproduction steps
- a proof of concept if available

## Responsible Disclosure

Please:

1. report privately before public disclosure
2. provide enough detail to reproduce the issue
3. allow time for a fix and verification

## Scope Notes

AgentKinetics currently minimizes attack surface by staying local-first and avoiding third-party auth callbacks, but local apps still need serious security review.

Areas that should remain high priority:

- auth and session handling
- approval authorization
- SSE ticket handling
- audit integrity
- local storage permissions

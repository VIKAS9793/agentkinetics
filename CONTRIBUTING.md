# Contributing to AgentKinetics

Thanks for contributing.

AgentKinetics is a modular monolith. Changes should preserve clear boundaries between contexts instead of leaking behavior across the app.

## Core Engineering Expectations

- keep domain models inside their owning context
- add or update ports before wiring new infrastructure
- route all persistence through the storage gateway or a published repository
- keep UI code out of direct storage access
- favor explicit types, explicit validation, and explicit failure paths

## Repository Shape

Top-level application contexts live under `src/agentkinetics/`:

- `identity`
- `orchestration`
- `policy`
- `audit`
- `memory`
- `tools`
- `interfaces`
- `storage`
- `shared`

## Typical Change Flow

1. Add or update the model in the owning context.
2. Add or update the port in `ports.py` if the boundary changes.
3. Implement the service or adapter logic.
4. Update `storage/schema.py` and `storage/sqlite_gateway.py` if persistence changes.
5. Add tests for the new behavior.
6. Update documentation if commands, routes, or runtime behavior changed.

## Local Development

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,orchestration]"
.\.venv\Scripts\python.exe -m pytest
```

Start the app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn agentkinetics.app:app --host 127.0.0.1 --port 8000
```

## Testing Expectations

- add unit tests for service logic
- add integration tests for route changes
- keep CLI behavior covered when commands change
- update browser-facing text assertions when UI copy changes intentionally

## Documentation Expectations

If you change any of the following, update the docs in the same change:

- setup commands
- runtime ports
- default file paths
- route names
- local test credentials
- architecture or policy behavior

## Review Standard

Good contributions are:

- typed
- modular
- auditable
- local-first
- easy to reason about after six months

## Contact

For major architecture or product-boundary changes:

- Vikas Sahani: [vikassahani17@gmail.com](mailto:vikassahani17@gmail.com)

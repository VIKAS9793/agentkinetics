# AgentKinetics Setup

This document is the canonical local setup guide for the current repository state.

Run every command from the repository root after cloning:

```powershell
git clone https://github.com/VIKAS9793/agentkinetics.git
cd agentkinetics
```

## What Actually Runs

AgentKinetics currently runs as one FastAPI application process.

- Product UI: server-rendered from the FastAPI app
- API: served by the same process
- Database: local SQLite file
- Artifacts: local filesystem directory

There is no separate frontend dev server.

Default local paths are repo-relative:

- database: `data/agentkinetics.sqlite3`
- artifacts: `data/artifacts/`

## Requirements

- Python 3.11 or newer
- Windows PowerShell, macOS Terminal, or Linux shell

If your machine maps `python` to a Windows Store alias, use `py -3.11` on Windows or install Python 3.11 from python.org.

## Windows PowerShell

Create the virtual environment:

```powershell
py -3.11 -m venv .venv
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,orchestration]"
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Start the app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn agentkinetics.app:app --host 127.0.0.1 --port 8000
```

Alternative packaged entrypoint:

```powershell
.\.venv\Scripts\agentkinetics-api.exe
```

## macOS Or Linux

Create the virtual environment:

```bash
python3.11 -m venv .venv
```

Install dependencies:

```bash
./.venv/bin/python -m pip install -e ".[dev,orchestration]"
```

Run tests:

```bash
./.venv/bin/python -m pytest
```

Start the app:

```bash
./.venv/bin/python -m uvicorn agentkinetics.app:app --host 127.0.0.1 --port 8000
```

## Open The App

After the server starts, use:

- Product UI: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/health`
- Admin surface: `http://127.0.0.1:8000/admin`

## First Local Bootstrap

The easiest first-run path is through the product UI.

1. Start the app with one of the commands above.
2. Open `http://127.0.0.1:8000/`.
3. In `Set up local operator access`, create:
   - Username: `admin`
   - Display name: `Admin UI`
   - Password: `correct horse battery staple`
   - Role: `admin`
4. In `Enter the run workspace`, sign in with:
   - Username: `admin`
   - Password: `correct horse battery staple`

These are dummy local-only credentials for development and docs.

## CLI Bootstrap Alternative

If you prefer not to create the first operator in the UI:

```powershell
.\.venv\Scripts\agentkinetics-cli.exe init-db
.\.venv\Scripts\agentkinetics-cli.exe create-user --username admin --password "correct horse battery staple" --display-name "Admin UI" --role admin
```

Then open the product UI and sign in.

## Common Commands

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run one CLI inspection:

```powershell
.\.venv\Scripts\agentkinetics-cli.exe show-run <run_id>
```

Start the app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn agentkinetics.app:app --host 127.0.0.1 --port 8000
```

## Local Runtime Defaults

These values come from `src/agentkinetics/config.py`:

- database path: `data/agentkinetics.sqlite3`
- artifacts path: `data/artifacts/`
- default tenant name: `local-default`
- session TTL: `12` hours

## Troubleshooting

### `python` points to the Windows Store alias

Use:

```powershell
py -3.11 -m venv .venv
```

Then continue with `.\.venv\Scripts\python.exe`.

### Login or bootstrap fails because the user already exists

Create a different username or reset local data.

### Clean local reset

Stop the app, then remove:

- `data/agentkinetics.sqlite3`
- `data/artifacts/`

Restart the app and bootstrap the first operator again.

### `/admin` is not accessible

The admin surface requires an authenticated admin session. Create the operator with role `admin`, then start a session first.

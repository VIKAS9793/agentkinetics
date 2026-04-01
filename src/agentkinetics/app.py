from __future__ import annotations

import uvicorn

from agentkinetics.interfaces.api import create_app


app = create_app()


def main() -> None:
    uvicorn.run("agentkinetics.app:app", host="127.0.0.1", port=8000, reload=False)

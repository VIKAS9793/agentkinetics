from __future__ import annotations

import argparse
import json

from agentkinetics.bootstrap import build_container
from agentkinetics.identity.models import Role
from agentkinetics.shared.errors import DomainError
from agentkinetics.shared.time import to_iso8601


def main() -> None:
    parser = argparse.ArgumentParser(prog="agentkinetics-cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Initialize the SQLite database and default tenant.")

    create_user_parser = subparsers.add_parser("create-user", help="Create a local user.")
    create_user_parser.add_argument("--username", required=True)
    create_user_parser.add_argument("--password", required=True)
    create_user_parser.add_argument("--display-name", required=True)
    create_user_parser.add_argument(
        "--role",
        choices=[role.value for role in Role],
        default=Role.ADMIN.value,
    )

    show_run_parser = subparsers.add_parser("show-run", help="Show a run and its timeline.")
    show_run_parser.add_argument("run_id")

    arguments = parser.parse_args()
    container = build_container()

    try:
        if arguments.command == "init-db":
            tenant = container.identity_service.ensure_default_tenant(
                name=container.config.default_tenant_name
            )
            print(json.dumps({"tenant_id": tenant.id, "tenant_name": tenant.name}, indent=2))
            return
        if arguments.command == "create-user":
            user = container.identity_service.create_local_user(
                username=arguments.username,
                password=arguments.password,
                display_name=arguments.display_name,
                role=Role(arguments.role),
            )
            print(
                json.dumps(
                    {
                        "user_id": user.id,
                        "username": user.username,
                        "role": user.role.value,
                    },
                    indent=2,
                )
            )
            return
        if arguments.command == "show-run":
            view = container.orchestration_service.get_run_view(run_id=arguments.run_id)
            print(
                json.dumps(
                    {
                        "run": {
                            "id": view.run.id,
                            "status": view.run.status.value,
                            "objective": view.run.objective,
                            "created_at": to_iso8601(view.run.created_at),
                            "updated_at": to_iso8601(view.run.updated_at),
                        },
                        "audit_events": [
                            {
                                "event_type": event.event_type,
                                "created_at": to_iso8601(event.created_at),
                            }
                            for event in view.audit_events
                        ],
                    },
                    indent=2,
                )
            )
            return
    except DomainError as exc:
        parser.exit(status=1, message=f"{exc}\n")

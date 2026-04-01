from __future__ import annotations

from dataclasses import dataclass

from agentkinetics.audit.service import AuditService
from agentkinetics.config import AppConfig
from agentkinetics.identity.service import IdentityService, LocalAuthProvider
from agentkinetics.memory.service import MemoryService
from agentkinetics.orchestration.langgraph_engine import LangGraphWorkflowEngine
from agentkinetics.orchestration.service import OrchestrationService
from agentkinetics.policy.service import PolicyService
from agentkinetics.storage.db import Database
from agentkinetics.storage.file_artifacts import LocalArtifactStore
from agentkinetics.storage.sqlite_gateway import SQLiteGateway
from agentkinetics.tools.service import ToolService


@dataclass(frozen=True)
class AppContainer:
    config: AppConfig
    database: Database
    gateway: SQLiteGateway
    identity_service: IdentityService
    orchestration_service: OrchestrationService
    memory_service: MemoryService
    policy_service: PolicyService
    audit_service: AuditService
    tool_service: ToolService
    artifact_store: LocalArtifactStore


def build_container(config: AppConfig | None = None) -> AppContainer:
    app_config = config or AppConfig()
    database = Database(path=app_config.database_path)
    database.initialize()
    gateway = SQLiteGateway(database=database)
    artifact_store = LocalArtifactStore(root=app_config.artifacts_dir)
    audit_service = AuditService(sink=gateway)
    policy_service = PolicyService(repository=gateway, audit_service=audit_service)
    workflow_engine = LangGraphWorkflowEngine()
    auth_provider = LocalAuthProvider(
        repository=gateway,
        session_ttl_hours=app_config.session_ttl_hours,
    )
    identity_service = IdentityService(repository=gateway, auth_provider=auth_provider)
    identity_service.ensure_default_tenant(name=app_config.default_tenant_name)
    memory_service = MemoryService(repository=gateway)
    orchestration_service = OrchestrationService(
        run_repository=gateway,
        checkpoint_store=gateway,
        approval_repository=gateway,
        policy_evaluator=policy_service,
        audit_service=audit_service,
        workflow_engine=workflow_engine,
    )
    tool_service = ToolService(audit_service=audit_service)
    return AppContainer(
        config=app_config,
        database=database,
        gateway=gateway,
        identity_service=identity_service,
        orchestration_service=orchestration_service,
        memory_service=memory_service,
        policy_service=policy_service,
        audit_service=audit_service,
        tool_service=tool_service,
        artifact_store=artifact_store,
    )

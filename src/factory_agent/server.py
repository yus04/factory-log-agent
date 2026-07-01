"""A2A プロトコルでエージェントを公開する Starlette サーバー。

`a2a-sdk` が提供する `A2AStarletteApplication` をベースに、Microsoft Agent Framework の
エージェントを `A2AExecutor` 経由で A2A エンドポイントとして公開する。
"""

from __future__ import annotations

import os

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_framework.a2a import A2AExecutor
from dotenv import load_dotenv
from starlette.applications import Starlette

from .agent import AGENT_NAME, build_agent


def _build_agent_card(public_url: str) -> AgentCard:
    """A2A クライアントがエージェントを発見するためのエージェントカードを構築する。"""
    skills = [
        AgentSkill(
            id="equipment_diagnostics",
            name="Equipment failure diagnostics",
            description=(
                "Analyze factory equipment incident logs to assess machine health "
                "and diagnose the root cause of failures."
            ),
            tags=["factory", "maintenance", "diagnostics", "predictive maintenance"],
            examples=[
                "Show me the failure trend for PUMP-001",
                "Which machine is the most costly?",
                "What is the main root cause of sensor anomalies?",
                "Analyze the top 5 incidents with the longest downtime",
            ],
        ),
        AgentSkill(
            id="log_analytics",
            name="Log aggregation and search",
            description=(
                "Aggregate and search logs by incident type, machine, "
                "failure code, time period, and more."
            ),
            tags=["analytics", "search", "aggregation"],
            examples=[
                "List the machine_failure incidents that occurred on Line A",
                "What is the total number of incidents and total downtime?",
            ],
        ),
    ]

    return AgentCard(
        name=AGENT_NAME,
        description=(
            "An AI agent that analyzes factory equipment logs (failures, sensor "
            "anomalies, maintenance events) to assess machine health and diagnose "
            "failure causes. Runs on Foundry Local."
        ),
        url=public_url,
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=skills,
        supports_authenticated_extended_card=True,
    )


def build_app() -> Starlette:
    """A2A エンドポイントを公開する Starlette アプリケーションを構築する。"""
    public_url = os.environ.get("A2A_PUBLIC_URL", "http://localhost:9999/")
    agent_card = _build_agent_card(public_url)

    request_handler = DefaultRequestHandler(
        agent_executor=A2AExecutor(build_agent(), stream=True),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    return server.build()


def run() -> None:
    """A2A サーバーを起動する (コンソールスクリプトのエントリポイント)。"""
    load_dotenv()
    host = os.environ.get("A2A_HOST", "0.0.0.0")
    port = int(os.environ.get("A2A_PORT", "9999"))

    print(f"[factory-agent] A2A サーバーを起動します: http://{host}:{port}/")
    print(f"[factory-agent] エージェントカード: http://{host}:{port}/.well-known/agent-card.json")
    uvicorn.run(build_app(), host=host, port=port)


if __name__ == "__main__":
    run()

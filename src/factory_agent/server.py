"""A2A プロトコルでエージェントを公開する Starlette サーバー。

`a2a-sdk` (v1.x) が提供する Starlette/ASGI ルートヘルパーをベースに、Microsoft Agent
Framework のエージェントを `A2AExecutor` 経由で A2A エンドポイントとして公開する。
"""

from __future__ import annotations

import os
import re

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from agent_framework.a2a import A2AExecutor
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from .agent import AGENT_NAME, build_agent


class FilteredA2AExecutor(A2AExecutor):
    async def handle_events(self, item, updater, streamed_artifact_ids=None, default_artifact_id=None):
        contents = getattr(item, "contents", [])
        for content in contents:
            if hasattr(content, "text") and content.text:
                content.text = re.sub(r"<tool_call>.*?</tool_call>", "", content.text, flags=re.DOTALL).strip()
        await super().handle_events(item, updater, streamed_artifact_ids, default_artifact_id)


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
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(url=public_url, protocol_binding="JSONRPC"),
        ],
        skills=skills,
    )


def build_app() -> Starlette:
    """A2A エンドポイントを公開する Starlette アプリケーションを構築する。"""
    public_url = os.environ.get("A2A_PUBLIC_URL", "http://localhost:9999/")
    agent_card = _build_agent_card(public_url)

    request_handler = DefaultRequestHandler(
        agent_executor=FilteredA2AExecutor(build_agent(), stream=True),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    app = Starlette(
        routes=[
            *create_agent_card_routes(agent_card),
            *create_jsonrpc_routes(request_handler, "/", enable_v0_3_compat=True),
        ]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


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

"""A2A プロトコルでエージェントを公開する Starlette サーバー。

`a2a-sdk` が提供する Starlette/ASGI サーバーをベースに、Microsoft Agent Framework の
エージェントを `A2AExecutor` 経由で A2A エンドポイントとして公開する。
"""

from __future__ import annotations

import os

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from agent_framework.a2a import A2AExecutor
from dotenv import load_dotenv
from starlette.applications import Starlette

from .agent import AGENT_NAME, build_agent


def _build_agent_card(public_url: str) -> AgentCard:
    """A2A クライアントがエージェントを発見するためのエージェントカードを構築する。"""
    skills = [
        AgentSkill(
            id="equipment_diagnostics",
            name="設備故障診断",
            description=(
                "工場設備のインシデントログを解析し、機械の状態評価や故障の根本原因を診断する。"
            ),
            tags=["factory", "maintenance", "diagnostics", "故障診断", "予知保全"],
            examples=[
                "PUMP-001 の故障傾向を教えて",
                "最もコストがかかっている機械はどれ?",
                "センサー異常の主な根本原因は?",
                "ダウンタイムが長いインシデント上位5件を分析して",
            ],
        ),
        AgentSkill(
            id="log_analytics",
            name="ログ集計・検索",
            description="インシデント種別・機械・故障コード・期間などでログを集計・検索する。",
            tags=["analytics", "search", "集計", "検索"],
            examples=[
                "Line A で発生した machine_failure を一覧化して",
                "全体のインシデント件数と総ダウンタイムは?",
            ],
        ),
    ]

    return AgentCard(
        name=AGENT_NAME,
        description=(
            "工場設備ログ (故障・センサー異常・保全イベント) を解析し、機械の状態や"
            "故障原因を診断する AI エージェント。Foundry Local 上で動作する。"
        ),
        version="0.1.0",
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
        agent_executor=A2AExecutor(build_agent(), stream=True),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    return Starlette(
        routes=[
            *create_agent_card_routes(agent_card),
            *create_jsonrpc_routes(request_handler, "/"),
        ]
    )


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

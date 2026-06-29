"""A2A 経由で公開エージェントを呼び出すサンプルクライアント。

A2A サーバー (`factory-agent-server`) が起動している状態で実行すると、
エージェントカードを取得し、リモートエージェントに質問を送信する。

使い方:
    uv run factory-agent-client "PUMP-001 の故障傾向を教えて"
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx
from a2a.client import A2ACardResolver
from agent_framework.a2a import A2AAgent
from dotenv import load_dotenv

DEFAULT_QUERY = "工場全体のインシデント状況を要約し、最も注意すべき機械を教えてください。"


async def _main(query: str) -> None:
    load_dotenv()
    base_url = os.environ.get("A2A_PUBLIC_URL", "http://localhost:9999/")

    async with httpx.AsyncClient(timeout=120.0) as http_client:
        resolver = A2ACardResolver(httpx_client=http_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        print(f"エージェントを発見しました: {agent_card.name}\n")

        async with A2AAgent(name=agent_card.name, agent_card=agent_card, url=base_url) as agent:
            print(f"質問: {query}\n回答: ", end="", flush=True)
            stream = agent.run(query, stream=True)
            async for update in stream:
                for content in update.contents:
                    if getattr(content, "text", None):
                        print(content.text, end="", flush=True)
            print()


def run() -> None:
    """コンソールスクリプトのエントリポイント。"""
    query = " ".join(sys.argv[1:]).strip() or DEFAULT_QUERY
    asyncio.run(_main(query))


if __name__ == "__main__":
    run()

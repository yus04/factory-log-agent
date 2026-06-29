"""ローカルでエージェントを対話実行するための簡易 CLI (A2A を使わず直接実行)。

A2A サーバーを立てる前の動作確認や、Foundry Local 単体での挙動確認に使う。
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from .agent import build_agent


async def _main() -> None:
    load_dotenv()
    print("Foundry Local 上でエージェントを初期化しています (初回はモデル取得に時間がかかります)...")
    agent = build_agent()
    print("準備完了。質問を入力してください。終了するには 'exit' または 'quit' を入力します。\n")

    while True:
        try:
            query = input("あなた> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            break

        print("エージェント> ", end="", flush=True)
        async for chunk in agent.run(query, stream=True):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print("\n")


def run() -> None:
    """コンソールスクリプトのエントリポイント。"""
    asyncio.run(_main())


if __name__ == "__main__":
    run()

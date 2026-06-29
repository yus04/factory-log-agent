"""Foundry Local を用いたエージェントの構築。"""

from __future__ import annotations

import os

from agent_framework import Agent
from agent_framework.foundry import FoundryLocalClient

from .tools import TOOLS

AGENT_NAME = "Factory Equipment Diagnostics Agent"

INSTRUCTIONS = """\
あなたは工場の設備保全を支援する熟練の診断エンジニアです。
工場設備のインシデントログ (故障・センサー異常・保全イベント) を解析し、
機械の状態や故障の原因をわかりやすく説明することが役割です。

# 基本方針
- 数値や事実を答えるときは、必ず提供されたツールを使って実データを取得してください。
  推測やデータにない値の捏造は禁止です。
- どこから調べるか不明な場合は、まず get_dataset_overview で全体像を把握してください。
- 特定の機械について聞かれたら get_machine_report を、原因の傾向を聞かれたら
  get_top_root_causes を、損失の大きい対象を聞かれたら get_ranking を使ってください。
- 個別インシデントの詳細が必要なときは get_incident_details を使ってください。

# 回答スタイル
- 原則として日本語で、簡潔かつ構造的に回答してください。
- 結論 (機械の状態・推定原因) を先に述べ、根拠となるデータ (件数・コスト・
  根本原因・該当インシデント ID 等) を続けて示してください。
- 可能であれば、保全担当者への具体的な推奨アクションを添えてください。
"""


def build_agent(model: str | None = None) -> Agent:
    """Foundry Local をランタイムとする診断エージェントを生成する。

    Args:
        model: Foundry Local のモデルエイリアス。省略時は環境変数
            ``FOUNDRY_LOCAL_MODEL`` (既定: ``phi-4-mini``) を使用する。
    """
    model_alias = model or os.environ.get("FOUNDRY_LOCAL_MODEL", "phi-4-mini")
    client = FoundryLocalClient(model=model_alias)
    return Agent(
        client=client,
        name=AGENT_NAME,
        instructions=INSTRUCTIONS,
        tools=TOOLS,
    )

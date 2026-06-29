"""エージェントが利用する関数ツール群。

各関数は型ヒントと docstring を持ち、Microsoft Agent Framework が自動的に
ツールスキーマ (function calling 用) を生成する。戻り値は LLM が解釈しやすいよう
日本語キーの JSON 文字列に統一している。
"""

from __future__ import annotations

import json
from typing import Annotated

from pydantic import Field

from . import data


def _dump(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def get_dataset_overview() -> str:
    """工場設備ログ全体のサマリーを取得する。

    総インシデント件数、対象期間、機械台数、インシデント種別ごとの件数、
    総ダウンタイム・総コストなどの全体像を返す。どこから分析を始めるか
    迷ったときに最初に呼び出すとよい。
    """
    return _dump(data.dataset_overview())


def list_machines() -> str:
    """登録されている全機械の一覧と、機械ごとのインシデント集計を取得する。

    機械 ID・種別・設置場所・インシデント件数・故障件数・総ダウンタイム・
    総コストを、コストの高い順に返す。
    """
    return _dump(data.list_machines())


def get_machine_report(
    machine_id: Annotated[str, Field(description="対象の機械 ID (例: CNC-001, ROB-002)")],
) -> str:
    """特定の機械についての詳細レポートを取得する。

    インシデント種別ごとの内訳、総ダウンタイム・総コスト、主な根本原因の上位、
    直近のインシデント一覧を返す。特定機械の状態や故障傾向を調べる際に使う。
    """
    return _dump(data.machine_report(machine_id))


def search_incidents(
    incident_type: Annotated[
        str | None,
        Field(description="インシデント種別。machine_failure / sensor_anomaly / maintenance_event のいずれか"),
    ] = None,
    machine_id: Annotated[str | None, Field(description="機械 ID で絞り込む (例: PUMP-001)")] = None,
    machine_type: Annotated[str | None, Field(description="機械種別の部分一致 (例: CNC, Robotic)")] = None,
    failure_code: Annotated[str | None, Field(description="故障コードで絞り込む (例: MF-004, SA-006)")] = None,
    location: Annotated[str | None, Field(description="設置場所の部分一致 (例: Line A)")] = None,
    min_downtime_minutes: Annotated[
        float | None, Field(description="この分数以上のダウンタイムを持つインシデントのみ")
    ] = None,
    limit: Annotated[int, Field(description="返す最大件数 (1-100)")] = 20,
) -> str:
    """条件を指定してインシデントを検索する。

    指定した条件 (省略可) で工場ログを絞り込み、新しい順にインシデント概要を返す。
    すべて省略すると最新のインシデントを返す。
    """
    return _dump(
        data.search_incidents(
            incident_type=incident_type,
            machine_id=machine_id,
            machine_type=machine_type,
            failure_code=failure_code,
            location=location,
            min_downtime_minutes=min_downtime_minutes,
            limit=limit,
        )
    )


def get_incident_details(
    incident_id: Annotated[str, Field(description="インシデント ID (例: INC-0007)")],
) -> str:
    """1 件のインシデントについて、すべての項目 (センサー値・対応内容・根本原因など) を取得する。"""
    return _dump(data.incident_details(incident_id))


def get_top_root_causes(
    incident_type: Annotated[
        str | None,
        Field(description="特定のインシデント種別に絞る場合に指定 (省略可)"),
    ] = None,
    limit: Annotated[int, Field(description="返す根本原因の数 (1-50)")] = 10,
) -> str:
    """発生頻度の高い根本原因 (root_cause) を集計して取得する。

    故障やセンサー異常の主な原因を把握したいときに使う。
    """
    return _dump(data.top_root_causes(incident_type=incident_type, limit=limit))


def get_ranking(
    by: Annotated[str, Field(description="集計指標: cost (コスト) または downtime (ダウンタイム)")] = "cost",
    group_by: Annotated[
        str, Field(description="集計単位: machine / machine_type / incident")
    ] = "machine",
    limit: Annotated[int, Field(description="返す件数 (1-50)")] = 10,
) -> str:
    """コストまたはダウンタイムが大きい順にランキングを取得する。

    どの機械・種別・インシデントが最も損失に寄与しているかを把握する際に使う。
    """
    return _dump(data.ranking(by=by, group_by=group_by, limit=limit))


# エージェントに登録するツールの一覧
TOOLS = [
    get_dataset_overview,
    list_machines,
    get_machine_report,
    search_incidents,
    get_incident_details,
    get_top_root_causes,
    get_ranking,
]

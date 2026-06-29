"""工場設備ログ CSV の読み込みと集計処理。

エージェントのツール (`tools.py`) から呼び出される純粋なデータ解析ロジックを
ここに集約する。LLM やエージェントフレームワークには依存しない。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

# プロジェクトルート (このファイルから 3 つ上: src/factory_agent/data.py -> リポジトリ直下)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CSV = "factory-log-data/factory_equipment_log.csv"

# 集計に利用する数値列
_NUMERIC_COLUMNS = ("sensor_value", "downtime_minutes", "cost_estimate")


def _resolve_csv_path() -> Path:
    """環境変数 ``FACTORY_LOG_CSV`` または既定パスから CSV のパスを解決する。"""
    raw = os.environ.get("FACTORY_LOG_CSV", _DEFAULT_CSV)
    path = Path(raw)
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    return path


@lru_cache(maxsize=1)
def load_data() -> pd.DataFrame:
    """工場ログ CSV を読み込み、整形済みの DataFrame を返す (結果はキャッシュ)。"""
    path = _resolve_csv_path()
    if not path.exists():
        raise FileNotFoundError(
            f"工場ログ CSV が見つかりません: {path} "
            "(環境変数 FACTORY_LOG_CSV で場所を指定できます)"
        )

    df = pd.read_csv(path)
    for column in _NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in ("incident_datetime", "resolved_datetime"):
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    return df


def dataset_overview() -> dict:
    """データセット全体のサマリー (件数・期間・コスト・ダウンタイムなど)。"""
    df = load_data()
    incident_types = df["incident_type"].value_counts().to_dict()
    statuses = df["resolution_status"].value_counts().to_dict()

    return {
        "総インシデント件数": int(len(df)),
        "対象期間": {
            "開始": _fmt_dt(df["incident_datetime"].min()),
            "終了": _fmt_dt(df["incident_datetime"].max()),
        },
        "機械台数": int(df["machine_id"].nunique()),
        "機械種別数": int(df["machine_type"].nunique()),
        "インシデント種別ごとの件数": incident_types,
        "解決状況ごとの件数": statuses,
        "総ダウンタイム_分": _safe_round(df["downtime_minutes"].sum()),
        "平均ダウンタイム_分": _safe_round(df["downtime_minutes"].mean()),
        "総コスト見積": _safe_round(df["cost_estimate"].sum()),
        "平均コスト見積": _safe_round(df["cost_estimate"].mean()),
    }


def list_machines() -> list[dict]:
    """機械ごとの基本情報とインシデント集計の一覧。"""
    df = load_data()
    rows: list[dict] = []
    for machine_id, group in df.groupby("machine_id"):
        failures = int((group["incident_type"] == "machine_failure").sum())
        rows.append(
            {
                "machine_id": machine_id,
                "machine_type": _first(group["machine_type"]),
                "location": _first(group["location"]),
                "インシデント件数": int(len(group)),
                "故障件数": failures,
                "総ダウンタイム_分": _safe_round(group["downtime_minutes"].sum()),
                "総コスト見積": _safe_round(group["cost_estimate"].sum()),
            }
        )
    rows.sort(key=lambda r: r["総コスト見積"] or 0, reverse=True)
    return rows


def machine_report(machine_id: str) -> dict:
    """特定の機械についての詳細レポート。"""
    df = load_data()
    group = df[df["machine_id"].str.casefold() == machine_id.casefold()]
    if group.empty:
        return {"error": f"機械 ID '{machine_id}' のインシデントは見つかりませんでした。"}

    root_causes = group["root_cause"].value_counts().head(5).to_dict()
    recent = (
        group.sort_values("incident_datetime", ascending=False)
        .head(10)
        .apply(_incident_summary, axis=1)
        .tolist()
    )

    return {
        "machine_id": _first(group["machine_id"]),
        "machine_type": _first(group["machine_type"]),
        "location": _first(group["location"]),
        "インシデント件数": int(len(group)),
        "故障件数": int((group["incident_type"] == "machine_failure").sum()),
        "センサー異常件数": int((group["incident_type"] == "sensor_anomaly").sum()),
        "保全イベント件数": int((group["incident_type"] == "maintenance_event").sum()),
        "総ダウンタイム_分": _safe_round(group["downtime_minutes"].sum()),
        "総コスト見積": _safe_round(group["cost_estimate"].sum()),
        "主な根本原因_上位5件": root_causes,
        "直近のインシデント": recent,
    }


def search_incidents(
    incident_type: str | None = None,
    machine_id: str | None = None,
    machine_type: str | None = None,
    failure_code: str | None = None,
    location: str | None = None,
    min_downtime_minutes: float | None = None,
    limit: int = 20,
) -> list[dict]:
    """条件でインシデントを絞り込み、概要のリストを返す。"""
    df = load_data()
    mask = pd.Series(True, index=df.index)

    if incident_type:
        mask &= df["incident_type"].str.casefold() == incident_type.casefold()
    if machine_id:
        mask &= df["machine_id"].str.casefold() == machine_id.casefold()
    if machine_type:
        mask &= df["machine_type"].str.contains(machine_type, case=False, na=False)
    if failure_code:
        mask &= df["failure_code"].str.casefold() == failure_code.casefold()
    if location:
        mask &= df["location"].str.contains(location, case=False, na=False)
    if min_downtime_minutes is not None:
        mask &= df["downtime_minutes"] >= float(min_downtime_minutes)

    matched = df[mask].sort_values("incident_datetime", ascending=False)
    limit = max(1, min(int(limit), 100))
    return matched.head(limit).apply(_incident_summary, axis=1).tolist()


def incident_details(incident_id: str) -> dict:
    """1 件のインシデントの全項目を返す。"""
    df = load_data()
    row = df[df["incident_id"].str.casefold() == incident_id.casefold()]
    if row.empty:
        return {"error": f"インシデント ID '{incident_id}' は見つかりませんでした。"}

    record = row.iloc[0].to_dict()
    return {key: _to_native(value) for key, value in record.items()}


def top_root_causes(incident_type: str | None = None, limit: int = 10) -> list[dict]:
    """発生頻度の高い根本原因を集計する。"""
    df = load_data()
    if incident_type:
        df = df[df["incident_type"].str.casefold() == incident_type.casefold()]

    limit = max(1, min(int(limit), 50))
    counts = df["root_cause"].value_counts().head(limit)
    return [{"root_cause": cause, "件数": int(count)} for cause, count in counts.items()]


def ranking(by: str = "cost", group_by: str = "machine", limit: int = 10) -> list[dict]:
    """コストまたはダウンタイムの大きい順にランキングする。

    Args:
        by: ``cost`` (コスト見積) または ``downtime`` (ダウンタイム分)。
        group_by: ``machine`` / ``machine_type`` / ``incident`` のいずれか。
        limit: 返す件数。
    """
    df = load_data()
    metric_column = "downtime_minutes" if by.lower().startswith("down") else "cost_estimate"
    metric_label = "ダウンタイム_分" if metric_column == "downtime_minutes" else "コスト見積"
    limit = max(1, min(int(limit), 50))

    group_by = group_by.lower()
    if group_by == "incident":
        ordered = df.sort_values(metric_column, ascending=False).head(limit)
        results = []
        for _, row in ordered.iterrows():
            summary = _incident_summary(row)
            summary[metric_label] = _to_native(row[metric_column])
            results.append(summary)
        return results

    key = "machine_type" if group_by == "machine_type" else "machine_id"
    grouped = (
        df.groupby(key)[metric_column].sum().sort_values(ascending=False).head(limit)
    )
    return [{key: name, f"合計{metric_label}": _safe_round(value)} for name, value in grouped.items()]


# --- 内部ヘルパー -----------------------------------------------------------


def _incident_summary(row: pd.Series) -> dict:
    return {
        "incident_id": _to_native(row.get("incident_id")),
        "machine_id": _to_native(row.get("machine_id")),
        "machine_type": _to_native(row.get("machine_type")),
        "incident_type": _to_native(row.get("incident_type")),
        "failure_code": _to_native(row.get("failure_code")),
        "発生日時": _fmt_dt(row.get("incident_datetime")),
        "概要": _to_native(row.get("failure_description")),
        "ダウンタイム_分": _to_native(row.get("downtime_minutes")),
        "コスト見積": _to_native(row.get("cost_estimate")),
        "根本原因": _to_native(row.get("root_cause")),
        "解決状況": _to_native(row.get("resolution_status")),
    }


def _first(series: pd.Series):
    return _to_native(series.iloc[0]) if len(series) else None


def _fmt_dt(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _safe_round(value, digits: int = 2):
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _to_native(value):
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if hasattr(value, "item"):
        return value.item()
    return value

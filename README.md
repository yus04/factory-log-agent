# 工場設備ログ診断エージェント (Factory Equipment Diagnostics Agent)

工場設備のインシデントログ (故障・センサー異常・保全イベント) を解析し、**機械の状態評価**や
**故障の根本原因の診断**を行う AI エージェントです。LLM ランタイムに **Foundry Local**、
エージェントフレームワークに **Microsoft Agent Framework** を採用し、構築したエージェントを
**A2A (Agent-to-Agent) プロトコル**で外部公開します。

## 技術スタック

| 項目 | 採用技術 |
| --- | --- |
| LLM ランタイム | [Foundry Local](https://learn.microsoft.com/azure/ai-foundry/foundry-local/) (ローカルでモデルを実行) |
| エージェントフレームワーク | [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/) (Python) |
| エージェント公開 | A2A プロトコル ([`a2a-sdk`](https://pypi.org/project/a2a-sdk/) + Starlette/ASGI) |
| 言語・パッケージ管理 | Python 3.10+ / [uv](https://docs.astral.sh/uv/) |
| データ解析 | pandas |

## アーキテクチャ

```
                 A2A (JSON-RPC over HTTP)
   A2A クライアント  ───────────────▶  Starlette サーバー (server.py)
                                              │  A2AExecutor
                                              ▼
                                   Agent (Microsoft Agent Framework)
                                              │  function calling
                          ┌───────────────────┼───────────────────┐
                          ▼                                        ▼
                  Foundry Local (LLM)                     ツール群 (tools.py)
                  例: phi-4-mini                                   │
                                                                   ▼
                                                  工場ログ解析 (data.py / pandas)
                                                  factory_equipment_log.csv
```

エージェントは LLM が直接 CSV を読むのではなく、登録された**関数ツール**を function calling で
呼び出して実データを集計・検索します。これにより、推測ではなくログに基づいた回答を返します。

### 主なツール

| ツール | 役割 |
| --- | --- |
| `get_dataset_overview` | データ全体のサマリー (件数・期間・総ダウンタイム・総コスト等) |
| `list_machines` | 全機械の一覧とインシデント集計 |
| `get_machine_report` | 特定機械の状態・故障傾向・主な根本原因 |
| `search_incidents` | 種別・機械・故障コード・期間などでインシデントを検索 |
| `get_incident_details` | 個別インシデントの全項目を取得 |
| `get_top_root_causes` | 発生頻度の高い根本原因を集計 |
| `get_ranking` | コスト/ダウンタイムの大きい順にランキング |

## ディレクトリ構成

```
maf-foundry-local/
├── factory-log-data/
│   └── factory_equipment_log.csv   # 解析対象の工場ログ
├── src/factory_agent/
│   ├── data.py        # CSV 読み込み・集計ロジック (pandas)
│   ├── tools.py       # エージェント用の関数ツール
│   ├── agent.py       # Foundry Local を使ったエージェント構築
│   ├── server.py      # A2A サーバー (Starlette)
│   ├── chat.py        # ローカル対話 CLI (A2A なしで動作確認)
│   └── client.py      # A2A クライアントのサンプル
├── pyproject.toml
├── .env.example
└── README.md
```

## 事前準備

### 1. Foundry Local のインストール

ローカルで LLM を実行するため、Foundry Local をインストールし、サービスを起動できる状態にします。

- インストール手順: [Foundry Local の概要](https://learn.microsoft.com/azure/ai-foundry/foundry-local/get-started)
- 動作確認:
  ```bash
  foundry --version
  foundry service status
  ```

> ツール呼び出し (function calling) に対応したモデルが必要です。既定では `phi-4-mini` を使用します。
> 初回実行時はモデルのダウンロードと初期化のため時間がかかります。

### 2. uv のインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 依存関係のインストール

```bash
cd maf-foundry-local
uv sync
```

### 4. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、必要に応じて値を変更します。

```bash
cp .env.example .env
```

| 変数 | 既定値 | 説明 |
| --- | --- | --- |
| `FOUNDRY_LOCAL_MODEL` | `phi-4-mini` | Foundry Local のモデルエイリアス |
| `FACTORY_LOG_CSV` | `factory-log-data/factory_equipment_log.csv` | 解析対象 CSV のパス |
| `A2A_HOST` | `0.0.0.0` | A2A サーバーの待ち受けホスト |
| `A2A_PORT` | `9999` | A2A サーバーの待ち受けポート |
| `A2A_PUBLIC_URL` | `http://localhost:9999/` | エージェントカード/クライアントが参照する公開 URL |

## 利用手順

### A2A サーバーとして公開する

```bash
uv run factory-agent-server
```

起動すると以下が利用可能になります。

- エージェントカード: `http://localhost:9999/.well-known/agent-card.json`
- A2A エンドポイント (JSON-RPC): `http://localhost:9999/`

### A2A クライアントから呼び出す

別のターミナルで、付属のサンプルクライアントを実行します。

```bash
uv run factory-agent-client "PUMP-001 の故障傾向を教えて"
```

引数を省略すると、全体状況を要約するデフォルトの質問が送信されます。

`curl` でエージェントカードを取得する例:

```bash
curl http://localhost:9999/.well-known/agent-card.json
```

### ローカルで対話実行する (A2A なし)

A2A を介さず、エージェントの挙動を直接確認したい場合に使います。

```bash
uv run factory-agent-chat
```

## 質問例

- 「工場全体のインシデント状況を要約して」
- 「PUMP-001 の状態と主な故障原因を教えて」
- 「最もコストがかかっている機械はどれ?」
- 「センサー異常の主な根本原因の上位は?」
- 「Line A で発生した machine_failure を一覧化して」
- 「ダウンタイムが長いインシデント上位5件を分析して」

## ライセンス / 注意事項

本プロジェクトはサンプル実装です。Microsoft Agent Framework を非 Azure / サードパーティの
モデルやシステムと組み合わせて利用する場合は、各サービスのライセンスとデータ取り扱いポリシーを
確認のうえ、自己責任でご利用ください。

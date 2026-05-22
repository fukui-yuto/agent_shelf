# 専門特化 AI エージェントフレームワーク 設計仕様書

**バージョン**: 0.1.0-draft  
**作成日**: 2026-05-23  
**ステータス**: Draft（要確認事項あり）

---

## 1. 概要

### 1.1 目的

特定のディレクトリ構造を配置するだけで、そのドメインに特化した AI エージェントとして動作するフレームワークを構築する。ドメイン定義に設定ファイルを必要とせず、ディレクトリ構造の「慣習」のみで専門エージェントが自動的に成立する。

### 1.2 基本コンセプト

```
agents/
└── vmware-ops/          ← このディレクトリ名がエージェント名になる
    ├── knowledge/        ← RAGのナレッジベース（ドキュメント群）
    ├── skills/           ← 実行可能なツール・スキル定義
    └── prompts/          ← システムプロンプト・ペルソナ定義
```

ディレクトリを置いて起動するだけで、そのエージェントが CLI / Web UI / API から呼び出せる状態になる。

---

## 2. システムアーキテクチャ

### 2.1 全体構成図

```
┌─────────────────────────────────────────────────────┐
│                   Interface Layer                    │
│          CLI         Web UI        REST API          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                  Agent Router                        │
│   - エージェント一覧の自動検出                          │
│   - リクエストを対象エージェントへルーティング             │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                 Agent Runtime                        │
│                                                      │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  RAG Engine │  │  Skill   │  │ Prompt Manager │  │
│  │  (Retrieval)│  │ Executor │  │ (Persona/Sys)  │  │
│  └─────────────┘  └──────────┘  └────────────────┘  │
│                                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │              LLM Adapter                        │ │
│  │   Claude / OpenAI / Ollama（切り替え可能）         │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│               Agent Directory                        │
│   agents/{agent-name}/knowledge/                     │
│                       skills/                        │
│                       prompts/                       │
└─────────────────────────────────────────────────────┘
```

### 2.2 コンポーネント責務

| コンポーネント | 責務 |
|---|---|
| Agent Router | `agents/` 配下のディレクトリを走査してエージェントを自動登録 |
| RAG Engine | `knowledge/` 配下のドキュメントをインデックス化し、クエリ時に関連チャンクを取得 |
| Skill Executor | `skills/` 配下の定義を読み込み、LLM の Tool Call として登録・実行 |
| Prompt Manager | `prompts/` 配下のファイルを合成してシステムプロンプトを構築 |
| LLM Adapter | Claude / OpenAI / Ollama を統一インターフェースで抽象化 |

---

## 3. ディレクトリ構造仕様

### 3.1 エージェントディレクトリの慣習

```
agents/
└── {agent-name}/
    ├── knowledge/          # RAGソース（必須ではない）
    │   ├── *.md
    │   ├── *.pdf
    │   ├── *.txt
    │   └── **/*.{md,pdf,txt,html}  # サブディレクトリも再帰的にインデックス化
    ├── skills/             # ツール定義（必須ではない）
    │   ├── {skill-name}.py       # Python実行スキル
    │   ├── {skill-name}.sh       # シェルスクリプトスキル
    │   └── {skill-name}.json     # 外部API呼び出しスキル（MCP互換）
    └── prompts/            # プロンプト定義（必須ではない）
        ├── system.md             # システムプロンプト（なければデフォルト使用）
        └── *.md                  # 追加コンテキスト（全てマージされる）
```

**ルール**:
- `{agent-name}` がそのままエージェントの識別子 / 表示名になる
- 3つのサブディレクトリはすべて省略可能。空ディレクトリでも「エージェント」として認識される
- ディレクトリ名に特殊文字（スペース以外）は使用可能。スペースはハイフンに正規化

### 3.2 スキル定義仕様

#### Python スキル（`.py`）

```python
# skills/get_vm_status.py
# ---
# description: 指定したVM名の稼働ステータスを返す
# parameters:
#   vm_name: string - VMの名前
# ---

def run(vm_name: str) -> dict:
    # フレームワークがこの関数を呼び出す
    ...
    return {"status": "running", "cpu_usage": 12.5}
```

ファイル先頭のコメントブロック（`# ---` 区切り）がツール定義として自動解析される。

#### シェルスキル（`.sh`）

```bash
#!/bin/bash
# ---
# description: ESXiホストのディスク使用量を確認する
# parameters:
#   host: string - ESXiホストのIPまたはホスト名
# ---
ssh root@"$host" df -h
```

#### MCP互換スキル（`.json`）

```json
{
  "name": "query_vcenter_api",
  "description": "vCenter REST APIにクエリを送信する",
  "input_schema": {
    "type": "object",
    "properties": {
      "endpoint": { "type": "string" },
      "method": { "type": "string", "enum": ["GET", "POST"] }
    }
  },
  "mcp": {
    "server_url": "http://localhost:8811/mcp"
  }
}
```

---

## 4. RAG エンジン仕様

### 4.1 インデックス化フロー

```
起動時 or ファイル変更検知
        │
        ▼
ドキュメントローダー
 - Markdown: そのままチャンク分割
 - PDF: テキスト抽出後チャンク分割
 - HTML: タグ除去後チャンク分割
        │
        ▼
チャンク分割
 - デフォルト: 512トークン / 64トークンオーバーラップ
        │
        ▼
エンベディング生成
 - デフォルト: ローカルモデル（sentence-transformers等）
 - オプション: OpenAI / Claude Embeddings
        │
        ▼
ベクトルDB保存
 - .agent_index/{agent-name}/ に保存（gitignore推奨）
```

### 4.2 検索フロー（クエリ時）

```
ユーザークエリ
        │
        ▼
クエリエンベディング生成
        │
        ▼
類似チャンク取得（Top-K、デフォルトK=5）
        │
        ▼
コンテキストとしてシステムプロンプトに注入
        │
        ▼
LLM へ送信
```

### 4.3 ベクトルDBの選択肢

| DB | 特徴 | 推奨ケース |
|---|---|---|
| **ChromaDB** | ローカル・ファイルベース・依存少ない | デフォルト推奨 |
| Qdrant | 高性能・Docker対応 | 大規模ナレッジ |
| FAISS | インメモリ・高速 | 揮発でよい場合 |
| Weaviate | フルマネージド | クラウド運用時 |

→ デフォルトは **ChromaDB**（追加インフラ不要）

---

## 5. LLM アダプター仕様

### 5.1 抽象インターフェース

```python
class LLMAdapter(Protocol):
    def chat(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        system: str | None = None,
    ) -> ChatResponse: ...
```

### 5.2 対応バックエンド

| バックエンド | 実装 | 備考 |
|---|---|---|
| Claude (Anthropic) | `anthropic` SDK | Tool Use対応 |
| OpenAI | `openai` SDK | Function Calling対応 |
| Ollama | HTTP直接呼び出し | ローカルLLM |
| OpenAI互換API | `openai` SDK（base_url変更） | vLLM, LM Studio等 |

### 5.3 切り替え方法

環境変数による切り替え（設定ファイル不要を貫く）:

```bash
# Claude使用
LLM_PROVIDER=claude \
LLM_MODEL=claude-sonnet-4-20250514 \
ANTHROPIC_API_KEY=sk-... \
agent run vmware-ops

# Ollama使用
LLM_PROVIDER=ollama \
LLM_MODEL=llama3.1:8b \
LLM_BASE_URL=http://localhost:11434 \
agent run vmware-ops
```

---

## 6. インターフェース仕様

### 6.1 CLI

```bash
# エージェント一覧
agent list

# エージェント起動（対話モード）
agent run {agent-name}

# 単発クエリ
agent query {agent-name} "VMのスナップショットを一覧表示する方法は？"

# ナレッジ再インデックス
agent index {agent-name}

# スキル一覧
agent skills {agent-name}
```

### 6.2 Web UI

- チャット形式のSPA（React or 軽量HTMLで実装）
- 左サイドバー: エージェント選択（自動検出された一覧）
- メインエリア: チャット
- エンドポイント: `http://localhost:8080`

### 6.3 REST API

```
POST /api/agents/{agent-name}/chat
Content-Type: application/json

{
  "message": "ユーザーの入力",
  "session_id": "任意のセッションID（省略可）"
}

→ Response:
{
  "reply": "エージェントの返答",
  "sources": [  // RAGで参照されたドキュメント
    { "file": "knowledge/vmware-best-practices.md", "chunk": "..." }
  ],
  "tool_calls": [  // 実行されたスキル
    { "skill": "get_vm_status", "result": {...} }
  ]
}
```

---

## 7. 会話履歴・メモリ（未確定）

> **⚠️ 要決定事項**

以下の3方式を検討中。実装コストとユースケースに応じて選択:

| 方式 | 概要 | コスト | 推奨ケース |
|---|---|---|---|
| **A: セッション内のみ** | メモリに保持、終了で消滅 | 低 | MVP・ステートレス運用 |
| **B: ファイル永続化** | `{agent-name}/.sessions/{id}.jsonl` に保存 | 中 | シングルユーザー |
| **C: エージェントごとDB** | SQLiteをエージェントディレクトリ内に配置 | 中 | マルチユーザー想定時 |

→ MVP では **方式A** で実装し、後から差し替え可能な設計にする

---

## 8. 実装技術スタック（候補）

| レイヤー | 選択肢 | 備考 |
|---|---|---|
| ランタイム言語 | Python / TypeScript | スキル実行のシェル連携を考慮するとPythonが現実的 |
| ベクトルDB | ChromaDB | ローカルファイルベース |
| エンベディング | `sentence-transformers` (ローカル) or API | オフライン運用を考慮 |
| Web UI | Vanilla HTML+JS / React | 軽量なら前者で十分 |
| API サーバー | FastAPI (Python) / Hono (TS) | |
| スキル実行サンドボックス | subprocess（最小構成） | 将来的にDocker隔離も検討 |

---

## 9. 未確定・要決定事項

| # | 項目 | 選択肢 | 優先度 |
|---|---|---|---|
| 1 | 会話履歴の永続化方式 | A/B/C（§7参照） | 高 |
| 2 | スキルの実行サンドボックス | subprocess / Docker / wasm | 中 |
| 3 | マルチエージェント連携 | 単一エージェントのみ vs エージェント間委譲 | 低 |
| 4 | 認証・アクセス制御 | なし / APIキー / OAuth | 中（API公開時） |
| 5 | エンベディングモデル | ローカル固定 vs API切り替え可能 | 中 |

---

## 10. MVP スコープ

最初にデリバーするものを絞る:

```
Phase 1 (MVP)
├── ディレクトリ自動検出
├── RAG（ChromaDB + ローカルエンベディング）
├── スキル実行（Pythonスクリプトのみ）
├── LLMアダプター（Claude + Ollama）
├── CLI インターフェース
└── 会話履歴: セッション内のみ

Phase 2
├── Web UI
├── REST API
├── シェルスキル / MCPスキル対応
└── OpenAI対応追加

Phase 3
├── 会話履歴永続化
├── スキルサンドボックス強化
└── マルチエージェント連携
```

---

*このドキュメントは設計ヒアリング結果に基づく初版です。未確定事項の決定後に改訂してください。*

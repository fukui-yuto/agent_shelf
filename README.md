# agent-shelf

設定ファイル不要の AI エージェントフレームワーク。

`agents/` 配下にディレクトリを置くだけで、専門特化した AI エージェントとして動作します。

## クイックスタート

### インストール

```bash
uv sync
```

### セットアップ

```bash
cp .env.example .env
# .env を編集して API キーを設定
```

### エージェントの作成

```
agents/
└── my-agent/
    ├── knowledge/        # RAG用ドキュメント (md, txt, html)
    ├── skills/           # ツールとして実行される Python スクリプト
    └── prompts/          # システムプロンプト定義
```

3つのサブディレクトリはすべて省略可能です。空ディレクトリでもエージェントとして認識されます。

### CLI コマンド

```bash
# エージェント一覧
agent list

# 対話モード
agent run my-agent

# 単発クエリ
agent query my-agent "Xのやり方を教えて"

# ナレッジの再インデックス
agent index my-agent

# スキル一覧
agent skills my-agent
```

## 設定

すべての設定は環境変数（または `.env` ファイル）で行います：

| 変数名 | 説明 | デフォルト |
|---|---|---|
| `LLM_PROVIDER` | LLM バックエンド (`claude` / `openai` / `gemini` / `ollama`) | `claude` |
| `LLM_MODEL` | モデル名 | `claude-sonnet-4-20250514` |
| `LLM_BASE_URL` | API ベース URL（Ollama / OpenAI 互換 API 用） | - |
| `ANTHROPIC_API_KEY` | Anthropic API キー | - |
| `OPENAI_API_KEY` | OpenAI API キー | - |
| `GOOGLE_API_KEY` | Google Gemini API キー | - |
| `EMBEDDING_PROVIDER` | エンベディング (`local` / `openai`) | `local` |

## エージェントディレクトリ構造

### knowledge/

ドキュメント（`.md`, `.txt`, `.html`）を配置します。自動的にチャンク分割・エンベディング生成され、ChromaDB にインデックスされます。クエリ時に関連チャンクが RAG として取得されます。

### skills/

フロントマターブロックでツールインターフェースを定義した Python スクリプト：

```python
# skills/get_status.py
# ---
# description: サービスのステータスを取得する
# parameters:
#   service_name: string - サービス名
# ---

def run(service_name: str) -> dict:
    return {"status": "running"}
```

フレームワークがこれらを LLM のツールとして登録し、LLM が呼び出した際に `run()` を実行します。

### prompts/

- `system.md` -- メインのシステムプロンプト（なければデフォルトを使用）
- `*.md` -- 追加コンテキスト（すべてマージされてシステムプロンプトに統合）

## アーキテクチャ

```
インターフェース層 (CLI)
        |
  Agent Router         -- agents/ 配下を自動検出
        |
  Agent Runtime        -- 各コンポーネントのオーケストレーション
   ├── RAG Engine      -- ChromaDB + エンベディング
   ├── Skill Executor  -- Python スキルの動的ロード・実行
   ├── Prompt Manager  -- システムプロンプトの組み立て
   └── LLM Adapter     -- Claude / OpenAI / Gemini / Ollama
```

## 技術スタック

- Python 3.12+ / uv
- ChromaDB（ベクトルストア）
- sentence-transformers（ローカルエンベディング）
- Anthropic SDK / OpenAI SDK / Gemini API / Ollama（LLM）
- Click + Rich（CLI）

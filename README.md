# AI設定ファイル品質改善ツール

CLAUDE.md / SKILL.md / commands/*.md を収集し、プロファイル別の品質チェック・スコアリングを行い、AI改善用プロンプトを生成するツール。

## 概要

### ワークフロー

2つの実行モードがある。

**手動モード** (`docker compose run --rm app`):

```text
1. [ツール] ファイル収集 → 品質チェック → ZIP化 + プロンプト生成
2. [人間]   ZIPとプロンプトをAIに送信
3. [AI]     各ファイルを改善して返却
4. [人間]   改善版を各プロジェクトに配置
```

**自動パイプライン** (`run_improve.sh`):

```text
1. [Docker]  ファイル収集 → 品質チェック → manifest.json + 個別プロンプト生成
2. [claude]  個別プロンプトを claude CLI (sonnet) で改善
3. [diff]    元ファイルと改善版の差分表示
4. [cp]      バックアップ後に元ファイルを上書き
```

## 必要要件

- Docker / Docker Compose
- jaq または jq（自動パイプライン使用時）
- claude CLI（自動パイプライン使用時）

## クイックスタート

```bash
# ビルド
docker compose build

# CLAUDE.md の品質チェック（カレントディレクトリ）
docker compose run --rm app python improve_claude_md.py .

# サンプルデータで動作確認
docker compose run --rm app python improve_claude_md.py --create-sample
```

## 使い方

### 手動モード

```bash
# 基本: カレントディレクトリを分析
docker compose run --rm app python improve_claude_md.py .

# ディレクトリと出力先を指定
docker compose run --rm app python improve_claude_md.py /path/to/projects --work-dir /path/to/output

# CLAUDE.md + SKILL.md を対象
docker compose run --rm app python improve_claude_md.py . --profiles claude-md,skill-md

# 全プロファイル
docker compose run --rm app python improve_claude_md.py . --profiles claude-md,skill-md,command-md

# レポートのみ（プロンプト生成スキップ）
docker compose run --rm app python improve_claude_md.py . --no-prompt
```

### 自動パイプライン

```bash
# デフォルト（~/prog 以下を対象）
./run_improve.sh

# ディレクトリ指定
./run_improve.sh /path/to/projects /path/to/workdir

# プロファイル指定
./run_improve.sh /path/to/projects /path/to/workdir --profiles claude-md,skill-md
```

4フェーズで動作:

| Phase | 内容 | 実行環境 |
|-------|------|----------|
| 1 | ファイル収集 + 品質採点 + manifest.json生成 | Docker |
| 2 | 個別プロンプトを claude CLI (sonnet) で改善 | ホスト |
| 3 | 元ファイルと改善版の diff 表示 | ホスト |
| 4 | バックアップ後に元ファイルを上書き | ホスト |

バックアップは `{work_dir}/backups_{timestamp}/` に保存される。

### ローカル実行（Docker不要）

```bash
# uv が必要
./run.sh
```

## プロファイル

対象ファイルの種別ごとに品質ルールを切り替える。デフォルトは `claude-md` のみ。

| プロファイル | 対象パターン | 必須項目 | 推奨項目 |
|-------------|------------|---------|---------|
| `claude-md` | `CLAUDE.md` | プロジェクト概要、技術スタック | 禁止事項、コード例、コマンド例 |
| `skill-md` | `SKILL.md` | トリガー条件、手順/フェーズ | 出力形式、前提条件 |
| `command-md` | `*.md` (commands/) | タイトル | 手順、入出力 |

## CLIオプション

| フラグ | 用途 | デフォルト |
|--------|------|-----------|
| `source_dir` | 検索元ディレクトリ | `~/prog` |
| `--work-dir` | 作業ディレクトリ | `~/prog/tmp_claude` |
| `--profiles` | 使用プロファイル（カンマ区切り） | `claude-md` |
| `--config` | JSON設定ファイルパス | デフォルト設定 |
| `--dump-config` | デフォルト設定をJSON出力して終了 | - |
| `--output-json` | manifest.json + 個別プロンプト出力 | - |
| `--no-prompt` | AI依頼プロンプト生成スキップ | - |
| `--create-sample` | サンプルデータで動作確認 | - |
| `--host-source-dir` | Docker内→ホストパス変換（source） | - |
| `--host-work-dir` | Docker内→ホストパス変換（work） | - |

### 設定カスタマイズ

```bash
# デフォルト設定をJSON出力
docker compose run --rm app python improve_claude_md.py --dump-config > my_rules.json

# 編集後に使用
docker compose run --rm app python improve_claude_md.py . --config my_rules.json
```

## 出力ファイル

### 手動モードの出力

| ファイル | 内容 |
|---------|------|
| `AI_PROMPT.md` | AI改善依頼プロンプト |
| `claude_md_files.zip` | 対象ファイル一式 |

### 自動パイプラインの出力

| ファイル | 内容 |
|---------|------|
| `manifest.json` | 処理対象ファイル一覧 |
| `*_PROMPT.md` | ファイル別の改善プロンプト |
| `*_IMPROVED.md` | AI改善後のファイル |

## 開発

```bash
# テスト実行
docker compose run --rm test

# 単一テスト
docker compose run --rm test pytest tests/test_improve_claude_md.py::TestProfiles -v
```

## ライセンス

MIT License

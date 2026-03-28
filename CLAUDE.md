# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code)
when working with code in this repository.

## Project Overview

AI設定ファイル品質改善ツール。
CLAUDE.md / SKILL.md / commands/*.md を収集し、
プロファイル別の品質チェック・スコアリングを行い、
AI改善用のプロンプトとZIPを生成する。

3つの実行方法:

- **Docker手動モード** (`docker compose run --rm app`):
  収集+採点+ZIP化 → 人間がAIに送信
- **自動パイプライン** (`run_improve.sh`):
  収集+採点 → claude CLI で自動改善 → diff → 上書き
- **ローカル実行** (`run.sh`):
  uv直接実行（Docker不要）

## Tech Stack

- Python 3.10+ / uv
- rich (CLI表示)
- pytest (テスト)
- Docker / Docker Compose (テスト・手動モード・自動パイプラインで使用)

## Docker ボリューム

| 環境変数 | コンテナパス | デフォルト |
|----------|-------------|-----------|
| `SOURCE_DIR` | `/source` (ro) | カレントディレクトリ |
| `WORK_DIR` | `/work` | `./tmp_work` |

`--work-dir` には `/work` を指定すること。マウント外パスは出力が消失する。

## Commands

```bash
# テスト実行
docker compose run --rm test

# 単一テスト
docker compose run --rm test pytest tests/test_improve_claude_md.py::TestProfiles::test_find_skill_md_files -v

# サンプルデータで動作確認
docker compose run --rm app python -m src --create-sample

# デフォルト設定をJSON出力
docker compose run --rm app python -m src --dump-config

# 自動パイプライン (claude CLI必要)
./run_improve.sh [source_dir] [work_dir] [--profiles claude-md,skill-md]
```

## Architecture

`src/` パッケージ構成:

### 設定層 (`src/config.py`)

- `DEFAULT_CONFIG`, `load_config()`, `_deep_merge()`

### データ層 (`src/models.py`)

- `TargetFile` (dataclass): ファイル情報保持
- `FoundFile` (NamedTuple): 検索結果

### パイプライン層 (`src/pipeline.py`)

- `MdImprover`: オーケストレーション
  - プロファイル特異性ソート → `find_files()` → `process_files()` → `run()`
  - 操作層に委譲（品質チェック・プロンプト生成・ファイル管理）

### 操作層

- `src/quality_checker.py`: `QualityChecker`
- `src/prompt_generator.py`: `PromptGenerator`
- `src/file_manager.py`: `FileManager`

### CLI層 (`src/cli.py`)

### プロファイル

| プロファイル | 対象パターン | 品質ルール |
|-------------|------------|-----------|
| `claude-md` | `CLAUDE.md` | プロジェクト概要・技術スタック必須、禁止事項・コード例チェック |
| `skill-md` | `SKILL.md` | トリガー条件・手順/フェーズ必須、出力形式・前提条件推奨 |
| `command-md` | `*.md` | タイトル必須、手順・入出力推奨 |

`run_improve.sh` の4フェーズ:

1. Docker内でPython実行 → `manifest.json` + 個別 `*_PROMPT.md` 生成
2. `manifest.json`を読み、各エントリに対して `claude --print` で改善
3. `diff` でプレビュー表示
4. バックアップ後に上書き

## Key Options

| フラグ | 用途 |
|--------|------|
| `--profiles` | 使用プロファイル (カンマ区切り、例: `claude-md,skill-md,command-md`) |
| `--config` | JSON設定ファイルパス（デフォルト設定をオーバーライド） |
| `--dump-config` | デフォルト設定をJSON形式で出力して終了 |
| `--output-json` | manifest.json + 個別プロンプト出力（自動パイプライン用） |
| `--host-source-dir` / `--host-work-dir` | Docker内パス→ホストパス変換 |
| `--no-prompt` | AI依頼プロンプト生成スキップ |
| `--create-sample` | `/tmp/claude_sample_prog` にサンプル作成 |

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI設定ファイル品質改善ツール。CLAUDE.md / SKILL.md / commands/*.md を収集し、プロファイル別の品質チェック・スコアリングを行い、AI改善用のプロンプトとZIPを生成する。

2つの実行モード:
- **手動モード** (`run.sh`): 収集+採点+ZIP化 → 人間がAIに送信
- **自動パイプライン** (`run_improve.sh`): 収集+採点 → claude CLI で自動改善 → diff → 上書き

## Tech Stack

- Python 3.10+ / uv
- rich (CLI表示)
- pytest (テスト)
- Docker (自動パイプラインのPhase 1で使用)

## Commands

```bash
# テスト実行
docker compose run --rm test

# 単一テスト
docker compose run --rm test pytest tests/test_improve_claude_md.py::TestProfiles::test_find_skill_md_files -v

# サンプルデータで動作確認
docker compose run --rm app python improve_claude_md.py --create-sample

# デフォルト設定をJSON出力
docker compose run --rm app python improve_claude_md.py --dump-config

# 自動パイプライン (claude CLI必要)
./run_improve.sh [source_dir] [work_dir] [--profiles claude-md,skill-md]
```

## Architecture

単一ファイル構成 (`improve_claude_md.py`):

### 設定層
- `DEFAULT_CONFIG`: プロファイル別の品質ルール・プロンプトテンプレートを辞書で定義
- `load_config()`: JSON設定ファイルを読み込みデフォルトとディープマージ
- `_deep_merge()`: ネスト対応の辞書マージ

### データ層
- `CLAUDEFile` (dataclass): ファイル情報保持（パス、内容、スコア、問題点、profile_name）

### ロジック層
- `CLAUDEMDImprover`: メインクラス
  - `__init__(source_dir, work_dir, config=None, profiles=None)`
  - `find_claude_files()` → `process_files()` → `show_report()` の流れ
  - `check_quality(content, profile_name)`: 設定駆動の品質チェック
  - `generate_ai_prompt()`: 一括AI依頼プロンプト生成
  - `generate_single_file_prompt()` / `save_single_file_prompt()`: 個別プロンプト生成
  - `run()`: オーケストレーション

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

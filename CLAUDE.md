# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLAUDE.md品質改善ツール。`~/prog/` 以下のローカルCLAUDE.mdを収集し、品質チェック・スコアリングを行い、AI改善用のプロンプトとZIPを生成する。

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
docker run --rm -v "$(pwd):/app" -w /app python:slim sh -c 'pip install -q rich pytest && pytest tests/ -v'

# 単一テスト
docker run --rm -v "$(pwd):/app" -w /app python:slim sh -c 'pip install -q rich pytest && pytest tests/test_improve_claude_md.py::TestGenerateSingleFilePrompt::test_returns_prompt_string_from_claude_file -v'

# サンプルデータで動作確認
docker run --rm -v "$(pwd):/app" -w /app python:slim sh -c 'pip install -q rich && python /app/improve_claude_md.py --create-sample'

# 自動パイプライン (claude CLI必要)
./run_improve.sh [source_dir] [work_dir]
```

## Architecture

単一ファイル構成 (`improve_claude_md.py`):

- `CLAUDEFile` (dataclass): ファイル情報保持（パス、内容、スコア、問題点）
- `CLAUDEMDImprover`: メインクラス
  - `find_claude_files()` → `process_files()` → `show_report()` の流れ
  - `check_quality()`: 正規表現ベースの品質チェック（必須セクション、曖昧表現、禁止事項）
  - `generate_ai_prompt()`: 一括AI依頼プロンプト生成
  - `generate_single_file_prompt()` / `save_single_file_prompt()`: 個別プロンプト生成（`--output-json`用）
  - `run()`: オーケストレーション。`output_json=True`で`manifest.json`+個別プロンプト出力

`run_improve.sh` の4フェーズ:
1. Docker内でPython実行 → `manifest.json` + 個別 `*_PROMPT.md` 生成
2. `manifest.json`を読み、各エントリに対して `claude --print` で改善
3. `diff` でプレビュー表示
4. バックアップ後に上書き

## Key Options

| フラグ | 用途 |
|--------|------|
| `--output-json` | manifest.json + 個別プロンプト出力（自動パイプライン用） |
| `--host-source-dir` / `--host-work-dir` | Docker内パス→ホストパス変換 |
| `--no-prompt` | AI依頼プロンプト生成スキップ |
| `--create-sample` | `/tmp/claude_sample_prog` にサンプル作成 |

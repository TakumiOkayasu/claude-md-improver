"""設定管理"""

import copy
import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "profiles": {
        "claude-md": {
            "target_pattern": "CLAUDE.md",
            "display_name": "CLAUDE.md",
            "quality_rules": {
                "required_sections": [
                    {"pattern": r"^#+ .*プロジェクト|^#+ .*Project", "name": "プロジェクト概要", "penalty": 15},
                    {"pattern": r"^#+ .*技術スタック|^#+ .*Tech Stack", "name": "技術スタック", "penalty": 15},
                ],
                "required_keywords": [
                    {"keywords": ["禁止", "NEVER"], "description": "禁止事項が明示されていない", "penalty": 10},
                ],
                "required_patterns": [
                    {"pattern": "```", "description": "コード例・コマンド例が不足", "penalty": 10},
                ],
                "max_lines": 500,
                "max_lines_penalty": 5,
                "vague_patterns": [
                    {"pattern": r"できるだけ|なるべく|適宜", "description": "曖昧な表現", "penalty": 5},
                    {"pattern": r"多分|たぶん|おそらく", "description": "不確実な表現", "penalty": 5},
                ],
                "good_patterns": [
                    {"pattern": r"^#+ .*例|^#+ .*Example", "description": "実例セクションあり", "flags": "MULTILINE"},
                    {"keywords": ["スキル", "skill"], "description": "スキル参照あり"},
                ],
            },
            "prompt_template": {
                "title": "CLAUDE.md改善依頼: {display_name}",
                "improvement_guidelines": [
                    "曖昧な表現を明確に (「できるだけ」→「必ず」、「多分」→削除)",
                    "禁止事項を明示 (具体的に、理由も記載)",
                    "技術スタックを明記",
                    "コマンド例・コード例を追加",
                ],
                "recommended_guidelines": [
                    "プロジェクト概要を追加",
                    "スキル参照を追加 (グローバルスキルへの参照)",
                ],
                "prohibited_actions": [
                    "既存の内容を勝手に削除しない",
                    "プロジェクト固有の情報を推測で追加しない",
                    "不明な部分は [要確認] とマークする",
                ],
                "quality_criteria": [
                    "AIが間違えない: 曖昧な指示は禁止、具体的なルールのみ",
                    "AIがミスしない: チェックリスト形式、自己検証可能に",
                    "AIがルールを守る: 禁止事項を明確に、理由も記載",
                ],
                "output_instruction": (
                    "改善後のCLAUDE.mdの内容のみを出力してください。説明やコメントは不要です。\n"
                    "元のファイルにYAMLフロントマター(---で囲まれたブロック)がある場合は、そのまま保持してください。\n"
                    "フロントマターがない場合は、`#` から始めてください。"
                ),
            },
        },
        "skill-md": {
            "target_pattern": "SKILL.md",
            "display_name": "SKILL.md",
            "quality_rules": {
                "required_sections": [
                    {"pattern": r"^#+ .*トリガー|^#+ .*Trigger", "name": "トリガー条件", "penalty": 20},
                    {
                        "pattern": r"^#+ .*手順|^#+ .*フェーズ|^#+ .*Step|^#+ .*Phase",
                        "name": "手順/フェーズ",
                        "penalty": 20,
                    },
                ],
                "required_keywords": [
                    {
                        "keywords": ["禁止", "NEVER", "制約"],
                        "description": "禁止事項/制約が明示されていない",
                        "penalty": 10,
                    },
                ],
                "required_patterns": [],
                "max_lines": 300,
                "max_lines_penalty": 5,
                "vague_patterns": [
                    {"pattern": r"できるだけ|なるべく|適宜", "description": "曖昧な表現", "penalty": 5},
                    {"pattern": r"多分|たぶん|おそらく", "description": "不確実な表現", "penalty": 5},
                ],
                "good_patterns": [
                    {"pattern": r"^#+ .*出力|^#+ .*Output", "description": "出力形式の定義あり", "flags": "MULTILINE"},
                    {"pattern": r"^#+ .*前提|^#+ .*Prereq", "description": "前提条件の定義あり", "flags": "MULTILINE"},
                ],
            },
            "prompt_template": {
                "title": "SKILL.md改善依頼: {display_name}",
                "improvement_guidelines": [
                    "トリガー条件を明確に（どの場面で発動するか）",
                    "手順をステップバイステップで記述",
                    "禁止事項/制約を明示",
                    "曖昧な表現を排除",
                ],
                "recommended_guidelines": [
                    "前提条件を追加",
                    "出力形式/テンプレートを追加",
                ],
                "prohibited_actions": [
                    "既存の内容を勝手に削除しない",
                    "スキルの目的を変更しない",
                    "不明な部分は [要確認] とマークする",
                ],
                "quality_criteria": [
                    "AIが正しく発動する: トリガー条件が明確",
                    "AIが正しく実行する: 手順が具体的でステップが明確",
                    "AIがルールを守る: 禁止事項・制約が明示",
                ],
                "output_instruction": (
                    "改善後のSKILL.mdの内容のみを出力してください。説明やコメントは不要です。\n"
                    "元のファイルにYAMLフロントマター(---で囲まれたブロック)がある場合は、そのまま保持してください。\n"
                    "フロントマターがない場合は、`#` から始めてください。"
                ),
            },
        },
        "command-md": {
            "target_pattern": "*.md",
            "display_name": "command",
            "quality_rules": {
                "required_sections": [
                    {"pattern": r"^#+ ", "name": "タイトル(H1)", "penalty": 15},
                ],
                "required_keywords": [],
                "required_patterns": [],
                "max_lines": 200,
                "max_lines_penalty": 5,
                "vague_patterns": [
                    {"pattern": r"できるだけ|なるべく|適宜", "description": "曖昧な表現", "penalty": 5},
                    {"pattern": r"多分|たぶん|おそらく", "description": "不確実な表現", "penalty": 5},
                ],
                "good_patterns": [
                    {"pattern": r"手順|ステップ|Step", "description": "手順の記述あり"},
                    {"pattern": r"入力|出力|Input|Output", "description": "入出力の明示あり"},
                ],
            },
            "prompt_template": {
                "title": "command改善依頼: {display_name}",
                "improvement_guidelines": [
                    "処理手順を明確に記述",
                    "入出力を明示",
                    "曖昧な表現を排除",
                ],
                "recommended_guidelines": [
                    "使用例を追加",
                ],
                "prohibited_actions": [
                    "既存の内容を勝手に削除しない",
                    "コマンドの目的を変更しない",
                    "不明な部分は [要確認] とマークする",
                ],
                "quality_criteria": [
                    "AIが正しく実行する: 手順が具体的",
                    "AIが間違えない: 曖昧な指示がない",
                ],
                "output_instruction": (
                    "改善後のコマンドファイルの内容のみを出力してください。説明やコメントは不要です。\n"
                    "元のファイルにYAMLフロントマター(---で囲まれたブロック)がある場合は、そのまま保持してください。\n"
                    "フロントマターがない場合は、`#` から始めてください。"
                ),
            },
        },
    },
    "exclude_dirs": [".git", "node_modules", "__pycache__", ".venv", "venv"],
    "sample_projects": [
        {
            "name": "project-a",
            "profile": "claude-md",
            "filename": "CLAUDE.md",
            "content": (
                "# Project A\n\nこれはプロジェクトAです。\n\n"
                "できるだけPythonを使ってください。\n"
                "多分FastAPIが良いと思います。\n"
            ),
        },
        {
            "name": "project-b",
            "profile": "claude-md",
            "filename": "CLAUDE.md",
            "content": (
                "# Project B\n\n## 技術スタック\n- TypeScript\n- React\n\n## 禁止事項\n- グローバル変数の使用禁止\n"
            ),
        },
        {
            "name": "project-c",
            "profile": "claude-md",
            "filename": "CLAUDE.md",
            "content": ("# プロジェクトC\n\nなるべくきれいに書いてください。\nおそらく動くと思います。\n"),
        },
    ],
}


def _deep_merge(base: dict, override: dict) -> dict:
    """override の値で base を上書き (ネスト対応)"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(config_path: "Path | None" = None) -> Dict[str, Any]:
    """設定ファイルを読み込み DEFAULT_CONFIG とマージ"""
    config = copy.deepcopy(DEFAULT_CONFIG)
    if config_path and config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            _deep_merge(config, json.load(f))
    return config

"""プロンプト生成・保存"""

from pathlib import Path
from typing import Any, Dict, List

from .models import TargetFile


class PromptGenerator:
    """AI改善用プロンプトの生成と保存"""

    def __init__(self, config: Dict[str, Any], work_dir: Path):
        self.config = config
        self.work_dir = work_dir

    def _get_prompt_template(self, profile_name: str) -> Dict[str, Any]:
        """プロファイルのプロンプトテンプレートを取得"""
        return self.config["profiles"][profile_name]["prompt_template"]

    def generate_single(self, file: TargetFile) -> str:
        """単一ファイル用のAI改善プロンプトを生成"""
        tmpl = self._get_prompt_template(file.profile_name)
        issues_text = "\n".join(f"- {issue}" for issue in file.problem_issues)

        title = tmpl.get("title", "{directory_name}").format(
            directory_name=file.directory_name,
            target_filename=self.config["profiles"][file.profile_name]["display_name"],
        )
        guidelines = "\n".join(f"- {g}" for g in tmpl.get("improvement_guidelines", []))
        recommended = "\n".join(f"- {g}" for g in tmpl.get("recommended_guidelines", []))
        prohibited = "\n".join(f"- {a}" for a in tmpl.get("prohibited_actions", []))
        criteria = "\n".join(f"- {c}" for c in tmpl.get("quality_criteria", []))
        output_inst = tmpl.get("output_instruction", "改善後の内容のみを出力してください。")

        return f"""# {title}

## 改善方針

### 必須対応
{guidelines}

### 推奨対応
{recommended}

### 禁止事項
{prohibited}

## 品質基準

{criteria}

## 対象ファイル情報

- **プロジェクト**: {file.directory_name}
- **品質スコア**: {file.score}/100

### 検出された問題
{issues_text}

## 現在の内容

````markdown
{file.content.strip()}
````

## 出力指示

{output_inst}
"""

    def save_single(self, file: TargetFile) -> Path:
        """プロンプトをファイルに保存"""
        prompt = self.generate_single(file)
        prompt_path = self.work_dir / f"{file.directory_name}_PROMPT.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        return prompt_path

    def generate_batch(self, processed: List[TargetFile]) -> str:
        """AI依頼用プロンプト生成 (一括版)"""
        profiles_used = sorted({f.profile_name for f in processed})
        prompt_parts: List[str] = [
            "# AI設定ファイル品質改善依頼",
            "",
            "以下のファイルの品質を改善してください。",
            "",
        ]

        for pname in profiles_used:
            tmpl = self._get_prompt_template(pname)
            display = self.config["profiles"][pname]["display_name"]
            prompt_parts.extend(
                [
                    f"## {display} の改善方針",
                    "",
                    "### 必須対応",
                ]
            )
            for g in tmpl.get("improvement_guidelines", []):
                prompt_parts.append(f"- {g}")
            prompt_parts.extend(["", "### 推奨対応"])
            for g in tmpl.get("recommended_guidelines", []):
                prompt_parts.append(f"- {g}")
            prompt_parts.extend(["", "### 禁止事項"])
            for a in tmpl.get("prohibited_actions", []):
                prompt_parts.append(f"- {a}")
            prompt_parts.extend(["", "### 品質基準"])
            for c in tmpl.get("quality_criteria", []):
                prompt_parts.append(f"- {c}")
            prompt_parts.extend(["", "---", ""])

        for file in processed:
            display = self.config["profiles"][file.profile_name]["display_name"]
            prompt_parts.extend(
                [
                    f"## ファイル: {file.directory_name}_{display}",
                    "",
                    f"**元のパス**: `{file.original_path}`",
                    f"**品質スコア**: {file.score}/100",
                    "",
                    "**検出された問題**:",
                ]
            )
            for issue in file.problem_issues:
                prompt_parts.append(f"- {issue}")
            prompt_parts.extend(
                [
                    "",
                    "**現在の内容**:",
                    "```markdown",
                    file.content.strip(),
                    "```",
                    "",
                    "---",
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "## 出力形式",
                "",
                "各ファイルについて、以下の形式で改善版を出力してください:",
                "",
                "```markdown",
                "### {directory_name}_{display_name}",
                "",
                "[改善後の内容]",
                "```",
                "",
                "## 改善のポイント",
                "",
                "各ファイルの改善点を簡潔に説明してください。",
            ]
        )

        return "\n".join(prompt_parts)

    def save_batch(self, prompt: str) -> Path:
        """AI依頼プロンプトを保存"""
        prompt_file = self.work_dir / "AI_IMPROVEMENT_REQUEST.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        return prompt_file

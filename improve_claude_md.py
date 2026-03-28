#!/usr/bin/env python3
"""
AI設定ファイル品質改善ツール

対象: CLAUDE.md / SKILL.md / commands/*.md
機能:
1. 対象ファイルを収集
2. プロファイル別の品質チェック・スコアリング
3. AI改善用プロンプト生成
4. 元の場所に戻す
"""

import copy
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# デフォルト設定 (プロファイル制)
# ---------------------------------------------------------------------------
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
                "title": "CLAUDE.md改善依頼: {directory_name}",
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
                    "マークダウン形式で、`#` から始めてください。"
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
                "title": "SKILL.md改善依頼: {directory_name}",
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
                    "マークダウン形式で、`#` から始めてください。"
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
                "title": "command改善依頼: {directory_name}",
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
                    "マークダウン形式で、`#` から始めてください。"
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


class FoundFile(NamedTuple):
    """検索で見つかったファイル"""

    path: Path
    profile_name: str


@dataclass
class CLAUDEFile:
    """対象ファイル情報"""

    original_path: Path
    backup_path: Path
    directory_name: str
    content: str
    issues: List[str]
    score: int
    profile_name: str = "claude-md"

    @property
    def problem_issues(self) -> List[str]:
        """問題点のみ抽出 (❌/⚠️)"""
        return [i for i in self.issues if i.startswith("❌") or i.startswith("⚠️")]


class CLAUDEMDImprover:
    """AI設定ファイル改善クラス"""

    def __init__(
        self,
        source_dir: Path,
        work_dir: Path,
        config: "Dict[str, Any] | None" = None,
        profiles: "List[str] | None" = None,
    ):
        self.source_dir = source_dir
        self.work_dir = work_dir
        self.config = config or DEFAULT_CONFIG
        self.active_profiles = profiles or ["claude-md"]
        unknown = set(self.active_profiles) - set(self.config["profiles"])
        if unknown:
            raise ValueError(f"不明なプロファイル: {', '.join(sorted(unknown))}")
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def find_claude_files(self) -> List[FoundFile]:
        """対象ファイルを検索"""
        results: List[FoundFile] = []
        exclude = set(self.config.get("exclude_dirs", []))
        for pname in self.active_profiles:
            profile = self.config["profiles"][pname]
            pattern = profile["target_pattern"]
            display = profile["display_name"]
            console.print(f"[cyan]{display}ファイルを検索中...[/cyan]")
            files = [f for f in self.source_dir.rglob(pattern) if not any(part in exclude for part in f.parts)]
            for f in files:
                results.append(FoundFile(f, pname))
            console.print(f"[green]✓[/green] {len(files)}個の{display}を発見")
        return results

    def backup_file(self, file_path: Path) -> Path:
        """ファイルをバックアップディレクトリにコピー"""
        dir_name = file_path.parent.name
        backup_name = f"{dir_name}_{file_path.name}"
        backup_path = self.work_dir / backup_name
        shutil.copy2(file_path, backup_path)
        return backup_path

    def check_quality(self, content: str, profile_name: str = "claude-md") -> Tuple[List[str], int]:
        """品質チェック (プロファイルのルールを動的適用)"""
        issues: List[str] = []
        score = 100
        rules = self.config["profiles"][profile_name]["quality_rules"]

        # 必須セクションチェック
        for section in rules.get("required_sections", []):
            if not re.search(section["pattern"], content, re.MULTILINE | re.IGNORECASE):
                issues.append(f"❌ 必須セクション不足: {section['name']}")
                score -= section.get("penalty", 15)

        # 必須キーワードチェック
        for rule in rules.get("required_keywords", []):
            if not any(kw in content for kw in rule["keywords"]):
                issues.append(f"⚠️  {rule['description']}")
                score -= rule.get("penalty", 10)

        # 必須パターンチェック
        for rule in rules.get("required_patterns", []):
            if rule["pattern"] not in content:
                issues.append(f"⚠️  {rule['description']}")
                score -= rule.get("penalty", 10)

        # 行数チェック
        max_lines = rules.get("max_lines", 500)
        line_count = len(content.splitlines())
        if line_count > max_lines:
            issues.append(f"⚠️  ファイルが長すぎる: {line_count}行 (推奨: {max_lines}行以下)")
            score -= rules.get("max_lines_penalty", 5)

        # 曖昧表現チェック
        for vp in rules.get("vague_patterns", []):
            if re.search(vp["pattern"], content):
                issues.append(f"⚠️  {vp['description']}が含まれている")
                score -= vp.get("penalty", 5)

        # 良い点
        for gp in rules.get("good_patterns", []):
            if "pattern" in gp:
                flags = re.MULTILINE if gp.get("flags") == "MULTILINE" else 0
                if re.search(gp["pattern"], content, flags):
                    issues.append(f"✅ {gp['description']}")
            elif "keywords" in gp:
                if any(kw in content or kw in content.lower() for kw in gp["keywords"]):
                    issues.append(f"✅ {gp['description']}")

        return issues, max(0, min(100, score))

    def _get_prompt_template(self, profile_name: str) -> Dict[str, Any]:
        """プロファイルのプロンプトテンプレートを取得"""
        return self.config["profiles"][profile_name]["prompt_template"]

    def generate_single_file_prompt(self, file: CLAUDEFile) -> str:
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

    def save_single_file_prompt(self, file: CLAUDEFile) -> Path:
        """プロンプトをファイルに保存"""
        prompt = self.generate_single_file_prompt(file)
        prompt_path = self.work_dir / f"{file.directory_name}_PROMPT.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        return prompt_path

    def improve_content(self, content: str, dir_name: str) -> str:
        """内容を改善 (AI依頼用プロンプト生成)"""
        # 改善は行わず、元のコンテンツをそのまま保持
        # AI への依頼プロンプトを生成するだけ
        return content

    def process_files(self, files: List[FoundFile]) -> List[CLAUDEFile]:
        """ファイルを処理"""
        processed = []

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("処理中...", total=len(files))

            for found in files:
                backup_path = self.backup_file(found.path)
                dir_name = found.path.parent.name
                content = found.path.read_text(encoding="utf-8")
                issues, score = self.check_quality(content, found.profile_name)
                improved_content = self.improve_content(content, dir_name)
                backup_path.write_text(improved_content, encoding="utf-8")

                processed.append(
                    CLAUDEFile(
                        original_path=found.path,
                        backup_path=backup_path,
                        directory_name=dir_name,
                        content=improved_content,
                        issues=issues,
                        score=score,
                        profile_name=found.profile_name,
                    )
                )

                progress.update(task, advance=1)

        return processed

    def show_report(self, processed: List[CLAUDEFile]):
        """レポート表示"""
        console.print("\n" + "=" * 80)
        console.print(Panel.fit("[bold cyan]品質チェック・改善レポート[/bold cyan]", border_style="cyan"))

        # サマリーテーブル
        table = Table(title="ファイル一覧", show_lines=True)
        table.add_column("プロジェクト", style="cyan")
        table.add_column("スコア", justify="center", style="yellow")
        table.add_column("状態", justify="center")
        table.add_column("パス")

        for file in processed:
            status = "🟢 良好" if file.score >= 80 else "🟡 要改善" if file.score >= 60 else "🔴 要修正"
            table.add_row(
                file.directory_name, f"{file.score}/100", status, str(file.original_path.relative_to(self.source_dir))
            )

        console.print(table)

        # 詳細レポート
        for file in processed:
            console.print(f"\n[bold]📁 {file.directory_name}[/bold] (スコア: {file.score}/100)")
            console.print(f"   パス: {file.original_path}")
            console.print(f"   バックアップ: {file.backup_path}")

            if file.issues:
                console.print("   問題点:")
                for issue in file.issues:
                    console.print(f"      {issue}")

        # 統計
        avg_score = sum(f.score for f in processed) / len(processed) if processed else 0
        console.print(f"\n[bold cyan]平均スコア:[/bold cyan] {avg_score:.1f}/100")

    def generate_ai_prompt(self, processed: List[CLAUDEFile]) -> str:
        """AI依頼用プロンプト生成 (一括版)"""
        # プロファイル別にグループ化して方針セクションを構築
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

    def save_ai_prompt(self, prompt: str) -> Path:
        """AI依頼プロンプトを保存"""
        prompt_file = self.work_dir / "AI_IMPROVEMENT_REQUEST.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        return prompt_file

    def restore_files(self, processed: List[CLAUDEFile], dry_run: bool = True):
        """ファイルを元の場所に戻す"""
        if dry_run:
            console.print("\n[yellow]⚠️  ドライランモード: 実際のファイルは変更されません[/yellow]")
            return

        console.print("\n[cyan]ファイルを元の場所に復元中...[/cyan]")

        for file in processed:
            try:
                shutil.copy2(file.backup_path, file.original_path)
                console.print(f"[green]✓[/green] {file.original_path}")
            except Exception as e:
                console.print(f"[red]✗[/red] {file.original_path}: {e}")

    def create_archive(self, processed: List[CLAUDEFile]) -> Path:
        """ZIPアーカイブを作成"""
        import zipfile
        from datetime import datetime

        profiles_tag = "_".join(sorted(self.active_profiles))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.work_dir / f"{profiles_tag}_files_{timestamp}.zip"

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in processed:
                arcname = file.backup_path.name
                zipf.write(file.backup_path, arcname)

        return archive_path

    def run(
        self,
        dry_run: bool = True,
        generate_prompt: bool = True,
        output_json: bool = False,
        host_source_dir: "str | None" = None,
        host_work_dir: "str | None" = None,
    ) -> List[CLAUDEFile]:
        """メイン処理"""
        profiles_label = ", ".join(self.active_profiles)
        console.print(
            Panel.fit(
                f"[bold]AI設定ファイル品質改善ツール[/bold]\n"
                f"プロファイル: {profiles_label}\n"
                f"対象: {self.source_dir}\n"
                f"作業: {self.work_dir}",
                border_style="blue",
            )
        )

        # ファイル検索
        files = self.find_claude_files()

        if not files:
            console.print("[yellow]⚠️  対象ファイルが見つかりませんでした[/yellow]")
            return []

        # 処理
        processed = self.process_files(files)

        # レポート
        self.show_report(processed)

        # ZIPアーカイブ作成
        console.print("\n[cyan]ZIPアーカイブを作成中...[/cyan]")
        archive_path = self.create_archive(processed)
        console.print(f"[green]✓[/green] アーカイブ作成: {archive_path}")

        # AI依頼プロンプト生成
        if generate_prompt:
            console.print("\n[cyan]AI依頼プロンプトを生成中...[/cyan]")
            prompt = self.generate_ai_prompt(processed)
            prompt_file = self.save_ai_prompt(prompt)
            console.print(f"[green]✓[/green] プロンプト保存: {prompt_file}")

            # プロンプトのプレビュー
            console.print("\n[bold]AI依頼プロンプト (抜粋):[/bold]")
            preview_lines = prompt.splitlines()[:30]
            for line in preview_lines:
                console.print(f"  {line}")
            if len(prompt.splitlines()) > 30:
                console.print(f"  ... (残り {len(prompt.splitlines()) - 30} 行)")

        # manifest.json + 個別プロンプト出力
        if output_json:
            manifest = []
            for file in processed:
                original = str(file.original_path)
                backup = str(file.backup_path)
                if host_source_dir and host_work_dir:
                    original = original.replace(str(self.source_dir), host_source_dir)
                    backup = backup.replace(str(self.work_dir), host_work_dir)
                manifest.append(
                    {
                        "directory_name": file.directory_name,
                        "profile_name": file.profile_name,
                        "original_path": original,
                        "backup_path": backup,
                        "score": file.score,
                        "issues": file.problem_issues,
                    }
                )
                self.save_single_file_prompt(file)

            manifest_path = self.work_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            console.print(f"[green]✓[/green] manifest.json 出力: {manifest_path}")

        # 復元 (dry_runでない場合のみ)
        if not dry_run:
            console.print("\n[bold red]警告: AI改善前のファイルで上書きしようとしています[/bold red]")
            console.print("[yellow]通常は --apply を使用せず、AI改善後に手動で戻してください[/yellow]")

        return processed


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="AI設定ファイル品質改善ツール (CLAUDE.md / SKILL.md / commands)",
        epilog="""
使用例:
  # CLAUDE.md のみ (従来互換)
  python improve_claude_md.py ~/prog

  # CLAUDE.md + SKILL.md
  python improve_claude_md.py ~/.claude --profiles claude-md,skill-md

  # 全プロファイル
  python improve_claude_md.py ~/.claude --profiles claude-md,skill-md,command-md

  # カスタム設定ファイル
  python improve_claude_md.py ~/prog --config my_rules.json

  # デフォルト設定を出力
  python improve_claude_md.py --dump-config
  """,
    )
    parser.add_argument(
        "source_dir", type=Path, nargs="?", default=Path.home() / "prog", help="検索元ディレクトリ (デフォルト: ~/prog)"
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path.home() / "prog" / "tmp_claude",
        help="作業ディレクトリ (デフォルト: ~/prog/tmp_claude)",
    )
    parser.add_argument("--config", type=Path, default=None, help="設定ファイルパス (JSON形式、省略時はデフォルト設定)")
    parser.add_argument(
        "--profiles", type=str, default=None, help="使用プロファイル (カンマ区切り、例: claude-md,skill-md,command-md)"
    )
    parser.add_argument("--dump-config", action="store_true", help="デフォルト設定をJSON形式で出力して終了")
    parser.add_argument("--no-prompt", action="store_true", help="AI依頼プロンプトを生成しない")
    parser.add_argument(
        "--output-json", action="store_true", help="manifest.json と個別プロンプトを出力 (自動パイプライン用)"
    )
    parser.add_argument(
        "--host-source-dir", type=str, default=None, help="ホスト側のsource_dirパス (Docker内パス→ホストパス変換用)"
    )
    parser.add_argument(
        "--host-work-dir", type=str, default=None, help="ホスト側のwork_dirパス (Docker内パス→ホストパス変換用)"
    )
    parser.add_argument("--create-sample", action="store_true", help="サンプルデータを作成して動作確認")

    args = parser.parse_args()

    # --dump-config: デフォルト設定を出力して終了
    if args.dump_config:
        print(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2))
        return

    # 設定ロード
    config = load_config(args.config)

    # プロファイル決定
    profiles = args.profiles.split(",") if args.profiles else ["claude-md"]

    # サンプルデータ作成
    if args.create_sample:
        console.print("[cyan]サンプルデータを作成中...[/cyan]")
        sample_dir = Path("/tmp/claude_sample_prog")
        sample_dir.mkdir(exist_ok=True)

        for sample in config.get("sample_projects", []):
            proj_dir = sample_dir / sample["name"]
            proj_dir.mkdir(exist_ok=True)
            filename = sample.get("filename", "CLAUDE.md")
            (proj_dir / filename).write_text(sample["content"])

        console.print(f"[green]✓[/green] サンプルデータ作成: {sample_dir}")
        args.source_dir = sample_dir
        args.work_dir = sample_dir / "tmp_claude"

    # 実行
    improver = CLAUDEMDImprover(
        args.source_dir,
        args.work_dir,
        config=config,
        profiles=profiles,
    )
    improver.run(
        dry_run=True,
        generate_prompt=not args.no_prompt,
        output_json=args.output_json,
        host_source_dir=args.host_source_dir,
        host_work_dir=args.host_work_dir,
    )

    # 最終メッセージ
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]✓ 処理完了[/bold cyan]")
    console.print("\n📦 成果物:")
    console.print(f"  - 作業ディレクトリ: {args.work_dir}")

    if not args.no_prompt:
        console.print(f"  - AI依頼プロンプト: {args.work_dir}/AI_IMPROVEMENT_REQUEST.md")

    zip_files = list(args.work_dir.glob("*_files_*.zip"))
    if zip_files:
        console.print(f"  - ZIPアーカイブ: {zip_files[-1]}")

    console.print("\n[bold yellow]次のステップ:[/bold yellow]")
    console.print("  1. AI_IMPROVEMENT_REQUEST.md を開く")
    console.print("  2. ZIPファイルと一緒にAIに送信")
    console.print("  3. AI改善後のファイルを受け取る")
    console.print("  4. 改善後のファイルを手動で上書き")


if __name__ == "__main__":
    main()

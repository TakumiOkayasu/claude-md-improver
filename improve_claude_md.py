#!/usr/bin/env python3
"""
CLAUDE.md品質改善ツール

機能:
1. ~/prog/以下のCLAUDE.mdを収集
2. (directory_name)_CLAUDE.mdにリネーム
3. 品質チェック・フォーマット統一
4. 内容の改善
5. 元の場所に戻す
"""

import json
import re
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

console = Console()


@dataclass
class CLAUDEFile:
    """CLAUDE.mdファイル情報"""
    original_path: Path
    backup_path: Path
    directory_name: str
    content: str
    issues: List[str]
    score: int

    @property
    def problem_issues(self) -> List[str]:
        """問題点のみ抽出 (❌/⚠️)"""
        return [i for i in self.issues if i.startswith("❌") or i.startswith("⚠️")]


class CLAUDEMDImprover:
    """CLAUDE.md改善クラス"""
    
    def __init__(self, source_dir: Path, work_dir: Path):
        self.source_dir = source_dir
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
    def find_claude_files(self) -> List[Path]:
        """CLAUDE.mdファイルを検索"""
        console.print("[cyan]CLAUDE.mdファイルを検索中...[/cyan]")
        files = list(self.source_dir.rglob("CLAUDE.md"))
        console.print(f"[green]✓[/green] {len(files)}個のファイルを発見")
        return files
    
    def backup_file(self, file_path: Path) -> Path:
        """ファイルをバックアップディレクトリにコピー"""
        # ディレクトリ名を取得
        dir_name = file_path.parent.name
        backup_name = f"{dir_name}_CLAUDE.md"
        backup_path = self.work_dir / backup_name
        
        # コピー
        shutil.copy2(file_path, backup_path)
        
        return backup_path
    
    def check_quality(self, content: str) -> Tuple[List[str], int]:
        """品質チェック"""
        issues = []
        score = 100
        
        # 必須セクションチェック
        required_sections = [
            (r"^#+ .*プロジェクト|^#+ .*Project", "プロジェクト概要"),
            (r"^#+ .*技術スタック|^#+ .*Tech Stack", "技術スタック"),
        ]
        
        for pattern, name in required_sections:
            if not re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                issues.append(f"❌ 必須セクション不足: {name}")
                score -= 15
        
        # 禁止事項の明確さ
        if "禁止" not in content and "NEVER" not in content:
            issues.append("⚠️  禁止事項が明示されていない")
            score -= 10
        
        # コマンド例の有無
        if "```" not in content:
            issues.append("⚠️  コード例・コマンド例が不足")
            score -= 10
        
        # 長すぎないか
        line_count = len(content.splitlines())
        if line_count > 500:
            issues.append(f"⚠️  ファイルが長すぎる: {line_count}行 (推奨: 500行以下)")
            score -= 5
        
        # 曖昧な表現チェック
        vague_patterns = [
            (r"できるだけ|なるべく|適宜", "曖昧な表現"),
            (r"多分|たぶん|おそらく", "不確実な表現"),
        ]
        
        for pattern, description in vague_patterns:
            if re.search(pattern, content):
                issues.append(f"⚠️  {description}が含まれている")
                score -= 5
        
        # 良い点も記録
        if re.search(r"^#+ .*例|^#+ .*Example", content, re.MULTILINE):
            issues.append("✅ 実例セクションあり")
        
        if "スキル" in content or "skill" in content.lower():
            issues.append("✅ スキル参照あり")
        
        return issues, max(0, min(100, score))
    
    def generate_single_file_prompt(self, file: CLAUDEFile) -> str:
        """単一ファイル用のAI改善プロンプトを生成"""
        issues_text = "\n".join(
            f"- {issue}" for issue in file.problem_issues
        )

        return f"""# CLAUDE.md改善依頼: {file.directory_name}

## 改善方針

### 必須対応
- 曖昧な表現を明確に (「できるだけ」→「必ず」、「多分」→削除)
- 禁止事項を明示 (具体的に、理由も記載)
- 技術スタックを明記
- コマンド例・コード例を追加

### 推奨対応
- プロジェクト概要を追加
- スキル参照を追加 (グローバルスキルへの参照)

### 禁止事項
- 既存の内容を勝手に削除しない
- プロジェクト固有の情報を推測で追加しない
- 不明な部分は [要確認] とマークする

## 品質基準

- AIが間違えない: 曖昧な指示は禁止、具体的なルールのみ
- AIがミスしない: チェックリスト形式、自己検証可能に
- AIがルールを守る: 禁止事項を明確に、理由も記載

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

改善後のCLAUDE.mdの内容のみを出力してください。説明やコメントは不要です。
マークダウン形式で、`#` から始めてください。
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
    
    def process_files(self, files: List[Path]) -> List[CLAUDEFile]:
        """ファイルを処理"""
        processed = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("処理中...", total=len(files))
            
            for file_path in files:
                # バックアップ
                backup_path = self.backup_file(file_path)
                dir_name = file_path.parent.name
                
                # 内容読み込み
                content = file_path.read_text(encoding="utf-8")
                
                # 品質チェック
                issues, score = self.check_quality(content)
                
                # 改善
                improved_content = self.improve_content(content, dir_name)
                
                # バックアップに改善版を保存
                backup_path.write_text(improved_content, encoding="utf-8")
                
                # 情報を記録
                processed.append(CLAUDEFile(
                    original_path=file_path,
                    backup_path=backup_path,
                    directory_name=dir_name,
                    content=improved_content,
                    issues=issues,
                    score=score
                ))
                
                progress.update(task, advance=1)
        
        return processed
    
    def show_report(self, processed: List[CLAUDEFile]):
        """レポート表示"""
        console.print("\n" + "="*80)
        console.print(Panel.fit(
            "[bold cyan]品質チェック・改善レポート[/bold cyan]",
            border_style="cyan"
        ))
        
        # サマリーテーブル
        table = Table(title="ファイル一覧", show_lines=True)
        table.add_column("プロジェクト", style="cyan")
        table.add_column("スコア", justify="center", style="yellow")
        table.add_column("状態", justify="center")
        table.add_column("パス")
        
        for file in processed:
            status = "🟢 良好" if file.score >= 80 else "🟡 要改善" if file.score >= 60 else "🔴 要修正"
            table.add_row(
                file.directory_name,
                f"{file.score}/100",
                status,
                str(file.original_path.relative_to(self.source_dir))
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
        """AI依頼用プロンプト生成"""
        prompt_parts = [
            "# CLAUDE.md品質改善依頼",
            "",
            "以下のローカルCLAUDE.mdファイルの品質を改善してください。",
            "",
            "## 改善方針",
            "",
            "### 必須対応",
            "- 曖昧な表現を明確に (「できるだけ」→「必ず」、「多分」→削除)",
            "- 禁止事項を明示 (具体的に、理由も記載)",
            "- 技術スタックを明記",
            "- コマンド例・コード例を追加",
            "",
            "### 推奨対応",
            "- プロジェクト概要を追加",
            "- スキル参照を追加 (グローバルスキルへの参照)",
            "- フロントマター追加 (project名, last_updated)",
            "",
            "### 禁止事項",
            "- 既存の内容を勝手に削除しない",
            "- プロジェクト固有の情報を推測で追加しない",
            "- 不明な部分は [要確認] とマークする",
            "",
            "## 品質基準",
            "",
            "- AIが間違えない: 曖昧な指示は禁止、具体的なルールのみ",
            "- AIがミスしない: チェックリスト形式、自己検証可能に",
            "- AIがルールを守る: 禁止事項を明確に、理由も記載",
            "",
            "---",
            "",
        ]
        
        for file in processed:
            prompt_parts.extend([
                f"## ファイル: {file.directory_name}_CLAUDE.md",
                "",
                f"**元のパス**: `{file.original_path}`",
                f"**品質スコア**: {file.score}/100",
                "",
                "**検出された問題**:",
            ])
            
            for issue in file.problem_issues:
                prompt_parts.append(f"- {issue}")
            
            prompt_parts.extend([
                "",
                "**現在の内容**:",
                "```markdown",
                file.content.strip(),
                "```",
                "",
                "---",
                "",
            ])
        
        prompt_parts.extend([
            "## 出力形式",
            "",
            "各ファイルについて、以下の形式で改善版を出力してください:",
            "",
            "```markdown",
            "### {directory_name}_CLAUDE.md",
            "",
            "[改善後の内容]",
            "```",
            "",
            "## 改善のポイント",
            "",
            "各ファイルの改善点を簡潔に説明してください。",
        ])
        
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
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.work_dir / f"claude_md_files_{timestamp}.zip"
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in processed:
                arcname = file.backup_path.name
                zipf.write(file.backup_path, arcname)
        
        return archive_path
    
    def run(
        self,
        dry_run: bool = True,
        generate_prompt: bool = True,
        output_json: bool = False,
        host_source_dir: str | None = None,
        host_work_dir: str | None = None,
    ) -> List[CLAUDEFile]:
        """メイン処理"""
        console.print(Panel.fit(
            "[bold]CLAUDE.md 品質改善ツール (AI支援版)[/bold]\n"
            f"対象: {self.source_dir}\n"
            f"作業: {self.work_dir}",
            border_style="blue"
        ))
        
        # ファイル検索
        files = self.find_claude_files()
        
        if not files:
            console.print("[yellow]⚠️  CLAUDE.mdファイルが見つかりませんでした[/yellow]")
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
                    original = original.replace(
                        str(self.source_dir), host_source_dir
                    )
                    backup = backup.replace(
                        str(self.work_dir), host_work_dir
                    )
                manifest.append({
                    "directory_name": file.directory_name,
                    "original_path": original,
                    "backup_path": backup,
                    "score": file.score,
                    "issues": file.problem_issues,
                })
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
        description="CLAUDE.md品質改善ツール (AI支援版)",
        epilog="""
使用例:
  # 1. CLAUDE.mdを収集して品質チェック
  python improve_claude_md.py
  
  # 2. 作業ディレクトリのZIPとAI依頼プロンプトを確認
  ls ~/prog/tmp_claude/
  
  # 3. ZIPとプロンプトをAIに渡して改善を依頼
  # (AI改善後のファイルを取得)
  
  # 4. 改善後のファイルを元の場所に手動で戻す
  """
    )
    parser.add_argument(
        "source_dir",
        type=Path,
        nargs="?",
        default=Path.home() / "prog",
        help="検索元ディレクトリ (デフォルト: ~/prog)"
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path.home() / "prog" / "tmp_claude",
        help="作業ディレクトリ (デフォルト: ~/prog/tmp_claude)"
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="AI依頼プロンプトを生成しない"
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="manifest.json と個別プロンプトを出力 (自動パイプライン用)"
    )
    parser.add_argument(
        "--host-source-dir",
        type=str,
        default=None,
        help="ホスト側のsource_dirパス (Docker内パス→ホストパス変換用)"
    )
    parser.add_argument(
        "--host-work-dir",
        type=str,
        default=None,
        help="ホスト側のwork_dirパス (Docker内パス→ホストパス変換用)"
    )
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="サンプルデータを作成して動作確認"
    )

    args = parser.parse_args()
    
    # サンプルデータ作成
    if args.create_sample:
        console.print("[cyan]サンプルデータを作成中...[/cyan]")
        sample_dir = Path("/tmp/claude_sample_prog")
        sample_dir.mkdir(exist_ok=True)
        
        # サンプルプロジェクト1
        (sample_dir / "project-a").mkdir(exist_ok=True)
        (sample_dir / "project-a" / "CLAUDE.md").write_text("""# Project A

これはプロジェクトAです。

できるだけPythonを使ってください。
多分FastAPIが良いと思います。
""")
        
        # サンプルプロジェクト2
        (sample_dir / "project-b").mkdir(exist_ok=True)
        (sample_dir / "project-b" / "CLAUDE.md").write_text("""# Project B

## 技術スタック
- TypeScript
- React

## 禁止事項
- グローバル変数の使用禁止
""")
        
        # サンプルプロジェクト3 (スコア低い)
        (sample_dir / "project-c").mkdir(exist_ok=True)
        (sample_dir / "project-c" / "CLAUDE.md").write_text("""# プロジェクトC

なるべくきれいに書いてください。
おそらく動くと思います。
""")
        
        console.print(f"[green]✓[/green] サンプルデータ作成: {sample_dir}")
        args.source_dir = sample_dir
        args.work_dir = sample_dir / "tmp_claude"
    
    # 実行
    improver = CLAUDEMDImprover(args.source_dir, args.work_dir)
    processed = improver.run(
        dry_run=True,
        generate_prompt=not args.no_prompt,
        output_json=args.output_json,
        host_source_dir=args.host_source_dir,
        host_work_dir=args.host_work_dir,
    )
    
    # 最終メッセージ
    console.print("\n" + "="*80)
    console.print("[bold cyan]✓ 処理完了[/bold cyan]")
    console.print(f"\n📦 成果物:")
    console.print(f"  - 作業ディレクトリ: {args.work_dir}")
    
    if not args.no_prompt:
        console.print(f"  - AI依頼プロンプト: {args.work_dir}/AI_IMPROVEMENT_REQUEST.md")
    
    # ZIPファイルを探す
    zip_files = list(args.work_dir.glob("claude_md_files_*.zip"))
    if zip_files:
        console.print(f"  - ZIPアーカイブ: {zip_files[-1]}")
    
    console.print("\n[bold yellow]次のステップ:[/bold yellow]")
    console.print("  1. AI_IMPROVEMENT_REQUEST.md を開く")
    console.print("  2. ZIPファイルと一緒にAIに送信")
    console.print("  3. AI改善後のファイルを受け取る")
    console.print("  4. 各プロジェクトのCLAUDE.mdに手動で上書き")


if __name__ == "__main__":
    main()

"""CLI エントリーポイント"""

import argparse
import json
from pathlib import Path
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import DEFAULT_CONFIG, load_config
from .models import TargetFile
from .pipeline import MdImprover

console = Console()


def show_report(processed: List[TargetFile], source_dir: Path) -> None:
    """レポート表示"""
    console.print("\n" + "=" * 80)
    console.print(
        Panel.fit(
            "[bold cyan]品質チェック・改善レポート[/bold cyan]",
            border_style="cyan",
        )
    )

    table = Table(title="ファイル一覧", show_lines=True)
    table.add_column("プロジェクト", style="cyan")
    table.add_column("スコア", justify="center", style="yellow")
    table.add_column("状態", justify="center")
    table.add_column("パス")

    for file in processed:
        if file.score >= 80:
            status = "🟢 良好"
        elif file.score >= 60:
            status = "🟡 要改善"
        else:
            status = "🔴 要修正"
        table.add_row(
            file.directory_name,
            f"{file.score}/100",
            status,
            str(file.original_path.relative_to(source_dir)),
        )

    console.print(table)

    for file in processed:
        console.print(f"\n[bold]📁 {file.directory_name}[/bold] (スコア: {file.score}/100)")
        console.print(f"   パス: {file.original_path}")
        console.print(f"   バックアップ: {file.backup_path}")

        if file.issues:
            console.print("   問題点:")
            for issue in file.issues:
                console.print(f"      {issue}")

    avg_score = sum(f.score for f in processed) / len(processed) if processed else 0
    console.print(f"\n[bold cyan]平均スコア:[/bold cyan] {avg_score:.1f}/100")


def main() -> None:
    """メイン関数"""
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
        "source_dir",
        type=Path,
        nargs="?",
        default=Path.home() / "prog",
        help="検索元ディレクトリ (デフォルト: ~/prog)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path.home() / "prog" / "tmp_claude",
        help="作業ディレクトリ (デフォルト: ~/prog/tmp_claude)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="設定ファイルパス (JSON形式、省略時はデフォルト設定)",
    )
    parser.add_argument(
        "--profiles",
        type=str,
        default=None,
        help="使用プロファイル (カンマ区切り、例: claude-md,skill-md,command-md)",
    )
    parser.add_argument(
        "--dump-config",
        action="store_true",
        help="デフォルト設定をJSON形式で出力して終了",
    )
    parser.add_argument("--no-prompt", action="store_true", help="AI依頼プロンプトを生成しない")
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="manifest.json と個別プロンプトを出力 (自動パイプライン用)",
    )
    parser.add_argument(
        "--host-source-dir",
        type=str,
        default=None,
        help="ホスト側のsource_dirパス (Docker内パス→ホストパス変換用)",
    )
    parser.add_argument(
        "--host-work-dir",
        type=str,
        default=None,
        help="ホスト側のwork_dirパス (Docker内パス→ホストパス変換用)",
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
    improver = MdImprover(
        args.source_dir,
        args.work_dir,
        config=config,
        profiles=profiles,
    )

    profiles_label = ", ".join(profiles)
    console.print(
        Panel.fit(
            f"[bold]AI設定ファイル品質改善ツール[/bold]\n"
            f"プロファイル: {profiles_label}\n"
            f"対象: {args.source_dir}\n"
            f"作業: {args.work_dir}",
            border_style="blue",
        )
    )

    processed = improver.run(
        generate_prompt=not args.no_prompt,
        output_json=args.output_json,
        host_source_dir=args.host_source_dir,
        host_work_dir=args.host_work_dir,
    )

    if not processed:
        console.print("[yellow]⚠️  対象ファイルが見つかりませんでした[/yellow]")
        return

    show_report(processed, args.source_dir)

    # アーカイブ作成
    console.print("\n[cyan]ZIPアーカイブを作成中...[/cyan]")
    archive_path = improver.create_archive(processed)
    console.print(f"[green]✓[/green] アーカイブ作成: {archive_path}")

    if args.output_json:
        manifest = args.work_dir / "manifest.json"
        console.print(f"[green]✓[/green] manifest.json 出力: {manifest}")

    # 最終メッセージ
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]✓ 処理完了[/bold cyan]")
    console.print(f"\n📦 成果物: {args.work_dir}")

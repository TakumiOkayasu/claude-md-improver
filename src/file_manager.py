"""ファイル探索・バックアップ・復元・アーカイブ"""

import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

from rich.console import Console

from .models import FoundFile, TargetFile

console = Console()


class FileManager:
    """ファイル探索・バックアップ・復元・アーカイブ管理"""

    def __init__(self, source_dir: Path, work_dir: Path, config: Dict[str, Any]):
        self.source_dir = source_dir
        self.work_dir = work_dir
        self.config = config

    def find(self, active_profiles: List[str]) -> List[FoundFile]:
        """対象ファイルを検索"""
        results: List[FoundFile] = []
        exclude: Set[str] = set(self.config.get("exclude_dirs", []))
        for pname in active_profiles:
            profile = self.config["profiles"][pname]
            pattern = profile["target_pattern"]
            display = profile["display_name"]
            console.print(f"[cyan]{display}ファイルを検索中...[/cyan]")
            files = []
            for f in self.source_dir.rglob(pattern):
                if not f.exists():
                    reason = "壊れたシンボリックリンク" if f.is_symlink() else "アクセス不可"
                    console.print(f"[yellow]⚠ スキップ ({reason}): {f}[/yellow]")
                    continue
                if any(part in exclude for part in f.parts):
                    continue
                files.append(f)
            for f in files:
                results.append(FoundFile(f, pname))
            console.print(f"[green]✓[/green] {len(files)}個の{display}を発見")
        return results

    def backup(self, file_path: Path) -> "tuple[Path, str]":
        """ファイルをバックアップし、(backup_path, directory_name) を返す"""
        dir_name = f"{file_path.parent.name}_{file_path.stem}"
        backup_name = f"{dir_name}{file_path.suffix}"
        backup_path = self.work_dir / backup_name
        shutil.copy2(file_path, backup_path)
        return backup_path, dir_name

    def restore(self, processed: List[TargetFile], dry_run: bool = True) -> None:
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

    def archive(self, processed: List[TargetFile], active_profiles: List[str]) -> Path:
        """ZIPアーカイブを作成"""
        profiles_tag = "_".join(sorted(active_profiles))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.work_dir / f"{profiles_tag}_files_{timestamp}.zip"

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in processed:
                arcname = file.backup_path.name
                zipf.write(file.backup_path, arcname)

        return archive_path

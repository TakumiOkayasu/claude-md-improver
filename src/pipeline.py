"""メインパイプライン（オーケストレーション）"""

import json
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import DEFAULT_CONFIG
from .file_manager import FileManager
from .models import FoundFile, TargetFile
from .prompt_generator import PromptGenerator
from .quality_checker import QualityChecker

console = Console()


class MdImprover:
    """AI設定ファイル改善パイプライン"""

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
        self.active_profiles = self._sort_by_specificity(self.active_profiles, self.config)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self._file_manager = FileManager(source_dir, work_dir, self.config)
        self._quality_checker = QualityChecker(self.config)
        self._prompt_generator = PromptGenerator(self.config, work_dir)

    @staticmethod
    def _sort_by_specificity(profiles: List[str], config: Dict[str, Any]) -> List[str]:
        """具体パターン優先でソート（ワイルドカードなし→あり、同一特異性は入力順維持）"""

        def _has_wildcard(pname: str) -> bool:
            pattern = config["profiles"][pname]["target_pattern"]
            return "*" in pattern or "?" in pattern or "[" in pattern

        return sorted(profiles, key=_has_wildcard)

    def find_files(self) -> List[FoundFile]:
        """対象ファイルを検索"""
        return self._file_manager.find(self.active_profiles)

    def process_files(self, files: List[FoundFile]) -> List[TargetFile]:
        """ファイルを処理"""
        processed = []

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("処理中...", total=len(files))

            for found in files:
                backup_path, dir_name = self._file_manager.backup(found.path)
                content = found.path.read_text(encoding="utf-8")
                issues, score = self._quality_checker.check(content, found.profile_name)

                processed.append(
                    TargetFile(
                        original_path=found.path,
                        backup_path=backup_path,
                        directory_name=dir_name,
                        content=content,
                        issues=issues,
                        score=score,
                        profile_name=found.profile_name,
                    )
                )

                progress.update(task, advance=1)

        return processed

    def output_manifest(
        self,
        processed: List[TargetFile],
        host_source_dir: "str | None" = None,
        host_work_dir: "str | None" = None,
    ) -> Path:
        """manifest.json + 個別プロンプトを出力"""
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
            self._prompt_generator.save_single(file)

        manifest_path = self.work_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest_path

    def create_archive(self, processed: List[TargetFile]) -> Path:
        """ZIPアーカイブを作成"""
        return self._file_manager.archive(processed, self.active_profiles)

    def run(
        self,
        generate_prompt: bool = True,
        output_json: bool = False,
        host_source_dir: "str | None" = None,
        host_work_dir: "str | None" = None,
    ) -> List[TargetFile]:
        """メイン処理（データ処理のみ。UI出力はcli.pyが担当）"""
        files = self.find_files()

        if not files:
            return []

        processed = self.process_files(files)

        if generate_prompt:
            prompt = self._prompt_generator.generate_batch(processed)
            self._prompt_generator.save_batch(prompt)

        if output_json:
            self.output_manifest(processed, host_source_dir, host_work_dir)

        return processed

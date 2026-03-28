"""データモデル定義"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, NamedTuple


class FoundFile(NamedTuple):
    """検索で見つかったファイル"""

    path: Path
    profile_name: str


@dataclass
class TargetFile:
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

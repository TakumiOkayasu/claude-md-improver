import json
from pathlib import Path

from improve_claude_md import CLAUDEFile, CLAUDEMDImprover


def _make_claude_file(
    tmp_path: Path,
    *,
    directory_name: str = "project-a",
    content: str = "# Project A\n\nSome content.",
    issues: list[str] | None = None,
    score: int = 85,
) -> CLAUDEFile:
    work_dir = tmp_path / "work"
    return CLAUDEFile(
        original_path=Path(f"/source/{directory_name}/CLAUDE.md"),
        backup_path=work_dir / f"{directory_name}_CLAUDE.md",
        directory_name=directory_name,
        content=content,
        issues=issues if issues is not None else [],
        score=score,
    )


class TestGenerateSingleFilePrompt:
    """generate_single_file_prompt のテスト"""

    def test_returns_prompt_string_from_claude_file(self, tmp_path: Path) -> None:
        """CLAUDEFileからプロンプト文字列を生成できる"""
        improver = CLAUDEMDImprover(source_dir=tmp_path, work_dir=tmp_path / "work")
        file = _make_claude_file(
            tmp_path, issues=["❌ 必須セクション不足: 技術スタック"]
        )

        result = improver.generate_single_file_prompt(file)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_prompt_contains_required_sections(self, tmp_path: Path) -> None:
        """プロンプトに改善方針・品質基準・問題点・内容が含まれる"""
        improver = CLAUDEMDImprover(source_dir=tmp_path, work_dir=tmp_path / "work")
        file = _make_claude_file(
            tmp_path,
            issues=["❌ 必須セクション不足: 技術スタック", "✅ 実例セクションあり"],
        )

        result = improver.generate_single_file_prompt(file)

        assert "改善方針" in result
        assert "品質基準" in result
        assert "❌ 必須セクション不足: 技術スタック" in result
        assert "✅ 実例セクションあり" not in result
        assert "# Project A" in result
        assert "Some content." in result
        assert "project-a" in result
        assert "85/100" in result

    def test_save_single_file_prompt(self, tmp_path: Path) -> None:
        """プロンプトファイルが {work_dir}/{dir_name}_PROMPT.md に保存される"""
        work_dir = tmp_path / "work"
        improver = CLAUDEMDImprover(source_dir=tmp_path, work_dir=work_dir)
        file = _make_claude_file(tmp_path, content="# Project A\n", score=100)

        improver.save_single_file_prompt(file)

        prompt_path = work_dir / "project-a_PROMPT.md"
        assert prompt_path.exists()
        content = prompt_path.read_text(encoding="utf-8")
        assert "project-a" in content


def _create_sample_projects(base_dir: Path) -> None:
    """テスト用のサンプルプロジェクトを作成"""
    for name in ("project-a", "project-b"):
        proj = base_dir / name
        proj.mkdir()
        (proj / "CLAUDE.md").write_text(f"# {name}\n\nContent for {name}.\n")


class TestOutputJson:
    """--output-json / manifest.json のテスト"""

    def test_run_output_json_creates_manifest(self, tmp_path: Path) -> None:
        """run(output_json=True) で manifest.json が出力される"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        _create_sample_projects(source_dir)
        work_dir = tmp_path / "work"

        improver = CLAUDEMDImprover(source_dir=source_dir, work_dir=work_dir)
        improver.run(output_json=True, generate_prompt=False)

        manifest_path = work_dir / "manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 2

    def test_manifest_contains_host_paths(self, tmp_path: Path) -> None:
        """manifest.json にhost pathが含まれる"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        _create_sample_projects(source_dir)
        work_dir = tmp_path / "work"

        improver = CLAUDEMDImprover(source_dir=source_dir, work_dir=work_dir)
        improver.run(
            output_json=True,
            generate_prompt=False,
            host_source_dir="/host/prog",
            host_work_dir="/host/work",
        )

        data = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
        for entry in data:
            assert entry["original_path"].startswith("/host/prog/")
            assert entry["backup_path"].startswith("/host/work/")

    def test_manifest_entries_have_required_fields(self, tmp_path: Path) -> None:
        """manifest.json の各エントリに必須フィールドが含まれる"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        _create_sample_projects(source_dir)
        work_dir = tmp_path / "work"

        improver = CLAUDEMDImprover(source_dir=source_dir, work_dir=work_dir)
        improver.run(output_json=True, generate_prompt=False)

        data = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
        required_keys = {"directory_name", "original_path", "backup_path", "score", "issues"}
        for entry in data:
            assert required_keys.issubset(entry.keys())
            assert isinstance(entry["score"], int)
            assert isinstance(entry["issues"], list)

import json
from pathlib import Path

from improve_claude_md import (
    DEFAULT_CONFIG,
    CLAUDEFile,
    CLAUDEMDImprover,
    _deep_merge,
    load_config,
)


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
        file = _make_claude_file(tmp_path, issues=["❌ 必須セクション不足: 技術スタック"])

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

    def test_manifest_contains_profile_name(self, tmp_path: Path) -> None:
        """manifest.json に profile_name フィールドが含まれる"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        _create_sample_projects(source_dir)
        work_dir = tmp_path / "work"

        improver = CLAUDEMDImprover(source_dir=source_dir, work_dir=work_dir)
        improver.run(output_json=True, generate_prompt=False)

        data = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
        for entry in data:
            assert entry["profile_name"] == "claude-md"


class TestDeepMerge:
    """_deep_merge のテスト"""

    def test_shallow_override(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 99}

    def test_nested_merge(self) -> None:
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 99}}
        result = _deep_merge(base, override)
        assert result == {"x": {"a": 1, "b": 99}}

    def test_list_replaced_not_merged(self) -> None:
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = _deep_merge(base, override)
        assert result == {"items": [4, 5]}


class TestLoadConfig:
    """load_config のテスト"""

    def test_default_config_without_file(self) -> None:
        """設定ファイルなしでデフォルト設定を返す"""
        config = load_config(None)
        assert config["profiles"]["claude-md"]["target_pattern"] == "CLAUDE.md"
        assert "skill-md" in config["profiles"]
        assert "command-md" in config["profiles"]

    def test_custom_config_merges(self, tmp_path: Path) -> None:
        """カスタム設定がデフォルトにマージされる"""
        config_file = tmp_path / "custom.json"
        custom = {"profiles": {"claude-md": {"quality_rules": {"max_lines": 999}}}}
        config_file.write_text(json.dumps(custom), encoding="utf-8")

        config = load_config(config_file)
        # カスタム値が反映
        assert config["profiles"]["claude-md"]["quality_rules"]["max_lines"] == 999
        # デフォルト値が残る
        assert config["profiles"]["skill-md"]["target_pattern"] == "SKILL.md"

    def test_nonexistent_file_returns_default(self, tmp_path: Path) -> None:
        """存在しないファイルを指定するとデフォルト設定を返す"""
        config = load_config(tmp_path / "nonexistent.json")
        assert config == DEFAULT_CONFIG


class TestProfiles:
    """複数プロファイルのテスト"""

    def test_find_skill_md_files(self, tmp_path: Path) -> None:
        """skill-md プロファイルで SKILL.md が見つかる"""
        source_dir = tmp_path / "source"
        skill_dir = source_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# My Skill\n\n## トリガー条件\ntest\n")

        improver = CLAUDEMDImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["skill-md"],
        )
        files = improver.find_claude_files()
        assert len(files) == 1
        assert files[0][0].name == "SKILL.md"
        assert files[0][1] == "skill-md"

    def test_multiple_profiles(self, tmp_path: Path) -> None:
        """複数プロファイルで両方のファイルが見つかる"""
        source_dir = tmp_path / "source"
        (source_dir / "proj").mkdir(parents=True)
        (source_dir / "proj" / "CLAUDE.md").write_text("# Proj\n")
        (source_dir / "skill").mkdir(parents=True)
        (source_dir / "skill" / "SKILL.md").write_text("# Skill\n")

        improver = CLAUDEMDImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["claude-md", "skill-md"],
        )
        files = improver.find_claude_files()
        names = {f[0].name for f in files}
        assert names == {"CLAUDE.md", "SKILL.md"}

    def test_skill_md_quality_rules_applied(self, tmp_path: Path) -> None:
        """skill-md プロファイルのルールが適用される"""
        improver = CLAUDEMDImprover(
            source_dir=tmp_path,
            work_dir=tmp_path / "work",
            profiles=["skill-md"],
        )
        content = "# My Skill\n\nSome content without required sections.\n"
        issues, score = improver.check_quality(content, "skill-md")

        # トリガー条件と手順/フェーズが不足として検出
        issue_text = " ".join(issues)
        assert "トリガー条件" in issue_text
        assert "手順/フェーズ" in issue_text
        assert score < 100

    def test_command_md_quality_rules_applied(self, tmp_path: Path) -> None:
        """command-md プロファイルのルールが適用される"""
        improver = CLAUDEMDImprover(
            source_dir=tmp_path,
            work_dir=tmp_path / "work",
            profiles=["command-md"],
        )
        content = "# My Command\n\n手順: step 1\n入力: args\n"
        issues, _score = improver.check_quality(content, "command-md")

        # 良い点が検出される
        issue_text = " ".join(issues)
        assert "手順の記述あり" in issue_text
        assert "入出力の明示あり" in issue_text

    def test_profile_name_in_claude_file(self, tmp_path: Path) -> None:
        """process_files で profile_name が CLAUDEFile に設定される"""
        source_dir = tmp_path / "source"
        skill_dir = source_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill\n")

        improver = CLAUDEMDImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["skill-md"],
        )
        files = improver.find_claude_files()
        processed = improver.process_files(files)
        assert len(processed) == 1
        assert processed[0].profile_name == "skill-md"

    def test_prompt_uses_profile_template(self, tmp_path: Path) -> None:
        """generate_single_file_prompt がプロファイルのテンプレートを使う"""
        improver = CLAUDEMDImprover(
            source_dir=tmp_path,
            work_dir=tmp_path / "work",
            profiles=["skill-md"],
        )
        file = CLAUDEFile(
            original_path=Path("/source/my-skill/SKILL.md"),
            backup_path=tmp_path / "work" / "my-skill_SKILL.md",
            directory_name="my-skill",
            content="# Skill\n",
            issues=["❌ 必須セクション不足: トリガー条件"],
            score=60,
            profile_name="skill-md",
        )

        result = improver.generate_single_file_prompt(file)
        assert "SKILL.md改善依頼" in result
        assert "トリガー条件を明確に" in result
        assert "トリガー条件" in result

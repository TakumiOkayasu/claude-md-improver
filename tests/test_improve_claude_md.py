import json
from pathlib import Path

from src import (
    DEFAULT_CONFIG,
    MdImprover,
    TargetFile,
    _deep_merge,
    load_config,
)
from src.prompt_generator import PromptGenerator
from src.quality_checker import QualityChecker


def _make_target_file(
    tmp_path: Path,
    *,
    directory_name: str = "project-a",
    content: str = "# Project A\n\nSome content.",
    issues: list[str] | None = None,
    score: int = 85,
) -> TargetFile:
    work_dir = tmp_path / "work"
    return TargetFile(
        original_path=Path(f"/source/{directory_name}/CLAUDE.md"),
        backup_path=work_dir / f"{directory_name}_CLAUDE.md",
        directory_name=directory_name,
        content=content,
        issues=issues if issues is not None else [],
        score=score,
    )


class TestGenerateSingleFilePrompt:
    """generate_single_prompt のテスト"""

    def test_returns_prompt_string_from_target_file(self, tmp_path: Path) -> None:
        """TargetFileからプロンプト文字列を生成できる"""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        generator = PromptGenerator(DEFAULT_CONFIG, work_dir)
        file = _make_target_file(tmp_path, issues=["❌ 必須セクション不足: 技術スタック"])

        result = generator.generate_single(file)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_prompt_contains_required_sections(self, tmp_path: Path) -> None:
        """プロンプトに改善方針・品質基準・問題点・内容が含まれる"""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        generator = PromptGenerator(DEFAULT_CONFIG, work_dir)
        file = _make_target_file(
            tmp_path,
            issues=["❌ 必須セクション不足: 技術スタック", "✅ 実例セクションあり"],
        )

        result = generator.generate_single(file)

        assert "改善方針" in result
        assert "品質基準" in result
        assert "❌ 必須セクション不足: 技術スタック" in result
        assert "✅ 実例セクションあり" not in result
        assert "# Project A" in result
        assert "Some content." in result
        assert "project-a" in result
        assert "85/100" in result

    def test_save_single_prompt(self, tmp_path: Path) -> None:
        """プロンプトファイルが {work_dir}/{dir_name}_PROMPT.md に保存される"""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        generator = PromptGenerator(DEFAULT_CONFIG, work_dir)
        file = _make_target_file(tmp_path, content="# Project A\n", score=100)

        generator.save_single(file)

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

        improver = MdImprover(source_dir=source_dir, work_dir=work_dir)
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

        improver = MdImprover(source_dir=source_dir, work_dir=work_dir)
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

        improver = MdImprover(source_dir=source_dir, work_dir=work_dir)
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

        improver = MdImprover(source_dir=source_dir, work_dir=work_dir)
        improver.run(output_json=True, generate_prompt=False)

        data = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
        for entry in data:
            assert entry["profile_name"] == "claude-md"


class TestDirectoryNameCollision:
    """directory_name 衝突バグの再現テスト"""

    def _create_commands_dir(self, source_dir: Path) -> None:
        """同一ディレクトリに複数 .md ファイルを作成"""
        commands = source_dir / "commands"
        commands.mkdir(parents=True)
        (commands / "fix.md").write_text("# バグ修正ガイド\n\n修正手順を説明。\n")
        (commands / "feat.md").write_text("# 機能実装ガイド\n\nTDDで実装。\n")
        (commands / "commit.md").write_text("# コミット準備\n\nコミットメッセージを生成。\n")

    def test_manifest_directory_names_are_unique(self, tmp_path: Path) -> None:
        """同一ディレクトリ内の複数ファイルで directory_name が全て異なる"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        self._create_commands_dir(source_dir)
        work_dir = tmp_path / "work"

        improver = MdImprover(source_dir=source_dir, work_dir=work_dir, profiles=["command-md"])
        improver.run(output_json=True, generate_prompt=False)

        data = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
        dir_names = [entry["directory_name"] for entry in data]
        assert len(dir_names) == len(set(dir_names)), f"directory_name に重複あり: {dir_names}"

    def test_prompt_files_created_per_file(self, tmp_path: Path) -> None:
        """同一ディレクトリ内の各ファイルに個別の _PROMPT.md が生成される"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        self._create_commands_dir(source_dir)
        work_dir = tmp_path / "work"

        improver = MdImprover(source_dir=source_dir, work_dir=work_dir, profiles=["command-md"])
        improver.run(output_json=True, generate_prompt=False)

        prompt_files = list(work_dir.glob("*_PROMPT.md"))
        data = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
        assert len(prompt_files) == len(data), (
            f"PROMPTファイル数({len(prompt_files)}) != manifestエントリ数({len(data)})"
        )

    def test_each_prompt_contains_correct_content(self, tmp_path: Path) -> None:
        """各PROMPTファイルが対応するファイルの内容を含む"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        self._create_commands_dir(source_dir)
        work_dir = tmp_path / "work"

        improver = MdImprover(source_dir=source_dir, work_dir=work_dir, profiles=["command-md"])
        improver.run(output_json=True, generate_prompt=False)

        data = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
        for entry in data:
            prompt_path = work_dir / f"{entry['directory_name']}_PROMPT.md"
            assert prompt_path.exists(), f"{prompt_path} が存在しない"
            prompt_content = prompt_path.read_text(encoding="utf-8")
            original_content = Path(entry["original_path"]).read_text(encoding="utf-8")
            first_line = original_content.splitlines()[0]
            assert first_line in prompt_content, f"{entry['directory_name']} のPROMPTに元ファイルの内容がない"


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

        improver = MdImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["skill-md"],
        )
        files = improver.find_files()
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

        improver = MdImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["claude-md", "skill-md"],
        )
        files = improver.find_files()
        names = {f[0].name for f in files}
        assert names == {"CLAUDE.md", "SKILL.md"}

    def test_skill_md_quality_rules_applied(self, tmp_path: Path) -> None:
        """skill-md プロファイルのルールが適用される"""
        checker = QualityChecker(DEFAULT_CONFIG)
        content = "# My Skill\n\nSome content without required sections.\n"
        issues, score = checker.check(content, "skill-md")

        issue_text = " ".join(issues)
        assert "トリガー条件" in issue_text
        assert "手順/フェーズ" in issue_text
        assert score < 100

    def test_command_md_quality_rules_applied(self, tmp_path: Path) -> None:
        """command-md プロファイルのルールが適用される"""
        checker = QualityChecker(DEFAULT_CONFIG)
        content = "# My Command\n\n手順: step 1\n入力: args\n"
        issues, _score = checker.check(content, "command-md")

        issue_text = " ".join(issues)
        assert "手順の記述あり" in issue_text
        assert "入出力の明示あり" in issue_text

    def test_profile_name_in_claude_file(self, tmp_path: Path) -> None:
        """process_files で profile_name が TargetFile に設定される"""
        source_dir = tmp_path / "source"
        skill_dir = source_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill\n")

        improver = MdImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["skill-md"],
        )
        files = improver.find_files()
        processed = improver.process_files(files)
        assert len(processed) == 1
        assert processed[0].profile_name == "skill-md"

    def test_broken_symlink_skipped(self, tmp_path: Path) -> None:
        """壊れたシンボリックリンクは除外される"""
        source_dir = tmp_path / "source"
        proj_dir = source_dir / "proj"
        proj_dir.mkdir(parents=True)
        (proj_dir / "CLAUDE.md").write_text("# Proj\n")

        # 壊れたシンボリックリンクを作成（リンク先が存在しない）
        broken_dir = source_dir / "broken"
        broken_dir.mkdir()
        (broken_dir / "CLAUDE.md").symlink_to("/nonexistent/path/CLAUDE.md")

        improver = MdImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
        )
        files = improver.find_files()

        # 壊れたシンボリックリンクは除外され、有効なファイルのみ返る
        assert len(files) == 1
        assert files[0][0].name == "CLAUDE.md"
        assert "proj" in str(files[0][0])

    def test_multi_profile_no_duplicate_files(self, tmp_path: Path) -> None:
        """3プロファイル同時使用で同一ファイルが重複しない"""
        source_dir = tmp_path / "source"
        skill_dir = source_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill\n")
        proj_dir = source_dir / "proj"
        proj_dir.mkdir(parents=True)
        (proj_dir / "CLAUDE.md").write_text("# Proj\n")

        improver = MdImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["claude-md", "skill-md", "command-md"],
        )
        files = improver.find_files()
        paths = [f.path for f in files]
        assert len(paths) == len(set(paths)), f"重複あり: {paths}"
        profiles = {f.path.name: f.profile_name for f in files}
        assert profiles["CLAUDE.md"] == "claude-md"
        assert profiles["SKILL.md"] == "skill-md"

    def test_command_md_does_not_rematch_skill_md(self, tmp_path: Path) -> None:
        """SKILL.mdはskill-mdでマッチ済みならcommand-mdでマッチしない"""
        source_dir = tmp_path / "source"
        skill_dir = source_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill\n")
        commands_dir = source_dir / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "fix.md").write_text("# Fix\n")

        improver = MdImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["skill-md", "command-md"],
        )
        files = improver.find_files()
        profiles = {f.path.name: f.profile_name for f in files}
        assert profiles["SKILL.md"] == "skill-md"
        assert profiles["fix.md"] == "command-md"
        assert len(files) == 2

    def test_symlink_to_same_file_not_duplicated(self, tmp_path: Path) -> None:
        """シンボリックリンク経由で同一ファイルを指す場合、重複しない"""
        source_dir = tmp_path / "source"
        skill_dir = source_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        original = skill_dir / "SKILL.md"
        original.write_text("# Skill\n")
        link_dir = source_dir / "link-skill"
        link_dir.mkdir(parents=True)
        (link_dir / "SKILL.md").symlink_to(original)

        improver = MdImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["skill-md"],
        )
        files = improver.find_files()
        assert len(files) == 1

    def test_profile_priority_order_is_deterministic(self, tmp_path: Path) -> None:
        """プロファイル指定順に関係なく、具体パターンが優先される"""
        source_dir = tmp_path / "source"
        skill_dir = source_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill\n")

        improver = MdImprover(
            source_dir=source_dir,
            work_dir=tmp_path / "work",
            profiles=["command-md", "skill-md"],
        )
        files = improver.find_files()
        assert len(files) == 1
        assert files[0].profile_name == "skill-md"

    def test_prompt_uses_profile_template(self, tmp_path: Path) -> None:
        """PromptGenerator がプロファイルのテンプレートを使う"""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        generator = PromptGenerator(DEFAULT_CONFIG, work_dir)
        file = TargetFile(
            original_path=Path("/source/my-skill/SKILL.md"),
            backup_path=work_dir / "my-skill_SKILL.md",
            directory_name="my-skill",
            content="# Skill\n",
            issues=["❌ 必須セクション不足: トリガー条件"],
            score=60,
            profile_name="skill-md",
        )

        result = generator.generate_single(file)
        assert "SKILL.md改善依頼" in result
        assert "トリガー条件を明確に" in result
        assert "トリガー条件" in result

"""品質チェック・スコアリング"""

import re
from typing import Any, Dict, List, Tuple


class QualityChecker:
    """プロファイル別の品質チェックを実行"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def check(self, content: str, profile_name: str = "claude-md") -> Tuple[List[str], int]:
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

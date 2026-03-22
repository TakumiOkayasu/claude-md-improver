#!/bin/bash

# CLAUDE.md品質改善ツール 実行スクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# 色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  CLAUDE.md 品質改善ツール (AI支援版)${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# uvのチェック
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  uvがインストールされていません${NC}"
    echo "インストール方法: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 仮想環境作成
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BLUE}仮想環境を作成中...${NC}"
    cd "$SCRIPT_DIR"
    uv venv --python 3.10
    echo -e "${GREEN}✓ 仮想環境作成完了${NC}"
fi

# 依存関係インストール (requirements.txt経由)
echo -e "${BLUE}依存関係をインストール中...${NC}"
source "$VENV_DIR/bin/activate"
uv pip install -r "$SCRIPT_DIR/requirements.txt" -q
echo -e "${GREEN}✓ 依存関係インストール完了${NC}"
echo ""

# Pythonスクリプト実行
python "$SCRIPT_DIR/improve_claude_md.py" "$@"

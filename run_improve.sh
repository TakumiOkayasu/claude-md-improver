#!/bin/bash
set -euo pipefail

# AI設定ファイル自動改善パイプライン
# Phase 1: 収集+採点 (Docker)
# Phase 2: AI改善 (claude CLI)
# Phase 3: diff プレビュー
# Phase 4: バックアップ + 上書き

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DOCKER_UID="$(id -u)"
export DOCKER_GID="$(id -g)"
SOURCE_DIR="${1:-$HOME/prog}"
WORK_DIR="${2:-$HOME/prog/tmp_claude}"
shift 2 2>/dev/null || true
EXTRA_ARGS=("$@")
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# 色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  AI設定ファイル自動改善パイプライン${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "  対象: ${SOURCE_DIR}"
echo -e "  作業: ${WORK_DIR}"
echo ""

# jaq (Rust製) 優先、なければ jq にフォールバック
if command -v jaq &>/dev/null; then
  JQ=jaq
elif command -v jq &>/dev/null; then
  JQ=jq
else
  echo -e "${RED}jaq または jq が必要です${NC}" >&2
  exit 1
fi

# manifest.json からエントリを読み取るヘルパー
# $1: jq フィルタ式
manifest_entries() {
  "$JQ" -r "$1" "${WORK_DIR}/manifest.json"
}

# ==============================
# Phase 1: 収集+採点 (Docker)
# ==============================
echo -e "${BLUE}[Phase 1] 収集+採点${NC}"

mkdir -p "${WORK_DIR}"

docker compose -f "${SCRIPT_DIR}/compose.yaml" run --rm \
  -e "SOURCE_DIR=${SOURCE_DIR}" \
  -e "WORK_DIR=${WORK_DIR}" \
  improve \
  python improve_claude_md.py /source \
    --work-dir /work \
    --output-json \
    --host-source-dir "${SOURCE_DIR}" \
    --host-work-dir "${WORK_DIR}" \
    --no-prompt "${EXTRA_ARGS[@]}"

if [ ! -f "${WORK_DIR}/manifest.json" ]; then
  echo -e "${RED}manifest.json が見つかりません。Phase 1 失敗。${NC}"
  exit 1
fi

FILE_COUNT=$("$JQ" 'length' "${WORK_DIR}/manifest.json")
echo -e "${GREEN}✓ ${FILE_COUNT}個のファイルを処理${NC}"
echo ""

# ==============================
# Phase 2: AI改善 (claude CLI)
# ==============================
echo -e "${BLUE}[Phase 2] AI改善${NC}"

SYSTEM_PROMPT="あなたはAI設定ファイルの品質改善専門家です。入力されたプロンプトに従い、改善後のファイルの内容のみを出力してください。説明やコメントは不要です。マークダウン形式で、# から始めてください。"

while read -r DIR_NAME; do
  PROMPT_FILE="${WORK_DIR}/${DIR_NAME}_PROMPT.md"
  IMPROVED_FILE="${WORK_DIR}/${DIR_NAME}_IMPROVED.md"

  if [ ! -f "${PROMPT_FILE}" ]; then
    echo -e "${YELLOW}  ⚠ ${DIR_NAME}: プロンプトファイルなし、スキップ${NC}"
    continue
  fi

  echo -n "  処理中: ${DIR_NAME} ... "

  # claude CLI で改善
  if claude --print \
    --model sonnet \
    --tools "" \
    --output-format text \
    --system-prompt "${SYSTEM_PROMPT}" \
    < "${PROMPT_FILE}" \
    > "${IMPROVED_FILE}" 2>"${WORK_DIR}/${DIR_NAME}_ERROR.log"; then

    # サニティチェック
    LINE_COUNT=$(wc -l < "${IMPROVED_FILE}" | tr -d ' ')
    FIRST_CHAR=$(head -c 1 "${IMPROVED_FILE}")

    if [ "${LINE_COUNT}" -lt 10 ]; then
      echo -e "${YELLOW}⚠ 出力が短すぎる (${LINE_COUNT}行)、スキップ${NC}"
      rm -f "${IMPROVED_FILE}"
      continue
    fi

    if [ "${FIRST_CHAR}" != "#" ]; then
      echo -e "${YELLOW}⚠ マークダウンヘッダーなし、スキップ${NC}"
      rm -f "${IMPROVED_FILE}"
      continue
    fi

    echo -e "${GREEN}✓${NC}"
  else
    echo -e "${RED}✗ claude CLI エラー${NC}"
    rm -f "${IMPROVED_FILE}"
    continue
  fi

  # レートリミット対策
  sleep 2
done < <(manifest_entries '.[].directory_name')

echo ""

# ==============================
# Phase 3: diff プレビュー
# ==============================
echo -e "${BLUE}[Phase 3] 差分プレビュー${NC}"
echo ""

while IFS='|' read -r DIR_NAME ORIGINAL_PATH; do
  IMPROVED_FILE="${WORK_DIR}/${DIR_NAME}_IMPROVED.md"

  if [ ! -f "${IMPROVED_FILE}" ]; then
    continue
  fi

  echo -e "${BLUE}--- ${DIR_NAME} ---${NC}"
  diff --color=always "${ORIGINAL_PATH}" "${IMPROVED_FILE}" || true
  echo ""
done < <(manifest_entries '.[] | "\(.directory_name)|\(.original_path)"')

# ==============================
# Phase 4: バックアップ + 上書き
# ==============================
echo -e "${BLUE}[Phase 4] バックアップ + 上書き${NC}"

BACKUP_DIR="${WORK_DIR}/backups_${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

while IFS='|' read -r DIR_NAME ORIGINAL_PATH; do
  IMPROVED_FILE="${WORK_DIR}/${DIR_NAME}_IMPROVED.md"

  if [ ! -f "${IMPROVED_FILE}" ]; then
    continue
  fi

  # バックアップ
  ORIG_FILENAME="$(basename "${ORIGINAL_PATH}")"
  cp "${ORIGINAL_PATH}" "${BACKUP_DIR}/${DIR_NAME}_${ORIG_FILENAME}"

  # 上書き
  cp "${IMPROVED_FILE}" "${ORIGINAL_PATH}"
  echo -e "  ${GREEN}✓${NC} ${DIR_NAME}: 適用完了"
done < <(manifest_entries '.[] | "\(.directory_name)|\(.original_path)"')

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✓ パイプライン完了${NC}"
echo -e "  バックアップ: ${BACKUP_DIR}"
echo -e "${BLUE}================================================${NC}"

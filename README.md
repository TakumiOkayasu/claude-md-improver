# CLAUDE.md 品質改善ツール (AI支援版)

`~/prog/` 以下のローカル `CLAUDE.md` を収集し、ZIP化してAIに改善を依頼するツール

## 概要

このツールは**AI (Claude) に改善作業を依頼する**ためのヘルパーです。

### ワークフロー

```
1. [ツール] CLAUDE.mdを収集 → ZIP化
2. [ツール] 品質チェック → AI依頼プロンプト生成
3. [人間]   ZIPとプロンプトをAIに送信
4. [AI]     各CLAUDE.mdを改善して返却
5. [人間]   改善版を各プロジェクトに配置
```

## 機能

1. **CLAUDE.md収集**: `~/prog/` 以下の全CLAUDE.mdを検索
2. **リネーム**: `(directory_name)_CLAUDE.md` に変更
3. **品質チェック**: 必須セクション、禁止事項、曖昧な表現をチェック
4. **ZIP化**: 全ファイルをZIPアーカイブに圧縮
5. **AI依頼プロンプト生成**: 改善指示を含むプロンプトを自動生成

## セットアップ

### 必要要件

- Python 3.10+
- uv

### インストール

```bash
# ZIPを展開
unzip claude-md-improver.zip
cd claude_md_improver

# 実行スクリプトで自動セットアップ
chmod +x run.sh
./run.sh

# または手動セットアップ
uv venv --python 3.10
source .venv/bin/activate
uv pip install -r requirements.txt
python improve_claude_md.py
```

## 使用方法

### 基本的な使い方

```bash
# 1. CLAUDE.mdを収集して品質チェック + ZIP化
python improve_claude_md.py

# 2. 出力ファイルを確認
ls ~/prog/tmp_claude/
# - AI_IMPROVEMENT_REQUEST.md  (AI依頼プロンプト)
# - claude_md_files_*.zip       (全CLAUDE.mdのZIP)
# - *_CLAUDE.md                 (個別ファイル)

# 3. AI_IMPROVEMENT_REQUEST.mdとZIPをAIに送信
# (AIに改善を依頼)

# 4. AI改善後のファイルを各プロジェクトに配置
cp ~/prog/tmp_claude/project-a_CLAUDE.md ~/prog/project-a/CLAUDE.md
cp ~/prog/tmp_claude/project-b_CLAUDE.md ~/prog/project-b/CLAUDE.md
```

### サンプルデータで動作確認

```bash
# サンプルデータ作成して実行
python improve_claude_md.py --create-sample

# 出力確認
cat /tmp/claude_sample_prog/tmp_claude/AI_IMPROVEMENT_REQUEST.md
unzip -l /tmp/claude_sample_prog/tmp_claude/claude_md_files_*.zip
```

### オプション

- `source_dir`: 検索元ディレクトリ (デフォルト: ~/prog)
- `--work-dir`: 作業ディレクトリ (デフォルト: ~/prog/tmp_claude)
- `--no-prompt`: AI依頼プロンプトを生成しない
- `--create-sample`: サンプルデータで動作確認

## 品質チェック項目

### 必須セクション

- プロジェクト概要
- 技術スタック

### 推奨事項

- 禁止事項の明示
- コード例・コマンド例
- 実例セクション
- スキル参照

### 避けるべき表現

- 曖昧な表現: "できるだけ", "なるべく", "適宜"
- 不確実な表現: "多分", "たぶん", "おそらく"

### スコアリング

- 100点: 完璧
- 80点以上: 良好
- 60-79点: 要改善
- 60点未満: 要修正

## AI改善の指示内容

AI依頼プロンプトには以下の改善指示が含まれます:

### 必須対応

1. **曖昧な表現を明確に**
   - "できるだけ" → "必ず"
   - "なるべく" → "必ず"  
   - "多分", "たぶん", "おそらく" → 削除

2. **禁止事項を明示**
   - 具体的に記述
   - 理由も記載
   - 例: "グローバル変数禁止 (保守性低下のため)"

3. **技術スタックを明記**
   - 使用言語・フレームワーク
   - バージョン情報

4. **コマンド例・コード例を追加**
   - 実行可能な形式
   - コメント付き

### 推奨対応

1. **プロジェクト概要を追加**
2. **スキル参照を追加** (グローバルスキルへの参照)
3. **フロントマター追加**
   ```yaml
   ---
   project: project-name
   last_updated: 2025-01-17
   ---
   ```

### 禁止事項 (AIへの指示)

- 既存の内容を勝手に削除しない
- プロジェクト固有の情報を推測で追加しない
- 不明な部分は `[要確認]` とマークする

## AI改善の品質基準

**AIが間違えない・ミスしない・ルールを守る** ための基準:

1. **曖昧な指示は禁止**: 具体的なルールのみ記述
2. **チェックリスト形式**: AIが自己検証可能に
3. **禁止事項を明確に**: 理由も併記

## 出力例

```
================================================================================
                     品質チェック・改善レポート                      
================================================================================

                               ファイル一覧                                
┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ プロジェクト ┃ スコア ┃   状態   ┃ パス                     ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ project-a    │ 65/100 │ 🟡 要改善 │ project-a/CLAUDE.md     │
│ project-b    │ 85/100 │ 🟢 良好   │ project-b/CLAUDE.md     │
└──────────────┴────────┴──────────┴─────────────────────────┘

📁 project-a (スコア: 65/100)
   パス: /tmp/claude_sample_prog/project-a/CLAUDE.md
   バックアップ: /tmp/claude_sample_prog/tmp_claude/project-a_CLAUDE.md
   問題点:
      ❌ 必須セクション不足: 技術スタック
      ⚠️  曖昧な表現が含まれている
      ⚠️  不確実な表現が含まれている

平均スコア: 75.0/100
```

## ワークフロー詳細

### ステップ1: ツール実行

```bash
python improve_claude_md.py
```

**出力**:
- `~/prog/tmp_claude/AI_IMPROVEMENT_REQUEST.md` - AI依頼プロンプト
- `~/prog/tmp_claude/claude_md_files_*.zip` - 全CLAUDE.mdのZIP
- `~/prog/tmp_claude/*_CLAUDE.md` - 個別ファイル (バックアップ)

### ステップ2: 品質レポート確認

ツールが表示する品質レポートを確認:

```
                       ファイル一覧                        
┏━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ プロジェクト ┃ スコア ┃   状態    ┃ パス                ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ project-b    │ 90/100 │  🟢 良好  │ project-b/CLAUDE.md │
│ project-a    │ 55/100 │ 🔴 要修正 │ project-a/CLAUDE.md │
└──────────────┴────────┴───────────┴─────────────────────┘
```

### ステップ3: AIに依頼

1. `AI_IMPROVEMENT_REQUEST.md` を開く
2. ZIPファイルをアップロード
3. プロンプトをAIに送信
4. AI改善版を受け取る

### ステップ4: 改善版を配置

```bash
# AI改善後のファイルを各プロジェクトに配置
cp project-a_CLAUDE_improved.md ~/prog/project-a/CLAUDE.md
cp project-b_CLAUDE_improved.md ~/prog/project-b/CLAUDE.md
```

### ステップ5: 動作確認

```bash
# 各プロジェクトで確認
cd ~/prog/project-a
cat CLAUDE.md

# 問題なければcommit
git add CLAUDE.md
git commit -m "improve: CLAUDE.mdの品質改善"
```

## 注意事項

- バックアップは `work_dir` に保存されます
- `--apply` なしでは元のファイルは変更されません
- 改善内容は保守的 (既存内容の削除はしない)
- 自動修正が不適切な場合は手動で調整してください

## トラブルシューティング

### ファイルが見つからない

```bash
# ディレクトリを確認
ls ~/prog/
find ~/prog -name "CLAUDE.md"
```

### 権限エラー

```bash
# 権限確認
ls -la ~/prog/project-a/CLAUDE.md

# 権限付与
chmod 644 ~/prog/project-a/CLAUDE.md
```

### Python 3.14が見つからない

```bash
# uvでPython 3.14をインストール
uv python install 3.14

# 環境作成
uv venv --python 3.14
```

## ライセンス

MIT License

## 貢献

Issue / Pull Request 歓迎

# クイックスタート

## 1分で始める

```bash
# 1. 展開
unzip claude-md-improver.zip
cd claude_md_improver

# 2. 実行
./run.sh

# 3. 出力確認
ls ~/prog/tmp_claude/
```

## 何が起きる?

1. `~/prog/` 以下の全CLAUDE.mdを検索
2. 品質チェック (スコア0-100)
3. ZIP化 + AI依頼プロンプト生成

## 出力ファイル

```
~/prog/tmp_claude/
├── AI_IMPROVEMENT_REQUEST.md           # これをAIに送る
├── claude_md_files_YYYYMMDD_HHMMSS.zip # これもAIに送る
└── *_CLAUDE.md                         # 個別バックアップ
```

## 次にすること

1. `AI_IMPROVEMENT_REQUEST.md` を開く
2. ZIPファイルをアップロード
3. プロンプトをAIに送信
4. AI改善版を受け取る
5. 各プロジェクトに配置

## トラブルシューティング

### uvがない

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Python 3.10がない

```bash
uv python install 3.10
```

### ~/progディレクトリがない

```bash
# カスタムディレクトリで実行
./run.sh /path/to/your/projects --work-dir /tmp/work
```

### CLAUDE.mdが見つからない

```bash
# サンプルデータで動作確認
./run.sh --create-sample
```

## 詳細

詳しい使い方は `README.md` を参照

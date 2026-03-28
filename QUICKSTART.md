# クイックスタート

## 1分で始める

```bash
# 1. ビルド
docker compose build

# 2. 品質チェック実行（カレントディレクトリ）
docker compose run --rm app python improve_claude_md.py .

# 3. サンプルデータで試す
docker compose run --rm app python improve_claude_md.py --create-sample
```

## 何が起きる?

1. CLAUDE.md / SKILL.md / commands/*.md を検索
2. プロファイル別に品質チェック (スコア 0-100)
3. AI依頼プロンプト + ZIP を生成

## プロファイル指定

```bash
# CLAUDE.md + SKILL.md を対象
docker compose run --rm app python improve_claude_md.py . --profiles claude-md,skill-md

# 全プロファイル
docker compose run --rm app python improve_claude_md.py . --profiles claude-md,skill-md,command-md
```

## 自動パイプライン

claude CLI で自動改善まで実行する場合:

```bash
# 前提: Docker, jaq or jq, claude CLI
./run_improve.sh
```

## トラブルシューティング

### Dockerがない

[Docker Desktop](https://www.docker.com/products/docker-desktop/)
をインストール。

### CLAUDE.md が見つからない

```bash
# サンプルデータで動作確認
docker compose run --rm app python improve_claude_md.py --create-sample
```

## 詳細

詳しい使い方は `README.md` を参照。

# project_b-data

「あたしンチ」のイベント・グッズ情報を自動収集する、個人利用アプリ [Atashinchi Watch](https://github.com/uchidashohei0420-dotcom/project_b) のためのデータフィード用リポジトリです。

`.github/workflows/collect.yml` が1日3回(JST 9/15/21時)、公式サイト・EC(ロフト/アニメイト/Amazon)・X(SNS、[Agent Reach](https://github.com/Panniantong/agent-reach)経由)を巡回し、`data/feed.json` を更新・コミットします。iOSアプリはこの`feed.json`を `raw.githubusercontent.com` 経由で取得するだけの薄いクライアントです。

## このリポジトリが公開である理由

収集対象はもともと公開情報(公式サイトのニュース、ECサイトの商品ページ、公開SNS投稿)であり、それを二次的にまとめたインデックス(タイトル・リンク・簡単なメタ情報)を公開しても、著作物本体(画像・文章)そのものを再配布しているわけではありません。`image_url`は元サイトへの参照リンクのみを保持し、画像そのものはこのリポジトリにコミットしません。

## 対象サイトへの配慮

- すべてのスクレイパーは`robots.txt`を尊重し、連絡先を明示したUser-Agentを送信します(`collector/config.py`の`USER_AGENT`)。
- Amazonはbot検知・利用規約面で最もリスクが高いソースとして扱っており、失敗時は他のソースを巻き込まず静かにスキップします。継続的にブロックされる場合は、Amazon Product Advertising APIへの切り替え、またはこのソースの削除を検討してください。

## セットアップ

1. リポジトリの `Settings → Secrets and variables → Actions` で `AGENT_REACH_X_COOKIE` を登録する(Agent Reach用、専用の捨てXアカウントのCookie値)。
2. `Actions`タブから`Collect feed`ワークフローを`workflow_dispatch`で手動実行し、グリーンになることを確認する。
3. 問題なければ、schedule(1日3回)が自動的に有効になります(追加設定は不要)。

## ローカルでの実行・テスト

```bash
pip install -r collector/requirements.txt pytest
pytest                      # オフラインのfixtureベーステスト
AGENT_REACH_X_COOKIE=xxx python -m collector.main   # 実際に収集してcommit&pushまで行う(要git remote設定)
python scripts/validate_feed.py                      # data/feed.jsonをスキーマ検証するだけ
```

## ディレクトリ構成

- `data/feed.json` — iOSアプリが取得する最新200件(新着順)
- `data/history/YYYY-MM.json` — 収集した全件の恒久アーカイブ(dedupeの正、削除・上書きされない)
- `data/status.json` — 直近runのソース別収集件数・成否(セレクタ崩れ等の検知用)
- `data/schema/feed.schema.json` — JSON Schema
- `collector/` — 収集ロジック本体(Pythonパッケージ)
- `.github/workflows/collect.yml` — 定期実行ワークフロー

詳細な設計は [Atashinchi Watchリポジトリのdocs/PLAN.md](https://github.com/uchidashohei0420-dotcom/project_b/blob/main/docs/PLAN.md) を参照してください。

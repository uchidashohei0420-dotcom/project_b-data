# project_b-data

「あたしンチ」のイベント・グッズ情報を自動収集する、個人利用アプリ [Atashinchi Watch](https://github.com/uchidashohei0420-dotcom/project_b) のためのデータフィード用リポジトリです。

`.github/workflows/collect.yml` が1日3回(JST 9/15/21時)、各情報源を巡回し、`data/feed.json` を更新・コミットします。iOSアプリはこの`feed.json`を `raw.githubusercontent.com` 経由で取得するだけの薄いクライアントです。

### 現在有効な情報源(`collector/main.py`の`ALL_SOURCES`)

- **けらえいこ公式サイト**(`official_keraeiko.py`): 実サイトで動作確認済み(`/category/topics`)。
- **楽天市場 商品検索API**(`ec_rakuten.py`): 「あたしンチ」グッズを扱う楽天市場の出店者を横断検索する公式JSON API。HTMLスクレイピングではないためbot検知・マークアップ変化に強い。`RAKUTEN_APP_ID`(無料・自己発行)が必要。
- **X/SNS**(`sns_x.py`, [Agent Reach](https://github.com/Panniantong/agent-reach)経由): `TWITTER_AUTH_TOKEN`/`TWITTER_CT0`未設定の間はスキップされる(runは失敗しない)。

### 無効化中の情報源(2026-08-21、実サイト検証済み・簡易スクレイピングでは到達不可と判明)

- **`ec_loft.py`**(ロフト): 実際のオンラインストア(`/store/`)がHTTP 503を返す(bot対策と思われる)。
- **`ec_animate.py`**(アニメイト通販): CDNの「overtraffic」ブロックページにリダイレクトされる。

これら2つを再度有効化するには、Playwright等のヘッドレスブラウザによるbot対策の突破が必要です。`collector/main.py`の`ALL_SOURCES`にインポート・追加すれば復活します。`official_30th.py`(あたしンち30周年特設サイト)と`ec_amazon.py`(Amazon)は、前者はニュース欄自体が存在しないため、後者は規約リスクが最も高く楽天APIで代替できたため、それぞれ削除・休止しています。

## このリポジトリが公開である理由

収集対象はもともと公開情報(公式サイトのニュース、ECサイトの商品ページ、公開SNS投稿)であり、それを二次的にまとめたインデックス(タイトル・リンク・簡単なメタ情報)を公開しても、著作物本体(画像・文章)そのものを再配布しているわけではありません。`image_url`は元サイトへの参照リンクのみを保持し、画像そのものはこのリポジトリにコミットしません。

## 対象サイトへの配慮

すべてのスクレイパーは`robots.txt`を尊重し、連絡先を明示したUser-Agentを送信します(`collector/config.py`の`USER_AGENT`)。EC情報源はスクレイピングではなく楽天の公式APIを使うことで、bot検知や利用規約面のリスクを構造的に避けています。

## セットアップ

1. 専用の捨てXアカウントでログインし、Cookie-Editor拡張機能等で`auth_token`と`ct0`の値をエクスポートする。
2. https://webservice.rakuten.co.jp/ で楽天会員登録の上、アプリID(`applicationId`)を発行する(無料・自己発行)。
3. リポジトリの `Settings → Secrets and variables → Actions` で `TWITTER_AUTH_TOKEN`・`TWITTER_CT0`(2つとも必須)・`RAKUTEN_APP_ID` を登録する。未設定のキーがあっても、そのソースだけがスキップされ、run全体は失敗しません。
4. `Actions`タブから`Collect feed`ワークフローを`workflow_dispatch`で手動実行し、グリーンになることを確認する。
5. 問題なければ、schedule(1日3回)が自動的に有効になります(追加設定は不要)。

## ローカルでの実行・テスト

```bash
pip install -r collector/requirements.txt pytest
pytest                      # オフラインのfixtureベーステスト
TWITTER_AUTH_TOKEN=xxx TWITTER_CT0=yyy RAKUTEN_APP_ID=zzz python -m collector.main   # 実際に収集してcommit&pushまで行う(要git remote設定)
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

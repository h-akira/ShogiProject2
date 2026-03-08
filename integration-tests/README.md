# 結合テスト

Playwright for Python を使用した E2E 結合テスト。
`docs/user_stories.md` のユーザーストーリー（US-1.1〜US-8.2）の受け入れ条件を検証する。

## セットアップ

```bash
cd integration-tests

# 仮想環境の作成・有効化
python -m venv env
source env/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt

# Playwright ブラウザのインストール
playwright install chromium

# 環境変数の設定
cp .env.example .env
# .env を編集して認証情報を入力
```

## テスト実行

```bash
# 全テスト実行
python -m pytest tests/ -v

# 特定のユーザーストーリーのみ実行
python -m pytest tests/test_us1_auth.py -v

# ブラウザ表示付き（デバッグ用）
python -m pytest tests/test_us1_auth.py -v --headed

# スクリーンショット（失敗時のみ）
python -m pytest tests/ -v --screenshot=only-on-failure

# スクリーンショット（全テスト）
python -m pytest tests/ -v --screenshot=on

# マークダウンレポート出力
python -m pytest tests/ -v --md=report.md
```

## テストファイル構成

| ファイル | 対象US | 内容 |
|---------|--------|------|
| `test_us1_auth.py` | US-1.1〜1.4 | 認証（ログイン・ログアウト等） |
| `test_us2_dashboard.py` | US-2.1 | ダッシュボード表示 |
| `test_us3_kifu.py` | US-3.1〜3.8 | 棋譜管理（CRUD・エクスプローラー） |
| `test_us4_share.py` | US-4.1〜4.2 | 棋譜共有 |
| `test_us5_tags.py` | US-5.1〜5.5 | タグ管理 |
| `test_us6_analysis.py` | US-6.1 | AI局面解析 |
| `test_us7_user.py` | US-7.1〜7.2 | ユーザー管理 |
| `test_us8_navigation.py` | US-8.1〜8.2 | ナビゲーション |

## 注意事項

- テスト対象は `BASE_URL`（デフォルト: `https://shogi-dev.h-akira.net`）
- US-7.2（アカウント削除）はページ表示の確認のみ（実際の削除は実行しない）
- US-1.1（アカウント作成）はサインアップ画面への遷移確認のみ
- テストで作成した棋譜・タグはテスト内でクリーンアップする

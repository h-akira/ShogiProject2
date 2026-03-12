# BUG-005: アカウント削除失敗時にエラーメッセージが表示されない

## ステータス

修正済み（検証済み）

## 発見日

2026-03-12

## 概要

アカウント削除でパスワード不一致（403）が発生した場合、CloudFront の Custom Error Response が API Gateway の 403 を横取りし、S3 の index.html を 200 で返すため、フロントエンドが正しくエラーハンドリングできない。

## 症状

- パスワードを間違えて削除を実行しても、適切なエラーメッセージが表示されない
- `customFetch` が HTML を JSON としてパースしようとして例外が発生し、`catch` ブロックのフォールバックメッセージが表示される

## 原因

`Infra/stacks/distribution_stack.py` の CloudFront Distribution に SPA 用の Custom Error Response が設定されている：

```python
cloudfront.ErrorResponse(
    http_status=403,
    response_http_status=200,
    response_page_path="/index.html",
)
cloudfront.ErrorResponse(
    http_status=404,
    response_http_status=200,
    response_page_path="/index.html",
)
```

この設定は **CloudFront ディストリビューション全体（全ビヘイビア）に適用される**。
本来は S3 オリジン（フロントエンド）用の SPA フォールバック設定だが、API Gateway ビヘイビア（`/api/v1/main/*`、`/api/v1/analysis/*`）から返される 403/404 レスポンスも横取りしてしまう。

### なぜ SPA フォールバックが必要か

Vue Router（History モード）を使用しているため、`/profile` や `/delete-account` などのパスにブラウザから直接アクセスすると、S3 にはそのパスのファイルが存在しない。OAC 経由の S3 アクセスではファイル未存在時に 403 が返るため、これを index.html にフォールバックさせて Vue Router にクライアント側ルーティングを処理させる必要がある。

### 実際のレスポンスの流れ

1. フロントエンドが DELETE `/api/v1/main/users/me` を送信
2. CloudFront が `/api/v1/main/*` ビヘイビアにマッチし、API Gateway にルーティング
3. Lambda がパスワード不一致で 403 + `{"message": "Invalid password"}` を返す
4. **CloudFront の error_responses が 403 を捕捉し、S3 の index.html を HTTP 200 で返す**
5. `customFetch` は 200 を受け取り、`res.json()` で HTML をパースしようとして例外発生
6. `handleDelete` の `catch` に入る

## 検証結果

`tmp/test-20260312/test_bug005.sh` で検証。

| テスト | HTTP | Content-Type | Body |
|---|---|---|---|
| CloudFront 経由 | 200 | text/html | index.html（S3） |
| API Gateway 直接 | 403 | application/json | `{"message":"Invalid password"}` |

API Gateway 自体は正しく 403 を返しているが、CloudFront が横取りしている。

## 影響範囲

- `Infra/stacks/distribution_stack.py` — CloudFront の error_responses 設定
- API Gateway 経由で 403 または 404 を返す全エンドポイントが影響を受ける
  - 現状 403 を返すのは DELETE `/users/me`（パスワード不一致）のみ
  - 404 を返すエンドポイントも同様に横取りされる可能性がある

## 再現手順

1. ログインしてアカウント削除ページに遷移
2. 誤ったパスワードを入力して「アカウントを削除」を押す
3. 確認ダイアログで「削除する」を押す
4. 適切なエラーメッセージが表示されない

## 修正案

### 案1: error_responses を削除し、S3 側のエラードキュメントで対応

CloudFront の error_responses を削除し、S3 の静的ウェブサイトホスティングのエラードキュメント設定で SPA フォールバックを実現する案。

**不可。** 現在 S3 オリジンは OAC（Origin Access Control）経由でアクセスしており、OAC は S3 の REST API エンドポイントを使用する。S3 の静的ウェブサイトホスティング（エラードキュメント設定を含む）は別のエンドポイントであり、OAC と併用できない。

### 案2: error_responses の対象を S3 オリジンのみに限定

CloudFront の error_responses をビヘイビア単位で設定し、S3 オリジンのビヘイビアにのみ適用する案。

**不可。** CloudFront の Custom Error Response はディストリビューション全体に適用される設定であり、ビヘイビア（パスパターン）単位では設定できない。これは CloudFront の仕様上の制約。

### 案3: error_responses を削除し、viewer-request の CloudFront Functions で SPA フォールバックを実現（推奨）

error_responses の 403/404 設定を削除し、代わりに **viewer-request** イベントの CloudFront Functions で SPA フォールバックを実現する。

仕組み: リクエストが S3 オリジンに到達する前に、URI を書き換える。`/api/` で始まるパスはそのまま通し、それ以外の拡張子なしパス（Vue Router のルート）を `/index.html` にリライトする。

```js
function handler(event) {
  var request = event.request;
  var uri = request.uri;
  // API パスはそのまま通す
  if (uri.startsWith('/api/')) {
    return request;
  }
  // 拡張子があるパス（.js, .css, .ico 等）はそのまま通す
  if (uri.includes('.')) {
    return request;
  }
  // それ以外（Vue Router のルート）は index.html にリライト
  request.uri = '/index.html';
  return request;
}
```

**メリット:**
- error_responses を完全に削除できるため、API の 403/404 がそのまま通る
- S3 に存在しないパスへのリクエストが事前に index.html にリライトされるため、S3 の 403 自体が発生しない
- CloudFront Functions は viewer-request で動作するため、追加のオリジンリクエストが発生しない
- OAC との互換性に問題なし

**デメリット:**
- CloudFront Functions の追加リソースが必要
- `/api/` 以外で拡張子なしの静的ファイルがある場合は個別対応が必要（通常は存在しない）

## 対応

案3を採用。

- `Infra/stacks/distribution_stack.py`:
  - CloudFront Functions（`SpaRewriteFunction`）を追加。viewer-request で `/api/` 以外の拡張子なしパスを `/index.html` にリライト
  - デフォルトビヘイビアに function_associations として紐付け
  - `error_responses`（403→200、404→200）を削除
- `Frontend/shogi-main/src/pages/DeleteAccountPage.vue`:
  - `catch` ブロックのメッセージを通信エラー用に変更（根本修正後は `try` 内で 403 が正しく処理されるため）
  - エラー時はダイアログを閉じず、ダイアログ内にエラーメッセージを表示（前回の暫定対応を維持）

## 暫定対応

根本修正（Infra）が完了するまでの暫定対応として、フロントエンド側で以下を実施済み：

- `Frontend/shogi-main/src/pages/DeleteAccountPage.vue`:
  - `handleDelete` に `catch` ブロックを追加（CloudFront が 200 + HTML を返すため `res.json()` が例外をスローするケースに対応）
  - エラー時はダイアログを閉じず、ダイアログ内にエラーメッセージを表示
  - `catch` のメッセージ: 「アカウント削除に失敗しました。パスワードを確認してください。」

## 関連

- BUG-004: アカウント削除時のパスワード不一致で強制ログアウトされる（バックエンド側の 401→403 変更で対応済み）
- `Infra/stacks/distribution_stack.py` — CloudFront Distribution 定義
- `docs/units_contracts.md` — CloudFront ビヘイビア設定

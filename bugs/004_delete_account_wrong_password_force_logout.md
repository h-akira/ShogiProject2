# BUG-004: アカウント削除時のパスワード不一致で強制ログアウトされる

## ステータス

修正済み（検証待ち）

## 発見日

2026-03-11

## 概要

アカウント削除時に誤ったパスワードを入力すると、エラーメッセージが表示されず強制ログアウトされる。

## 症状

- アカウント削除画面で誤ったパスワードを入力して削除を実行しても、エラーが表示されない
- ユーザーが強制ログアウトされ、トップページに遷移する
- アカウント自体は削除されていない（パスワード検証で弾かれているため）

## 原因

バックエンドがパスワード不一致時に 401 を返すが、フロントエンドの `customFetch` が 401 を一律「認証切れ」と判断し、リフレッシュ→リトライ→再度 401→`forceLogout()` を実行する。`handleDelete` のステータスチェックに到達する前に強制ログアウトが走る。

根本原因は、HTTP 401 が「認証トークン切れ」と「パスワード不一致」の2つの意味で使われていること。

## 影響範囲

- `Backend/main/src/common/exceptions.py` — `AuthenticationError` が 401 を返す
- `Backend/main/src/services/user_service.py` — `delete_account` でパスワード不一致時に `AuthenticationError` を送出
- `Frontend/shogi-main/src/api/custom-fetch.ts` — 401 の一律ハンドリング
- `Frontend/shogi-main/src/pages/DeleteAccountPage.vue` — レスポンスのステータスチェック
- `docs/openapi_main.yaml` — DELETE `/users/me` のエラーレスポンス定義

## 再現手順

1. ログインしてプロフィールページに遷移
2. 「アカウント削除」ボタンを押す
3. 誤ったパスワードを入力して「アカウントを削除」を押す
4. 確認ダイアログで「削除する」を押す
5. エラーが表示されず、ログアウトされてトップページに遷移する

## 修正案

### 案1: パスワード不一致のレスポンスコードを 403 に変更（推奨）

401 は「認証されていない（トークン切れ）」、403 は「認証済みだが操作が拒否された」という HTTP セマンティクスに合わせる。

- `Backend/main/src/common/exceptions.py`: `AuthenticationError.status_code` を 401 → 403 に変更
- `docs/openapi_main.yaml`: DELETE `/users/me` のエラーレスポンスを 401（認証エラー）と 403（パスワード不一致）に分離
- `Frontend`: OpenAPI 変更後に orval で再生成。`DeleteAccountPage.vue` は `!== 204` で判定済みのため変更不要

`AuthenticationError` は `delete_account` でのみ使用されており、影響範囲は限定的。

## 対応

案1を採用。パスワード不一致のレスポンスコードを 401 → 403 に変更した。

- `docs/openapi_main.yaml`: DELETE `/users/me` に 403 レスポンスを追加、401 を認証エラー専用に限定
- `docs/changes/008_delete_account_password_error_403.md`: 変更通知を作成
- `Backend/main/src/common/exceptions.py`: `AuthenticationError.status_code` を 403 に変更
- `Frontend/shogi-main/src/api/generated/`: orval で再生成
- `Frontend/shogi-main/src/pages/DeleteAccountPage.vue`: ステータスチェック（`!== 204`）とエラーメッセージ表示を追加（先行対応済み）

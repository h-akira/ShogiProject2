# 変更通知 008: アカウント削除のパスワード不一致レスポンスを 401 → 403 に変更

## 変更概要

DELETE `/users/me` でパスワード不一致時に返すステータスコードを 401 から 403 に変更。401 は API Gateway / Cognito Authorizer による認証エラー（トークン無効・期限切れ）専用とし、アプリケーションレベルのパスワード検証失敗は 403 で返す。

## 背景

フロントエンドの `customFetch` が 401 を一律「認証切れ」と判断して強制ログアウトするため、パスワード不一致でもユーザーがログアウトされてしまう問題（BUG-004）の修正。

## 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `docs/openapi_main.yaml` | DELETE `/users/me` のレスポンスに 403 を追加、401 の説明を「認証エラー」に限定 |

## 影響を受けるユニット

| ユニット | 影響 | 必要な対応 |
|---------|------|-----------|
| Backend (main) | `AuthenticationError` のステータスコードを 403 に変更 | `common/exceptions.py` を修正 |
| Frontend | orval で API クライアントを再生成 | `npm run generate:api` を実行 |
| Infra | 影響なし | 不要 |
| CI/CD | 影響なし | 不要 |

## 関連

- `bugs/004_delete_account_wrong_password_force_logout.md`

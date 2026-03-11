# 変更通知 007: パスワード変更を Cognito SDK 直接呼び出しに変更

## 変更概要

パスワード変更の実装方式を Cognito Managed Login リダイレクトから、フロントエンドで Cognito SDK（`ChangePassword` API）を直接呼び出す方式に変更した。

## 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `docs/technical_policies.md` | パスワード変更の方針を「Managed Login」から「SDK 直接呼び出し」に更新 |
| `Infra/stacks/cognito_stack.py` | App Client の OAuth スコープに `COGNITO_ADMIN` を追加 |
| `Frontend/shogi-main/src/auth/auth.ts` | 認可リクエストのスコープに `aws.cognito.signin.user.admin` を追加 |
| `Frontend/shogi-main/env.d.ts` | `VITE_COGNITO_REGION` の型定義を追加 |
| `Frontend/shogi-main/src/pages/ChangePasswordPage.vue` | 新規作成 |
| `Frontend/shogi-main/src/pages/ProfilePage.vue` | パスワード変更ボタンの遷移先を変更 |
| `Frontend/shogi-main/src/router/index.ts` | `/change-password` ルートを追加 |
| `Frontend/buildspec.yml` | `VITE_COGNITO_REGION` 環境変数を追加（`CDK_DEFAULT_REGION` を使用） |

## 影響を受けるユニット

| ユニット | 影響 | 対応 |
|---------|------|------|
| Infra | OAuth スコープ変更 | 実装済み。再デプロイが必要 |
| Frontend | パスワード変更ページ追加、スコープ変更 | 実装済み |
| CI/CD | `buildspec.yml` は Frontend リポジトリ内のため追加対応不要 | 不要 |
| Backend | 影響なし | 不要 |

## デプロイ順序

Infra（Cognito スコープ変更）を先にデプロイしてから Frontend をデプロイすること。

## 追加された環境変数

| 環境変数 | 値の出所 | 用途 |
|---------|---------|------|
| `VITE_COGNITO_REGION` | `CDK_DEFAULT_REGION`（`ap-northeast-1`） | Cognito SDK クライアントのリージョン指定 |

# 003: VITE_COGNITO_DOMAIN 環境変数の追加

## 変更概要

`docs/units_contracts.md` の「フロントエンドビルド時の環境変数」テーブルに `VITE_COGNITO_DOMAIN` を追加。

Cognito Managed Login の `/oauth2/authorize`、`/oauth2/token`、`/logout` エンドポイントへのリダイレクトに Cognito ドメイン名が必要なため。

## 対象ファイル

- `docs/units_contracts.md`

## 影響を受けるユニット

- CI/CD: `Frontend/buildspec.yml` で既に `VITE_COGNITO_DOMAIN` を export 済み。対応不要。
- インフラ: `CognitoDomain` は既にエクスポート済み。対応不要。
- フロントエンド: `auth.ts` で `import.meta.env.VITE_COGNITO_DOMAIN` を使用する実装に変更済み。

## 各ユニットで必要な対応

なし（既に全ユニットで対応済み。ドキュメントの追従のみ）。

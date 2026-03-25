# 004: DomainName エクスポート追加・CloudFrontDomainName 削除・redirect_uri 修正

## 変更概要

- `CloudFrontDomainName` エクスポートを削除し、代わりに `DomainName`（カスタムドメイン名）エクスポートを追加
- フロントエンドの `VITE_REDIRECT_URI` がCloudFrontの生ドメインを使用していたため、Cognitoの `redirect_mismatch` エラーが発生していた問題を修正
- Cognito カスタムドメイン用の Route 53 Alias レコードを追加

## 対象ファイル

- `docs/units_contracts.md` — エクスポート一覧・`VITE_REDIRECT_URI` の出所を修正
- `Infra/stacks/distribution_stack.py` — `CloudFrontDomainName` 削除、`DomainName` 追加
- `Infra/stacks/cognito_stack.py` — Route 53 Alias レコード追加
- `Infra/init/cfn-execution-policies.yaml` — `DescribeUserPoolDomain` の Resource を `*` に分離
- `Frontend/buildspec.yml` — `CF_DOMAIN` を `DOMAIN_NAME` に置換

## 影響を受けるユニット

| ユニット | 必要な対応 |
|---------|-----------|
| Frontend | `buildspec.yml` で `CloudFrontDomainName` の代わりに `DomainName` エクスポートを参照するよう変更済み。Infra デプロイ後にフロントエンドの再ビルドが必要 |
| CI/CD | 変更不要（エクスポート名の変更はフロントエンド buildspec 側で吸収） |
| Backend | 変更不要 |

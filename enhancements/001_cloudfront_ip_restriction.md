# ENH-001: CloudFront IP制限（CloudFront Functions）

## ステータス

完了（検証済み）

## 起票日

2026-03-12

## 種別

仕様追加

## 概要

CloudFront Functions を使い、検証環境では特定IPのみアクセス可能にする。本番環境ではIP制限なし。

## 背景・動機

検証環境が現在インターネット上に公開されており、関係者以外のアクセスを防ぎたい。WAFはコストが高い（月額$5〜 + リクエスト課金）ため、CloudFront Functions（無料枠 200万リクエスト/月、以降 $0.10/100万リクエスト）で実現する。

## 要件

- 検証環境（dev）: 指定IPリスト以外からのアクセスを 403 で拒否する
- 本番環境（pro）: IP制限なし（全アクセス許可）
- 許可IPリストはCICD（CodeBuild環境変数）経由で指定する
- 許可IPリストが空または未指定の場合はIP制限を適用しない（本番と同じ動作）

## 影響範囲

- `Infra/stacks/distribution_stack.py` — CloudFront Function のコード修正
- `Infra/app.py` — 環境変数の受け渡し追加
- `Infra/buildspec.yml` — 環境変数の受け渡し追加
- `CICD/infra.yaml` — CodeBuild 環境変数・パラメータ追加
- `CICD/deploy_dev.sh` — パラメータ追加
- `CICD/deploy_prod.sh` — パラメータ追加（空文字）

## 実現案

### 案1: 既存SPAリライト Function にIP制限ロジックを統合（推奨）

既存の `SpaRewriteFunction` の先頭にIP判定を追加する。CloudFront Functions は Viewer Request で1つしかアタッチできないため、別 Function にはできない。

#### データフロー

```
CICD/infra.yaml (Parameter: AllowedIps)
  → CodeBuild 環境変数 ALLOWED_IPS
    → Infra/buildspec.yml で CDK context に渡す (-c allowed_ips=...)
      → Infra/app.py で try_get_context("allowed_ips") を取得
        → DistributionStack の引数 allowed_ips
          → CloudFront Function コードに許可IPリストを埋め込み
```

#### CloudFront Function コード（イメージ）

```javascript
function handler(event) {
  var request = event.request;
  var clientIp = event.viewer.ip;
  var allowedIps = ['1.2.3.4', '5.6.7.8']; // CDKで動的に埋め込み

  if (allowedIps.length > 0) {
    var allowed = false;
    for (var i = 0; i < allowedIps.length; i++) {
      if (allowedIps[i] === clientIp) {
        allowed = true;
        break;
      }
    }
    if (!allowed) {
      return {
        statusCode: 403,
        statusDescription: 'Forbidden',
        body: { encoding: 'text', data: 'Access Denied' }
      };
    }
  }

  // SPA rewrite
  var uri = request.uri;
  if (!uri.startsWith('/api/') && !uri.includes('.')) {
    request.uri = '/index.html';
  }
  return request;
}
```

#### 変更詳細

1. `CICD/infra.yaml`: `AllowedIps` パラメータ追加（デフォルト空文字）、CodeBuild 環境変数に追加
2. `CICD/deploy_dev.sh`: `AllowedIps` に許可IPをカンマ区切りで指定
3. `CICD/deploy_prod.sh`: `AllowedIps` は空文字（指定しない）
4. `Infra/buildspec.yml`: `ALLOWED_IPS` を CDK context に渡す（`-c allowed_ips=${ALLOWED_IPS}`）
5. `Infra/app.py`: `allowed_ips` を context から取得し `DistributionStack` に渡す
6. `Infra/stacks/distribution_stack.py`: `allowed_ips` 引数を追加、CloudFront Function コードにIP制限ロジックを埋め込み

## 関連

- [CloudFront Functions event structure](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/functions-event-structure.html) — `event.viewer.ip` でクライアントIPを取得可能

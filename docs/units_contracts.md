# ユニット間の契約

## 概要

本ドキュメントは、[units_definition.md](units_definition.md) で定義した各ユニット間のインターフェース（契約）を定義する。

---

## 管理規約

AWS リソースの命名やリポジトリ管理に使用する変数を以下の通り定義する。

| 変数 | 意味 | 値 |
|------|------|-----|
| `${project}` | プロジェクト識別子（固定） | `sgp` |
| `${env}` | 環境識別子（可変） | `dev`, `pro` |
| `${service}` | サービス識別名 | 下表参照 |

### ユニット別定義

| ユニット | `${service}` | GitHub リポジトリ | サブモジュールパス |
|---------|-------------|-----------------|-----------------|
| フロントエンド | `frontend` | `h-akira/ShogiProject2_Frontend` | `Frontend/` |
| メイン API | `backend-main` | `h-akira/ShogiProject2_Backend_main` | `Backend/main/` |
| 解析 API | `backend-analysis` | `h-akira/ShogiProject2_Backend_analysis` | `Backend/analysis/` |
| インフラ | `infra` | `h-akira/ShogiProject2_Infra` | `Infra/` |
| CI/CD | `cicd` | `h-akira/ShogiProject2_CICD` | `CICD/` |

各リポジトリは本プロジェクトの Git サブモジュールとして管理する。

### 命名パターン

| 対象 | パターン | 例 |
|------|---------|-----|
| スタック名 | `stack-${project}-${env}-<識別名>` | `stack-sgp-dev-backend-main` |
| AWS リソース名 | `<リソースタイプ>-${project}-${env}-<識別名>` | `role-sgp-dev-backend-main-LambdaExec` |
| エクスポート名 | `${project}-${env}-<識別名>` | `sgp-dev-backend-main-ApiGatewayId` |
| パラメータストア | `/${project}/${env}/<識別名>` | `/sgp/dev/backend-main/TableName` |

---

## 連携方式

ユニット間の値の受け渡しには以下の方法を使用できる。

| 方法 | 用途 |
|------|------|
| CloudFormation エクスポート | スタック間の直接参照（`Fn::ImportValue`）。本プロジェクトでは CDK ↔ SAM 間を含め、原則としてこの方式を採用する |
| パラメータストア (SSM) | エクスポートでは対応できない場合の代替手段 |

---

## 依存関係とエクスポート一覧

### 依存関係図

```mermaid
graph LR
  infra -->|Cognito 情報| backend-main
  infra -->|Cognito 情報| backend-analysis
  infra -->|Cognito 情報, CloudFront 情報等| cicd
  backend-main -->|API Gateway ID| infra
  backend-analysis -->|API Gateway ID| infra
```

infra ↔ backend-main / backend-analysis 間に循環依存が存在する。実装時にはインフラユニット内でスタックを分割するなどして循環を解消すること。

### インフラ → バックエンド（Cognito 情報）

インフラユニットが Cognito の情報を公開し、各バックエンドユニットが参照する。

| キー | 値 | 用途 | 参照先 |
|------|-----|------|-------|
| `${project}-${env}-infra-CognitoUserPoolArn` | User Pool ARN | API Gateway の Cognito Authorizer | backend-main, backend-analysis |
| `${project}-${env}-infra-CognitoUserPoolId` | User Pool ID | Lambda での認証検証（必要な場合） | backend-main, backend-analysis |
| `${project}-${env}-infra-CognitoClientId` | App Client ID | Lambda での認証検証（必要な場合） | backend-main, backend-analysis, CI/CD |

### バックエンド → インフラ（API Gateway ID）

各バックエンドユニットが API Gateway の情報を公開し、インフラユニットが CloudFront のオリジンとして登録する。

| キー | 値 | 用途 | 参照先 |
|------|-----|------|-------|
| `${project}-${env}-backend-main-ApiGatewayId` | REST API ID | CloudFront のオリジン設定 | infra |
| `${project}-${env}-backend-main-ApiGatewayStageName` | ステージ名 | CloudFront のオリジンパス | infra |
| `${project}-${env}-backend-analysis-ApiGatewayId` | REST API ID | CloudFront のオリジン設定 | infra |
| `${project}-${env}-backend-analysis-ApiGatewayStageName` | ステージ名 | CloudFront のオリジンパス | infra |

CloudFront でのパスパターン割り当ては以下の通り。

| サービス | パスパターン |
|---------|------------|
| `backend-main` | `/api/v1/main/*` |
| `backend-analysis` | `/api/v1/analysis/*` |

### インフラ → CI/CD（デプロイ先情報）

CI/CD パイプラインがデプロイやビルド時の環境変数注入に使用する。

| キー | 値 | 用途 | 参照先 |
|------|-----|------|-------|
| `${project}-${env}-infra-S3BucketName` | バケット名 | フロントエンドのデプロイ先 | CI/CD |
| `${project}-${env}-infra-CloudFrontDistributionId` | Distribution ID | キャッシュ無効化の対象 | CI/CD |
| `${project}-${env}-infra-CloudFrontDomainName` | ドメイン名 | フロントエンドビルド時の環境変数注入 | CI/CD |
| `${project}-${env}-infra-CognitoClientId` | App Client ID | フロントエンドビルド時の環境変数注入 | CI/CD |
| `${project}-${env}-infra-CognitoDomain` | Cognito ドメイン | フロントエンドビルド時の環境変数注入 | CI/CD |

---

## フロントエンド ↔ バックエンド通信仕様

| 項目 | 仕様 |
|------|------|
| 認証方式 | `Authorization: Bearer {Access Token}` ヘッダー |
| データ形式 | JSON (`Content-Type: application/json`) |
| エラー形式 | `{ "message": "エラーメッセージ" }` |
| CORS | CloudFront 経由の同一オリジンのためブラウザ上は不要。API Gateway 側の CORS は直接アクセス対策として設定 |

各バックエンドの API エンドポイント一覧は [_api_list.md](_api_list.md) を参照。

> `_api_list.md` は暫定版であり、OpenAPI 定義で置き換える予定。

---

## フロントエンドビルド時の環境変数

CI/CD パイプラインがエクスポート値を取得し、フロントエンドのビルド時に以下の環境変数として注入する。

| 環境変数 | 値の出所 | 用途 |
|---------|---------|------|
| `VITE_COGNITO_AUTHORITY` | `infra`（Cognito） | OIDC Issuer URL |
| `VITE_COGNITO_CLIENT_ID` | `infra`（Cognito） | App Client ID |
| `VITE_REDIRECT_URI` | `infra`（CloudFront） | OIDC コールバック URL |
| `VITE_API_BASE_URL` | - | API ベースパス（`/api/v1`） |

---

## バックエンド間連携の方針（将来）

現時点ではメイン API と解析 API の間にバックエンド間連携はない。将来的に連携が必要になった場合に備え、以下の方針を定める。

### 連携方式

| 方式 | 用途 | 手段 |
|------|------|------|
| 同期連携 | あるバックエンドが別のバックエンドの API を呼び出す | Lambda から API Gateway のエンドポイントを HTTP で呼び出す |
| 非同期連携 | イベント駆動で別のバックエンドに処理を委譲する | SNS/SQS を介したメッセージング |

### 認証情報の扱い

バックエンド間連携時の認証は以下のいずれかの方式を採用する。

#### 方式 A: ユーザーのトークンを中継する

```mermaid
sequenceDiagram
  participant FE as フロントエンド
  participant A as バックエンド A
  participant B as バックエンド B

  FE->>A: リクエスト（Bearer Token）
  A->>B: リクエスト（同じ Bearer Token を中継）
  B->>A: レスポンス
  A->>FE: レスポンス
```

- フロントエンドから受け取った Access Token をそのまま中継先バックエンドに渡す
- 呼び出し先の API Gateway の Cognito Authorizer がトークンを検証する
- ユーザーコンテキストが保持されるため、呼び出し先でも `cognito:username` を取得可能
- 追加の認証設定が不要

#### 方式 B: IAM 認証を使用する

- Lambda の実行ロールに呼び出し先 API Gateway の `execute-api:Invoke` 権限を付与する
- IAM 認証（SigV4 署名）で API Gateway を呼び出す
- ユーザーコンテキストはリクエストボディやヘッダーで明示的に渡す必要がある
- サービス間通信であることが明確になる

### 採用方針

- **同期連携**: ユーザー操作の文脈で別サービスのデータが必要な場合は**方式 A（トークン中継）**を優先する。シンプルで追加の認証設定が不要なためである
- **非同期連携**: SNS/SQS を介する場合はトークンを中継できないため、**方式 B（IAM 認証）**または認証不要な内部エンドポイントを使用する

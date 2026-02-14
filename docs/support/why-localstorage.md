# なぜlocalStorageを使うのか（Cookie vs localStorage）

旧システムではCookieでセッション管理していたが、新システムではlocalStorageを採用する。
その理由を解説する。

---

## 1. 旧システム（SSR + Cookie）の仕組み

旧システムでは、ブラウザとLambdaが**同じオリジン**で動作していた。

```mermaid
sequenceDiagram
  participant Browser as ブラウザ
  participant Lambda as Lambda（SSR）
  participant Cognito as Cognito

  Browser->>Lambda: POST /accounts/login（ID/PW送信）
  Lambda->>Cognito: 認証
  Cognito-->>Lambda: トークン
  Lambda-->>Browser: Set-Cookie: session=xxx

  Note over Browser: 以降、Cookieは自動送信される

  Browser->>Lambda: GET /kifu/index/hakira<br/>Cookie: session=xxx（自動付与）
  Lambda-->>Browser: HTML
```

**Cookieの利点**: ブラウザが自動で毎回送信してくれるので、開発者がトークン管理を意識する必要がない。

---

## 2. 新システムでの3つの選択肢

SPAからAPIを呼ぶとき、トークンの保管場所とAPI Gatewayでの検証方法の組み合わせで3つの方式がある。

```mermaid
graph TD
  Q{"トークンの保管と検証方式"}
  Q --> A["方式A<br/>localStorage<br/>+ Cognito Authorizer"]
  Q --> B["方式B<br/>Cookie<br/>+ Cognito Authorizer<br/>（付け替え層経由）"]
  Q --> C["方式C<br/>Cookie<br/>+ Lambda Authorizer"]

  style A fill:#4CAF50,color:#fff
  style B fill:#2196F3,color:#fff
  style C fill:#FF9800,color:#fff
```

---

### 方式A: localStorage + Cognito Authorizer

```mermaid
sequenceDiagram
  participant Vue as Vue 3 SPA
  participant Amplify as Amplify SDK
  participant APIGW as API Gateway
  participant Auth as Cognito Authorizer<br/>（API Gateway組み込み）
  participant Lambda as Lambda

  Vue->>Amplify: fetchAuthSession()
  Amplify-->>Vue: ID Token（localStorageから取得）

  Vue->>APIGW: GET /api/v1/kifus<br/>Authorization: Bearer {ID Token}
  APIGW->>Auth: トークン検証を委譲
  Auth->>Auth: 署名検証・有効期限チェック
  Auth-->>APIGW: 検証OK（claims付与）
  APIGW->>Lambda: リクエスト転送
  Lambda-->>Vue: レスポンス
```

- **Cognito Authorizer** はAPI Gatewayに組み込まれた認証機能
- `Authorization` ヘッダーのJWTを自動で検証する
- **設定だけで動く**（コードを書く必要がない）

---

### 方式B: Cookie + 付け替え層 + Cognito Authorizer

```mermaid
sequenceDiagram
  participant Vue as Vue 3 SPA
  participant CF as CloudFront Functions<br/>（付け替え層）
  participant APIGW as API Gateway
  participant Auth as Cognito Authorizer<br/>（API Gateway組み込み）
  participant Lambda as Lambda

  Vue->>CF: GET /api/v1/kifus<br/>Cookie: token=xxx（ブラウザが自動送信）
  CF->>CF: Cookieからトークンを取り出し<br/>Authorizationヘッダーに付け替え
  CF->>APIGW: GET /api/v1/kifus<br/>Authorization: Bearer {token}
  APIGW->>Auth: トークン検証を委譲
  Auth->>Auth: 署名検証・有効期限チェック
  Auth-->>APIGW: 検証OK（claims付与）
  APIGW->>Lambda: リクエスト転送
  Lambda-->>Vue: レスポンス
```

- CookieのHttpOnly属性でXSSに強い保管ができる
- **Cognito Authorizerをそのまま使える**（検証コード不要）
- ただし、CookieからAuthorizationヘッダーへの**付け替え層**（CloudFront FunctionsやAPI Gateway変換テンプレート等）が必要

---

### 方式C: Cookie + Lambda Authorizer

```mermaid
sequenceDiagram
  participant Vue as Vue 3 SPA
  participant APIGW as API Gateway
  participant LAuth as Lambda Authorizer<br/>（自前実装）
  participant Lambda as Lambda

  Vue->>APIGW: GET /api/v1/kifus<br/>Cookie: token=xxx（ブラウザが自動送信）
  APIGW->>LAuth: Cookieヘッダーを渡す
  LAuth->>LAuth: Cookieからトークンを取り出し
  LAuth->>LAuth: JWT署名検証・有効期限チェック
  LAuth-->>APIGW: 検証OK（IAMポリシー返却）
  APIGW->>Lambda: リクエスト転送
  Lambda-->>Vue: レスポンス
```

- **Lambda Authorizer** はAPI Gatewayのリクエストを検証するためのLambda関数
- Cookieからのトークン取り出しとJWT検証を一箇所でまとめて行う
- **実際の本番システムでも広く使われているパターン**で、珍しい構成ではない

---

## 3. 比較

いずれも実用的な方式であり、要件に応じた選択になる。

| 観点 | 方式A: localStorage | 方式B: Cookie+付け替え | 方式C: Cookie+Lambda Auth |
|------|--------------------|-----------------------|--------------------------|
| トークン保管 | localStorage | Cookie（HttpOnly） | Cookie（HttpOnly） |
| XSSリスク | JSから読める | HttpOnlyなら読めない | HttpOnlyなら読めない |
| CSRF対策 | 不要 | 必要 | 必要 |
| API Gateway検証 | Cognito Authorizer | Cognito Authorizer | Lambda Authorizer |
| 追加実装 | なし | 付け替え層 | Authorizer Lambda |
| Amplify SDK | デフォルト動作 | カスタム設定が必要 | カスタム設定が必要 |
| 運用コスト | 最小 | CF Functionsの管理 | Authorizer Lambdaの管理 |

**どの方式が優れているという話ではなく、トレードオフの関係にある。**

---

## 4. 本アプリでは方式A（localStorage）を選ぶ理由

本アプリでは**シンプルさを優先して方式Aを採用する**。

### 理由1: 認証まわりの実装量を最小にしたい

方式B・Cでは追加のコンポーネントが必要になる：

| 方式 | 追加で実装・管理するもの |
|------|----------------------|
| 方式B | CloudFront Functions等の付け替え層、CSRF対策、Cookieの設定管理 |
| 方式C | Lambda Authorizer（JWT検証ロジック、JWKS公開鍵取得・キャッシュ）、CSRF対策 |
| **方式A** | **なし（SAMテンプレートの設定のみ）** |

### 理由2: Amplify SDKのデフォルトに乗れる

Amplify SDKはデフォルトでlocalStorageにトークンを保存し、
`fetchAuthSession()` で取り出してAuthorizationヘッダーに付与するフローを想定している。
この標準的な流れをそのまま使える。

### 理由3: XSSリスクは実用上許容できる

localStorageの弱点はXSS攻撃時のトークン漏洩だが、以下の理由で許容範囲と判断する：

1. **トークンは短命（1時間）** — 盗まれても1時間で無効になる
2. **Refresh Tokenの無効化が可能** — CognitoのRevoke機能で即座に取り消せる
3. **アプリの性質** — 棋譜管理アプリであり、金融・医療のような高セキュリティ要件ではない
4. **XSS自体を防ぐ** — Vueの自動エスケープ、CSPヘッダー等で根本対策を行う

---

## 5. まとめ

```mermaid
graph LR
  A["本アプリの方針"] --> B["方式A<br/>localStorage + Cognito Authorizer"]
  B --> B1["認証コード不要"]
  B --> B2["Amplifyデフォルト"]
  B --> B3["構成がシンプル"]

  style A fill:#E3F2FD
  style B fill:#4CAF50,color:#fff
```

| 判断ポイント | 結論 |
|-------------|------|
| 方式B・Cはダメなのか？ | いいえ。いずれも本番で広く使われている実績ある方式 |
| なぜ方式Aを選ぶのか？ | 認証の実装量を最小にし、Amplifyのデフォルトに乗れるシンプルさを優先 |
| XSSリスクは大丈夫か？ | トークン短命 + Vue自動エスケープ + CSPで実用上十分 |

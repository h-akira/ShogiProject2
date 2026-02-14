# Cognito + JWT 認証ガイド

本アプリ（Vue 3 SPA + Lambda + API Gateway）で採用する認証方式の解説。

---

## 1. なぜこの認証方式なのか

旧システム（SSR）ではサーバー側でログイン処理からセッション管理まですべて行っていた。
SPA（Single Page Application）では**フロントエンドとバックエンドが完全に分離**されるため、認証の仕組みが変わる。

```mermaid
graph LR
  subgraph 旧システム（SSR）
    A[ブラウザ] -->|ログインフォーム送信| B[Lambda]
    B -->|Cognito認証| C[Cognito]
    B -->|セッションCookie発行| A
    A -->|Cookie付きリクエスト| B
  end
```

```mermaid
graph LR
  subgraph 新システム（SPA）
    A[Vue 3 SPA] -->|直接認証| C[Cognito]
    C -->|トークン発行| A
    A -->|トークン付きAPIリクエスト| B[API Gateway + Lambda]
    B -->|トークン検証| B
  end
```

**ポイント**: 新システムではログイン処理にLambdaを経由しない。フロントエンドが直接Cognitoと通信する。

---

## 2. Cognitoが発行する3つのトークン

ログインが成功すると、Cognitoは**3種類のトークン**を発行する。

```mermaid
graph TD
  Login[ログイン成功] --> ID[ID Token]
  Login --> Access[Access Token]
  Login --> Refresh[Refresh Token]

  ID -->|用途| ID_USE["「この人は誰か」を証明<br/>ユーザー名・メール等を含む"]
  Access -->|用途| ACC_USE["「何にアクセスできるか」を制御<br/>OAuth 2.0 スコープを含む"]
  Refresh -->|用途| REF_USE["期限切れトークンの再発行<br/>再ログインを不要にする"]

  style ID fill:#4CAF50,color:#fff
  style Access fill:#2196F3,color:#fff
  style Refresh fill:#FF9800,color:#fff
```

### 各トークンの比較

| | ID Token | Access Token | Refresh Token |
|---|---|---|---|
| **中身** | ユーザー情報（名前、メール等） | アクセス権限（スコープ） | 暗号化済み（中身は見えない） |
| **有効期限** | 1時間（デフォルト） | 1時間（デフォルト） | 30日（デフォルト） |
| **本アプリでの用途** | API呼出時にヘッダーに付与 | 使用しない | トークン自動更新 |
| **形式** | JWT（デコード可能） | JWT（デコード可能） | 暗号化文字列 |

### 本アプリでは「ID Token」を使う

API Gatewayでスコープ制御（「このユーザーは読み取りのみ」など）を行わない場合、**ID Token**を使うのが標準。
API GatewayはID Tokenからユーザー名やメールアドレスを取り出して、Lambdaに渡してくれる。

---

## 3. 認証の全体フロー

### 3.1 サインアップ（ユーザー登録）

```mermaid
sequenceDiagram
  actor User as ユーザー
  participant Vue as Vue 3 SPA
  participant Cognito as Cognito

  User->>Vue: メールアドレスとパスワードを入力
  Vue->>Cognito: signUp(email, password)
  Cognito-->>Vue: 「確認コードを送信しました」
  Cognito->>User: 確認コードをメール送信 ✉️

  User->>Vue: 確認コードを入力
  Vue->>Cognito: confirmSignUp(email, code)
  Cognito-->>Vue: 「登録完了」
  Vue-->>User: ログイン画面へ遷移
```

### 3.2 ログイン

```mermaid
sequenceDiagram
  actor User as ユーザー
  participant Vue as Vue 3 SPA
  participant Cognito as Cognito

  User->>Vue: メールアドレスとパスワードを入力
  Vue->>Cognito: signIn(email, password)
  Cognito->>Cognito: パスワード検証（SRPプロトコル）
  Cognito-->>Vue: ID Token + Access Token + Refresh Token

  Vue->>Vue: トークンをブラウザに保存
  Vue-->>User: ホーム画面へ遷移
```

### 3.3 API呼出（認証済みリクエスト）

```mermaid
sequenceDiagram
  participant Vue as Vue 3 SPA
  participant APIGW as API Gateway
  participant Lambda as Lambda

  Vue->>Vue: 保存済みのID Tokenを取得

  Vue->>APIGW: GET /api/v1/kifus<br/>Authorization: Bearer {ID Token}

  APIGW->>APIGW: ID Tokenの署名を検証<br/>（Cognitoの公開鍵を使用）
  APIGW->>APIGW: 有効期限を確認
  APIGW->>APIGW: 発行者（Cognito）を確認

  alt 検証成功
    APIGW->>Lambda: リクエスト転送<br/>（ユーザー情報を付加）
    Lambda->>Lambda: claims["cognito:username"]<br/>でユーザーを特定
    Lambda-->>APIGW: レスポンス（JSON）
    APIGW-->>Vue: レスポンス
  else 検証失敗（期限切れ・改ざん等）
    APIGW-->>Vue: 401 Unauthorized
  end
```

**重要**: API Gatewayは**毎回Cognitoに問い合わせるわけではない**。Cognitoが公開している公開鍵（JWKS）を使って、API Gateway内部でトークンの正当性を検証する。これにより高速に動作する。

### 3.4 トークンの自動更新（リフレッシュ）

ID Tokenは1時間で有効期限が切れる。ユーザーに毎回再ログインさせないために、Refresh Tokenで自動更新する。

```mermaid
sequenceDiagram
  participant Vue as Vue 3 SPA
  participant Amplify as Amplify SDK<br/>（フロント内部）
  participant Cognito as Cognito
  participant APIGW as API Gateway

  Vue->>Amplify: fetchAuthSession()
  Amplify->>Amplify: ID Tokenの有効期限をチェック

  alt トークンが有効
    Amplify-->>Vue: キャッシュ済みのID Tokenを返却
  else トークンが期限切れ
    Amplify->>Cognito: Refresh Tokenを送信
    Cognito->>Cognito: Refresh Token検証
    Cognito-->>Amplify: 新しいID Token + Access Token
    Amplify-->>Vue: 新しいID Tokenを返却
  end

  Vue->>APIGW: 新しいID TokenでAPIリクエスト
```

**Amplify SDKがこの処理を自動で行う**。開発者が意識する必要はほぼない。

---

## 4. トークンの保管場所

トークンをブラウザのどこに保存するかはセキュリティ上の重要な判断。

```mermaid
graph TD
  subgraph 保管方法の選択肢
    A["localStorage<br/>（Amplifyデフォルト）"] -->|特徴| A1["✅ リロードしても残る<br/>✅ タブ間で共有<br/>❌ XSS攻撃で盗まれるリスク"]
    B["メモリ（変数）"] -->|特徴| B1["✅ XSSに強い<br/>❌ リロードで消える<br/>❌ タブ間で共有不可"]
    C["Cookie<br/>（HttpOnly）"] -->|特徴| C1["✅ JSからアクセス不可<br/>✅ リロードしても残る<br/>⚠️ CSRF対策が必要"]
  end

  style A fill:#FF9800,color:#fff
  style B fill:#4CAF50,color:#fff
  style C fill:#2196F3,color:#fff
```

### 本アプリでの方針

| トークン | 保管場所 | 理由 |
|---------|---------|------|
| ID Token / Access Token | **Amplifyデフォルト（localStorage）** | Amplify SDKの標準動作。短命（1時間）なのでリスクは限定的 |
| Refresh Token | **Amplifyデフォルト（localStorage）** | 同上。Cognitoのトークン無効化（Revoke）機能で対処可能 |

> **補足**: セキュリティ要件が高い場合はCookie Storageへの切り替えも可能だが、
> 本アプリでは棋譜管理という性質上、Amplifyデフォルトで十分と判断する。

---

## 5. JWTトークンの中身

ID Tokenは「JWT」（JSON Web Token）という形式。3つのパートがドット（`.`）で繋がった文字列。

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ...  .SflKxwRJSMeKKF2QT4fw...
 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^
           ヘッダー（署名アルゴリズム等）      ペイロード（ユーザー情報）    署名
```

### ペイロード（中身）の例

```json
{
  "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "cognito:username": "hakira",
  "email": "hakira@example.com",
  "email_verified": true,
  "token_use": "id",
  "iss": "https://cognito-idp.ap-northeast-1.amazonaws.com/ap-northeast-1_XXXXX",
  "aud": "1234567890abcdefghijklmnop",
  "exp": 1737543600,
  "iat": 1737540000
}
```

| フィールド | 説明 |
|-----------|------|
| `sub` | ユーザーの一意識別子（UUID） |
| `cognito:username` | ユーザー名。**Lambda側でこの値を使ってユーザーを特定する** |
| `email` | メールアドレス |
| `token_use` | トークン種別（`id` or `access`） |
| `iss` | 発行者（CognitoユーザープールのURL） |
| `aud` | 対象（CognitoアプリクライアントID） |
| `exp` | 有効期限（UNIXタイムスタンプ） |
| `iat` | 発行日時（UNIXタイムスタンプ） |

### API Gatewayの検証内容

API Gatewayは以下を確認してから、Lambdaにリクエストを転送する：

1. **署名の正当性**: Cognitoの公開鍵（JWKS）で署名を検証 → 改ざんされていないか
2. **有効期限**: `exp` が現在時刻より未来か → 期限切れではないか
3. **発行者**: `iss` が正しいCognitoユーザープールか → 偽のトークンではないか
4. **対象**: `aud` が正しいアプリクライアントIDか → 別アプリのトークンではないか

---

## 6. Lambdaでのユーザー特定

API Gatewayが検証を通過すると、トークンの中身（claims）がLambdaのイベントに付加される。

```python
def lambda_handler(event, context):
    # API Gatewayが付加したユーザー情報を取得
    claims = event["requestContext"]["authorizer"]["claims"]

    username = claims["cognito:username"]  # → "hakira"
    email = claims["email"]                # → "hakira@example.com"

    # このusernameでDynamoDBを検索
    # pk = f"kifu#uname#{username}"
```

**Lambda側でトークンの検証処理を書く必要はない**。API Gatewayがすべて行ってくれる。

---

## 7. フロントエンド実装の全体像

### Amplify SDK のセットアップ

```typescript
// main.ts
import { Amplify } from 'aws-amplify'

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: 'ap-northeast-1_XXXXX',
      userPoolClientId: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    }
  }
})
```

### 認証操作の対応表

| 画面 | Amplify API | Lambda API |
|------|------------|------------|
| サインアップ | `signUp()` | **不要** |
| メール確認 | `confirmSignUp()` | **不要** |
| ログイン | `signIn()` | **不要** |
| ログアウト | `signOut()` | **不要** |
| パスワード変更 | `updatePassword()` | **不要** |
| パスワード忘却 | `resetPassword()` + `confirmResetPassword()` | **不要** |
| プロフィール表示 | - | `GET /api/v1/users/me` |
| アカウント削除 | - | `DELETE /api/v1/users/me` |

**認証操作のほとんどはフロントエンドで完結し、Lambda APIは不要。**

### API呼出の共通パターン

```typescript
import { fetchAuthSession } from 'aws-amplify/auth'

async function apiRequest(method: string, path: string, body?: object) {
  // Amplify SDKがトークンの有効期限チェック＆自動更新を行う
  const session = await fetchAuthSession()
  const token = session.tokens?.idToken?.toString()

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  if (response.status === 401) {
    // トークンが無効 → ログイン画面へリダイレクト
    router.push('/login')
    return
  }

  return response.json()
}
```

---

## 8. まとめ：認証で覚えておくこと

```mermaid
graph TD
  A["認証操作<br/>（サインアップ、ログイン等）"] -->|Amplify SDK| B[Cognito]
  B -->|3つのトークン発行| C[Vue 3 SPA]
  C -->|ID Token付きリクエスト| D[API Gateway]
  D -->|公開鍵で署名検証| D
  D -->|ユーザー情報付きで転送| E[Lambda]
  E -->|username でDB検索| F[DynamoDB]

  style A fill:#E1F5FE
  style B fill:#FF9800,color:#fff
  style C fill:#4CAF50,color:#fff
  style D fill:#2196F3,color:#fff
  style E fill:#9C27B0,color:#fff
  style F fill:#607D8B,color:#fff
```

| 役割 | 担当 | 開発者がやること |
|------|------|----------------|
| ログイン/登録 | Cognito + Amplify SDK | Amplify APIを呼ぶだけ |
| トークン管理 | Amplify SDK | 自動（意識不要） |
| トークン検証 | API Gateway | SAMテンプレートで設定するだけ |
| ユーザー特定 | Lambda | `claims["cognito:username"]` を読むだけ |

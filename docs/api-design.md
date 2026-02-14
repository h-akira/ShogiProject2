# 将棋棋譜管理アプリ API設計書

## 概要

旧システム（WAMBDA独自フレームワーク、SSR）をVue 3 SPA + Lambda REST APIに移行する。
全機能を踏襲しつつ、SPAに適したJSON APIとして再設計する。

- **フロントエンド**: Vue 3 + TypeScript、独自将棋盤コンポーネント（shogi-sampleベース）
- **バックエンド**: Lambda + API Gateway（REST JSON API、Lambdalith構成）
- **認証**: Cognito + JWT（フロントからCognito SDK直接、APIはJWT検証のみ）
- **DB**: DynamoDB Single Table Design（旧システムのキー設計を踏襲）
- **局面解析**: SQS FIFO + コンテナイメージLambda（踏襲）

---

## 1. 全体アーキテクチャ

```
[Vue 3 SPA] --(HTTPS)--> [API Gateway + Cognito Authorizer] --> [Lambda] --> [DynamoDB]
     |                                                              |
     +-- Cognito SDK 直接呼出（認証操作）                           +-- [SQS FIFO] --> [Analysis Lambda (Docker)]
```

### Lambda構成

| Lambda | 構成 | 説明 |
|--------|------|------|
| API Lambda | **Lambdalith**（モノリシック） | 全エンドポイントを1つのLambdaで処理。コールドスタート削減 |
| 解析Lambda | コンテナイメージ | やねうら王エンジンを含む。SQSトリガーで起動 |

### 認証の分離

| 操作 | 実行場所 | 方式 |
|------|----------|------|
| サインアップ / ログイン / メール確認 | フロントエンド | Cognito SDK直接 |
| パスワード変更 / リセット | フロントエンド | Cognito SDK直接 |
| ログアウト | フロントエンド | Cognito SDK直接 |
| API呼出 | フロントエンド → API Gateway | `Authorization: Bearer {ID Token}` |
| JWT検証 | API Gateway | Cognito Authorizer（自動） |
| ユーザー特定 | Lambda | `event.requestContext.authorizer.claims["cognito:username"]` |

---

## 2. エンドポイント一覧

### 2.1 ユーザー

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/users/me` | 要 | ユーザー情報取得 |
| DELETE | `/api/v1/users/me` | 要 | アカウント削除 |

### 2.2 棋譜

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/kifus` | 要 | 棋譜一覧（最終更新順、ページネーション） |
| POST | `/api/v1/kifus` | 要 | 棋譜作成 |
| GET | `/api/v1/kifus/{kid}` | 要 | 棋譜詳細 |
| PUT | `/api/v1/kifus/{kid}` | 要 | 棋譜編集 |
| DELETE | `/api/v1/kifus/{kid}` | 要 | 棋譜削除（関連タグレコードも削除） |
| GET | `/api/v1/kifus/explorer` | 要 | フォルダエクスプローラー |
| GET | `/api/v1/shared/{share_code}` | 不要 | 共有棋譜閲覧 |

### 2.3 タグ

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/tags` | 要 | タグ一覧 |
| POST | `/api/v1/tags` | 要 | タグ作成 |
| GET | `/api/v1/tags/{tid}` | 要 | タグ詳細（紐づく棋譜一覧含む） |
| PUT | `/api/v1/tags/{tid}` | 要 | タグ編集 |
| DELETE | `/api/v1/tags/{tid}` | 要 | タグ削除（関連レコードも削除） |

### 2.4 AI局面解析

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/analysis` | 要 | 解析リクエスト送信 |
| GET | `/api/v1/analysis/{aid}` | 要 | 解析結果照会（ポーリング） |

---

## 3. エンドポイント詳細

### 3.1 ユーザー

#### GET `/api/v1/users/me`

現在ログイン中のユーザー情報を取得する。

**Response 200:**
```json
{
  "username": "hakira",
  "email": "hakira@example.com",
  "email_verified": true,
  "created_at": "2025-01-15T10:00:00+09:00"
}
```

#### DELETE `/api/v1/users/me`

アカウントを削除する。Cognitoユーザーを削除し、関連DynamoDBデータはバックグラウンドで削除する。

**Request:**
```json
{
  "current_password": "mypassword123"
}
```

**Response 200:**
```json
{
  "message": "アカウントが削除されました"
}
```

---

### 3.2 棋譜

#### GET `/api/v1/kifus`

自分の棋譜一覧を最終更新日順（降順）で取得する。各棋譜にはタグ情報も含む。

**Query Params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | integer | 10 | 取得件数（1-50） |
| `cursor` | string | - | ページネーションカーソル（Base64エンコード済LastEvaluatedKey） |

**Response 200:**
```json
{
  "items": [
    {
      "kid": "aBcDeFgHiJkL",
      "slug": "2025/01/vs-tanaka.kif",
      "first_or_second": "first",
      "result": "win",
      "share": true,
      "share_code": "aBcDeFgHiJkLmNoPqRsTuVwXyZaBcDeFgHiJ",
      "created": "2025-01-20 14:30:00",
      "latest_update": "2025-01-21 09:15:00",
      "tags": [
        { "tid": "xYz12345", "name": "居飛車" },
        { "tid": "aBc67890", "name": "角換わり" }
      ]
    }
  ],
  "next_cursor": "eyJwayI6IC4uLn0=",
  "has_more": true
}
```

- `next_cursor` が `null` の場合、次のページはない
- フロントエンドは `next_cursor` をそのまま次リクエストの `cursor` パラメータに渡す

#### POST `/api/v1/kifus`

新規棋譜を作成する。

**Request:**
```json
{
  "slug": "2025/01/vs-tanaka",
  "kifu": "# ---- Kifu for Windows V7 V7.71 棋譜ファイル ----\n...",
  "memo": "角換わり腰掛け銀の定跡形。途中で相手が変化した。",
  "first_or_second": "first",
  "result": "win",
  "share": false,
  "tag_ids": ["xYz12345", "aBc67890"]
}
```

**フィールド定義:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `slug` | string | 要 | 1-100文字、`/`開始不可、`#`含有不可、`.kif`不要（自動付与） |
| `kifu` | string | - | KIF形式文字列 |
| `memo` | string | - | 自由テキスト |
| `first_or_second` | string | - | `"none"` / `"first"` / `"second"`（default: `"none"`） |
| `result` | string | - | `"none"` / `"win"` / `"lose"` / `"sennichite"` / `"jishogi"`（default: `"none"`） |
| `share` | boolean | - | default: `false` |
| `tag_ids` | string[] | - | タグIDの配列（default: `[]`） |

**Response 201:**
```json
{
  "kid": "aBcDeFgHiJkL",
  "slug": "2025/01/vs-tanaka.kif",
  "kifu": "# ---- Kifu for Windows ...",
  "memo": "角換わり腰掛け銀の定跡形。途中で相手が変化した。",
  "first_or_second": "first",
  "result": "win",
  "share": false,
  "share_code": "aBcDeFgHiJkLmNoPqRsTuVwXyZaBcDeFgHiJ",
  "created": "2025-01-20 14:30:00",
  "latest_update": "2025-01-20 14:30:00",
  "tags": [
    { "tid": "xYz12345", "name": "居飛車" },
    { "tid": "aBc67890", "name": "角換わり" }
  ]
}
```

**Error 409 (slug重複):**
```json
{
  "error": {
    "code": "CONFLICT",
    "message": "Slug already exists",
    "details": {}
  }
}
```

#### GET `/api/v1/kifus/{kid}`

棋譜の詳細情報を取得する。盤面再生に必要な全データを含む。

**Response 200:** POST作成時と同形式の棋譜オブジェクト

#### PUT `/api/v1/kifus/{kid}`

棋譜を編集する。

**Request:** POST と同形式。`tag_ids`は最終状態を送信し、サーバー側で差分更新する。

**Response 200:** 更新後の棋譜オブジェクト

#### DELETE `/api/v1/kifus/{kid}`

棋譜を削除する。棋譜に紐づくタグ関連レコード（`tag#kid#{kid}` / `tid#{tid}`）も同時に削除する。

**Response 204:** No Content

#### GET `/api/v1/kifus/explorer`

フォルダエクスプローラー。slugの階層構造をフォルダとして表示する。

**Query Params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | string | - | Base64URLエンコードされたフォルダパス（省略=ルート） |

**Response 200:**
```json
{
  "current_path": "2025/01",
  "breadcrumbs": [
    { "name": "2025", "path": "MjAyNQ" },
    { "name": "01", "path": "MjAyNS8wMQ" }
  ],
  "folders": [
    { "name": "practice", "count": 5, "path": "MjAyNS8wMS9wcmFjdGljZQ" }
  ],
  "files": [
    { "name": "vs-tanaka.kif", "kid": "aBcDeFgHiJkL" },
    { "name": "vs-suzuki.kif", "kid": "mNoPqRsTuVwX" }
  ]
}
```

- `path` はBase64URLエンコード（パディングなし）されたフォルダパス
- `breadcrumbs` は現在のパスまでの各フォルダのナビゲーション用
- `folders[].path` と `breadcrumbs[].path` も同様にBase64URLエンコード済

> **実装方針**: DynamoDBのCommonLSIに対して `begins_with("slug#{path}/")` でクエリし、
> 指定パス以下の全件を取得してサーバー側でフォルダ/ファイルに分類する（旧システム踏襲）。
> 1ユーザーあたり数千件規模であれば実用上問題ない。

#### GET `/api/v1/shared/{share_code}`

**認証不要。** 共有コードに対応する棋譜を取得する。`share`フラグが`true`の棋譜のみ閲覧可能。
プライベート情報（kid, slug, tags, username）は返さない。

**Response 200:**
```json
{
  "kifu": "# ---- Kifu for Windows V7 V7.71 棋譜ファイル ----\n...",
  "memo": "角換わり腰掛け銀の定跡形",
  "first_or_second": "first",
  "result": "win",
  "share_code": "aBcDeFgHiJkLmNoPqRsTuVwXyZaBcDeFgHiJ",
  "created": "2025-01-20 14:30:00",
  "latest_update": "2025-01-21 09:15:00"
}
```

---

### 3.3 タグ

#### GET `/api/v1/tags`

自分のタグ一覧を取得する。

**Response 200:**
```json
{
  "items": [
    {
      "tid": "xYz12345",
      "name": "居飛車",
      "created": "2025-01-10 10:00:00",
      "latest_update": "2025-01-10 10:00:00"
    }
  ]
}
```

#### POST `/api/v1/tags`

新規タグを作成する。

**Request:**
```json
{
  "name": "四間飛車"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | 要 | 1-127文字 |

**Response 201:**
```json
{
  "tid": "nEwTaG12",
  "name": "四間飛車",
  "created": "2025-01-22 10:00:00",
  "latest_update": "2025-01-22 10:00:00"
}
```

#### GET `/api/v1/tags/{tid}`

タグの詳細情報と、そのタグが付与された棋譜一覧を返す。

**Response 200:**
```json
{
  "tid": "xYz12345",
  "name": "居飛車",
  "created": "2025-01-10 10:00:00",
  "latest_update": "2025-01-10 10:00:00",
  "kifus": [
    {
      "kid": "aBcDeFgHiJkL",
      "slug": "2025/01/vs-tanaka.kif",
      "latest_update": "2025-01-21 09:15:00",
      "created": "2025-01-20 14:30:00"
    }
  ],
  "kifu_count": 1
}
```

#### PUT `/api/v1/tags/{tid}`

タグ名を編集する。

**Request:**
```json
{
  "name": "居飛車（改名後）"
}
```

**Response 200:** 更新後のタグオブジェクト

#### DELETE `/api/v1/tags/{tid}`

タグを削除する。棋譜に付与されている関連レコード（`tag#kid#{kid}` / `tid#{tid}`）も同時に削除する。

**Response 204:** No Content

---

### 3.4 AI局面解析

#### POST `/api/v1/analysis`

AI解析リクエストを送信する。SQS FIFOキューにメッセージを送信し、非同期で解析が実行される。

**Request:**
```json
{
  "position": "position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
  "movetime": 3000
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `position` | string | 要 | `position sfen `で始まるSFEN文字列 |
| `movetime` | integer | - | `3000` / `5000` / `10000`（default: `3000`） |

**レート制限:**
- SQSキュー内メッセージ数が5以上の場合 → 拒否
- 直近1時間の解析リクエストが30件以上の場合 → 拒否

**Response 202 Accepted:**
```json
{
  "aid": "aNaLySiS12345",
  "status": "accepted"
}
```

**Response 429 Too Many Requests:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "解析リクエストの上限に達しています。しばらくお待ちください。",
    "details": {}
  }
}
```

#### GET `/api/v1/analysis/{aid}`

解析結果を照会する（ポーリング用）。フロントエンドは数秒間隔でポーリングし、`status`が`"running"`の間はリトライする。

**Response 200（実行中）:**
```json
{
  "aid": "aNaLySiS12345",
  "status": "running",
  "result": null
}
```

**Response 200（完了）:**
```json
{
  "aid": "aNaLySiS12345",
  "status": "completed",
  "result": {
    "candidates": [
      {
        "rank": 1,
        "score": 120,
        "pv": "▲７六歩(77) △８四歩(83) ▲２六歩(27)"
      },
      {
        "rank": 2,
        "score": 95,
        "pv": "▲２六歩(27) △８四歩(83) ▲７六歩(77)"
      }
    ]
  }
}
```

**Response 200（失敗）:**
```json
{
  "aid": "aNaLySiS12345",
  "status": "failed",
  "result": null
}
```

※ 解析結果のSFEN→日本語棋譜表記変換はサーバー側で行う（旧システムの`_response2message`と同様）

---

## 4. エラーレスポンス統一フォーマット

すべてのエンドポイントで共通のエラーフォーマットを使用する。

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "人間が読めるエラーメッセージ",
    "details": {}
  }
}
```

### エラーコード一覧

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `VALIDATION_ERROR` | バリデーションエラー（`details`にフィールド別エラーを含む） |
| 400 | `INVALID_REQUEST` | リクエスト形式不正 |
| 401 | `UNAUTHORIZED` | 認証が必要（トークン未送信 or 無効） |
| 403 | `FORBIDDEN` | 権限なし（他ユーザーのリソースへのアクセス） |
| 404 | `RESOURCE_NOT_FOUND` | リソースが存在しない |
| 409 | `CONFLICT` | 競合（slugの重複等） |
| 429 | `RATE_LIMIT_EXCEEDED` | レート制限超過（解析リクエスト） |
| 500 | `INTERNAL_ERROR` | サーバー内部エラー |

**バリデーションエラーの例:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "入力値に誤りがあります",
    "details": {
      "slug": "Slug cannot start with '/'.",
      "kifu": "KIF形式の棋譜データが必要です"
    }
  }
}
```

---

## 5. DynamoDB テーブル設計 (Single Table Design)

### 5.1 テーブル基本情報

| 項目 | 値 |
|------|-----|
| テーブル名 | `table-sgp-pro-main` |
| Partition Key | `pk` (String) |
| Sort Key | `sk` (String) |
| 課金モード | PAY_PER_REQUEST (On-Demand) |
| TTL属性 | `expired` |

### 5.2 エンティティとキー設計

#### 棋譜 (Kifu)

| 属性 | 値 | 例 |
|------|-----|-----|
| `pk` | `kifu#uname#{username}` | `kifu#uname#hakira` |
| `sk` | `kid#{kid}` | `kid#aBcDeFgHiJkL` |
| `cgsi_pk` | `scode#{share_code}` | `scode#aBcDeFgH...` |
| `clsi_sk` | `slug#{slug}.kif` | `slug#2025/01/vs-tanaka.kif` |
| `kifu` | KIF形式文字列 | - |
| `memo` | メモ文字列 | - |
| `first_or_second` | `none` / `first` / `second` | `first` |
| `result` | `none` / `win` / `lose` / `sennichite` / `jishogi` | `win` |
| `share` | Boolean | `true` |
| `created` | ISO文字列 | `2025-01-20 14:30:00` |
| `latest_update` | ISO文字列 | `2025-01-21 09:15:00` |

#### タグ (Tag)

| 属性 | 値 | 例 |
|------|-----|-----|
| `pk` | `tag#uname#{username}` | `tag#uname#hakira` |
| `sk` | `tid#{tid}` | `tid#xYz12345` |
| `clsi_sk` | `tname#{tag_name}` | `tname#居飛車` |
| `tname` | タグ名 | `居飛車` |
| `created` | ISO文字列 | `2025-01-10 10:00:00` |
| `latest_update` | ISO文字列 | `2025-01-10 10:00:00` |

#### 棋譜-タグ関連 (Kifu-Tag Association)

| 属性 | 値 | 例 |
|------|-----|-----|
| `pk` | `tag#kid#{kid}` | `tag#kid#aBcDeFgHiJkL` |
| `sk` | `tid#{tid}` | `tid#xYz12345` |
| `clsi_sk` | `tname#{tag_name}` | `tname#居飛車` |
| `tname` | タグ名（非正規化） | `居飛車` |
| `latest_update` | ISO文字列 | `2025-01-20 14:30:00` |

#### 解析 (Analysis)

| 属性 | 値 | 例 |
|------|-----|-----|
| `pk` | `analysis` | `analysis` |
| `sk` | `aid#{aid}` | `aid#aNaLySiS12345` |
| `cgsi_pk` | `analysis#uname#{username}` | `analysis#uname#hakira` |
| `created` | ISO文字列 | `2025-01-22 10:00:00` |
| `status` | `waiting` / `successed` / `failed` | `waiting` |
| `response` | JSON文字列（解析結果） | - |
| `expired` | UNIX timestamp (Number, TTL) | `1737540000` |

### 5.3 環境変数（Lambda）

旧システムではDynamoDB上にシステム設定エンティティを持っていたが、
上限値は変更頻度が低いため環境変数で管理する。

| 環境変数名 | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `KIFU_MAX` | integer | `2000` | 1ユーザーあたりの棋譜上限数 |
| `TAG_MAX` | integer | `50` | 1ユーザーあたりのタグ上限数 |
| `MAIN_TABLE_NAME` | string | - | DynamoDBテーブル名 |
| `SQS_QUEUE_URL` | string | - | 解析用SQS FIFOキューURL |

### 5.5 インデックス設計

#### Local Secondary Indexes (LSI)

| Index | PK | SK | 用途 |
|-------|-----|-----|------|
| CommonLSI | `pk` | `clsi_sk` | slug検索、タグ名検索、フォルダエクスプローラー |
| LatestUpdateIndex | `pk` | `latest_update` | 棋譜一覧（最終更新順） |
| CreatedIndex | `pk` | `created` | 解析レート制限チェック（直近1時間） |

#### Global Secondary Indexes (GSI)

| Index | PK | SK | 用途 |
|-------|-----|-----|------|
| CommonGSI | `cgsi_pk` | - | 共有コード検索 |
| SwapIndex | `sk` | `pk` | タグ逆引き（タグ削除時等） |

### 5.6 アクセスパターン対応表

| アクセスパターン | Table/Index | クエリ条件 |
|-----------------|-------------|-----------|
| 棋譜一覧（最終更新順） | LatestUpdateIndex | pk=`kifu#uname#{user}`, ScanIndexForward=false |
| 棋譜詳細取得 | Main | pk=`kifu#uname#{user}`, sk=`kid#{kid}` |
| slug重複チェック | CommonLSI | pk=`kifu#uname#{user}`, clsi_sk=`slug#{slug}.kif` |
| フォルダエクスプローラー | CommonLSI | pk=`kifu#uname#{user}`, clsi_sk begins_with `slug#{path}/` |
| 共有コード検索 | CommonGSI | cgsi_pk=`scode#{code}` |
| タグ一覧 | Main | pk=`tag#uname#{user}` |
| 棋譜のタグ取得 | Main | pk=`tag#kid#{kid}` |
| タグの棋譜逆引き | SwapIndex | sk=`tid#{tid}`, pk begins_with `tag#kid#` |
| 解析結果取得 | Main | pk=`analysis`, sk=`aid#{aid}` |
| 解析レート制限チェック | CreatedIndex | pk=`analysis`, created > (1時間前) |

---

## 6. ページネーション

カーソルベースページネーション。DynamoDB `LastEvaluatedKey` をBase64URLエンコードして使用する。

### 方式

1. サーバーがDynamoDBクエリ結果の `LastEvaluatedKey` をBase64URLエンコードして `next_cursor` として返す
2. フロントエンドは `next_cursor` をそのまま次リクエストの `cursor` クエリパラメータに渡す
3. `next_cursor` が `null` の場合、次のページはない

### レスポンスフォーマット

```json
{
  "items": [...],
  "next_cursor": "eyJwayI6IC4uLn0",
  "has_more": true
}
```

### 対象エンドポイント

- `GET /api/v1/kifus` — `limit` (default 10, max 50) + `cursor`

---

## 7. 認証フロー

### フロントエンドの認証操作（Cognito SDK直接）

| 操作 | Cognito SDK メソッド |
|------|---------------------|
| サインアップ | `signUp()` |
| メール確認 | `confirmSignUp()` |
| ログイン | `signIn()` |
| ログアウト | `signOut()` |
| パスワード変更 | `changePassword()` |
| パスワード忘却（コード送信） | `forgotPassword()` |
| パスワードリセット（コード確認） | `forgotPasswordSubmit()` |

### API Gateway Cognito Authorizer

```yaml
# SAM template での設定
Resources:
  ApiGateway:
    Type: AWS::Serverless::Api
    Properties:
      Auth:
        DefaultAuthorizer: CognitoAuthorizer
        Authorizers:
          CognitoAuthorizer:
            UserPoolArn: !GetAtt UserPool.Arn
            Identity:
              Header: Authorization

  # 共有エンドポイントは認証不要
  SharedKifuFunction:
    Type: AWS::Serverless::Function
    Properties:
      Events:
        SharedKifu:
          Type: Api
          Properties:
            Path: /api/v1/shared/{share_code}
            Method: GET
            Auth:
              Authorizer: NONE
```

### Lambda側のユーザー特定

```python
def get_username_from_event(event):
    """API Gateway Cognito Authorizerからusernameを取得"""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    username = claims.get("cognito:username")
    if not username:
        raise UnauthorizedError("Username not found in token")
    return username
```

---

## 8. CORS設定

SPA + API構成のため、API GatewayでCORSを設定する。

```yaml
Globals:
  Api:
    Cors:
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
      AllowHeaders: "'Content-Type,Authorization'"
      AllowOrigin: "'https://your-frontend-domain.com'"
      AllowCredentials: false
```

---

## 9. Lambda関数構成

```
Lambda/
  handler.py              # メインハンドラー（ルーティング）
  routes/
    kifus.py              # 棋譜関連エンドポイント
    tags.py               # タグ関連エンドポイント
    analysis.py           # 解析関連エンドポイント
    users.py              # ユーザー関連エンドポイント
    shared.py             # 共有棋譜エンドポイント
  services/
    kifu_service.py       # 棋譜ビジネスロジック
    tag_service.py        # タグビジネスロジック
    analysis_service.py   # 解析ビジネスロジック
    user_service.py       # ユーザービジネスロジック
  models/
    dynamo.py             # DynamoDBアクセス層
  utils/
    shogi.py              # 将棋ロジック（SFEN→日本語棋譜変換等）
    pagination.py         # ページネーションヘルパー
    validation.py         # バリデーションヘルパー
    errors.py             # エラーハンドリング
```

---

## 10. 旧システムからの主な変更点

| 項目 | 旧システム | 新システム |
|------|-----------|-----------|
| アーキテクチャ | SSR (WAMBDA) | SPA (Vue 3) + REST API |
| 認証処理 | サーバー側で全処理 | フロントでCognito SDK、APIはJWT検証のみ |
| APIレスポンス | HTML | JSON |
| URL構造 | `/kifu/index/{username}` | `/api/v1/kifus`（usernameはJWTから取得） |
| セッション管理 | Cookie (JWT in Cookie) | Authorization Bearerヘッダー |
| フォルダパス | Base64 URLパス | Base64 クエリパラメータ |
| 将棋盤 | shogi-playerライブラリ | 独自実装（shogi-sampleベース） |
| DynamoDB | Single Table | Single Table（踏襲） |
| 解析結果変換 | サーバー側（Shogiクラス） | サーバー側（維持） |
| タグ更新 | 差分更新 | 差分更新（維持、tag_ids最終状態送信） |

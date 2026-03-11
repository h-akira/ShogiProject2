# BUG-003: トークンリフレッシュ未実装により1時間で認証切れ＆フロントエンドがログアウトしない

## ステータス

修正済み（検証待ち）

## 発見日

2026-03-11

## 概要

フロントエンドにトークンリフレッシュ機能が実装されておらず、Cognito のアクセストークン/IDトークンの有効期限（1時間）経過後にバックエンド API が認証エラーになる。さらに、認証エラー時にフロントエンドをログアウトさせる処理もないため、フロントエンドはログイン状態のまま API だけ失敗する不整合が発生する。

## 症状

- ログインから約1時間経過すると、バックエンド API 呼び出しが認証エラー（401）になる
- バックエンドが認証エラーを返しても、フロントエンドはログイン状態のまま表示される
- ユーザーから見ると「ログインしているのに操作が全て失敗する」状態になる

## 原因

3つの実装不備が重なっている。

1. **リフレッシュトークンが保存されるだけで使われていない**: `auth.ts` の `saveTokens()` でリフレッシュトークンを `sessionStorage` に保存しているが、期限切れ時にリフレッシュトークンを使って新しいトークンを取得する処理が存在しない
2. **API 呼び出し時の 401 ハンドリングがない**: `custom-fetch.ts` でレスポンスステータスが 401 の場合にリフレッシュを試みる、またはログアウトさせるロジックがない
3. **フロントエンドの認証状態がトークンの有効性を見ていない**: `auth.ts` の `isAuthenticated` は `!!accessToken.value`（トークン文字列の存在有無）だけで判定しており、トークンの `exp` クレーム（有効期限）をチェックしていない

## 影響範囲

- `Frontend/shogi-main/src/auth/auth.ts` — リフレッシュ機能なし、有効期限チェックなし
- `Frontend/shogi-main/src/api/custom-fetch.ts` — 401 ハンドリングなし
- 認証が必要な全ページ・全 API 呼び出しに影響

## 再現手順

1. ログインする
2. 1時間以上放置する（またはブラウザの開発者ツールで sessionStorage のトークンを期限切れのものに差し替える）
3. 棋譜一覧など認証が必要なページで操作する
4. API 呼び出しが失敗するが、フロントエンドはログイン状態のまま表示される

## Cognito トークン有効期限設定（参考）

| トークン | 有効期限 | 設定箇所 |
|---------|---------|---------|
| Access Token | 1時間 | `Infra/stacks/cognito_stack.py` L104 |
| ID Token | 1時間 | `Infra/stacks/cognito_stack.py` L105 |
| Refresh Token | 30日 | `Infra/stacks/cognito_stack.py` L106 |

## 修正案

### 案1: custom-fetch での 401 検知 + リフレッシュ + ログアウトフォールバック

`custom-fetch.ts` で 401 レスポンスを検知した際に、リフレッシュトークンを使って Cognito `/oauth2/token` エンドポイント（`grant_type=refresh_token`）で新しいトークンを取得し、リクエストをリトライする。リフレッシュも失敗した場合は `logout()` を呼んでフロントエンドもログアウトさせる。

- メリット: 実装がシンプル。ユーザーは1時間ごとの切れ目を意識しない
- デメリット: 初回の 401 発生時に1リクエスト分の遅延が生じる

### 案2: 案1 + プロアクティブなトークンリフレッシュ

案1に加え、IDトークンの `exp` クレームを監視し、期限切れの数分前にバックグラウンドでリフレッシュを実行するタイマーを設ける。

- メリット: 401 が発生する前にトークンが更新されるため、ユーザー体験が最も良い
- デメリット: タイマー管理の実装が追加で必要

## 対応

案1を採用して実装。

### 変更ファイル

- `Frontend/shogi-main/src/auth/auth.ts`
  - `refreshTokens()`: リフレッシュトークンで Cognito `/oauth2/token`（`grant_type=refresh_token`）を呼び出し、新しいアクセストークン/IDトークンを取得する。同時呼び出しの直列化あり
  - `forceLogout()`: 認証切れ時に外部から呼び出せるログアウト関数
- `Frontend/shogi-main/src/api/custom-fetch.ts`
  - 401 レスポンス検知時に `refreshTokens()` でリフレッシュを試行し、成功すればリトライ
  - リフレッシュ失敗またはリトライも 401 の場合は `forceLogout()` で強制ログアウト

## 関連

- `Infra/stacks/cognito_stack.py` — Cognito User Pool Client のトークン有効期限設定
- [Cognito Token Endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html) — `grant_type=refresh_token` の仕様

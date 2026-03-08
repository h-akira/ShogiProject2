# 002: Cognito ユーザー識別子が UUID に変更

## 変更概要

Infra ユニットの Cognito User Pool 設定として `sign_in_aliases: email=True` を採用した。
これにより、ユーザーはメールアドレスでサインイン可能だが、`cognito:username` はメールアドレスではなく **Cognito が自動生成する UUID** となる。

## 対象ファイル

- `Infra/stacks/cognito_stack.py` — Cognito User Pool の `sign_in_aliases` 設定

## 影響を受けるユニット

### Backend (メイン API)

- `Backend/main/src/common/auth.py` の `get_username()` が `cognito:username` を返しており、これが UUID になる
- データストアのユーザー識別子として UUID が使われることになるため、既存の想定（ユーザー名文字列）と異なる可能性がある
- `GET /api/v1/main/users/me` のレスポンスで返す `username` フィールドの値が UUID になる

### Backend (解析 API)

- Cognito Access Token から取得する `cognito:username` が UUID になる

### Frontend

- プロフィールページで表示する「ユーザー名」が UUID になる
- 表示用のユーザー名が必要な場合は、Cognito の `email` 属性や `preferred_username` カスタム属性を使用する必要がある

## 各ユニットで必要な対応

### Backend (メイン API)

- `cognito:username`（UUID）をユーザー識別子として使用する方針自体は問題ない（一意性が保証される）
- ユーザー情報取得 API のレスポンスで「表示用ユーザー名」が必要な場合は、Cognito の `email` 属性を返すか、`preferred_username` カスタム属性を追加する

### Backend (解析 API)

- 特に対応不要（UUID でユーザーを識別できる）

### Frontend

- プロフィールページの「ユーザー名」表示を、メイン API から取得する `email` に変更するか、別途表示名を設けるか検討が必要

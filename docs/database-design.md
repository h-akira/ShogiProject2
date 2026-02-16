# DynamoDB テーブル設計

Single Table Design による棋譜管理アプリのデータベース設計。

旧システム（WAMBDA）のキー設計を踏襲しつつ、新APIに必要なアクセスパターンを網羅する。

---

## 1. テーブル基本情報

| 項目 | 値 |
|------|-----|
| テーブル名 | `table-sgp-pro-main` |
| Partition Key | `pk` (String) |
| Sort Key | `sk` (String) |
| 課金モード | PAY_PER_REQUEST (On-Demand) |
| TTL属性 | `expired` |

---

## 2. エンティティ定義

### 2.1 棋譜 (Kifu)

| 属性 | 型 | キー | 必須 | 説明 |
|------|-----|------|------|------|
| `pk` | String | PK | 要 | `kifu#uname#{username}` |
| `sk` | String | SK | 要 | `kid#{kid}` |
| `cgsi_pk` | String | GSI-PK | - | `scode#{share_code}` — 共有コード検索用 |
| `clsi_sk` | String | LSI-SK | 要 | `slug#{slug}.kif` — slug検索・エクスプローラー用 |
| `kifu` | String | - | - | KIF形式棋譜データ |
| `memo` | String | - | - | メモ |
| `first_or_second` | String | - | 要 | `none` / `first` / `second` |
| `result` | String | - | 要 | `none` / `win` / `lose` / `sennichite` / `jishogi` |
| `share` | Boolean | - | 要 | 共有フラグ（default: `false`） |
| `share_code` | String | - | 要 | 36文字のランダム文字列（作成時に自動生成） |
| `created` | String | LSI-SK | 要 | ISO形式 `YYYY-MM-DD HH:mm:ss` |
| `latest_update` | String | LSI-SK | 要 | ISO形式 `YYYY-MM-DD HH:mm:ss` |

**kid**: 12文字のランダム英数字文字列。

**slug制約**:
- 1〜100文字
- `/` 開始不可、`#` 含有不可
- `.kif` は自動付与（ユーザー入力には含めない）
- 同一ユーザー内で一意

**share_code**: 棋譜作成時に必ず生成する。`share` が `false` の場合でもコード自体は保持する（共有ON/OFF切り替え時にコードを再生成しない）。

#### データ例

```
pk:            kifu#uname#hakira
sk:            kid#aBcDeFgHiJkL
cgsi_pk:       scode#aBcDeFgHiJkLmNoPqRsTuVwXyZaBcDeFgHiJ
clsi_sk:       slug#2025/01/vs-tanaka.kif
kifu:          "# ---- Kifu for Windows V7 ..."
memo:          "角換わり腰掛け銀の定跡形"
first_or_second: "first"
result:        "win"
share:         true
share_code:    "aBcDeFgHiJkLmNoPqRsTuVwXyZaBcDeFgHiJ"
created:       "2025-01-20 14:30:00"
latest_update: "2025-01-21 09:15:00"
```

### 2.2 タグ (Tag)

| 属性 | 型 | キー | 必須 | 説明 |
|------|-----|------|------|------|
| `pk` | String | PK | 要 | `tag#uname#{username}` |
| `sk` | String | SK | 要 | `tid#{tid}` |
| `clsi_sk` | String | LSI-SK | 要 | `tname#{tag_name}` — タグ名検索・一意性チェック用 |
| `tname` | String | - | 要 | タグ名（1〜127文字） |
| `created` | String | - | 要 | ISO形式 |
| `latest_update` | String | - | 要 | ISO形式 |

**tid**: 8文字のランダム英数字文字列。

#### データ例

```
pk:            tag#uname#hakira
sk:            tid#xYz12345
clsi_sk:       tname#居飛車
tname:         "居飛車"
created:       "2025-01-10 10:00:00"
latest_update: "2025-01-10 10:00:00"
```

### 2.3 棋譜-タグ関連 (Kifu-Tag Association)

棋譜とタグの多対多関係を表現するエンティティ。

| 属性 | 型 | キー | 必須 | 説明 |
|------|-----|------|------|------|
| `pk` | String | PK | 要 | `tag#kid#{kid}` |
| `sk` | String | SK | 要 | `tid#{tid}` |
| `clsi_sk` | String | LSI-SK | 要 | `tname#{tag_name}` — タグ名順での取得用 |
| `tname` | String | - | 要 | タグ名（非正規化コピー） |
| `latest_update` | String | - | 要 | ISO形式 |

**非正規化の理由**: 棋譜詳細取得時に `pk=tag#kid#{kid}` でクエリするだけでタグ名を含む情報を返せるようにするため。タグマスタへの追加クエリが不要になる。

#### データ例

```
pk:            tag#kid#aBcDeFgHiJkL
sk:            tid#xYz12345
clsi_sk:       tname#居飛車
tname:         "居飛車"
latest_update: "2025-01-20 14:30:00"
```

### 2.4 解析 (Analysis)

| 属性 | 型 | キー | 必須 | 説明 |
|------|-----|------|------|------|
| `pk` | String | PK | 要 | `analysis` (固定値) |
| `sk` | String | SK | 要 | `aid#{aid}` |
| `cgsi_pk` | String | GSI-PK | 要 | `analysis#uname#{username}` — ユーザー別解析履歴用 |
| `position` | String | - | 要 | SFEN形式の局面文字列 |
| `movetime` | Number | - | 要 | 思考時間（ミリ秒） |
| `status` | String | - | 要 | `waiting` / `successed` / `failed` |
| `response` | String | - | - | JSON文字列（解析結果。完了時に格納） |
| `created` | String | LSI-SK | 要 | ISO形式 |
| `expired` | Number | TTL | 要 | UNIX timestamp（TTL自動削除用） |

**aid**: 8文字のランダム英数字文字列。

**TTL**: 解析結果は一時的なデータのため、1時間後に自動削除する。

#### データ例

```
pk:            analysis
sk:            aid#aNaLySiS12345
cgsi_pk:       analysis#uname#hakira
position:      "position sfen lnsgkgsnl/..."
movetime:      3000
status:        "waiting"
response:      null
created:       "2025-01-22 10:00:00"
expired:       1737540000
```

---

## 3. インデックス設計

### 3.1 Local Secondary Indexes (LSI)

LSI はテーブル作成時にのみ定義可能（後から追加不可）。

| Index名 | PK | SK | 射影 | 用途 |
|---------|-----|-----|------|------|
| CommonLSI | `pk` | `clsi_sk` | ALL | slug検索、タグ名検索、フォルダエクスプローラー |
| LatestUpdateIndex | `pk` | `latest_update` | ALL | 棋譜一覧（最終更新順） |
| CreatedIndex | `pk` | `created` | ALL | 解析レート制限チェック（直近1時間） |

> **射影をALLにする理由**: 棋譜一覧ではタグ情報以外の全属性をレスポンスに含める必要がある。KEYS_ONLYにすると本テーブルへのFetchが発生し、コスト・レイテンシが増加する。1ユーザーあたりの棋譜数は最大2000件であり、LSIのパーティションサイズ上限（10GB）に達するリスクは低い。

### 3.2 Global Secondary Indexes (GSI)

| Index名 | PK | SK | 射影 | 用途 |
|---------|-----|-----|------|------|
| CommonGSI | `cgsi_pk` | - | ALL | 共有コード検索、ユーザー別解析履歴 |
| SwapIndex | `sk` | `pk` | KEYS_ONLY | タグ逆引き（タグ削除時に関連レコードを特定） |

> **SwapIndexの射影がKEYS_ONLYの理由**: タグ削除時は `pk` と `sk` が分かれば `DeleteItem` を発行できるため、他の属性は不要。

---

## 4. アクセスパターン対応表

| # | アクセスパターン | Table/Index | 操作 | クエリ条件 |
|---|-----------------|-------------|------|-----------|
| 1 | 棋譜一覧（最終更新順） | LatestUpdateIndex | Query | pk=`kifu#uname#{user}`, ScanIndexForward=false |
| 2 | 棋譜詳細取得 | Main | GetItem | pk=`kifu#uname#{user}`, sk=`kid#{kid}` |
| 3 | slug重複チェック | CommonLSI | Query | pk=`kifu#uname#{user}`, clsi_sk=`slug#{slug}.kif` |
| 4 | フォルダエクスプローラー | CommonLSI | Query | pk=`kifu#uname#{user}`, clsi_sk begins_with `slug#{path}/` |
| 5 | 共有コード検索 | CommonGSI | Query | cgsi_pk=`scode#{code}` |
| 6 | タグ一覧 | Main | Query | pk=`tag#uname#{user}` |
| 7 | 棋譜のタグ取得 | Main | Query | pk=`tag#kid#{kid}` |
| 8 | タグの棋譜逆引き | SwapIndex | Query | sk=`tid#{tid}`, pk begins_with `tag#kid#` |
| 9 | 解析結果取得 | Main | GetItem | pk=`analysis`, sk=`aid#{aid}` |
| 10 | 解析レート制限チェック | CreatedIndex | Query | pk=`analysis`, created > (1時間前) |
| 11 | 棋譜数カウント | Main | Query (Select=COUNT) | pk=`kifu#uname#{user}` |
| 12 | タグ数カウント | Main | Query (Select=COUNT) | pk=`tag#uname#{user}` |

### パターン詳細

#### #1 棋譜一覧（マイページ）

```python
table.query(
    IndexName='LatestUpdateIndex',
    KeyConditionExpression='pk = :pk',
    ExpressionAttributeValues={':pk': f'kifu#uname#{username}'},
    ScanIndexForward=False,
    Limit=10,
)
```

返却された各棋譜に対して、タグ情報を付加する（パターン#7）。

#### #4 フォルダエクスプローラー

```python
table.query(
    IndexName='CommonLSI',
    KeyConditionExpression='pk = :pk AND begins_with(clsi_sk, :prefix)',
    ExpressionAttributeValues={
        ':pk': f'kifu#uname#{username}',
        ':prefix': f'slug#{path}/',
    },
)
```

返却結果をサーバー側でフォルダ/ファイルに分類する。

#### #7 棋譜のタグ取得

```python
table.query(
    KeyConditionExpression='pk = :pk',
    ExpressionAttributeValues={':pk': f'tag#kid#{kid}'},
)
```

`tname` 属性が非正規化されているため、タグマスタへの追加クエリは不要。

#### #8 タグの棋譜逆引き（タグ削除時）

```python
table.query(
    IndexName='SwapIndex',
    KeyConditionExpression='sk = :sk AND begins_with(pk, :prefix)',
    ExpressionAttributeValues={
        ':sk': f'tid#{tid}',
        ':prefix': 'tag#kid#',
    },
)
```

返却された各アイテムの `pk` (= `tag#kid#{kid}`) と `sk` (= `tid#{tid}`) を使って `DeleteItem` を発行。

#### #10 解析レート制限チェック

```python
from datetime import datetime, timedelta

one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

table.query(
    IndexName='CreatedIndex',
    KeyConditionExpression='pk = :pk AND created > :since',
    ExpressionAttributeValues={
        ':pk': 'analysis',
        ':since': one_hour_ago,
    },
    Select='COUNT',
)
```

---

## 5. データ操作と整合性

### 5.1 棋譜作成

1. slug重複チェック（パターン#3）
2. 棋譜数カウント（パターン#11）→ 上限チェック
3. `PutItem` で棋譜エンティティを作成
4. `tag_ids` が指定されている場合、各タグの関連エンティティを `BatchWriteItem` で作成

### 5.2 棋譜編集（タグの差分更新）

リクエストの `tag_ids` は最終状態を表す。サーバー側で現在のタグ（パターン#7）と比較し、差分を算出する。

```
current_tags = {t1, t2, t3}
new_tags     = {t2, t3, t4}

to_add    = new_tags - current_tags  → {t4}
to_remove = current_tags - new_tags  → {t1}
```

- `to_add`: 関連エンティティを `PutItem`
- `to_remove`: 関連エンティティを `DeleteItem`

slug変更時は `clsi_sk` が変わるため、slugの重複チェック（パターン#3）を再実行する。`clsi_sk` はアイテムの属性として `UpdateItem` で更新可能。

### 5.3 棋譜削除

1. `DeleteItem` で棋譜エンティティを削除
2. パターン#7 で関連タグを取得
3. 各関連エンティティを `BatchWriteItem` (Delete) で削除

### 5.4 タグ名変更

タグ名はタグマスタと関連エンティティの両方に保持されている（非正規化）。タグ名変更時は以下の更新が必要:

1. タグマスタの `tname` と `clsi_sk` を `UpdateItem` で更新
2. パターン#8 でこのタグに紐づく全関連エンティティを取得
3. 各関連エンティティの `tname` と `clsi_sk` を `UpdateItem` で更新

> **トレードオフ**: タグ名変更は低頻度の操作であり、関連レコードの上限も棋譜上限（2000件）以下。一方、棋譜詳細取得（高頻度）でタグ名の追加クエリを省略できるメリットが大きい。

### 5.5 タグ削除

1. パターン#8 でこのタグに紐づく全関連エンティティを取得
2. 関連エンティティを `BatchWriteItem` (Delete) で一括削除
3. タグマスタを `DeleteItem` で削除

### 5.6 解析リクエスト

1. レート制限チェック（パターン#10）
2. SQSキューのメッセージ数チェック（`GetQueueAttributes`）
3. 解析エンティティを `PutItem` で作成（status=`waiting`）
4. SQS FIFOキューにメッセージ送信

解析Lambda（コンシューマ）が完了時に `status` と `response` を `UpdateItem` で更新。

---

## 6. 環境変数（Lambda）

旧システムではDynamoDB上にシステム設定エンティティを持っていたが、上限値は変更頻度が低いため環境変数で管理する。

| 環境変数名 | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `KIFU_MAX` | integer | `2000` | 1ユーザーあたりの棋譜上限数 |
| `TAG_MAX` | integer | `50` | 1ユーザーあたりのタグ上限数 |
| `MAIN_TABLE_NAME` | string | - | DynamoDBテーブル名 |
| `SQS_QUEUE_URL` | string | - | 解析用SQS FIFOキューURL |

---

## 7. 容量見積もり

### アイテムサイズの概算

| エンティティ | 概算サイズ | 備考 |
|-------------|-----------|------|
| 棋譜 | 1〜10 KB | KIF本文のサイズに依存。200手の棋譜で約5KB |
| タグ | 〜200 B | 属性が少ない |
| 棋譜-タグ関連 | 〜200 B | 属性が少ない |
| 解析 | 〜1 KB | レスポンスJSON含む。TTLで自動削除 |

### ユーザーあたりの上限

- 棋譜: 最大 2,000 件 → 最大 20 MB
- タグ: 最大 50 件 → 最大 10 KB
- 関連: 最大 2,000 × 50 = 100,000 件（理論上限）→ 最大 20 MB
- 合計: 最大約 40 MB / ユーザー

> LSI のパーティションサイズ上限は 10 GB。1パーティション（= 1ユーザー）あたり40MB程度であれば問題なし。

---

## 8. 旧システムからの変更点

旧システム（WAMBDA + SSR）のDynamoDB設計との差分を以下にまとめる。

### 維持した設計

- テーブル名 `table-sgp-pro-main`、PK (`pk`) / SK (`sk`) 構造
- 棋譜のキーパターン: `kifu#uname#{username}` / `kid#{kid}`
- タグのキーパターン: `tag#uname#{username}` / `tid#{tid}`
- 棋譜-タグ関連のキーパターン: `tag#kid#{kid}` / `tid#{tid}`
- 解析のキーパターン: `analysis` / `aid#{aid}`
- CommonLSI、CommonGSI、SwapIndex の基本構造
- slugベースの階層構造（フォルダエクスプローラー）
- タグ名の非正規化（関連エンティティに `tname` を保持）
- kid は12文字、tid / aid は8文字、share_code は36文字のランダム英数字

### 変更した設計

| 項目 | 旧 | 新 | 理由 |
|------|-----|-----|------|
| LSI: LatestAccessIndex | あり（`latest_access` をSKとするLSI） | **廃止** | 新システムでは最終アクセス日時を追跡しない |
| LSI射影 | INCLUDE（`clsi_sk`, `public`, `cgsi_pk` のみ） | **ALL** | 棋譜一覧で全属性が必要。Fetchコスト回避のため |
| SwapIndex射影 | ALL | **KEYS_ONLY** | タグ削除時は `pk`/`sk` のみで十分 |
| `public` 属性 | あり（公開フラグ） | **廃止** | `share` フラグに統一 |
| `title` 属性 | あり（棋譜タイトル） | **廃止** | `slug` がファイルパス兼識別名を兼ねる |
| `latest_access` 属性 | あり（最終アクセス日時） | **廃止** | 新システムでは不使用 |
| 共有エンティティ | `share#{code}` / `data` で独立エンティティを作成 | **廃止** | 棋譜の `cgsi_pk=scode#{code}` で直接検索に変更。データのコピーが不要 |
| システム設定 | `system` / `none` エンティティ（`kifu_max`, `tag_max`） | **Lambda環境変数** | 変更頻度が低いため。DBアクセス1回削減 |
| タグの `cgsi_pk` | `tag#uname#{user}#tid#{tid}` | **不使用** | 旧ではGSIでタグを一意に引く用途があったが、新では不要 |
| `first_or_second` の値 | `先手` / `後手`（日本語） | `first` / `second`（英語） | REST APIのJSON設計に合わせ英語enum化 |
| `result` の値 | `勝利` / `敗北` 等（日本語） | `win` / `lose` 等（英語） | 同上 |

### 移行時の注意

- **テーブル再作成が必要**: LSIの構成が変更されている（LatestAccessIndex廃止、射影変更）ため、既存テーブルのインデックス変更では対応できない。新テーブルを作成しデータを移行する
- **enum値の変換**: `first_or_second` と `result` の値が日本語→英語に変更されているため、データ移行時に変換が必要
- **共有エンティティの移行**: 旧の `share#{code}` エンティティは不要。棋譜エンティティの `cgsi_pk` に `scode#{share_code}` を設定するだけでよい

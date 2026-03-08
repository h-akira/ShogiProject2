# DynamoDB vs Aurora DSQL 比較と提案

## 1. 現行設計（DynamoDB）の課題

現在の `01_database_design.md` で定義されたシングルテーブルデザインには以下の課題がある。

### 1.1 1 ページで多数のクエリが発生する

**例: 棋譜詳細ページ（`GET /kifus/{kid}`）**

1. 棋譜本体を取得（ベーステーブル GetItem）
2. 棋譜のタグ一覧を取得（ベーステーブル Query: `pk = KIFUTAG#<kid>`）

→ 最低 2 リクエスト

**例: タグ詳細ページ（`GET /tags/{tid}`）**

1. タグ本体を取得（ベーステーブル GetItem）
2. タグに紐づく棋譜 ID を逆引き（SwapIndex Query: `sk = TAG#<tid>`）
3. 棋譜の詳細を取得（BatchGetItem: 棋譜 ID × N 件）

→ 最低 3 リクエスト（棋譜数が多い場合は BatchGetItem の分割も発生）

**例: マイページ（`GET /kifus/recent`）**

1. 最近の棋譜一覧を取得（LatestUpdateIndex Query + FilterExpression）
2. 棋譜総数を取得（ベーステーブル Query: `Select=COUNT`）

→ 最低 2 リクエスト。さらに FilterExpression はフィルタ前にデータを読み取るため、Tag アイテムが多いと無駄な読み取りが発生する。

### 1.2 逆引きの困難さ

- KifuTag の逆引き（タグ → 棋譜）は SwapIndex（KEYS_ONLY）を使うため、棋譜の実データは別途 BatchGetItem が必要
- ALL プロジェクションにするとストレージとスループットが増加する

### 1.3 データ整合性の管理が複雑

- タグ名変更時: Tag アイテム + 全関連 KifuTag アイテムの `name` 属性を更新（トランザクション使用の場合も 25 アイテム制限）
- 棋譜削除時: Kifu アイテム + 全関連 KifuTag アイテムの削除
- アカウント削除時: 全 Kifu + 全 Tag + 全 KifuTag の削除（大量の BatchWriteItem）

これらは DynamoDB にトランザクション保証がない操作であり、部分的な失敗時の整合性回復が難しい。

---

## 2. DynamoDB vs Aurora DSQL 比較

| 観点 | DynamoDB | Aurora DSQL |
|------|----------|-------------|
| **データモデル** | Key-Value / ドキュメント | リレーショナル（PostgreSQL 互換） |
| **クエリの柔軟性** | 事前定義した GSI に限定 | SQL（JOIN、サブクエリ、集約関数） |
| **多対多関連** | 中間テーブル + GSI 逆引き | JOIN で 1 クエリ |
| **参照整合性** | アプリケーション層 | アプリケーション層（CASCADE 未推奨） |
| **トランザクション** | 25 アイテム / 4 MB 制限 | 3,000 行 / トランザクション |
| **サーバーレス** | ○（完全） | ○（完全） |
| **VPC 不要** | ○ | ○（IAM 認証＋パブリックエンドポイント） |
| **IAM 認証** | 標準 | ○（パスワードレス） |
| **コールドスタート** | 影響なし | DB 接続確立のオーバーヘッドあり |
| **料金モデル** | 読み書きリクエスト課金 | DPU 課金 |
| **無料枠** | 25 GB + 2500万 読み + 500万 書き | 100,000 DPU + 1 GB |
| **東京リージョン** | ○ | ○ |
| **CloudFormation** | ○ | ○ |
| **SAM** | ○ | ○ |
| **成熟度** | 非常に高い | GA 直後（2025年5月〜） |

---

## 3. 本プロジェクトにおける Aurora DSQL の利点

### 3.1 クエリの大幅な簡素化

**棋譜詳細 + タグ取得が 1 クエリに**:

```sql
SELECT k.*, array_agg(t.name) AS tag_names
FROM kifus k
LEFT JOIN kifu_tags kt ON k.kid = kt.kid
LEFT JOIN tags t ON kt.tid = t.tid
WHERE k.username = $1 AND k.kid = $2
GROUP BY k.kid;
```

**タグ → 棋譜の逆引きも 1 クエリに**:

```sql
SELECT k.kid, k.slug, k.side, k.result, k.updated_at
FROM kifus k
JOIN kifu_tags kt ON k.kid = kt.kid
WHERE kt.tid = $1 AND k.username = $2
ORDER BY k.updated_at DESC;
```

**エクスプローラー（パス検索）も 1 クエリに**:

```sql
SELECT slug FROM kifus
WHERE username = $1 AND slug LIKE $2 || '%'
ORDER BY slug;
```

### 3.2 GSI 設計の不要化

DynamoDB では 4 つの GSI（CommonGSI, LatestUpdateIndex, ShareCodeIndex, SwapIndex）を設計・管理する必要があった。Aurora DSQL では通常のインデックスで対応可能。

### 3.3 データ整合性の向上

- タグ名変更: `UPDATE tags SET name = $1 WHERE tid = $2` の 1 文で完了。KifuTag に非正規化コピーを持つ必要がない
- 棋譜削除: `DELETE FROM kifu_tags WHERE kid = $1; DELETE FROM kifus WHERE kid = $1;` を 1 トランザクションで実行可能
- アカウント削除: `DELETE FROM kifu_tags WHERE kid IN (SELECT kid FROM kifus WHERE username = $1); DELETE FROM kifus WHERE username = $1; DELETE FROM tags WHERE username = $1;` を 1 トランザクションで実行可能（3,000 行制限に注意）

### 3.4 カウントクエリの効率化

```sql
SELECT COUNT(*) FROM kifus WHERE username = $1;
```

DynamoDB のように別途 COUNT クエリを発行する必要がない（メインクエリの window function 等で同時取得可能）。

---

## 4. 懸念事項と対策

### 4.1 コールドスタートへの影響

| 懸念 | 対策 |
|------|------|
| DB 接続確立のレイテンシ | コネクション再利用（Lambda 実行コンテキスト） |
| IAM トークン生成のオーバーヘッド | aurora-dsql-python-connector が自動管理 |
| VPC 配置は不要 | DynamoDB と同様にパブリックエンドポイント |

### 4.2 OCC（楽観的同時実行制御）

Aurora DSQL はロックを取得せず、コミット時に競合を検出する。個人利用の棋譜管理アプリでは同一リソースへの同時書き込みが稀であるため、実質的な問題にはならない。念のため、アプリケーション層でリトライロジックを実装する。

### 4.3 トランザクション行数制限（3,000 行）

アカウント削除時に棋譜数 + タグ数 + KifuTag 数が 3,000 行を超える場合は、バッチ分割が必要。ただし、個人利用の棋譜管理アプリでこの上限に達する可能性は低い（数千件の棋譜を持つユーザーは稀）。

### 4.4 成熟度

Aurora DSQL は 2025年5月 GA で比較的新しいサービス。一方で：
- PostgreSQL 16 互換のためエコシステムは成熟
- 公式 Python コネクタ、SQLAlchemy ダイアレクト、Django アダプタが揃っている
- CloudFormation / SAM での IaC 対応済み

### 4.5 外部キー制約

Aurora DSQL は外部キーの定義自体は可能だが、CASCADE 操作は推奨されない。本プロジェクトでは DynamoDB 設計時点からアプリケーション層で参照整合性を管理する設計だったため、影響なし。

---

## 5. RDB スキーマ設計案

### テーブル定義

```sql
-- 棋譜テーブル
CREATE TABLE kifus (
  kid         VARCHAR(12) PRIMARY KEY,
  username    VARCHAR(255) NOT NULL,
  slug        VARCHAR(1024) NOT NULL,
  side        VARCHAR(20) NOT NULL DEFAULT 'none',
  result      VARCHAR(20) NOT NULL DEFAULT 'none',
  memo        TEXT NOT NULL DEFAULT '',
  kif         TEXT NOT NULL DEFAULT '',
  shared      BOOLEAN NOT NULL DEFAULT FALSE,
  share_code  VARCHAR(36),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- タグテーブル
CREATE TABLE tags (
  tid         VARCHAR(12) PRIMARY KEY,
  username    VARCHAR(255) NOT NULL,
  name        VARCHAR(127) NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 棋譜-タグ関連テーブル
CREATE TABLE kifu_tags (
  kid         VARCHAR(12) NOT NULL,
  tid         VARCHAR(12) NOT NULL,
  PRIMARY KEY (kid, tid)
);
```

### インデックス

```sql
-- 棋譜: ユーザー別の更新日時降順
CREATE INDEX ASYNC idx_kifus_user_updated
  ON kifus (username, updated_at DESC);

-- 棋譜: ユーザー別の slug（一意性チェック + エクスプローラー）
CREATE UNIQUE INDEX ASYNC idx_kifus_user_slug
  ON kifus (username, slug);

-- 棋譜: 共有コード検索
CREATE UNIQUE INDEX ASYNC idx_kifus_share_code
  ON kifus (share_code) WHERE share_code IS NOT NULL;

-- タグ: ユーザー別のタグ名（一意性チェック）
CREATE UNIQUE INDEX ASYNC idx_tags_user_name
  ON tags (username, name);

-- 棋譜-タグ関連: タグ側からの逆引き
CREATE INDEX ASYNC idx_kifu_tags_tid
  ON kifu_tags (tid);
```

### DynamoDB 設計との対応

| DynamoDB (GSI/パターン) | Aurora DSQL (インデックス/クエリ) |
|------------------------|-------------------------------|
| LatestUpdateIndex | `idx_kifus_user_updated` + `ORDER BY updated_at DESC` |
| CommonGSI (SLUG#) | `idx_kifus_user_slug` + `WHERE slug = ?` or `LIKE ?%` |
| ShareCodeIndex | `idx_kifus_share_code` + `WHERE share_code = ?` |
| CommonGSI (TAGNAME#) | `idx_tags_user_name` + `WHERE name = ?` |
| SwapIndex | `idx_kifu_tags_tid` + JOIN |
| ベーステーブル (pk + sk) | PRIMARY KEY + JOIN |

---

## 6. アクセスパターンの対応表

| # | パターン | DynamoDB | Aurora DSQL |
|---|---------|----------|-------------|
| 1 | 最近の棋譜一覧 | LatestUpdateIndex Query + FilterExpression + 別途 COUNT | `SELECT * FROM kifus WHERE username = $1 ORDER BY updated_at DESC LIMIT 10` + `COUNT(*) OVER()` |
| 2 | 棋譜詳細取得 | GetItem + KifuTag Query (2 リクエスト) | 1 クエリ（JOIN） |
| 3 | slug 一意性チェック | CommonGSI Query (Select=COUNT) | `INSERT ... ON CONFLICT` or UNIQUE 制約 |
| 4 | エクスプローラー | CommonGSI Query (begins_with) | `WHERE slug LIKE $1 || '%'` |
| 5 | 共有棋譜取得 | ShareCodeIndex Query | `WHERE share_code = $1` |
| 6 | タグ一覧 | ベーステーブル Query (begins_with TAG#) | `SELECT * FROM tags WHERE username = $1` |
| 7 | 棋譜のタグ取得 | ベーステーブル Query (pk = KIFUTAG#) | JOIN kifu_tags + tags |
| 8 | タグの棋譜逆引き | SwapIndex + BatchGetItem (2〜3 リクエスト) | 1 クエリ（JOIN） |
| 9 | タグ名一意性 | CommonGSI Query | UNIQUE 制約 |
| 10 | 棋譜数カウント | ベーステーブル Query (Select=COUNT) | `COUNT(*)` or window function |
| 11 | タグ数カウント | ベーステーブル Query (Select=COUNT) | `COUNT(*)` |
| 12 | 棋譜数 (total_count) | 別途 COUNT クエリ | `COUNT(*) OVER()` (メインクエリ内) |

---

## 7. 提案

### 結論: Aurora DSQL への変更を推奨する

#### 推奨理由

1. **クエリの簡素化**: 多数のリクエストが JOIN で 1 クエリに統合される。特にタグ逆引き（3→1 リクエスト）、棋譜詳細+タグ（2→1 リクエスト）の改善が大きい
2. **GSI 設計の排除**: 4 つの GSI を設計・管理する複雑性がなくなる。通常の RDB インデックスで対応可能
3. **データ整合性**: タグ名の非正規化コピー（KifuTag.name）が不要になり、更新時の整合性管理が劇的に簡素化される
4. **サーバーレス互換**: DynamoDB と同様にサーバーレスで、VPC 不要、IAM 認証、従量課金
5. **Python エコシステムの充実**: 公式コネクタ + SQLAlchemy + Django アダプタが揃っている
6. **低コスト**: 無料枠あり。個人利用の棋譜管理アプリでは十分

#### 注意すべき点

1. **リトライロジックの実装**: OCC による楽観的ロックのため、書き込み競合時のリトライが必要（個人利用では稀）
2. **3,000 行/トランザクション制限**: アカウント削除時に大量データがある場合はバッチ分割が必要
3. **サービスの成熟度**: GA から約 9 ヶ月。コミュニティの知見は DynamoDB ほど蓄積されていない
4. **コールドスタートの DB 接続オーバーヘッド**: DynamoDB よりやや遅い可能性がある（コネクション再利用で緩和）

#### アーキテクチャへの影響

- `technical_policies.md` の「各マイクロサービスはリソースを共有しない」原則に適合（Aurora DSQL クラスタを backend-main 内で管理）
- SAM テンプレートで `AWS::DSQL::Cluster` を定義可能
- Lambda の実行ロールに `dsql:DbConnectAdmin` を追加
- VPC 設定の変更は不要

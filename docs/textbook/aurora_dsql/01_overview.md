# Aurora DSQL 調査レポート

## 調査日

2026-02-28

## 1. Aurora DSQL とは

Amazon Aurora DSQL は、AWS が提供するサーバーレス・分散型リレーショナルデータベースサービスである。2024年12月の re:Invent でプレビュー発表され、**2025年5月27日に GA（一般提供）** となった。

### 主な特徴

| 項目 | 内容 |
|------|------|
| 種別 | サーバーレス分散 SQL データベース |
| PostgreSQL 互換 | バージョン 16 ベース |
| 可用性 | シングルリージョン 99.99% / マルチリージョン 99.999% |
| アーキテクチャ | Active-Active、マルチ AZ |
| スケーリング | 自動（コンピュート・I/O・ストレージ） |
| 運用 | フルマネージド（パッチ、VACUUM、チューニング不要） |
| 同時実行制御 | 楽観的同時実行制御（OCC） |
| トランザクション分離レベル | Repeatable Read 固定 |

### 利用可能リージョン（2026年2月時点）

- US East (N. Virginia, Ohio)、US West (Oregon)
- Asia Pacific (Tokyo, Osaka, Seoul, Sydney, Melbourne)
- Canada (Central, Calgary)
- Europe (Frankfurt, Ireland, London, Paris)

**東京リージョン（ap-northeast-1）で利用可能。**

---

## 2. 料金モデル

Aurora DSQL はサーバーレスモデルで、使った分だけ課金される。

| 課金項目 | 単位 | 料金 |
|---------|------|------|
| DPU（Distributed Processing Unit） | 100万 DPU あたり | $8 |
| ストレージ | GB-month | 別途 |

### 無料枠

- 毎月 100,000 DPU + 1 GB ストレージが無料

### 特徴

- リクエスト単位の課金ではなく、DPU（コンピュートリソース＋I/O）で課金
- インスタンスの事前プロビジョニング不要
- アイドル時はストレージ料金のみ

### 本プロジェクトにおけるコスト見込み

個人利用の棋譜管理アプリでは、無料枠内で十分に収まる可能性が高い。DynamoDB のオンデマンド課金と同様に、低トラフィック時のコストは非常に低い。

---

## 3. PostgreSQL 互換性

### サポートされる機能

- **Wire Protocol**: PostgreSQL v3 プロトコル（psql, psycopg, pgjdbc 等で接続可能）
- **SQL 構文**: DDL（CREATE TABLE/INDEX 等）、DML（SELECT/INSERT/UPDATE/DELETE）
- **データ型**: 標準 PostgreSQL データ型の大部分
- **JOIN**: 内部結合、外部結合、サブクエリ等
- **インデックス**: B-tree インデックス（`CREATE INDEX ASYNC` で非ブロッキング作成）
- **ビュー**: サポート（GA で追加）
- **シーケンス/IDENTITY カラム**: サポート
- **SQL 関数**: SQL ベースの関数

### サポートされない/制限がある機能

| 機能 | 状況 | 代替手段 |
|------|------|---------|
| 外部キー制約の CASCADE | パフォーマンス問題の可能性 | アプリケーション層で参照整合性を実装 |
| トリガー | 未サポート | アプリケーション層のイベント駆動ロジック |
| PL/pgSQL（ストアドプロシージャ） | 未サポート | SQL 関数 or Lambda でロジック実装 |
| 一時テーブル | 未サポート | CTE（WITH 句）やサブクエリで代替 |
| TRUNCATE | 未サポート | `DELETE FROM table_name` で代替 |
| 複数データベース | 1 クラスタ = 1 DB（`postgres`） | スキーマで論理分離 or 別クラスタ |
| 悲観的ロック | OCC のためなし | リトライロジックの実装が必要 |
| コレーション | `C` のみ | — |

### トランザクション制約

- DDL と DML は別トランザクション
- 1 トランザクション内の DDL は 1 文のみ
- **1 トランザクションで変更可能な行数は最大 3,000 行**
- 接続タイムアウト: 1 時間

---

## 4. Lambda からの接続

### IAM 認証

Aurora DSQL はパスワードレスの IAM 認証を採用する。Lambda の実行ロールに適切な IAM ポリシーを付与することで、パスワード管理なしに接続可能。

### 接続フロー

```
Lambda 起動
  → IAM トークン生成（aurora-dsql-python-connector が自動化）
  → PostgreSQL 接続（psycopg / psycopg2 / asyncpg）
  → SQL 実行
```

### VPC 不要

Aurora DSQL はパブリックエンドポイントを持ち、IAM 認証で保護される。Lambda を VPC 内に配置する必要がない（PrivateLink も利用可能）。これは DynamoDB と同様のメリットであり、Lambda のコールドスタートに VPC のオーバーヘッドが加わらない。

---

## 5. CloudFormation / SAM / CDK 対応

| ツール | 状況 |
|--------|------|
| CloudFormation | サポート済み（シングルリージョンクラスタ） |
| SAM | CloudFormation 拡張のため利用可能 |
| CDK | L1 コンストラクトが利用可能（L2 は開発中） |
| AWS Backup | サポート済み |
| PrivateLink | サポート済み |
| CloudTrail | サポート済み |
| KMS CMK | サポート済み |

SAM テンプレートから `AWS::DSQL::Cluster` リソースを定義してクラスタを作成可能。

---

## 6. 参考リンク

- [What is Amazon Aurora DSQL?](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)
- [Aurora DSQL and PostgreSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with.html)
- [SQL feature compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [Migrating from PostgreSQL to Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html)
- [Aurora DSQL pricing](https://aws.amazon.com/rds/aurora/dsql/pricing/)
- [Amazon Aurora DSQL is now generally available](https://aws.amazon.com/blogs/aws/amazon-aurora-dsql-is-now-generally-available/)

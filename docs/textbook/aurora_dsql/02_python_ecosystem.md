# Aurora DSQL Python エコシステム

## 1. 公式 Python コネクタ

### aurora-dsql-python-connector

AWS が公式提供する Python コネクタ。IAM 認証トークンの自動生成を行う透過的な認証レイヤーである。

- **リポジトリ**: [awslabs/aurora-dsql-python-connector](https://github.com/awslabs/aurora-dsql-python-connector)
- **初回リリース**: 2025年11月（Python, Node.js, JDBC コネクタとして発表）
- **最新リリース**: 2026年2月（Go, Python, Node.js コネクタの更新版）
- **インストール**: `pip install aurora-dsql-python-connector`

### サポートするドライバ

| ドライバ | 種別 | 用途 |
|---------|------|------|
| psycopg (v3) | 同期/非同期 | 推奨。最新の PostgreSQL ドライバ |
| psycopg2 | 同期 | レガシー互換。Lambda レイヤーでの利用実績多い |
| asyncpg | 非同期 | 高パフォーマンスな非同期処理向け |

ドライバは別途インストールが必要：

```bash
# psycopg v3 の場合
pip install "psycopg[binary,pool]"

# psycopg2 の場合
pip install psycopg2-binary

# asyncpg の場合
pip install asyncpg
```

### 接続コード例（psycopg）

```python
from aurora_dsql_python_connector import DsqlConnector

connector = DsqlConnector()

# IAM 認証トークンを自動生成して接続
conn = connector.connect(
    host="<cluster-endpoint>",
    dbname="postgres",
    driver="psycopg"
)

with conn.cursor() as cur:
    cur.execute("SELECT * FROM kifus WHERE username = %s", (username,))
    rows = cur.fetchall()

conn.close()
```

### 接続コード例（psycopg2）

```python
from aurora_dsql_python_connector import DsqlConnector

connector = DsqlConnector()

conn = connector.connect(
    host="<cluster-endpoint>",
    dbname="postgres",
    driver="psycopg2"
)

with conn.cursor() as cur:
    cur.execute("SELECT * FROM kifus WHERE username = %s", (username,))
    rows = cur.fetchall()

conn.close()
```

---

## 2. SQLAlchemy サポート

### aurora-dsql-sqlalchemy

Aurora DSQL 用の SQLAlchemy ダイアレクト。

- **リポジトリ**: [awslabs/aurora-dsql-sqlalchemy](https://github.com/awslabs/aurora-dsql-sqlalchemy)
- **PyPI**: [aurora-dsql-sqlalchemy](https://pypi.org/project/aurora-dsql-sqlalchemy/)
- **最新バージョン**: 1.1.0（2026年1月19日）
- **対応 Python**: 3.10〜3.13
- **インストール**: `pip install aurora-dsql-sqlalchemy`

---

## 3. ORM / フレームワーク対応

| フレームワーク | 状況 |
|--------------|------|
| SQLAlchemy | 公式ダイアレクトあり（aurora-dsql-sqlalchemy） |
| Django | 公式アダプタあり（aurora-dsql-django） |
| Tortoise ORM | 公式サポート（2026年2月発表） |

---

## 4. Lambda での利用ベストプラクティス

### コネクション管理

Lambda のハンドラ外でコネクションを初期化し、再利用する：

```python
import os
from aurora_dsql_python_connector import DsqlConnector

# Lambda 実行コンテキストで初期化（コールドスタート時のみ）
connector = DsqlConnector()
CLUSTER_ENDPOINT = os.environ["DSQL_CLUSTER_ENDPOINT"]

def get_connection():
    return connector.connect(
        host=CLUSTER_ENDPOINT,
        dbname="postgres",
        driver="psycopg"
    )

# Connection reuse
_conn = None

def get_or_create_connection():
    global _conn
    if _conn is None or _conn.closed:
        _conn = get_connection()
    return _conn

def handler(event, context):
    conn = get_or_create_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT ...")
        result = cur.fetchall()
    return {"statusCode": 200, "body": result}
```

### IAM ポリシー

Lambda 実行ロールに必要な IAM ポリシー：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "dsql:DbConnectAdmin",
      "Resource": "arn:aws:dsql:<region>:<account-id>:cluster/<cluster-id>"
    }
  ]
}
```

### SAM テンプレート例

```yaml
Resources:
  DsqlCluster:
    Type: AWS::DSQL::Cluster
    Properties:
      DeletionProtectionEnabled: true
      Tags:
        - Key: Project
          Value: sgp

  MainFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.handler
      Runtime: python3.12
      Environment:
        Variables:
          DSQL_CLUSTER_ENDPOINT: !GetAtt DsqlCluster.Endpoint
      Policies:
        - Statement:
            - Effect: Allow
              Action: dsql:DbConnectAdmin
              Resource: !Sub "arn:aws:dsql:${AWS::Region}:${AWS::AccountId}:cluster/${DsqlCluster}"
```

---

## 5. 参考リンク

- [Aurora DSQL Connector for Python](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_program-with-dsql-connector-for-python.html)
- [Aurora DSQL launches new Go, Python, and Node.js connectors (2026/02)](https://aws.amazon.com/about-aws/whats-new/2026/02/aurora-dsql-launches-go-python-nodejs-connectors/)
- [Aurora DSQL launches new Python, Node.js, and JDBC Connectors (2025/11)](https://aws.amazon.com/about-aws/whats-new/2025/11/aurora-dsql-python-node-js-jdbc-connectors-iam/)
- [Aurora DSQL Python Connector Lambda benchmark](https://dev.classmethod.jp/en/articles/aurora-dsql-python-connector-lambda-benchmark/)

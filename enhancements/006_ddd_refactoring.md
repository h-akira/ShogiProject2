# ENH-006: Backend/main DDD リファクタリング

## ステータス

完了（検証済み）

## 起票日

2026-04-18

## 種別

改善

## 概要

Backend/main を classic 3-layer architecture（routes → services → repositories）から DDD 準拠の 4-layer architecture（presentation → application → domain → infrastructure）にリファクタリングする。DDD 学習の教材も兼ねる。

## 背景・動機

- DDD の概念（集約、Value Object、リポジトリパターン、依存逆転等）を実践的に学ぶ教材として、既存の本番コードを題材にする
- 既存コードはサービス層にドメインロジック・バリデーション・DB アクセスが混在しており、テスタビリティとモジュール分離に課題がある
- DDD 準拠にすることで、ドメインロジックの単体テストが IO なしで高速に実行でき、テストピラミッドの健全化が期待できる

## 要件

- 既存 14 エンドポイントの機能を一切損なわない
- DDD 4 層（presentation / application / domain / infrastructure）に分離する
- ドメイン層は純粋 Python（外部依存ゼロ）とする
- Value Object でバリデーションを表現し、ドメイン例外は HTTP ステータスを持たない
- Repository はドメイン層に ABC（インターフェース）、インフラ層に実装を配置する（DIP）
- DDD 設計書を docs/ に整備する（旧ドキュメントを置換）
- DDD テストピラミッドに沿ったテスト構造を整備する

## 影響範囲

- `Backend/main/src/` — 全面的に再構成（旧 routes/, services/, repositories/ を削除し、新 4 層を構築）
- `Backend/main/docs/` — 旧設計書 01〜08 + technical_policies.md を削除し、DDD 設計書 01〜05 を新規作成
- `Backend/main/tests/` — 旧 local/ を削除し、domain/ + application/ を新規作成
- `Backend/main/README.md` — ディレクトリ構成・設計ドキュメント一覧を更新
- `Backend/main/tests/dsql/README.md` — 参照リンクを修正

## 実現案

### 案1: 段階的移行（採用）

Phase 0〜5 の段階的アプローチで、各フェーズが独立して検証可能:

1. **Phase 0**: DDD 設計書の作成（コード変更なし）
2. **Phase 1**: ドメイン層の構築（新規追加のみ、既存コードに触れない）
3. **Phase 2**: アプリケーション層の構築（新規追加のみ）
4. **Phase 3**: インフラ層の構築（既存リポジトリのリファクタ）
5. **Phase 4**: プレゼンテーション層の構築（既存ルートのリファクタ）
6. **Phase 5**: クリーンアップと最終検証

## 対応

`ddd` ブランチで全 Phase（0〜5）を実施済み。コミット: `95e42cc`

### DDD 設計書（docs/）

| ファイル | 内容 |
|---------|------|
| `docs/01_domain_model.md` | ドメインモデル概要・境界づけられたコンテキスト・ユビキタス言語 |
| `docs/02_aggregates.md` | 集約定義（Kifu / Tag）・Value Object 8 種・不変条件 |
| `docs/03_use_cases.md` | 15 ユースケース・Command/Response DTO |
| `docs/04_architecture.md` | 4 層アーキテクチャ・依存ルール・DI 設計 |
| `docs/05_testing_strategy.md` | DDD テストピラミッド・テスト構成 |

### 設計判断

- **単一 Bounded Context**「KifuManagement」（テーブル 3 つで密結合、複数 BC は過剰）
- **2 集約**: Kifu（集約ルート、tag_ids を保持）、Tag（独立ライフサイクル）
- **8 Value Object**: KifuId, TagId, Slug, Side, GameResult, ShareCode, TagName, Username
- **DI コンテナ**: フレームワーク不使用、関数ベースの lazy singleton パターン

### 変更ファイル

**新規作成:**
- `src/domain/` — value_objects.py, kifu.py, tag.py, repositories.py, exceptions.py, services.py, events.py
- `src/application/` — dto.py, kifu_use_cases.py, tag_use_cases.py, user_use_cases.py
- `src/infrastructure/` — db.py, kifu_repository.py, tag_repository.py, cognito_client.py
- `src/presentation/` — container.py, exception_handlers.py, routes/（kifus, tags, users, shared）
- `tests/domain/` — test_value_objects.py, test_kifu.py, test_tag.py, test_services.py
- `tests/application/` — helpers/in_memory_repositories.py, test_kifu_use_cases.py, test_tag_use_cases.py, test_user_use_cases.py

**削除:**
- `src/services/`, `src/routes/`, `src/repositories/`, `src/common/exceptions.py`
- `tests/local/`
- `docs/01〜08`, `docs/technical_policies.md`

**更新:**
- `src/app.py`, `README.md`, `tests/README.md`, `tests/dsql/README.md`, `tests/pytest.ini`

### テスト結果

- ドメインテスト: 62 件パス（純粋 Python、IO なし、0.10 秒）
- アプリケーションテスト: 36 件パス（InMemoryRepository 使用）
- DSQL テスト: 変更影響なし（raw SQL のみ、アプリケーションコード非依存）
- E2E テスト（integration-tests/）: パス
- デプロイ後の動作確認: 完了

### デプロイ後に発見された不具合

レガシーデータの TagId が 8 文字だったが、TagId VO が 12 文字固定でバリデーションしていたため、タグ関連の全 API（recent、explorer、kifu detail 等）が `DomainValidationError` で 400 エラーを返していた。DSQL 上のデータは無事。TagId のバリデーションを 8-12 文字に緩和して修正（コミット: `084e567`）。

## 関連

- `DDD/` — DDD 学習資料（本リファクタリングの前提知識）
- `docs/openapi_main.yaml` — API 仕様（変更なし）
- `docs/units_contracts.md` — ユニット間契約（変更なし）

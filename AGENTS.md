# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

将棋の棋譜管理Webアプリケーション。AWS上にサーバーレスアーキテクチャで構築。

## リポジトリ構成

Git サブモジュールで管理されたマルチリポジトリ構成。ユニット別のディレクトリ・リポジトリ名の一覧は `docs/units_contracts.md` の「ユニット別定義」を参照すること（情報の重複による不整合を防ぐため、ここには転記しない）。

`docs/` はサブモジュールではなく、本リポジトリ直下で管理する共有設計ドキュメント群。各ユニット固有の詳細設計はサブモジュール内の `docs/` に配置する（例: `Backend/main/docs/`）。

## 設計ドキュメント (`docs/`)

ドキュメントは依存関係を持ち、段階的に作成されている。詳細は `docs/flow.md` を参照。
**コードの実装・修正時は、関連するドキュメントを事前に読んで設計意図を理解すること。**

| ファイル | 責務 |
|---------|------|
| `flow.md` | ドキュメント作成フローと依存関係。全体像の把握に最適 |
| `user_stories.md` | ユーザー視点の要求定義（US-X.X）。機能の受け入れ条件を網羅 |
| `technical_policies.md` | 技術方針。レイヤー構成・技術選定・Lambdalith 等の設計原則 |
| `units_definition.md` | 開発ユニット分割と各ユニットの責務。ユーザーストーリーとの対応表 |
| `units_contracts.md` | ユニット間契約。命名規約・CloudFormation エクスポート・通信仕様 |
| `_api_list.md` | API エンドポイント一覧（一時ファイル。将来の仕様変更時には更新しない） |
| `openapi_*.yaml` | OpenAPI 定義。マイクロサービスごとに作成 |

## 仕様変更通知 (`docs/fix/`)

いずれかのユニット（Frontend, Backend, Infra 等）の都合で `openapi_*.yaml` や `units_contracts.md` などの共有ドキュメントに修正が入った場合、**他ユニットへの影響を伝えるために `docs/fix/XXX_任意の名前.md` を作成する**。

- `XXX` は 3 桁の連番（`001`, `002`, ...）。既存ファイルの最大番号 + 1 を採番する
- 内容: 変更概要、対象ファイル・エンドポイント、影響を受けるユニット、各ユニットで必要な対応
- 変更を行ったタイミングで必ず作成すること

## アーキテクチャ

詳細は `docs/technical_policies.md` および `docs/units_contracts.md` を参照。

- フロントエンド: Vue 3 SPA（`shogi-board/` ライブラリ + `shogi-main/` アプリ）
- バックエンド: Python, API Gateway + Lambda (SAM), DynamoDB
- インフラ: CloudFront, S3, Cognito (CDK)
- CI/CD: CodeBuild (CloudFormation)

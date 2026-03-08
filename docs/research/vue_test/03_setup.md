# セットアップ手順

各パッケージに Vitest を導入し、テストを実行できる環境を構築する手順を示す。

---

## 1. shogi-board のセットアップ

`shogi-board` はゲームロジック（純粋関数）が主なテスト対象であり、DOM 環境は必須ではない。最小構成で導入できる。

### 1.1 パッケージのインストール

```bash
cd Frontend/shogi-board
npm install -D vitest
```

| パッケージ | 用途 |
|-----------|------|
| `vitest` | テストランナー |

> コンポーネント（`ShogiBoard.vue` 等）のテストも行う場合は、追加で `@vue/test-utils` と `jsdom` が必要になる（Phase 2 以降で検討）。

### 1.2 Vitest の設定

`vite.config.ts` に `test` セクションを追加する。

```typescript
// Frontend/shogi-board/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import dts from 'vite-plugin-dts'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    dts({ tsconfigPath: './tsconfig.app.json' }),
  ],
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'ShogiBoard',
      fileName: 'shogi-board',
    },
    rollupOptions: {
      external: ['vue'],
      output: {
        globals: {
          vue: 'Vue',
        },
      },
    },
  },
  // ↓ 追加
  test: {
    // テストファイルのパターン
    include: ['src/**/*.test.ts'],
  },
})
```

### 1.3 npm スクリプトの追加

```json
// Frontend/shogi-board/package.json の scripts に追加
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

| スクリプト | 動作 |
|-----------|------|
| `npm test` | テストを 1 回実行して終了 |
| `npm run test:watch` | ファイル変更を監視して自動再実行（開発中に便利） |

### 1.4 テストファイルの配置

テストファイルはテスト対象のファイルと同じディレクトリに `*.test.ts` として配置する。

```
src/core/
├── game.ts
├── game.test.ts      ← テストファイル
├── sfen.ts
├── sfen.test.ts      ← テストファイル
├── kif.ts
├── kif.test.ts       ← テストファイル
├── moves.ts
├── moves.test.ts     ← テストファイル
├── rules.ts
├── rules.test.ts     ← テストファイル
├── types.ts
└── constants.ts
```

> **配置方針の補足:** テストファイルの配置には「`__tests__/` ディレクトリにまとめる」方式もあるが、本プロジェクトでは **コロケーション方式**（テスト対象ファイルの隣に配置）を採用する。対象ファイルとテストファイルの対応が明確で、ファイル間の移動が少なく済む。

### 1.5 動作確認

```bash
cd Frontend/shogi-board
npm test
```

テストファイルが存在すれば、Vitest がそれを検出して実行する。

---

## 2. shogi-main のセットアップ

`shogi-main` では Vue コンポーネントのテストと API モック（MSW）が必要になるため、インストールするパッケージが多い。

### 2.1 パッケージのインストール

```bash
cd Frontend/shogi-main
npm install -D vitest @vue/test-utils jsdom
```

| パッケージ | 用途 |
|-----------|------|
| `vitest` | テストランナー |
| `@vue/test-utils` | Vue コンポーネントのマウント・操作・検証 |
| `jsdom` | Node.js 上でブラウザ DOM をエミュレーション |

> `msw` と `@faker-js/faker` は既にインストール済み。

### 2.2 Vitest の設定

```typescript
// Frontend/shogi-main/vite.config.ts
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  // ↓ 追加
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
    setupFiles: ['./vitest.setup.ts'],
  },
})
```

| 設定項目 | 説明 |
|---------|------|
| `environment: 'jsdom'` | Vue コンポーネントのテストに必要な DOM 環境 |
| `include` | テストファイルのパターン |
| `setupFiles` | テスト実行前に読み込むセットアップファイル |

### 2.3 MSW のテスト用セットアップ

テスト環境用の MSW サーバーを作成する。既存のブラウザ用 (`src/mocks/browser.ts`) と同じハンドラーを使う。

#### サーバー定義

```typescript
// Frontend/shogi-main/src/mocks/server.ts（新規作成）
import { setupServer } from 'msw/node'
import { getUsersMock } from '@/api/generated/main/users/users.msw'
import { getKifusMock } from '@/api/generated/main/kifus/kifus.msw'
import { getSharedMock } from '@/api/generated/main/shared/shared.msw'
import { getTagsMock } from '@/api/generated/main/tags/tags.msw'
import { getAnalysisMock } from '@/api/generated/analysis/analysis/analysis.msw'

export const server = setupServer(
  ...getUsersMock(),
  ...getKifusMock(),
  ...getSharedMock(),
  ...getTagsMock(),
  ...getAnalysisMock(),
)
```

> `browser.ts` と `server.ts` の違いは `setupWorker`（ブラウザ）か `setupServer`（Node.js）かだけ。ハンドラーは完全に共通。

#### Vitest セットアップファイル

```typescript
// Frontend/shogi-main/vitest.setup.ts（新規作成）
import { beforeAll, afterEach, afterAll } from 'vitest'
import { server } from '@/mocks/server'

// テスト開始前: MSW サーバーを起動
beforeAll(() => server.listen())

// 各テスト後: ハンドラーをリセット（テスト間の干渉を防止）
afterEach(() => server.resetHandlers())

// 全テスト完了後: MSW サーバーを停止
afterAll(() => server.close())
```

| フック | タイミング | 目的 |
|--------|----------|------|
| `beforeAll` | 全テストの前に 1 回 | MSW サーバー起動 |
| `afterEach` | 各テストの後 | `server.use()` で追加したハンドラーをリセット |
| `afterAll` | 全テストの後に 1 回 | MSW サーバー停止、Node.js HTTP モジュール復元 |

### 2.4 npm スクリプトの追加

```json
// Frontend/shogi-main/package.json の scripts に追加
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

### 2.5 テストファイルの配置

```
src/
├── utils/
│   ├── explorer.ts
│   ├── explorer.test.ts      ← ユーティリティのテスト
│   ├── labels.ts
│   └── labels.test.ts        ← ユーティリティのテスト
├── pages/
│   ├── KifuListPage.vue
│   ├── KifuListPage.test.ts  ← ページコンポーネントのテスト
│   └── ...
├── components/
│   ├── AppHeader.vue
│   ├── AppHeader.test.ts     ← 共通コンポーネントのテスト
│   └── ...
└── mocks/
    ├── browser.ts             ← 既存（ブラウザ用）
    └── server.ts              ← 新規（テスト用）
```

### 2.6 TypeScript 設定の確認

`tsconfig.app.json` には既にテストファイルの除外設定がある:

```json
{
  "exclude": ["src/**/__tests__/*"]
}
```

コロケーション方式（`*.test.ts`）を使う場合、追加で除外設定が必要:

```json
{
  "exclude": ["src/**/__tests__/*", "src/**/*.test.ts"]
}
```

これにより、テストファイルがプロダクションビルドの型チェックから除外される。

テスト用の TypeScript 設定は Vitest が自動で処理するため、別途 `tsconfig.test.json` を作る必要はない。

### 2.7 動作確認

```bash
cd Frontend/shogi-main
npm test
```

---

## 3. セットアップ後のファイル構成まとめ

### shogi-board

```
Frontend/shogi-board/
├── vite.config.ts          ← test セクション追加
├── package.json            ← test スクリプト追加
└── src/core/
    ├── game.ts
    ├── game.test.ts        ← 新規
    ├── sfen.ts
    ├── sfen.test.ts        ← 新規
    └── ...
```

**新規ファイル:** テストファイル群のみ
**変更ファイル:** `vite.config.ts`, `package.json`

### shogi-main

```
Frontend/shogi-main/
├── vite.config.ts          ← test セクション追加
├── vitest.setup.ts         ← 新規（MSW セットアップ）
├── tsconfig.app.json       ← exclude 追加
├── package.json            ← test スクリプト追加
└── src/
    ├── mocks/
    │   ├── browser.ts      ← 既存（変更なし）
    │   └── server.ts       ← 新規（テスト用 MSW）
    ├── utils/
    │   └── *.test.ts       ← 新規
    └── pages/
        └── *.test.ts       ← 新規
```

**新規ファイル:** `vitest.setup.ts`, `src/mocks/server.ts`, テストファイル群
**変更ファイル:** `vite.config.ts`, `tsconfig.app.json`, `package.json`

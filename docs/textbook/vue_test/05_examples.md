# 具体的なテストコード例

各テスト対象の具体的なテストコード例を示す。これらはそのままコピーして使用可能な実装例。

---

## 1. shogi-board コアロジックのテスト

### 1.1 game.test.ts — 局面操作

```typescript
// Frontend/shogi-board/src/core/game.test.ts
import { describe, it, expect } from 'vitest'
import { createInitialState, applyMove, undoMove, replayToMove } from './game'
import type { BoardMove, DropMove, Move } from './types'

describe('createInitialState', () => {
  it('creates a standard hirate starting position', () => {
    const state = createInitialState()

    // Turn is sente
    expect(state.turn).toBe('sente')
    expect(state.moveCount).toBe(0)
    expect(state.history).toHaveLength(0)

    // Sente's king is at row 8, col 4 (5九)
    const senteKing = state.board[8]![4]
    expect(senteKing).toEqual({ type: 'king', owner: 'sente', promoted: false })

    // Gote's king is at row 0, col 4 (5一)
    const goteKing = state.board[0]![4]
    expect(goteKing).toEqual({ type: 'king', owner: 'gote', promoted: false })

    // Sente's pawns are on row 6
    for (let col = 0; col < 9; col++) {
      expect(state.board[6]![col]).toEqual({ type: 'pawn', owner: 'sente', promoted: false })
    }

    // Empty hands
    expect(state.hands.sente).toEqual({})
    expect(state.hands.gote).toEqual({})
  })
})

describe('applyMove', () => {
  it('moves a piece on the board', () => {
    const state = createInitialState()

    // 7六歩: pawn at row 6 col 2 (7七) moves to row 5 col 2 (7六)
    const move: BoardMove = {
      type: 'move',
      from: { row: 6, col: 2 },
      to: { row: 5, col: 2 },
      promote: false,
    }

    const next = applyMove(state, move)

    // Origin is now empty
    expect(next.board[6]![2]).toBeNull()

    // Destination has the pawn
    expect(next.board[5]![2]).toEqual({ type: 'pawn', owner: 'sente', promoted: false })

    // Turn switched to gote
    expect(next.turn).toBe('gote')
    expect(next.moveCount).toBe(1)
    expect(next.history).toHaveLength(1)
  })

  it('captures an enemy piece and adds it to hand', () => {
    let state = createInitialState()

    // Manually set up a capture scenario:
    // Place a gote pawn at row 5, col 2 (where sente pawn will move)
    state = {
      ...state,
      board: state.board.map(row => row.map(cell => cell ? { ...cell } : null)),
    }
    state.board[5]![2] = { type: 'pawn', owner: 'gote', promoted: false }

    const move: BoardMove = {
      type: 'move',
      from: { row: 6, col: 2 },
      to: { row: 5, col: 2 },
      promote: false,
    }

    const next = applyMove(state, move)

    // Sente's hand now has a pawn
    expect(next.hands.sente.pawn).toBe(1)
  })

  it('promotes a piece when promote flag is true', () => {
    let state = createInitialState()
    state = {
      ...state,
      board: state.board.map(row => row.map(cell => cell ? { ...cell } : null)),
    }

    // Place a sente pawn at row 3 (enemy zone boundary)
    state.board[3]![0] = { type: 'pawn', owner: 'sente', promoted: false }
    // Clear destination
    state.board[2]![0] = null

    const move: BoardMove = {
      type: 'move',
      from: { row: 3, col: 0 },
      to: { row: 2, col: 0 },
      promote: true,
    }

    const next = applyMove(state, move)
    expect(next.board[2]![0]).toEqual({ type: 'pawn', owner: 'sente', promoted: true })
  })

  it('drops a piece from hand', () => {
    let state = createInitialState()
    state = {
      ...state,
      hands: { sente: { pawn: 1 }, gote: {} },
      board: state.board.map(row => row.map(cell => cell ? { ...cell } : null)),
    }
    // Ensure the target square is empty
    state.board[4]![4] = null

    const move: DropMove = {
      type: 'drop',
      pieceType: 'pawn',
      to: { row: 4, col: 4 },
    }

    const next = applyMove(state, move)
    expect(next.board[4]![4]).toEqual({ type: 'pawn', owner: 'sente', promoted: false })
    expect(next.hands.sente.pawn).toBeUndefined() // 0 is deleted
  })

  it('does not mutate the original state (immutability)', () => {
    const state = createInitialState()
    const move: BoardMove = {
      type: 'move',
      from: { row: 6, col: 2 },
      to: { row: 5, col: 2 },
      promote: false,
    }

    applyMove(state, move)

    // Original state should be unchanged
    expect(state.board[6]![2]).toEqual({ type: 'pawn', owner: 'sente', promoted: false })
    expect(state.board[5]![2]).toBeNull()
    expect(state.turn).toBe('sente')
  })
})

describe('undoMove', () => {
  it('restores the previous state after undo', () => {
    const initial = createInitialState()
    const move: BoardMove = {
      type: 'move',
      from: { row: 6, col: 2 },
      to: { row: 5, col: 2 },
      promote: false,
    }

    const afterMove = applyMove(initial, move)
    const afterUndo = undoMove(afterMove)

    expect(afterUndo).not.toBeNull()
    expect(afterUndo!.turn).toBe('sente')
    expect(afterUndo!.moveCount).toBe(0)
    expect(afterUndo!.board[6]![2]).toEqual({ type: 'pawn', owner: 'sente', promoted: false })
    expect(afterUndo!.board[5]![2]).toBeNull()
  })

  it('returns null when there is no history', () => {
    const state = createInitialState()
    expect(undoMove(state)).toBeNull()
  })
})

describe('replayToMove', () => {
  it('replays moves up to the specified count', () => {
    const initial = createInitialState()
    const moves: Move[] = [
      { type: 'move', from: { row: 6, col: 2 }, to: { row: 5, col: 2 }, promote: false }, // 7六歩
      { type: 'move', from: { row: 2, col: 2 }, to: { row: 3, col: 2 }, promote: false }, // 3四歩
    ]

    const after1 = replayToMove(initial, moves, 1)
    expect(after1.moveCount).toBe(1)
    expect(after1.turn).toBe('gote')

    const after2 = replayToMove(initial, moves, 2)
    expect(after2.moveCount).toBe(2)
    expect(after2.turn).toBe('sente')
  })
})
```

### 1.2 sfen.test.ts — SFEN 変換

```typescript
// Frontend/shogi-board/src/core/sfen.test.ts
import { describe, it, expect } from 'vitest'
import { toSfen, parseSfen, moveToUsi, parseUsiMove } from './sfen'
import { createInitialState } from './game'

// Standard hirate SFEN
const HIRATE_SFEN = 'lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1'

describe('toSfen', () => {
  it('generates correct SFEN for hirate starting position', () => {
    const state = createInitialState()
    expect(toSfen(state)).toBe(HIRATE_SFEN)
  })
})

describe('parseSfen', () => {
  it('parses the hirate SFEN correctly', () => {
    const state = parseSfen(HIRATE_SFEN)

    expect(state.turn).toBe('sente')
    expect(state.moveCount).toBe(0)

    // Check some pieces
    expect(state.board[0]![0]).toEqual({ type: 'lance', owner: 'gote', promoted: false })
    expect(state.board[8]![4]).toEqual({ type: 'king', owner: 'sente', promoted: false })
  })

  it('parses a position with pieces in hand', () => {
    const sfen = 'lnsgkgsnl/1r5b1/pppppp1pp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b P 1'
    const state = parseSfen(sfen)
    expect(state.hands.sente.pawn).toBe(1)
  })

  it('throws on invalid SFEN string', () => {
    expect(() => parseSfen('invalid')).toThrow()
  })
})

describe('toSfen -> parseSfen round-trip', () => {
  it('restores the original state through serialization', () => {
    const original = createInitialState()
    const sfen = toSfen(original)
    const restored = parseSfen(sfen)

    expect(toSfen(restored)).toBe(sfen)
    expect(restored.turn).toBe(original.turn)
    expect(restored.moveCount).toBe(original.moveCount)
  })
})

describe('moveToUsi', () => {
  it('converts a board move to USI notation', () => {
    // 7六歩: from (row=6, col=2) to (row=5, col=2)
    expect(moveToUsi({
      type: 'move',
      from: { row: 6, col: 2 },
      to: { row: 5, col: 2 },
      promote: false,
    })).toBe('7g7f')
  })

  it('converts a promotion move to USI notation', () => {
    expect(moveToUsi({
      type: 'move',
      from: { row: 3, col: 1 },
      to: { row: 0, col: 4 },
      promote: true,
    })).toBe('8d5a+')
  })

  it('converts a drop move to USI notation', () => {
    expect(moveToUsi({
      type: 'drop',
      pieceType: 'pawn',
      to: { row: 4, col: 4 },
    })).toBe('P*5e')
  })
})

describe('parseUsiMove', () => {
  it('parses a board move', () => {
    expect(parseUsiMove('7g7f')).toEqual({
      type: 'move',
      from: { row: 6, col: 2 },
      to: { row: 5, col: 2 },
      promote: false,
    })
  })

  it('parses a promotion move', () => {
    const move = parseUsiMove('8d5a+')
    expect(move.type).toBe('move')
    if (move.type === 'move') {
      expect(move.promote).toBe(true)
    }
  })

  it('parses a drop move', () => {
    expect(parseUsiMove('P*5e')).toEqual({
      type: 'drop',
      pieceType: 'pawn',
      to: { row: 4, col: 4 },
    })
  })
})
```

### 1.3 rules.test.ts — ルール判定（抜粋）

```typescript
// Frontend/shogi-board/src/core/rules.test.ts
import { describe, it, expect } from 'vitest'
import { isInCheck, getPromotionStatus, isNifu, getLegalBoardMoves } from './rules'
import { createInitialState, applyMove } from './game'
import { createHirateBoard, createEmptyHands } from './constants'
import type { Board, Piece, GameState } from './types'

// Helper: create an empty 9x9 board
function emptyBoard(): Board {
  return Array.from({ length: 9 }, () => Array(9).fill(null))
}

describe('isInCheck', () => {
  it('returns false for the hirate starting position', () => {
    const board = createHirateBoard()
    expect(isInCheck(board, 'sente')).toBe(false)
    expect(isInCheck(board, 'gote')).toBe(false)
  })

  it('detects check by a rook', () => {
    const board = emptyBoard()
    // Sente king at 5九 (row 8, col 4)
    board[8]![4] = { type: 'king', owner: 'sente', promoted: false }
    // Gote rook on the same file at 5一 (row 0, col 4)
    board[0]![4] = { type: 'rook', owner: 'gote', promoted: false }

    expect(isInCheck(board, 'sente')).toBe(true)
  })

  it('does not detect check when blocked by another piece', () => {
    const board = emptyBoard()
    board[8]![4] = { type: 'king', owner: 'sente', promoted: false }
    board[0]![4] = { type: 'rook', owner: 'gote', promoted: false }
    // Blocking piece in between
    board[4]![4] = { type: 'pawn', owner: 'sente', promoted: false }

    expect(isInCheck(board, 'sente')).toBe(false)
  })
})

describe('getPromotionStatus', () => {
  it('returns none for a king', () => {
    const piece: Piece = { type: 'king', owner: 'sente', promoted: false }
    expect(getPromotionStatus(piece, { row: 4, col: 4 }, { row: 3, col: 4 })).toBe('none')
  })

  it('returns none for a gold', () => {
    const piece: Piece = { type: 'gold', owner: 'sente', promoted: false }
    expect(getPromotionStatus(piece, { row: 3, col: 4 }, { row: 2, col: 4 })).toBe('none')
  })

  it('returns optional when a silver enters the enemy zone', () => {
    const piece: Piece = { type: 'silver', owner: 'sente', promoted: false }
    // Moving into enemy zone (row <= 2 for sente)
    expect(getPromotionStatus(piece, { row: 3, col: 4 }, { row: 2, col: 4 })).toBe('optional')
  })

  it('returns mandatory for a pawn reaching the last rank', () => {
    const piece: Piece = { type: 'pawn', owner: 'sente', promoted: false }
    // Sente pawn reaching row 0 (1段目)
    expect(getPromotionStatus(piece, { row: 1, col: 0 }, { row: 0, col: 0 })).toBe('mandatory')
  })

  it('returns mandatory for a knight reaching the last two ranks', () => {
    const piece: Piece = { type: 'knight', owner: 'sente', promoted: false }
    expect(getPromotionStatus(piece, { row: 3, col: 3 }, { row: 1, col: 4 })).toBe('mandatory')
  })
})

describe('isNifu', () => {
  it('detects nifu (two unpromoted pawns on the same file)', () => {
    const board = emptyBoard()
    board[3]![4] = { type: 'pawn', owner: 'sente', promoted: false }

    expect(isNifu(board, 'sente', 4)).toBe(true)
  })

  it('does not flag promoted pawn as nifu', () => {
    const board = emptyBoard()
    board[3]![4] = { type: 'pawn', owner: 'sente', promoted: true } // と金

    expect(isNifu(board, 'sente', 4)).toBe(false)
  })

  it('does not flag opponent pawn as nifu', () => {
    const board = emptyBoard()
    board[3]![4] = { type: 'pawn', owner: 'gote', promoted: false }

    expect(isNifu(board, 'sente', 4)).toBe(false)
  })
})
```

---

## 2. shogi-main ユーティリティのテスト

### 2.1 explorer.test.ts

```typescript
// Frontend/shogi-main/src/utils/explorer.test.ts
import { describe, it, expect } from 'vitest'
import { buildBreadcrumbs } from './explorer'

describe('buildBreadcrumbs', () => {
  it('returns empty array for empty string', () => {
    expect(buildBreadcrumbs('')).toEqual([])
  })

  it('returns single breadcrumb for single-level path', () => {
    expect(buildBreadcrumbs('folder')).toEqual([
      { name: 'folder', path: 'folder' },
    ])
  })

  it('returns cumulative paths for multi-level path', () => {
    expect(buildBreadcrumbs('a/b/c')).toEqual([
      { name: 'a', path: 'a' },
      { name: 'b', path: 'a/b' },
      { name: 'c', path: 'a/b/c' },
    ])
  })
})
```

### 2.2 labels.test.ts

```typescript
// Frontend/shogi-main/src/utils/labels.test.ts
import { describe, it, expect } from 'vitest'
import { sideLabel, resultLabel } from './labels'

describe('sideLabel', () => {
  it('maps side values to Japanese labels', () => {
    expect(sideLabel.none).toBe('-')
    expect(sideLabel.sente).toBe('先手')
    expect(sideLabel.gote).toBe('後手')
  })
})

describe('resultLabel', () => {
  it('maps result values to Japanese labels', () => {
    expect(resultLabel.none).toBe('-')
    expect(resultLabel.win).toBe('勝ち')
    expect(resultLabel.loss).toBe('負け')
    expect(resultLabel.sennichite).toBe('千日手')
    expect(resultLabel.jishogi).toBe('持将棋')
  })
})
```

---

## 3. shogi-main コンポーネントのテスト

### 3.1 KifuListPage.test.ts — ページコンポーネント

```typescript
// Frontend/shogi-main/src/pages/KifuListPage.test.ts
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import KifuListPage from './KifuListPage.vue'
import PrimeVue from 'primevue/config'

// Note: MSW server is started in vitest.setup.ts
// The auto-generated mock handlers return Faker-generated data by default

// Create a minimal router for testing
function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/kifus', component: KifuListPage },
      { path: '/kifus/new', component: { template: '<div>new</div>' } },
      { path: '/kifus/:kid', component: { template: '<div>detail</div>' } },
      { path: '/tags/:tid', component: { template: '<div>tag</div>' } },
    ],
  })
}

describe('KifuListPage', () => {
  it('renders the page title', async () => {
    const router = createTestRouter()
    await router.push('/kifus')
    await router.isReady()

    const wrapper = mount(KifuListPage, {
      global: {
        plugins: [router, PrimeVue],
      },
    })

    // Wait for onMounted async call to complete
    await flushPromises()

    expect(wrapper.text()).toContain('マイページ')
  })

  it('displays total count after loading', async () => {
    const router = createTestRouter()
    await router.push('/kifus')
    await router.isReady()

    const wrapper = mount(KifuListPage, {
      global: {
        plugins: [router, PrimeVue],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('保存棋譜数')
  })

  it('shows empty message when no kifus exist', async () => {
    // Override the MSW handler for this test only
    const { server } = await import('@/mocks/server')
    const { http, HttpResponse } = await import('msw')

    server.use(
      http.get('*/kifus/recent', () => {
        return HttpResponse.json({
          kifus: [],
          total_count: 0,
        })
      })
    )

    const router = createTestRouter()
    await router.push('/kifus')
    await router.isReady()

    const wrapper = mount(KifuListPage, {
      global: {
        plugins: [router, PrimeVue],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('棋譜がありません')
  })
})
```

### ポイント解説

```
テストの流れ:

1. createTestRouter()   ← 最小限のルーター定義を作成
2. router.push('/kifus') ← テスト対象のパスに遷移
3. mount(KifuListPage)  ← コンポーネントをマウント（MSW が API レスポンスを返す）
4. flushPromises()      ← 非同期処理（API 呼び出し）の完了を待つ
5. expect(...)          ← レンダリング結果を検証
```

- `flushPromises()` は Vue Test Utils が提供する関数で、すべての pending な Promise を解決する。`onMounted` 内の API 呼び出しが完了するのを待つために必要。
- `server.use()` で特定テストだけモックを上書きすることで、正常系・異常系・空データ等のパターンをテストできる。
- PrimeVue コンポーネント（DataTable 等）のスタブ化が必要な場合は `global.stubs` を使う。

---

## 4. テスト実行コマンド

```bash
# shogi-board のテスト実行
cd Frontend/shogi-board
npm test

# shogi-main のテスト実行
cd Frontend/shogi-main
npm test

# ウォッチモード（ファイル変更時に自動再実行）
npm run test:watch

# 特定のファイルだけ実行
npx vitest run src/core/game.test.ts

# カバレッジ付きで実行（要設定追加）
npx vitest run --coverage
```

---

## 5. テストを書くときのパターン集

### パターン 1: 純粋関数のテスト

```typescript
// 最もシンプル。入力と出力を検証するだけ
it('does something with given input', () => {
  const result = someFunction(input)
  expect(result).toEqual(expected)
})
```

### パターン 2: エラーケースのテスト

```typescript
// 関数がエラーをスローすることを検証
it('throws on invalid input', () => {
  expect(() => someFunction(invalidInput)).toThrow()
  // 特定のエラーメッセージを検証する場合:
  expect(() => someFunction(invalidInput)).toThrow('Invalid input')
})
```

### パターン 3: ラウンドトリップテスト

```typescript
// シリアライズ → デシリアライズで元に戻ることを検証
it('round-trips correctly', () => {
  const original = createSomeData()
  const serialized = serialize(original)
  const deserialized = deserialize(serialized)
  expect(serialize(deserialized)).toBe(serialized)
})
```

### パターン 4: API エラーのテスト

```typescript
// MSW でエラーレスポンスを返して、UI のエラーハンドリングを検証
it('shows error on API failure', async () => {
  server.use(
    http.get('*/some-endpoint', () => {
      return HttpResponse.json({ message: 'Error' }, { status: 500 })
    })
  )

  const wrapper = mount(SomeComponent, { /* options */ })
  await flushPromises()

  expect(wrapper.text()).toContain('エラー')
})
```

### パターン 5: ユーザー操作のテスト

```typescript
// ボタンクリック等のインタラクションを検証
it('navigates on button click', async () => {
  const wrapper = mount(SomeComponent, {
    global: { plugins: [router] },
  })

  await wrapper.find('button').trigger('click')
  await flushPromises()

  expect(router.currentRoute.value.path).toBe('/expected-path')
})
```

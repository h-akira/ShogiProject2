# user_stories.md 変更通知: 棋譜編集・将棋盤入力モードの受け入れ条件追加

## 変更概要

`docs/user_stories.md` の US-3.3（棋譜の将棋盤 GUI 入力）と US-3.6（棋譜の編集）に受け入れ条件を追加した。BUG-002（棋譜編集画面で将棋盤入力モードに切り替えると棋譜データが消失する）の修正に伴う変更。

## 変更内容

### US-3.3: 棋譜の将棋盤 GUI 入力

以下の受け入れ条件を追加:

- 「一手戻す」操作で直前の入力を取り消せる
- 新規作成時は「初期局面に戻る」操作で盤面をリセットできる

### US-3.6: 棋譜の編集

以下の受け入れ条件を追加:

- 将棋盤入力モードでも既存の棋譜データ（指し手）が盤面にプリロードされ、最終局面が表示される
- 「変更を破棄」操作で保存済みの棋譜データを復元できる

## フロントエンド側の対応（対応済み）

### shogi-board パッケージ

| ファイル | 変更内容 |
|---------|---------|
| `src/composables/useMode.ts` | `loadKif()` で `inputGame` にも KIF を読み込むように修正 |
| `src/components/InputControls.vue` | input モード用コントロール（一手戻す・リセット/変更破棄）を新規作成。`resetLabel` prop でボタンラベルをカスタマイズ可能 |
| `src/components/ShogiBoard.vue` | `InputControls` を統合。`resetLabel` prop と `reset` emit を追加し、リセット処理を親コンポーネントに委譲 |

### shogi-main パッケージ

| ファイル | 変更内容 |
|---------|---------|
| `src/pages/KifuEditPage.vue` | ShogiBoard に `resetLabel="変更を破棄"` を設定し、リセット時に確認ダイアログ → 保存済みデータ復元 |
| `src/pages/KifuCreatePage.vue` | ShogiBoard の `@reset` で `boardRef.reset()` を呼び出し（初期局面に戻る） |

## 結合テスト（integration-tests）への影響

以下のテストケースを `test_us3_kifu.py` に追加する必要がある:

| テストクラス | テストケース | 検証内容 |
|-------------|------------|---------|
| TestUS3_3_KifuBoardInput | `test_board_input_undo` | 将棋盤入力後に「一手戻す」ボタンで手が戻ること |
| TestUS3_6_KifuEdit | `test_edit_kifu_board_preload` | 編集画面で将棋盤に既存棋譜がプリロードされること |
| TestUS3_6_KifuEdit | `test_edit_kifu_preserves_kif_data` | 将棋盤モードで更新後、棋譜データが保持されること |
| TestUS3_6_KifuEdit | `test_edit_kifu_discard_changes` | 「変更を破棄」で保存済みデータが復元されること |

## 関連

- `bugs/002_kifu_edit_board_mode_data_loss.md` — バグ詳細

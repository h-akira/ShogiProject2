# BUG-006: 後手番の棋譜解析で評価値の符号が逆になる

## ステータス

修正済み（検証済み）

## 発見日

2026-03-17

## 概要

棋譜解析機能で後手番の局面を解析すると、評価値の符号が先手基準で逆になる。後手が明らかに優勢な局面で後手番のとき、評価値がプラス（先手有利）として表示される。

## 症状

- 後手番の局面で解析すると、後手優勢なのに評価値がプラス（先手有利に見える）で表示される
- 先手番の局面では正しく表示される（後手優勢ならマイナス）
- 最善手の候補順位自体は正しい（順位はエンジンの multipv そのまま）

## 原因

USIプロトコルの仕様として、エンジン（やねうら王）は常に**現在の手番の視点**で評価値を返す。

- SFEN `... b ...`（先手番）: 正の値 = 先手有利（先手基準と一致するため問題なし）
- SFEN `... w ...`（後手番）: 正の値 = 後手有利（先手基準とは逆）

`Backend/analysis/worker/engine.py` の `analyze` メソッド（L48-68）で、エンジンからの評価値をそのまま返しており、手番に応じた符号変換を行っていない。フロントエンド `Frontend/shogi-main/src/pages/KifuDetailPage.vue`（L244）でも `c.score` をそのまま表示している。

## 影響範囲

- `Backend/analysis/worker/engine.py` — `ShogiEngine.analyze()`
- `Backend/analysis/worker/handler.py` — Lambda handler（値を中継）
- `Backend/analysis/api/services/analysis_service.py` — `get_analysis()`（値を中継）
- `Frontend/shogi-main/src/pages/KifuDetailPage.vue` — 解析結果表示

## 再現手順

1. 棋譜詳細ページで、後手番の局面に進める
2. 「AI局面解析」で解析を実行する
3. 後手が明らかに優勢な局面であるにもかかわらず、評価値がプラス（先手有利）として表示される
4. 同じ棋譜の1手前（先手番）で解析すると、後手優勢ならマイナスで正しく表示される

## 修正案

### 案1: バックエンドで先手基準に正規化（推奨）

`engine.py` の `analyze` メソッドで、SFENから手番を判定し、後手番（`w`）の場合に評価値の符号を反転する。

```python
def analyze(self, sfen: str, movetime: int) -> list[dict]:
    self._send(f"position sfen {sfen}")
    self._send(f"go movetime {movetime}")
    ...
    # Normalize score to sente perspective
    turn = sfen.split()[1]  # 'b' = sente, 'w' = gote
    sign = -1 if turn == "w" else 1

    for line in lines:
        ...
        if score_type == "mate":
            score = MATE_SCORE if int(score_val) > 0 else -MATE_SCORE
        else:
            score = int(score_val)
        candidates[rank] = {"rank": rank, "score": score * sign, "pv": pv}
```

**メリット**: APIレスポンスが常に先手基準になり、フロントエンドや将来の機能（評価グラフ等）で一貫して扱える。
**注意点**: 詰み（mate）スコアにも `sign` を適用する必要がある。

### 案2: フロントエンドで表示時に反転

`KifuDetailPage.vue` で `analysisResult.sfen` から手番を判定し、表示時に符号を反転する。

**メリット**: バックエンドの変更が不要。
**デメリット**: APIの `score` の意味が手番依存のままとなり、他のAPI利用者やグラフ機能で混乱を招く。

## 対応

案1（バックエンドで先手基準に正規化）を採用。

### 変更ファイル

- `Backend/analysis/worker/engine.py` — `ShogiEngine.analyze()`: SFENの手番フィールドを参照し、後手番（`w`）の場合に評価値の符号を反転するよう修正。cp値・mate値ともに対象。
- `Backend/analysis/tests/test_engine.py` — `TestAnalyzeGoteTurn` クラスを追加。後手番のcp値・mate値がそれぞれ正しく反転されることを検証するテスト2件を追加。

## 関連

- USIプロトコル仕様: エンジンの `score cp` / `score mate` は現在の手番の視点で返される
- やねうら王ドキュメント

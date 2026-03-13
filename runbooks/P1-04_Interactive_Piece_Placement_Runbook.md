---
title: "P1-04 Interactive Piece Placement Runbook"
version: "0.1.0"
owner: "SoChi-lab Frontend Team"
last_updated: "2026-02-20"
status: "draft"
tags: [runbook, frontend, gameplay, interactive, placement]
---

# 🎯 Purpose

現在の「領域当て」方式（どの空きエリアがどのピースか当てるだけ）から、
**「ピースを実際に回転させて3D空間に配置する」方式**に発展させる。

プレイヤーはピースの3D形状を把握し、正しい向きに回転させてからパズルに差し込む体験を得る。
これが SoChi BLOCKS の核心的なゲームプレイとなる。

---

## 💡 Background & Current State

### 現在の実装（MVP v1 = 領域当て方式）

| 要素 | 現状 |
|---|---|
| ピース選択 | トレイカードをクリック |
| 配置 | 3D空間の空きセルをクリック → `cell.piece === selectedPiece` で判定 |
| 回転 | **なし** |
| 難易度 | ピースの形状・向きに関係なく「どのエリアか」だけを当てる |

### 課題

- 向きの概念がないため、ピースを「空間的に理解」する必要がない
- 12個のピースを順に当てるだけになり、ゲームとして浅い
- 3D空間の意味が薄い

### 目指すゲームプレイ

```
ピース選択 → 3Dプレビューで向き確認 → 回転操作 → パズルに配置 → 正誤判定
```

---

## 🎮 Game Design Spec

### インタラクションフロー

```
① トレイのピースカードをクリック → ピース選択
② 画面にそのピースの3Dプレビューが出現（ステージングエリア）
③ 回転ボタンまたはジェスチャーでピースを回転（X/Y/Z軸）
④ パズルの空きセルをクリック → 「このへんに置きたい」
⑤ 判定：現在の向きのピースがその空きエリアにフィットするか？
   ✅ 正解 → ピースが実体化してはまる
   ❌ 不正解 → シェイク + エラーフィードバック（向きが違う or エリアが違う）
```

### 判定ロジック詳細

**単純化された判定方針（オートフィット方式）**

```
1. selectedPiece の正規形状を master_pieces.json から取得
   → shape_json: [[x,y,z], ...]（正準向き）

2. 現在の回転状態（rotationIndex: 0〜23）を適用して座標変換

3. パズルの空きセル（removedPiecesに属し未配置）をスキャン

4. クリックされたセルが selectedPiece の空きセルである場合:
   → 変換後のピース形状を「クリックセルを基準点のひとつ」として全N通りの
     アンカーで試行（ピースの各セルを基準点として配置）

5. いずれかのアンカーで全セルが selectedPiece の空きセルと一致 → ✅ 正解
   一致しない → ❌ 向きが違う or エリアが違う
```

> **ポイント**: アンカー（基準点）の選択はシステムが自動試行するため、
> プレイヤーは「どこに置くか」よりも「どの向きか」に集中できる。

### 3D回転の考え方

立方体の回転群は **24通り**（回転対称性の群）。

```
回転状態を 0〜23 のインデックスで管理。
各インデックスは 3×3 整数回転行列に対応。

実用的な表現:
  rotX(n) = X軸を中心に 90°×n 回転  (n=0,1,2,3)
  rotY(n) = Y軸を中心に 90°×n 回転  (n=0,1,2,3)

24通りの組み合わせを事前定義した行列テーブルとして持つ。
```

**対称ピースの取り扱い**:
同じ形状が複数の回転インデックスで一致する場合がある（例: 直線5連のI型）。
いずれの「正しい向き」を選んでも正解とする（判定は形状一致で行う）。

---

## 🖼️ UX Layout Proposals

### 案A: サイドステージ（推奨）

```
┌────────────────────┬──────────────┐
│                    │              │
│   パズル3D         │  ピース      │
│   (OrbitControls)  │  プレビュー  │
│                    │  3D          │
│                    │  [↻X][↻Y][↻Z]│
├────────────────────┴──────────────┤
│  トレイ: [F] [I] [L] ...          │
└───────────────────────────────────┘
```

- 利点: 常にパズルとピースを並べて見られる
- 欠点: モバイルでは横幅が狭い

### 案B: ボトムプレビュー

```
┌───────────────────────────────────┐
│                                   │
│         パズル3D                  │
│                                   │
├──────────────┬────────────────────┤
│  ピース      │  [↻X] [↻Y] [↻Z]   │
│  プレビュー  │  回転ボタン        │
├──────────────┴────────────────────┤
│  トレイ: [F] [I] [L] ...          │
└───────────────────────────────────┘
```

- 利点: モバイル縦向きに適合
- 欠点: パズルの表示エリアが縮む

### 案C: モーダル配置モード

```
ピースカード選択
    ↓
[配置モード画面]
┌───────────────────────────────────┐
│  ピース: F                        │
│                                   │
│     [大きなピースプレビュー3D]    │
│                                   │
│  [←] [→X] [↑Y] [→Z] [→]         │
│   戻る  回転ボタン群  パズルへ    │
└───────────────────────────────────┘
    ↓「パズルへ」押下
パズル画面 → 空きセルをクリックして配置
```

- 利点: 各工程に集中できる、モバイルに強い
- 欠点: 画面遷移が増える（2ステップ感）

---

## 🔧 Technical Architecture

### 新規ファイル

| ファイル | 役割 |
|---|---|
| `frontend/src/utils/rotations.ts` | 24回転行列の定義・座標変換・正規化 |
| `frontend/src/utils/placement.ts` | ピース配置検証ロジック（フィット判定） |
| `frontend/src/components/PieceStage.tsx` | ピース3Dプレビュー（R3F Canvas独立） |
| `frontend/src/components/RotationControls.tsx` | 回転ボタンUI |

### 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `frontend/src/hooks/useGameState.ts` | `rotationIndex: number` 追加、`ROTATE_X/Y/Z` アクション追加 |
| `frontend/src/components/PuzzleVoxels.tsx` | 配置判定の呼び出し変更 |
| `frontend/src/App.tsx` | レイアウト変更（ステージングエリア追加）、判定ロジック変更 |
| `frontend/src/App.css` | 新レイアウト対応スタイル |

### `rotations.ts` の核心

```typescript
// 24通りの回転行列（3x3）を事前定義
export const ROTATION_MATRICES: number[][][] = [ /* 24 entries */ ];

// 座標に回転行列を適用
export function applyRotation(
  cells: [number, number, number][],
  rotIndex: number
): [number, number, number][] { ... }

// 正規化（最小座標を原点に）
export function normalize(
  cells: [number, number, number][]
): [number, number, number][] { ... }
```

### `placement.ts` の核心

```typescript
// 現在の回転でピースがクリックされたセルの空きエリアにフィットするか判定
export function canPlace(
  pieceId: string,           // "F", "L" など
  rotIndex: number,          // 現在の回転インデックス
  clickedCell: PuzzleCell,   // プレイヤーがクリックしたセル
  emptyCells: PuzzleCell[],  // そのピースの全空きセル（puzzle data から）
): boolean {
  // 1. master_pieces から正規形状取得
  // 2. rotIndex で回転適用 + 正規化
  // 3. clickedCell を基準に各セルをアンカーとして試行
  // 4. いずれかで全セルが emptyCells と一致すれば true
}
```

### `useGameState.ts` の変更

```typescript
// 追加アクション
| { type: 'ROTATE'; axis: 'X' | 'Y' | 'Z'; dir: 1 | -1 }

// 追加状態
rotationIndex: number;  // 0〜23

// ROTATEアクションの処理
case 'ROTATE':
  return {
    ...state,
    rotationIndex: nextRotationIndex(state.rotationIndex, action.axis, action.dir),
  };

// SELECT_PIECEでrotationIndexをリセット
case 'SELECT_PIECE':
  return {
    ...state,
    selectedPiece: ...,
    rotationIndex: 0,  // ← ピース変更時に向きをリセット
  };
```

---

## 📋 Implementation Phases

### Phase 1: 回転ライブラリ（バックエンドロジック）

- `rotations.ts`: 24回転行列の定義と座標変換
- `placement.ts`: フィット判定ロジック
- ユニットテストで検証可能（UIなし）

### Phase 2: ゲーム状態に回転を統合

- `useGameState.ts` に `rotationIndex` と `ROTATE` アクション追加
- `handleEmptyCellClick` を新判定ロジックに差し替え

### Phase 3: ピースプレビューUI

- `PieceStage.tsx`: 選択中ピースを回転状態で3D表示（独立したR3F Canvas）
- `RotationControls.tsx`: X/Y/Z軸回転ボタン
- レイアウト案の決定と実装（A/B/C）

### Phase 4: エフェクト・UX仕上げ

- 正解時のアニメーション（ピースがはまるエフェクト）
- エラーフィードバックの改善（「向きが合ってない」vs「エリアが違う」の区別）
- 全ピース配置時のクリア演出（VictoryOverlay の復活・改善）
- ヒント機能（現在の向きが正しければ空きエリアをハイライト）

---

## ❓ Open Questions（決定が必要な事項）

| # | 質問 | 選択肢 |
|---|---|---|
| 1 | **UXレイアウト** | 案A（サイドステージ）/ 案B（ボトム）/ 案C（モーダル） |
| 2 | **回転操作** | ボタン方式（X/Y/Z軸ボタン）/ ジェスチャー（スワイプ）/ 両方 |
| 3 | **難易度設計** | 回転なし（向き固定で簡単）/ 回転あり（本格的） ← 今は後者前提 |
| 4 | **エラー詳細度** | 「違う」だけ / 「向きが違う」「エリアが違う」を区別 |
| 5 | **ピース基準点** | オートフィット（推奨）/ プレイヤーが基準点を指定 |
| 6 | **モバイル回転操作** | ピースプレビューをドラッグで回転 / ボタンのみ |

---

## ✅ Verification Checklist（実装後の確認項目）

- [ ] 24回転すべての行列が正しく定義されている（回転後の形状が正しい）
- [ ] 対称ピース（I型など）でどの正しい向きを選んでも正解になる
- [ ] 間違った向きでクリックするとエラーになる
- [ ] 間違ったエリアでクリックするとエラーになる
- [ ] ピース変更時に回転がリセットされる
- [ ] 全ピース配置でクリア状態になる
- [ ] モバイル（スマホ）でトレイタップ・空きセルタップが正常動作
- [ ] Answerトグルで全ピース表示に切り替えられる（ゲーム状態維持）
- [ ] TypeScript エラーゼロ（`tsc --noEmit`）

---

## 🗒️ Notes

- `master_pieces.json` の `shape_json` は `[[x,y,z],...]` 形式。Z軸の扱いに注意（ビューワーでY/Z軸スワップ済み）。
- 回転行列テーブルは [Wikipedia: Rotation group SO(3)](https://en.wikipedia.org/wiki/Octahedral_symmetry) の24元素を参照。
- Phase 1〜2 はUIなしで実装・テスト可能。Phase 3 に入る前に判定ロジックを固める。

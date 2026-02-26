---
title: "P1-07 3D Puzzle UI/UX Improvement Runbook"
version: "0.1.0"
owner: "SoChi-lab Frontend Team"
last_updated: "2026-02-26"
status: "draft"
tags: [runbook, ui, ux, threejs, r3f, mobile, onboarding]
---

# 🎯 Purpose
SoChi BLOCKS の 3Dパズルにおいて、初回体験での離脱（例: 30秒でやめた）を減らし、
「思い通りに動かない」ストレスを解消して、思考体験へ到達させる。

---

# ✅ Scope（今回やること / やらないこと）
## Do（対象）
- 視認性（ブラー/半透明）の設計変更
- ピース回転操作の再設計（選択制）
- 配置箇所の選択UI（グリッドカーソル方式）
- ピース原点（anchor）導入の設計検討（段階導入）
- チュートリアル/オンボーディング導線の追加（軽量）

## Not Do（今回やらない）
- 3Dエンジンや描画基盤の全面刷新
- パズルデータ生成パイプラインの全面変更（必要最小限の拡張のみ）
- 高機能なアニメ/演出の作り込み（最小限）

---

# 🧠 Problem Statement（現状課題）
ユーザーからのフィードバックにより主要課題は2つ：
1) ピース回転の操作性が悪く、意図通り回らない  
2) ピース配置箇所の選択が難しく、意図しない場所にハマるストレスがある  

副次課題：
- UIがシンプルすぎて冷たく無機質に感じる可能性
- 操作の理解までの導線（チュートリアル/ガイド）が不足

---

# 🧩 Requirements（要件）
## UX要件
- 「今動かしているピース」が常に最も見やすい
- 操作が “再現可能” である（同じ入力→同じ結果）
- 初回ユーザーが迷ったときに、最短で操作理解に到達できる

## UI要件
- ボタンは増やしすぎない（視覚ノイズ抑制）
- iOS表示も前提（タッチ誤爆・小画面対策）
- PC / Mobile で必要なら操作体系を分岐できる設計

---

# 🛠️ Implementation Plan（段階実装）
## Phase 1（即効性・低リスク）: Blur / Visibility
### A. ブラー（半透明）設計変更
- 既に配置済み（固定）ブロックを半透明化
- 操作対象（動かしている）ピースは不透明・強調

#### Acceptance Criteria
- 操作中ピースの輪郭・形状が明確に視認できる
- 固定済みブロックが邪魔に感じにくい

#### Notes
- 「ブラー」＝「半透明（opacity）」でまず実装（本当のブラーはコスト高）

---

## Phase 2（最重要）: Rotation UX（選択制）
### B. 回転操作を “選択制” に変更
- 回転軸（X/Y/Z）をUIで明示して選択
- Z軸回転は独立ボタン（誤操作減）
- 既存のドラッグ回転/ジェスチャーは “ビュー全体回転” に寄せる（検討）

#### UI案（例）
- Rotate Mode: [X] [Y] [Z]
- Rotate + / Rotate -（もしくは 90° ボタン）

#### Acceptance Criteria
- “意図しない軸で回る” 体験が消える
- 操作説明なしでも、ボタン表示で回転の意味が伝わる

---

## Phase 3（最重要）: Placement UX（グリッドカーソル）
### C. 配置箇所を “グリッドカーソル” で選ぶ
- カーソル（x,y,z）をボタンで移動
- “ガラケー操作” のイメージ：上下左右＋奥/手前（必要なら）
- ピースはカーソル位置にスナップする

#### UI案（最小）
- Cursor: ↑ ↓ ← →
- （必要なら）Z+ / Z- または Layer 切替

#### Acceptance Criteria
- “意図したところにハマらない” ストレスが大きく減る
- 移動の粒度がグリッド単位で安定する

---

## Phase 4（設計重め）: Piece Anchor（原点）
### D. ピースに anchor（原点）を導入
目的：ピース切り替え時に配置箇所をキープし、スポーンが安定する

#### 設計案
- piece data に `anchor: [ax, ay, az]` を追加（ローカル座標）
- 配置時は `gridCursor - anchor` を基準に transform を決定

#### 段階導入（おすすめ）
1) anchor をコード内で仮固定（デフォルト：最小座標のセル等）
2) JSONに anchor を追加（後方互換：未設定なら自動計算）

#### Acceptance Criteria
- ピース切り替え時、カーソル位置が保持される
- スポーン時のズレが発生しない

---

## Phase 5（軽量）: Onboarding / Tutorial
### E. チュートリアル導線を追加
- 「遊び方」ページの改善 or viewer 内に簡易オーバーレイ
- 初回だけ出す（localStorage フラグ）
- 3ステップ程度（回転→カーソル→配置）

#### Acceptance Criteria
- 初回離脱が減る（計測できるなら滞在時間/操作回数で見る）
- 操作の迷いが減る（ヒント表示回数など）

---

# ⚠️ Risks / Concerns（懸念点）
## 1) ボタン増加によるUI崩壊
- 小画面で圧迫・誤タップ増
- “洗練” が “ごちゃごちゃ” に変わる

**対策**
- ボタンは「カーソル」と「回転選択」に限定
- 詳細操作はモード切替にまとめる（Rotate/Move）

## 2) 操作体系の複雑化
- 改善のつもりが学習コスト増になる

**対策**
- 初回は “最小機能セット” だけ見せる（段階開放）
- チュートリアルで3操作に絞る

## 3) anchor導入の開発コスト
- データ仕様の変更が発生しうる

**対策**
- 自動計算で後方互換を維持
- Phase4は設計→小さく導入

## 4) モバイル/PCの相性差
- スワイプ/ボタン混在のUX破綻

**対策**
- 入力デバイスに応じてUI切替（Mobileはボタン寄り、PCはキー+マウス）

---

# ✅ Definition of Done（完了条件）
- 「回転」と「配置」が意図通りにできる（自己テスト + 1名以上の他者テスト）
- iOS / PC で最低限の操作が成立
- ブラー変更が適用され、操作対象が最も見やすい
- “初回向けガイド” が存在し、迷いにくい

---

# 🧪 Test Checklist（手動テスト）
- [ ] iPhone Safari: タップ誤爆が起きにくい
- [ ] ピース回転：X/Y/Z で期待通り回る
- [ ] 配置：カーソル移動→意図したグリッドに置ける
- [ ] 固定ブロック半透明：見やすさ向上
- [ ] チュートリアル：初回のみ表示される

---

# 🧾 Claude Code Prompt（実装依頼テンプレ）
以下を Claude Code に渡して進める。

## Prompt
あなたは SoChi BLOCKS のフロントエンドエンジニアです。
現状の3Dビューア（React + Three.js / R3F想定）に対して、以下の順で改善を実装してください。

1) 固定済みブロックを半透明化し、操作対象ピースを最も見やすくする（opacityでOK）
2) ピース回転を「選択制」に変更：
   - 回転軸 X/Y/Z をボタンで選べる
   - Z軸回転は独立操作にする
3) 配置箇所を「グリッドカーソル方式」に変更：
   - ボタンでカーソルを上下左右（必要なら前後/レイヤー）に移動
   - ピースはカーソル位置にスナップ
4) （設計→小実装）ピースanchor導入を検討し、未設定なら自動計算で後方互換を維持する

制約：
- UIボタンは増やしすぎない。モバイル(iOS)で破綻しないレイアウトにする。
- 既存のURL/パズル読み込み仕様は壊さない。
- 変更点をファイル単位で一覧化し、最小差分で実装する。

出力：
- 実装差分（どのファイルをどう変えたか）
- 画面上の操作説明（短文でOK）
- iOS/PCの注意点

---

# 📌 Notes（メモ）
- ブラー=半透明でまず導入（本ブラーは後回し）
- “思い通りに動かない” を最優先で解消する
- 初回体験の改善が目的（見た目の作り込みは二の次）

---

# 🔍 Current State Analysis（コードベース調査結果）
> 調査日: 2026-02-26 / 対象ブランチ: main

## 現状の構成サマリ

| ファイル | 役割 |
|---|---|
| `frontend/src/App.tsx` | ゲーム状態管理・UI組立・キーボードショートカット |
| `frontend/src/components/Viewer.tsx` | R3F Canvas + OrbitControls + AxisArrows |
| `frontend/src/components/PuzzleVoxels.tsx` | 全ブロックのレンダリング・クリックハンドラ |
| `frontend/src/components/PieceStage.tsx` | ピースプレビュー3D + ドラッグ回転 |
| `frontend/src/hooks/useGameState.ts` | gameReducer / GameState / dispatch wrappers |
| `frontend/src/utils/placement.ts` | validAnchors / placementCells / refCellOf |
| `frontend/src/components/TutorialOverlay.tsx` | 初回ヘルプオーバーレイ（localStorage フラグ済） |

## フェーズ別 現状と差分

### Phase 1 ブラー（半透明）— **部分的に実装済み**
**既存の opacity 体系（PuzzleVoxels.tsx）:**
```
固定ブロック (solid)   : opacity=1, transparent=false  ← 変更必要
配置済みピース         : opacity=1, transparent=false  ← 変更必要
アンカーセル           : opacity=0.60
ゴーストセル           : opacity=0.28
選択中・非ゴースト      : opacity=0.05
ピース未選択           : opacity=0.15
```
**問題**: 固定ブロック・配置済みブロックが常に不透明なため、ゴーストが視覚的に埋もれる。
**必要な変更**: `selectedPiece` が存在するとき、solid 側を半透明にする。

**レイヤリング方針（重要）**:
- active（操作中ピース）: 最も目立つ（不透明 or 高 opacity）
- ghost（配置プレビュー）: 次に目立つ（中 opacity、active より下）
- placed（既に配置済み）: active 選択中のみ薄く（視認性の邪魔を減らす）
- solid（盤面/固定）: 基本は薄め（active 選択中はさらに薄く）

※ 目的は「今動かしているものが最も見える」こと。

---

### Phase 2 回転操作 — **Z軸のみ実装済み**
**現状のサイドバー（App.tsx 356–362行目）:**
```tsx
<div className=”z-rotation-row”>
  <button onClick={() => rotate('Z', -1)}>↺</button>
  <span>Z軸</span>
  <button onClick={() => rotate('Z', 1)}>↻</button>
</div>
```
**現状のキーボード**: ←→/WASD → Y軸、↑↓/WS → X軸、Q/E → Z軸、R → リセット
**現状のドラッグ**: PieceStage.tsx で水平=Y、垂直=X（DRAG_THRESHOLD=25px）
**問題**: モバイルはZ軸ボタンしかなく、X/Yはドラッグのみ → 意図しない回転が起きやすい。
**必要な変更**: X/Y のボタンを追加し、3軸すべてを明示的に操作可能にする。

---

### Phase 3 グリッドカーソル — **未実装**
**現状**: ユーザーは 3D ビューア上のアンカーセル（半透明ハイライト）を直接クリックして配置。
**問題**: モバイルで小さいセルに精確にタップするのが困難。意図しない場所に置いてしまう。
**必要な変更**: カーソルで配置候補を選択し、確定ボタンで配置する仕組みを追加。

**モバイル仕様（誤タップ対策）**:
- Mobile（`pointer: coarse`）では 3Dビュー上のアンカーセルタップは「カーソル移動のみ」とし、
  実際の配置は「配置する」ボタンで確定する。
- PC（`pointer: fine`）はアンカークリック即配置を許容（利便性維持）。

実装例:
```ts
const isTouchDevice = window.matchMedia('(pointer: coarse)').matches;
// isAnchor クリック時:
if (isTouchDevice) { moveCursorToAnchor(coord); }  // 移動のみ
else               { handleEmptyCellClick(coord); } // 即配置
```

---

### Phase 4 ピース Anchor — **コードレベルで de facto 実装済み**
`placement.ts` の `refCellOf()` が「min(z,y,x) セル」を擬似アンカーとして使用中。
Phase 3 の「候補サイクル方式」であれば JSON への anchor 追加は **不要**（既存で十分）。
将来「任意グリッドカーソル方式」に移行する場合のみ JSON 拡張を検討。

---

### Phase 5 チュートリアル — **基本実装済み、内容更新が必要**
`TutorialOverlay.tsx` に localStorage フラグ済みオーバーレイが存在。
手順2の説明「WASD/矢印キー/Q/E」は Phase 2 の UI 変更後に更新が必要。

---

# 📐 Detailed Implementation Design（実装設計詳細）

## Phase 1: 固定ブロック半透明化

### 変更ファイル: `PuzzleVoxels.tsx`

**設計**: `selectedPiece` が存在するとき、solid セルの opacity を下げる。

```
selectedPiece あり  → solid opacity: 0.55（半透明）
selectedPiece なし  → solid opacity: 1.0（現状維持）
```

**Props 変更**: 既存の `selectedPiece?: string | null` を流用（追加変更なし）。

**Before / After（イメージ）:**
```tsx
// Before
<meshStandardMaterial color={solidColor} transparent={false} opacity={1} />

// After（まずはこれだけで実装）
const hasSelected = selectedPiece != null;
const solidOpacity = hasSelected ? 0.55 : 1.0;
<meshStandardMaterial
  color={solidColor}
  transparent={hasSelected}
  opacity={solidOpacity}
/>

// 表示が破綻した場合のみ（段階適用）:
// material.depthWrite = false
// mesh.renderOrder = 0 (solid) / 10 (placed) / 20 (ghost) / 30 (active)
```

**描画注意（Three.js）**:
半透明（`transparent=true` + `opacity`）だけでまず実装する。
表示が破綻する場合のみ、以下を段階的に適用する（順番重要）:
1. `depthWrite=false`（半透明同士の前後関係が崩れる場合）
2. `renderOrder` 調整（例: solid=0 < placed=10 < ghost=20 < active=30）

※ `depthWrite=false` は副作用（描画順の違和感）が出ることがあるため必須にはしない。

---

## Phase 2: 回転候補カードUI（姿勢選択）

### 変更ファイル: `App.tsx`, `App.css`, `useGameState.ts`, 新規 `RotationCandidates.tsx`

**コンセプト**: ピース選択中、サイドバーにピースの「ユニーク姿勢カード」を横スクロールで表示。
カードをタップ/クリックすることで姿勢を直接適用する。
ドラッグ回転への依存をなくし、モバイルでの意図しない回転を排除する。

**UI（ワイヤーフレーム）:**
```
┌──────────────── サイドバー ─────────────────┐
│  [▪]  [▪]  [■]  [▪]  [▪]  [▪]  →         │  ← 横スクロール姿勢カード (■=現在選択)
│              3 / 12                          │  ← 選択インジケーター（オプション）
│            [ R リセット ]                    │
└──────────────────────────────────────────────┘
```

**候補の定義:**
- 24方向回転の中から、セル集合が重複するものを除外した「ユニーク姿勢」
- ピースの対称性によって枚数が変わる（最大24、典型的には6〜12枚）
- 候補順: 正規化キー順（v1固定）

**ユニーク姿勢の抽出ロジック（`placement.ts` に追加）:**
```ts
export function uniqueRotationIndices(pieceCells: Vec3[]): number[] {
  const seen = new Set<string>();
  const result: number[] = [];
  for (let i = 0; i < 24; i++) {
    const cells = normalize(applyRotation(pieceCells, i));
    const key = cells.map(([x,y,z]) => `${x},${y},${z}`).sort().join('|');
    if (!seen.has(key)) { seen.add(key); result.push(i); }
  }
  return result;
}
```

**サムネイルレンダリング方針:**
- 1カードあたり小さな R3F `<Canvas>`（48×48px, `frameloop=”demand”`）
- `PieceStage` の Canvas 描画部分だけを切り出した `PieceThumbnail` コンポーネントを新規作成
- 最大24枚だが典型的に6〜12枚 → WebGL コンテキスト数は許容範囲

**`useGameState.ts` 変更:**
```ts
// GameAction に追加
| { type: 'SET_ROTATION'; index: number }

// Reducer:
case 'SET_ROTATION':
  return { ...state, rotationIndex: action.index };
  // Phase 3 実装後: cursorIndex: 0 も追加
```
- 既存の `ROTATE`（axis/step）は **残す**（PC キーボードショートカット用）

**`PieceStage` の扱い（決定: 完全廃止）:**
- `PieceStage.tsx` を使用している箇所をすべて削除（`App.tsx` / Sidebar 等）
- ドラッグ回転（X/Y drag）も同時に廃止
- **理由**: 姿勢選択はカードUIで完結、UIの減少でモバイルの認知負荷と実装コストを削減
- **選択中カードの強調**でカード廃止後も「現在姿勢」を保証する:
  - 選択中カードに枠線 / 背景 / スケール強調
  - R（リセット）で必ず index=0（元姿勢）カードに戻る
  - （任意）選択中カードへ `scrollIntoView` で自動スクロール

**新規 `RotationCandidates.tsx`（概要）:**
```tsx
// サイドバー内で使用
<RotationCandidates
  piece={selectedPiece}
  currentRotIndex={rotationIndex}
  onSelect={(idx) => dispatch({ type: 'SET_ROTATION', index: idx })}
  onReset={resetRotation}
/>
```

**`z-rotation-row` の扱い:**
- `RotationCandidates` コンポーネントに置き換え（完全削除）
- キーボードショートカット（WASD/QE/R）は **残す**（PCユーザー向け）

---

## Phase 3: 配置候補サイクル方式（グリッドカーソル v1）

### 設計方針の決定: **「候補サイクル方式」を採用**

理由: 3D座標ナビゲーション（↑↓←→で x/y/z を移動）より、
「有効配置候補の中を順番に見ていく」方が初心者に直感的で実装リスクも低い。

```
有効配置が 3箇所ある場合:
  [ ← ]  位置 2 / 3  [ → ]
  [    配置する    ]
```

カーソルが指す位置のゴースト → 最も明るく表示。

### 変更ファイル: `useGameState.ts`, `App.tsx`, `PuzzleVoxels.tsx`, `App.css`

#### `useGameState.ts`
```ts
// GameState に追加
cursorIndex: number;   // validAnchorCells の何番目を指しているか (0-based)

// Actions を追加
| { type: 'NEXT_CURSOR' }
| { type: 'PREV_CURSOR' }
| { type: 'SET_CURSOR_INDEX'; index: number }

// SELECT_PIECE 時に cursorIndex: 0 でリセット
// PLACE_PIECE 後に cursorIndex: 0 でリセット
// RESET_ROTATION 時に cursorIndex: 0 でリセット（候補順が変わるため）
```

**カーソルの安定性（UX）**:
- `validAnchorCells` が変化した場合（回転/ピース変更/盤面変化）、
  `cursorIndex` は原則 0 にリセットする（v1 は単純さ優先）。
- 将来改善案: 直前の `cursorAnchorKey` に最も近い候補へスナップ。

#### `App.tsx`
```tsx
// validAnchorCells (Set) を配列に変換して cursorIndex で参照
const sortedAnchors = useMemo(() => {
  if (!validAnchorCells) return [];

  const parseKey = (k: string) => k.split(',').map(Number) as [number, number, number];

  // z → y → x の数値ソート（順番が安定し、ユーザーが理解しやすい）
  return [...validAnchorCells].sort((a, b) => {
    const [ax, ay, az] = parseKey(a);
    const [bx, by, bz] = parseKey(b);
    if (az !== bz) return az - bz;
    if (ay !== by) return ay - by;
    return ax - bx;
  });
}, [validAnchorCells]);
const cursorAnchor: Vec3 | undefined = sortedAnchors[gameState.cursorIndex]
  ?.split(',').map(Number) as Vec3 | undefined;

// カーソル位置に対応するゴーストセル（1placement分）
const cursorGhostCells = useMemo(() => { ... }, [cursorAnchor, ...]);

// 配置ハンドラ（カーソル位置に確定）
const handlePlaceAtCursor = () => {
  if (!cursorAnchor) return;
  handleEmptyCellClick(cursorAnchor);
};

// サイドバーに追加するUI
<div className=”cursor-nav”>
  <button onClick={() => dispatch PREV_CURSOR}>←</button>
  <span>{cursorIndex + 1} / {sortedAnchors.length}</span>
  <button onClick={() => dispatch NEXT_CURSOR}>→</button>
</div>
<button
  className=”place-btn”
  disabled={sortedAnchors.length === 0}
  onClick={handlePlaceAtCursor}
>
  配置する
</button>
```

#### `PuzzleVoxels.tsx`
```ts
// cursorAnchorKey を新 prop として受け取る
// アンカーセルの描画を分岐:
//   cursorAnchorKey と一致 → opacity 0.85（カーソル位置）
//   それ以外のアンカー    → opacity 0.25（存在するがカーソル外）
//   ゴースト             → opacity 0.40（カーソル位置のゴースト）
```

#### キーボード（App.tsx）
```ts
// 既存のキーバインドに追記
case 'ArrowLeft':  case 'a': ... PREV_CURSOR; break;   // 既存の回転と競合 → 検討
case 'ArrowRight': case 'd': ... NEXT_CURSOR; break;
case 'Enter': case ' ': handlePlaceAtCursor(); break;
```

> **競合注意**: ←→/WASD は現在 Y軸回転に割り当て済み。
> Phase 3 実装時に「ピース選択中は ←→ = カーソル移動、ピース未選択時は ビュー操作」
> または別キー（Tab / N / P など）にする方針を決定すること。

---

## Phase 4: Piece Anchor（暫定スキップ）

Phase 3「候補サイクル方式」では `placement.ts` の `refCellOf()` がそのまま利用できるため、
JSON への `anchor` フィールド追加は **現時点で不要**。

将来「任意グリッドカーソル方式」に移行する場合に以下を追加:
```json
// puzzle_*.json の master_pieces 拡張案（後方互換）
{
  “piece”: “A”,
  “cells”: [[0,0,0],[1,0,0],[2,0,0],[0,1,0],[0,0,1]],
  “anchor”: [0, 0, 0]   // ← 追加。未設定なら refCellOf() を使う
}
```

---

## Phase 5: チュートリアル内容更新

### 変更ファイル: `TutorialOverlay.tsx`

Phase 2 完了後、手順 2 の説明を更新:
```
// Before
2. 回転: WASD / 矢印キー (XY軸)、Q / E (Z軸) で回転させます。

// After
2. 回転: サイドバーの姿勢カードをタップして向きを選びます。
         (PC: WASD・Q/E キーでも回転できます)
```

---

# 🗺️ Implementation Order（実装順序と依存関係）

```
Phase 1 (Blur)
  └─ PuzzleVoxels.tsx のみ変更、リスク最小
  └─ 推奨: 最初に実装・確認

Phase 2 (Rotation Card UI)
  └─ placement.ts + useGameState.ts + App.tsx + App.css + 新規 RotationCandidates.tsx
  └─ Phase 1 完了後に着手可
  └─ PieceStage の扱い（廃止 or 維持）を事前に決定すること

Phase 3 (Cursor Cycle)
  └─ useGameState.ts + App.tsx + PuzzleVoxels.tsx
  └─ Phase 2 完了後に着手
  └─ ★ 最も効果が高いが変更範囲も大きい

Phase 5 (Tutorial update)
  └─ Phase 2 完了後に更新（1ファイル・数行）

Phase 4 (Anchor JSON)
  └─ Phase 3 完了後、必要性を再評価してから実施
```

## 変更ファイル一覧サマリ

| Phase | ファイル | 変更種別 |
|---|---|---|
| 1 | `PuzzleVoxels.tsx` | solid セルの opacity 条件追加 |
| 2 | `placement.ts` | `uniqueRotationIndices()` 追加 |
| 2 | `useGameState.ts` | `SET_ROTATION` アクション追加 |
| 2 | `App.tsx` | `z-rotation-row` を `RotationCandidates` に置き換え |
| 2 | `App.css` | `rotation-candidates` スタイル追加 |
| 2 | `RotationCandidates.tsx` | 新規作成（姿勢カードUI） |
| 2 | `PieceStage.tsx` | ドラッグ回転廃止 or コンポーネント廃止（要決定） |
| 3 | `useGameState.ts` | `cursorIndex` + `NEXT/PREV_CURSOR` アクション追加 |
| 3 | `App.tsx` | cursor nav UI + `handlePlaceAtCursor` 追加 |
| 3 | `PuzzleVoxels.tsx` | `cursorAnchorKey` prop + 描画分岐追加 |
| 3 | `App.css` | `cursor-nav` / `place-btn` スタイル追加 |
| 5 | `TutorialOverlay.tsx` | 手順2テキスト更新 |

---

# ✅ Decisions（確定済み方針）

| # | 項目 | 決定内容 |
|---|---|---|
| 1 | Phase 3 カーソルキー | **ボタン専用（v1）** — ←→/WASD は Y軸回転のまま維持 |
| 2 | Phase 3 配置確定 | **PC: 3Dクリック即配置 + 確定ボタン両対応** / **Mobile: 確定ボタン必須** |
| 3 | 候補サイクル順序 | **z→y→x 数値ソート固定**（v1）|
| 4 | PieceStage の扱い | **完全廃止**（表示もドラッグも撤去、カードUIに一本化）|
| 5 | サムネイル描画方式 | **小 R3F Canvas（48×48px, `frameloop="demand"`）** |
📘 P1-05: Interactive Rotation & Placement Core RunBook
title: "P1-05 Rotation & Placement Core"
version: "1.0.0"
owner: "SoChi-lab Frontend"
status: "design-approved"
goal: "SoChi BLOCKS を '領域当て' から '本格3D配置ゲーム' に進化させる"
🎯 目的

24回転を安全に実装（手書き禁止）

回転状態をゲーム状態に統合

オートアンカー方式で配置判定

数学的に正しい回転群を保証

UIより先にロジックを完全固定

🧠 設計思想（絶対守る）

24回転は手書き禁止

ロジックと表示を分離

正規化して比較

すべてテストで保証

回転は index 管理

📁 ファイル構成
frontend/src/utils/
    rotations.ts
    placement.ts
    geometry.ts (helper)

frontend/src/utils/__tests__/
    rotations.test.ts
    placement.test.ts
🧮 Part 1: 24回転の安全な生成戦略
❌ やってはいけない

24個の行列を手書き

Wikipediaからコピペ

✅ 正しい生成法
アルゴリズム
1. newZ として ±X, ±Y, ±Z → 6通り
2. newY として newZ に直交する軸 → 4通り
3. newX = cross(newY, newZ)
4. 行列を生成
5. Setでユニーク化 → 24になること確認

6 × 4 = 24

rotations.ts 仕様
型
export type Vec3 = [number, number, number]
export type Mat3 = [
  [number, number, number],
  [number, number, number],
  [number, number, number]
]
必須API
export const ROTATION_MATRICES: Mat3[]

export function applyRotation(
  cells: Vec3[],
  rotIndex: number
): Vec3[]

export function normalize(
  cells: Vec3[]
): Vec3[]

export function rotateIndex(
  current: number,
  axis: 'X' | 'Y' | 'Z',
  dir: 1 | -1
): number
rotateIndex 設計
基本思想

R_x90, R_y90, R_z90 の3つだけ固定

次状態 = R_axis × currentMatrix

key検索でインデックス取得

必須テスト（rotations.test.ts）

 length === 24

 det === +1

 直交（M^T M = I）

 ユニーク

 閉包性

 rotateIndex往復性

 整数格子保持

🧩 Part 2: オートアンカー配置判定
placement.ts 仕様
export function canPlace(
  pieceCells: Vec3[],
  rotIndex: number,
  clickedCell: Vec3,
  emptyCells: Vec3[]
): boolean
判定アルゴリズム
1. 回転適用
2. normalize
3. for each cell in rotatedPiece:
      offset = clickedCell - cell
      translated = rotatedPiece + offset
      if 全セルが emptyCells に含まれる:
           return true
4. return false
注意点

emptyCells は Set<string> にする

normalize は回転直後のみ

座標比較は文字列キー化

必須テスト（placement.test.ts）

正しい回転でtrue

間違い回転でfalse

エリア違いでfalse

対称ピースでもtrue

🧠 Part 3: Game State統合

useGameState.ts に追加：

rotationIndex: number

アクション：

{ type: 'ROTATE'; axis: 'X' | 'Y' | 'Z'; dir: 1 | -1 }

SELECT_PIECEでrotationIndex = 0

🎮 Part 4: UI方針（ゲーム特化）

プレビューはドラッグ回転

ボタンは補助

正解時に吸い込まれるアニメ

不正解時はシェイク

🚀 実装フェーズ
Phase 1

rotations.ts + tests 完成

Phase 2

placement.ts + tests 完成

Phase 3

useGameState 統合

Phase 4

UI統合

🔥 ゲーム化の本質

この設計で変わるもの：

思考負荷が空間理解へ移行

子供も大人も本気で考える

クリアの快感が生まれる

Instagram導線が「本物」になる

🛡 バグ防止チェックリスト

ロジックとThree.js座標系を混ぜない

24回転は生成のみ

Set比較必須

テストなしでUIに入らない

🎯 完了定義

tsc エラーゼロ

vitest 全通過

全ピース配置でクリア

🧠 戦略的意味

これが完成すると：

SoChi BLOCKSは

「教材」ではなく
「知的3Dゲームエンジン」になる
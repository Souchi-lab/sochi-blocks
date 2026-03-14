# SoChi BLOCKS — アクセス解析運用ガイド

## 1. 測定IDの設定方法

**変更が必要な箇所は2つ（同じIDを設定する）:**

### A. Viewer アプリ（React）
```
frontend/src/constants/siteConfig.ts
```
```typescript
export const GA4_ID = 'G-XXXXXXXXXX'; // ← 実際のIDに差し替える
```
差し替え後に **ビルドが必要**:
```bash
npm run build --prefix frontend
```

### B. ランディングページ（静的HTML）
```
docs/index.html
```
`G-XXXXXXXXXX` を2箇所（script src と gtag config）に書かれているので両方差し替える。ビルド不要、そのまま GitHub Pages に反映される。

---

## 2. イベント一覧

| イベント名 | 発火条件 | 送信パラメータ | 実装箇所 |
|-----------|---------|--------------|---------|
| `puzzle_open` | パズルデータ読み込み完了時 | puzzle_id, difficulty, piece_count, source_page | `App.tsx` useEffect |
| `puzzle_start` | 最初のピース選択時（1回のみ） | puzzle_id, difficulty, piece_count, source_page | `App.tsx` handleSelectPiece |
| `puzzle_complete` | 全ピース配置完了時 | puzzle_id, difficulty, piece_count, clear_seconds, source_page | `App.tsx` useEffect |
| `difficulty_select` | パズルカードをクリックした時 | difficulty, puzzle_id, source_page | `docs/index.html` (event delegation) |
| `tutorial_start` | チュートリアルモーダル表示時 | source_page | `TutorialOverlay.tsx` useEffect |
| `next_puzzle` | 「Next Puzzle →」ボタン押下時 | from_puzzle_id, to_puzzle_id, difficulty, source_page | `VictoryOverlay.tsx` onClick |

### パラメータ定義

| パラメータ | 説明 |
|-----------|-----|
| `puzzle_id` | パズルID（例: `20260312_004`）|
| `difficulty` | `Easy` / `Medium` / `Hard` / `Hardest` |
| `piece_count` | 除去ピース数（2 / 4 / 6 / 8）|
| `clear_seconds` | puzzle_start から puzzle_complete までの秒数 |
| `source_page` | `location.pathname` の値 |

---

## 3. GA4 DebugView での確認方法

1. Chrome の [Google Analytics Debugger 拡張](https://chrome.google.com/webstore/detail/google-analytics-debugger) を有効化
2. GA4 管理画面 → 「DebugView」を開く
3. `?debug=1` を URL に付けてアクセス（または拡張が有効なら自動）
4. 以下のフローで確認する:

```
index.html を開く
  → page_view イベントが入ること

パズルカードをクリック
  → difficulty_select イベントが入ること（difficulty, puzzle_id パラメータ確認）

viewer.html でパズルが読み込まれる
  → puzzle_open イベントが入ること

ピースを選択する
  → puzzle_start イベントが入ること（一度だけ）

全ピースを配置してクリア
  → puzzle_complete イベントが入ること（clear_seconds パラメータ確認）

「ヘルプ」ボタンからチュートリアルを開く
  → tutorial_start イベントが入ること

「Next Puzzle →」をクリック
  → next_puzzle イベントが入ること
```

---

## 4. UTM 付き URL の使い方

SNS 投稿からの流入を計測するには、リンクに UTM パラメータを付ける。

### 例

**Instagram Reel → 最新Easy パズル:**
```
https://souchi-lab.github.io/sochi-blocks/viewer.html?puzzle_id=20260314_001&utm_source=instagram&utm_medium=reel&utm_campaign=daily_puzzle_20260314
```

**TikTok → トップページ:**
```
https://souchi-lab.github.io/sochi-blocks/?utm_source=tiktok&utm_medium=video&utm_campaign=daily_puzzle_20260314
```

### GA4 での確認
- 「集客」→「トラフィック獲得」→ UTM 別セッション数を確認
- UTM パラメータは GA4 が自動で収集するため、追加実装は不要

---

## 5. 重要な分析軸

以下の観点で GA4 のファネル・探索レポートを活用する:

### puzzle_open → puzzle_start の変換率
「開いたがゲームを始めていない」ユーザーを特定。
改善仮説: チュートリアルが多すぎる、UI が分かりにくい、など。

### puzzle_start → puzzle_complete の変換率（難易度別）
難易度ごとのクリア率。Easy でも低い場合はルールが伝わっていない可能性。

### clear_seconds の分布
「早すぎる（バグ？）」「長すぎる（詰まっている）」を把握。

### SNS 流入 → puzzle_open の転換率
`utm_source=instagram/tiktok` のユーザーがパズルを開いているかを確認。

---

## 6. イベントの追加方法

1. `frontend/src/utils/analytics.ts` の末尾に `trackXxx()` 関数を追加（既存パターンをコピー）
2. 発火させたいコンポーネントや `App.tsx` から `trackXxx()` を呼ぶ
3. このファイルのイベント一覧テーブルを更新する
4. `npm run build --prefix frontend` でビルドして確認

### 関数テンプレート

```typescript
export function trackXxx(params: {
  paramA: string;
  paramB?: number;
}): void {
  trackEvent('xxx_event_name', {
    param_a: params.paramA,
    param_b: params.paramB,
    source_page: location.pathname,
  });
}
```

---

## 7. 開発時の動作確認

`npm run dev --prefix frontend` で起動した場合、gtag は実際には送信されない（`GA4_ID` が `G-XXXXXXXXXX` のまま）。

代わりに、ブラウザのコンソールに以下のデバッグ出力が表示される:

```
[analytics] puzzle_open { puzzle_id: '20260312_004', difficulty: 'Easy', ... }
[analytics] puzzle_start { puzzle_id: '20260312_004', ... }
```

本番 ID を設定してビルドした場合でも、広告ブロッカーが有効な場合は送信されないが、ゲームの動作には影響しない。

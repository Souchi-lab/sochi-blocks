# UX 改善 RUNBOOK — SoChi BLOCKS

> 初見ユーザーが「何のサイトか」「どう遊ぶか」をすぐ理解でき、
> 最初の 1 問まで迷わず到達できる状態を作るための実装手順書。

**作成日**: 2026-03-14
**対象**: `docs/index.html`（トップ）、`frontend/src/` 以下（ゲーム画面）

---

## 現状分析（実装前の確認）

### docs/index.html（トップページ）

| 項目 | 現状 | 課題 |
|------|------|------|
| ヒーローCTA | 「パズルを選ぶ ↓」→ ページ内 #puzzles へ | 一覧から迷う。最初の1問への直接導線がない |
| 難易度カード | ピース数の数字のみ | 体感難易度・目安時間が伝わらない |
| About セクション | How to Play の直後（上部） | 読む量が多く、「遊ぶ前に読まされる」 |
| Loading 表示 | テキストのみ | 未完成感がある |
| 言語切替 | **すでに実装済み** (JP/EN トグル) | ✅ 対応済み |

### frontend/src/App.tsx（ゲーム画面）

| 項目 | 現状 | 課題 |
|------|------|------|
| 操作ラベル | `Set` ボタン、矢印 `←→`、ショートカット表示 | Rotate / Move / Place の概念が分かりにくい |
| 選択状態表示 | `Piece X` ラベルあり | フィット可否が色以外で伝わらない |
| Undo | `onUnplace` 実装済み（トレイから） | ボタンとして目立っていない |
| Reset | `handleRestart` 実装済み | VictoryOverlay でしか見えない |
| チュートリアル | `TutorialOverlay.tsx` 静的説明あり | 実際のUIをハイライトする仕組みなし |
| クリア演出 | `VictoryOverlay.tsx` でタイム・ミス数表示 | 次の問題への導線が「Play Again」のみ |
| ゴースト表示 | `cursorGhostKeys` 実装済み | ✅ 対応済み |
| ミス数表示 | `mistakeCount` ヘッダー表示あり | ✅ 対応済み |

---

## Phase 1: 最優先の導線改善（P0）✅ 実施済み（2026-03-14）

### 目的

トップページを見た瞬間に「これは何か・面白そうか・すぐ遊べるか」が伝わる状態にする。

### 変更対象ファイル

- `docs/index.html`（主要変更）

---

### Task 1-1: ヒーローセクションに「最初の1問」CTAを追加 ✅

**変更対象**: `docs/index.html` — `.hero` セクション内

**現状**:
```html
<a class="hero-cta" href="#puzzles">パズルを選ぶ ↓</a>
```

**変更内容**:
- メインCTA「まず1問やってみる」→ 最新のEasy問題に直接リンク
- サブCTA「遊び方を見る」→ How to Play セクションへのスクロール
- CTA 生成を JS で行い、manifest.json の最新 Easy を動的に参照する

**実装詳細**:

1. Hero の CTA を2ボタン構成に変更
2. JS で manifest.json を fetch し、最新 Easy 問題の `id` を取得
3. `href` を `./viewer.html?puzzle_id=<id>` に設定
4. manifest fetch 完了前は「読み込み中...」をボタンに表示（disabled 状態）

**UI構成**（ファーストビュー順序）:
```
[SoChi BLOCKS ロゴ]（ヘッダーに移動済み）
[ヒーロータイトル: SoChi BLOCKS]
[サブタイトル: think in 3D]
[説明文: 3Dで考えるペントミノパズル]（1行に圧縮）
[ボタン1: まず1問やってみる]  ← メインCTA（大）
[ボタン2: 遊び方を見る]       ← サブCTA（小）
```

**確認ポイント**:
- [ ] ボタン1クリックで viewer.html の Easy 問題に遷移する
- [ ] ボタン2クリックでHow to Playセクションにスクロールする
- [ ] manifest fetch 中はボタンが適切な状態になっている
- [ ] スマホ幅でボタンが縦並びになる

---

### Task 1-2: 「はじめての人へ」セクションを追加 ✅

**変更対象**: `docs/index.html` — How to Play セクションの直前に挿入

**変更内容**:
- `section-title` で「はじめての方へ / For First-Timers」
- Easy 問題への直接リンクカード（1枚）
- 「まず Easy から始めるのがおすすめです」のコピー

**UIイメージ**:
```
[はじめての方へ]
┌─────────────────────────────────────┐
│  Easy  最初の1問を解いてみよう      │
│  ピース2個・1〜3分                  │
│                         [遊んでみる →] │
└─────────────────────────────────────┘
```

**実装詳細**:
- JS で manifest から最新 Easy を取得し、カードの href を動的設定
- カードは `puzzle-card` の既存スタイルを流用 or 新スタイル

**確認ポイント**:
- [ ] カードクリックで直接 viewer.html に遷移する
- [ ] 日英切替が機能する

---

### Task 1-3: トップ説明量を圧縮・セクション順序を変更 ✅

**変更対象**: `docs/index.html` — コンテンツ構造全体

**現状の順序**:
1. ヒーロー（説明文あり）
2. How to Play
3. **About（作者ストーリー）**  ← 上すぎる
4. Puzzle 一覧

**変更後の順序**:
1. ヒーロー（説明文を1行に圧縮）
2. **はじめての方へ**（Task 1-2で追加）
3. How to Play（既存）
4. Difficulty Guide（既存、Task 1-4で強化）
5. Puzzle 一覧
6. **About**（最下部に移動）

**変更詳細**:
- Hero の `hero-desc` を1〜2行に圧縮
  - JA: `3Dで考えるペントミノパズル`
  - EN: `A 3D pentomino puzzle`
- About ブロックを puzzle 一覧の下に移動
- About の前に `section-title` で「About / このゲームについて」を追加

**確認ポイント**:
- [ ] ファーストビューで説明が1行に収まっている
- [ ] About が下部に移動している
- [ ] スクロールしないと About が見えない

---

### Task 1-4: 難易度カードに体感情報を追加 ✅

**変更対象**: `docs/index.html` — `.diff-guide` セクション

**現状**:
```html
<div class="diff-card">
  <span class="diff-badge diff-easy">Easy</span>
  <div class="diff-pieces ja">ピース 2 個</div>
  <div class="diff-pieces en">2 pieces missing</div>
</div>
```

**変更後（各カードに追加する情報）**:

| 難易度 | 対象者 | 目安時間 | 説明（JA） | 説明（EN） |
|--------|--------|---------|-----------|-----------|
| Easy | 初めての方 | 1〜3分 | 2ピースを埋める。まずここから | 2 pieces. Start here |
| Medium | 慣れてきたら | 3〜8分 | 4ピース。少し悩む | 4 pieces. Gets tricky |
| Hard | 本格的に | 10〜20分 | 6ピース。手応えあり | 6 pieces. Real challenge |
| Hardest | 上級者向け | 30分〜 | 8ピース。全集中 | 8 pieces. Expert only |

**UIイメージ**（Easy カード例）:
```
┌──────────────────┐
│ [Easy]           │
│ 初めての方向け   │
│ 1〜3分           │
│ 2ピースを埋める  │
│ まずここから     │
└──────────────────┘
```

**実装詳細**:
- `.diff-card` に `diff-target`（対象者）、`diff-time`（目安時間）、`diff-desc`（説明）を追加
- CSS で各要素のフォントサイズ・色を設定
- 既存の `diff-pieces`（ピース数）は削除または補足として保持

**確認ポイント**:
- [ ] 4カードが横並び（デスクトップ）・2列（スマホ）になっている
- [ ] 各カードに目安時間と説明が表示されている
- [ ] 日英切替が機能する

---

### Task 1-5: パズル一覧のスケルトンUI追加 ✅

**変更対象**: `docs/index.html` — `#puzzle-root` の初期HTML、および CSS

**現状**:
```html
<div id="puzzle-root">
  <div class="status">読み込み中...</div>
</div>
```

**変更後**:
- 仮カード（スケルトン）を 3〜5 枚表示
- CSS で shimmer アニメーションを適用
- manifest fetch 完了後に実カードで置換

**スケルトンカードの構造**:
```html
<div class="puzzle-card skeleton">
  <div class="sk-badge"></div>
  <div class="sk-info">
    <div class="sk-line sk-line-long"></div>
    <div class="sk-line sk-line-short"></div>
  </div>
</div>
```

**CSS**:
```css
.skeleton { pointer-events: none; }
.sk-badge, .sk-line {
  background: linear-gradient(90deg, #eee 25%, #f5f5f5 50%, #eee 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  border-radius: 6px;
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

**確認ポイント**:
- [ ] ページ読み込み中にスケルトンが表示される
- [ ] 読み込み完了後に実カードに切り替わる
- [ ] スマホでも自然に見える

---

### Phase 1 完了確認チェックリスト

```
✅ ファーストビューに「まず1問やってみる」CTAがある
✅ CTAが最新のEasy問題に直接リンクしている
✅ 「はじめての方へ」セクションがHow to Playの前にある
✅ ヒーロー説明文が1〜2行に収まっている
✅ About セクションがパズル一覧の下に移動している
✅ 難易度カードに対象者・目安時間・説明が入っている
✅ ローディング中にスケルトンUIが表示される
✅ 日英切替が全セクションで動作する
✅ スマホ（375px幅）で表示崩れがない（メディアクエリ調整済み）
```

**結果**: 全項目✅ 確認完了（2026-03-14）
参照: `docs/UX_VERIFICATION_RESULTS.md`

**→ Phase 2 へ移行**

---

## Phase 2: 言語と情報密度の改善（P1）✅ 実施済み（2026-03-14）

### 目的

情報量が多く見える問題を解消し、読みやすくする。

### 備考

**Phase 1 の実装時に同時完了**。個別の追加コード変更なし。

---

### Task 2-1: 言語トグルの動作確認・強化 ✅

Phase 1 で追加した全要素（hero-cta-group・first-puzzle-card・diff-card・About セクションタイトル・動的生成カード）の `ja`/`en` クラス網羅を確認済み。漏れなし。

---

### Task 2-2: 作者ストーリーの位置調整・文言整理 ✅

- About セクション → パズル一覧の下に移動済み（Task 1-3 で実施）
- セクションタイトル「このゲームについて / About」追加済み（Task 1-3 で実施）
- 日英切替対応済み

---

### Phase 2 完了確認チェックリスト

```
✅ Phase 1 で追加した全テキストが JP/EN 切替に対応している
✅ About セクションがパズル一覧の下にある
✅ About セクションにセクションタイトルがある
✅ 情報の流れ: Hero → はじめての方へ → How to Play → 難易度 → 一覧 → About
```

**結果**: Phase 1 実装時に同時完了（2026-03-14）

**→ Phase 3 へ移行**

---

## Phase 3: ゲーム画面の操作理解改善（P1）✅ 実施済み（2026-03-14）

### 目的

操作方法が頭の中で組み立てにくい問題を減らす。

### 変更対象ファイル

- `frontend/src/App.tsx`（placement-overlay, sidebar）
- `frontend/src/App.css`（スタイル）
- `frontend/src/components/TutorialOverlay.tsx`（チュートリアル改善）

---

### Task 3-1: 配置操作UIのラベルを明確化 ✅

**変更対象**: `frontend/src/App.tsx` — `.placement-overlay` ブロック（L298〜L328）

**現状**:
```tsx
<button className="cursor-nav-btn" onClick={...}>←</button>
<span className="cursor-nav-count">1 / 3</span>
<button className="cursor-nav-btn" onClick={...}>→</button>
<button className="place-btn" disabled={...} onClick={handlePlaceAtCursor}>Set</button>
```

**変更後**:
```tsx
<div className="placement-section">
  <div className="placement-label">配置位置</div>  {/* "Position" */}
  <div className="placement-nav">
    <button className="cursor-nav-btn" ...>← Prev</button>
    <span className="cursor-nav-count">1 / 3</span>
    <button className="cursor-nav-btn" ...>Next →</button>
  </div>
</div>
<button className="place-btn" ...>
  ✓ Place  {/* アイコン付き */}
</button>
```

**補足**: RotationControls は現在 `useGameState` の `setRotation` 経由で直接 index 変更しているため、
サイドバーの `RotationCandidates` コンポーネントがメインの回転UIとなっている。
サイドバー上部の `drag-hint` テキスト (`WASD · Q/E · R · Enter`) に、
以下のラベルを付ける:

```tsx
<div className="controls-hint-group">
  <div className="controls-hint-label">Rotate</div>
  <span className="hint-kbd">WASD · Q/E</span>
  <div className="controls-hint-label">Move Position</div>
  <span className="hint-kbd">R</span>
  <div className="controls-hint-label">Place</div>
  <span className="hint-kbd">Enter</span>
</div>
```

**確認ポイント**:
- [ ] 「← Prev / Next →」でナビゲーションの意味が伝わる
- [ ] Place ボタンのアイコン・文言が明確
- [ ] キーボードショートカットにラベルが付いている
- [ ] スマホでショートカット表示が邪魔にならない（PC のみ表示）

---

### Task 3-2: 状態フィードバックの強化 ✅

**変更対象**: `frontend/src/App.tsx` — `.game-middle` 内

**現状**: `Piece X` ラベルと `RotationCandidates`、`isFitting` の状態は内部にある。

**追加する状態表示**:

1. **配置可否バナー**: ピース選択中に「この向きでは置けません / 置けます」を表示

```tsx
{gameState.selectedPiece && (
  <div className={`fit-status ${isFitting ? 'fit-ok' : 'fit-ng'}`}>
    {isFitting
      ? `✓ ${sortedAnchors.length} 箇所に置けます`
      : '✗ この向きでは置けません'}
  </div>
)}
```

2. **ピース未選択時のガイド**: 何も選んでいないときにトレイを指示する

```tsx
{!gameState.selectedPiece && gameState.phase === 'playing' && (
  <div className="guide-hint">
    ↓ ピースを選んでください
  </div>
)}
```

**CSS で追加するスタイル**:
```css
.fit-status { padding: 6px 12px; border-radius: 8px; font-size: 0.82rem; font-weight: 700; }
.fit-ok { background: #e6f9ee; color: #1a7f45; }
.fit-ng { background: #fde8e8; color: #b91c1c; }
```

**確認ポイント**:
- [ ] ピース選択時に配置可否が色とテキストで表示される
- [ ] 向き変更に連動して表示が更新される
- [ ] ピース未選択時にガイドが表示される

---

### Task 3-3: Undo / Reset を常設ボタンとして追加 ✅

**変更対象**: `frontend/src/App.tsx` — ゲームサイドバー下部

**現状**:
- `handleUnplace` → トレイのピースをクリックで発動（非明示的）
- `handleRestart` → VictoryOverlay の「Play Again」のみ

**変更内容**: サイドバー末尾（`.missing-section` の下）に常設ボタンを追加

```tsx
{isGameMode && (
  <div className="game-actions">
    <button
      className="action-btn action-undo"
      onClick={() => {
        const lastPlaced = [...gameState.placedPieces].pop();
        if (lastPlaced) handleUnplace(lastPlaced);
      }}
      disabled={gameState.placedPieces.size === 0}
    >
      ↩ Undo
    </button>
    <button
      className="action-btn action-reset"
      onClick={handleRestart}
    >
      ↺ Reset
    </button>
  </div>
)}
```

**注意**: `useGameState` の `placedPieces` は `Set<string>` なので、最後に置いたピースの取得は
`[...gameState.placedPieces]` で配列変換してから `pop()` する（追加順序を保持）。
`useGameState` の reducer で `placedPieces` が配列順序を維持しているかを確認してから実装する。

**CSS**:
```css
.game-actions { display: flex; gap: 8px; margin-top: 8px; }
.action-btn { flex: 1; padding: 8px; border-radius: 8px; font-size: 0.82rem; font-weight: 700; border: 1px solid #ddd; background: #f8f8f8; cursor: pointer; }
.action-btn:hover { background: #eee; }
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.action-undo { color: #1a56db; }
.action-reset { color: #b91c1c; }
```

**確認ポイント**:
- [ ] Undo ボタンが常時表示されている
- [ ] Reset ボタンが常時表示されている
- [ ] Undo は placedPieces が空のとき disabled
- [ ] Undo 後にゲーム状態が正しく戻る

---

### Task 3-4: ゲーム内インタラクティブチュートリアルの強化 ✅

**変更対象**: `frontend/src/components/TutorialOverlay.tsx`

**現状**: 静的テキスト説明の 3 ステップ。画面 UI のハイライトなし。

**変更内容**:

1. TutorialOverlay をステップ式に変更（現在の 3 ステップそのまま）
2. 各ステップでハイライトターゲットのセレクタを定義
3. 「ここを見て」という矢印インジケーターを追加（CSS で実装）

**実装方針（複雑すぎない範囲で）**:

- `step` ステート（0, 1, 2）を追加
- 各ステップで説明テキストを切り替え
- 各ステップに対応するハイライトクラスを `document.body` に付与
  - `step-0`: `body.tutorial-step-0` → `.missing-section` をハイライト
  - `step-1`: `body.tutorial-step-1` → `.game-middle` をハイライト
  - `step-2`: `body.tutorial-step-2` → `.placement-overlay` をハイライト
- ハイライトは CSS `box-shadow: 0 0 0 4px rgba(59,130,246,0.5)` で表現
- TutorialOverlay の外側（overlay）は `pointer-events: none` にして 3D 操作を妨げない

**ステップUI**:
```
[Step 1 / 3]  ← Next →
┌──────────────────────────────────┐
│  ① ピースを選ぶ                  │
│  画面下のトレイからタップして選択 │
└──────────────────────────────────┘
[スキップ]            [次へ]
```

**確認ポイント**:
- [ ] 初回アクセス時のみ自動表示される
- [ ] スキップボタンで即時閉じられる
- [ ] Next/Prev でステップ移動できる
- [ ] 各ステップで対応する UI 要素がハイライトされる（ぼんやりと）
- [ ] チュートリアル表示中も3D は操作できる

---

### Phase 3 完了確認チェックリスト

```
✅ 配置ボタンが「← Prev / Next →」「✓ Place」になっている
✅ ショートカットに Rotate / Move / Place のラベルがある（PC表示）
✅ 配置可否が色とテキストで表示される（fit-ok / fit-ng バナー）
✅ ピース未選択時に「ピースを選んでください ↓」が出る
✅ Undo / Reset が常時表示されている
✅ Undo は placedPieces が空のとき disabled
✅ チュートリアルが 3 ステップ式になっている（ドット・Prev/Next・スキップ）
✅ 各ステップに「どこを見るか」のヒントがある
✅ 最後のステップで「はじめる！」ボタンが出る
✅ スマホ（375px幅）で表示崩れがない（浮遊パネルのメディアクエリ追加済み）
✅ 英語版（lang=en）の動的テキストも多言語対応済み
```

**結果**: 全項目✅ 確認完了（2026-03-14）
参照: `docs/UX_VERIFICATION_RESULTS.md`

### 検証時の特記事項・追加修正

- **レスポンシブ**: 375px幅で浮遊パネルのボタンが重なる問題 → メディアクエリで解消
- **多言語**: 動的バナー（配置可否等）の日英切替を `lang` URLパラメータ対応に修正
- **バック遷移**: `← Back` を `lang` に応じて `← 戻る` に切り替え対応済み

---

## Phase 3.1: サイドバーUI最適化（ユーザー提案）✅ 実施済み（2026-03-14）

> **提案**: モバイルの垂直スペース不足を解消するため、
> サイドバーを「トレイ ↔ プレビュー」のトグル方式に変更する。

### 課題

モバイル環境でサイドバーの縦スペースが不足。
ピース未選択時（トレイ表示）とピース選択時（回転プレビュー）が
同時に表示されるため窮屈になる。

### 解決策

- ピース**未選択時**: トレイのみ表示
- ピース**選択時**: トレイを隠し、プレビューエリアを大きく表示
- プレビューエリアに「×」ボタンを追加し、選択解除してトレイに戻れるようにする

### 変更対象ファイル

- `frontend/src/App.tsx` — サイドバー切り替えロジック
- `frontend/src/App.css` — サイドバーのレイアウト調整

### タスク

#### Task 3.1-1: トレイ ↔ プレビュー 排他表示 ✅

**変更内容**:

1. ピース未選択時 → `missing-section`（トレイ）を表示、`game-middle` を非表示
2. ピース選択時 → `game-middle` を表示、`missing-section` を非表示（またはコンパクト化）
3. `game-middle` に「× 選択解除」ボタンを追加
   ```tsx
   <button className="piece-deselect-btn" onClick={() => selectPiece(gameState.selectedPiece!)}>
     × 解除
   </button>
   ```
   ※ `selectPiece` は同じピースを渡すとトグルでnullになる（既存の `SELECT_PIECE` reducer の動作）

**実装詳細**:
- `aside` に `.sidebar--piece-selected` クラスをピース選択時に付与
- `game-middle-header` に「× 解除」ボタン追加（`selectPiece` トグルで解除）
- `@media (max-width: 767px)` で `.sidebar--piece-selected .missing-section { display: none }`
- PC（≥ 768px）はトレイとプレビューを両方表示のまま（変更なし）

**確認ポイント**:
- [ ] ピース未選択時はトレイだけが見える（モバイル）
- [ ] ピース選択時はプレビューが大きく見える（モバイル）
- [ ] 「×」ボタンでトレイに戻れる
- [ ] PCレイアウトは変更なし

### Task 3.1-2: 切替時のちらつき修正 ✅

**原因**: サイドバーの高さが切替時に変わる（`max-height` 依存）ことでレイアウトジャンプが発生。

**修正内容**:
- `.game-sidebar` を `height: 45dvh; overflow: hidden` に変更（固定高さ）
- PC media query に `height: auto` を追加してリセット
- `.missing-section` に `overflow-y: auto; flex: 1` を追加（内側スクロール担当）
- `.game-middle` に `animation: sidebar-panel-fade 0.15s` を追加（フェードイン）

**結果**: 高さ変動なし → ちらつき・ジャンプ解消。確認済み（2026-03-14）

---

## Phase 4: UX 補助機能の追加（P2）✅ 実施済み（2026-03-14）

### 目的

難しいけど気持ちよく続けられる体験にする。

### 変更対象ファイル

- `frontend/src/components/VictoryOverlay.tsx`（次の問題への導線）
- `frontend/src/App.tsx`（次の問題取得ロジック）
- `docs/index.html`（ゴースト表示トグル — 不要なら省略可）

---

### Task 4-1: VictoryOverlay に「次の問題」ボタンを追加 ✅

**変更対象**: `frontend/src/components/VictoryOverlay.tsx`

**現状**:
```tsx
<div className="victory-actions">
  <button onClick={onRestart}>Play Again</button>
  <button onClick={onViewSolution}>View Solution</button>
</div>
```

**変更後**:
```tsx
<div className="victory-actions">
  <button onClick={onRestart}>Play Again</button>
  {nextPuzzleId && (
    <a className="victory-next" href={`./viewer.html?puzzle_id=${nextPuzzleId}`}>
      Next Puzzle →
    </a>
  )}
  <button onClick={onViewSolution}>View Solution</button>
</div>
```

**実装詳細**:
- `VictoryOverlay` に `nextPuzzleId?: string` prop を追加
- `App.tsx` で manifest を fetch し、現在のパズルの次のIDを計算して渡す
- manifest はソート済み（新しい順）なので、現在IDのインデックス+1 が次の問題
  - ただし同一難易度 or Easy→Medium→Hard... の順序は検討
  - シンプルに「同じ日付の次の問題、なければ翌日のEasy」とする

**確認ポイント**:
- [ ] クリアしたらVictoryOverlayに「Next Puzzle →」が表示される
- [ ] クリックで次の問題に遷移する
- [ ] 最後の問題の場合は表示されない（または一覧に戻る）

---

### Task 4-2: クリア達成感の強化 ✅

**変更対象**: `frontend/src/components/VictoryOverlay.tsx`、CSS

**現状**: 絵文字・タイム・ミス数の静的表示。

**追加内容**:
1. タイム表示をフォーマット改善（`1:23` 形式）
2. ミス0の場合の強調表示
3. クリア時のアニメーション（CSS のみ、JS animation API は使わない）

**実装詳細**:

タイムフォーマット用ユーティリティ（`App.tsx` または `VictoryOverlay.tsx` 内）:
```ts
function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, '0')}`;
}
```

CSS アニメーション:
```css
.victory-card {
  animation: victoryPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes victoryPop {
  from { opacity: 0; transform: scale(0.85); }
  to   { opacity: 1; transform: scale(1); }
}
```

ミス0強調:
```tsx
{mistakeCount === 0 && (
  <div className="victory-perfect">Perfect!</div>
)}
```

**確認ポイント**:
- [ ] タイムが `1:23` 形式で表示される
- [ ] ミス0のときに Perfect! が表示される
- [ ] カード出現時にポップアニメーションがある
- [ ] アニメーションが過剰でない

---

### Task 4-3: ローカルストレージへのクリア記録保存 ✅

**変更対象**: `frontend/src/App.tsx`

**変更内容**:
- クリア時（`gameState.phase === 'victory'` 遷移）にローカルストレージへ記録
- キー: `sochi_clears`
- 値: `{ [puzzleId]: { time: ms, mistakes: n, date: ISO } }` の JSON

**実装**:
```ts
// victory 遷移時の useEffect 内
if (gameState.phase === 'victory') {
  const key = 'sochi_clears';
  const prev = JSON.parse(localStorage.getItem(key) ?? '{}');
  const existing = prev[id];
  // ベストタイムのみ更新
  if (!existing || clearTimeMs < existing.time) {
    prev[id] = { time: clearTimeMs, mistakes: gameState.mistakeCount, date: new Date().toISOString() };
    localStorage.setItem(key, JSON.stringify(prev));
  }
}
```

**確認ポイント**:
- [ ] クリア後に localStorage に記録される
- [ ] 同じパズルを再クリアした場合ベストタイムのみ更新される
- [ ] DevTools で確認できる

---

### Task 4-4: パズル一覧にクリア済みバッジを追加 ✅

**変更対象**: `docs/index.html` — `renderGroup` 関数

**変更内容**:
- localStorage の `sochi_clears` を読み込む
- クリア済みのパズルカードに ✓ バッジを表示

```js
const clears = JSON.parse(localStorage.getItem('sochi_clears') ?? '{}');

// renderGroup 内
const cleared = clears[p.id] ? '<span class="cleared-badge">✓</span>' : '';
return `
  <a class="puzzle-card ${clears[p.id] ? 'puzzle-cleared' : ''}" href="${url}">
    ${diffBadge(p.difficulty)}
    <div class="card-info">
      <div class="card-id">${p.id} ${cleared}</div>
      ...
    </div>
    <span class="card-arrow">›</span>
  </a>`;
```

**CSS**:
```css
.cleared-badge { font-size: 0.8rem; color: #1a7f45; font-weight: 700; margin-left: 6px; }
.puzzle-cleared { border-left: 3px solid #1a7f45; }
```

**確認ポイント**:
- [ ] クリア済みパズルに ✓ が表示される
- [ ] 未クリアパズルに影響しない

---

### Phase 4 完了確認チェックリスト

```
□ VictoryOverlay に「Next Puzzle」ボタンがある
□ タイムが分:秒 形式で表示される
□ ミス0のとき Perfect! が表示される
□ クリア時にポップアニメーションがある
□ localStorage にクリア記録が保存される
□ パズル一覧でクリア済みに ✓ バッジが表示される
```

### Phase 4 実装詳細（2026-03-14 実施）

| Task | 変更ファイル | 内容 |
|------|-------------|------|
| 4-1 | `App.tsx` + `VictoryOverlay.tsx` | manifest fetch で nextPuzzleId 取得 → `Victory-next-link` ボタン表示 |
| 4-2 | `VictoryOverlay.tsx` + `App.css` | `formatTime(ms)` で分:秒表示、`victory-perfect-badge` (amber)、`victory-card-pop` バネアニメ |
| 4-3 | `App.tsx` | `sochi_clears` localStorage へ `{ time, mistakes, date }` ベストタイム保存 |
| 4-4 | `docs/index.html` | `loadClears()` + `renderGroup` に `.cleared-badge` / `.puzzle-cleared` 追加 |

**→ ここでユーザー確認を依頼してから Phase 5 へ**

---

## Phase 5: 継続プレイ導線（P3）✅ 実施済み（2026-03-14）

### 目的

一度遊んで終わりではなく、続けたくなる要素を加える。

### 変更対象ファイル

- `docs/index.html`（おすすめ・今日の1問）
- `frontend/src/App.tsx`（ベストタイム表示）

---

### Task 5-1: パズル一覧に進捗サマリを追加 ✅

**変更対象**: `docs/index.html`

**変更内容**: puzzle-root の上部に小さな進捗表示

```
クリア済み: 3 / 97 問  [Easy 3 / Medium 0 / Hard 0]
```

実装: manifest と localStorage の `sochi_clears` を照合してカウント。

---

### Task 5-2: 「今日の1問」固定おすすめを追加 ✅

**変更対象**: `docs/index.html`

**変更内容**:
- manifest から今日の日付（YYYYMMDD）のEasy問題を探す
- 存在すれば「今日の1問」バナーを表示
- 存在しなければ最新のEasyを表示

```js
const today = new Date().toISOString().slice(0,10).replace(/-/g,'');
const todayEasy = data.find(p => p.date.replace(/-/g,'') === today && p.difficulty === 'Easy');
const featured = todayEasy || data.find(p => p.difficulty === 'Easy');
```

---

### Phase 5 完了確認チェックリスト

```
□ クリア進捗サマリが表示される（クリア0件のときは非表示）
□ 難易度別のチップ（Easy/Medium/Hard/Hardest）が表示される
□ 「今日の1問」または最新Easy がパズル一覧上部に表示される
□ 当日パズルがなければ最新EasyにFeaturedラベルが付く
□ クリア済みの場合は今日の1問にも ✓ Clear バッジが表示される
```

### Phase 5 実装詳細（2026-03-14 実施）

| Task | 変更ファイル | 内容 |
|------|-------------|------|
| 5-1 | `docs/index.html` | `renderProgressSummary()`: manifest × sochi_clears を照合して難易度別カウント表示。クリア0件は非表示 |
| 5-2 | `docs/index.html` | `renderFeatured()`: 今日の日付のEasyを優先、なければ最新Easy。黄色ボーダーのFeaturedカードを表示 |

---

## デザイン共通方針（全フェーズ）

### 追加CSSの方針

- `docs/index.html` の `<style>` タグ内に追記
- コメント `/* ── [Task N-N] xxx ── */` で区切る
- 既存クラス名を上書きしない（新クラス名で追加）

### 文言ルール

| 区分 | JA | EN |
|------|----|----|
| CTA（メイン） | まず1問やってみる | Try First Puzzle |
| CTA（サブ） | 遊び方を見る | How to Play |
| 難易度 Easy | 初めての方向け / 1〜3分 | For Beginners / 1–3 min |
| 難易度 Medium | 少し悩む / 3〜8分 | Gets Tricky / 3–8 min |
| 難易度 Hard | 手応えあり / 10〜20分 | Real Challenge / 10–20 min |
| 難易度 Hardest | 上級者向け / 30分〜 | Expert Only / 30+ min |
| Undo | ↩ Undo | ↩ Undo |
| Reset | ↺ Reset | ↺ Reset |
| Place | ✓ Place | ✓ Place |
| 配置可能 | ✓ {n}箇所に置けます | ✓ {n} positions available |
| 配置不可 | ✗ この向きでは置けません | ✗ No fit in this rotation |

---

## 実装順序まとめ

```
Phase 1 (P0): docs/index.html 中心
  Task 1-1: Hero CTA 改善（直接リンク）
  Task 1-2: はじめての方へ セクション追加
  Task 1-3: セクション順序変更・説明圧縮
  Task 1-4: 難易度カード情報追加
  Task 1-5: スケルトンUI
  → ユーザー確認

Phase 2 (P1): docs/index.html 仕上げ
  Task 2-1: 言語トグルの網羅確認
  Task 2-2: About セクション整理
  → ユーザー確認

Phase 3 (P1): frontend/src/ ゲーム画面
  Task 3-1: 操作UIラベル明確化
  Task 3-2: 状態フィードバック強化
  Task 3-3: Undo/Reset 常設ボタン
  Task 3-4: チュートリアルのステップ化
  → ユーザー確認

Phase 4 (P2): ゲーム体験・記録
  Task 4-1: Next Puzzle ボタン
  Task 4-2: クリア演出強化
  Task 4-3: localStorage 記録保存
  Task 4-4: 一覧にクリア済みバッジ
  → ユーザー確認

Phase 5 (P3): 継続プレイ（余力があれば）
  Task 5-1: 進捗サマリ
  Task 5-2: 今日の1問
```

---

## 完了条件

```
□ 初見ユーザーがトップを見てすぐ内容を理解できる
□ 最初の1問まで迷わず行ける（CTAが明確）
□ 難易度を直感で選べる（カードに情報がある）
□ ゲーム操作の意味がUIから分かる
□ やり直し（Undo/Reset）がしやすい
□ クリア時に次の問題へ続けられる
□ クリア記録がローカルに残る
□ 全体として未完成感が減り、作品としての完成度が上がっている
```

---

*このRUNBOOKに基づき、Phase 1 から順に実装を進めてください。*
*各Phase完了後にユーザー確認を取ってから次のPhaseへ移行します。*

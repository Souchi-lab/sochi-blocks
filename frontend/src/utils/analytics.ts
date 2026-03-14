/**
 * analytics.ts — GA4 イベント計測ユーティリティ
 *
 * 使い方:
 *   1. App.tsx の初期化時に initAnalytics(GA4_ID) を一度だけ呼ぶ
 *   2. 各コンポーネントから trackXxx() を呼ぶ
 *
 * イベント追加方法:
 *   1. この末尾に trackXxx 関数を追加する（既存パターンをコピー）
 *   2. GA4 イベント名は snake_case で統一する
 *   3. 発火箇所のコンポーネントから呼び出す
 *   4. runbooks/ANALYTICS_RUNBOOK.md のイベント一覧を更新する
 */

declare global {
  interface Window {
    dataLayer: unknown[];
    gtag: (...args: unknown[]) => void;
  }
}

// ── 難易度の導出 ──────────────────────────────────────────────────
/** removedPieces の数から難易度文字列を返す */
export function getDifficulty(pieceCount: number): string {
  if (pieceCount <= 2) return 'Easy';
  if (pieceCount <= 4) return 'Medium';
  if (pieceCount <= 6) return 'Hard';
  return 'Hardest';
}

// ── GA4 初期化 ────────────────────────────────────────────────────
/**
 * GA4 を動的に初期化する。App.tsx の最初の useEffect で一度だけ呼ぶ。
 * 測定IDは frontend/src/constants/siteConfig.ts の GA4_ID を変更すること。
 */
export function initAnalytics(measurementId: string): void {
  if (!measurementId || measurementId === 'G-XXXXXXXXXX') return;
  if (typeof window === 'undefined') return;

  // gtag.js スクリプトを動的に挿入
  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer ?? [];
  window.gtag = function (...args: unknown[]) {
    window.dataLayer.push(args);
  };
  window.gtag('js', new Date());
  window.gtag('config', measurementId);
}

// ── 基底送信関数 ──────────────────────────────────────────────────
/**
 * GA4 イベントを送信する。
 * - gtag 未設定・広告ブロッカー時は何もしない（ゲームに影響しない）
 * - 開発時 (Vite DEV) はコンソールにデバッグ出力する
 */
export function trackEvent(name: string, params: Record<string, unknown> = {}): void {
  try {
    if (typeof window !== 'undefined' && typeof window.gtag === 'function') {
      window.gtag('event', name, params);
    }
    if (import.meta.env.DEV) {
      console.log('[analytics]', name, params);
    }
  } catch {
    // 解析失敗でゲームを止めない
  }
}

// ── 個別イベント ──────────────────────────────────────────────────

/**
 * パズル画面が開かれた時（データ読み込み完了直後）。
 * 「開いたがゲームを始めていない」ユーザーを把握するために使う。
 */
export function trackPuzzleOpen(params: {
  puzzleId: string;
  difficulty: string;
  pieceCount: number;
  sourcePage?: string;
}): void {
  trackEvent('puzzle_open', {
    puzzle_id: params.puzzleId,
    difficulty: params.difficulty,
    piece_count: params.pieceCount,
    source_page: params.sourcePage ?? (typeof location !== 'undefined' ? location.pathname : ''),
  });
}

/**
 * 最初のゲームアクション（最初のピース選択）時。
 * puzzle_open と区別して「本当に始めたか」を計測する。
 * ⚠ clear_seconds の計測開始基準はこの trackPuzzleStart の時点。
 */
export function trackPuzzleStart(params: {
  puzzleId: string;
  difficulty: string;
  pieceCount: number;
  sourcePage?: string;
}): void {
  trackEvent('puzzle_start', {
    puzzle_id: params.puzzleId,
    difficulty: params.difficulty,
    piece_count: params.pieceCount,
    source_page: params.sourcePage ?? (typeof location !== 'undefined' ? location.pathname : ''),
  });
}

/**
 * パズルクリア時。
 * clear_seconds は puzzle_start（最初のピース選択）からの経過秒数。
 */
export function trackPuzzleComplete(params: {
  puzzleId: string;
  difficulty: string;
  pieceCount: number;
  clearSeconds: number;
  sourcePage?: string;
}): void {
  trackEvent('puzzle_complete', {
    puzzle_id: params.puzzleId,
    difficulty: params.difficulty,
    piece_count: params.pieceCount,
    clear_seconds: params.clearSeconds,
    source_page: params.sourcePage ?? (typeof location !== 'undefined' ? location.pathname : ''),
  });
}

/**
 * パズルカードを選んだ時（難易度付きのパズルをクリック）。
 * ランディングページの JS からも直接 gtag() で送信している。
 */
export function trackDifficultySelect(params: {
  difficulty: string;
  sourcePage?: string;
}): void {
  trackEvent('difficulty_select', {
    difficulty: params.difficulty,
    source_page: params.sourcePage ?? (typeof location !== 'undefined' ? location.pathname : ''),
  });
}

/** チュートリアル表示開始時 */
export function trackTutorialStart(params: { sourcePage?: string } = {}): void {
  trackEvent('tutorial_start', {
    source_page: params.sourcePage ?? (typeof location !== 'undefined' ? location.pathname : ''),
  });
}

/** 「次のパズルへ」を押した時 */
export function trackNextPuzzle(params: {
  fromPuzzleId: string;
  toPuzzleId: string;
  difficulty: string;
  sourcePage?: string;
}): void {
  trackEvent('next_puzzle', {
    from_puzzle_id: params.fromPuzzleId,
    to_puzzle_id: params.toPuzzleId,
    difficulty: params.difficulty,
    source_page: params.sourcePage ?? (typeof location !== 'undefined' ? location.pathname : ''),
  });
}

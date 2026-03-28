import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { Viewer } from './components/Viewer';
import { PieceTray } from './components/PieceTray';
import { PieceShapeMini } from './components/PieceShapeMini';
import { RotationCandidates } from './components/RotationCandidates';
import { VictoryOverlay } from './components/VictoryOverlay';
import { TutorialOverlay } from './components/TutorialOverlay';
import { useGameState } from './hooks/useGameState';
import { useAutoPlayer } from './hooks/useAutoPlayer';
import type { PuzzleData } from './types/puzzle';
import { loadPieceColors, loadMasterPieces, getPieceColor, getPieceShape } from './constants/pieceColors';
import { validAnchors, placementCells } from './utils/placement';
import type { Vec3 } from './utils/rotations';
import { SNSOverlay } from './components/SNSOverlay';
import { TutorialVideoOverlay } from './components/TutorialVideoOverlay';
import {
  initAnalytics,
  getDifficulty,
  trackPuzzleOpen,
  trackPuzzleStart,
  trackPuzzleComplete,
} from './utils/analytics';
import { GA4_ID } from './constants/siteConfig';
import './App.css';

type CaptureAngle = 'x' | 'y' | null;

function getParams() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');
  const puzzleId = params.get('puzzle_id');
  const removedPiecesStr = params.get('removed_pieces') ?? '';
  const urlRemovedPieces = removedPiecesStr
    ? removedPiecesStr.split(',').map((s) => s.trim()).filter(Boolean)
    : [];
  const mode = params.get('mode');
  const capture = mode === 'capture';
  const autoplay = params.get('autoplay') === '1';
  const snsMode = params.get('sns') === '1';
  const snsVideoMode = (params.get('video_mode') as 'full_play' | 'teaser' | 'tutorial' | 'assembly') ?? 'full_play';
  const angle = (params.get('angle') as CaptureAngle) ?? null;
  const initialDelayMs = autoplay ? (parseInt(params.get('delay') ?? '0', 10) || 0) : 0;
  const lang = params.get('lang') ?? 'ja';

  let puzzleFile: string;
  if (id) {
    puzzleFile = `puzzles/${id}.json`;
  } else if (puzzleId) {
    puzzleFile = `puzzles/puzzle_${puzzleId}.json`;
  } else {
    puzzleFile = '';
  }

  const captureAll = params.get('capture_all') === '1';
  return { id: id ?? puzzleId ?? '', puzzleFile, urlRemovedPieces, capture, captureAll, angle, autoplay, initialDelayMs, snsMode, snsVideoMode, lang };
}

// ── Missing pieces card (answer mode + capture mode) ──────────────
function MissingCard({ pieces, title = "Missing Pieces", subtitle = "(not used in this solution)" }: { pieces: string[], title?: string, subtitle?: string }) {
  const n = pieces.length;
  const cellSize = n <= 2 ? 20 : n <= 4 ? 16 : 12;

  return (
    <div className="missing-card">
      <div className="missing-title">{title}</div>
      <div className="missing-subtitle">{subtitle}</div>
      <div className="missing-pieces">
        {pieces.map((p) => (
          <div key={p} className="piece-item">
            <PieceShapeMini piece={p} cellSize={cellSize} />
            <div className="piece-label" style={{ color: getPieceColor(p) }}>{p}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────
function App() {
  const [data, setData] = useState<PuzzleData | null>(null);
  const [colorsLoaded, setColorsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);
  const [showTutorial, setShowTutorial] = useState(false);
  const [flashErrorPiece, setFlashErrorPiece] = useState<string | null>(null);
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [cellFlash, setCellFlash] = useState<{ type: 'error' } | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const [clearTimeMs, setClearTimeMs] = useState(0);
  // [Task 4-1] 次のパズルID
  const [nextPuzzleId, setNextPuzzleId] = useState<string | null>(null);

  // ── Analytics: セッション内フラグ（重複送信防止）──
  const startTrackedRef = useRef(false);   // puzzle_start 送信済み
  const victoryTrackedRef = useRef(false); // puzzle_complete 送信済み

  const { id, puzzleFile, urlRemovedPieces, capture, captureAll, angle, autoplay, initialDelayMs, snsMode, snsVideoMode, lang } = useMemo(getParams, []);
  const isTutorialVideo = snsVideoMode === 'tutorial';

  const removedPieces = useMemo(() => {
    const fromJson = data?.removed_pieces ?? [];
    return fromJson.length > 0 ? fromJson : urlRemovedPieces;
  }, [data, urlRemovedPieces]);

  // Stabilize the removedPieces array reference to prevent infinite loops in useGameState
  const stableRemovedPieces = useMemo(() => removedPieces, [JSON.stringify(removedPieces)]);

  const { state: gameState, selectPiece, placePiece, unplacePiece, wrongClick, setRotation, setCursorIndex, restart } =
    useGameState(stableRemovedPieces);

  // Game mode: has removed pieces AND not in capture/answer view
  const isGameMode = stableRemovedPieces.length > 0 && !capture && !showAnswer;

  // ── Missing logic for interactive placement ──
  const allEmptyCells = useMemo((): Vec3[] => {
    if (!data) return [];
    // removed_pieces に属するセルのうち、まだ配置されていないもののみ
    const removedSet = new Set(stableRemovedPieces);
    return data.cells
      .filter(c => removedSet.has(c.piece) && !gameState.placedCells.has(`${c.x},${c.y},${c.z}`))
      .map(c => [c.x, c.y, c.z] as Vec3);
  }, [data, stableRemovedPieces, gameState.placedCells]);

  const fittingRotIndices = useMemo(() => {
    if (!data || !gameState.selectedPiece) return [];
    const shape = getPieceShape(gameState.selectedPiece) as Vec3[];
    const indices: number[] = [];
    for (let i = 0; i < 24; i++) {
      const anchors = validAnchors(shape, i, allEmptyCells);
      if (anchors.length > 0) indices.push(i);
    }
    return indices;
  }, [data, gameState.selectedPiece, allEmptyCells]);

  const sortedAnchors = useMemo((): Vec3[] => {
    if (!data || !gameState.selectedPiece) return [];
    const shape = getPieceShape(gameState.selectedPiece) as Vec3[];
    const anchors = validAnchors(shape, gameState.rotationIndex, allEmptyCells);
    return [...anchors].sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
  }, [data, gameState.selectedPiece, gameState.rotationIndex, allEmptyCells]);

  const validAnchorCells = useMemo((): Set<string> => {
    return new Set(sortedAnchors.map(a => `${a[0]},${a[1]},${a[2]}`));
  }, [sortedAnchors]);

  const cursorGhostKeys = useMemo((): Set<string> => {
    if (!data || !gameState.selectedPiece || sortedAnchors.length === 0) return new Set();
    const shape = getPieceShape(gameState.selectedPiece) as Vec3[];
    const anchor = sortedAnchors[gameState.cursorIndex];
    if (!anchor) return new Set();
    const cells = placementCells(shape, gameState.rotationIndex, anchor);
    return new Set(cells.map(([x, y, z]) => `${x},${y},${z}`));
  }, [data, gameState.selectedPiece, gameState.rotationIndex, sortedAnchors, gameState.cursorIndex]);

  const isFitting = gameState.selectedPiece ? fittingRotIndices.includes(gameState.rotationIndex) : false;

  // ── Analytics: GA4 初期化（一度だけ）──
  useEffect(() => {
    initAnalytics(GA4_ID);
  }, []);

  // ── Analytics: パズル ID が変わったらフラグリセット ──
  useEffect(() => {
    startTrackedRef.current = false;
    victoryTrackedRef.current = false;
  }, [id]);

  // ── Analytics: puzzle_open — データ読み込み完了時 ──
  useEffect(() => {
    if (!data || autoplay || !id || !isGameMode) return;
    trackPuzzleOpen({
      puzzleId: id,
      difficulty: getDifficulty(stableRemovedPieces.length),
      pieceCount: stableRemovedPieces.length,
    });
  // data が変わった時だけ発火。stableRemovedPieces は依存に含めるが二重送信しないよう data に紐づける
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // ── Analytics: puzzle_complete — クリア確定時 ──
  useEffect(() => {
    if (gameState.phase !== 'victory' || clearTimeMs === 0 || autoplay || victoryTrackedRef.current) return;
    victoryTrackedRef.current = true;
    trackPuzzleComplete({
      puzzleId: id,
      difficulty: getDifficulty(stableRemovedPieces.length),
      pieceCount: stableRemovedPieces.length,
      clearSeconds: Math.round(clearTimeMs / 1000),
    });
  }, [gameState.phase, clearTimeMs, autoplay, id, stableRemovedPieces]);

  // Check local storage for initial tutorial display
  useEffect(() => {
    if (autoplay) return;
    const hasSeen = localStorage.getItem('sochi_tutorial_seen');
    if (!hasSeen) {
      setShowTutorial(true);
    }
  }, [autoplay]);

  // クリアタイム計測
  useEffect(() => {
    if (autoplay) return;
    if (gameState.phase === 'playing' && startTimeRef.current === null) {
      startTimeRef.current = Date.now();
    } else if (gameState.phase === 'victory' && startTimeRef.current !== null) {
      setClearTimeMs(Date.now() - startTimeRef.current);
      startTimeRef.current = null;
    }
  }, [gameState.phase, autoplay]);

  useEffect(() => {
    if (!puzzleFile) {
      setError('No puzzle specified. Use ?puzzle_id=20260224_001');
      return;
    }
    Promise.all([
      fetch(puzzleFile).then((res) => {
        if (!res.ok) throw new Error(`Puzzle not found: ${id}`);
        return res.json();
      }),
      loadPieceColors(),
      loadMasterPieces(),
    ])
      .then(([puzzleData]) => {
        setData(puzzleData);
        setColorsLoaded(true);
      })
      .catch((e) => setError(e.message));
  }, [id, puzzleFile]);

  // [Task 4-1] manifest から次のパズルIDを取得
  useEffect(() => {
    if (!id || autoplay) return;
    fetch('puzzles/manifest.json')
      .then(r => r.ok ? r.json() : null)
      .then((manifest: Array<{ id: string }> | null) => {
        if (!manifest) return;
        const idx = manifest.findIndex(p => p.id === id);
        if (idx !== -1 && idx + 1 < manifest.length) {
          setNextPuzzleId(manifest[idx + 1].id);
        }
      })
      .catch(() => {});
  }, [id, autoplay]);

  // [Task 4-3] クリア記録を localStorage に保存（ベストタイムのみ更新）
  useEffect(() => {
    if (gameState.phase !== 'victory' || autoplay || !id || clearTimeMs === 0) return;
    try {
      const key = 'sochi_clears';
      const prev = JSON.parse(localStorage.getItem(key) ?? '{}');
      const existing = prev[id];
      if (!existing || clearTimeMs < existing.time) {
        prev[id] = { time: clearTimeMs, mistakes: gameState.mistakeCount, date: new Date().toISOString() };
        localStorage.setItem(key, JSON.stringify(prev));
      }
    } catch { /* localStorage unavailable */ }
  }, [gameState.phase, id, clearTimeMs, gameState.mistakeCount, autoplay]);

  // Cleanup flash timer on unmount
  useEffect(() => {
    return () => { if (flashTimerRef.current) clearTimeout(flashTimerRef.current); };
  }, []);

  useAutoPlayer({
    autoplay,
    snsMode,
    snsVideoMode,
    data,
    gameState,
    selectPiece,
    placePiece,
    wrongClick,
    unplacePiece,
    setRotation,
    setCursorIndex,
    initialDelayMs,
  });

  // ── Analytics: puzzle_start — 最初のピース選択時に一度だけ送信 ──
  const handleSelectPiece = useCallback((piece: string) => {
    if (!startTrackedRef.current && isGameMode) {
      startTrackedRef.current = true;
      trackPuzzleStart({
        puzzleId: id,
        difficulty: getDifficulty(stableRemovedPieces.length),
        pieceCount: stableRemovedPieces.length,
      });
    }
    selectPiece(piece);
  }, [selectPiece, id, stableRemovedPieces, isGameMode]);

  const handleRestart = useCallback(() => {
    if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
    setFlashErrorPiece(null);
    setCellFlash(null);
    setClearTimeMs(0);
    startTrackedRef.current = false;
    victoryTrackedRef.current = false;
    restart();
  }, [restart]);

  const handleUnplace = useCallback((piece: string) => {
    if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
    setFlashErrorPiece(null);
    setCellFlash(null);
    unplacePiece(piece);
  }, [unplacePiece]);

  const handleCloseTutorial = useCallback(() => {
    localStorage.setItem('sochi_tutorial_seen', '1');
    setShowTutorial(false);
  }, []);

  const handleEmptyCellClick = useCallback((_coord: Vec3) => {
    wrongClick();
  }, [wrongClick]);

  const handlePlaceAtCursor = useCallback(() => {
    if (!gameState.selectedPiece || cursorGhostKeys.size === 0) return;
    const coords = Array.from(cursorGhostKeys);
    placePiece(gameState.selectedPiece, coords);
  }, [gameState.selectedPiece, cursorGhostKeys, placePiece]);

  if (error) return <div className="status">Error: {error}</div>;
  if (!data || !colorsLoaded) return <div className="status">Loading...</div>;

  // ── Capture mode ─────────────────────────────────────────────────
  if (capture) {
    const captureHidden = captureAll ? new Set<string>() : new Set(removedPieces);
    return (
      <div className="capture-root">
        <Viewer data={data} capture={true} captureAngle={angle} hiddenPieces={captureHidden} />
        <div className="capture-brand">
          <span className="brand-text">SoChi BLOCKS</span>
          <span className="brand-tagline">think in 3D</span>
        </div>
        {!captureAll && removedPieces.length > 0 && (
          <div className="capture-missing">
            <MissingCard pieces={removedPieces} />
          </div>
        )}
      </div>
    );
  }

  // ── Normal mode ─────────────────────────────────────────────────
  return (
    <div className={`app-layout ${isTutorialVideo ? 'tutorial-video-mode' : snsMode ? 'sns-mode' : ''}`}>
      <header className="app-header">
        <div className="header-left">
          {!autoplay && (
            <a href="./index.html" className="back-btn">{lang === 'en' ? '← Back' : '← 戻る'}</a>
          )}
          <div className="brand-group">
            <span className="brand-text">SoChi BLOCKS</span>
            <span className="brand-tagline">think in 3D</span>
          </div>
        </div>
        <div className="header-right">
          {!autoplay && isGameMode && gameState.mistakeCount > 0 && (
            <span className="mistake-badge">✕ {gameState.mistakeCount}</span>
          )}
          {!autoplay && isGameMode && (
            <button
              className="tutorial-trigger-btn"
              onClick={() => setShowTutorial(true)}
              title={lang === 'en' ? 'Help' : 'ヘルプ'}
            >
              {lang === 'en' ? 'Help' : 'ヘルプ'}
            </button>
          )}
        </div>
      </header>

      <div className="app-body">
        <div className="viewer-area">
          <Viewer
            data={data}
            capture={false}
            captureAngle={angle}
            removedPieces={isGameMode ? new Set(removedPieces) : undefined}
            placedCells={isGameMode ? gameState.placedCells : undefined}
            selectedPiece={isGameMode ? gameState.selectedPiece : undefined}
            validAnchorCells={isGameMode ? validAnchorCells : undefined}
            ghostCells={isGameMode ? cursorGhostKeys : undefined}
            onEmptyCellClick={isGameMode ? handleEmptyCellClick : undefined}
            cellFlash={isGameMode ? cellFlash : null}
            snsMode={snsMode}
          />
          {isGameMode && gameState.selectedPiece && (!snsMode || isTutorialVideo) && (
            <div className="placement-overlay">
              {sortedAnchors.length > 1 && (
                <>
                  <button
                    className="cursor-nav-btn"
                    onClick={() => setCursorIndex((gameState.cursorIndex - 1 + sortedAnchors.length) % sortedAnchors.length)}
                    aria-label="前の配置位置"
                  >
                    ← Prev
                  </button>
                  <span className="cursor-nav-count">
                    {gameState.cursorIndex + 1} / {sortedAnchors.length}
                  </span>
                  <button
                    className="cursor-nav-btn"
                    onClick={() => setCursorIndex((gameState.cursorIndex + 1) % sortedAnchors.length)}
                    aria-label="次の配置位置"
                  >
                    Next →
                  </button>
                </>
              )}
              <button
                className="place-btn"
                disabled={sortedAnchors.length === 0}
                onClick={handlePlaceAtCursor}
              >
                ✓ Place
              </button>
            </div>
          )}
          {isTutorialVideo ? (
            <TutorialVideoOverlay />
          ) : snsMode ? (
            <SNSOverlay videoMode={snsVideoMode} removedPieces={stableRemovedPieces} />
          ) : (
            isGameMode && gameState.phase === 'victory' && (
              <VictoryOverlay
                mistakeCount={gameState.mistakeCount}
                puzzleId={id}
                removedPieces={stableRemovedPieces}
                clearTimeMs={clearTimeMs}
                nextPuzzleId={nextPuzzleId}
                onRestart={handleRestart}
                onViewSolution={() => setShowAnswer(true)}
              />
            )
          )}
          <TutorialOverlay
            isVisible={showTutorial}
            onClose={handleCloseTutorial}
          />
        </div>

        {removedPieces.length > 0 && (!snsMode || isTutorialVideo) && (
          <aside className={`game-sidebar${isGameMode && gameState.selectedPiece ? ' sidebar--piece-selected' : ''}`}>
            {/* [Task 3-2] ピース未選択時のガイド */}
            {isGameMode && !gameState.selectedPiece && gameState.phase === 'playing' && (
              <div className="guide-hint">
                {lang === 'ja' ? 'ピースを選んでください ↓' : 'Pick a piece ↓'}
              </div>
            )}

            {isGameMode && gameState.selectedPiece && (
              <div className="game-middle">
                {/* [Phase 3.1] ヘッダー: ピース名 + 解除ボタン */}
                <div className="game-middle-header">
                  <div
                    className="stage-piece-label"
                    style={{ color: getPieceColor(gameState.selectedPiece) }}
                  >
                    Piece {gameState.selectedPiece}
                  </div>
                  <button
                    className="piece-deselect-btn"
                    onClick={() => handleSelectPiece(gameState.selectedPiece!)}
                    aria-label="選択解除"
                    title={lang === 'ja' ? 'トレイに戻る' : 'Back to tray'}
                  >
                    ×
                  </button>
                </div>
                {/* [Task 3-2] 配置可否フィードバック */}
                <div className={`fit-status ${isFitting ? 'fit-ok' : 'fit-ng'}`}>
                  {isFitting
                    ? (lang === 'ja' ? `✓ ${sortedAnchors.length}箇所に置けます` : `✓ ${sortedAnchors.length} ways to place`)
                    : (lang === 'ja' ? '✗ この向きでは置けません' : '✗ Cannot place this orientation')}
                </div>
                <RotationCandidates
                  piece={gameState.selectedPiece}
                  currentRotIndex={gameState.rotationIndex}
                  isFitting={isFitting}
                  candidateIndices={fittingRotIndices}
                  onSelect={setRotation}
                />
                {/* [Task 3-1] ショートカットをラベル付きで表示 */}
                <div className="controls-hint-group">
                  <div className="controls-hint-row">
                    <span className="controls-hint-label">Rotate</span>
                    <span className="hint-kbd">WASD · Q/E</span>
                  </div>
                  <div className="controls-hint-row">
                    <span className="controls-hint-label">Move</span>
                    <span className="hint-kbd">R</span>
                  </div>
                  <div className="controls-hint-row">
                    <span className="controls-hint-label">Place</span>
                    <span className="hint-kbd">Enter</span>
                  </div>
                </div>
              </div>
            )}
            <div className="missing-section">
              <div className="missing-overlay">
                {isGameMode ? (
                  <PieceTray
                    removedPieces={removedPieces}
                    placedPieces={gameState.placedPieces}
                    selectedPiece={gameState.selectedPiece}
                    flashErrorPiece={flashErrorPiece}
                    onSelect={handleSelectPiece}
                    onUnplace={handleUnplace}
                  />
                ) : (
                  <MissingCard
                    pieces={removedPieces}
                    title="Solution Pieces"
                    subtitle="(pieces used in this answer)"
                  />
                )}
              </div>
            </div>
            {/* [Task 3-3] Undo / Reset 常設ボタン */}
            {isGameMode && (
              <div className="game-actions">
                <button
                  className="action-btn action-undo"
                  onClick={() => {
                    const pieces = [...gameState.placedPieces];
                    const last = pieces[pieces.length - 1];
                    if (last) handleUnplace(last);
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
          </aside>
        )}
      </div>
    </div>
  );
}

export default App;

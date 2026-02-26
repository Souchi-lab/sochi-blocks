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
import { validAnchors, placementCells, uniqueRotationIndices } from './utils/placement';
import type { Vec3 } from './utils/rotations';
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
  const angle = (params.get('angle') as CaptureAngle) ?? null;

  let puzzleFile: string;
  if (id) {
    puzzleFile = `puzzles/${id}.json`;
  } else if (puzzleId) {
    puzzleFile = `puzzles/puzzle_${puzzleId}.json`;
  } else {
    puzzleFile = '';
  }

  return { id: id ?? puzzleId ?? '', puzzleFile, urlRemovedPieces, capture, angle, autoplay };
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

  const { id, puzzleFile, urlRemovedPieces, capture, angle, autoplay } = useMemo(getParams, []);

  const removedPieces = useMemo(() => {
    const fromJson = data?.removed_pieces ?? [];
    return fromJson.length > 0 ? fromJson : urlRemovedPieces;
  }, [data, urlRemovedPieces]);

  // Stabilize the removedPieces array reference to prevent infinite loops in useGameState
  const stableRemovedPieces = useMemo(() => removedPieces, [JSON.stringify(removedPieces)]);

  const { state: gameState, selectPiece, placePiece, unplacePiece, wrongClick, rotate, resetRotation, setRotation, setCursorIndex, restart } =
    useGameState(stableRemovedPieces);

  // Game mode: has removed pieces AND not in capture/answer view
  const isGameMode = stableRemovedPieces.length > 0 && !capture && !showAnswer;

  const hasProblemMode = stableRemovedPieces.length > 0;

  // Check local storage for initial tutorial display
  useEffect(() => {
    if (autoplay) return;
    const hasSeen = localStorage.getItem('sochi_tutorial_seen');
    if (!hasSeen) {
      setShowTutorial(true);
    }
  }, [autoplay]);

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

  // Cleanup flash timer on unmount
  useEffect(() => {
    return () => { if (flashTimerRef.current) clearTimeout(flashTimerRef.current); };
  }, []);

  // ── All currently empty cells (removed-pieces region, not yet filled) ──
  const allEmptyCells = useMemo((): Vec3[] => {
    if (!data || !isGameMode) return [];
    const removedSet = new Set(removedPieces);
    return data.cells
      .filter(c => removedSet.has(c.piece) && !gameState.placedCells.has(`${c.x},${c.y},${c.z}`))
      .map(c => [c.x, c.y, c.z] as Vec3);
  }, [data, isGameMode, removedPieces, gameState.placedCells]);

  // ── Valid anchor cells for current rotation ──
  const validAnchorCells = useMemo((): Set<string> | undefined => {
    if (!isGameMode || !gameState.selectedPiece) return undefined;
    const pieceCells = getPieceShape(gameState.selectedPiece) as Vec3[];
    if (pieceCells.length === 0) return undefined;
    const anchors = validAnchors(pieceCells, gameState.rotationIndex, allEmptyCells);
    return anchors.length > 0
      ? new Set(anchors.map(([x, y, z]) => `${x},${y},${z}`))
      : undefined;
  }, [isGameMode, gameState.selectedPiece, gameState.rotationIndex, allEmptyCells]);

  // Stage panel glows green when any valid placement exists for the current rotation
  const isFitting = (validAnchorCells?.size ?? 0) > 0;

  // Rotation candidates filtered to only placeable orientations
  // Falls back to all unique rotations if none are placeable (shouldn't happen in normal play)
  const fittingRotIndices = useMemo((): number[] | undefined => {
    if (!isGameMode || !gameState.selectedPiece) return undefined;
    const pieceCells = getPieceShape(gameState.selectedPiece) as Vec3[];
    if (pieceCells.length === 0) return undefined;
    const allIndices = uniqueRotationIndices(pieceCells);
    const fitting = allIndices.filter(idx => validAnchors(pieceCells, idx, allEmptyCells).length > 0);
    return fitting.length > 0 ? fitting : allIndices;
  }, [isGameMode, gameState.selectedPiece, allEmptyCells]);

  // ── Sorted anchor list for cursor navigation (z → y → x) ──
  const sortedAnchors = useMemo((): string[] => {
    if (!validAnchorCells) return [];
    return [...validAnchorCells].sort((a, b) => {
      const [ax, ay, az] = a.split(',').map(Number);
      const [bx, by, bz] = b.split(',').map(Number);
      if (az !== bz) return az - bz;
      if (ay !== by) return ay - by;
      return ax - bx;
    });
  }, [validAnchorCells]);

  // Currently targeted anchor (cursor position)
  const cursorAnchorKey: string | undefined = sortedAnchors[gameState.cursorIndex];

  // ── Ghost cells: only the cursor anchor's placement (5 cells) ──
  const cursorGhostCells = useMemo((): Set<string> | undefined => {
    if (!isGameMode || !gameState.selectedPiece || !cursorAnchorKey) return undefined;
    const pieceCells = getPieceShape(gameState.selectedPiece) as Vec3[];
    const anchor = cursorAnchorKey.split(',').map(Number) as Vec3;
    const ghostSet = new Set<string>();
    for (const [x, y, z] of placementCells(pieceCells, gameState.rotationIndex, anchor)) {
      ghostSet.add(`${x},${y},${z}`);
    }
    return ghostSet;
  }, [isGameMode, gameState.selectedPiece, gameState.rotationIndex, cursorAnchorKey]);

  // ── Place piece at the current cursor anchor ──
  const handlePlaceAtCursor = useCallback(() => {
    if (!gameState.selectedPiece || !cursorAnchorKey) return;
    const coord = cursorAnchorKey.split(',').map(Number) as Vec3;
    const pieceCells = getPieceShape(gameState.selectedPiece) as Vec3[];
    const cells = placementCells(pieceCells, gameState.rotationIndex, coord);
    const coords = cells.map(([x, y, z]) => `${x},${y},${z}`);
    if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
    setFlashErrorPiece(null);
    setCellFlash(null);
    placePiece(gameState.selectedPiece, coords);
  }, [gameState.selectedPiece, gameState.rotationIndex, cursorAnchorKey, placePiece]);

  const handleEmptyCellClick = useCallback((coord: Vec3) => {
    if (!gameState.selectedPiece || !data) return;

    const coordKey = `${coord[0]},${coord[1]},${coord[2]}`;

    // Mobile (coarse pointer): tap on anchor → move cursor there
    const isTouchDevice = window.matchMedia('(pointer: coarse)').matches;
    if (isTouchDevice) {
      const idx = sortedAnchors.indexOf(coordKey);
      if (idx >= 0) setCursorIndex(idx);
      return;
    }

    // PC: click → immediate placement
    const triggerError = () => {
      wrongClick();
      setFlashErrorPiece(gameState.selectedPiece!);
      setCellFlash({ type: 'error' });
      if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
      flashTimerRef.current = setTimeout(() => {
        setFlashErrorPiece(null);
        setCellFlash(null);
      }, 500);
    };

    if (!validAnchorCells?.has(coordKey)) {
      triggerError();
      return;
    }

    const pieceCells = getPieceShape(gameState.selectedPiece) as Vec3[];
    const cells = placementCells(pieceCells, gameState.rotationIndex, coord);
    const coords = cells.map(([x, y, z]) => `${x},${y},${z}`);
    if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
    setFlashErrorPiece(null);
    setCellFlash(null);
    placePiece(gameState.selectedPiece, coords);
  }, [gameState.selectedPiece, gameState.rotationIndex, validAnchorCells, sortedAnchors, data, placePiece, wrongClick, setCursorIndex]);

  // Keyboard shortcuts
  useEffect(() => {
    if (!isGameMode || gameState.phase === 'victory') return;
    const handler = (e: KeyboardEvent) => {
      if (!gameState.selectedPiece) return;
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      switch (e.key) {
        case 'ArrowLeft': case 'a': case 'A': e.preventDefault(); rotate('Y', -1); break;
        case 'ArrowRight': case 'd': case 'D': e.preventDefault(); rotate('Y', 1); break;
        case 'ArrowUp': case 'w': case 'W': e.preventDefault(); rotate('X', -1); break;
        case 'ArrowDown': case 's': case 'S': e.preventDefault(); rotate('X', 1); break;
        case 'q': case 'Q': e.preventDefault(); rotate('Z', -1); break;
        case 'e': case 'E': e.preventDefault(); rotate('Z', 1); break;
        case 'r': case 'R': e.preventDefault(); resetRotation(); break;
        case 'Escape': e.preventDefault(); selectPiece(gameState.selectedPiece); break;
        case 'Enter': case ' ': e.preventDefault(); handlePlaceAtCursor(); break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isGameMode, gameState.phase, gameState.selectedPiece, rotate, resetRotation, selectPiece, handlePlaceAtCursor]);

  // handleRestart: clear any pending flash before resetting game state
  const handleRestart = useCallback(() => {
    if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
    setFlashErrorPiece(null);
    setCellFlash(null);
    restart();
  }, [restart]);

  // handleUnplace: clear flash then remove piece from placed state (selects it for re-placement)
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

  useAutoPlayer({
    autoplay,
    data,
    gameState,
    selectPiece,
    placePiece,
    rotate
  });

  if (error) return <div className="status">Error: {error}</div>;
  if (!data || !colorsLoaded) return <div className="status">Loading...</div>;

  // ── Capture mode ─────────────────────────────────────────────────
  if (capture) {
    const captureHidden = new Set(removedPieces);
    return (
      <div className="capture-root">
        <Viewer data={data} capture={true} captureAngle={angle} hiddenPieces={captureHidden} />
        <div className="capture-brand">
          <span className="brand-text">SoChi BLOCKS</span>
          <span className="brand-tagline">think in 3D</span>
        </div>
        {removedPieces.length > 0 && (
          <div className="capture-missing">
            <MissingCard pieces={removedPieces} />
          </div>
        )}
      </div>
    );
  }

  // ── Normal mode ─────────────────────────────────────────────────
  return (
    <div className="app-layout">
      {/* ① Header */}
      <header className="app-header">
        <div className="header-left">
          {!autoplay && (
            <a href="./index.html" className="back-btn">← Back</a>
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
              title="Help"
            >
              Help
            </button>
          )}
          {!autoplay && isGameMode && (
            <button className="reset-btn" onClick={handleRestart}>
              Reset
            </button>
          )}
          {!autoplay && hasProblemMode && (
            <button
              className="toggle-btn"
              onClick={() => setShowAnswer((prev) => !prev)}
            >
              {showAnswer ? 'Problem' : 'Answer'}
            </button>
          )}
        </div>
      </header>

      {/* ② Body */}
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
            ghostCells={isGameMode ? cursorGhostCells : undefined}
            onEmptyCellClick={isGameMode ? handleEmptyCellClick : undefined}
            cellFlash={isGameMode ? cellFlash : null}
          />
          {/* Placement overlay — cursor nav + Set button */}
          {isGameMode && gameState.selectedPiece && (
            <div className="placement-overlay">
              {sortedAnchors.length > 0 && (
                <>
                  <button
                    className="cursor-nav-btn"
                    onClick={() => setCursorIndex((gameState.cursorIndex - 1 + sortedAnchors.length) % sortedAnchors.length)}
                    aria-label="前の配置位置"
                  >
                    ←
                  </button>
                  <span className="cursor-nav-count">
                    {gameState.cursorIndex + 1} / {sortedAnchors.length}
                  </span>
                  <button
                    className="cursor-nav-btn"
                    onClick={() => setCursorIndex((gameState.cursorIndex + 1) % sortedAnchors.length)}
                    aria-label="次の配置位置"
                  >
                    →
                  </button>
                </>
              )}
              <button
                className="place-btn"
                disabled={sortedAnchors.length === 0}
                onClick={handlePlaceAtCursor}
              >
                Set
              </button>
            </div>
          )}
          {isGameMode && gameState.phase === 'victory' && (
            <VictoryOverlay
              mistakeCount={gameState.mistakeCount}
              onRestart={handleRestart}
              onViewSolution={() => setShowAnswer(true)}
            />
          )}
          <TutorialOverlay
            isVisible={showTutorial}
            onClose={handleCloseTutorial}
          />
        </div>

        {removedPieces.length > 0 && (
          <aside className="game-sidebar">
            {isGameMode && gameState.selectedPiece && (
              <div className="game-middle">
                <div
                  className="stage-piece-label"
                  style={{ color: getPieceColor(gameState.selectedPiece) }}
                >
                  Piece {gameState.selectedPiece}
                </div>

                {/* Rotation selection */}
                <RotationCandidates
                  piece={gameState.selectedPiece}
                  currentRotIndex={gameState.rotationIndex}
                  isFitting={isFitting}
                  candidateIndices={fittingRotIndices}
                  onSelect={setRotation}
                  onReset={resetRotation}
                />

                <div className="drag-hint">
                  <span className="hint-kbd">WASD · Q/E · R · Enter</span>
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
                    onSelect={selectPiece}
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
          </aside>
        )}
      </div>
    </div>
  );
}

export default App;

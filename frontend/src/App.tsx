import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { Viewer } from './components/Viewer';
import { PieceTray } from './components/PieceTray';
import { PieceShapeMini } from './components/PieceShapeMini';
import { PieceStage } from './components/PieceStage';
import { VictoryOverlay } from './components/VictoryOverlay';
import { useGameState } from './hooks/useGameState';
import type { PuzzleData } from './types/puzzle';
import { loadPieceColors, loadMasterPieces, getPieceColor, getPieceShape } from './constants/pieceColors';
import { validAnchors, placementCells } from './utils/placement';
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
  const angle = (params.get('angle') as CaptureAngle) ?? null;

  let puzzleFile: string;
  if (id) {
    puzzleFile = `puzzles/${id}.json`;
  } else if (puzzleId) {
    puzzleFile = `puzzles/puzzle_${puzzleId}.json`;
  } else {
    puzzleFile = '';
  }

  return { id: id ?? puzzleId ?? '', puzzleFile, urlRemovedPieces, capture, angle };
}

// ── Missing pieces card (answer mode + capture mode) ──────────────
function MissingCard({ pieces }: { pieces: string[] }) {
  const n = pieces.length;
  const cellSize = n <= 2 ? 20 : n <= 4 ? 16 : 12;

  return (
    <div className="missing-card">
      <div className="missing-title">Missing Pieces</div>
      <div className="missing-subtitle">(not used in this solution)</div>
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
  const [flashErrorPiece, setFlashErrorPiece] = useState<string | null>(null);
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [cellFlash, setCellFlash] = useState<{ type: 'error' } | null>(null);

  const { id, puzzleFile, urlRemovedPieces, capture, angle } = useMemo(getParams, []);

  const removedPieces = useMemo(() => {
    const fromJson = data?.removed_pieces ?? [];
    return fromJson.length > 0 ? fromJson : urlRemovedPieces;
  }, [data, urlRemovedPieces]);

  const { state: gameState, selectPiece, placePiece, unplacePiece, wrongClick, rotate, resetRotation, restart } =
    useGameState(removedPieces);

  // Game mode: has removed pieces AND not in capture/answer view
  const isGameMode = removedPieces.length > 0 && !capture && !showAnswer;

  const hasProblemMode = removedPieces.length > 0;

  useEffect(() => {
    if (!puzzleFile) {
      setError('No puzzle specified. Use ?id=2026-002 or ?puzzle_id=5x4x3_0010');
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

  // ── Valid anchor cells + ghost cells (all cells occupied by any valid placement) ──
  const { validAnchorCells, ghostCells } = useMemo((): {
    validAnchorCells: Set<string> | undefined;
    ghostCells: Set<string> | undefined;
  } => {
    if (!isGameMode || !gameState.selectedPiece)
      return { validAnchorCells: undefined, ghostCells: undefined };
    const pieceCells = getPieceShape(gameState.selectedPiece) as Vec3[];
    if (pieceCells.length === 0)
      return { validAnchorCells: undefined, ghostCells: undefined };

    const anchors = validAnchors(pieceCells, gameState.rotationIndex, allEmptyCells);
    const anchorSet = new Set(anchors.map(([x, y, z]) => `${x},${y},${z}`));

    const ghostSet = new Set<string>();
    for (const anchor of anchors) {
      for (const [x, y, z] of placementCells(pieceCells, gameState.rotationIndex, anchor)) {
        ghostSet.add(`${x},${y},${z}`);
      }
    }

    return { validAnchorCells: anchorSet, ghostCells: ghostSet };
  }, [isGameMode, gameState.selectedPiece, gameState.rotationIndex, allEmptyCells]);

  // Stage panel glows green when any valid placement exists for the current rotation
  const isFitting = (validAnchorCells?.size ?? 0) > 0;

  const handleEmptyCellClick = useCallback((coord: Vec3) => {
    if (!gameState.selectedPiece || !data) return;

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

    const coordKey = `${coord[0]},${coord[1]},${coord[2]}`;
    if (!validAnchorCells?.has(coordKey)) {
      // Clicked a non-anchor empty cell — shouldn't happen since only anchors have onClick,
      // but guard anyway
      triggerError();
      return;
    }

    // Valid anchor clicked — compute the 5 cells and place
    const pieceCells = getPieceShape(gameState.selectedPiece) as Vec3[];
    const cells = placementCells(pieceCells, gameState.rotationIndex, coord);
    const coords = cells.map(([x, y, z]) => `${x},${y},${z}`);

    if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
    setFlashErrorPiece(null);
    setCellFlash(null);
    placePiece(gameState.selectedPiece, coords);
  }, [gameState.selectedPiece, gameState.rotationIndex, validAnchorCells, data, placePiece, wrongClick]);

  // Keyboard shortcuts
  useEffect(() => {
    if (!isGameMode || gameState.phase === 'victory') return;
    const handler = (e: KeyboardEvent) => {
      if (!gameState.selectedPiece) return;
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      switch (e.key) {
        case 'ArrowLeft':  e.preventDefault(); rotate('Y', -1); break;
        case 'ArrowRight': e.preventDefault(); rotate('Y',  1); break;
        case 'ArrowUp':    e.preventDefault(); rotate('X', -1); break;
        case 'ArrowDown':  e.preventDefault(); rotate('X',  1); break;
        case 'q': case 'Q': e.preventDefault(); rotate('Z', -1); break;
        case 'e': case 'E': e.preventDefault(); rotate('Z',  1); break;
        case 'r': case 'R': e.preventDefault(); resetRotation(); break;
        case 'Escape':      e.preventDefault(); selectPiece(gameState.selectedPiece); break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isGameMode, gameState.phase, gameState.selectedPiece, rotate, resetRotation, selectPiece]);

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
          <a href="./index.html" className="back-btn">← Back</a>
          <div className="brand-group">
            <span className="brand-text">SoChi BLOCKS</span>
            <span className="brand-tagline">think in 3D</span>
          </div>
        </div>
        <div className="header-right">
          {isGameMode && gameState.mistakeCount > 0 && (
            <span className="mistake-badge">✕ {gameState.mistakeCount}</span>
          )}
          {isGameMode && (
            <button className="reset-btn" onClick={handleRestart}>
              Reset
            </button>
          )}
          {hasProblemMode && (
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
            ghostCells={isGameMode ? ghostCells : undefined}
            onEmptyCellClick={isGameMode ? handleEmptyCellClick : undefined}
            cellFlash={isGameMode ? cellFlash : null}
          />
          {isGameMode && gameState.phase === 'victory' && (
            <VictoryOverlay
              mistakeCount={gameState.mistakeCount}
              onRestart={handleRestart}
              onViewSolution={() => setShowAnswer(true)}
            />
          )}
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
                <div className={`stage-panel${isFitting ? ' stage-panel--fits' : ''}`}>
                  <PieceStage
                    piece={gameState.selectedPiece}
                    rotationIndex={gameState.rotationIndex}
                    onRotate={rotate}
                  />
                </div>
                <div className="z-rotation-row">
                  <button className="rot-z-btn" onClick={() => rotate('Z', -1)} title="Z軸 反時計回り (Q)">↺</button>
                  <span className="z-hint">Z軸</span>
                  <button className="rot-z-btn" onClick={() => rotate('Z',  1)} title="Z軸 時計回り (E)">↻</button>
                </div>
                <div className="drag-hint">ドラッグで回転<span className="hint-kbd"> / ←↑→↓ · Q/E · R リセット</span> · 光ったら配置</div>
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
                  <MissingCard pieces={removedPieces} />
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

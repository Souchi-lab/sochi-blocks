import { useEffect, useState, useMemo } from 'react';
import { Viewer } from './components/Viewer';
import type { PuzzleData } from './types/puzzle';
import { loadPieceColors, loadMasterPieces, getPieceColor, getPieceShape } from './constants/pieceColors';
import './App.css';

type CaptureAngle = 'x' | 'y' | null;

function getParams() {
  const params = new URLSearchParams(window.location.search);
  // Support both ?id=2026-002 (new) and ?puzzle_id=5x4x3_0010 (legacy)
  const id = params.get('id');
  const puzzleId = params.get('puzzle_id');
  // URL removed_pieces is only for capture mode (internal use)
  const removedPiecesStr = params.get('removed_pieces') ?? '';
  const urlRemovedPieces = removedPiecesStr
    ? removedPiecesStr.split(',').map((s) => s.trim()).filter(Boolean)
    : [];
  const mode = params.get('mode');
  const capture = mode === 'capture';
  const angle = (params.get('angle') as CaptureAngle) ?? null;

  // Determine puzzle file path
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

// ── Brand header overlay ────────────────────────────────────────
function BrandOverlay() {
  return (
    <div className="brand-overlay">
      <div className="brand-title">S o C h i &nbsp; B L O C K S</div>
      <div className="brand-tagline">T H I N K &nbsp; I N &nbsp; 3 D .</div>
    </div>
  );
}

// ── Mini piece shape (2D projection, matching 2D layer image style) ──
function PieceShapeMini({ piece, cellSize }: { piece: string; cellSize: number }) {
  const shape = getPieceShape(piece);
  const color = getPieceColor(piece);
  const gap = Math.max(1, Math.round(cellSize * 0.12));

  // Project to 2D (x, y), deduplicate
  const seen = new Set<string>();
  const coords: [number, number][] = [];
  for (const [x, y] of shape.map(([x, y]) => [x, y])) {
    const key = `${x},${y}`;
    if (!seen.has(key)) { seen.add(key); coords.push([x, y]); }
  }
  const minX = Math.min(...coords.map(([x]) => x));
  const minY = Math.min(...coords.map(([, y]) => y));
  const norm = coords.map(([x, y]) => [x - minX, y - minY] as [number, number]);
  const maxY = Math.max(...norm.map(([, y]) => y));

  const step = cellSize + gap;
  const w = (Math.max(...norm.map(([x]) => x)) + 1) * step - gap;
  const h = (maxY + 1) * step - gap;

  return (
    <div style={{ position: 'relative', width: w, height: h, flexShrink: 0 }}>
      {norm.map(([x, y], i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: x * step,
            top: (maxY - y) * step,
            width: cellSize,
            height: cellSize,
            background: color,
            borderRadius: Math.max(1, Math.round(cellSize * 0.2)),
          }}
        />
      ))}
    </div>
  );
}

// ── Missing pieces overlay (matching 2D layer image style) ──────
function MissingOverlay({ pieces }: { pieces: string[] }) {
  if (pieces.length === 0) return null;
  // Adaptive cell size based on piece count (mirrors generate_instagram_images.py)
  const n = pieces.length;
  const cellSize = n <= 2 ? 20 : n <= 4 ? 16 : 12;

  return (
    <div className="missing-overlay">
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
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────
function App() {
  const [data, setData] = useState<PuzzleData | null>(null);
  const [colorsLoaded, setColorsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);

  const { id, puzzleFile, urlRemovedPieces, capture, angle } = useMemo(getParams, []);

  // Merge: JSON removed_pieces (primary) + URL removed_pieces (capture fallback)
  const removedPieces = useMemo(() => {
    const fromJson = data?.removed_pieces ?? [];
    return fromJson.length > 0 ? fromJson : urlRemovedPieces;
  }, [data, urlRemovedPieces]);

  const hiddenPieces = useMemo(
    () => (showAnswer ? undefined : new Set(removedPieces)),
    [showAnswer, removedPieces]
  );

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

  if (error) {
    return <div className="status">Error: {error}</div>;
  }
  if (!data || !colorsLoaded) {
    return <div className="status">Loading...</div>;
  }

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      <Viewer
        data={data}
        hiddenPieces={hiddenPieces}
        capture={capture}
        captureAngle={angle}
      />
      <BrandOverlay />
      <div className="bottom-controls">
        {!capture && hasProblemMode && (
          <button
            className="toggle-btn"
            onClick={() => setShowAnswer((prev) => !prev)}
          >
            {showAnswer ? 'Problem' : 'Answer'}
          </button>
        )}
        <MissingOverlay pieces={removedPieces} />
      </div>
    </div>
  );
}

export default App;

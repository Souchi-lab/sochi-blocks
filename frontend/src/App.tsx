import { useEffect, useState, useMemo } from 'react';
import { Viewer } from './components/Viewer';
import type { PuzzleData } from './types/puzzle';
import { loadPieceColors } from './constants/pieceColors';
import './App.css';

type CaptureAngle = 'x' | 'y' | null;

function getParams() {
  const params = new URLSearchParams(window.location.search);
  // Support both ?id=2026-002 (new) and ?puzzle_id=5x4x3_0010 (legacy)
  const id = params.get('id');
  const puzzleId = params.get('puzzle_id');
  const removedPiecesStr = params.get('removed_pieces') ?? '';
  const removedPieces = removedPiecesStr
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
    puzzleFile = '';  // no puzzle specified
  }

  return { id: id ?? puzzleId ?? '', puzzleFile, removedPieces, capture, angle };
}

function App() {
  const [data, setData] = useState<PuzzleData | null>(null);
  const [colorsLoaded, setColorsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);

  const { id, puzzleFile, removedPieces, capture, angle } = useMemo(getParams, []);

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
    <div style={{ width: '100vw', height: '100vh' }}>
      <Viewer
        data={data}
        hiddenPieces={hiddenPieces}
        capture={capture}
        captureAngle={angle}
      />
      {!capture && hasProblemMode && (
        <button
          className="toggle-btn"
          onClick={() => setShowAnswer((prev) => !prev)}
        >
          {showAnswer ? 'Problem' : 'Answer'}
        </button>
      )}
    </div>
  );
}

export default App;

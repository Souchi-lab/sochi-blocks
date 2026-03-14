import { ShareResult } from './ShareResult';
import { trackNextPuzzle, getDifficulty } from '../utils/analytics';

function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, '0')}`;
}

type Props = {
  mistakeCount: number;
  puzzleId: string;
  removedPieces: string[];
  clearTimeMs: number;
  nextPuzzleId?: string | null;
  onRestart: () => void;
  onViewSolution: () => void;
};

export function VictoryOverlay({
  mistakeCount,
  puzzleId,
  removedPieces,
  clearTimeMs,
  nextPuzzleId,
  onRestart,
  onViewSolution,
}: Props) {
  const isPerfect = mistakeCount === 0;

  return (
    <div className="victory-overlay">
      <div className="victory-card">
        <div className="victory-emoji">🎉</div>
        <div className="victory-title">Solved!</div>

        {/* [Task 4-2] タイム表示 + Perfect バッジ */}
        {clearTimeMs > 0 && (
          <div className="victory-time">
            {formatTime(clearTimeMs)}
            {isPerfect && <span className="victory-perfect-badge">Perfect!</span>}
          </div>
        )}

        <div className="victory-mistakes">
          {isPerfect
            ? 'No mistakes!'
            : `Mistakes: ${mistakeCount}`}
        </div>

        <ShareResult
          puzzleId={puzzleId}
          removedPieces={removedPieces}
          mistakeCount={mistakeCount}
          clearTimeMs={clearTimeMs}
        />

        <div className="victory-actions">
          <button className="victory-restart" onClick={onRestart}>
            Play Again
          </button>
          <button className="victory-view-solution" onClick={onViewSolution}>
            View Solution
          </button>
        </div>

        {/* [Task 4-1] 次のパズルへ */}
        {nextPuzzleId && (
          <a
            className="victory-next-link"
            href={`./viewer.html?puzzle_id=${nextPuzzleId}`}
            onClick={() => trackNextPuzzle({
              fromPuzzleId: puzzleId,
              toPuzzleId: nextPuzzleId,
              difficulty: getDifficulty(removedPieces.length),
            })}
          >
            Next Puzzle →
          </a>
        )}
      </div>
    </div>
  );
}

import { ShareResult } from './ShareResult';

type Props = {
  mistakeCount: number;
  puzzleId: string;
  removedPieces: string[];
  clearTimeMs: number;
  onRestart: () => void;
  onViewSolution: () => void;
};

export function VictoryOverlay({
  mistakeCount,
  puzzleId,
  removedPieces,
  clearTimeMs,
  onRestart,
  onViewSolution,
}: Props) {
  return (
    <div className="victory-overlay">
      <div className="victory-card">
        <div className="victory-emoji">🎉</div>
        <div className="victory-title">Solved!</div>
        <div className="victory-mistakes">
          {mistakeCount === 0
            ? 'Perfect — no mistakes!'
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
      </div>
    </div>
  );
}

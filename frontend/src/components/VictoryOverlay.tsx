type Props = {
  mistakeCount: number;
  onRestart: () => void;
  onViewSolution: () => void;
};

export function VictoryOverlay({ mistakeCount, onRestart, onViewSolution }: Props) {
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

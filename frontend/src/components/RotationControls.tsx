import { getPieceColor } from '../constants/pieceColors';

type Props = {
  piece: string;
  onRotate: (axis: 'X' | 'Y' | 'Z', dir: 1 | -1) => void;
};

const AXES = ['X', 'Y', 'Z'] as const;

export function RotationControls({ piece, onRotate }: Props) {
  const color = getPieceColor(piece);

  return (
    <div className="rotation-controls">
      <div className="rotation-piece-label">
        Piece&nbsp;
        <span style={{ color, fontWeight: 800 }}>{piece}</span>
      </div>
      <div className="rotation-hint">回転させて向きを合わせよう</div>
      <div className="rotation-grid">
        {AXES.map(axis => (
          <div key={axis} className="rotation-row">
            <span className="rotation-axis-label">{axis}</span>
            <button
              className="rot-btn"
              onClick={() => onRotate(axis, -1)}
              aria-label={`Rotate ${axis} counter-clockwise`}
            >↺</button>
            <button
              className="rot-btn"
              onClick={() => onRotate(axis, 1)}
              aria-label={`Rotate ${axis} clockwise`}
            >↻</button>
          </div>
        ))}
      </div>
    </div>
  );
}

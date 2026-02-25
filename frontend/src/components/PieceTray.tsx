import { getPieceColor } from '../constants/pieceColors';
import { PieceShapeMini } from './PieceShapeMini';

// ── PieceTray ──────────────────────────────────────────────────────
type Props = {
  removedPieces: string[];
  placedPieces: Set<string>;
  selectedPiece: string | null;
  flashErrorPiece: string | null;
  onSelect: (piece: string) => void;
  onUnplace: (piece: string) => void;
};

export function PieceTray({
  removedPieces,
  placedPieces,
  selectedPiece,
  flashErrorPiece,
  onSelect,
  onUnplace,
}: Props) {
  const n = removedPieces.length;
  const cellSize = n <= 2 ? 20 : n <= 4 ? 16 : 12;

  const placedCount = placedPieces.size;
  const totalCount  = removedPieces.length;

  return (
    <div className="piece-tray">
      <div className="tray-label">
        {placedCount === totalCount
          ? 'All pieces placed!'
          : `${placedCount} / ${totalCount} placed`}
      </div>
      <div className="tray-pieces">
        {removedPieces.map((piece) => {
          const placed   = placedPieces.has(piece);
          const selected = selectedPiece === piece;
          const error    = flashErrorPiece === piece;

          const cls = [
            'tray-card',
            selected ? 'tray-card--selected' : '',
            placed   ? 'tray-card--placed'   : '',
            error    ? 'tray-card--error'    : '',
          ].filter(Boolean).join(' ');

          return (
            <button
              key={piece}
              className={cls}
              onClick={() => placed ? onUnplace(piece) : onSelect(piece)}
            >
              <PieceShapeMini piece={piece} cellSize={cellSize} />
              <div className="piece-label" style={{ color: getPieceColor(piece) }}>
                {piece}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

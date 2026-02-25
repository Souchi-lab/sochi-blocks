import { getPieceColor, getPieceShape } from '../constants/pieceColors';

type Props = {
  piece: string;
  cellSize: number;
};

/**
 * 2D pixel-art preview of a pentomino piece (XY projection, z-axis collapsed).
 * Used in both PieceTray (game mode) and MissingCard (answer/capture mode).
 */
export function PieceShapeMini({ piece, cellSize }: Props) {
  const shape = getPieceShape(piece);
  const color = getPieceColor(piece);
  const gap = Math.max(1, Math.round(cellSize * 0.12));

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

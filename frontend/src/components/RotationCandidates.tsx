import { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { applyRotation, normalize, type Vec3 } from '../utils/rotations';
import { getPieceColor, getPieceShape } from '../constants/pieceColors';
import { uniqueRotationIndices } from '../utils/placement';
import './RotationCandidates.css';

const BOX_SIZE = 0.88;

type ThumbProps = { piece: string; rotIndex: number };

function PieceThumbnail({ piece, rotIndex }: ThumbProps) {
  const color = getPieceColor(piece);
  const { cells, ox, oy, oz } = useMemo(() => {
    const raw = getPieceShape(piece) as Vec3[];
    if (raw.length === 0) return { cells: [], ox: 0, oy: 0, oz: 0 };
    const rotated = normalize(applyRotation(raw, rotIndex));
    const maxX = Math.max(...rotated.map(c => c[0]));
    const maxY = Math.max(...rotated.map(c => c[1]));
    const maxZ = Math.max(...rotated.map(c => c[2]));
    return { cells: rotated, ox: maxX / 2, oy: maxY / 2, oz: maxZ / 2 };
  }, [piece, rotIndex]);

  return (
    <Canvas
      camera={{ position: [4, 4, 4], fov: 40 }}
      style={{ width: '100%', height: '100%', display: 'block' }}
      gl={{ antialias: false, alpha: true }}
    >
      <ambientLight intensity={1.5} />
      <directionalLight position={[5, 8, 5]} intensity={2.0} />
      <group>
        {cells.map(([x, y, z], i) => (
          <mesh key={i} position={[x - ox, z - oz, y - oy]}>
            <boxGeometry args={[BOX_SIZE, BOX_SIZE, BOX_SIZE]} />
            <meshStandardMaterial color={color} roughness={0.6} metalness={0.05} />
          </mesh>
        ))}
      </group>
    </Canvas>
  );
}

type Props = {
  piece: string;
  currentRotIndex: number;
  isFitting: boolean;
  /** Pre-filtered rotation indices (placeable-only). Falls back to all unique rotations. */
  candidateIndices?: number[];
  onSelect: (index: number) => void;
};

export function RotationCandidates({ piece, currentRotIndex, isFitting, candidateIndices, onSelect }: Props) {
  const shape = useMemo(() => getPieceShape(piece) as Vec3[], [piece]);
  const allIndices = useMemo(() => uniqueRotationIndices(shape), [shape]);

  // Use provided candidates (placeable-only) if available, otherwise all unique rotations
  const rotIndices = candidateIndices ?? allIndices;

  // Map currentRotIndex to card index by shape equivalence
  const selectedCard = useMemo(() => {
    const currentCells = normalize(applyRotation(shape, currentRotIndex));
    const currentKey = currentCells.map(([x, y, z]) => `${x},${y},${z}`).sort().join('|');
    return rotIndices.findIndex(idx => {
      const cells = normalize(applyRotation(shape, idx));
      const key = cells.map(([x, y, z]) => `${x},${y},${z}`).sort().join('|');
      return key === currentKey;
    });
  }, [shape, currentRotIndex, rotIndices]);

  const count = rotIndices.length;

  // If current rotation is not among candidates (e.g. WASD rotated to non-placeable),
  // show it as-is in the thumbnail but navigate from index 0
  const displayRotIndex = selectedCard >= 0 ? rotIndices[selectedCard] : currentRotIndex;
  const countLabel = selectedCard >= 0 ? `${selectedCard + 1} / ${count}` : `– / ${count}`;

  const goPrev = () => onSelect(rotIndices[(selectedCard <= 0 ? count : selectedCard) - 1]);
  const goNext = () => onSelect(rotIndices[(selectedCard + 1) % count]);

  return (
    <div className="rotation-candidates">
      <div className="rot-nav-row">
        <button
          className="rot-nav-btn"
          onClick={goPrev}
          aria-label="前の姿勢"
        >
          ←
        </button>
        <div className={`rot-canvas-wrap${isFitting ? ' rot-canvas-wrap--fits' : ''}`}>
          <PieceThumbnail piece={piece} rotIndex={displayRotIndex} />
        </div>
        <button
          className="rot-nav-btn"
          onClick={goNext}
          aria-label="次の姿勢"
        >
          →
        </button>
      </div>
      <div className="rot-count-label">
        {countLabel}
      </div>
    </div>
  );
}

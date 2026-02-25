import { useMemo, useRef, useCallback, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { applyRotation, normalize, type Vec3 } from '../utils/rotations';
import { getPieceColor, getPieceShape } from '../constants/pieceColors';

type Props = {
  piece: string;
  rotationIndex: number;
  onRotate: (axis: 'X' | 'Y' | 'Z', dir: 1 | -1) => void;
};

const BOX_SIZE = 0.88;
const DRAG_THRESHOLD = 25; // px before snapping one 90° step

export function PieceStage({ piece, rotationIndex, onRotate }: Props) {
  const color = getPieceColor(piece);

  // Apply rotation to canonical piece shape, then center for display
  const { cells, ox, oy, oz } = useMemo(() => {
    const raw = getPieceShape(piece) as Vec3[];
    if (raw.length === 0) return { cells: [], ox: 0, oy: 0, oz: 0 };

    const rotated = normalize(applyRotation(raw, rotationIndex));
    const maxX = Math.max(...rotated.map(c => c[0]));
    const maxY = Math.max(...rotated.map(c => c[1]));
    const maxZ = Math.max(...rotated.map(c => c[2]));
    return { cells: rotated, ox: maxX / 2, oy: maxY / 2, oz: maxZ / 2 };
  }, [piece, rotationIndex]);

  // ── Drag-to-rotate ──────────────────────────────────────────────
  const dragOrigin = useRef<{ x: number; y: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handlePointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    dragOrigin.current = { x: e.clientX, y: e.clientY };
    setIsDragging(true);
  }, []);

  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragOrigin.current) return;
    const dx = e.clientX - dragOrigin.current.x;
    const dy = e.clientY - dragOrigin.current.y;

    if (Math.abs(dx) >= DRAG_THRESHOLD || Math.abs(dy) >= DRAG_THRESHOLD) {
      if (Math.abs(dx) >= Math.abs(dy)) {
        // Horizontal drag → Y-axis rotation
        onRotate('Y', dx > 0 ? 1 : -1);
      } else {
        // Vertical drag → X-axis rotation
        onRotate('X', dy > 0 ? 1 : -1);
      }
      // Reset anchor to current pointer position
      dragOrigin.current = { x: e.clientX, y: e.clientY };
    }
  }, [onRotate]);

  const handlePointerUp = useCallback(() => {
    dragOrigin.current = null;
    setIsDragging(false);
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', userSelect: 'none' }}>
      <Canvas
        camera={{ position: [4, 4, 4], fov: 40 }}
        style={{ background: '#f0f0f0', width: '100%', height: '100%' }}
      >
        <ambientLight intensity={1.5} />
        <directionalLight position={[5, 8, 5]} intensity={2.0} />
        <directionalLight position={[-3, 2, -3]} intensity={0.5} />
        <group>
          {cells.map(([x, y, z], i) => (
            <mesh
              key={i}
              position={[x - ox, z - oz, y - oy]}
            >
              <boxGeometry args={[BOX_SIZE, BOX_SIZE, BOX_SIZE]} />
              <meshStandardMaterial color={color} roughness={0.6} metalness={0.05} />
            </mesh>
          ))}
        </group>
        {/* Fixed camera — same direction as puzzle viewer [d,d,d].
            Drag events handled on wrapper div → rotationIndex changes via onRotate. */}
      </Canvas>

      {/* Drag-to-rotate overlay — sits above the Canvas so pointer events reach
          this div before R3F's canvas event system can consume them (mobile fix) */}
      <div
        style={{
          position: 'absolute', inset: 0,
          cursor: isDragging ? 'grabbing' : 'grab',
          touchAction: 'none',
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onPointerLeave={handlePointerUp}
      />

      {/* 2D axis gizmo — isometric directions from fixed [4,4,4] camera:
          Puzzle X → screen lower-right (-30°)
          Puzzle Y → screen lower-left  (210°)
          Puzzle Z → screen up          (90°)  */}
      <svg
        width="64" height="64" viewBox="0 0 60 60"
        style={{ position: 'absolute', bottom: 6, left: 6, pointerEvents: 'none', overflow: 'visible' }}
      >
        <circle cx="30" cy="30" r="2" fill="#666" />
        {/* Z — up */}
        <line x1="30" y1="30" x2="30" y2="12" stroke="#3388ff" strokeWidth="2" strokeLinecap="round" />
        <text x="30" y="7" textAnchor="middle" fill="#3388ff" fontSize="11" fontWeight="bold">Z</text>
        {/* X — lower-right */}
        <line x1="30" y1="30" x2="46" y2="39" stroke="#ff3333" strokeWidth="2" strokeLinecap="round" />
        <text x="51" y="44" textAnchor="middle" fill="#ff3333" fontSize="11" fontWeight="bold">X</text>
        {/* Y — lower-left */}
        <line x1="30" y1="30" x2="14" y2="39" stroke="#22cc44" strokeWidth="2" strokeLinecap="round" />
        <text x="9" y="44" textAnchor="middle" fill="#22cc44" fontSize="11" fontWeight="bold">Y</text>
      </svg>
    </div>
  );
}

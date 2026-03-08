import { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { PuzzleVoxels } from './PuzzleVoxels';
import type { PuzzleData } from '../types/puzzle';
import type { Vec3 } from '../utils/rotations';

type CaptureAngle = 'x' | 'y' | null;
type CellFlash = { type: 'error' } | null;

type Props = {
  data: PuzzleData;
  capture?: boolean;
  captureAngle?: CaptureAngle;
  // Game mode props (all optional — capture mode passes none)
  removedPieces?: Set<string>;
  /** coordKey → pieceId: which cells have been filled */
  placedCells?: Map<string, string>;
  /** Currently selected piece */
  selectedPiece?: string | null;
  /** coordKeys of valid click targets for the current rotation */
  validAnchorCells?: Set<string>;
  /** coordKeys of all cells occupied by any valid placement (ghost preview) */
  ghostCells?: Set<string>;
  onEmptyCellClick?: (coord: Vec3) => void;
  cellFlash?: CellFlash;
  phase?: string;
  // Legacy prop for answer/capture mode (hides pieces without placeholders)
  hiddenPieces?: Set<string>;
};

function calcCameraPosition(
  grid: PuzzleData['grid'],
  angle: CaptureAngle
): [number, number, number] {
  const d = Math.max(grid.x, grid.y, grid.z) * 1.8;
  if (angle === 'y') return [-d, d, -d];
  return [d, d, d];
}

export const Viewer = ({
  data,
  capture,
  captureAngle,
  removedPieces,
  placedCells,
  selectedPiece,
  validAnchorCells,
  ghostCells,
  onEmptyCellClick,
  cellFlash,
  hiddenPieces,
}: Props) => {
  const cameraPos = useMemo(
    () => calcCameraPosition(data.grid, captureAngle ?? null),
    [data.grid, captureAngle]
  );

  const bg = capture ? '#ffffff' : '#f5f5f5';

  return (
    <Canvas camera={{ position: cameraPos, fov: 40 }} style={{ background: bg, width: '100%', height: '100%' }}>
      <ambientLight intensity={1.5} />
      <directionalLight position={[5, 8, 5]} intensity={2.0} />
      <directionalLight position={[-5, 3, -5]} intensity={0.8} />
      <directionalLight position={[0, -5, 5]} intensity={0.4} />
      <PuzzleVoxels
        data={data}
        capture={capture}
        removedPieces={removedPieces}
        placedCells={placedCells}
        selectedPiece={selectedPiece}
        validAnchorCells={validAnchorCells}
        ghostCells={ghostCells}
        onEmptyCellClick={onEmptyCellClick}
        cellFlash={cellFlash}
        hiddenPieces={hiddenPieces}
      />
      {!capture && <OrbitControls makeDefault enablePan={true} />}
    </Canvas>
  );
};

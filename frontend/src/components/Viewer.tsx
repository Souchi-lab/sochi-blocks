import { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { PuzzleVoxels } from './PuzzleVoxels';
import type { PuzzleData } from '../types/puzzle';

type CaptureAngle = 'x' | 'y' | null;

type Props = {
  data: PuzzleData;
  hiddenPieces?: Set<string>;
  capture?: boolean;
  captureAngle?: CaptureAngle;
};

function calcCameraPosition(
  grid: PuzzleData['grid'],
  angle: CaptureAngle
): [number, number, number] {
  const d = Math.max(grid.x, grid.y, grid.z) * 1.8;
  if (angle === 'y') return [-d, d, -d];
  return [d, d, d]; // default & angle 'x'
}

export const Viewer = ({ data, hiddenPieces, capture, captureAngle }: Props) => {
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
      <PuzzleVoxels data={data} hiddenPieces={hiddenPieces} capture={capture} />
      {!capture && <OrbitControls makeDefault enablePan={true} />}
    </Canvas>
  );
};

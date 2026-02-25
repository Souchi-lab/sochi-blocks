import { useMemo, useEffect } from 'react';
import * as THREE from 'three';
import { Html } from '@react-three/drei';

type Props = {
  origin: [number, number, number];
  length: number;
};

// Puzzle coordinate → Three.js axis mapping (same swap as PuzzleVoxels):
//   Puzzle X → Three.js (1, 0, 0)  red
//   Puzzle Y → Three.js (0, 0, 1)  green  (puzzle Y is three.js Z)
//   Puzzle Z → Three.js (0, 1, 0)  blue   (puzzle Z is three.js Y)
const AXES = [
  { dir: [1, 0, 0] as [number, number, number], color: 0xff3333, css: '#ff3333', label: 'X', tipAxis: 'x' },
  { dir: [0, 0, 1] as [number, number, number], color: 0x22cc44, css: '#22cc44', label: 'Y', tipAxis: 'z' },
  { dir: [0, 1, 0] as [number, number, number], color: 0x3388ff, css: '#3388ff', label: 'Z', tipAxis: 'y' },
] as const;

export function AxisArrows({ origin, length }: Props) {
  const headLen   = length * 0.35;
  const headWidth = headLen * 0.5;
  const tipOffset = length + headLen * 0.8;
  const [ox, oy, oz] = origin;

  const helpers = useMemo(() => {
    const o = new THREE.Vector3(...origin);
    return AXES.map(({ dir, color }) =>
      new THREE.ArrowHelper(
        new THREE.Vector3(...dir),
        o,
        length,
        color,
        headLen,
        headWidth,
      )
    );
  // origin as tuple is stable — spread deps to trigger on actual value changes
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ox, oy, oz, length, headLen, headWidth]);

  useEffect(() => {
    return () => {
      helpers.forEach((h) => {
        h.line.geometry.dispose();
        h.cone.geometry.dispose();
        (h.line.material as THREE.Material).dispose();
        (h.cone.material as THREE.Material).dispose();
      });
    };
  }, [helpers]);

  const tipPositions: [number, number, number][] = [
    [ox + tipOffset, oy, oz],          // X tip
    [ox, oy, oz + tipOffset],          // Y tip (puzzle Y → three Z)
    [ox, oy + tipOffset, oz],          // Z tip (puzzle Z → three Y)
  ];

  return (
    <group>
      {helpers.map((helper, i) => (
        <primitive key={i} object={helper} />
      ))}
      {AXES.map(({ css, label }, i) => (
        <Html
          key={label}
          position={tipPositions[i]}
          style={{ pointerEvents: 'none' }}
          center
        >
          <span
            style={{
              color: css,
              fontWeight: 'bold',
              fontSize: '12px',
              userSelect: 'none',
              textShadow: '0 0 4px rgba(255,255,255,0.9), 0 0 2px rgba(255,255,255,0.9)',
            }}
          >
            {label}
          </span>
        </Html>
      ))}
    </group>
  );
}

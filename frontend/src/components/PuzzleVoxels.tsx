import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import type { PuzzleData } from '../types/puzzle';
import { getPieceColor } from '../constants/pieceColors';
import type { Vec3 } from '../utils/rotations';

/** Set when an error occurs — causes anchor cells to flash red briefly. */
type CellFlash = { type: 'error' } | null;

type Props = {
  data: PuzzleData;
  capture?: boolean;
  // Legacy: completely hide cells (used by capture mode)
  hiddenPieces?: Set<string>;
  // Game mode props (all optional)
  removedPieces?: Set<string>;
  /** coordKey → pieceId: which cells have been filled and by which piece */
  placedCells?: Map<string, string>;
  /** Currently selected piece (used to color anchor highlights) */
  selectedPiece?: string | null;
  /** coordKeys of valid click targets for the current rotation */
  validAnchorCells?: Set<string>;
  /** coordKeys of all cells occupied by any valid placement (ghost preview) */
  ghostCells?: Set<string>;
  onEmptyCellClick?: (coord: Vec3) => void;
  cellFlash?: CellFlash;
};

const BOX_SIZE = 0.96;

declare global {
  interface Window {
    __CAPTURE_READY__?: boolean;
  }
}

export const PuzzleVoxels = ({
  data,
  capture,
  hiddenPieces,
  removedPieces,
  placedCells,
  selectedPiece,
  validAnchorCells,
  ghostCells,
  onEmptyCellClick,
  cellFlash,
}: Props) => {
  const { grid, cells } = data;
  const flagSet = useRef(false);

  const offset = useMemo(
    () => ({
      x: (grid.x - 1) / 2,
      y: (grid.y - 1) / 2,
      z: (grid.z - 1) / 2,
    }),
    [grid]
  );

  useFrame(() => {
    if (capture && !flagSet.current) {
      flagSet.current = true;
      window.__CAPTURE_READY__ = true;
    }
  });

  return (
    <group>
      {cells.map((cell, i) => {
        if (hiddenPieces?.has(cell.piece)) return null;

        const pos: [number, number, number] = [
          cell.x - offset.x,
          cell.z - offset.z,
          cell.y - offset.y,
        ];

        const coordKey = `${cell.x},${cell.y},${cell.z}`;
        const isRemoved = removedPieces?.has(cell.piece) ?? false;
        const filledBy = placedCells?.get(coordKey);   // pieceId that filled this cell
        const isEmpty = isRemoved && filledBy === undefined;

        if (!isEmpty) {
          // Solid cell — original puzzle block or player-placed block.
          const isPlacedByPlayer = filledBy !== undefined;
          const solidColor = isPlacedByPlayer ? getPieceColor(filledBy) : getPieceColor(cell.piece);
          const hasSelected = selectedPiece != null;

          // Dim only the original puzzle background when a piece is being placed.
          // Player-placed blocks stay fully opaque (confirmed placement).
          const dimBackground = hasSelected && !isPlacedByPlayer;

          return (
            <mesh key={i} position={pos}>
              <boxGeometry args={[BOX_SIZE, BOX_SIZE, BOX_SIZE]} />
              <meshStandardMaterial
                color={dimBackground ? '#a8a8a8' : solidColor}
                transparent={true}
                opacity={dimBackground ? 0.8 : 1}
                depthWrite={!dimBackground}
                roughness={0.6}
                metalness={0.05}
              />
            </mesh>
          );
        }

        // ── Ghost / empty cell ──────────────────────────────────────
        const isAnchor = validAnchorCells?.has(coordKey) ?? false;
        const isGhost = ghostCells?.has(coordKey) ?? false;
        const isFlashing = cellFlash?.type === 'error' && isAnchor;
        const hasSelection = selectedPiece != null;

        // Visual hierarchy (Phase 3 cursor mode):
        //   flashing anchor        → red   (error feedback)
        //   ghost (cursor cells)   → 1.0   (solid preview of piece at cursor position)
        //   anchor (non-cursor)    → 0.35  (dim indicator: other valid anchor positions)
        //   non-ghost + selection  → 0.05  (very dim: empty holes not targeted)
        //   no piece selected      → 0.15  (neutral gray holes)
        const opacity = isFlashing ? 0.85
          : isGhost ? 1.0
            : isAnchor ? 0.35
              : hasSelection ? 0.05
                : 0.15;

        const color = isFlashing ? '#ef4444'
          : (isAnchor || isGhost) ? getPieceColor(selectedPiece!)
            : '#888888';

        return (
          <mesh
            key={i}
            position={pos}
            onClick={(e) => {
              e.stopPropagation();
              onEmptyCellClick?.([cell.x, cell.y, cell.z]);
            }}
          >
            <boxGeometry args={[BOX_SIZE, BOX_SIZE, BOX_SIZE]} />
            <meshStandardMaterial
              color={color}
              opacity={opacity}
              transparent={true}
              roughness={0.8}
              metalness={0.0}
              depthWrite={false}
            />
          </mesh>
        );
      })}
    </group>
  );
};

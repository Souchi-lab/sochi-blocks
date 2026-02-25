/**
 * placement.ts
 *
 * Placement validation and anchor computation.
 *
 * Key concept: "empty cells" are ALL unplaced cells in the removed-pieces region —
 * no per-piece ownership. The player explores where a piece fits geometrically.
 *
 * Anchor model:
 *   The "reference cell" of a piece at a given rotation is the cell at minimum
 *   (z, y, x) in the normalized rotated shape — conceptually its "front-top-left".
 *   validAnchors() returns the empty cells where placing the reference cell would
 *   result in the entire piece fitting within the available empty space.
 *   One highlighted anchor cell = one possible placement → minimal visual clutter.
 */

import { applyRotation, normalize, type Vec3 } from './rotations';

function cellKey(v: Vec3): string {
  return `${v[0]},${v[1]},${v[2]}`;
}

/**
 * Check whether pieceCells (at the given rotation) can be placed such that
 * clickedCell is covered, and all resulting cells fall within emptyCells.
 *
 * @param pieceCells  Canonical shape from master_pieces.json (Vec3[])
 * @param rotIndex    Current rotation index (0–23)
 * @param clickedCell The puzzle cell the player clicked on
 * @param emptyCells  All empty cells belonging to this piece in the puzzle
 */
export function canPlace(
  pieceCells: Vec3[],
  rotIndex: number,
  clickedCell: Vec3,
  emptyCells: Vec3[],
): boolean {
  // Build a fast lookup set for the empty cells
  const emptySet = new Set<string>(emptyCells.map(cellKey));

  // Rotate and normalize the piece shape
  const rotated = normalize(applyRotation(pieceCells, rotIndex));

  // Try each cell of the rotated shape as the anchor
  for (const anchor of rotated) {
    const dx = clickedCell[0] - anchor[0];
    const dy = clickedCell[1] - anchor[1];
    const dz = clickedCell[2] - anchor[2];

    const allFit = rotated.every(([x, y, z]) =>
      emptySet.has(cellKey([x + dx, y + dy, z + dz]))
    );

    if (allFit) return true;
  }

  return false;
}

/**
 * Check whether pieceCells (at the given rotation) fits exactly inside regionCells.
 * Still used by integration tests to validate puzzle data.
 */
export function shapeFitsRegion(
  pieceCells: Vec3[],
  rotIndex: number,
  regionCells: Vec3[],
): boolean {
  if (pieceCells.length !== regionCells.length) return false;
  return canPlace(pieceCells, rotIndex, regionCells[0], regionCells);
}

// ── New-model helpers ────────────────────────────────────────────

/**
 * Canonical reference cell: the min (z, y, x) cell of the normalized rotated
 * piece — its "front-top-left". Used as the single highlighted click target
 * for each valid placement.
 */
function refCellOf(rotated: Vec3[]): Vec3 {
  return [...rotated].sort(
    (a, b) => a[2] - b[2] || a[1] - b[1] || a[0] - b[0]
  )[0];
}

/**
 * Find all empty cells where placing the piece's reference cell produces a
 * fully valid placement (all 5 piece cells inside emptyCells).
 *
 * Returns one Vec3 per distinct valid placement — these are the cells the
 * player should click to place the piece.
 */
export function validAnchors(
  pieceCells: Vec3[],
  rotIndex: number,
  emptyCells: Vec3[],
): Vec3[] {
  if (emptyCells.length === 0 || pieceCells.length === 0) return [];
  const emptySet = new Set<string>(emptyCells.map(cellKey));
  const rotated  = normalize(applyRotation(pieceCells, rotIndex));
  const ref      = refCellOf(rotated);

  return emptyCells.filter(ec => {
    const dx = ec[0] - ref[0];
    const dy = ec[1] - ref[1];
    const dz = ec[2] - ref[2];
    return rotated.every(([x, y, z]) =>
      emptySet.has(cellKey([x + dx, y + dy, z + dz]))
    );
  });
}

/**
 * Given a confirmed anchor cell (from validAnchors), return the exact Vec3[]
 * that the piece would occupy — these cells are marked filled after placement.
 */
export function placementCells(
  pieceCells: Vec3[],
  rotIndex: number,
  anchor: Vec3,
): Vec3[] {
  const rotated = normalize(applyRotation(pieceCells, rotIndex));
  const ref     = refCellOf(rotated);
  const dx = anchor[0] - ref[0];
  const dy = anchor[1] - ref[1];
  const dz = anchor[2] - ref[2];
  return rotated.map(([x, y, z]) => [x + dx, y + dy, z + dz] as Vec3);
}

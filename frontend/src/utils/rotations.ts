/**
 * rotations.ts
 *
 * Algorithmically generates all 24 proper rotation matrices for a 3D integer lattice.
 *
 * Strategy (from the runbook — never hand-write the 24 matrices):
 *   1. Pick newZ from the 6 face directions: ±X, ±Y, ±Z
 *   2. For each newZ, pick newY from all 4 directions perpendicular to newZ
 *   3. newX = cross(newY, newZ)   (guarantees det = +1)
 *   4. Build 3×3 matrix from [newX | newY | newZ] as columns
 *   5. De-duplicate by string key → must yield exactly 24
 */

export type Vec3 = [number, number, number];
export type Mat3 = [
  [number, number, number],
  [number, number, number],
  [number, number, number]
];

// ── Low-level helpers ──────────────────────────────────────────────

function cross(a: Vec3, b: Vec3): Vec3 {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

function matMul(A: Mat3, B: Mat3): Mat3 {
  const result: number[][] = [[0,0,0],[0,0,0],[0,0,0]];
  for (let i = 0; i < 3; i++)
    for (let j = 0; j < 3; j++)
      for (let k = 0; k < 3; k++)
        result[i][j] += A[i][k] * B[k][j];
  return result as Mat3;
}

function matApply(M: Mat3, v: Vec3): Vec3 {
  return [
    M[0][0]*v[0] + M[0][1]*v[1] + M[0][2]*v[2],
    M[1][0]*v[0] + M[1][1]*v[1] + M[1][2]*v[2],
    M[2][0]*v[0] + M[2][1]*v[1] + M[2][2]*v[2],
  ];
}

function matKey(M: Mat3): string {
  return M.flat().join(',');
}

// ── 24-rotation generation ─────────────────────────────────────────

const FACE_DIRS: Vec3[] = [
  [1,0,0], [-1,0,0],
  [0,1,0], [0,-1,0],
  [0,0,1], [0,0,-1],
];

function buildMatrix(newX: Vec3, newY: Vec3, newZ: Vec3): Mat3 {
  // Columns of the rotation matrix = new axis directions
  return [
    [newX[0], newY[0], newZ[0]],
    [newX[1], newY[1], newZ[1]],
    [newX[2], newY[2], newZ[2]],
  ];
}

const IDENTITY: Mat3 = [[1,0,0],[0,1,0],[0,0,1]];
const IDENTITY_KEY = matKey(IDENTITY);

function generateRotations(): Mat3[] {
  const seen = new Map<string, Mat3>();

  for (const newZ of FACE_DIRS) {
    for (const newY of FACE_DIRS) {
      // newY must be perpendicular to newZ (dot product = 0)
      const dot = newY[0]*newZ[0] + newY[1]*newZ[1] + newY[2]*newZ[2];
      if (dot !== 0) continue;

      const newX = cross(newY, newZ);
      const M = buildMatrix(newX, newY, newZ);
      const key = matKey(M);
      if (!seen.has(key)) seen.set(key, M);
    }
  }

  // Ensure identity is always at index 0 (canonical "no rotation" state)
  const all = Array.from(seen.values());
  const identityIdx = all.findIndex(M => matKey(M) === IDENTITY_KEY);
  if (identityIdx > 0) {
    [all[0], all[identityIdx]] = [all[identityIdx], all[0]];
  }
  return all;
}

/** All 24 proper rotation matrices for the integer lattice. Generated algorithmically. */
export const ROTATION_MATRICES: Mat3[] = generateRotations();

// Sanity check at module load (only fires in dev/test — removed in production builds)
if (ROTATION_MATRICES.length !== 24) {
  throw new Error(`Expected 24 rotation matrices, got ${ROTATION_MATRICES.length}`);
}

// ── Public API ─────────────────────────────────────────────────────

/**
 * Apply rotation matrix at rotIndex to each cell coordinate.
 * Does NOT normalize. Call normalize() afterwards if needed.
 */
export function applyRotation(cells: Vec3[], rotIndex: number): Vec3[] {
  const M = ROTATION_MATRICES[rotIndex];
  return cells.map(v => matApply(M, v));
}

/**
 * Translate cells so the minimum coordinate along each axis is 0.
 * This gives a canonical position-independent form for shape comparison.
 */
export function normalize(cells: Vec3[]): Vec3[] {
  const minX = Math.min(...cells.map(c => c[0]));
  const minY = Math.min(...cells.map(c => c[1]));
  const minZ = Math.min(...cells.map(c => c[2]));
  return cells.map(([x, y, z]) => [x - minX, y - minY, z - minZ]);
}

// ── Base 90° rotation matrices for rotateIndex ────────────────────

const R_X90: Mat3 = [[1,0,0],[0,0,-1],[0,1,0]];
const R_Y90: Mat3 = [[0,0,1],[0,1,0],[-1,0,0]];
const R_Z90: Mat3 = [[0,-1,0],[1,0,0],[0,0,1]];

// Build key → index lookup table once
const _matKeyToIndex = new Map<string, number>(
  ROTATION_MATRICES.map((M, i) => [matKey(M), i])
);

/**
 * Given the current rotation index, apply one 90° step around the given axis
 * (dir: +1 = clockwise, -1 = counter-clockwise) and return the new index.
 *
 * Uses: nextMatrix = R_axis^dir × currentMatrix, then looks up in table.
 */
export function rotateIndex(
  current: number,
  axis: 'X' | 'Y' | 'Z',
  dir: 1 | -1
): number {
  const axisMatrix = axis === 'X' ? R_X90 : axis === 'Y' ? R_Y90 : R_Z90;
  const currentM = ROTATION_MATRICES[current];

  let stepped: Mat3;
  if (dir === 1) {
    stepped = matMul(axisMatrix, currentM);
  } else {
    // dir === -1: multiply by the inverse (= transpose for rotation matrices)
    const axisInv: Mat3 = [
      [axisMatrix[0][0], axisMatrix[1][0], axisMatrix[2][0]],
      [axisMatrix[0][1], axisMatrix[1][1], axisMatrix[2][1]],
      [axisMatrix[0][2], axisMatrix[1][2], axisMatrix[2][2]],
    ];
    stepped = matMul(axisInv, currentM);
  }

  const key = matKey(stepped);
  const idx = _matKeyToIndex.get(key);
  if (idx === undefined) throw new Error(`rotateIndex: result not in table (key=${key})`);
  return idx;
}

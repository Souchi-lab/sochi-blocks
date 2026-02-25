import { describe, it, expect } from 'vitest';
import {
  ROTATION_MATRICES,
  applyRotation,
  normalize,
  rotateIndex,
  type Mat3,
  type Vec3,
} from '../rotations';

// ── Helpers ──────────────────────────────────────────────────────

function det3(M: Mat3): number {
  return (
    M[0][0] * (M[1][1]*M[2][2] - M[1][2]*M[2][1]) -
    M[0][1] * (M[1][0]*M[2][2] - M[1][2]*M[2][0]) +
    M[0][2] * (M[1][0]*M[2][1] - M[1][1]*M[2][0])
  );
}

function matMul(A: Mat3, B: Mat3): Mat3 {
  const R: number[][] = [[0,0,0],[0,0,0],[0,0,0]];
  for (let i = 0; i < 3; i++)
    for (let j = 0; j < 3; j++)
      for (let k = 0; k < 3; k++)
        R[i][j] += A[i][k] * B[k][j];
  return R as Mat3;
}

function isIdentity(M: Mat3): boolean {
  for (let i = 0; i < 3; i++)
    for (let j = 0; j < 3; j++) {
      const expected = i === j ? 1 : 0;
      if (Math.abs(M[i][j] - expected) > 1e-9) return false;
    }
  return true;
}

function matKey(M: Mat3): string {
  return M.flat().join(',');
}

// ── Tests ─────────────────────────────────────────────────────────

describe('ROTATION_MATRICES', () => {
  it('has exactly 24 entries', () => {
    expect(ROTATION_MATRICES).toHaveLength(24);
  });

  it('all matrices have det = +1', () => {
    for (const M of ROTATION_MATRICES) {
      expect(det3(M)).toBeCloseTo(1, 9);
    }
  });

  it('all matrices are orthogonal (M^T M = I)', () => {
    for (const M of ROTATION_MATRICES) {
      const MT = [
        [M[0][0], M[1][0], M[2][0]],
        [M[0][1], M[1][1], M[2][1]],
        [M[0][2], M[1][2], M[2][2]],
      ] as Mat3;
      const prod = matMul(MT, M);
      expect(isIdentity(prod)).toBe(true);
    }
  });

  it('all entries are integers', () => {
    for (const M of ROTATION_MATRICES)
      for (const row of M)
        for (const v of row)
          expect(Number.isInteger(v)).toBe(true);
  });

  it('are all unique', () => {
    const keys = new Set(ROTATION_MATRICES.map(matKey));
    expect(keys.size).toBe(24);
  });

  it('are closed under composition (group property)', () => {
    const keys = new Set(ROTATION_MATRICES.map(matKey));
    for (const A of ROTATION_MATRICES) {
      for (const B of ROTATION_MATRICES) {
        const AB = matMul(A, B);
        expect(keys.has(matKey(AB))).toBe(true);
      }
    }
  });
});

describe('applyRotation', () => {
  it('applies rotation 0 (identity) without changing cells', () => {
    const cells: Vec3[] = [[1,0,0],[0,1,0],[0,0,1]];
    expect(applyRotation(cells, 0)).toEqual(cells);
  });

  it('output is always integer coordinates', () => {
    const cells: Vec3[] = [[2,1,0],[1,2,3]];
    for (let i = 0; i < 24; i++) {
      const rotated = applyRotation(cells, i);
      for (const [x,y,z] of rotated) {
        expect(Number.isInteger(x)).toBe(true);
        expect(Number.isInteger(y)).toBe(true);
        expect(Number.isInteger(z)).toBe(true);
      }
    }
  });
});

describe('normalize', () => {
  it('shifts min coordinate to 0 on each axis', () => {
    const cells: Vec3[] = [[3,4,5],[4,5,6],[5,6,7]];
    const n = normalize(cells);
    expect(Math.min(...n.map(c => c[0]))).toBe(0);
    expect(Math.min(...n.map(c => c[1]))).toBe(0);
    expect(Math.min(...n.map(c => c[2]))).toBe(0);
  });

  it('preserves relative positions', () => {
    const cells: Vec3[] = [[2,0,0],[3,0,0],[4,0,0]];
    const n = normalize(cells);
    expect(n).toEqual([[0,0,0],[1,0,0],[2,0,0]]);
  });

  it('is idempotent', () => {
    const cells: Vec3[] = [[0,1,2],[2,3,4]];
    expect(normalize(normalize(cells))).toEqual(normalize(cells));
  });
});

describe('rotateIndex', () => {
  it('returns a valid index (0–23)', () => {
    for (let i = 0; i < 24; i++) {
      for (const axis of ['X', 'Y', 'Z'] as const) {
        const next = rotateIndex(i, axis, 1);
        expect(next).toBeGreaterThanOrEqual(0);
        expect(next).toBeLessThan(24);
      }
    }
  });

  it('round-trip: 4 × 90° rotations returns to original index', () => {
    for (const axis of ['X', 'Y', 'Z'] as const) {
      for (let start = 0; start < 24; start++) {
        let idx = start;
        for (let step = 0; step < 4; step++) idx = rotateIndex(idx, axis, 1);
        expect(idx).toBe(start);
      }
    }
  });

  it('+1 and -1 are inverses', () => {
    for (const axis of ['X', 'Y', 'Z'] as const) {
      for (let i = 0; i < 24; i++) {
        const forward = rotateIndex(i, axis, 1);
        const back    = rotateIndex(forward, axis, -1);
        expect(back).toBe(i);
      }
    }
  });
});

import { describe, it, expect } from 'vitest';
import { canPlace, shapeFitsRegion, validAnchors, placementCells } from '../placement';
import { ROTATION_MATRICES, normalize, applyRotation, type Vec3 } from '../rotations';

// ── Helpers ──────────────────────────────────────────────────────

/** Build emptyCells by rotating a canonical shape and placing it at an offset. */
function makeEmpty(shape: Vec3[], rotIndex: number, offset: Vec3): Vec3[] {
  const rotated = normalize(applyRotation(shape, rotIndex));
  return rotated.map(([x, y, z]) => [x + offset[0], y + offset[1], z + offset[2]]);
}

// ── Test shapes ───────────────────────────────────────────────────

// L-shaped piece: 4 cells in a line + 1 corner
const L_SHAPE: Vec3[] = [[0,0,0],[1,0,0],[2,0,0],[3,0,0],[3,1,0]];

// Simple 1×1×5 bar (I-type, highly symmetric)
const I_SHAPE: Vec3[] = [[0,0,0],[1,0,0],[2,0,0],[3,0,0],[4,0,0]];

// 3D piece: staircase
const STAIR_3D: Vec3[] = [[0,0,0],[1,0,0],[1,1,0],[1,1,1]];

// ── Tests ─────────────────────────────────────────────────────────

describe('canPlace', () => {
  describe('correct rotation → true', () => {
    it('rotation 0 at origin: clicking any cell returns true', () => {
      const emptyCells = makeEmpty(L_SHAPE, 0, [0,0,0]);
      for (const cell of emptyCells) {
        expect(canPlace(L_SHAPE, 0, cell, emptyCells)).toBe(true);
      }
    });

    it('correct rotation with offset: clicking any cell returns true', () => {
      const ROT = 3;
      const offset: Vec3 = [5, 2, 1];
      const emptyCells = makeEmpty(L_SHAPE, ROT, offset);
      for (const cell of emptyCells) {
        expect(canPlace(L_SHAPE, ROT, cell, emptyCells)).toBe(true);
      }
    });

    it('works for all 24 rotations of L-shape', () => {
      for (let rot = 0; rot < 24; rot++) {
        const offset: Vec3 = [10, 10, 10];
        const emptyCells = makeEmpty(L_SHAPE, rot, offset);
        // Click the first empty cell
        expect(canPlace(L_SHAPE, rot, emptyCells[0], emptyCells)).toBe(true);
      }
    });
  });

  describe('wrong rotation → false', () => {
    it('rotation 0 piece does not fit rotation-1 empty cells', () => {
      // Build emptyCells using rotation 1
      const emptyCells = makeEmpty(L_SHAPE, 1, [0,0,0]);
      // Attempt placement with rotation 0 (different shape orientation)
      // Click on a cell that is in emptyCells
      const clickedCell = emptyCells[0];
      // Only true if rotations 0 and 1 produce the same normalized shape
      const rot0Shape = normalize(applyRotation(L_SHAPE, 0));
      const rot1Shape = normalize(applyRotation(L_SHAPE, 1));
      const isSameShape = JSON.stringify(
        rot0Shape.map(v => v.join(',')).sort()
      ) === JSON.stringify(
        rot1Shape.map(v => v.join(',')).sort()
      );
      if (!isSameShape) {
        expect(canPlace(L_SHAPE, 0, clickedCell, emptyCells)).toBe(false);
      }
      // (if same shape, this rotation pair is symmetric — skip)
    });
  });

  describe('wrong region → false', () => {
    it('clicking outside emptyCells always returns false', () => {
      const emptyCells = makeEmpty(L_SHAPE, 0, [0,0,0]);
      const outsideCell: Vec3 = [99, 99, 99];
      expect(canPlace(L_SHAPE, 0, outsideCell, emptyCells)).toBe(false);
    });

    it('emptyCells belongs to a different piece region', () => {
      const emptyForL = makeEmpty(L_SHAPE, 0, [0,0,0]);
      // Provide I-shape cells as emptyCells, but click on L-shape cells
      const emptyForI = makeEmpty(I_SHAPE, 0, [10,0,0]);
      expect(canPlace(L_SHAPE, 0, emptyForI[0], emptyForI)).toBe(false);
    });
  });

  describe('symmetric pieces (I-shape) → true for all matching orientations', () => {
    it('I-shape: all rotations that produce the same normalized shape should pass', () => {
      const baseEmpty = makeEmpty(I_SHAPE, 0, [0,0,0]);
      const baseShape = normalize(applyRotation(I_SHAPE, 0));
      const baseKey = JSON.stringify(baseShape.map(v => v.join(',')).sort());

      let hitCount = 0;
      for (let rot = 0; rot < 24; rot++) {
        const rotShape = normalize(applyRotation(I_SHAPE, rot));
        const rotKey = JSON.stringify(rotShape.map(v => v.join(',')).sort());
        if (rotKey === baseKey) {
          hitCount++;
          expect(canPlace(I_SHAPE, rot, baseEmpty[0], baseEmpty)).toBe(true);
        }
      }
      // I-shape along X has multiple symmetric rotations
      expect(hitCount).toBeGreaterThan(1);
    });
  });

  describe('3D staircase piece', () => {
    it('correct rotation and region returns true', () => {
      for (let rot = 0; rot < 24; rot++) {
        const offset: Vec3 = [3, 3, 3];
        const emptyCells = makeEmpty(STAIR_3D, rot, offset);
        expect(canPlace(STAIR_3D, rot, emptyCells[0], emptyCells)).toBe(true);
      }
    });
  });
});

describe('shapeFitsRegion', () => {
  it('returns true when rotation matches the region exactly', () => {
    for (let rot = 0; rot < 24; rot++) {
      const region = makeEmpty(L_SHAPE, rot, [5, 2, 1]);
      expect(shapeFitsRegion(L_SHAPE, rot, region)).toBe(true);
    }
  });

  it('returns false when cell count differs', () => {
    const region = makeEmpty(L_SHAPE, 0, [0, 0, 0]);
    const shorterShape: Vec3[] = [[0,0,0],[1,0,0],[2,0,0]]; // 3 cells vs 5
    expect(shapeFitsRegion(shorterShape, 0, region)).toBe(false);
  });

  it('returns false when rotation does not match region shape', () => {
    const rot0region = makeEmpty(L_SHAPE, 0, [0, 0, 0]);
    // Find a rotation that produces a genuinely different shape
    let foundMismatch = false;
    for (let rot = 1; rot < 24; rot++) {
      const rot0shape = normalize(applyRotation(L_SHAPE, 0));
      const rotNshape = normalize(applyRotation(L_SHAPE, rot));
      const same = JSON.stringify(rot0shape.map(v => v.join(',')).sort()) ===
                   JSON.stringify(rotNshape.map(v => v.join(',')).sort());
      if (!same) {
        expect(shapeFitsRegion(L_SHAPE, rot, rot0region)).toBe(false);
        foundMismatch = true;
        break;
      }
    }
    expect(foundMismatch).toBe(true);
  });

  it('3D staircase: correct rotation fits its own region for all 24 rotations', () => {
    for (let rot = 0; rot < 24; rot++) {
      const region = makeEmpty(STAIR_3D, rot, [1, 1, 1]);
      expect(shapeFitsRegion(STAIR_3D, rot, region)).toBe(true);
    }
  });
});

// ── validAnchors ──────────────────────────────────────────────────

describe('validAnchors', () => {
  it('returns exactly one anchor when piece fits exactly in its own region', () => {
    const emptyCells = makeEmpty(L_SHAPE, 0, [0, 0, 0]);
    const anchors = validAnchors(L_SHAPE, 0, emptyCells);
    expect(anchors.length).toBe(1);
  });

  it('anchor cell is within the provided empty cells', () => {
    const offset: Vec3 = [3, 2, 1];
    const emptyCells = makeEmpty(L_SHAPE, 0, offset);
    const anchors = validAnchors(L_SHAPE, 0, emptyCells);
    const emptyKeys = new Set(emptyCells.map(([x, y, z]) => `${x},${y},${z}`));
    for (const [ax, ay, az] of anchors) {
      expect(emptyKeys.has(`${ax},${ay},${az}`)).toBe(true);
    }
  });

  it('returns empty array when no rotation fits', () => {
    // emptyCells built from rot 0, try a different rotation that makes a different shape
    const emptyCells = makeEmpty(L_SHAPE, 0, [0, 0, 0]);
    let foundMismatch = false;
    for (let rot = 1; rot < 24; rot++) {
      const rot0shape = normalize(applyRotation(L_SHAPE, 0));
      const rotNshape = normalize(applyRotation(L_SHAPE, rot));
      const same = JSON.stringify(rot0shape.map(v => v.join(',')).sort()) ===
                   JSON.stringify(rotNshape.map(v => v.join(',')).sort());
      if (!same) {
        expect(validAnchors(L_SHAPE, rot, emptyCells)).toHaveLength(0);
        foundMismatch = true;
        break;
      }
    }
    expect(foundMismatch).toBe(true);
  });

  it('returns empty array when emptyCells is empty', () => {
    expect(validAnchors(L_SHAPE, 0, [])).toHaveLength(0);
  });

  it('returns multiple anchors when piece fits in multiple positions', () => {
    // I-shape along X in a 10-cell-long row: 6 valid placements (positions 0..5)
    const row: Vec3[] = Array.from({ length: 10 }, (_, i) => [i, 0, 0] as Vec3);
    const anchors = validAnchors(I_SHAPE, 0, row);
    // I_SHAPE has 5 cells; 10-cell row → 10-5+1 = 6 valid start positions
    expect(anchors.length).toBe(6);
  });

  it('works for all 24 rotations of L-shape placed at exact region', () => {
    for (let rot = 0; rot < 24; rot++) {
      const emptyCells = makeEmpty(L_SHAPE, rot, [5, 5, 5]);
      const anchors = validAnchors(L_SHAPE, rot, emptyCells);
      expect(anchors.length).toBeGreaterThanOrEqual(1);
    }
  });
});

// ── placementCells ────────────────────────────────────────────────

describe('placementCells', () => {
  it('returns exactly piece-size cells', () => {
    const emptyCells = makeEmpty(L_SHAPE, 0, [0, 0, 0]);
    const anchors = validAnchors(L_SHAPE, 0, emptyCells);
    expect(anchors.length).toBeGreaterThan(0);
    const cells = placementCells(L_SHAPE, 0, anchors[0]);
    expect(cells.length).toBe(L_SHAPE.length);
  });

  it('returned cells all fall within the empty cells', () => {
    for (let rot = 0; rot < 24; rot++) {
      const offset: Vec3 = [4, 3, 2];
      const emptyCells = makeEmpty(L_SHAPE, rot, offset);
      const emptyKeys = new Set(emptyCells.map(([x, y, z]) => `${x},${y},${z}`));
      const anchors = validAnchors(L_SHAPE, rot, emptyCells);
      for (const anchor of anchors) {
        const cells = placementCells(L_SHAPE, rot, anchor);
        for (const [x, y, z] of cells) {
          expect(emptyKeys.has(`${x},${y},${z}`)).toBe(true);
        }
      }
    }
  });

  it('validAnchors + placementCells round-trip: placed cells cover entire region', () => {
    // When the empty region is exactly 1 piece-worth of cells,
    // the single anchor's placementCells should exactly equal the empty cells.
    const emptyCells = makeEmpty(STAIR_3D, 3, [2, 2, 2]);
    const anchors = validAnchors(STAIR_3D, 3, emptyCells);
    expect(anchors.length).toBe(1);
    const cells = placementCells(STAIR_3D, 3, anchors[0]);
    const cellKeys = new Set(cells.map(([x, y, z]) => `${x},${y},${z}`));
    const emptyKeys = new Set(emptyCells.map(([x, y, z]) => `${x},${y},${z}`));
    expect(cellKeys).toEqual(emptyKeys);
  });
});

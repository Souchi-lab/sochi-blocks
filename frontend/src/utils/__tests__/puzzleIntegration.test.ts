/**
 * Integration test: verify shapeFitsRegion correctly finds at least one valid
 * rotation for every removed piece in every real puzzle JSON file.
 *
 * Reads master_pieces.json and all puzzle_*.json files directly from public/,
 * which is the same data the production app uses.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { shapeFitsRegion } from '../placement';
import type { Vec3 } from '../rotations';

// ── Path helpers ─────────────────────────────────────────────────

const __filename = fileURLToPath(import.meta.url);
const __dir = dirname(__filename);
const PUBLIC = resolve(__dir, '../../../public');

function readJson<T>(relPath: string): T {
  return JSON.parse(readFileSync(resolve(PUBLIC, relPath), 'utf-8')) as T;
}

// ── Load data ────────────────────────────────────────────────────

type MasterPiece = { id: string; shape_json: number[][] };
type PuzzleCell  = { x: number; y: number; z: number; piece: string };
type PuzzleGrid  = { x: number; y: number; z: number };
type PuzzleData  = { puzzle_id: string; grid: PuzzleGrid; cells: PuzzleCell[]; removed_pieces?: string[] };

const masterList = readJson<MasterPiece[]>('colors/master_pieces.json');
const masterMap  = new Map(masterList.map(p => [p.id, p.shape_json as Vec3[]]));

const puzzleDir = resolve(PUBLIC, 'puzzles');
const puzzleFiles = readdirSync(puzzleDir).filter(f => f.endsWith('.json'));
const puzzles = puzzleFiles.map(f =>
  readJson<PuzzleData>(`puzzles/${f}`)
);

// ── Helpers ──────────────────────────────────────────────────────

/** Extract the 3D region (all cells of a given piece) from a puzzle. */
function regionOf(puzzle: PuzzleData, pieceId: string): Vec3[] {
  return puzzle.cells
    .filter(c => c.piece === pieceId)
    .map(c => [c.x, c.y, c.z] as Vec3);
}

// ── Tests ─────────────────────────────────────────────────────────

describe('shapeFitsRegion — real puzzle data', () => {
  it('master_pieces.json has at least one piece entry', () => {
    expect(masterList.length).toBeGreaterThan(0);
  });

  it('all puzzle files load without error', () => {
    expect(puzzles.length).toBeGreaterThan(0);
  });

  for (const puzzle of puzzles) {
    const removed = puzzle.removed_pieces ?? [];
    if (removed.length === 0) continue;

    describe(`puzzle ${puzzle.puzzle_id} (${removed.length} removed: ${removed.join(', ')})`, () => {
      for (const pieceId of removed) {
        it(`piece ${pieceId}: at least one of 24 rotations fits its region`, () => {
          const canonical = masterMap.get(pieceId);
          expect(canonical, `piece ${pieceId} not in master_pieces.json`).toBeDefined();

          const region = regionOf(puzzle, pieceId);
          expect(region.length, `region for ${pieceId} is empty in puzzle`).toBeGreaterThan(0);
          expect(
            region.length,
            `canonical length ${canonical!.length} ≠ region length ${region.length}`
          ).toBe(canonical!.length);

          // At least ONE rotation must fit the region
          let foundRot = -1;
          for (let r = 0; r < 24; r++) {
            if (shapeFitsRegion(canonical!, r, region)) {
              foundRot = r;
              break;
            }
          }
          expect(
            foundRot,
            `no rotation of piece ${pieceId} fits its region in puzzle ${puzzle.puzzle_id}`
          ).toBeGreaterThanOrEqual(0);
        });
      }
    });
  }
});

// ── Data integrity tests ──────────────────────────────────────────

describe('puzzle data integrity', () => {
  for (const puzzle of puzzles) {
    describe(`puzzle ${puzzle.puzzle_id}`, () => {
      it('all cell piece IDs exist in master_pieces.json', () => {
        for (const cell of puzzle.cells) {
          expect(
            masterMap.has(cell.piece),
            `piece '${cell.piece}' at (${cell.x},${cell.y},${cell.z}) not in master_pieces.json`
          ).toBe(true);
        }
      });

      it('all cell coordinates are within grid bounds', () => {
        const { x: gx, y: gy, z: gz } = puzzle.grid;
        for (const cell of puzzle.cells) {
          expect(cell.x, `x=${cell.x} out of [0,${gx-1}]`).toBeGreaterThanOrEqual(0);
          expect(cell.x, `x=${cell.x} out of [0,${gx-1}]`).toBeLessThan(gx);
          expect(cell.y, `y=${cell.y} out of [0,${gy-1}]`).toBeGreaterThanOrEqual(0);
          expect(cell.y, `y=${cell.y} out of [0,${gy-1}]`).toBeLessThan(gy);
          expect(cell.z, `z=${cell.z} out of [0,${gz-1}]`).toBeGreaterThanOrEqual(0);
          expect(cell.z, `z=${cell.z} out of [0,${gz-1}]`).toBeLessThan(gz);
        }
      });

      it('cell count equals grid volume (fully packed)', () => {
        const { x: gx, y: gy, z: gz } = puzzle.grid;
        expect(puzzle.cells.length).toBe(gx * gy * gz);
      });

      it('no duplicate cell coordinates', () => {
        const keys = new Set(puzzle.cells.map(c => `${c.x},${c.y},${c.z}`));
        expect(keys.size).toBe(puzzle.cells.length);
      });

      if ((puzzle.removed_pieces ?? []).length > 0) {
        it('all removed_pieces IDs appear in cells', () => {
          const pieceIds = new Set(puzzle.cells.map(c => c.piece));
          for (const rp of puzzle.removed_pieces!) {
            expect(
              pieceIds.has(rp),
              `removed piece '${rp}' has no cells in puzzle`
            ).toBe(true);
          }
        });
      }
    });
  }
});

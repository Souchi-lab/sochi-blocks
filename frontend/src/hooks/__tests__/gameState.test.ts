import { describe, it, expect } from 'vitest';
import { gameReducer, initialState } from '../useGameState';
import type { GameState } from '../useGameState';

// ── Helpers ───────────────────────────────────────────────────────

function makeState(overrides: Partial<GameState> = {}): GameState {
  return { ...initialState(['F', 'I']), ...overrides };
}

// ── initialState ─────────────────────────────────────────────────

describe('initialState', () => {
  it('phase is playing when removed pieces exist', () => {
    const s = initialState(['F', 'I']);
    expect(s.phase).toBe('playing');
    expect(s.removedPieces).toEqual(['F', 'I']);
    expect(s.placedPieces.size).toBe(0);
    expect(s.selectedPiece).toBeNull();
    expect(s.rotationIndex).toBe(0);
    expect(s.mistakeCount).toBe(0);
  });

  it('phase is idle when no removed pieces', () => {
    const s = initialState([]);
    expect(s.phase).toBe('idle');
  });
});

// ── SELECT_PIECE ─────────────────────────────────────────────────

describe('SELECT_PIECE', () => {
  it('selects a piece and resets rotationIndex', () => {
    const s = makeState({ rotationIndex: 5 });
    const next = gameReducer(s, { type: 'SELECT_PIECE', piece: 'F' });
    expect(next.selectedPiece).toBe('F');
    expect(next.rotationIndex).toBe(0);
  });

  it('deselects if same piece clicked again (toggle)', () => {
    const s = makeState({ selectedPiece: 'F' });
    const next = gameReducer(s, { type: 'SELECT_PIECE', piece: 'F' });
    expect(next.selectedPiece).toBeNull();
    expect(next.rotationIndex).toBe(0);
  });

  it('switches selection from one piece to another', () => {
    const s = makeState({ selectedPiece: 'F', rotationIndex: 3 });
    const next = gameReducer(s, { type: 'SELECT_PIECE', piece: 'I' });
    expect(next.selectedPiece).toBe('I');
    expect(next.rotationIndex).toBe(0); // reset on switch
  });

  it('does not mutate other state fields', () => {
    const s = makeState({ mistakeCount: 2, phase: 'playing' });
    const next = gameReducer(s, { type: 'SELECT_PIECE', piece: 'F' });
    expect(next.mistakeCount).toBe(2);
    expect(next.phase).toBe('playing');
  });
});

// ── PLACE_PIECE ──────────────────────────────────────────────────

describe('PLACE_PIECE', () => {
  const COORDS = ['1,2,0', '1,3,0', '2,2,0'];

  it('adds piece to placedPieces and clears selection', () => {
    const s = makeState({ selectedPiece: 'F', rotationIndex: 7 });
    const next = gameReducer(s, { type: 'PLACE_PIECE', piece: 'F', coords: COORDS });
    expect(next.placedPieces.has('F')).toBe(true);
    expect(next.selectedPiece).toBeNull();
    expect(next.rotationIndex).toBe(0);
  });

  it('records filled coords in placedCells with correct pieceId', () => {
    const s = makeState();
    const next = gameReducer(s, { type: 'PLACE_PIECE', piece: 'F', coords: COORDS });
    for (const coord of COORDS) {
      expect(next.placedCells.get(coord)).toBe('F');
    }
    expect(next.placedCells.size).toBe(COORDS.length);
  });

  it('phase stays playing when pieces remain unplaced', () => {
    const s = makeState();
    const next = gameReducer(s, { type: 'PLACE_PIECE', piece: 'F', coords: COORDS });
    expect(next.phase).toBe('playing');
    expect(next.placedPieces.size).toBe(1);
  });

  it('phase becomes victory when last piece is placed', () => {
    const s = makeState({ placedPieces: new Set(['F']), placedCells: new Map([['0,0,0', 'F']]) });
    const next = gameReducer(s, { type: 'PLACE_PIECE', piece: 'I', coords: ['1,0,0'] });
    expect(next.phase).toBe('victory');
    expect(next.placedPieces.size).toBe(2);
  });

  it('does not mutate the original placedPieces Set', () => {
    const s = makeState();
    const original = s.placedPieces;
    gameReducer(s, { type: 'PLACE_PIECE', piece: 'F', coords: COORDS });
    expect(original.has('F')).toBe(false);
  });

  it('does not mutate the original placedCells Map', () => {
    const s = makeState();
    const original = s.placedCells;
    gameReducer(s, { type: 'PLACE_PIECE', piece: 'F', coords: COORDS });
    expect(original.size).toBe(0);
  });

  it('placing single-piece puzzle immediately triggers victory', () => {
    const s = initialState(['X']);
    const next = gameReducer(s, { type: 'PLACE_PIECE', piece: 'X', coords: COORDS });
    expect(next.phase).toBe('victory');
  });
});

// ── UNPLACE_PIECE ─────────────────────────────────────────────────

describe('UNPLACE_PIECE', () => {
  const COORDS = ['1,2,0', '1,3,0', '2,2,0'];

  function stateAfterPlace(): GameState {
    const s = makeState();
    return gameReducer(s, { type: 'PLACE_PIECE', piece: 'F', coords: COORDS });
  }

  it('removes piece from placedPieces', () => {
    const s = stateAfterPlace();
    const next = gameReducer(s, { type: 'UNPLACE_PIECE', piece: 'F' });
    expect(next.placedPieces.has('F')).toBe(false);
  });

  it('removes the piece cells from placedCells', () => {
    const s = stateAfterPlace();
    const next = gameReducer(s, { type: 'UNPLACE_PIECE', piece: 'F' });
    for (const coord of COORDS) {
      expect(next.placedCells.has(coord)).toBe(false);
    }
    expect(next.placedCells.size).toBe(0);
  });

  it('selects the unplaced piece and resets rotationIndex', () => {
    const s = gameReducer(stateAfterPlace(), { type: 'ROTATE', axis: 'X', dir: 1 });
    const next = gameReducer(s, { type: 'UNPLACE_PIECE', piece: 'F' });
    expect(next.selectedPiece).toBe('F');
    expect(next.rotationIndex).toBe(0);
  });

  it('sets phase back to playing even if all pieces had been placed', () => {
    // Place both pieces → victory, then unplace one
    let s = makeState();
    s = gameReducer(s, { type: 'PLACE_PIECE', piece: 'F', coords: ['0,0,0'] });
    s = gameReducer(s, { type: 'PLACE_PIECE', piece: 'I', coords: ['1,0,0'] });
    expect(s.phase).toBe('victory');

    const next = gameReducer(s, { type: 'UNPLACE_PIECE', piece: 'F' });
    expect(next.phase).toBe('playing');
    expect(next.placedPieces.has('F')).toBe(false);
    expect(next.placedPieces.has('I')).toBe(true);
  });

  it('does not mutate the original placedPieces Set', () => {
    const s = stateAfterPlace();
    const original = s.placedPieces;
    gameReducer(s, { type: 'UNPLACE_PIECE', piece: 'F' });
    expect(original.has('F')).toBe(true);
  });

  it('does not mutate the original placedCells Map', () => {
    const s = stateAfterPlace();
    const original = s.placedCells;
    gameReducer(s, { type: 'UNPLACE_PIECE', piece: 'F' });
    expect(original.size).toBe(COORDS.length);
  });

  it('only removes cells belonging to the unplaced piece', () => {
    let s = makeState();
    s = gameReducer(s, { type: 'PLACE_PIECE', piece: 'F', coords: ['0,0,0', '1,0,0'] });
    s = gameReducer(s, { type: 'PLACE_PIECE', piece: 'I', coords: ['2,0,0', '3,0,0'] });
    const next = gameReducer(s, { type: 'UNPLACE_PIECE', piece: 'F' });
    expect(next.placedCells.has('0,0,0')).toBe(false);
    expect(next.placedCells.has('1,0,0')).toBe(false);
    expect(next.placedCells.get('2,0,0')).toBe('I');
    expect(next.placedCells.get('3,0,0')).toBe('I');
  });
});

// ── WRONG_CLICK ──────────────────────────────────────────────────

describe('WRONG_CLICK', () => {
  it('increments mistakeCount', () => {
    const s = makeState({ mistakeCount: 0 });
    const next = gameReducer(s, { type: 'WRONG_CLICK' });
    expect(next.mistakeCount).toBe(1);
  });

  it('does not change selection or placement', () => {
    const s = makeState({ selectedPiece: 'F', placedPieces: new Set(['I']) });
    const next = gameReducer(s, { type: 'WRONG_CLICK' });
    expect(next.selectedPiece).toBe('F');
    expect(next.placedPieces.has('I')).toBe(true);
  });

  it('accumulates multiple mistakes', () => {
    let s = makeState();
    s = gameReducer(s, { type: 'WRONG_CLICK' });
    s = gameReducer(s, { type: 'WRONG_CLICK' });
    s = gameReducer(s, { type: 'WRONG_CLICK' });
    expect(s.mistakeCount).toBe(3);
  });
});

// ── ROTATE ───────────────────────────────────────────────────────

describe('ROTATE', () => {
  it('changes rotationIndex from identity (0) with X+1', () => {
    const s = makeState({ rotationIndex: 0 });
    const next = gameReducer(s, { type: 'ROTATE', axis: 'X', dir: 1 });
    expect(next.rotationIndex).not.toBe(0); // X+1 from 0 gives non-identity
    expect(next.rotationIndex).toBeGreaterThanOrEqual(0);
    expect(next.rotationIndex).toBeLessThan(24);
  });

  it('round-trip 4 rotations on same axis returns to start', () => {
    let s = makeState({ rotationIndex: 0 });
    // Four 90° rotations around X should return to identity
    for (let i = 0; i < 4; i++) {
      s = gameReducer(s, { type: 'ROTATE', axis: 'X', dir: 1 });
    }
    expect(s.rotationIndex).toBe(0);
  });

  it('does not change other fields', () => {
    const s = makeState({ selectedPiece: 'F', mistakeCount: 2 });
    const next = gameReducer(s, { type: 'ROTATE', axis: 'Y', dir: -1 });
    expect(next.selectedPiece).toBe('F');
    expect(next.mistakeCount).toBe(2);
  });
});

// ── RESET_ROTATION ───────────────────────────────────────────────

describe('RESET_ROTATION', () => {
  it('sets rotationIndex back to 0', () => {
    const s = makeState({ rotationIndex: 13 });
    const next = gameReducer(s, { type: 'RESET_ROTATION' });
    expect(next.rotationIndex).toBe(0);
  });

  it('does not change other fields', () => {
    const s = makeState({ selectedPiece: 'F', mistakeCount: 4, rotationIndex: 5 });
    const next = gameReducer(s, { type: 'RESET_ROTATION' });
    expect(next.selectedPiece).toBe('F');
    expect(next.mistakeCount).toBe(4);
    expect(next.phase).toBe('playing');
  });
});

// ── RESTART ──────────────────────────────────────────────────────

describe('RESTART', () => {
  it('resets all state to initial with same removed pieces', () => {
    const s = makeState({
      selectedPiece: 'F',
      placedPieces: new Set(['I']),
      rotationIndex: 7,
      mistakeCount: 3,
      phase: 'victory',
    });
    const next = gameReducer(s, { type: 'RESTART' });
    expect(next.selectedPiece).toBeNull();
    expect(next.placedPieces.size).toBe(0);
    expect(next.rotationIndex).toBe(0);
    expect(next.mistakeCount).toBe(0);
    expect(next.phase).toBe('playing');
    expect(next.removedPieces).toEqual(['F', 'I']);
  });

  it('replaces removed pieces if payload provides new ones', () => {
    const s = makeState();
    const next = gameReducer(s, { type: 'RESTART', removedPieces: ['A', 'B', 'C'] });
    expect(next.removedPieces).toEqual(['A', 'B', 'C']);
    expect(next.phase).toBe('playing');
  });

  it('phase is idle when restarted with empty removed pieces', () => {
    const s = makeState();
    const next = gameReducer(s, { type: 'RESTART', removedPieces: [] });
    expect(next.phase).toBe('idle');
  });
});

// ── Full game flow ────────────────────────────────────────────────

describe('full game flow', () => {
  it('select → rotate → place → victory for a 1-piece puzzle', () => {
    let s = initialState(['Z']);

    // Select piece
    s = gameReducer(s, { type: 'SELECT_PIECE', piece: 'Z' });
    expect(s.selectedPiece).toBe('Z');

    // Rotate a few times
    s = gameReducer(s, { type: 'ROTATE', axis: 'Y', dir: 1 });
    s = gameReducer(s, { type: 'ROTATE', axis: 'X', dir: -1 });

    // Wrong click adds mistake
    s = gameReducer(s, { type: 'WRONG_CLICK' });
    expect(s.mistakeCount).toBe(1);

    // Place the piece (victory)
    s = gameReducer(s, { type: 'PLACE_PIECE', piece: 'Z', coords: ['0,0,0'] });
    expect(s.phase).toBe('victory');
    expect(s.selectedPiece).toBeNull();
    expect(s.mistakeCount).toBe(1);

    // Restart clears placedCells too
    s = gameReducer(s, { type: 'RESTART' });
    expect(s.phase).toBe('playing');
    expect(s.mistakeCount).toBe(0);
    expect(s.placedPieces.size).toBe(0);
    expect(s.placedCells.size).toBe(0);
  });

  it('selecting already-selected piece deselects it', () => {
    let s = initialState(['F', 'I']);
    s = gameReducer(s, { type: 'SELECT_PIECE', piece: 'F' });
    s = gameReducer(s, { type: 'SELECT_PIECE', piece: 'F' }); // toggle off
    expect(s.selectedPiece).toBeNull();
  });

  it('switching pieces resets rotation', () => {
    let s = initialState(['F', 'I']);
    s = gameReducer(s, { type: 'SELECT_PIECE', piece: 'F' });
    s = gameReducer(s, { type: 'ROTATE', axis: 'Z', dir: 1 });
    const rotAfterF = s.rotationIndex;
    expect(rotAfterF).not.toBe(0);

    s = gameReducer(s, { type: 'SELECT_PIECE', piece: 'I' }); // switch
    expect(s.rotationIndex).toBe(0); // reset
    expect(s.selectedPiece).toBe('I');
  });

  it('full 2-piece puzzle: select, rotate, place both → victory, then restart', () => {
    let s = initialState(['F', 'I']);

    // Place piece F
    s = gameReducer(s, { type: 'SELECT_PIECE', piece: 'F' });
    s = gameReducer(s, { type: 'ROTATE', axis: 'X', dir: 1 });
    s = gameReducer(s, { type: 'RESET_ROTATION' });
    expect(s.rotationIndex).toBe(0);
    s = gameReducer(s, { type: 'WRONG_CLICK' });
    s = gameReducer(s, { type: 'PLACE_PIECE', piece: 'F', coords: ['1,0,0', '2,0,0', '3,0,0'] });
    expect(s.phase).toBe('playing');
    expect(s.placedPieces.has('F')).toBe(true);
    expect(s.selectedPiece).toBeNull();
    expect(s.mistakeCount).toBe(1);

    // Place piece I → victory
    s = gameReducer(s, { type: 'SELECT_PIECE', piece: 'I' });
    s = gameReducer(s, { type: 'PLACE_PIECE', piece: 'I', coords: ['0,0,0'] });
    expect(s.phase).toBe('victory');
    expect(s.placedPieces.has('I')).toBe(true);

    // Restart → clean slate
    s = gameReducer(s, { type: 'RESTART' });
    expect(s.phase).toBe('playing');
    expect(s.mistakeCount).toBe(0);
    expect(s.placedPieces.size).toBe(0);
    expect(s.selectedPiece).toBeNull();
    expect(s.removedPieces).toEqual(['F', 'I']);
  });
});

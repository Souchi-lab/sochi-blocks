import { useReducer, useRef, useEffect } from 'react';
import { rotateIndex } from '../utils/rotations';

export type GamePhase = 'idle' | 'playing' | 'victory';

export interface GameState {
  phase: GamePhase;
  removedPieces: string[];
  placedPieces: Set<string>;
  /** coordKey ("x,y,z") → pieceId: tracks which cells have been filled and by which piece */
  placedCells: Map<string, string>;
  selectedPiece: string | null;
  rotationIndex: number;
  /** Index into sortedAnchors — which valid placement position is currently targeted */
  cursorIndex: number;
  mistakeCount: number;
}

export type GameAction =
  | { type: 'SELECT_PIECE'; piece: string }
  | { type: 'PLACE_PIECE'; piece: string; coords: string[] }
  | { type: 'UNPLACE_PIECE'; piece: string }
  | { type: 'WRONG_CLICK' }
  | { type: 'ROTATE'; axis: 'X' | 'Y' | 'Z'; dir: 1 | -1 }
  | { type: 'RESET_ROTATION' }
  | { type: 'SET_ROTATION'; index: number }
  | { type: 'SET_CURSOR_INDEX'; index: number }
  | { type: 'RESTART'; removedPieces?: string[] };

export function initialState(removedPieces: string[]): GameState {
  return {
    phase: removedPieces.length > 0 ? 'playing' : 'idle',
    removedPieces,
    placedPieces: new Set(),
    placedCells: new Map(),
    selectedPiece: null,
    rotationIndex: 0,
    cursorIndex: 0,
    mistakeCount: 0,
  };
}

export function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'SELECT_PIECE':
      return {
        ...state,
        selectedPiece: state.selectedPiece === action.piece ? null : action.piece,
        rotationIndex: 0,
        cursorIndex: 0,
      };

    case 'PLACE_PIECE': {
      const nextPlaced = new Set(state.placedPieces);
      nextPlaced.add(action.piece);

      const nextCells = new Map(state.placedCells);
      for (const coord of action.coords) nextCells.set(coord, action.piece);

      const allPlaced = state.removedPieces.every(p => nextPlaced.has(p));
      return {
        ...state,
        placedPieces: nextPlaced,
        placedCells: nextCells,
        selectedPiece: null,
        rotationIndex: 0,
        cursorIndex: 0,
        phase: allPlaced ? 'victory' : 'playing',
      };
    }

    case 'UNPLACE_PIECE': {
      const nextPlaced = new Set(state.placedPieces);
      nextPlaced.delete(action.piece);

      const nextCells = new Map(state.placedCells);
      for (const [key, pid] of nextCells) {
        if (pid === action.piece) nextCells.delete(key);
      }

      return {
        ...state,
        placedPieces: nextPlaced,
        placedCells: nextCells,
        selectedPiece: action.piece,
        rotationIndex: 0,
        cursorIndex: 0,
        phase: 'playing',
        mistakeCount: state.mistakeCount + 1,
      };
    }

    case 'WRONG_CLICK':
      return state;

    case 'ROTATE':
      return {
        ...state,
        rotationIndex: rotateIndex(state.rotationIndex, action.axis, action.dir),
        cursorIndex: 0,
      };

    case 'RESET_ROTATION':
      return { ...state, rotationIndex: 0, cursorIndex: 0 };

    case 'SET_ROTATION':
      return { ...state, rotationIndex: action.index, cursorIndex: 0 };

    case 'SET_CURSOR_INDEX':
      return { ...state, cursorIndex: action.index };

    case 'RESTART':
      return initialState(action.removedPieces ?? state.removedPieces);

    default:
      return state;
  }
}

export function useGameState(removedPieces: string[]) {
  const [state, dispatch] = useReducer(gameReducer, removedPieces, initialState);

  const prevRemoved = useRef(removedPieces);
  useEffect(() => {
    if (prevRemoved.current !== removedPieces) {
      dispatch({ type: 'RESTART', removedPieces });
      prevRemoved.current = removedPieces;
    }
  }, [removedPieces]);

  const selectPiece = (piece: string) => dispatch({ type: 'SELECT_PIECE', piece });
  const placePiece = (piece: string, coords: string[]) => dispatch({ type: 'PLACE_PIECE', piece, coords });
  const unplacePiece = (piece: string) => dispatch({ type: 'UNPLACE_PIECE', piece });
  const wrongClick = () => dispatch({ type: 'WRONG_CLICK' });
  const rotate = (axis: 'X' | 'Y' | 'Z', dir: 1 | -1) => dispatch({ type: 'ROTATE', axis, dir });
  const resetRotation = () => dispatch({ type: 'RESET_ROTATION' });
  const setRotation = (index: number) => dispatch({ type: 'SET_ROTATION', index });
  const setCursorIndex = (index: number) => dispatch({ type: 'SET_CURSOR_INDEX', index });
  const restart = () => dispatch({ type: 'RESTART' });

  return { state, selectPiece, placePiece, unplacePiece, wrongClick, rotate, resetRotation, setRotation, setCursorIndex, restart };
}

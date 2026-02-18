export type PuzzleCell = {
  x: number;
  y: number;
  z: number;
  piece: string;
};

export type PuzzleGrid = {
  x: number;
  y: number;
  z: number;
};

export type PuzzleData = {
  puzzle_id: string;
  grid: PuzzleGrid;
  cells: PuzzleCell[];
  removed_pieces?: string[];
};

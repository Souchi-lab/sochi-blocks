export const DEFAULT_COLOR = "#cccccc";

let _colors: Record<string, string> | null = null;

export async function loadPieceColors(): Promise<Record<string, string>> {
  if (_colors) return _colors;
  const res = await fetch("colors/piece_colors.json");
  _colors = await res.json();
  return _colors!;
}

// Synchronous fallback – populated after loadPieceColors() resolves
export function getPieceColor(piece: string): string {
  return _colors?.[piece] ?? DEFAULT_COLOR;
}

// ── Master piece shapes ──────────────────────────────────────────
// shape_json: [[x, y, z], ...]  (z ignored for 2D preview)
let _pieces: Record<string, number[][]> | null = null;

export async function loadMasterPieces(): Promise<Record<string, number[][]>> {
  if (_pieces) return _pieces;
  const res = await fetch("colors/master_pieces.json");
  const data: Array<{ id: string; shape_json: number[][] }> = await res.json();
  _pieces = Object.fromEntries(data.map((p) => [p.id, p.shape_json]));
  return _pieces!;
}

export function getPieceShape(piece: string): number[][] {
  return _pieces?.[piece] ?? [];
}

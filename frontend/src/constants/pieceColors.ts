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

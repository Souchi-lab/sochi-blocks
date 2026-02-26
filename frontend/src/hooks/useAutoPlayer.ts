import { useEffect, useRef } from 'react';
import type { PuzzleData } from '../types/puzzle';
import type { GameState } from './useGameState';
import { getPieceShape } from '../constants/pieceColors';
import { validAnchors, placementCells } from '../utils/placement';
import { rotateIndex } from '../utils/rotations';
import type { Vec3 } from '../utils/rotations';

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
const axes: ('X' | 'Y' | 'Z')[] = ['X', 'Y', 'Z'];

export function useAutoPlayer({
    autoplay,
    data,
    gameState,
    selectPiece,
    placePiece,
    rotate,
}: {
    autoplay: boolean;
    data: PuzzleData | null;
    gameState: GameState;
    selectPiece: (p: string) => void;
    placePiece: (p: string, coords: string[]) => void;
    rotate: (axis: 'X' | 'Y' | 'Z', dir: 1 | -1) => void;
}) {
    const isPlaying = useRef(false);

    // Live ref to placed cells so async loop can get current state of board
    const placedCellsRef = useRef(gameState.placedCells);
    useEffect(() => {
        placedCellsRef.current = gameState.placedCells;
    }, [gameState.placedCells]);

    useEffect(() => {
        console.log(`[AutoPlayer] Checking startup conditions: autoplay=${autoplay}, data=${!!data}, phase=${gameState.phase}, removedPieces=${gameState.removedPieces.length}`);
        if (!autoplay || !data || gameState.phase === 'victory' || gameState.removedPieces.length === 0) return;
        if (isPlaying.current) return;
        isPlaying.current = true;

        const playScenario = async () => {
            const removedSet = new Set(gameState.removedPieces);
            const remaining = [...gameState.removedPieces];

            // Target ~30 seconds total duration. 
            // Calculate base multiplier to scale all delays.
            // If 2 pieces take ~30s, that's 1.0 multiplier.
            // If 6 pieces, we need to move 3x faster (0.33 multiplier).
            const targetTotalMs = 30000;
            const estimatedMsPerPieceWithFullDelay = 15000; // rough average from previous fixed delays
            const pacingMultiplier = Math.max(0.2, Math.min(1.5, targetTotalMs / (remaining.length * estimatedMsPerPieceWithFullDelay)));

            console.log(`[AutoPlayer] Starting scenario with ${remaining.length} pieces. Pacing Multiplier: ${pacingMultiplier.toFixed(2)}`);

            for (const pieceToPlay of remaining) {
                // ------- Step 1: Select the piece -------
                selectPiece(pieceToPlay);
                await sleep(1500 * pacingMultiplier);

                // Get the piece's canonical shape
                const pieceShape = getPieceShape(pieceToPlay) as Vec3[];
                if (!pieceShape || pieceShape.length === 0) {
                    console.warn(`[AutoPlayer] No shape for piece: ${pieceToPlay}`);
                    continue;
                }

                const targetCoords = new Set(
                    data.cells.filter(c => c.piece === pieceToPlay).map(c => `${c.x},${c.y},${c.z}`)
                );

                // ------- Step 2: Simulate thinking (random rotations) -------
                const thinkCount = Math.floor(Math.random() * 3) + 5; // 5 to 7 rotations

                // We track rotation locally — do NOT rely on gameState.rotationIndex
                let localRotIndex = 0;

                for (let i = 0; i < thinkCount; i++) {
                    const axis = axes[Math.floor(Math.random() * axes.length)];
                    const dir = Math.random() > 0.5 ? 1 : -1;
                    rotate(axis, dir); // purely for the visual
                    localRotIndex = rotateIndex(localRotIndex, axis, dir); // track locally
                    await sleep((1000 + Math.random() * 1000) * pacingMultiplier);
                }

                await sleep(1000 * pacingMultiplier);

                // ------- Step 3: Find a valid rotation & place -------
                // Current empty cells (re-computed freshly using the live ref)
                const allEmptyCells = data.cells
                    .filter(c => removedSet.has(c.piece) && !placedCellsRef.current.has(`${c.x},${c.y},${c.z}`))
                    .map(c => [c.x, c.y, c.z] as Vec3);

                console.log(`[AutoPlayer] Placing: ${pieceToPlay}, empty cells: ${allEmptyCells.length}`);

                // Try strictly all 24 rotations to find the one matching data.cells
                let targetRotIndex = -1;
                let targetCoordsToPlace: string[] | null = null;

                for (let rot = 0; rot < 24; rot++) {
                    const anchors = validAnchors(pieceShape, rot, allEmptyCells);
                    for (const anc of anchors) {
                        const cells = placementCells(pieceShape, rot, anc);
                        const coords = cells.map(([x, y, z]) => `${x},${y},${z}`);
                        const isPerfectFit = coords.every(coordStr => targetCoords.has(coordStr));

                        if (isPerfectFit) {
                            targetRotIndex = rot;
                            targetCoordsToPlace = coords;
                            break;
                        }
                    }
                    if (targetCoordsToPlace) break;
                }

                if (targetCoordsToPlace !== null) {
                    // Find shortest path to target rotation for visual effect
                    const path = getRotationPath(localRotIndex, targetRotIndex);
                    for (const step of path) {
                        rotate(step.axis, step.dir);
                        await sleep(300 * pacingMultiplier);
                    }
                    console.log(`[AutoPlayer] Found exact solution anchor at rotation ${targetRotIndex}`);
                    await sleep(800 * pacingMultiplier);
                    placePiece(pieceToPlay, targetCoordsToPlace);
                } else {
                    console.error(`[AutoPlayer] Could not find valid placement for: ${pieceToPlay}`);
                }

                // Wait before moving to the next piece
                await sleep(2000 * pacingMultiplier);
            }
        };

        playScenario().catch(console.error);

        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [autoplay, data, gameState.removedPieces, gameState.phase]);
}

// Helper to find shortest rotation sequence between two states
function getRotationPath(start: number, end: number): { axis: 'X' | 'Y' | 'Z', dir: 1 | -1 }[] {
    if (start === end) return [];

    // BFS queue: [current_rot, sequence_of_moves]
    const q: { curr: number, path: { axis: 'X' | 'Y' | 'Z', dir: 1 | -1 }[] }[] = [{ curr: start, path: [] }];
    const seen = new Set([start]);

    const axes: ('X' | 'Y' | 'Z')[] = ['X', 'Y', 'Z'];
    const dirs: (1 | -1)[] = [1, -1];

    while (q.length > 0) {
        const { curr, path } = q.shift()!;
        for (const axis of axes) {
            for (const dir of dirs) {
                const next = rotateIndex(curr, axis, dir);
                if (next === end) {
                    return [...path, { axis, dir }];
                }
                if (!seen.has(next)) {
                    seen.add(next);
                    q.push({ curr: next, path: [...path, { axis, dir }] });
                }
            }
        }
    }
    return [];
}

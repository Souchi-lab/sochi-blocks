import { useEffect, useRef } from 'react';
import type { PuzzleData } from '../types/puzzle';
import type { GameState } from './useGameState';
import { getPieceShape } from '../constants/pieceColors';
import { validAnchors, placementCells, uniqueRotationIndices } from '../utils/placement';
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
    setRotation,
    setCursorIndex,
    initialDelayMs = 0,
}: {
    autoplay: boolean;
    data: PuzzleData | null;
    gameState: GameState;
    selectPiece: (p: string) => void;
    placePiece: (p: string, coords: string[]) => void;
    rotate: (axis: 'X' | 'Y' | 'Z', dir: 1 | -1) => void;
    setRotation?: (index: number) => void;
    setCursorIndex?: (index: number) => void;
    /** Optional pause (ms) before gameplay starts — allows external camera orbit demos */
    initialDelayMs?: number;
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
            // Allow external camera orbit demo before gameplay starts
            if (initialDelayMs > 0) await sleep(initialDelayMs);

            const removedSet = new Set(gameState.removedPieces);
            const remaining = [...gameState.removedPieces];

            // Target ~30 seconds total duration.
            // Calculate base multiplier to scale all delays.
            const targetTotalMs = 30000;
            const estimatedMsPerPieceWithFullDelay = 15000;
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

                // ------- Step 2: Simulate thinking (cycle rotation cards) -------
                const thinkCount = Math.floor(Math.random() * 3) + 5; // 5 to 7 rotations

                // We track rotation locally — do NOT rely on gameState.rotationIndex
                let localRotIndex = 0;

                if (setRotation) {
                    // New UI: simulate clicking rotation cards
                    const uniqueRots = uniqueRotationIndices(pieceShape);
                    for (let i = 0; i < thinkCount; i++) {
                        const idx = uniqueRots[Math.floor(Math.random() * uniqueRots.length)];
                        setRotation(idx);
                        localRotIndex = idx;
                        await sleep((800 + Math.random() * 700) * pacingMultiplier);
                    }
                } else {
                    // Fallback: old rotate() method
                    for (let i = 0; i < thinkCount; i++) {
                        const axis = axes[Math.floor(Math.random() * axes.length)];
                        const dir = Math.random() > 0.5 ? 1 : -1;
                        rotate(axis, dir);
                        localRotIndex = rotateIndex(localRotIndex, axis, dir);
                        await sleep((1000 + Math.random() * 1000) * pacingMultiplier);
                    }
                }

                await sleep(1000 * pacingMultiplier);

                // ------- Step 3: Find a valid rotation & place -------
                const allEmptyCells = data.cells
                    .filter(c => removedSet.has(c.piece) && !placedCellsRef.current.has(`${c.x},${c.y},${c.z}`))
                    .map(c => [c.x, c.y, c.z] as Vec3);

                console.log(`[AutoPlayer] Placing: ${pieceToPlay}, empty cells: ${allEmptyCells.length}`);

                let targetRotIndex = -1;
                let targetCoordsToPlace: string[] | null = null;
                let targetAnchor: Vec3 | null = null;

                for (let rot = 0; rot < 24; rot++) {
                    const anchors = validAnchors(pieceShape, rot, allEmptyCells);
                    for (const anc of anchors) {
                        const cells = placementCells(pieceShape, rot, anc);
                        const coords = cells.map(([x, y, z]) => `${x},${y},${z}`);
                        const isPerfectFit = coords.every(coordStr => targetCoords.has(coordStr));

                        if (isPerfectFit) {
                            targetRotIndex = rot;
                            targetAnchor = anc;
                            targetCoordsToPlace = coords;
                            break;
                        }
                    }
                    if (targetCoordsToPlace) break;
                }

                if (targetCoordsToPlace !== null && targetAnchor !== null) {
                    // Apply final rotation
                    if (setRotation) {
                        // New UI: directly select the correct rotation card
                        setRotation(targetRotIndex);
                    } else {
                        // Fallback: animate path to target rotation
                        const path = getRotationPath(localRotIndex, targetRotIndex);
                        for (const step of path) {
                            rotate(step.axis, step.dir);
                            await sleep(300 * pacingMultiplier);
                        }
                    }
                    console.log(`[AutoPlayer] Found exact solution anchor at rotation ${targetRotIndex}`);
                    await sleep(800 * pacingMultiplier);

                    // Demonstrate cursor cycling through placement positions
                    if (setCursorIndex) {
                        // Compute sorted anchors for this rotation (mirrors App.tsx logic)
                        const allAnchorsForRot = validAnchors(pieceShape, targetRotIndex, allEmptyCells);
                        const anchorKeys = [...new Set(allAnchorsForRot.map(([x, y, z]) => `${x},${y},${z}`))];
                        const sortedKeys = anchorKeys.sort((a, b) => {
                            const [ax, ay, az] = a.split(',').map(Number);
                            const [bx, by, bz] = b.split(',').map(Number);
                            return az !== bz ? az - bz : ay !== by ? ay - by : ax - bx;
                        });
                        const targetAnchorKey = `${targetAnchor[0]},${targetAnchor[1]},${targetAnchor[2]}`;
                        const targetIdx = sortedKeys.indexOf(targetAnchorKey);

                        // Cycle through up to 2 other positions before landing on target
                        if (sortedKeys.length > 1) {
                            const cyclesToShow = Math.min(2, sortedKeys.length - 1);
                            for (let i = 0; i < cyclesToShow; i++) {
                                setCursorIndex((i + 1) % sortedKeys.length);
                                await sleep(400 * pacingMultiplier);
                            }
                        }
                        if (targetIdx >= 0) setCursorIndex(targetIdx);
                        await sleep(500 * pacingMultiplier);
                    }

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

import { useEffect, useRef } from 'react';
import type { PuzzleData } from '../types/puzzle';
import type { GameState } from './useGameState';
import { getPieceShape } from '../constants/pieceColors';
import { validAnchors, placementCells, uniqueRotationIndices } from '../utils/placement';
import { rotateIndex } from '../utils/rotations';
import type { Vec3 } from '../utils/rotations';

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
const axes: ('X' | 'Y' | 'Z')[] = ['X', 'Y', 'Z'];

// ── SNS モード設定 ────────────────────────────────────────────────

interface DiffConfig {
    label: 'EASY' | 'MEDIUM' | 'HARD' | 'EXTREME';
    hook: string;
    thinkCount: number;      // 思案ローテーション数 (多いほど迷いが増す)
    misplaceAt: Set<number>; // ミスプレイスするピースインデックス (0始まり)
}

function getSNSDiff(n: number, hookOverride?: string): DiffConfig {
    const hook = hookOverride ?? '';
    if (n <= 2) return {
        label: 'EASY',
        hook: hook || 'Can you solve this?',
        thinkCount: 3,
        misplaceAt: new Set(),
    };
    if (n <= 4) return {
        label: 'MEDIUM',
        hook: hook || 'Think you can solve this?',
        thinkCount: 8,
        misplaceAt: new Set([1]),
    };
    // 6 pieces: HARD
    if (n <= 6) return {
        label: 'HARD',
        hook: hook || 'Only the sharpest can solve this.',
        thinkCount: 10,
        misplaceAt: new Set([1, 3]),
    };
    // 7-8 pieces: EXTREME
    return {
        label: 'EXTREME',
        hook: hook || "This one's nearly impossible...",
        thinkCount: 10,
        misplaceAt: new Set([1, 3, 5]),
    };
}

// SNS モード固定タイミング (ms)
// ★ ステップ316時点の「早送り」設定 (EXTREME ではない)
const SNS = {
    select: 300,        // ピース選択後の間
    thinkPerRot: 160,   // ローテーション1回あたり
    thinkFinal: 250,    // 正解ローテーション後の間
    wrongCursor: 220,   // 間違いカーソル位置を見せる時間
    misplacePause: 1000, // ★大げさ: 誤配置を見せる時間 (1秒!)
    retractPause: 700,   // ★大げさ: 引き剥がし後の間
    snapPause: 100,      // 正解 snap 後の間
    settle: 400,        // 配置後の静止時間
    victoryHold: 2500,  // VICTORY 表示後の待機
};

function snsDispatch(phase: string, detail: Record<string, unknown> = {}) {
    window.dispatchEvent(
        new CustomEvent('autoplay-phase', { detail: { phase, ...detail } })
    );
}

// ── メインフック ──────────────────────────────────────────────────

export function useAutoPlayer({
    autoplay,
    snsMode = false,
    data,
    gameState,
    selectPiece,
    placePiece,
    rotate,
    setRotation,
    setCursorIndex,
    wrongClick,
    unplacePiece,
    initialDelayMs = 0,
}: {
    autoplay: boolean;
    snsMode?: boolean;
    data: PuzzleData | null;
    gameState: GameState;
    selectPiece: (p: string) => void;
    placePiece: (p: string, coords: string[]) => void;
    rotate: (axis: 'X' | 'Y' | 'Z', dir: 1 | -1) => void;
    setRotation?: (index: number) => void;
    setCursorIndex?: (index: number) => void;
    wrongClick?: (p: string) => void;
    unplacePiece?: (p: string) => void;
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
        if (!autoplay || !data || gameState.phase === 'victory' || gameState.removedPieces.length === 0) return;
        if (isPlaying.current) return;
        isPlaying.current = true;

        const playScenario = async () => {
            // Allow external camera orbit demo before gameplay starts
            if (initialDelayMs > 0) await sleep(initialDelayMs);

            const removedList = [...gameState.removedPieces];
            const totalPieces = removedList.length;

            // --- SNS モード特有の設定 ---
            const params = new URLSearchParams(window.location.search);
            const hookOverride = params.get('hook') || undefined;
            const diff = getSNSDiff(totalPieces, hookOverride);

            if (snsMode) {
                console.log(`[AutoPlayer][SNS] ${diff.label} / ${totalPieces} pieces / Misplace: ${[...diff.misplaceAt].join(',')}`);
                snsDispatch('intro', { label: diff.label, total: totalPieces, hook: diff.hook });
                await sleep(snsMode ? 1000 : 0); // Intro pause
            }

            // Normal mode duration targets
            const targetTotalMs = 30000;
            const estimatedMsPerPieceWithFullDelay = 15000;
            const pacingMultiplier = Math.max(0.2, Math.min(1.5, targetTotalMs / (totalPieces * estimatedMsPerPieceWithFullDelay)));

            for (let i = 0; i < totalPieces; i++) {
                const pieceToPlay = removedList[i];

                if (snsMode) {
                    console.log(`[AutoPlayer][SNS] Piece ${pieceToPlay} (${i + 1}/${totalPieces})`);
                    snsDispatch('float', { pieceIdx: i, total: totalPieces, label: diff.label, hook: diff.hook });
                }

                // ------- Step 1: Select the piece -------
                selectPiece(pieceToPlay);
                await sleep(snsMode ? SNS.select : 1500 * pacingMultiplier);

                const pieceShape = getPieceShape(pieceToPlay) as Vec3[];
                if (!pieceShape || pieceShape.length === 0) continue;

                const targetCoords = new Set(
                    data.cells.filter(c => c.piece === pieceToPlay).map(c => `${c.x},${c.y},${c.z}`)
                );

                // ------- Step 2: Thinking (Rotations) -------
                const uniqueRots = uniqueRotationIndices(pieceShape);
                const thinkCount = snsMode ? diff.thinkCount : (Math.floor(Math.random() * 3) + 5);
                let currentRot = 0;

                for (let r = 0; r < thinkCount; r++) {
                    const idx = uniqueRots[Math.floor(Math.random() * uniqueRots.length)];
                    if (setRotation) setRotation(idx);
                    currentRot = idx;
                    await sleep(snsMode ? SNS.thinkPerRot : (800 + Math.random() * 700) * pacingMultiplier);
                }

                // ------- Step 3: Find Solution -------
                const allEmptyCells = data.cells
                    .filter(c => !placedCellsRef.current.has(`${c.x},${c.y},${c.z}`))
                    .map(c => [c.x, c.y, c.z] as Vec3);

                let solutionRot = 0;
                let solutionCoords: string[] | null = null;
                let solutionAnchor: Vec3 | null = null;

                for (let rot = 0; rot < 24; rot++) {
                    const anchors = validAnchors(pieceShape, rot, allEmptyCells);
                    for (const anc of anchors) {
                        const cells = placementCells(pieceShape, rot, anc);
                        const coords = cells.map(([x, y, z]) => `${x},${y},${z}`);
                        if (coords.every(coordStr => targetCoords.has(coordStr))) {
                            solutionRot = rot;
                            solutionAnchor = anc;
                            solutionCoords = coords;
                            break;
                        }
                    }
                    if (solutionCoords) break;
                }

                if (!solutionCoords || !solutionAnchor) continue;

                // Sync to solution rotation
                if (setRotation) setRotation(solutionRot);
                await sleep(snsMode ? SNS.thinkFinal : 1000 * pacingMultiplier);

                // ------- Step 4: MISPLACE Logic (SNS Mode Only) -------
                const isMisplace = snsMode && diff.misplaceAt.has(i);
                if (isMisplace) {
                    const solutionKeys = new Set(solutionCoords);
                    const mistakenEmptyCells = allEmptyCells.filter(c => !solutionKeys.has(`${c[0]},${c[1]},${c[2]}`));

                    if (mistakenEmptyCells.length > 0) {
                        const badAnchor = mistakenEmptyCells[Math.floor(Math.random() * mistakenEmptyCells.length)];
                        const badAnchors = validAnchors(pieceShape, solutionRot, allEmptyCells);
                        const badKeys = badAnchors.map(a => `${a[0]},${a[1]},${a[2]}`).sort();
                        const targetBadIdx = badKeys.indexOf(`${badAnchor[0]},${badAnchor[1]},${badAnchor[2]}`);

                        if (setCursorIndex && targetBadIdx >= 0) {
                            setCursorIndex(targetBadIdx);
                            await sleep(SNS.wrongCursor);
                        }

                        // WRONG PLACE
                        if (wrongClick) wrongClick(pieceToPlay);
                        snsDispatch('misplace');
                        await sleep(SNS.misplacePause);

                        // RETRACT
                        if (unplacePiece) unplacePiece(pieceToPlay);
                        snsDispatch('misplace_retract');
                        await sleep(SNS.retractPause);

                        // Recovery delay
                        await sleep(300);
                    }
                }

                // ------- Step 5: FINAL PLACEMENT -------
                const finalAnchors = validAnchors(pieceShape, solutionRot, allEmptyCells);
                const finalKeys = finalAnchors.map(a => `${a[0]},${a[1]},${a[2]}`).sort();
                const targetIdx = finalKeys.indexOf(`${solutionAnchor[0]},${solutionAnchor[1]},${solutionAnchor[2]}`);

                if (setCursorIndex && targetIdx >= 0) {
                    setCursorIndex(targetIdx);
                    await sleep(snsMode ? 150 : 500 * pacingMultiplier);
                }

                if (snsMode) snsDispatch('snap');
                placePiece(pieceToPlay, solutionCoords);

                await sleep(snsMode ? SNS.settle : 2000 * pacingMultiplier);
            }

            if (snsMode) {
                console.log(`[AutoPlayer][SNS] Done!`);
                snsDispatch('victory', { total: totalPieces, label: diff.label, hook: diff.hook });
                await sleep(SNS.victoryHold);
            }
        };

        playScenario().catch(console.error);
    }, [autoplay, data, gameState.removedPieces, gameState.phase, snsMode]);
}

// Shortest path helper kept for fallback but SNS uses setRotation directly
function getRotationPath(start: number, end: number): { axis: 'X' | 'Y' | 'Z', dir: 1 | -1 }[] {
    if (start === end) return [];
    const q: { curr: number, path: { axis: 'X' | 'Y' | 'Z', dir: 1 | -1 }[] }[] = [{ curr: start, path: [] }];
    const seen = new Set([start]);
    const dirs: (1 | -1)[] = [1, -1];
    while (q.length > 0) {
        const { curr, path } = q.shift()!;
        for (const axis of axes) {
            for (const dir of dirs) {
                const next = rotateIndex(curr, axis, dir);
                if (next === end) return [...path, { axis, dir }];
                if (!seen.has(next)) {
                    seen.add(next);
                    q.push({ curr: next, path: [...path, { axis, dir }] });
                }
            }
        }
    }
    return [];
}

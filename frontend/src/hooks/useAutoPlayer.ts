import { useEffect, useRef } from 'react';
import type { PuzzleData } from '../types/puzzle';
import type { GameState } from './useGameState';
import { getPieceShape } from '../constants/pieceColors';
import { validAnchors, placementCells, uniqueRotationIndices } from '../utils/placement';
import type { Vec3 } from '../utils/rotations';

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

// ── SNS モード設定 ────────────────────────────────────────────────

interface DiffConfig {
    label: 'EASY' | 'MEDIUM' | 'HARD' | 'EXTREME';
    hook: string;
    thinkCount: number;
    misplaceAt: Set<number>;
}

function getSNSDiff(n: number, hookOverride?: string): DiffConfig {
    const hook = hookOverride ?? '';
    if (n <= 2) return { label: 'EASY',    hook: hook || 'Can you solve this?',             thinkCount: 3,  misplaceAt: new Set() };
    if (n <= 4) return { label: 'MEDIUM',  hook: hook || 'Think you can solve this?',        thinkCount: 8,  misplaceAt: new Set([1]) };
    if (n <= 6) return { label: 'HARD',    hook: hook || 'Only the sharpest can solve this.', thinkCount: 10, misplaceAt: new Set([1, 3]) };
    return              { label: 'EXTREME', hook: hook || "This one's nearly impossible...",  thinkCount: 10, misplaceAt: new Set([1, 3, 5]) };
}

// SNS モード固定タイミング (ms)
const SNS = {
    select: 300,
    thinkPerRot: 160,
    thinkFinal: 250,
    wrongCursor: 220,
    misplacePause: 1000,
    retractPause: 700,
    snapPause: 100,
    settle: 400,
    victoryHold: 2500,
};

// Teaser モード設定 (目標: 6〜8秒)
const TEASER = {
    drama:  { select: 150, thinkCount: 3,  thinkPerRot: 60,  thinkFinal: 100, cursorFinal: 60,  settle: 150 },
    fast:   { select: 20,  thinkCount: 2,  thinkPerRot: 10,  thinkFinal: 15,  cursorFinal: 20,  settle: 25  },
    last:   { select: 180, thinkCount: 4,  thinkPerRot: 80,  thinkFinal: 130, cursorFinal: 80,  settle: 220 },
    wrongCursor:   80,
    misplacePause: 500,
    retractPause:  320,
    recovery:      100,
    victoryHold:  1200,
};

// Tutorial モード設定 (目標: 約30秒・分かりやすさ優先)
const TUTORIAL = {
    introHold:    2200,  // タイトル表示時間
    problemHold:  1400,  // 問題提示表示時間
    select:        900,  // ピース選択後の間
    thinkCount:      7,  // 回転数 (向きの多様性を見せる)
    thinkPerRot:   370,  // 各回転の表示時間
    thinkFinal:    750,  // 正解回転後の間
    cursorFinal:   550,  // カーソル確定後の間
    fitHold:       800,  // Fit! フラッシュの表示時間
    victoryHold:  3500,  // Victory CTA 表示時間
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
    snsVideoMode = 'full_play',
    data,
    gameState,
    selectPiece,
    placePiece,
    setRotation,
    setCursorIndex,
    wrongClick,
    unplacePiece,
    initialDelayMs = 0,
}: {
    autoplay: boolean;
    snsMode?: boolean;
    snsVideoMode?: 'full_play' | 'teaser' | 'tutorial' | 'assembly';
    data: PuzzleData | null;
    gameState: GameState;
    selectPiece: (p: string) => void;
    placePiece: (p: string, coords: string[]) => void;
    setRotation?: (index: number) => void;
    setCursorIndex?: (index: number) => void;
    wrongClick?: (p: string) => void;
    unplacePiece?: (p: string) => void;
    initialDelayMs?: number;
}) {
    const isPlaying = useRef(false);

    const placedCellsRef = useRef(gameState.placedCells);
    useEffect(() => {
        placedCellsRef.current = gameState.placedCells;
    }, [gameState.placedCells]);

    useEffect(() => {
        if (!autoplay || !data || gameState.phase === 'victory' || gameState.removedPieces.length === 0) return;
        if (isPlaying.current) return;
        isPlaying.current = true;

        const playScenario = async () => {
            if (initialDelayMs > 0) await sleep(initialDelayMs);

            const removedList = [...gameState.removedPieces];
            // 'F' is gray — always play it last so the video opens with a colorful piece
            const fIdx = removedList.indexOf('F');
            if (fIdx !== -1 && fIdx !== removedList.length - 1) {
                removedList.splice(fIdx, 1);
                removedList.push('F');
            }
            const totalPieces = removedList.length;

            const params = new URLSearchParams(window.location.search);
            const hookOverride = params.get('hook') || undefined;
            const diff = getSNSDiff(totalPieces, hookOverride);
            const lang = (params.get('lang') as 'ja' | 'en') ?? 'ja';

            const isTeaser   = snsMode && snsVideoMode === 'teaser';
            const isTutorial = snsVideoMode === 'tutorial';

            // ── Intro ──────────────────────────────────────────────
            if (snsMode) {
                if (isTutorial) {
                    snsDispatch('tutorial_intro', { lang });
                    await sleep(TUTORIAL.introHold);
                    snsDispatch('tutorial_problem', { total: totalPieces, lang });
                    await sleep(TUTORIAL.problemHold);
                } else {
                    console.log(`[AutoPlayer][SNS] ${diff.label} / ${totalPieces} pieces / mode: ${snsVideoMode}`);
                    snsDispatch('assembly_intro', { total: totalPieces, hook: diff.hook });
                    await sleep(isTeaser ? 1200 : 1800);
                    snsDispatch('intro', { label: diff.label, total: totalPieces, hook: diff.hook });
                    await sleep(isTeaser ? 700 : 1000);
                }
            }

            // Normal mode pacing
            const targetTotalMs = 30000;
            const estimatedMsPerPieceWithFullDelay = 15000;
            const pacingMultiplier = Math.max(0.2, Math.min(1.5, targetTotalMs / (totalPieces * estimatedMsPerPieceWithFullDelay)));

            // ── Piece loop ─────────────────────────────────────────
            for (let i = 0; i < totalPieces; i++) {
                const pieceToPlay = removedList[i];

                const isTeaserDrama = isTeaser && i === 0;
                const isTeaserLast  = isTeaser && i === totalPieces - 1 && totalPieces > 1;
                const isTeaserFast  = isTeaser && !isTeaserDrama && !isTeaserLast;
                const tRole = isTeaserDrama ? TEASER.drama : isTeaserFast ? TEASER.fast : isTeaserLast ? TEASER.last : null;

                if (snsMode) {
                    if (isTutorial) {
                        // step labels (select/rotate/place) intentionally omitted
                    } else {
                        const roleTag = isTeaserDrama ? ' [DRAMA]' : isTeaserFast ? ' [FAST]' : isTeaserLast ? ' [LAST]' : '';
                        console.log(`[AutoPlayer][SNS] Piece ${pieceToPlay} (${i + 1}/${totalPieces})${roleTag}`);
                        snsDispatch('float', { pieceIdx: i, total: totalPieces, label: diff.label, hook: diff.hook });
                        if (isTeaserFast && i === 1) snsDispatch('speed_flash');
                    }
                }

                // ── Select ────────────────────────────────────────
                selectPiece(pieceToPlay);
                await sleep(
                    isTutorial ? TUTORIAL.select :
                    snsMode    ? (tRole?.select ?? SNS.select) :
                    1500 * pacingMultiplier
                );

                const pieceShape = getPieceShape(pieceToPlay) as Vec3[];
                if (!pieceShape || pieceShape.length === 0) continue;

                const targetCoords = new Set(
                    data.cells.filter(c => c.piece === pieceToPlay).map(c => `${c.x},${c.y},${c.z}`)
                );

                // ── Rotate ────────────────────────────────────────

                const uniqueRots = uniqueRotationIndices(pieceShape);
                const thinkCount =
                    isTutorial ? TUTORIAL.thinkCount :
                    snsMode    ? (tRole?.thinkCount ?? diff.thinkCount) :
                    (Math.floor(Math.random() * 3) + 5);

                for (let r = 0; r < thinkCount; r++) {
                    const idx = uniqueRots[Math.floor(Math.random() * uniqueRots.length)];
                    if (setRotation) setRotation(idx);
                    await sleep(
                        isTutorial ? TUTORIAL.thinkPerRot :
                        snsMode    ? (tRole?.thinkPerRot ?? SNS.thinkPerRot) :
                        (800 + Math.random() * 700) * pacingMultiplier
                    );
                }

                // ── Find solution ─────────────────────────────────
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

                if (setRotation) setRotation(solutionRot);
                await sleep(
                    isTutorial ? TUTORIAL.thinkFinal :
                    snsMode    ? (tRole?.thinkFinal ?? SNS.thinkFinal) :
                    1000 * pacingMultiplier
                );

                // ── Misplace (SNS only, not tutorial) ────────────
                const isMisplace = snsMode && !isTutorial && (isTeaser ? isTeaserDrama : diff.misplaceAt.has(i));
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
                            await sleep(isTeaser ? TEASER.wrongCursor : SNS.wrongCursor);
                        }

                        if (wrongClick) wrongClick(pieceToPlay);
                        snsDispatch('misplace');
                        await sleep(isTeaser ? TEASER.misplacePause : SNS.misplacePause);

                        if (unplacePiece) unplacePiece(pieceToPlay);
                        snsDispatch('misplace_retract');
                        await sleep(isTeaser ? TEASER.retractPause : SNS.retractPause);

                        await sleep(isTeaser ? TEASER.recovery : 300);
                    }
                }

                // ── Place ─────────────────────────────────────────

                const finalAnchors = validAnchors(pieceShape, solutionRot, allEmptyCells);
                const finalKeys = finalAnchors.map(a => `${a[0]},${a[1]},${a[2]}`).sort();
                const targetIdx = finalKeys.indexOf(`${solutionAnchor[0]},${solutionAnchor[1]},${solutionAnchor[2]}`);

                if (setCursorIndex && targetIdx >= 0) {
                    setCursorIndex(targetIdx);
                    await sleep(
                        isTutorial ? TUTORIAL.cursorFinal :
                        snsMode    ? (tRole?.cursorFinal ?? 150) :
                        500 * pacingMultiplier
                    );
                }

                if (!isTutorial && snsMode) snsDispatch('snap');
                placePiece(pieceToPlay, solutionCoords);

                if (isTutorial) {
                    snsDispatch('tutorial_fit', { pieceIdx: i + 1, total: totalPieces, lang });
                    await sleep(TUTORIAL.fitHold);
                } else {
                    await sleep(snsMode ? (tRole?.settle ?? SNS.settle) : 2000 * pacingMultiplier);
                    if (isTeaserDrama) {
                        snsDispatch('tap_hint');
                        await sleep(700);
                    }
                }
            }

            // ── Victory ──────────────────────────────────────────
            if (snsMode) {
                if (isTutorial) {
                    snsDispatch('tutorial_victory', { total: totalPieces, lang });
                    await sleep(TUTORIAL.victoryHold);
                } else {
                    console.log(`[AutoPlayer][SNS] Done!`);
                    snsDispatch('victory', { total: totalPieces, label: diff.label, hook: diff.hook });
                    await sleep(isTeaser ? TEASER.victoryHold : SNS.victoryHold);
                }
            }
        };

        playScenario().catch(console.error);
    }, [autoplay, data, gameState.removedPieces, gameState.phase, snsMode]);
}

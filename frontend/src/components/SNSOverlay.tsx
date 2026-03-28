import { useEffect, useState, useRef } from 'react';
import { SITE_URL, SITE_NAME } from '../constants/siteConfig';
import { getPieceColor } from '../constants/pieceColors';
import { PieceShapeMini } from './PieceShapeMini';

// ── 型定義 ────────────────────────────────────────────────────────

type Phase =
    | 'idle'
    | 'assembly_intro'
    | 'intro'
    | 'float'
    | 'misplace'
    | 'misplace_retract'
    | 'snap'
    | 'settle'
    | 'tap_hint'
    | 'victory'
    | 'tutorial_intro'
    | 'tutorial_problem'
    | 'tutorial_select'
    | 'tutorial_rotate'
    | 'tutorial_place'
    | 'tutorial_fit'
    | 'tutorial_victory';

interface OverlayState {
    phase: Phase;
    pieceIdx: number;
    total: number;
    label: string;
    hook: string;
    flashKey: number;        // アニメーションリスタート用
    starsShown: number;      // ★ カウントアップ用
    victoryReady: boolean;   // Playwright 用 selector
    tapHintShown: boolean;   // TAP TO PLAY 常時表示フラグ
    speedFlashKey: number;   // SPEED RUN フラッシュトリガー
    tutorialLang: string;    // tutorial 言語 ('ja' | 'en')
    tutorialFitKey: number;  // Fit! フラッシュリスタート用
}

const INITIAL: OverlayState = {
    phase: 'idle',
    pieceIdx: 0,
    total: 0,
    label: '',
    hook: '',
    flashKey: 0,
    starsShown: 0,
    victoryReady: false,
    tapHintShown: false,
    speedFlashKey: 0,
    tutorialLang: 'ja',
    tutorialFitKey: 0,
};

// ── メインコンポーネント ──────────────────────────────────────────

const SCATTER_POSITIONS = [
    { x: -500, y: -900 },
    { x:  -80, y: -940 },
    { x:   80, y: -940 },
    { x:  500, y: -900 },
    { x: -640, y:    0 },
    { x:  640, y:    0 },
    { x: -420, y:  900 },
    { x:  420, y:  900 },
];

// ピース数に応じたレイアウト設定
function getAssemblyLayout(n: number): { cellSize: number; lands: { x: number; y: number }[] } {
    if (n <= 2) return {
        cellSize: 130,
        lands: [{ x: -260, y: 0 }, { x: 260, y: 0 }],
    };
    if (n <= 4) return {
        cellSize: 110,
        lands: [
            { x: -260, y: -250 }, { x: 260, y: -250 },
            { x: -260, y:  250 }, { x: 260, y:  250 },
        ],
    };
    if (n <= 6) return {
        cellSize: 86,
        lands: [
            { x: -320, y: -220 }, { x: 0, y: -220 }, { x: 320, y: -220 },
            { x: -320, y:  220 }, { x: 0, y:  220 }, { x: 320, y:  220 },
        ],
    };
    // 7〜8ピース: 4×2グリッド (x間隔280px, cellSize60でmax4列=261px → ギリ収まる)
    return {
        cellSize: 60,
        lands: [
            { x: -420, y: -250 }, { x: -140, y: -250 }, { x: 140, y: -250 }, { x: 420, y: -250 },
            { x: -420, y:  250 }, { x: -140, y:  250 }, { x: 140, y:  250 }, { x: 420, y:  250 },
        ],
    };
}

export function SNSOverlay({
    videoMode = 'full_play',
    removedPieces = [],
}: {
    videoMode?: 'full_play' | 'teaser' | 'assembly' | 'tutorial';
    removedPieces?: string[];
}) {
    const [s, setS] = useState<OverlayState>(INITIAL);
    const starsTimerRef = useRef<ReturnType<typeof setTimeout>[]>([]);

    useEffect(() => {
        const handler = (e: Event) => {
            const d = (e as CustomEvent).detail as Record<string, unknown>;
            const phaseStr = d.phase as string;

            // phase を変えない独立イベントを先に処理
            if (phaseStr === 'speed_flash') {
                setS(prev => ({ ...prev, speedFlashKey: prev.speedFlashKey + 1 }));
                return;
            }

            const phase = phaseStr as Phase;

            setS(prev => {
                const next: OverlayState = { ...prev };

                switch (phase) {
                    case 'assembly_intro':
                        next.phase = 'assembly_intro';
                        next.hook = (d.hook as string) ?? '';
                        next.total = (d.total as number) ?? 0;
                        break;

                    case 'intro':
                        next.phase = 'intro';
                        next.label = (d.label as string) ?? '';
                        next.hook = (d.hook as string) ?? '';
                        next.total = (d.total as number) ?? 0;
                        next.pieceIdx = 0;
                        break;

                    case 'float':
                        next.phase = 'float';
                        next.pieceIdx = (d.pieceIdx as number) ?? 0;
                        next.total = (d.total as number) ?? prev.total;
                        next.label = (d.label as string) ?? prev.label;
                        next.hook = (d.hook as string) ?? prev.hook;
                        break;

                    case 'misplace':
                        next.phase = 'misplace';
                        next.flashKey = prev.flashKey + 1;
                        break;

                    case 'misplace_retract':
                        next.phase = 'misplace_retract';
                        next.flashKey = prev.flashKey + 1;
                        break;

                    case 'snap':
                        next.phase = 'snap';
                        next.flashKey = prev.flashKey + 1;
                        break;

                    case 'settle':
                        next.phase = 'settle';
                        next.pieceIdx = (d.pieceIdx as number) ?? prev.pieceIdx;
                        break;

                    case 'tap_hint':
                        next.phase = 'tap_hint';
                        next.tapHintShown = true;
                        break;

                    case 'tutorial_intro':
                        next.phase = 'tutorial_intro';
                        next.tutorialLang = (d.lang as string) ?? 'ja';
                        break;

                    case 'tutorial_problem':
                        next.phase = 'tutorial_problem';
                        next.total = (d.total as number) ?? prev.total;
                        next.tutorialLang = (d.lang as string) ?? prev.tutorialLang;
                        break;

                    case 'tutorial_select':
                        next.phase = 'tutorial_select';
                        next.pieceIdx = (d.pieceIdx as number) ?? prev.pieceIdx;
                        next.total = (d.total as number) ?? prev.total;
                        next.tutorialLang = (d.lang as string) ?? prev.tutorialLang;
                        break;

                    case 'tutorial_rotate':
                        next.phase = 'tutorial_rotate';
                        next.tutorialLang = (d.lang as string) ?? prev.tutorialLang;
                        break;

                    case 'tutorial_place':
                        next.phase = 'tutorial_place';
                        next.tutorialLang = (d.lang as string) ?? prev.tutorialLang;
                        break;

                    case 'tutorial_fit':
                        next.phase = 'tutorial_fit';
                        next.pieceIdx = (d.pieceIdx as number) ?? prev.pieceIdx;
                        next.total = (d.total as number) ?? prev.total;
                        next.tutorialFitKey = prev.tutorialFitKey + 1;
                        break;

                    case 'tutorial_victory': {
                        next.phase = 'tutorial_victory';
                        next.total = (d.total as number) ?? prev.total;
                        next.tutorialLang = (d.lang as string) ?? prev.tutorialLang;
                        next.victoryReady = false;
                        starsTimerRef.current.forEach(clearTimeout);
                        starsTimerRef.current = [];
                        const tvDone = setTimeout(() => {
                            setS(p => ({ ...p, victoryReady: true }));
                        }, 2800);
                        starsTimerRef.current.push(tvDone);
                        break;
                    }

                    case 'victory': {
                        next.phase = 'victory';
                        next.total = (d.total as number) ?? prev.total;
                        next.label = (d.label as string) ?? prev.label;
                        next.hook = (d.hook as string) ?? prev.hook;
                        next.starsShown = 0;
                        next.victoryReady = false;

                        // ★ カウントアップ: teaser は高速 (100ms/個), full_play は通常 (320ms/個)
                        const n = next.total;
                        const starDelay    = videoMode === 'teaser' ? 150 : 500;
                        const starInterval = videoMode === 'teaser' ? 100 : 320;
                        const donePad      = videoMode === 'teaser' ? 200 : 600;
                        starsTimerRef.current.forEach(clearTimeout);
                        starsTimerRef.current = [];
                        for (let i = 1; i <= n; i++) {
                            const t = setTimeout(() => {
                                setS(p => ({ ...p, starsShown: i }));
                            }, starDelay + i * starInterval);
                            starsTimerRef.current.push(t);
                        }
                        // 全部点灯後 .victory-screen-done クラスを付与
                        const done = setTimeout(() => {
                            setS(p => ({ ...p, victoryReady: true }));
                        }, starDelay + n * starInterval + donePad);
                        starsTimerRef.current.push(done);
                        break;
                    }
                }
                return next;
            });
        };

        window.addEventListener('autoplay-phase', handler);
        return () => {
            window.removeEventListener('autoplay-phase', handler);
            starsTimerRef.current.forEach(clearTimeout);
        };
    }, []);

    const { phase, pieceIdx, total, label, hook, flashKey, starsShown, victoryReady, tapHintShown, speedFlashKey, tutorialLang, tutorialFitKey } = s;

    const isTutorialPhase = phase.startsWith('tutorial_');
    const showMain = phase !== 'idle' && phase !== 'assembly_intro' && phase !== 'victory' && !isTutorialPhase;
    const showVic = phase === 'victory';
    const pieceLabel = pieceIdx === 0 ? hook : `Piece ${pieceIdx + 1} of ${total}`;
    const showCta = victoryReady || (videoMode === 'teaser' && starsShown >= 1);

    // ③ 難易度別 Victory サブテキスト
    const victorySubText: Record<string, string> = {
        EASY:    'NICE! ✨',
        MEDIUM:  'GREAT! ⭐',
        HARD:    'IMPRESSIVE! 🔥',
        EXTREME: 'LEGENDARY! 👑',
    };
    const victorySub = victorySubText[label] ?? 'AMAZING! 🎊';

    return (
        <div className={`sns-overlay${victoryReady ? ' victory-screen-done' : ''}`}>

            {/* ── ASSEMBLY_INTRO: 散らばったピースが収束する冒頭演出 ── */}
            {phase === 'assembly_intro' && removedPieces.length > 0 && (
                <div className="sns-assembly-container">
                    {(() => {
                        const { cellSize, lands } = getAssemblyLayout(removedPieces.length);
                        return removedPieces.map((p, i) => {
                            const scatter = SCATTER_POSITIONS[i % SCATTER_POSITIONS.length];
                            const land    = lands[i % lands.length];
                            return (
                                <div
                                    key={p}
                                    className="sns-assembly-piece"
                                    style={{
                                        '--scatter-x': `${scatter.x}px`,
                                        '--scatter-y': `${scatter.y}px`,
                                        '--scatter-r': `${(i % 2 === 0 ? -1 : 1) * (15 + i * 8)}deg`,
                                        '--land-x': `${land.x}px`,
                                        '--land-y': `${land.y}px`,
                                        '--delay': `${i * 0.09}s`,
                                        '--piece-offset': `${Math.round(cellSize * 1.3)}px`,
                                    } as React.CSSProperties}
                                >
                                    <PieceShapeMini piece={p} cellSize={cellSize} />
                                </div>
                            );
                        });
                    })()}
                    <div className="sns-assembly-hook">{hook || 'Can you solve this?'}</div>
                </div>
            )}

            {/* ── ウォーターマーク (常時) ──────────────────────────── */}
            {showMain && (
                <div className="sns-watermark">{SITE_NAME}</div>
            )}

            {/* ── A: INTRO バッジ — 難易度をドラマチックに表示 ───── */}
            {phase === 'intro' && label && (
                <div className={`sns-intro-badge sns-intro-badge--${label.toLowerCase()}`}>
                    {label}
                </div>
            )}

            {/* ── フックテキスト ─────────────────────────────────── */}
            {showMain && (
                <div className={`sns-hook-text${phase === 'intro' ? ' sns-hook-text--intro' : ''}`}>
                    <span className="sns-hook-main">{pieceLabel}</span>
                    {pieceIdx === 0 && phase !== 'intro' && <span className="sns-hook-sub">{label}</span>}
                </div>
            )}

            {/* ── ミッションピース横並びバー (画面下部・常時表示) ────── */}
            {showMain && removedPieces.length > 0 && (
                <div className="sns-piece-bar">
                    {removedPieces.map(p => (
                        <div key={p} className="sns-piece-card">
                            <PieceShapeMini piece={p} cellSize={32} />
                            <span className="sns-piece-label" style={{ color: getPieceColor(p) }}>
                                {p}
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {/* ── ドットインジケーター ──────────────────────────────── */}
            {showMain && total > 0 && (
                <div className="sns-dots">
                    {Array.from({ length: total }).map((_, i) => (
                        <span
                            key={i}
                            className={`sns-dot${i < pieceIdx ? ' done' : i === pieceIdx ? ' current' : ''}`}
                        />
                    ))}
                </div>
            )}

            {/* ── MISPLACE: 大げさ赤フラッシュ + ✗ ───────────────── */}
            {phase === 'misplace' && (
                <div key={`mp-${flashKey}`} className="sns-misplace-layer">
                    <div className="sns-red-flash" />
                    <div className="sns-wrong-icon">✗</div>
                    <div className="sns-wrong-label">Wait... that's wrong!</div>
                </div>
            )}

            {/* ── MISPLACE_RETRACT: 画面シェイク ──────────────────── */}
            {phase === 'misplace_retract' && (
                <div key={`rt-${flashKey}`} className="sns-retract-shake" />
            )}

            {/* ── SNAP: 白フラッシュ ────────────────────────────────── */}
            {phase === 'snap' && (
                <div key={`sn-${flashKey}`} className="sns-snap-flash" />
            )}

            {/* ── ② SPEED RUN フラッシュ (fast フェーズ開始時) ────── */}
            {speedFlashKey > 0 && (
                <div key={`sf-${speedFlashKey}`} className="sns-speed-flash">
                    <span className="sns-speed-icon">⚡</span>
                    <span className="sns-speed-label">SPEED RUN</span>
                </div>
            )}

            {/* ── B-1: TAP HINT — 指タップアニメーション (一度だけ) ── */}
            {phase === 'tap_hint' && (
                <div className="sns-tap-hint">
                    <div className="sns-tap-ring" />
                    <div className="sns-tap-finger">👆</div>
                    <div className="sns-tap-label">TAP TO PLAY</div>
                </div>
            )}

            {/* ── B-1: TAP TO PLAY 常時バッジ (tap_hint 以降) ──────── */}
            {tapHintShown && phase !== 'tap_hint' && showMain && (
                <div className="sns-tap-persistent">TAP TO PLAY 🎮</div>
            )}

            {/* ── TUTORIAL フェーズ群 ───────────────────────────────── */}
            {phase === 'tutorial_intro' && (
                <div className="sns-tutorial-overlay">
                    <div className="sns-tutorial-title">
                        {tutorialLang === 'en' ? 'How to Play' : '遊び方'}
                    </div>
                    <div className="sns-tutorial-sub">
                        {tutorialLang === 'en' ? 'Learn in 30s!' : '30秒でわかる！'}
                    </div>
                </div>
            )}

            {phase === 'tutorial_problem' && (
                <div className="sns-tutorial-overlay">
                    <div className="sns-tutorial-title">
                        {tutorialLang === 'en' ? 'Solve this!' : 'このパズルを解こう'}
                    </div>
                    <div className="sns-tutorial-sub">
                        {tutorialLang === 'en' ? `${total} pieces` : `ピース × ${total}`}
                    </div>
                </div>
            )}

            {(phase === 'tutorial_select' || phase === 'tutorial_rotate' || phase === 'tutorial_place') && (
                <div className="sns-tutorial-step">
                    {phase === 'tutorial_select' && (tutorialLang === 'en' ? '① Select a piece 👇' : '① ピースを選ぶ 👇')}
                    {phase === 'tutorial_rotate' && (tutorialLang === 'en' ? '② Rotate it 🔄' : '② 向きを変える 🔄')}
                    {phase === 'tutorial_place'  && (tutorialLang === 'en' ? '③ Set the position ✅' : '③ 位置を決める ✅')}
                </div>
            )}

            {phase === 'tutorial_fit' && (
                <div key={`tf-${tutorialFitKey}`} className="sns-tutorial-fit">
                    Fit! ✓
                </div>
            )}

            {phase === 'tutorial_victory' && (
                <div className="sns-tutorial-overlay sns-tutorial-overlay--victory">
                    <div className="sns-tutorial-victory-text">Solved! 🎉</div>
                    <div className="sns-tutorial-victory-cta">
                        {tutorialLang === 'en' ? 'Give it a try!' : 'あなたも挑戦！'}
                    </div>
                </div>
            )}

            {/* ── VICTORY 画面 ──────────────────────────────────────── */}
            {showVic && (
                <div className="sns-victory">
                    {/* コンフェッティ絵文字バースト */}
                    <div className="sns-confetti">
                        {['🎉', '🎊', '✨', '🏆', '🎯', '💫', '⭐', '🌟'].map((e, i) => (
                            <span key={i} className={`sns-confetti-item c${i}`}>{e}</span>
                        ))}
                    </div>

                    <div className="sns-victory-solved">Solved!</div>
                    <div className="sns-victory-sub">{victorySub}</div>
                    <div className="sns-victory-label">{label}</div>
                    <div className="sns-victory-stars">
                        {Array.from({ length: total }).map((_, i) => (
                            <span key={i} className={`sns-star${i < starsShown ? ' lit' : ''}`}>★</span>
                        ))}
                    </div>

                    {showCta && (
                        <div className="sns-victory-cta">
                            Can YOU beat it? 🎮<br />
                            <span className="sns-victory-url">{SITE_URL}</span>
                        </div>
                    )}
                    <div className="sns-watermark">{SITE_NAME}</div>
                </div>
            )}
        </div>
    );
}

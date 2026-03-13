import { useEffect, useState, useRef, useMemo } from 'react';
import { SITE_URL, SITE_NAME } from '../constants/siteConfig';
import './TutorialVideoOverlay.css';

// ── フェーズ定義 ──────────────────────────────────────────────────

type TutPhase =
    | 'idle'
    | 'intro'
    | 'problem'
    | 'select'
    | 'rotate'
    | 'place'
    | 'fit'
    | 'victory';

interface TutState {
    phase: TutPhase;
    pieceIdx: number;   // 配置済みピース数 (0始まり: 現在のピース)
    total: number;
    fitKey: number;
    starsShown: number;
    victoryReady: boolean;
}

const INITIAL: TutState = {
    phase: 'idle',
    pieceIdx: 0,
    total: 0,
    fitKey: 0,
    starsShown: 0,
    victoryReady: false,
};

// ── バイリンガルテキスト ──────────────────────────────────────────

const T = {
    ja: {
        title:    'SoChi BLOCKS',
        tagline:  '3D で考えるパズル',
        problem:  'ぴったり入るピースを探そう',
        select:   'ピースを選ぶ',
        rotate:   '向きを変える',
        place:    '配置して確定',
        fit:      'Fit! ✨',
        solved:   'クリア！',
        cta:      'あなたも挑戦しよう！',
    },
    en: {
        title:    'SoChi BLOCKS',
        tagline:  'Think in 3D.',
        problem:  'Find the piece that fits',
        select:   'Select a piece',
        rotate:   'Rotate it',
        place:    'Place it',
        fit:      'Fit! ✨',
        solved:   'Solved!',
        cta:      'Try it yourself!',
    },
} as const;

const STEP_NUM: Partial<Record<TutPhase, string>> = {
    select: '①',
    rotate: '②',
    place:  '③',
};

// ── メインコンポーネント ──────────────────────────────────────────

export function TutorialVideoOverlay() {
    const [s, setS] = useState<TutState>(INITIAL);
    const starsTimerRef = useRef<ReturnType<typeof setTimeout>[]>([]);

    // lang は URL パラメータから読む (mount 時固定)
    const lang = useMemo<'ja' | 'en'>(() => {
        const p = new URLSearchParams(window.location.search).get('lang');
        return p === 'en' ? 'en' : 'ja';
    }, []);

    useEffect(() => {
        const handler = (e: Event) => {
            const d = (e as CustomEvent).detail as Record<string, unknown>;
            const phaseStr = d.phase as string;

            setS(prev => {
                const next = { ...prev };
                switch (phaseStr) {
                    case 'tutorial_intro':
                        next.phase = 'intro';
                        break;
                    case 'tutorial_problem':
                        next.phase = 'problem';
                        next.total = (d.total as number) ?? 0;
                        break;
                    case 'tutorial_select':
                        next.phase = 'select';
                        next.pieceIdx = (d.pieceIdx as number) ?? 0;
                        next.total    = (d.total as number) ?? prev.total;
                        break;
                    case 'tutorial_rotate':
                        next.phase = 'rotate';
                        break;
                    case 'tutorial_place':
                        next.phase = 'place';
                        break;
                    case 'tutorial_fit':
                        next.phase   = 'fit';
                        next.fitKey  = prev.fitKey + 1;
                        next.pieceIdx = (d.pieceIdx as number) ?? prev.pieceIdx;
                        break;
                    case 'tutorial_victory': {
                        next.phase        = 'victory';
                        next.total        = (d.total as number) ?? prev.total;
                        next.starsShown   = 0;
                        next.victoryReady = false;
                        // ★ カウントアップ
                        const n = next.total;
                        starsTimerRef.current.forEach(clearTimeout);
                        starsTimerRef.current = [];
                        for (let i = 1; i <= n; i++) {
                            const t = setTimeout(() => {
                                setS(p => ({ ...p, starsShown: i }));
                            }, 400 + i * 350);
                            starsTimerRef.current.push(t);
                        }
                        const done = setTimeout(() => {
                            setS(p => ({ ...p, victoryReady: true }));
                        }, 400 + n * 350 + 700);
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

    const { phase, pieceIdx, total, fitKey, starsShown, victoryReady } = s;
    const t = T[lang];
    const isStepPhase = phase === 'select' || phase === 'rotate' || phase === 'place';
    const isFit = phase === 'fit';

    if (phase === 'idle') return null;

    return (
        <div className={`tut-overlay${victoryReady ? ' victory-screen-done' : ''}`}>

            {/* ── ウォーターマーク ────────────────────────────────── */}
            {phase !== 'victory' && (
                <div className="tut-watermark">{SITE_NAME}</div>
            )}

            {/* ── Intro ────────────────────────────────────────────── */}
            {phase === 'intro' && (
                <div className="tut-intro">
                    <div className="tut-intro-title">{t.title}</div>
                    <div className="tut-intro-tagline">{t.tagline}</div>
                </div>
            )}

            {/* ── Problem ──────────────────────────────────────────── */}
            {phase === 'problem' && (
                <div className="tut-problem-banner">
                    <div className="tut-problem-text">{t.problem}</div>
                    <div className="tut-problem-dots">
                        {Array.from({ length: total }).map((_, i) => (
                            <span key={i} className="tut-dot" />
                        ))}
                    </div>
                </div>
            )}

            {/* ── Step card (select / rotate / place) ──────────────── */}
            {isStepPhase && (
                <>
                    <div className="tut-step-card">
                        <span className="tut-step-num">{STEP_NUM[phase]}</span>
                        <span className="tut-step-text">{t[phase as 'select' | 'rotate' | 'place']}</span>
                    </div>
                    {total > 0 && (
                        <div className="tut-progress">
                            {Array.from({ length: total }).map((_, i) => (
                                <span
                                    key={i}
                                    className={`tut-dot${i < pieceIdx ? ' done' : i === pieceIdx ? ' current' : ''}`}
                                />
                            ))}
                        </div>
                    )}
                </>
            )}

            {/* ── Fit flash ────────────────────────────────────────── */}
            {isFit && (
                <div key={`fit-${fitKey}`} className="tut-fit-layer">
                    <div className="tut-fit-flash" />
                    <div className="tut-fit-text">{t.fit}</div>
                    <div className="tut-progress">
                        {Array.from({ length: total }).map((_, i) => (
                            <span
                                key={i}
                                className={`tut-dot${i < pieceIdx ? ' done' : i === pieceIdx ? ' current' : ''}`}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* ── Victory ──────────────────────────────────────────── */}
            {phase === 'victory' && (
                <div className="tut-victory">
                    <div className="tut-confetti">
                        {['🎉', '🎊', '✨', '🏆', '🎯', '💫', '⭐', '🌟'].map((em, i) => (
                            <span key={i} className={`tut-confetti-item c${i}`}>{em}</span>
                        ))}
                    </div>
                    <div className="tut-victory-solved">{t.solved}</div>
                    <div className="tut-victory-stars">
                        {Array.from({ length: total }).map((_, i) => (
                            <span key={i} className={`tut-star${i < starsShown ? ' lit' : ''}`}>★</span>
                        ))}
                    </div>
                    {victoryReady && (
                        <div className="tut-victory-cta">
                            {t.cta}
                            <span className="tut-victory-url">{SITE_URL}</span>
                        </div>
                    )}
                    <div className="tut-watermark">{SITE_NAME}</div>
                </div>
            )}
        </div>
    );
}

import { useEffect, useState, useRef } from 'react';
import { SITE_URL, SITE_NAME } from '../constants/siteConfig';

// ── 型定義 ────────────────────────────────────────────────────────

type Phase =
    | 'idle'
    | 'intro'
    | 'float'
    | 'misplace'
    | 'misplace_retract'
    | 'snap'
    | 'settle'
    | 'tap_hint'
    | 'victory';

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
};

// ── メインコンポーネント ──────────────────────────────────────────

export function SNSOverlay({ videoMode = 'full_play' }: { videoMode?: 'full_play' | 'teaser' }) {
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

    const { phase, pieceIdx, total, label, hook, flashKey, starsShown, victoryReady, tapHintShown, speedFlashKey } = s;

    const showMain = phase !== 'idle' && phase !== 'victory';
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

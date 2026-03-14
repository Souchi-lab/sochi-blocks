import { useState, useEffect } from 'react';
import { trackTutorialStart } from '../utils/analytics';
import './TutorialOverlay.css';

interface TutorialOverlayProps {
    isVisible: boolean;
    onClose: () => void;
}

const LANG_KEY = 'sochi_lang';

function detectLang(): 'ja' | 'en' {
    const stored = localStorage.getItem(LANG_KEY);
    if (stored === 'en' || stored === 'ja') return stored;
    return navigator.language.startsWith('ja') ? 'ja' : 'en';
}

interface Step {
    icon: string;
    titleJa: string;
    titleEn: string;
    bodyJa: React.ReactNode;
    bodyEn: React.ReactNode;
    hintJa: string;
    hintEn: string;
}

const STEPS: Step[] = [
    {
        icon: '👆',
        titleJa: 'ピースを選ぶ',
        titleEn: 'Select a Piece',
        bodyJa: (
            <>
                画面下のトレイに、置くべきピースが並んでいます。<br />
                タップして選びましょう。
            </>
        ),
        bodyEn: (
            <>
                The tray below shows the pieces you need to place.<br />
                Tap one to select it.
            </>
        ),
        hintJa: '↓ 画面下のトレイを見てください',
        hintEn: '↓ Look at the piece tray below',
    },
    {
        icon: '🔄',
        titleJa: '向きを変える',
        titleEn: 'Rotate It',
        bodyJa: (
            <>
                右パネルのサムネイルをタップして向きを変えます。<br />
                空きスペースに合う向きを探しましょう。<br />
                <span className="hint-pc">PC: <kbd>WASD</kbd> / <kbd>Q</kbd><kbd>E</kbd> キーでも回転できます</span>
            </>
        ),
        bodyEn: (
            <>
                Tap a thumbnail in the right panel to rotate.<br />
                Find the orientation that fits the empty space.<br />
                <span className="hint-pc">PC: Use <kbd>WASD</kbd> / <kbd>Q</kbd><kbd>E</kbd> keys to rotate</span>
            </>
        ),
        hintJa: '→ 右のサムネイルで向きを選んでください',
        hintEn: '→ Tap a thumbnail on the right to rotate',
    },
    {
        icon: '✅',
        titleJa: '配置して確定',
        titleEn: 'Place It',
        bodyJa: (
            <>
                3D 画面の下に「← Prev / Next →」ボタンが出ます。<br />
                位置を選んで <kbd>✓ Place</kbd> をタップすれば確定。<br />
                全ピースを埋めたらクリアです！<br />
                <span className="hint-pc">PC: 3D 上をクリックしても配置できます</span>
            </>
        ),
        bodyEn: (
            <>
                「← Prev / Next →」buttons appear below the 3D view.<br />
                Pick a position, then tap <kbd>✓ Place</kbd> to confirm.<br />
                Fill all pieces to win!<br />
                <span className="hint-pc">PC: You can also click directly on the 3D grid</span>
            </>
        ),
        hintJa: '↑ 3D 画面下のボタンで配置します',
        hintEn: '↑ Use the buttons below the 3D view to place',
    },
];

export function TutorialOverlay({ isVisible, onClose }: TutorialOverlayProps) {
    const [lang, setLang] = useState<'ja' | 'en'>(detectLang);
    const [step, setStep] = useState(0);

    // Analytics: チュートリアルが表示された時に送信
    useEffect(() => {
        if (isVisible) {
            trackTutorialStart();
        }
    }, [isVisible]);

    if (!isVisible) return null;

    const current = STEPS[step];
    const isFirst = step === 0;
    const isLast = step === STEPS.length - 1;

    const toggleLang = () => {
        const next = lang === 'ja' ? 'en' : 'ja';
        setLang(next);
        localStorage.setItem(LANG_KEY, next);
    };

    const handleClose = () => {
        setStep(0);
        onClose();
    };

    return (
        <div className="tutorial-overlay" onClick={handleClose}>
            <div className="tutorial-card" onClick={e => e.stopPropagation()}>
                <button className="tutorial-close-btn" onClick={handleClose} aria-label="Close">×</button>

                {/* Header */}
                <div className="tutorial-header">
                    <h2 className="tutorial-title">
                        {lang === 'ja' ? '遊び方' : 'How to Play'}
                    </h2>
                    <button className="tutorial-lang-btn" onClick={toggleLang}>
                        {lang === 'ja' ? 'EN' : 'JP'}
                    </button>
                </div>

                {/* Step indicator */}
                <div className="tutorial-step-indicator">
                    {STEPS.map((_, i) => (
                        <div
                            key={i}
                            className={`tutorial-step-dot ${i === step ? 'active' : i < step ? 'done' : ''}`}
                        />
                    ))}
                </div>

                {/* Step content */}
                <div className="tutorial-step-card">
                    <div className="tutorial-step-icon">{current.icon}</div>
                    <div className="tutorial-step-num">
                        {lang === 'ja' ? `ステップ ${step + 1} / ${STEPS.length}` : `Step ${step + 1} of ${STEPS.length}`}
                    </div>
                    <div className="tutorial-step-title">
                        {lang === 'ja' ? current.titleJa : current.titleEn}
                    </div>
                    <div className="tutorial-step-body">
                        {lang === 'ja' ? current.bodyJa : current.bodyEn}
                    </div>
                    <div className="tutorial-step-hint">
                        {lang === 'ja' ? current.hintJa : current.hintEn}
                    </div>
                </div>

                {/* Navigation */}
                <div className="tutorial-nav">
                    <button
                        className="tutorial-skip-btn"
                        onClick={handleClose}
                    >
                        {lang === 'ja' ? 'スキップ' : 'Skip'}
                    </button>
                    <div className="tutorial-nav-right">
                        {!isFirst && (
                            <button
                                className="tutorial-nav-btn tutorial-prev-btn"
                                onClick={() => setStep(s => s - 1)}
                            >
                                ← {lang === 'ja' ? '前へ' : 'Prev'}
                            </button>
                        )}
                        {!isLast ? (
                            <button
                                className="tutorial-nav-btn tutorial-next-btn"
                                onClick={() => setStep(s => s + 1)}
                            >
                                {lang === 'ja' ? '次へ' : 'Next'} →
                            </button>
                        ) : (
                            <button
                                className="tutorial-nav-btn tutorial-done-btn"
                                onClick={handleClose}
                            >
                                {lang === 'ja' ? 'はじめる！' : "Let's Play!"}
                            </button>
                        )}
                    </div>
                </div>

                {/* Video link */}
                <a className="tutorial-video-link" href="./how-to-play.html" target="_blank" rel="noopener">
                    {lang === 'ja' ? '▶ 動画で確認する' : '▶ Watch video tutorial'}
                </a>
            </div>
        </div>
    );
}

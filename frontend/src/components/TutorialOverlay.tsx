import { useState } from 'react';
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

export function TutorialOverlay({ isVisible, onClose }: TutorialOverlayProps) {
    const [lang, setLang] = useState<'ja' | 'en'>(detectLang);

    if (!isVisible) return null;

    const toggleLang = () => {
        const next = lang === 'ja' ? 'en' : 'ja';
        setLang(next);
        localStorage.setItem(LANG_KEY, next);
    };

    return (
        <div className="tutorial-overlay">
            <div className="tutorial-card">
                <button className="tutorial-close-btn" onClick={onClose} aria-label="Close">×</button>

                <div className="tutorial-header">
                    <h2 className="tutorial-title">
                        {lang === 'ja' ? '遊び方' : 'How to Play'}
                    </h2>
                    <button className="tutorial-lang-btn" onClick={toggleLang}>
                        {lang === 'ja' ? 'EN' : 'JP'}
                    </button>
                </div>

                {lang === 'ja' ? (
                    <div className="tutorial-content">
                        <ul className="tutorial-list">
                            <li>
                                <strong>① ピースを選ぶ</strong>
                                <br />
                                トレイからピースをタップして選びます。
                            </li>
                            <li>
                                <strong>② 向きを変える</strong>
                                <br />
                                <kbd>←</kbd> <kbd>→</kbd> で回転させて、空きスペースに合う向きを探します。
                                <span className="hint-pc">（PC: <kbd>WASD</kbd> / <kbd>Q</kbd><kbd>E</kbd> キーも使えます）</span>
                            </li>
                            <li>
                                <strong>③ 配置して確定</strong>
                                <br />
                                <kbd>←</kbd> <kbd>→</kbd> で位置を選び、<kbd>Set</kbd> をタップして確定します。
                                <span className="hint-pc">（PC: 3D 上をクリックしても配置できます）</span>
                            </li>
                        </ul>
                        <p className="tutorial-hint">3D はドラッグで自由に回転できます</p>
                        <a className="tutorial-video-link" href="./how-to-play.html" target="_blank" rel="noopener">
                            ▶ 動画で確認する
                        </a>
                    </div>
                ) : (
                    <div className="tutorial-content">
                        <ul className="tutorial-list">
                            <li>
                                <strong>① Select a piece</strong>
                                <br />
                                Tap any piece from the tray to select it.
                            </li>
                            <li>
                                <strong>② Rotate it</strong>
                                <br />
                                Use <kbd>←</kbd> <kbd>→</kbd> to rotate and find the right orientation.
                                <span className="hint-pc"> (PC: <kbd>WASD</kbd> / <kbd>Q</kbd><kbd>E</kbd> keys)</span>
                            </li>
                            <li>
                                <strong>③ Place it</strong>
                                <br />
                                Use <kbd>←</kbd> <kbd>→</kbd> to choose a position, then tap <kbd>Set</kbd>.
                                <span className="hint-pc"> (PC: Click directly on the 3D grid)</span>
                            </li>
                        </ul>
                        <p className="tutorial-hint">Drag the 3D model to view from any angle</p>
                        <a className="tutorial-video-link" href="./how-to-play.html" target="_blank" rel="noopener">
                            ▶ Watch video tutorial
                        </a>
                    </div>
                )}
            </div>
        </div>
    );
}

import './TutorialOverlay.css';

interface TutorialOverlayProps {
    isVisible: boolean;
    onClose: () => void;
}

export function TutorialOverlay({ isVisible, onClose }: TutorialOverlayProps) {
    if (!isVisible) return null;

    return (
        <div className="tutorial-overlay">
            <div className="tutorial-card">
                <button className="tutorial-close-btn" onClick={onClose} aria-label="閉じる">×</button>
                <h2 className="tutorial-title">Help</h2>
                <div className="tutorial-content">
                    <ul className="tutorial-list">
                        <li><strong>1. Select:</strong> トレイからピースをタップして選びます。</li>
                        <li><strong>2. Rotate:</strong> サイドバーの <kbd>←</kbd> <kbd>→</kbd> で向きを切り替えます。<span className="hint-pc">（PC: <kbd>WASD</kbd> / <kbd>Q</kbd><kbd>E</kbd> キーも使えます）</span></li>
                        <li><strong>3. Place:</strong> 画面下の <kbd>←</kbd> <kbd>→</kbd> で配置位置を選び、<kbd>Set</kbd> をタップして確定します。<span className="hint-pc">（PC: 3D上をクリックしても配置できます）</span></li>
                    </ul>
                </div>
            </div>
        </div>
    );
}

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
                <div className="tutorial-video-container">
                    <video
                        src="/how_to_play.mp4"
                        muted
                        playsInline
                        autoPlay
                        loop
                        className="tutorial-video"
                    />
                </div>
                <div className="tutorial-content">
                    <ul className="tutorial-list">
                        <li><strong>1. 選択:</strong> 下のトレイからピースをクリックします。</li>
                        <li><strong>2. 回転:</strong> <kbd>WASD</kbd> / <kbd>矢印キー</kbd> (XY軸)、<kbd>Q</kbd> / <kbd>E</kbd> (Z軸) で回転させます。</li>
                        <li><strong>3. 配置:</strong> 3D空間上で半透明の形（ゴースト）が緑色に光る場所をクリックすると配置できます。</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}

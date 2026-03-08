import { useState } from 'react';

type Props = {
  puzzleId: string;
  removedPieces: string[];
  mistakeCount: number;
  clearTimeMs: number;
};

// ピースID → 絵文字 (カラースクエア近似)
const PIECE_EMOJI: Record<string, string> = {
  F: '⬜', I: '🟦', L: '🟧', P: '🟥',
  N: '🟪', T: '🟩', U: '🟨', V: '🩵',
  W: '💚', X: '🔴', Y: '🟫', Z: '🔵',
};

function getDifficulty(n: number): string {
  const stars = Math.max(1, Math.min(5, n));
  return '★'.repeat(stars) + '☆'.repeat(5 - stars);
}

function formatTime(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return m > 0 ? `${m}:${s.toString().padStart(2, '0')}` : `${totalSec}秒`;
}

function buildShareText(
  puzzleId: string,
  removedPieces: string[],
  mistakeCount: number,
  clearTimeMs: number,
): string {
  const difficulty = getDifficulty(removedPieces.length);
  const emojis = removedPieces.map((p) => PIECE_EMOJI[p] ?? '🧩').join('');
  const mistakeLine = mistakeCount === 0 ? 'ノーミス！' : `ミス ${mistakeCount}回`;
  const timeLine = clearTimeMs > 0
    ? `⏱ ${formatTime(clearTimeMs)}  ${mistakeLine}`
    : mistakeLine;
  const url = `https://souchi-lab.github.io/sochi-blocks/viewer.html?puzzle_id=${puzzleId}`;

  return [
    `🧩 SoChi BLOCKS #${puzzleId}`,
    `難易度 ${difficulty}`,
    emojis,
    timeLine,
    '',
    `今日のパズルに挑戦→ ${url}`,
  ].join('\n');
}

export function ShareResult({ puzzleId, removedPieces, mistakeCount, clearTimeMs }: Props) {
  const [copied, setCopied] = useState(false);
  const [shareStatus, setShareStatus] = useState<'none' | 'shared' | 'copied'>('none');

  const shareText = buildShareText(puzzleId, removedPieces, mistakeCount, clearTimeMs);
  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`;
  const viewerUrl = `https://souchi-lab.github.io/sochi-blocks/viewer.html?puzzle_id=${puzzleId}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      setShareStatus('copied');
      setTimeout(() => {
        setCopied(false);
        setShareStatus('none');
      }, 2000);
    } catch {
      // clipboard API が使えない場合
    }
  };

  const handleX = () => {
    window.open(twitterUrl, '_blank', 'noopener,noreferrer');
  };

  const handleInstagram = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `SoChi BLOCKS #${puzzleId}`,
          text: shareText,
          url: viewerUrl,
        });
        setShareStatus('shared');
        setTimeout(() => setShareStatus('none'), 2000);
      } catch (err) {
        // ユーザーキャンセル以外の場合にコピーへフォールバック
        if ((err as Error).name !== 'AbortError') {
          await handleCopy();
        }
      }
    } else {
      // Web Share API 非対応環境ではコピー
      await handleCopy();
    }
  };

  return (
    <div className="share-result">
      <div className="share-text-preview">{shareText}</div>
      <div className="share-buttons">
        <button className="share-btn share-btn--x" onClick={handleX}>
          𝕏 でシェア
        </button>
        <button className="share-btn share-btn--instagram" onClick={handleInstagram}>
          {shareStatus === 'copied' ? '📋 コピーしました' : '📸 シェア'}
        </button>
        <button
          className={`share-btn share-btn--copy${copied ? ' share-btn--copied' : ''}`}
          onClick={handleCopy}
        >
          {copied ? '✓ コピー済み' : '📋 コピー'}
        </button>
      </div>
      {shareStatus === 'copied' && (
        <div className="share-hint">※お使いの環境ではクリップボードにコピーされました</div>
      )}
    </div>
  );
}

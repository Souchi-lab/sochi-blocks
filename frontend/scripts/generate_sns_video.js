import { chromium } from 'playwright';
import ffmpeg from 'fluent-ffmpeg';
import ffmpegStatic from 'ffmpeg-static';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

ffmpeg.setFfmpegPath(ffmpegStatic);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function generateVideo() {
    const rawArgs = process.argv.slice(2);
    const positional = rawArgs.filter(a => !a.startsWith('--'));
    const puzzleId = positional[0] || '20260224_001';
    // --mode teaser / --mode full_play の他、npm が --mode を消費した場合に
    // positional[1] に 'teaser' や 'full_play' が直接来るケースにも対応
    const modeIdx = rawArgs.indexOf('--mode');
    const videoMode = (modeIdx >= 0 ? rawArgs[modeIdx + 1] : '')
        || positional.find(a => a === 'teaser' || a === 'full_play')
        || 'full_play';
    if (videoMode !== 'full_play' && videoMode !== 'teaser') {
        console.error(`❌ Unknown --mode: "${videoMode}". Use "full_play" or "teaser".`);
        process.exit(1);
    }

    // sns=1 を付与して SNS 用のオーバーレイとカメラリグを有効化
    // teaser モード時は video_mode=teaser を追加
    const url = `http://localhost:5173/viewer.html?puzzle_id=${puzzleId}&autoplay=1&sns=1${videoMode === 'teaser' ? '&video_mode=teaser' : ''}`;
    const outputDir = path.join(__dirname, '..', 'public', 'sns_videos');

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    const suffix = videoMode === 'teaser' ? '_teaser' : '_full';
    const webmPath = path.join(outputDir, `${puzzleId}${suffix}.webm`);
    const mp4Path = path.join(outputDir, `${puzzleId}${suffix}.mp4`);

    console.log(`🎬 Launching browser for puzzle: ${puzzleId} [mode: ${videoMode}]`);
    console.log(`🌐 URL: ${url}`);

    const browser = await chromium.launch({ headless: true });
    const contextCreateTime = Date.now();
    // SNS 用に 9:16 (1080x1920) の縦長動画として記録
    const context = await browser.newContext({
        viewport: { width: 1080, height: 1920 },
        recordVideo: {
            dir: outputDir,
            size: { width: 1080, height: 1920 }
        }
    });

    const page = await context.newPage();

    const t0 = Date.now();
    const ts = () => `+${((Date.now() - t0) / 1000).toFixed(2)}s`;

    // ブラウザ側の [AutoPlayer] ログを表示
    page.on('console', msg => {
        if (msg.text().includes('[AutoPlayer]')) {
            console.log(`${ts()} ${msg.text()}`);
        }
    });

    await page.goto(url);

    // teaser: ロード画面をトリムするためコンテンツ開始時刻を計測
    let trimStartSeconds = 0;
    if (videoMode === 'teaser') {
        try {
            await page.waitForSelector('.sns-watermark', { timeout: 30000 });
            const elapsedMs = Date.now() - contextCreateTime;
            // コンテンツ開始 300ms 前からを残す（カラフルなパズルをチラ見せ）
            trimStartSeconds = Math.max(0, (elapsedMs - 300) / 1000);
            console.log(`✂️  Trim start: ${trimStartSeconds.toFixed(2)}s (page load: ${(elapsedMs / 1000).toFixed(2)}s)`);
        } catch {
            console.warn('⚠️  .sns-watermark not found, skipping trim.');
        }
    }

    console.log(`${ts()} ⏳ Waiting for victory screen (.victory-screen-done)...`);

    // SNSOverlay が勝演を終えて victoryReady になるとこのクラスが付与される
    try {
        await page.waitForSelector('.victory-screen-done', { timeout: 300000 });
    } catch (err) {
        console.error('❌ Puzzle not solved or victory screen not shown within 300s.');
        await context.close();
        await browser.close();
        process.exit(1);
    }

    console.log(`${ts()} ✅ victory-screen-done detected`);
    // 最後のアニメーションが落ち着くまで待つ (teaser は短め)
    await page.waitForTimeout(videoMode === 'teaser' ? 800 : 2000);

    console.log('✅ Puzzle solved! Capturing video...');
    const videoPath = await page.video()?.path();
    await context.close();
    await browser.close();

    if (!videoPath) {
        console.error('❌ Failed to get video path from Playwright.');
        process.exit(1);
    }

    if (fs.existsSync(webmPath)) fs.unlinkSync(webmPath);
    fs.renameSync(videoPath, webmPath);
    console.log(`🎥 WebM saved: ${webmPath}`);

    // Conversion to MP4 (SNS 共有用)
    console.log('🔄 Converting to MP4...');

    const ffmpegCmd = ffmpeg(webmPath);
    if (trimStartSeconds > 0) {
        ffmpegCmd.seekInput(trimStartSeconds);
    }
    ffmpegCmd
        .outputOptions([
            '-pix_fmt yuv420p',
            '-c:v libx264',
            '-crf 23',
            '-preset superfast'
        ])
        .save(mp4Path)
        .on('end', async () => {
            console.log(`✅ MP4 saved: ${mp4Path}`);
            // Clean up temporary WebM
            if (fs.existsSync(webmPath)) {
                fs.unlinkSync(webmPath);
                console.log('Sweep: Cleaned up temporary WebM.');
            }
            // docs/sns_videos/ にも同期コピー (GitHub Pages 用)
            const docsDir = path.join(__dirname, '..', '..', 'docs', 'sns_videos');
            if (fs.existsSync(docsDir)) {
                const docsMp4 = path.join(docsDir, `${puzzleId}${suffix}.mp4`);
                fs.copyFileSync(mp4Path, docsMp4);
                console.log(`📂 Synced to docs: ${docsMp4}`);
            }
            console.log(`\n🎉 Done! → ${mp4Path}`);
            process.exit(0);
        })
        .on('error', (err) => {
            console.error('❌ Conversion error:', err);
            process.exit(1);
        });
}

generateVideo().catch(console.error);

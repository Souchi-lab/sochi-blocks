import { chromium } from 'playwright';
import ffmpeg from 'fluent-ffmpeg';
import ffmpegStatic from 'ffmpeg-static';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

ffmpeg.setFfmpegPath(ffmpegStatic);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function generateTutorialVideo() {
    const puzzleId = process.argv[2] || '20260226_001';
    const url = `http://localhost:5173/viewer.html?puzzle_id=${puzzleId}&autoplay=1`;

    // Output goes to docs/how_to_play.mp4 (project root docs folder)
    const docsDir = path.join(__dirname, '..', '..', 'docs');
    const tmpDir = path.join(__dirname, '..', 'public', 'sns_videos');

    if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });
    if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

    const webmPath = path.join(tmpDir, `tutorial_${puzzleId}.webm`);
    const mp4Path  = path.join(docsDir, 'how_to_play.mp4');

    console.log(`🎬 Generating tutorial video for puzzle: ${puzzleId}`);

    // Wide viewport so sidebar (rotation cards, cursor nav) is fully visible
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 900, height: 650 },
        recordVideo: {
            dir: tmpDir,
            size: { width: 900, height: 650 },
        },
    });

    const page = await context.newPage();

    page.on('console', msg => {
        if (msg.text().includes('[AutoPlayer]')) console.log(msg.text());
    });

    console.log(`🌐 Navigating to ${url}`);
    await page.goto(url);

    console.log('⏳ Waiting for puzzle to be solved...');
    try {
        await page.waitForSelector('.victory-card', { timeout: 300000 });
    } catch {
        console.error('❌ Puzzle was not solved within 300s.');
        await context.close();
        await browser.close();
        process.exit(1);
    }

    // Linger on the victory screen a moment
    await page.waitForTimeout(3000);

    console.log('✅ Puzzle solved. Saving video...');
    const videoPath = await page.video().path();
    await context.close();
    await browser.close();

    if (fs.existsSync(webmPath)) fs.unlinkSync(webmPath);
    fs.renameSync(videoPath, webmPath);
    console.log(`🎥 Raw WebM: ${webmPath}`);

    // Convert to MP4
    console.log('🔄 Converting to MP4...');
    await new Promise((resolve, reject) => {
        ffmpeg(webmPath)
            .outputOptions([
                '-pix_fmt yuv420p',
                '-c:v libx264',
                '-crf 22',
                '-preset medium',
            ])
            .save(mp4Path)
            .on('end', () => {
                console.log(`✅ Saved: ${mp4Path}`);
                resolve(undefined);
            })
            .on('error', (err) => {
                console.error('❌ Conversion error:', err);
                reject(err);
            });
    });

    // Clean up temp WebM
    if (fs.existsSync(webmPath)) {
        fs.unlinkSync(webmPath);
        console.log('🧹 Cleaned up temporary WebM.');
    }

    console.log('🎉 Tutorial video ready: docs/how_to_play.mp4');
}

generateTutorialVideo().catch(console.error);

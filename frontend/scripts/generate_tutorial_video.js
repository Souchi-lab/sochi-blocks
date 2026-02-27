import { chromium } from 'playwright';
import ffmpeg from 'fluent-ffmpeg';
import ffmpegStatic from 'ffmpeg-static';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

ffmpeg.setFfmpegPath(ffmpegStatic);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Simulate a smooth mouse drag on the canvas to orbit the 3D viewer.
 * OrbitControls listens to real DOM events, so Playwright mouse drag works directly.
 */
async function smoothOrbit(page, fromX, fromY, toX, toY, steps = 40) {
    await page.mouse.move(fromX, fromY);
    await page.mouse.down();
    for (let i = 1; i <= steps; i++) {
        const x = fromX + (toX - fromX) * i / steps;
        const y = fromY + (toY - fromY) * i / steps;
        await page.mouse.move(x, y);
        await page.waitForTimeout(30); // ~30fps feel
    }
    await page.mouse.up();
}

async function generateTutorialVideo() {
    const puzzleId = process.argv[2] || '20260226_001';

    // delay=4000 gives the autoplay a 4-second head start pause
    // during which we perform the camera orbit demo
    const ORBIT_DURATION_MS = 4000;
    const url = `http://localhost:5173/viewer.html?puzzle_id=${puzzleId}&autoplay=1&delay=${ORBIT_DURATION_MS}`;

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

    // ── Camera orbit demo ────────────────────────────────────────────
    // Wait for the 3D canvas to be ready (WebGL initialized)
    console.log('🎥 Waiting for 3D canvas...');
    await page.waitForSelector('.viewer-area canvas');
    await page.waitForTimeout(800); // let WebGL settle

    // Get the viewer-area bounding box (left panel only, not sidebar)
    const viewerArea = page.locator('.viewer-area').first();
    const box = await viewerArea.boundingBox();

    if (box) {
        const cx = box.x + box.width / 2;
        const cy = box.y + box.height / 2;

        console.log('🔄 Performing camera orbit demo...');

        // Sweep 1: slow horizontal orbit (left → right) — shows the 3D depth
        await smoothOrbit(page, cx - 120, cy + 10, cx + 80, cy - 20, 50);
        await page.waitForTimeout(400);

        // Sweep 2: diagonal — shows the stacked layers (top-down angle)
        await smoothOrbit(page, cx + 40, cy + 80, cx - 40, cy - 60, 40);
        await page.waitForTimeout(400);

        // Sweep 3: gentle return orbit to a natural viewing angle
        await smoothOrbit(page, cx - 40, cy - 20, cx + 30, cy + 10, 30);
        await page.waitForTimeout(400);

        console.log('✅ Camera orbit done. Waiting for autoplay to start...');
    } else {
        console.warn('⚠️  Could not find .viewer-area — skipping camera orbit.');
    }

    // ── Wait for autoplay to solve the puzzle ────────────────────────
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

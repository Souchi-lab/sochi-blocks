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
    const puzzleId = process.argv[2] || '20260224_001';
    const url = `http://localhost:5173/viewer.html?puzzle_id=${puzzleId}&autoplay=1`;
    const outputDir = path.join(__dirname, '..', 'public', 'sns_videos');

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    const webmPath = path.join(outputDir, `${puzzleId}.webm`);
    const mp4Path = path.join(outputDir, `${puzzleId}.mp4`);
    const gifPath = path.join(outputDir, `${puzzleId}.gif`);

    console.log(`🎬 Launching browser for puzzle: ${puzzleId}`);
    // We launch headless, but recording still works
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 600, height: 600 },
        recordVideo: {
            dir: outputDir,
            size: { width: 600, height: 600 }
        }
    });

    const page = await context.newPage();

    // Pipe browser console logs to terminal
    page.on('console', msg => {
        if (msg.text().includes('[AutoPlayer]')) {
            console.log(msg.text());
        }
    });

    console.log(`🌐 Navigating to ${url}`);
    await page.goto(url);

    console.log('⏳ Waiting for puzzle to be solved (Victory screen)...');
    // Wait for the "Victory" indicator to appear
    try {
        await page.waitForSelector('.victory-card', { timeout: 300000 });
    } catch (err) {
        console.error('❌ Failed to solve puzzle within 300s.');
        await context.close();
        await browser.close();
        process.exit(1);
    }

    // Wait an extra 2.5 seconds to show the completed puzzle cleanly in the video
    await page.waitForTimeout(2500);

    console.log('✅ Puzzle solved. Capturing video...');
    const videoPath = await page.video().path();
    await context.close();
    await browser.close();

    // Overwrite existing if any
    if (fs.existsSync(webmPath)) fs.unlinkSync(webmPath);
    fs.renameSync(videoPath, webmPath);
    console.log(`🎥 Video saved as WebM: ${webmPath}`);

    // Convert to MP4
    console.log('🔄 Converting to MP4 and GIF for SNS...');

    const convertToMp4 = new Promise((resolve, reject) => {
        ffmpeg(webmPath)
            .outputOptions([
                '-pix_fmt yuv420p',
                '-c:v libx264',
                '-crf 23',
                '-preset medium'
            ])
            .save(mp4Path)
            .on('end', () => {
                console.log(`✅ Saved MP4: ${mp4Path}`);
                resolve();
            })
            .on('error', (err) => {
                console.error('❌ MP4 conversion error:', err);
                reject(err);
            });
    });

    const convertToGif = new Promise((resolve, reject) => {
        ffmpeg(webmPath)
            .outputOptions([
                '-vf scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse'
            ])
            .save(gifPath)
            .on('end', () => {
                console.log(`✅ Saved GIF: ${gifPath}`);
                resolve();
            })
            .on('error', (err) => {
                console.error('❌ GIF conversion error:', err);
                reject(err);
            });
    });

    await Promise.all([convertToMp4, convertToGif]).then(() => {
        // Clean up temporary WebM
        if (fs.existsSync(webmPath)) {
            fs.unlinkSync(webmPath);
            console.log(`🧹 Cleaned up temporary WebM: ${puzzleId}.webm`);
        }
        console.log('🎉 All done! Ready for SNS posting.');
    }).catch(err => {
        console.error('❌ Finalization error:', err);
    });
}

generateVideo().catch(console.error);

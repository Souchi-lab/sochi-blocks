/**
 * generate_tutorial_video.js
 *
 * SoChi BLOCKS チュートリアル動画（約30秒）を Playwright で録画する。
 * video_mode=tutorial を使い、TutorialVideoOverlay を通じてステップテキストを表示する。
 *
 * 使い方:
 *   node frontend/scripts/generate_tutorial_video.js [puzzle_id] [--lang ja|en]
 *
 * 例:
 *   node frontend/scripts/generate_tutorial_video.js 20260313_001
 *   node frontend/scripts/generate_tutorial_video.js 20260313_001 --lang en
 *
 * 事前準備:
 *   npm run dev --prefix frontend  ← localhost:5173 を起動しておく
 *
 * 出力:
 *   frontend/public/sns_videos/tutorial_ja.mp4  (または tutorial_en.mp4)
 *   docs/sns_videos/tutorial_ja.mp4             (GitHub Pages 用にコピー)
 */

import { chromium } from 'playwright';
import ffmpeg from 'fluent-ffmpeg';
import ffmpegStatic from 'ffmpeg-static';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

ffmpeg.setFfmpegPath(ffmpegStatic);

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

async function generateTutorialVideo() {
    const rawArgs    = process.argv.slice(2);
    const positional = rawArgs.filter(a => !a.startsWith('--'));

    // puzzle_id
    const puzzleId = positional[0] || '20260313_001';

    // --lang ja|en
    const langIdx = rawArgs.indexOf('--lang');
    const lang = langIdx >= 0 ? (rawArgs[langIdx + 1] ?? 'ja') : 'ja';
    if (lang !== 'ja' && lang !== 'en') {
        console.error(`❌ --lang must be "ja" or "en", got: "${lang}"`);
        process.exit(1);
    }

    // tutorial モード URL (sns=1 不要: tutorial は実際のゲームUIを表示する)
    const url = [
        `http://localhost:5173/viewer.html`,
        `?puzzle_id=${puzzleId}`,
        `&autoplay=1`,
        `&video_mode=tutorial`,
        `&lang=${lang}`,
    ].join('');

    const outputDir = path.join(__dirname, '..', 'public', 'sns_videos');
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    const baseName = `tutorial_${lang}`;
    const webmPath = path.join(outputDir, `${baseName}.webm`);
    const mp4Path  = path.join(outputDir, `${baseName}.mp4`);

    console.log(`🎬 Tutorial video  puzzle=${puzzleId}  lang=${lang}`);
    console.log(`🌐 ${url}`);

    const browser = await chromium.launch({ headless: true });

    // モバイルビューポート — 実際のスマホ UI を録画する
    const context = await browser.newContext({
        viewport: { width: 390, height: 844 },
        recordVideo: {
            dir: outputDir,
            size: { width: 390, height: 844 },
        },
    });

    const page = await context.newPage();
    const t0 = Date.now();
    const ts = () => `+${((Date.now() - t0) / 1000).toFixed(2)}s`;

    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('[AutoPlayer]') || text.includes('[Tutorial]')) {
            console.log(`${ts()} ${text}`);
        }
    });

    await page.goto(url);

    console.log(`${ts()} ⏳ Waiting for .victory-screen-done ...`);

    // tutorial は約30秒なので 120秒でタイムアウト
    try {
        await page.waitForSelector('.victory-screen-done', { timeout: 120000 });
    } catch {
        console.error('❌ .victory-screen-done not found within 120s');
        await context.close();
        await browser.close();
        process.exit(1);
    }

    console.log(`${ts()} ✅ victory-screen-done detected`);
    // CTA アニメーションが落ち着くまで待つ
    await page.waitForTimeout(2500);

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

    console.log('🔄 Converting to MP4...');
    ffmpeg(webmPath)
        .outputOptions([
            '-pix_fmt yuv420p',
            '-c:v libx264',
            '-crf 22',
            '-preset superfast',
        ])
        .save(mp4Path)
        .on('end', () => {
            console.log(`✅ MP4 saved: ${mp4Path}`);

            if (fs.existsSync(webmPath)) {
                fs.unlinkSync(webmPath);
                console.log('🧹 Cleaned up WebM.');
            }

            // docs/sns_videos/ にコピー (GitHub Pages 用)
            const docsDir = path.join(__dirname, '..', '..', 'docs', 'sns_videos');
            if (fs.existsSync(docsDir)) {
                const docsMp4 = path.join(docsDir, `${baseName}.mp4`);
                fs.copyFileSync(mp4Path, docsMp4);
                console.log(`📂 Synced to docs: ${docsMp4}`);
            }

            console.log('\n🎉 Done!');
            console.log(`   JP: node frontend/scripts/generate_tutorial_video.js ${puzzleId} --lang ja`);
            console.log(`   EN: node frontend/scripts/generate_tutorial_video.js ${puzzleId} --lang en`);
            process.exit(0);
        })
        .on('error', err => {
            console.error('❌ Conversion error:', err);
            process.exit(1);
        });
}

generateTutorialVideo().catch(console.error);

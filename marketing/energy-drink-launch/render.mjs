// Export launch.html to an MP4: renders every frame deterministically in headless Chromium
// and pipes it to ffmpeg together with the soundtrack from soundtrack.py.
//
//   python3 soundtrack.py                 # writes soundtrack.wav
//   node render.mjs [out.mp4] [fps]       # needs playwright + ffmpeg (FFMPEG env var to override)
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const dir = path.dirname(fileURLToPath(import.meta.url));
const out = path.resolve(process.argv[2] ?? path.join(dir, 'voltra-launch.mp4'));
const fps = Number(process.argv[3] ?? 30);
const ffmpeg = process.env.FFMPEG ?? 'ffmpeg';
const audio = path.join(dir, 'soundtrack.wav');

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(pathToFileURL(path.join(dir, 'launch.html')).href + '?render');
const duration = await page.evaluate(() => window.DURATION);
const frames = Math.round(duration * fps);

const args = ['-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-'];
if (existsSync(audio)) args.push('-i', audio, '-c:a', 'aac', '-b:a', '192k', '-shortest');
args.push('-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out);
const ff = spawn(ffmpeg, args, { stdio: ['pipe', 'inherit', 'inherit'] });

const canvas = page.locator('canvas');
for (let i = 0; i < frames; i++) {
  await page.evaluate(t => window.render(t), i / fps);
  const jpg = await canvas.screenshot({ type: 'jpeg', quality: 95 });
  if (!ff.stdin.write(jpg)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % fps === 0) process.stderr.write(`frame ${i}/${frames}\n`);
}
ff.stdin.end();
await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}`)))));
await browser.close();
console.log(`wrote ${out}`);

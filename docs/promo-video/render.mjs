// Renders video.html frame by frame.
// Usage: node render.mjs <shotsDir> <outDir> [--lang zh|en] [--format wide|square] [--fps 30] [--at t1,t2,...]
import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : def; };
const [shotsDir, outDir] = args.slice(0, 2).map(a => resolve(a));
const fps = Number(opt('--fps', 30));
const at = opt('--at', null);
const lang = opt('--lang', 'zh');
const format = opt('--format', 'wide');
mkdirSync(outDir, { recursive: true });

const here = dirname(fileURLToPath(import.meta.url));
const shots = JSON.parse(readFileSync(`${shotsDir}/shots.json`, 'utf8'));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('pageerror', e => { console.error('page error:', e.message); process.exit(1); });
await page.goto(`${pathToFileURL(`${here}/video.html`).href}?lang=${lang}&format=${format}`);
await page.evaluate(async ([s, d]) => { await window.setup(s, d, s.comment.at(-1).file); await document.fonts.ready; }, [shots, pathToFileURL(shotsDir).href]);
const timeline = await page.evaluate(() => window.TIMELINE);
await page.setViewportSize(timeline.size);
writeFileSync(`${outDir}/timeline.json`, JSON.stringify(timeline, null, 2));

const times = at ? at.split(',').map(Number) : Array.from({ length: Math.ceil(timeline.duration * fps) }, (_, i) => i / fps);
const started = Date.now();
for (const [i, t] of times.entries()) {
  await page.evaluate(t => window.renderFrame(t), t);
  const name = at ? `still-${t.toFixed(2)}.jpg` : `f${String(i).padStart(5, '0')}.jpg`;
  await page.screenshot({ path: `${outDir}/${name}`, type: 'jpeg', quality: 94 });
  if (i % 150 === 0) console.log(`frame ${i}/${times.length} t=${t.toFixed(2)} ${((Date.now() - started) / 1000).toFixed(0)}s`);
}
await browser.close();
console.log(`done: ${times.length} frames, ${timeline.events.length} sound events, ${timeline.duration.toFixed(2)}s`);

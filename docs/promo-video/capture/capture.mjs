// Drives the real Taco shell and captures UI keyframes for the promo video.
// Usage: node capture.mjs <file.taco.html> <outDir> [zh|en]
import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';

const LANGS = {
  zh: { locale: 'zh-CN', phrase: 'spec 不该', comment: '这句做成片头大字！🌮', author: '小林',
        bubble: '评论', add: '添加评论', handoff: '交接改动' },
  en: { locale: 'en-US', phrase: 'a spec should not', comment: 'Make this the opening title! 🌮', author: 'Alex',
        bubble: 'Comment', add: 'Add comment', handoff: 'Handoff' },
};
const [file, outDir, lang = 'zh'] = process.argv.slice(2);
const L = LANGS[lang];
mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'], viewport: { width: 1440, height: 810 }, deviceScaleFactor: 2, locale: L.locale });
const page = await context.newPage();
await page.goto('file://' + file);
await page.waitForTimeout(2000);

const shots = {};
let cursor = { x: 720, y: 600 };
async function shot(scene, opts = {}) {
  shots[scene] ??= [];
  const name = `${scene}-${String(shots[scene].length).padStart(2, '0')}.png`;
  await page.screenshot({ path: `${outDir}/${name}` });
  shots[scene].push({ file: name, cursor: { ...cursor }, click: !!opts.click });
}
async function move(x, y) { cursor = { x, y }; await page.mouse.move(x, y); }
async function center(locator) {
  const b = await locator.boundingBox();
  return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
}

// 1. Browse
await move(120, 300);
await shot('browse');

// 2. Select a phrase with a real drag
const box = await page.evaluate(phrase => {
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const i = n.data.indexOf(phrase);
    if (i < 0) continue;
    const r = document.createRange();
    r.setStart(n, i); r.setEnd(n, i + 1);
    const a = r.getBoundingClientRect();
    r.setStart(n, n.data.length - 2); r.setEnd(n, n.data.length - 1);
    const z = r.getBoundingClientRect();
    return { x1: a.left + 1, y1: a.top + a.height / 2, x2: z.right, y2: z.top + z.height / 2 };
  }
}, L.phrase);
await move(box.x1, box.y1);
await shot('select');
await page.mouse.down();
const steps = 8;
for (let s = 1; s <= steps; s++) {
  const t = s / steps;
  // a phrase that wraps: sweep right along line 1, then drop to line 2
  const wraps = Math.abs(box.y2 - box.y1) > 5;
  const x = !wraps ? box.x1 + (box.x2 - box.x1) * t
    : t < 0.6 ? box.x1 + (1055 - box.x1) * (t / 0.6) : 1055 + (box.x2 - 1055) * ((t - 0.6) / 0.4);
  const y = !wraps || t >= 0.6 ? box.y2 : box.y1;
  await move(x, y);
  await shot('select');
}
await page.mouse.up();
await page.waitForTimeout(500);
await shot('select');

// 3. Comment
const bubble = page.getByText(L.bubble, { exact: true }).last();
const bc = await center(bubble);
await move(bc.x, bc.y);
await shot('comment', { click: true });
await bubble.click();
await page.waitForTimeout(500);
await shot('comment');
// type in exactly ten chunks so every language yields the same keyframes
const chars = [...L.comment];
for (let i = 0; i < 10; i++) {
  await page.keyboard.insertText(chars.slice(Math.round(i * chars.length / 10), Math.round((i + 1) * chars.length / 10)).join(''));
  await page.waitForTimeout(40);
  await shot('comment');
}
const add = page.getByRole('button', { name: L.add, exact: true });
const ac = await center(add);
await move(ac.x, ac.y);
await shot('comment', { click: true });
await add.click();
const nameDialog = page.locator('dialog.author-name-dialog');
await nameDialog.waitFor({ timeout: 1500 }).catch(() => {});
if (await nameDialog.isVisible()) {
  await nameDialog.locator('input').fill(L.author);
  await nameDialog.getByRole('button', { name: L.add, exact: true }).click();
}
await page.waitForTimeout(700);
await shot('comment');

// 4. Mermaid diagram
const mmd = page.getByRole('button', { name: 'review-loop.mmd' });
const mc = await center(mmd);
await move(mc.x, mc.y);
await shot('diagram', { click: true });
await mmd.click();
await page.waitForTimeout(2500);
await move(760, 500);
await shot('diagram');

// 5. Storyboard
const sb = page.getByRole('button', { name: 'storyboard.md' });
const sc = await center(sb);
await move(sc.x, sc.y);
await sb.click();
await page.waitForTimeout(900);
await shot('storyboard', { click: true });

// 6. Handoff
const ho = page.getByRole('button', { name: L.handoff, exact: true }).first();
const hc = await center(ho);
await move(hc.x, hc.y);
await shot('handoff', { click: true });
await ho.click();
await page.waitForTimeout(900);
await shot('handoff');
const handoffText = await page.evaluate(() => navigator.clipboard.readText());
writeFileSync(`${outDir}/handoff.txt`, handoffText);

writeFileSync(`${outDir}/shots.json`, JSON.stringify(shots, null, 2));
await browser.close();
console.log(Object.fromEntries(Object.entries(shots).map(([k, v]) => [k, v.length])));

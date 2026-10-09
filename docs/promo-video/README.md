# Taco promo video

A 54-second promo video in Chinese (`zh`) and English (`en`), in two formats: `wide` (1920×1080) and `square` (1080×1080). The square cut is for social feeds such as X, where small players shrink a 16:9 video too far to read: its type is larger, and the camera zooms in on the real UI and follows the cursor. The video's own storyboard is a Taco (`storyboard/`), and every product shot in it is a real screenshot of the production shell. Playwright drives that shell: it opens the file, selects text, writes a comment, opens the Mermaid diagram, and hands off to an Agent. The motion graphics and the soundtrack are both generated in code, with no external assets.

| File | Purpose |
| --- | --- |
| `storyboard/`, `storyboard-en/` | The storyboard Markdown, Mermaid diagram, and music notes (Chinese / English) |
| `capture/capture.mjs` | Drives `skills/taco/taco-shell.html` and captures the UI keyframes plus the Handoff text |
| `video.html` | Deterministic composition with all on-screen copy for both languages (`?lang=zh\|en`): `renderFrame(t)` is a pure function of time, and `TIMELINE` exports the sound events |
| `render.mjs` | Renders `video.html` frame by frame with Chromium |
| `score.py` | Synthesizes the soundtrack with numpy from the timeline (112 BPM, Am–F–C–G) |

## Rebuild

```sh
node skills/taco/scripts/pack.mjs --dir docs/promo-video/storyboard --out tmp/Taco_宣传片.taco.html \
  --title "Taco 宣传片" --entry spec.md \
  --group "策划=spec.md,music.md" --group "分镜=scenes/storyboard.md,diagrams/review-loop.mmd"
node docs/promo-video/capture/capture.mjs "$PWD/tmp/Taco_宣传片.taco.html" tmp/promo/shots
node docs/promo-video/render.mjs tmp/promo/shots tmp/promo/frames      # use --at 3,18,40 for stills
python3 docs/promo-video/score.py tmp/promo/frames/timeline.json tmp/promo/score.wav
ffmpeg -framerate 30 -i tmp/promo/frames/f%05d.jpg -i tmp/promo/score.wav \
  -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest \
  -movflags +faststart tmp/taco-promo.mp4
```

For the English cut, pack `storyboard-en/` as `tmp/Taco_Promo.taco.html` (`--title "Taco Promo"`, groups `Planning=spec.md,music.md` and `Storyboard=scenes/storyboard.md,diagrams/review-loop.mmd`), then pass `en` as the third argument to `capture.mjs` and `--lang en` to `render.mjs`; the remaining steps are the same. Add `--format square` to `render.mjs` for the square cut.

Requirements: Node 22 with Playwright and Chromium, Python 3 with numpy, and ffmpeg. The scripts import Playwright from `/opt/node-tools/node_modules/playwright`; change that path to match your environment.

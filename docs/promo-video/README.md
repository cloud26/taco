# Taco promo video

A 54-second, 1920×1080 promo video. The video's own storyboard is a Taco (`storyboard/`), and every product shot in it is a real screenshot of the production shell. Playwright drives that shell: it opens the file, selects text, writes a comment, opens the Mermaid diagram, and hands off to an Agent. The motion graphics and the soundtrack are both generated in code, with no external assets.

| File | Purpose |
| --- | --- |
| `storyboard/` | The storyboard Markdown, Mermaid diagram, and music notes |
| `capture/capture.mjs` | Drives `skills/taco/taco-shell.html` and captures the UI keyframes plus the Handoff text |
| `video.html` | Deterministic composition: `renderFrame(t)` is a pure function of time, and `TIMELINE` exports the sound events |
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

Requirements: Node 22 with Playwright and Chromium, Python 3 with numpy, and ffmpeg. The scripts import Playwright from `/opt/node-tools/node_modules/playwright`; change that path to match your environment.

# VOLTRA — energy drink launch video

A 24-second, 1920×1080 launch film for **VOLTRA Citrus Ginger Surge**, a fictional zero-sugar energy drink.

**Watch:** [`voltra-launch.mp4`](voltra-launch.mp4). You can also open `launch.html` in a browser to see a live, looping preview.

| Time | Scene |
|------|-------|
| 0–3 s | "Something is charging": a battery fills up while electric arcs flicker around it |
| 3–11 s | Flash, splash and the can reveal, the VOLTRA title slam, "Clean energy", then the flavor callout with rising bubbles |
| 11–16 s | "What's inside": 0 g sugar, 120 mg natural caffeine, B-vitamins, no artificial colors or preservatives |
| 16–21 s | The label is scanned in GuessIngs: the ingredients get checked off and the verdict is **GREEN** |
| 21–24 s | End card: "Clean energy. Nothing to hide.", then **AVAILABLE NOW** |

The ingredient list in the scan scene was run through the app's own deterministic engine
(`backend/app/services/scoring.py`), and it came back GREEN. Green tea extract, ginger juice, natural caffeine and
stevia aren't in the knowledge base yet, so they don't change the score.

## Re-render

Every frame is a pure function of time (`window.render(t)` in `launch.html`), so the export is frame-exact.

```bash
python3 soundtrack.py            # synthesizes soundtrack.wav (standard library only)
node render.mjs                  # headless Chromium via Playwright, pipes frames to ffmpeg → voltra-launch.mp4
# FFMPEG=/path/to/ffmpeg node render.mjs out.mp4 60   # custom ffmpeg binary, output and fps
```

To change the brand, flavor, claims or timing, edit the constants and scene functions in `launch.html`.

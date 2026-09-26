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

## Music

The video has an **original Bollywood / bhangra-style track** made by `bollywood_soundtrack.py`, so there are no
copyright claims when you post it. It plays in D with a Bhairav-flavoured scale at 100 BPM, and each section follows a scene:

| Time | Music |
|------|-------|
| 0–3 s | Tanpura drone, a rising sitar run, then a dhol roll into the reveal |
| 3–16 s | Dhol chaal groove with a tumbi riff, claps, chimta and bass, plus a sitar lead over "What's inside" |
| 16–21 s | Breakdown during the scan: bansuri melody, tanpura and soft tabla |
| 21–24 s | Full groove, then a **tihai** (the phrase played three times) that lands on the final hit |

`soundtrack.py` still makes the original electronic track. To use a real song you have a licence for, swap the audio
without re-rendering the video:

```bash
ffmpeg -i voltra-launch.mp4 -i song.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4
```

## Re-render

Every frame is a pure function of time (`window.render(t)` in `launch.html`), so the export is frame-exact.

```bash
python3 bollywood_soundtrack.py  # synthesizes soundtrack.wav (standard library only)
node render.mjs                  # headless Chromium via Playwright, pipes frames to ffmpeg → voltra-launch.mp4
# FFMPEG=/path/to/ffmpeg node render.mjs out.mp4 60   # custom ffmpeg binary, output and fps
# AUDIO=song.mp3 node render.mjs                     # any other audio file
```

To change the brand, flavor, claims or timing, edit the constants and scene functions in `launch.html`.

"""Render reel.html to an Instagram Reel (MP4) plus carousel slides and a cover image."""
import pathlib, subprocess, sys
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
FPS = 30
URL = (HERE / "reel.html").as_uri()

def main():
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        # --- Reel 1080x1920 ---
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(URL + "?w=1080&h=1920"); page.evaluate("Promise.all([...document.fonts].map(f => f.load()))")
        page.evaluate("document.fonts.ready"); assert page.evaluate("document.fonts.check('800 40px Bricolage Grotesque') && document.fonts.check('500 40px Inter')"), "fonts missing"
        page.wait_for_timeout(800)
        duration = page.evaluate("DURATION")
        frames = int(duration * FPS)
        proc = subprocess.Popen([ffmpeg, "-y", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                                 "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "18",
                                 "-preset", "medium", "-movflags", "+faststart", "-c:a", "aac",
                                 str(OUT / "reel_day01_germany_top_destination.mp4")],
                                stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        for i in range(frames):
            page.evaluate(f"render({i / FPS})")
            proc.stdin.write(page.screenshot(type="jpeg", quality=95))
            if i % 150 == 0:
                print(f"frame {i}/{frames}", file=sys.stderr)
        proc.stdin.close(); proc.wait()
        # cover: hook scene fully built
        page.evaluate("render(0, true)")
        page.screenshot(path=str(OUT / "reel_cover.png"))
        page.close()
        # --- Carousel 1080x1350 ---
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.goto(URL + "?w=1080&h=1350&mode=carousel"); page.evaluate("Promise.all([...document.fonts].map(f => f.load()))")
        page.evaluate("document.fonts.ready"); assert page.evaluate("document.fonts.check('800 40px Bricolage Grotesque') && document.fonts.check('500 40px Inter')"), "fonts missing"
        page.wait_for_timeout(800)
        for i in range(page.evaluate("SCENE_COUNT")):
            page.evaluate(f"render({i}, true)")
            page.screenshot(path=str(OUT / "carousel" / f"slide_{i + 1:02d}.png"))
        browser.close()

if __name__ == "__main__":
    main()

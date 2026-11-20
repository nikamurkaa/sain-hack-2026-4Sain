"""Compare the isolated React frames with the original Figma handoff at 2x.

Start Vite locally, then run compare.py HANDOFF.zip OUTPUT_DIRECTORY.
Requires Python Playwright, Pillow and a Chromium installation.
"""
import argparse
import json
import os
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

from PIL import Image, ImageChops, ImageEnhance, ImageStat
from playwright.sync_api import sync_playwright

BOUNDS = """root => [...root.querySelectorAll('.design-widget')].map(el => {
  function box(e) {const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]}
  return {box:box(el), labels:[...el.querySelectorAll('.design-label')].map(e=>{
    const s=getComputedStyle(e);
    return {box:box(e), family:s.fontFamily.split(',')[0].replace(/["']/g,''),
      size:parseFloat(s.fontSize), weight:Number(s.fontWeight),
      loaded:document.fonts.check(s.fontWeight+' '+s.fontSize+' '+s.fontFamily,e.textContent),
      text:e.textContent};
  })};
})"""


def audit_geometry(actual, blocks):
    deviations, font_errors, text_errors = [], [], []
    for component, block in zip(actual, blocks, strict=True):
        x, y, _, _ = block["box"]
        deviations.extend(abs(a-b) for a,b in zip(component["box"],block["box"]))
        for label, design in zip(component["labels"], block["texts"], strict=True):
            dx,dy,w,h = design["box"]
            deviations.extend(abs(a-b) for a,b in zip(label["box"],[x+dx,y+dy,w,h]))
            if (label["family"] != design["font"] or abs(label["size"]-design["size"])>.01
                    or label["weight"] != design["weight"] or not label["loaded"]):
                font_errors.append(design["value"])
            if label["text"] != design.get("lines",design["value"]).replace("\u2028","\n"):
                text_errors.append(design["value"])
    return dict(max_css_px=round(max(deviations),3), font_errors=font_errors, text_errors=text_errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--port",type=int,default=5160)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    frames=json.loads((Path(__file__).resolve().parents[2]/"src/design/frames.json").read_text())
    report=[]
    with ZipFile(args.handoff) as archive, sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
        page=browser.new_page(viewport=dict(width=375,height=812),device_scale_factor=2)
        page.route("**/*",lambda route: route.continue_() if route.request.url.startswith(f"http://127.0.0.1:{args.port}/") else route.abort())
        for i,frame in enumerate(frames,1):
            prefix=f"{i:02}"
            entry=next(n for n in archive.namelist() if n.startswith(f"screens/{prefix}_") and n.endswith(".png"))
            reference=Image.open(BytesIO(archive.read(entry))).convert("RGB")
            page.goto(f"http://127.0.0.1:{args.port}/tests/visual/fixture.html?frame={i}")
            root=page.locator(".design-frame")
            root.wait_for()
            page.evaluate("document.fonts.ready")
            page.wait_for_load_state("networkidle")
            path=args.output/f"{prefix}-browser.png"
            page.screenshot(path=path)
            actual=Image.open(path).convert("RGB")
            assert actual.size == reference.size == (750,1624)
            diff=ImageChops.difference(reference,actual)
            ImageEnhance.Brightness(diff).enhance(3).save(args.output/f"{prefix}-diff.png")
            Image.blend(reference,actual,0.5).save(args.output/f"{prefix}-overlay.png")
            stats=audit_geometry(root.evaluate(BOUNDS),frame["blocks"])
            regions={}
            for block in frame["blocks"]:
                x,y,w,h=block["box"]
                box=tuple(round(2*p) for p in (x,y,x+w,y+h))
                if w>=1 and h>=1:
                    regions[block["name"]+f" ({x}, {y})"]=round(sum(ImageStat.Stat(diff.crop(box)).mean)/3,2)
            report.append(dict(frame=i,title=frame["title"],geometry=stats,region_rgb_error=regions))
        browser.close()
    (args.output/"checks.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if any(r["geometry"]["max_css_px"]>.1 or r["geometry"]["text_errors"] or r["geometry"]["font_errors"] for r in report):
        raise SystemExit("See checks.json for differences in layout or text.")

if __name__ == "__main__":
    main()

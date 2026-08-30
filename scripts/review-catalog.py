#!/usr/bin/env python3
"""Lay every product's photos beside its description, to find misfiled images.

kumiko-asanoha is described as a six-armed star on a triangular grid and
photographed as a square grid with a fan, a nested square and a diamond
lattice. Either its images belong to another product or it is mis-named. This
puts each listing's words next to its pictures so the mismatch is visible
rather than argued about.

Needs the Shopify CDN, so it runs on a GitHub runner.
"""
import glob, html, json, os, pathlib, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "catalog-review"
CHROME = os.environ.get("CHROME_BIN", "chrome-headless-shell")
PER_PRODUCT = 3

def fetch(url, dest):
    if dest.exists():
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "autoreels/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if len(data) < 2048:
            return False
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"    ! {dest.name}: {e}", file=sys.stderr)
        return False

def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "kumiko-*"
    (OUT / "img").mkdir(parents=True, exist_ok=True)
    rows = []
    for f in sorted(glob.glob(str(ROOT / "examples" / "catalog" / f"{pattern}.json"))):
        d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        print(f"  {d['handle']}")
        imgs = []
        for img in d.get("images", [])[:PER_PRODUCT]:
            name = f"{d['handle']}--" + img["url"].split("/")[-1].split("?")[0]
            if fetch(img["url"], OUT / "img" / name):
                imgs.append(name)
        rows.append({
            "handle": d["handle"],
            "title": d["title"],
            "desc": " ".join(d.get("description", "").split())[:300],
            "imgs": imgs,
        })

    cards = []
    for r in rows:
        shots = "".join(f'<img src="img/{html.escape(i)}">' for i in r["imgs"])
        cards.append(
            f'<section><h2>{html.escape(r["title"])}'
            f'<span class="h">{html.escape(r["handle"])}</span></h2>'
            f'<p>{html.escape(r["desc"])}…</p><div class="row">{shots}</div></section>')

    page = f"""<!doctype html><meta charset="utf-8"><style>
      body {{ margin:0; padding:32px; background:#ede6d8; color:#2a2520;
             font:15px/1.5 Georgia,serif; width:1560px; }}
      h1 {{ font-size:26px; margin:0 0 6px; }}
      .lead {{ color:#5a5048; margin:0 0 28px; }}
      section {{ background:#fff; border:1px solid #d8cdb8; border-radius:8px;
                 padding:18px 20px; margin-bottom:20px; }}
      h2 {{ font-size:20px; margin:0 0 8px; }}
      .h {{ font:12px ui-monospace,monospace; color:#8a7f70; margin-left:12px; }}
      p {{ margin:0 0 14px; color:#4a4038; }}
      .row {{ display:flex; gap:12px; }}
      .row img {{ width:33%; height:300px; object-fit:cover; border-radius:5px;
                  background:#e3dccb; }}
    </style>
    <h1>Kapya.Craft — listing text against listing photos</h1>
    <p class="lead">Each card shows what the listing says, above what the
    listing shows. Read the words, then look at the grid in the pictures.</p>
    {''.join(cards)}"""

    (OUT / "index.html").write_text(page, encoding="utf-8")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--screenshot=" + str(OUT / "catalog-review.png"),
                    "--window-size=1624,%d" % (360 + 470 * len(rows)),
                    (OUT / "index.html").as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"\n{len(rows)} products -> {OUT / 'catalog-review.png'}")

if __name__ == "__main__":
    main()

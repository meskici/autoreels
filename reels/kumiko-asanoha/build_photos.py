#!/usr/bin/env python3
"""The photo cut: the same 20s script over the real product photography.

Differs from build.py in two ways that matter.

Photos replace the drawn lamp entirely. The drawn lamp exists only because this
container cannot reach the Shopify CDN; where the real frames are available
they win, every time.

The synthetic cast-wall pattern is gone. The brand profile is explicit - "the
wall pattern is the strongest and least copyable asset. Prefer real footage of
the lit lamp over any generated visual" - and no photo in the catalogue shows
the pattern on a wall. Faking it here would be inventing the one asset the
brand sells. Beat 4 runs the copy over the real lit frame instead, and
SHOT_NOTES records the photograph that would make this beat land.
"""
import json, pathlib, sys
from asanoha import W, H, CREAM, INK, GOLD, S, one_star

HERE = pathlib.Path(__file__).parent
ASSETS = HERE / "assets"

# Each shot names the photo by the alt text it was chosen for. `pos` is the
# CSS object-position of the cover crop - the one knob to turn if a shot
# frames badly, since the 6000x4000 originals crop hard to 9:16.
SHOTS = [
    dict(file="DSC02133.jpg",  t=0.00, pos="50% 50%", z0=1.18, z1=1.06,
         why="ışıkla dolan kafes deseni, yakın plan — the macro open"),
    dict(file="asanoha-4.jpg", t=3.95, pos="50% 45%", z0=1.04, z1=1.13,
         why="yanık halde: desen detayı — naming the motif"),
    dict(file="DSC02126.jpg",  t=7.75, pos="50% 50%", z0=1.16, z1=1.04,
         why="yemek masasında yanık halde — the pull back to the whole lamp"),
    dict(file="DSC02122.jpg",  t=11.95, pos="50% 50%", z0=1.04, z1=1.12,
         why="yandan görünüm, yanık kafes gövde — what the light does"),
    dict(file="Product_Staging-1efb1cf3-aada-4e9a-a96b-6f6bc59da6a2.jpg",
         t=16.35, pos="50% 45%", z0=1.10, z1=1.02,
         why="asanoha desenli el yapımı masa lambası — the close"),
]

SHOT_NOTES = """Beat 4 says the light carries the pattern to the wall, and no
photograph in the catalogue shows that. One phone shot - lamp lit, a metre off
a plain wall, room dark - would give this beat its own frame and would be the
single highest-value addition to the shoot."""

CAPS = [
    ("c1",  0.45,  3.70, "Şuna bak.",                         "Altı kollu bir yıldız."),
    ("c2",  4.15,  7.50, "Asanoha diyorlar.",                 "Kenevir yaprağından geliyor."),
    ("c3",  8.05, 11.70, "Kumiko’nun en çok işlenen motifi.", "Geleneğinde çıtalar çivisiz birleşiyor."),
    ("c4", 12.60, 16.10, "Işık kafesten geçerken deseni duvara taşıyor.", "Uzaklaştırdıkça gölge büyüyor, yumuşuyor."),
    ("c5", 16.60, 19.70, "Kumiko Serisi.",                    "Seninki hangi duvara düşecek?"),
]

def main():
    missing = [s["file"] for s in SHOTS if not (ASSETS / s["file"]).exists()]
    if missing:
        raise SystemExit("missing photos (run fetch_photos.py first): " + ", ".join(missing))

    star = one_star(46, 90, 90)

    shots_html = "\n".join(
        f'      <div class="shot" id="s{i}"><img src="assets/{s["file"]}" alt=""'
        f' data-layout-allow-overflow'
        f' style="object-position:{s["pos"]}"/></div>'
        for i, s in enumerate(SHOTS))

    caps_html = "\n".join(
        f'      <div class="cap" id="{c[0]}"><p class="l1">{c[3]}</p>'
        f'<p class="l2">{c[4]}</p></div>' for c in CAPS)

    kb = ",\n          ".join(
        f'{{sel:"#s{i} img", t:{s["t"]}, z0:{s["z0"]}, z1:{s["z1"]}}}'
        for i, s in enumerate(SHOTS))
    capjs = ",\n          ".join(
        f'{{sel:"#{c[0]}", i:{c[1]}, o:{c[2]}}}' for c in CAPS)

    html = f"""<!doctype html>
<html lang="tr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>Kumiko.Asanoha — motif (fotoğraflı kurgu)</title>
    <script src="vendor/gsap.min.js"></script>
    <style>
      @font-face {{
        font-family: "Playfair Display";
        src: url("fonts/PlayfairDisplay-Bold.ttf") format("truetype");
        font-weight: 700; font-style: normal;
      }}
      html, body {{ margin: 0; padding: 0; background: {INK}; }}
      #root {{
        position: relative; width: {W}px; height: {H}px; overflow: hidden;
        font-family: "Playfair Display", serif; font-weight: 700;
        background: {INK};
      }}
      .shot {{ position: absolute; inset: 0; opacity: 0; overflow: hidden; }}
      .shot img {{
        position: absolute; inset: 0;
        width: {W}px; height: {H}px;
        object-fit: cover;
        display: block;
      }}
      /* Keeps the caption legible over frames this build never got to see. */
      #band {{
        position: absolute; left: 0; right: 0; bottom: 0; height: 620px;
        background: linear-gradient(to bottom,
          rgba(26,22,18,0) 0%, rgba(26,22,18,0.72) 38%, rgba(26,22,18,0.94) 100%);
      }}
      .cap {{
        position: absolute; left: 0; right: 0; bottom: 172px;
        padding: 0 88px; opacity: 0;
      }}
      .cap p {{ margin: 0; text-align: left; letter-spacing: -0.005em; }}
      .cap .l1 {{ font-size: 62px; line-height: 1.15; color: {CREAM}; }}
      .cap .l2 {{ padding-top: 20px; font-size: 40px; line-height: 1.28; color: {GOLD}; }}
      /* The constructed motif appears as a drawn annotation beside the copy,
         never traced onto the photograph - it cannot be registered to a frame
         this build cannot see, and a misaligned overlay would misrepresent it. */
      #keymark {{ position: absolute; right: 88px; bottom: 452px; opacity: 0; }}
      #mark {{ position: absolute; left: 88px; bottom: 58px; opacity: 0; }}
      #mark .name {{ margin: 0; font-size: 34px; color: {CREAM}; letter-spacing: 0.02em; }}
      #mark .tag {{ margin: 6px 0 0; font-size: 26px; color: {GOLD}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="asanoha" data-start="0"
         data-width="{W}" data-height="{H}" data-duration="20">
{shots_html}

      <svg id="keymark" width="180" height="180" viewBox="0 0 180 180"
           xmlns="http://www.w3.org/2000/svg">
        <g fill="none" stroke="{GOLD}" stroke-width="4" stroke-linecap="round">
          <path d="{star}"/>
        </g>
      </svg>

      <div id="band"></div>
{caps_html}

      <div id="mark">
        <p class="name">Kapya.Craft</p>
        <p class="tag">Işık, katman katman.</p>
      </div>
    </div>

    <script>
      function build() {{
        const tl = gsap.timeline({{ paused: true }});

        const shots = [
          {kb}
        ];
        shots.forEach(function (s, i) {{
          const layer = "#s" + i;
          tl.fromTo(layer, {{ opacity: 0 }},
            {{ opacity: 1, duration: i === 0 ? 0.5 : 0.75, ease: "power2.inOut" }}, s.t);
          // Ken Burns: one slow continuous move per shot, no hold.
          tl.fromTo(s.sel, {{ scale: s.z0 }},
            {{ scale: s.z1, duration: 5.4, ease: "none" }}, s.t);
        }});

        tl.fromTo("#keymark", {{ opacity: 0, y: 16 }},
          {{ opacity: 0.95, y: 0, duration: 0.6, ease: "power3.out" }}, 4.4);
        tl.to("#keymark", {{ opacity: 0, duration: 0.5, ease: "power2.in" }}, 7.2);

        const caps = [
          {capjs}
        ];
        caps.forEach(function (c) {{
          tl.fromTo(c.sel, {{ opacity: 0, y: 26 }},
            {{ opacity: 1, y: 0, duration: 0.55, ease: "power3.out" }}, c.i);
          tl.to(c.sel, {{ opacity: 0, y: -18, duration: 0.45, ease: "power2.in" }}, c.o);
        }});

        tl.fromTo("#mark", {{ opacity: 0, y: 18 }},
          {{ opacity: 1, y: 0, duration: 0.7, ease: "power3.out" }}, 17.3);

        window.__timelines["asanoha"] = tl;
      }}
      if (document.fonts && document.fonts.ready) {{
        document.fonts.ready.then(build);
      }} else {{ build(); }}
    </script>
  </body>
</html>
"""
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote index.html (photo cut) — {len(SHOTS)} shots")
    for s in SHOTS:
        print(f"  {s['t']:>5.2f}s  {s['file']:<62} {s['why']}")
    print("\nNOTE:", " ".join(SHOT_NOTES.split()))

if __name__ == "__main__":
    main()

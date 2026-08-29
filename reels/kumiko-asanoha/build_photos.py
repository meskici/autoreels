#!/usr/bin/env python3
"""The Kumiko reel, written to the motif the photographs actually show.

The product description says asanoha - a six-armed star from the hemp leaf -
and the photographs do not show that. The panel is a square grid carrying a
fan along the top, a nested-square figure down one column and a diamond
lattice through the field. So the prose description is not used as a source
here. Every line traces to one of two things that can be checked: the
structured spec on the listing, or the photographs themselves.

Two claims from the old copy are gone for the same reason.

The motif is no longer named. The lamp is sold as "Kumiko.Asanoha" but nothing
on it is asanoha, so the video describes what is visible instead of repeating
a name the object contradicts.

The wall pattern is gone. The cells are backed by a white diffuser, which
spreads light rather than throwing a figure, and no photograph shows a pattern
cast on anything. The brand profile already makes this call for another
product - "Plise diffuses light rather than throwing a pattern. Never write
wall-pattern copy for it" - and it applies here on the same evidence.
"""
import json, pathlib, sys
W, H = 1080, 1920
CREAM, INK, GOLD = "#ede6d8", "#2a2520", "#c9a24b"

HERE = pathlib.Path(__file__).parent
ASSETS = HERE / "assets"

# Each shot names the photo by the alt text it was chosen for. `pos` is the
# CSS object-position of the cover crop - the one knob to turn if a shot
# frames badly, since the 6000x4000 originals crop hard to 9:16.
SHOTS = [
    dict(file="DSC02133.jpg",  t=0.00, dur=4.70, pos="50% 50%", z0=1.18, z1=1.06,
         why="ışıkla dolan kafes deseni, yakın plan — the macro open"),
    dict(file="asanoha-4.jpg", t=3.95, dur=4.55, pos="50% 45%", z0=1.04, z1=1.13,
         why="yanık halde: desen detayı — the figures, close"),
    dict(file="DSC02126.jpg",  t=7.75, dur=4.95, pos="50% 50%", z0=1.16, z1=1.04,
         why="yemek masasında yanık halde — the pull back to the whole lamp"),
    dict(file="DSC02122.jpg",  t=11.95, dur=5.15, pos="50% 50%", z0=1.04, z1=1.12,
         why="yandan görünüm, yanık kafes gövde — the light in a room"),
    dict(file="Product_Staging-1efb1cf3-aada-4e9a-a96b-6f6bc59da6a2.jpg",
         t=16.35, dur=3.65, pos="50% 45%", z0=1.10, z1=1.02,
         why="asanoha desenli el yapımı masa lambası — the close"),
]

SHOT_NOTES = """The listing contradicts its own photographs: it is titled
Kumiko.Asanoha and its description explains the six-armed hemp-leaf star, but
the lamp in all six images carries a fan, a nested square and a diamond
lattice on a square grid. Nothing here can fix that - either the title and
description belong to a different lamp, or this lamp is mis-named on the
store. Until it is settled the video describes the object and never names the
motif."""

CAPS = [
    ("c1",  0.45,  3.70, "Şuna bak.",                     "Tek bir desen değil."),
    ("c2",  4.15,  7.50, "Üstte yelpaze, ortada baklava.", "Hepsi aynı yüzde."),
    ("c3",  8.05, 11.70, "Kumiko geleneğinde çıtalar kareyi dolduruyor.", "Desen oradan çıkıyor."),
    ("c4", 12.60, 16.10, "İçinde 5 watt var, 2700 kelvin.", "Akşam ışığı bu, kitap için değil."),
    ("c5", 16.60, 19.70, "Kumiko Serisi.",                 "21 santim. Nereye koyardın?"),
]

def main():
    missing = [s["file"] for s in SHOTS if not (ASSETS / s["file"]).exists()]
    if missing:
        raise SystemExit("missing photos (run fetch_photos.py first): " + ", ".join(missing))

    shots_html = "\n".join(
        f'      <div class="shot" id="s{i}"><img src="assets/{s["file"]}" alt=""'
        f' data-layout-allow-overflow'
        f' style="object-position:{s["pos"]}"/></div>'
        for i, s in enumerate(SHOTS))

    caps_html = "\n".join(
        f'      <div class="cap" id="{c[0]}"><p class="l1">{c[3]}</p>'
        f'<p class="l2">{c[4]}</p></div>' for c in CAPS)

    kb = ",\n          ".join(
        f'{{sel:"#s{i} img", t:{s["t"]}, dur:{s["dur"]}, z0:{s["z0"]}, z1:{s["z1"]}}}'
        for i, s in enumerate(SHOTS))
    capjs = ",\n          ".join(
        f'{{sel:"#{c[0]}", i:{c[1]}, o:{c[2]}}}' for c in CAPS)

    html = f"""<!doctype html>
<html lang="tr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>Kumiko Serisi masa lambası — fotoğraflı kurgu</title>
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
      #mark {{ position: absolute; left: 88px; bottom: 58px; opacity: 0; }}
      #mark .name {{ margin: 0; font-size: 34px; color: {CREAM}; letter-spacing: 0.02em; }}
      #mark .tag {{ margin: 6px 0 0; font-size: 26px; color: {GOLD}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="kumiko" data-start="0"
         data-width="{W}" data-height="{H}" data-duration="20">
{shots_html}

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
            {{ scale: s.z1, duration: s.dur, ease: "none" }}, s.t);
        }});

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

        window.__timelines["kumiko"] = tl;
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

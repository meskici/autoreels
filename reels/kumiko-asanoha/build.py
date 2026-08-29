#!/usr/bin/env python3
"""Generate the Kumiko.Asanoha reel composition.

The asanoha lattice is constructed, not drawn by hand or by a model: a
triangular lattice where every triangle contributes three centroid arms.
That is the hemp-leaf figure the motif is named for, and constructing it is
the only way to guarantee the brand's one non-negotiable - that the motif
comes out right.
"""
import pathlib
from asanoha import (W, H, CREAM, INK, GOLD, RUST, S,
                     lattice_paths, to_path_d, one_star)

# Lattice covering the lamp body generously.
body = to_path_d(lattice_paths(S, 260, 820, 400, 1250))
# A coarser lattice for the cast wall pattern.
wall = to_path_d(lattice_paths(S * 2.6, -700, 1800, -400, 2400))

# One highlighted hemp-leaf star, for the beat that names the motif.
star = one_star(S, 540, 960)

# Y21 x G11 x D11 cm (product spec). Straight-sided square-section column,
# not a tapered shade. 400px = 11cm across the front face, so 1cm = 36.4px;
# the body reads 19.0cm tall and the wood-look base takes the remaining 2.0cm.
# The right-hand panel is the same face foreshortened, which is what makes it
# read as a box rather than a flat screen.
FACE = "M318 440 L718 440 L718 1131 L318 1131 Z"
SIDE = "M718 440 L762 419 L762 1110 L718 1131 Z"
TOP    = "M318 440 L362 419 L762 419 L718 440 Z"
BASE_F = "M274 1131 L722 1131 L722 1199 L274 1199 Z"
BASE_S = "M722 1131 L766 1110 L766 1178 L722 1199 Z"

CAPS = [
    # (id, start, out, line1, line2, phase)
    ("c1",  0.45,  3.70, "Şuna bak.",                        "Altı kollu bir yıldız.",                             "light"),
    ("c2",  4.15,  7.50, "Asanoha diyorlar.",                "Kenevir yaprağından geliyor.",                        "light"),
    ("c3",  8.05, 11.70, "Kumiko’nun en çok işlenen motifi.","Geleneğinde çıtalar çivisiz birleşiyor.", "light"),
    ("c4", 12.60, 16.10, "Işık kafesten geçerken deseni duvara taşıyor.", "Uzaklaştırdıkça gölge büyüyor, yumuşuyor.", "dark"),
    ("c5", 16.60, 19.70, "Kumiko Serisi.",                   "Seninki hangi duvara düşecek?",                       "dark"),
]

cap_html = []
for (cid, _s, _o, l1, l2, phase) in CAPS:
    cls = "cap cap-" + phase
    cap_html.append(
        f'<div class="{cls}" id="{cid}">'
        f'<p class="l1">{l1}</p><p class="l2">{l2}</p>'
        f'</div>')
cap_html = "\n      ".join(cap_html)

HTML = f"""<!doctype html>
<html lang="tr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>Kumiko.Asanoha — motif</title>
    <script src="vendor/gsap.min.js"></script>
    <style>
      @font-face {{
        font-family: "Playfair Display";
        src: url("fonts/PlayfairDisplay-Bold.ttf") format("truetype");
        font-weight: 700;
        font-style: normal;
      }}
      html, body {{ margin: 0; padding: 0; background: {INK}; }}
      #root {{
        position: relative;
        width: {W}px;
        height: {H}px;
        overflow: hidden;
        font-family: "Playfair Display", serif;
        font-weight: 700;
      }}
      .layer {{ position: absolute; inset: 0; }}
      #bg {{ background: {CREAM}; }}
      #wallwrap {{ opacity: 0; }}
      #glow {{
        background: radial-gradient(closest-side,
          rgba(201,162,75,0.95) 0%, rgba(201,162,75,0.45) 42%,
          rgba(201,162,75,0.10) 70%, rgba(201,162,75,0) 100%);
        width: 1500px; height: 1500px;
        left: -232px; top: 42px;
        inset: auto;
        opacity: 0;
      }}
      svg {{ display: block; width: {W}px; height: {H}px; }}

      /* Captions ------------------------------------------------------- */
      .cap {{
        position: absolute;
        left: 0; right: 0;
        bottom: 168px;
        padding: 46px 88px 44px;
        opacity: 0;
      }}
      .cap-light {{ background: rgba(237,230,216,0.95); }}
      .cap-dark  {{ background: rgba(42,37,32,0.92); }}
      .cap p {{
        position: relative;
        margin: 0;
        text-align: left;
        letter-spacing: -0.005em;
      }}
      .cap .l1 {{ font-size: 62px; line-height: 1.15; }}
      .cap .l2 {{ padding-top: 20px; font-size: 40px; line-height: 1.28; }}
      .cap-light .l1 {{ color: {INK}; }}
      .cap-light .l2 {{ color: #4a4038; }}
      .cap-dark  .l1 {{ color: {CREAM}; }}
      .cap-dark  .l2 {{ color: {GOLD}; }}

      #mark {{
        position: absolute;
        left: 88px; bottom: 58px;
        opacity: 0;
      }}
      #mark .name {{
        margin: 0; font-size: 34px; color: {CREAM}; letter-spacing: 0.02em;
      }}
      #mark .tag {{
        margin: 6px 0 0; font-size: 26px; color: {GOLD};
      }}
    </style>
  </head>
  <body>
    <div id="root"
         data-composition-id="asanoha"
         data-start="0"
         data-width="{W}"
         data-height="{H}"
         data-duration="20">

      <div class="layer" id="bg"></div>

      <div id="glow" class="layer"></div>

      <div class="layer" id="wallwrap">
        <svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
          <g id="wallg" fill="none" stroke="{GOLD}" stroke-width="5"
             stroke-linecap="round" opacity="0.5">
            <path d="{wall}"/>
          </g>
        </svg>
      </div>

      <div class="layer" id="lampwrap">
        <svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <clipPath id="faceclip"><path d="{FACE}"/></clipPath>
            <clipPath id="sideclip"><path d="{SIDE}"/></clipPath>
          </defs>

          <g clip-path="url(#sideclip)">
            <rect id="shadeside" x="700" y="400" width="120" height="760" fill="#ded5c3"/>
            <g id="lattside" fill="none" stroke="{INK}" stroke-width="7"
               stroke-linecap="round" opacity="0.55"
               transform="translate(718,0) scale(0.31,1) translate(-718,0)">
              <path d="{body}"/>
            </g>
          </g>

          <g clip-path="url(#faceclip)">
            <rect id="shade" x="300" y="400" width="440" height="760" fill="{CREAM}"/>
            <g id="latt" fill="none" stroke="{INK}" stroke-width="3.2"
               stroke-linecap="round">
              <path d="{body}"/>
            </g>
            <g id="starg" fill="none" stroke="{GOLD}" stroke-width="7"
               stroke-linecap="round" opacity="0">
              <path d="{star}"/>
            </g>
          </g>

          <path id="captop" d="{TOP}" fill="#cfc5b1" stroke="{INK}"
                stroke-width="5" stroke-linejoin="round"/>

          <path id="outline" d="{FACE}" fill="none" stroke="{INK}"
                stroke-width="5" stroke-linejoin="round"/>
          <path id="outlineside" d="{SIDE}" fill="none" stroke="{INK}"
                stroke-width="5" stroke-linejoin="round"/>

          <g id="base" opacity="0">
            <path id="basefront" d="{BASE_F}" fill="#8a6a45"/>
            <path id="baseside"  d="{BASE_S}" fill="#6b5134"/>
          </g>
        </svg>
      </div>

      {cap_html}

      <div id="mark">
        <p class="name">Kapya.Craft</p>
        <p class="tag">Işık, katman katman.</p>
      </div>
    </div>

    <script>
      function build() {{
        const tl = gsap.timeline({{ paused: true }});

        // --- the pull-back: macro lattice resolves into the whole lamp ----
        tl.fromTo("#lampwrap",
          {{ scale: 5.6, xPercent: -2, yPercent: 3 }},
          {{ scale: 4.55, xPercent: 1, yPercent: -1, duration: 4.0, ease: "none" }}, 0);
        tl.to("#lampwrap",
          {{ scale: 3.35, xPercent: 0, yPercent: 0, duration: 3.8, ease: "none" }}, 4.0);
        tl.to("#lampwrap",
          {{ scale: 1.0, duration: 4.2, ease: "power2.inOut" }}, 7.8);
        tl.to("#lampwrap",
          {{ scale: 1.03, duration: 8.0, ease: "sine.inOut" }}, 12.0);

        // --- naming the motif: one hemp leaf picked out in gold ----------
        tl.to("#starg", {{ opacity: 1, duration: 0.7, ease: "power2.out" }}, 4.3);
        tl.to("#starg", {{ opacity: 0, duration: 0.8, ease: "power2.in" }}, 7.3);

        // --- the lamp arrives -------------------------------------------
        tl.fromTo("#base", {{ opacity: 0, y: 26 }},
          {{ opacity: 1, y: 0, duration: 0.9, ease: "power3.out" }}, 10.6);

        // --- lights off in the room, light on in the lamp ----------------
        tl.to("#bg", {{ backgroundColor: "{INK}", duration: 0.65, ease: "power2.in" }}, 11.55);
        tl.to("#shade", {{ attr: {{ fill: "#3a2f1f" }}, duration: 0.65, ease: "power2.in" }}, 11.55);
        tl.to("#shadeside", {{ attr: {{ fill: "#241c12" }}, duration: 0.65, ease: "power2.in" }}, 11.55);
        tl.to("#captop", {{ attr: {{ fill: "#2b2318", stroke: "#9a7a38" }}, duration: 0.65, ease: "power2.in" }}, 11.55);
        tl.to("#latt", {{ attr: {{ stroke: "{GOLD}" }}, duration: 0.7, ease: "power2.out" }}, 11.75);
        tl.to("#lattside", {{ attr: {{ stroke: "#9a7a38" }}, duration: 0.7, ease: "power2.out" }}, 11.75);
        tl.to("#outline", {{ attr: {{ stroke: "{GOLD}" }}, duration: 0.7, ease: "power2.out" }}, 11.75);
        tl.to("#outlineside", {{ attr: {{ stroke: "#9a7a38" }}, duration: 0.7, ease: "power2.out" }}, 11.75);
        tl.to("#basefront", {{ attr: {{ fill: "#4a3922" }}, duration: 0.65 }}, 11.55);
        tl.to("#baseside", {{ attr: {{ fill: "#3a2c1a" }}, duration: 0.65 }}, 11.55);
        tl.to("#glow", {{ opacity: 0.72, duration: 1.5, ease: "power2.out" }}, 11.85);
        tl.to("#glow", {{ opacity: 0.68, duration: 2.2, ease: "sine.inOut",
                          repeat: 2, yoyo: true }}, 14.0);

        // --- the pattern the light throws: it grows and it softens -------
        tl.fromTo("#wallwrap",
          {{ opacity: 0, scale: 1.0, filter: "blur(2px)" }},
          {{ opacity: 1, scale: 1.0, filter: "blur(2px)", duration: 1.0, ease: "power2.out" }}, 12.35);
        tl.to("#wallwrap",
          {{ scale: 1.72, filter: "blur(5px)", duration: 5.2, ease: "power1.inOut" }}, 13.6);
        tl.to("#wallg",
          {{ attr: {{ opacity: 0.30 }}, duration: 5.2, ease: "power1.inOut" }}, 13.6);

        // --- captions ---------------------------------------------------
        const caps = {[[c[0], c[1], c[2]] for c in CAPS]!r};
        caps.forEach(function (c) {{
          const sel = "#" + c[0];
          tl.fromTo(sel, {{ opacity: 0, y: 26 }},
            {{ opacity: 1, y: 0, duration: 0.55, ease: "power3.out" }}, c[1]);
          tl.to(sel, {{ opacity: 0, y: -18, duration: 0.45, ease: "power2.in" }}, c[2]);
        }});

        tl.fromTo("#mark", {{ opacity: 0, y: 18 }},
          {{ opacity: 1, y: 0, duration: 0.7, ease: "power3.out" }}, 17.3);

        window.__timelines["asanoha"] = tl;
      }}

      if (document.fonts && document.fonts.ready) {{
        document.fonts.ready.then(build);
      }} else {{
        build();
      }}
    </script>
  </body>
</html>
"""

out = pathlib.Path(__file__).parent / "index.html"
out.write_text(HTML, encoding="utf-8")
print("wrote", out, len(HTML), "bytes")

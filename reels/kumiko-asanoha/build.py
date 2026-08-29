#!/usr/bin/env python3
"""Generate the Kumiko.Asanoha reel composition.

The asanoha lattice is constructed, not drawn by hand or by a model: a
triangular lattice where every triangle contributes three centroid arms.
That is the hemp-leaf figure the motif is named for, and constructing it is
the only way to guarantee the brand's one non-negotiable - that the motif
comes out right.
"""
import math, pathlib

W, H = 1080, 1920
CREAM, INK, GOLD, RUST = "#ede6d8", "#2a2520", "#c9a24b", "#a53324"
S = 56.0                                   # lattice edge, viewBox units

def lattice_paths(side, x0, x1, y0, y1):
    """Asanoha over a rectangle: lattice edges + centroid arms per triangle."""
    def pt(q, r):
        return (side * (q + r / 2.0), side * math.sqrt(3) / 2.0 * r)
    NB = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
    h = side * math.sqrt(3) / 2.0
    rlo, rhi = int(y0 / h) - 2, int(y1 / h) + 3
    seen, out = set(), []
    def add(p, q):
        k = (round(p[0], 2), round(p[1], 2), round(q[0], 2), round(q[1], 2))
        if (k[2], k[3], k[0], k[1]) in seen or k in seen:
            return
        seen.add(k)
        out.append(k)
    for r in range(rlo, rhi):
        qlo = int((x0 - side * r / 2.0) / side) - 2
        qhi = int((x1 - side * r / 2.0) / side) + 3
        for q in range(qlo, qhi):
            C = pt(q, r)
            for (dq, dr) in NB[:3]:
                add(C, pt(q + dq, r + dr))
            for (a, b) in ((NB[0], NB[1]), (NB[1], NB[2])):
                A, B = pt(q + a[0], r + a[1]), pt(q + b[0], r + b[1])
                G = ((C[0] + A[0] + B[0]) / 3, (C[1] + A[1] + B[1]) / 3)
                add(C, G); add(A, G); add(B, G)
    return out

def to_path_d(segs):
    return " ".join(f"M{x1} {y1}L{x2} {y2}" for (x1, y1, x2, y2) in segs)

# Lattice covering the lamp body generously.
body = to_path_d(lattice_paths(S, 280, 800, 420, 1240))
# A coarser lattice for the cast wall pattern.
wall = to_path_d(lattice_paths(S * 2.6, -700, 1800, -400, 2400))

# One highlighted hemp-leaf star, for the beat that names the motif.
def one_star(side, cx, cy):
    NB = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
    def pt(q, r):
        return (cx + side * (q + r / 2.0), cy + side * math.sqrt(3) / 2.0 * r)
    segs = []
    C = pt(0, 0)
    for k in range(6):
        a, b = NB[k], NB[(k + 1) % 6]
        A, B = pt(*a), pt(*b)
        G = ((C[0] + A[0] + B[0]) / 3, (C[1] + A[1] + B[1]) / 3)
        segs += [(C[0], C[1], G[0], G[1]), (A[0], A[1], G[0], G[1]),
                 (B[0], B[1], G[0], G[1]), (C[0], C[1], A[0], A[1])]
    return to_path_d(segs)

star = one_star(S, 540, 960)

LAMP = ("M350 1182 L390 522 Q392 480 434 480 L646 480 Q688 480 690 522 "
        "L730 1182 Z")

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
        left: -210px; top: 220px;
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
            <clipPath id="lampclip"><path d="{LAMP}"/></clipPath>
          </defs>
          <g clip-path="url(#lampclip)">
            <rect id="shade" x="280" y="420" width="560" height="840" fill="{CREAM}"/>
            <g id="latt" fill="none" stroke="{INK}" stroke-width="3.2"
               stroke-linecap="round">
              <path d="{body}"/>
            </g>
            <g id="starg" fill="none" stroke="{GOLD}" stroke-width="7"
               stroke-linecap="round" opacity="0">
              <path d="{star}"/>
            </g>
          </g>
          <path id="outline" d="{LAMP}" fill="none" stroke="{INK}"
                stroke-width="6" stroke-linejoin="round"/>
          <g id="base" opacity="0">
            <rect x="418" y="1182" width="244" height="46" rx="7" fill="{INK}"/>
            <rect x="386" y="1228" width="308" height="18" rx="9" fill="{INK}"/>
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
        tl.to("#latt", {{ attr: {{ stroke: "{GOLD}" }}, duration: 0.7, ease: "power2.out" }}, 11.75);
        tl.to("#outline", {{ attr: {{ stroke: "{GOLD}" }}, duration: 0.7, ease: "power2.out" }}, 11.75);
        tl.to("#base rect", {{ attr: {{ fill: "#171310" }}, duration: 0.65 }}, 11.55);
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

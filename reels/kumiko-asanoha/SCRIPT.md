# Kumiko Serisi masa lambası — 20s, fotoğraflı kurgu

## The source problem, first

The listing is titled **Kumiko.Asanoha** and its description explains asanoha:
*"kenevir yaprağından çıkan altı kollu yıldız."* The six photographs attached
to that listing show no six-armed star. The panel is a **square** grid
carrying a fan across the top, a nested-square figure down one column, and a
diamond lattice through the field — and the cells are backed by a white
diffuser.

Asanoha is a six-armed star on a triangular grid. This is not that.

So this cut does not use the prose description as a source. Every line traces
to one of two things that can be checked: the **structured spec** on the
listing, or the **photographs**. The motif is never named, because the name on
the listing is contradicted by the object.

**This needs fixing on the store, not here.** Either the title and description
belong to a different lamp, or this lamp is mis-named.

## The lines

| Beat | In | Line | Traces to |
|---|---|---|---|
| 1 | 0.45s | **Şuna bak.** / Tek bir desen değil. | the photographs — several distinct figures on one face |
| 2 | 4.15s | **Üstte yelpaze, ortada baklava.** / Hepsi aynı yüzde. | the photographs — fan along the top band, diamond lattice through the field |
| 3 | 8.05s | **Kumiko geleneğinde çıtalar kareyi dolduruyor.** / Desen oradan çıkıyor. | kept in the past tense of the tradition, as the profile requires; makes no claim about how this object is made |
| 4 | 12.60s | **İçinde 5 watt var, 2700 kelvin.** / Akşam ışığı bu, kitap için değil. | spec: *"5W E27 LED, 2700K sıcak beyaz"* |
| 5 | 16.60s | **Kumiko Serisi.** / 21 santim. Nereye koyardın? | spec: *"Y21 × G11 × D11 cm"*; tags |

Close card: Kapya.Craft / Işık, katman katman.

## What was cut, and why

**The motif name.** The old copy opened *"Altı kollu bir yıldız / Asanoha
diyorlar"* over a lamp with neither. The profile calls a wrong motif the one
thing this brand cannot ship.

**The wall pattern.** The old beat 4 said the light carries the pattern to the
wall. The cells are backed by a diffuser, which spreads light rather than
throwing a figure, and no photograph shows a pattern cast on anything. The
profile already makes this call for another product — *"Plise diffuses light
rather than throwing a pattern. Never write wall-pattern copy for it"* — and
the same evidence applies here.

**The drawn lamp, and the constructed asanoha lattice with it.** Both existed
only because the Shopify CDN is unreachable from some environments. The runner
reaches it, so the photographs are used instead — and keeping a wrong-motif
renderer beside the right one would only invite the mistake again. Recoverable
from git history if a genuine asanoha product ever needs it.

## Voiceover

Not synthesised. Kokoro has no Turkish and no ElevenLabs key is set, but the
profile also says the brand's real voice is Mert's own: *"One person talking
out loud, in Turkish, to one other person."* The five lines are timed to be
read over the cut as it stands.

## Caption and hashtags

> Bir yüzde birden fazla desen var: üstte yelpaze, ortada baklava, kenarda
> kare içinde kare. Kumiko geleneğinde ince çıtalar kareyi böyle dolduruyor.
> İçinde 5 watt, 2700 kelvin — akşam ışığı, kitap okumak için değil. 21 santim,
> komodine oturuyor.
>
> Profildeki linkten inceleyebilirsin.

`#kapyacraft #dekoratifaydinlatma #masalambasi #elyapimi #tasarimlamba`

## Checked against the brand profile

- No banned word, no superlative, no discount or urgency framing; price never mentioned.
- Opens on what the viewer can see, not on the product name.
- Present continuous, not the written aorist. One particle (*bak*).
- One question, at the close.
- No three-item list — the caption's three figures are prose, the on-screen line names two.
- Never claims the object is carved, joined or worked from wood; the body is PETG + PLA.
- The craft reference stays about the tradition and makes no claim about this lamp.

## Rendering

`.github/workflows/hyperframes-reel.yml` on a GitHub runner, which can reach
the CDN. `fetch_photos.py` pulls the frames, `build_photos.py` writes
`index.html`, then check and render. The MP4 and a contact sheet land in the
run's artifacts, and the contact sheet is committed to `review/`.

The 6000×4000 originals crop hard to 9:16. Each shot's `object-position` is a
named field in `SHOTS` — one value to change if a frame sits wrong. The centre
crops currently hold the subject and needed no adjustment.

# autoreels

Product in, vertical Reel out. A Creatify-style short-video pipeline for Shopify
stores. The script follows your brand's rules, the visuals are your own product
photos, and every intermediate is a file you can open and edit.

```
autoreels make kumiko-asanoha --variants 3
```

Three 1080×1920 MP4s. Each gets a different hook, burned-in word-by-word
captions, Ken Burns motion over your photos, narration, a caption and hashtags.

## Why this and not Creatify

Creatify and Holo take a product URL and hand you a video. So does this. They
differ in what happens in between.

| | Creatify / Holo | autoreels |
|---|---|---|
| Script | their house voice | written to a brand profile you own, in your language |
| Facts | scraped, sometimes invented | only what your product description says |
| Intermediates | none, just an MP4 | product / script / storyboard JSON, editable, re-runnable |
| Cost per video | per-credit | free, or cents of TTS |
| Runs offline | no | yes, keyless, with the template scriptwriter |

## Run it without installing anything

`.github/workflows/reels.yml` renders on GitHub's runners. Open Actions, pick
**Make reels**, hit *Run workflow*, choose a product, a format and a variant
count. The MP4s land in the run's **Artifacts**, alongside a contact sheet and
each video's length.

The runner installs FFmpeg, reaches the Shopify CDN and every AI provider, and
runs the tests before it renders. You install nothing.

Set no secrets and you still get real videos: template scripts, silent audio,
Ken Burns over your live product photos. Each secret below upgrades one stage.
Add them under *Settings → Secrets and variables → Actions*.

| Secret | Upgrades |
|---|---|
| `ANTHROPIC_API_KEY` | scripts written to the brand rules |
| `ELEVENLABS_API_KEY` | Turkish narration over the silent cut |
| `FAL_API_KEY` or `RUNWAY_API_KEY` | unlocks the `animate` option |
| `SHOPIFY_ADMIN_TOKEN` | the *live_shopify* toggle, which bypasses the shipped catalog |

GitHub shows the *Run workflow* button only once the workflow file sits on the
repository's default branch. Merge this branch there and the button appears.

## Install

```bash
git clone <this repo> && cd autoreels
pip install -e .          # or just run `python3 -m autoreels`
```

No Python dependencies. FFmpeg is the one requirement, and the render stage is
the only thing that needs it.

```bash
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Debian/Ubuntu
winget install Gyan.FFmpeg   # Windows
```

Check what you have:

```bash
autoreels doctor
```

## The five stages

Each writes JSON into `runs/<handle>-<timestamp>/`, so you can inspect what the
machine decided, fix it by hand, and re-run from there.

| | Stage | Output | Needs |
|---|---|---|---|
| 1 | **ingest** | `product.json` | Shopify Admin token, or `--product-json` |
| 2 | **script** | `script-a.json` | `ANTHROPIC_API_KEY` (falls back to templates) |
| 3 | **voiceover** | `audio-a/beat*.mp3` | ElevenLabs or OpenAI key (falls back to silence) |
| 4 | **storyboard** | `storyboard-a.json` | nothing |
| 4b | **animate** *(opt-in)* | `animated-a/shot*.mp4` | Runway or fal key, `--animate` |
| 5 | **render** | `<handle>-a.mp4` | FFmpeg |

Everything has a keyless fallback, so a fresh clone with only FFmpeg installed
produces a real video on the first run.

## Feeding it products

**With an Admin API token** (`.env`):

```
SHOPIFY_STORE=yourstore.myshopify.com
SHOPIFY_ADMIN_TOKEN=shpat_xxx
```

```bash
autoreels make kumiko-asanoha
```

**From the shipped catalog.** `examples/catalog/` holds all 15 Kapya.Craft
products pulled live from Shopify, photos and alt text included, ready to run:

```bash
autoreels make --product-json examples/catalog/solaris.json --variants 3
```

**Without one.** Save the product JSON and point at it. This is how you use it
alongside the Shopify MCP in Claude, or with your own photos:

```bash
autoreels make --product-json examples/kumiko-asanoha.json
```

Image URLs without a scheme are read from disk, so you can drop your own phone
shots into the list:

```json
{"images": [{"url": "shots/lamp-dark.jpg", "altText": "lamp off, room lit"}]}
```

## Animating the stills

By default a shot is a Ken Burns move over a real photo. With a key you can
send selected shots to an image-to-video model instead. The model animates
**your photo**. Nothing asks it to invent a product.

```bash
autoreels make solaris --animate hook      # just the opening shot
autoreels make solaris --animate 0,3       # specific shots
autoreels make solaris --animate all       # everything, priciest
```

Default is `none`. These services bill per clip, so nothing is sent unless you
ask. `--animate hook` is the sensible setting: the first two seconds decide
whether the rest gets watched.

Set one key, `RUNWAY_API_KEY` or `FAL_API_KEY` (fal hosts Kling), and
`AUTOREELS_VIDEO=auto` picks it up. Model ids on both services change often, so
the endpoint, model and aspect ratio are all environment variables. A rename
becomes a `.env` edit.

**Fine repeating geometry is the failure case.** These models redraw the frame.
A lattice or a pleat comes back wrong in ways a buyer will notice, and for a
craft brand that beats having no animation. A brand profile names the tags to
avoid:

```json
"animation": {
  "avoid_tags": ["Kumiko Serisi"],
  "avoid_reason": "Fine repeating lattice. The motif comes back wrong."
}
```

autoreels warns and continues. You make the call. Any shot that fails or times
out keeps its Ken Burns move without stopping the run, so a partial failure
still produces a finished video.

## Brand profiles

A brand profile is the difference between a generic slideshow and something
that sounds like you. It carries the language, the voice, the copy rules, the
banned words, and the video formats the brand actually shoots.

Two ship: `kapya` (Kapya.Craft, Turkish, five lamp formats) and `generic`.
Write your own by copying `autoreels/brand/generic.json` and passing the path:

```bash
autoreels make my-product --brand ./brands/mybrand.json
autoreels formats --brand ./brands/mybrand.json
```

The profile's `formats` are the shot templates. Each declares how long it runs,
how many beats, whether a narrator speaks, and what photos it *needs*. When your
photo set cannot support the format you picked, autoreels says so before it
renders rather than handing you something weak.

## Common runs

```bash
# three hooks to A/B against each other
autoreels make kumiko-asanoha --variants 3

# a specific format, with a music bed
autoreels make kumiko-asanoha --format lights_off --music beds/ambient.mp3

# script only: read it, edit script-a.json, then render
autoreels script kumiko-asanoha
autoreels make kumiko-asanoha --script-json runs/<run>/script-a.json

# no API key? write the script in a chat window and paste the answer in
autoreels make kumiko-asanoha --script-json my-scripts.json

# re-render one storyboard after hand-editing its timings
autoreels render runs/<run>/storyboard-a.json
```

## Editing the machine's work

The whole point of the JSON intermediates. `script-a.json` is beats:

```json
{"role": "hook", "voiceover": "Asanoha, kenevir yaprağından çıkan altı kollu yıldız.",
 "on_screen": "Altı kollu yıldız", "image_index": 4, "duration": 2.8, "motion": "zoom_in"}
```

Change the words, swap `image_index` to a better photo, retime it, then re-run
with `--script-json`. Nothing regenerates behind your back.

`--script-json` takes either shape: a `script-a.json` this pipeline saved, or
raw model output with no `variant` or `language` field, which is what you get
by pasting the scriptwriting prompt into any chat window and saving the reply.
Indices, durations and motions are clamped on the way in, so a model that
returns `"duration": 99` or `"image_index": 41` can't produce a broken render.

`storyboard-a.json` is one level down: resolved file paths, absolute timings,
and the on-screen window for every caption word. Edit it and use
`autoreels render` to skip straight to FFmpeg.

## Voiceover

`AUTOREELS_TTS=auto` picks ElevenLabs if a key is present, then OpenAI, then
silence. Several formats are written silent by design, and the captions carry
them. Each beat retimes itself to the length the narration came out at, so
nothing gets clipped.

## Tests

```bash
python3 -m unittest discover tests -v
```

29 tests, stdlib only. The render test is skipped when FFmpeg is absent.

## What it does not do

- It does not post to Instagram or TikTok. Export and upload.
- It does not generate video from text. Ken Burns over your own photos is the
  deliberate choice here: real footage of the real product beats generated
  footage of an imagined one.
- It does not source music. Pass your own licensed bed with `--music`.
- It does not invent product facts. If your description doesn't say it, it
  won't reach the screen.

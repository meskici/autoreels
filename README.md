# autoreels

Product in, vertical Reel out. A Creatify-style short-video pipeline for Shopify
stores — but the script is written to *your* brand's rules, the visuals are your
real product photos, and every intermediate is a file you can open and edit.

```
autoreels make kumiko-asanoha --variants 3
```

→ three 1080×1920 MP4s, each with a different hook, burned-in word-by-word
captions, Ken Burns motion on your actual photos, narration, caption text and
hashtags.

## Why this and not Creatify

Creatify and Holo take a product URL and hand you a video. So does this. The
difference is what happens in between:

| | Creatify / Holo | autoreels |
|---|---|---|
| Script | their house voice | written to a brand profile you own, in your language |
| Facts | scraped, sometimes invented | only what your product description says |
| Intermediates | none — you get an MP4 | product / script / storyboard JSON, editable, re-runnable |
| Cost per video | per-credit | free, or cents of TTS |
| Runs offline | no | yes, keyless, with the template scriptwriter |

## Install

```bash
git clone <this repo> && cd autoreels
pip install -e .          # or just run `python3 -m autoreels`
```

No Python dependencies. FFmpeg is the one requirement, and only for the render
stage:

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
| 4 | **storyboard** | `storyboard-a.json` | — |
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

**Without one** — save the product JSON and point at it. This is how you use it
alongside the Shopify MCP in Claude, or with your own photos:

```bash
autoreels make --product-json examples/kumiko-asanoha.json
```

Image URLs without a scheme are read from disk, so you can drop your own phone
shots into the list:

```json
{"images": [{"url": "shots/lamp-dark.jpg", "altText": "lamp off, room lit"}]}
```

## Brand profiles

A brand profile is the difference between a generic slideshow and something
that sounds like you. It carries the language, the voice, the copy rules, the
banned words, and the video formats the brand actually shoots.

Two ship: `kapya` (Kapya.Craft — Turkish, five lamp formats) and `generic`.
Write your own by copying `autoreels/brand/generic.json` and passing the path:

```bash
autoreels make my-product --brand ./brands/mybrand.json
autoreels formats --brand ./brands/mybrand.json
```

The profile's `formats` are the shot templates. Each declares how long it runs,
how many beats, whether it is narrated, and — importantly — what photos it
*needs*. autoreels warns you before rendering when your photo set can't support
the format you picked, instead of quietly producing something weak.

## Common runs

```bash
# three hooks to A/B against each other
autoreels make kumiko-asanoha --variants 3

# a specific format, with a music bed
autoreels make kumiko-asanoha --format lights_off --music beds/ambient.mp3

# script only — read it, edit script-a.json, then render
autoreels script kumiko-asanoha
autoreels make kumiko-asanoha --script-json runs/<run>/script-a.json

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

`storyboard-a.json` is one level down: resolved file paths, absolute timings,
and the on-screen window for every caption word. Edit it and use
`autoreels render` to skip straight to FFmpeg.

## Voiceover

`AUTOREELS_TTS=auto` picks ElevenLabs if a key is present, then OpenAI, then
silence. Silence is not a failure mode — several formats are written to be
silent, and the captions carry them. Beats retime themselves to however long
the narration actually came out, so nothing gets clipped.

## Tests

```bash
python3 -m unittest discover tests -v
```

29 tests, stdlib only. The render test is skipped when FFmpeg is absent.

## What it does not do

- It does not post to Instagram or TikTok. Export and upload.
- It does not generate video from text or animate a still into real motion —
  Ken Burns on your own photos is what it does, deliberately. Real footage of
  the actual product beats generated footage of an imagined one.
- It does not source music. Pass your own licensed bed with `--music`.
- It does not invent product facts. If your description doesn't say it, it
  won't reach the screen.

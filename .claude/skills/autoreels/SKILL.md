---
name: autoreels
description: "Render a finished vertical Reel/TikTok MP4 from a Shopify product using the autoreels pipeline in this repo — pulls the live product and its photos, writes the script to the brand profile, synthesises voiceover, burns captions, and renders 1080x1920 video. Use when the user asks to make, render, or generate a reel, short video, TikTok, or video ad for a product, asks for hook variants to A/B test, or wants to go from a product to a finished video file. Prefer this over hand-written shot lists whenever the user wants an actual video file rather than a plan."
---

# autoreels — product to rendered Reel

This repo is the pipeline. Your job is to run it with the right inputs and to
tell the user what you can see about the result.

Pairs with `kapya-craft-ads` (brand truth, positioning, copy rules) and
`kapya-craft-reels` (manual shot-list method). Reach for this one when the user
wants a **video file**; reach for `kapya-craft-reels` when they want a shot list
to film themselves.

## Step 1 — check the toolchain

```bash
python3 -m autoreels doctor
```

Read the output before doing anything else. It tells you which stages are live:

- `ffmpeg MISS` → no render is possible. Say so immediately, give the install
  line for their platform, and offer `autoreels script` (script + storyboard,
  no video) in the meantime. Do not start a run that will fail at stage 5.
- `claude MISS` → the pipeline's template scriptwriter runs instead, which
  reuses the store's own sentences and reads flat. You are a better
  scriptwriter than that fallback: build the prompt the code would send
  (`python3 -c "...script._build_prompt(...)"`, or read
  `autoreels/stages/script.py`), write the variants yourself against the brand
  rules, save them as a JSON array, and pass `--script-json`. Raw model shape is
  accepted — no `variant` or `language` field needed.
- `voice none` → the video will be silent with captions only. Fine for the
  silent formats, worth flagging for the narrated ones.

## Step 2 — get the product in

The Admin API path needs a token the user may not have. The reliable path is
the Shopify MCP, which you already have:

1. `Shopify:search_products` with `status:active` to find the product.
2. `Shopify:get-product` with its GID for the full image set and description.
3. Write that response to a JSON file and pass it with `--product-json`.

`autoreels` normalises the MCP shape directly — no reformatting needed. Keep the
`images` array as it comes back; the alt text is what the scriptwriter uses to
match beats to the right photo.

Always pull live. Never write a script from a remembered product or price.

## Step 3 — pick the format honestly

```bash
python3 -m autoreels formats --brand kapya
```

Each format declares what photos it *needs*. Check that against what
`get-product` actually returned before choosing. A standard product shoot has
no dark frame, no workshop shots, and no nature reference — so `lights_off`,
`from_nature` and `workshop` usually are not buildable from the store photos
alone.

Default to `motif` for a standard photo set. If the format the user asked for
isn't supported by their photos, say so and name the one extra phone shot that
would unlock it — then either build the supported format or wait, their call.
Do not silently downgrade.

## Step 4 — run it

```bash
python3 -m autoreels make \
  --product-json /path/to/product.json \
  --brand kapya \
  --format motif \
  --variants 3
```

Use `--variants 3` whenever the user is testing hooks; one variant only when
they named a specific angle. Add `--music <path>` only if they supplied a bed —
never source music yourself.

`--animate` sends stills to an image-to-video model. It costs real money per
clip, so never add it on your own initiative — only when the user asks, and
default to `--animate hook` rather than `all` unless they say otherwise. Check
`doctor` for a configured provider first, and repeat the brand's warning if the
product carries an `avoid_tags` tag: for fine repeating geometry the model
redraws the motif and the result is off-brand, which matters more here than a
bit of extra motion.

The command prints each stage, then the full script, caption and hashtags per
variant. Relay the script and the output paths. Do not paste the JSON files.

## Step 5 — check the render before handing it over

The pipeline can succeed and still produce something wrong. Verify:

```bash
ffprobe -v error -show_entries format=duration -show_entries stream=width,height \
  -of default=noprint_wrappers=1 runs/<run>/<handle>-a.mp4
ffmpeg -y -loglevel error -ss 4 -i runs/<run>/<handle>-a.mp4 -frames:v 1 /tmp/frame.png
```

Read the frame. Check that the caption sits inside the frame, that the photo
under it is the one the beat is talking about, and that the product is not
cropped out of shot by the Ken Burns move. On any animated shot, check the
product's geometry against the source photo — if the model redrew a motif,
say so and re-render that shot without animation. If a beat is wrong, edit
`script-a.json` and re-run with `--script-json` rather than regenerating.

Then send the MP4 to the user with `SendUserFile`.

## Fixing rather than regenerating

Every run leaves editable JSON. When the user wants a change, make it at the
lowest level that covers it:

| The user says | Edit | Then run |
|---|---|---|
| "wrong photo on that line" | `image_index` in `script-a.json` | `make --script-json` |
| "hook is weak" | `voiceover` + `on_screen` of beat 0 | `make --script-json` |
| "too fast" | `duration` in `script-a.json` | `make --script-json` |
| "caption timing is off" | `words` in `storyboard-a.json` | `autoreels render` |

Regenerating throws away everything the user already approved. Edit first.

## Honesty checkpoints

- No MCP posts to Instagram or TikTok. The deliverable is a file the user uploads.
- autoreels does not animate stills into real motion or generate footage. It is
  Ken Burns on real photos. Do not describe it as AI video generation.
- Every claim in the script traces to the product description. If the user asks
  for a claim the description doesn't support, say the description doesn't
  support it and ask for the fact.

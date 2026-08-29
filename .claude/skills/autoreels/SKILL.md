---
name: autoreels
description: "Render a finished vertical Reel/TikTok MP4 from a Shopify product using the autoreels pipeline in this repo. It pulls the live product and its photos, writes the script to the brand profile, synthesises voiceover, burns captions, and renders 1080x1920 video. Use when the user asks to make, render, or generate a reel, short video, TikTok, or video ad for a product, asks for hook variants to A/B test, or wants to go from a product to a finished video file. Prefer this over hand-written shot lists whenever the user wants an actual video file rather than a plan."
---

# autoreels: product to rendered Reel

This repo is the pipeline. Your job is to run it with the right inputs and to
tell the user what you can see about the result.

Pairs with `kapya-craft-ads` (brand truth, positioning, copy rules) and
`kapya-craft-reels` (manual shot-list method). Reach for this one when the user
wants a **video file**. Reach for `kapya-craft-reels` when they want a shot list
to film themselves.

## Step 1: check the toolchain

```bash
python3 -m autoreels doctor
```

Read the output before doing anything else. It tells you which stages are live:

- `ffmpeg MISS` means no render is possible. Say so, give the install line for
  their platform, and offer `autoreels script` (script and storyboard, no video)
  in the meantime. Do not start a run that will fail at stage 5.
- `claude MISS` → the pipeline's template scriptwriter runs instead, which
  reuses the store's own sentences and reads flat. You are a better
  scriptwriter than that fallback: build the prompt the code would send
  (`python3 -c "...script._build_prompt(...)"`, or read
  `autoreels/stages/script.py`), write the variants yourself against the brand
  rules, save them as a JSON array, and pass `--script-json`. Raw model shape is
  accepted, so no `variant` or `language` field is needed.
- `voice none` means a silent video carried by captions. Fine for the silent
  formats. Flag it for the narrated ones.

## Step 2: get the product in

The Admin API path needs a token the user may not have. The reliable path is
the Shopify MCP, which you already have:

1. `Shopify:search_products` with `status:active` to find the product.
2. `Shopify:get-product` with its GID for the full image set and description.
3. Write that response to a JSON file and pass it with `--product-json`.

`autoreels` normalises the MCP shape directly, so reformat nothing. Keep the
`images` array as it comes back: the scriptwriter reads the alt text to match
each beat to the right photo.

Always pull live. Never write a script from a remembered product or price.

## Step 3: pick the format honestly

```bash
python3 -m autoreels formats --brand kapya
```

Each format declares what photos it *needs*. Check that against what
`get-product` returned before choosing. A standard product shoot carries no dark
frame, no workshop shots and no nature reference, which rules out `lights_off`,
`from_nature` and `workshop` on store photos alone.

Default to `motif` for a standard photo set. When their photos cannot support
the format they asked for, say so and name the one extra phone shot that would
unlock it. Then build the supported format or wait, whichever they choose.
Never downgrade without telling them.

## Step 3b: show the user the words before you render

The user reads every line before it goes into a video. A false line reached a
finished render once already, so this is not optional and it is not a
formality.

Print the on-screen text and the voiceover for every variant, in a table, and
stop. Do not start the render in the same turn. Ask them to approve, edit a
line, or throw a variant out.

Check each line against the product description yourself first, and say which
lines you are least sure of. A claim you cannot point at a sentence for does
not go in the table; it goes in a question.

## Step 4: run it

```bash
python3 -m autoreels make \
  --product-json /path/to/product.json \
  --brand kapya \
  --format motif \
  --variants 3
```

Use `--variants 3` whenever the user is testing hooks, and one variant when
they named a specific angle. Add `--music <path>` only if they supplied a bed.
Never source music yourself.

`--animate` sends stills to an image-to-video model and costs real money per
clip. Add it only when the user asks, and default to `--animate hook` over `all`
unless they say otherwise. Check `doctor` for a configured provider first. If
the product carries an `avoid_tags` tag, repeat the brand's warning: on fine
repeating geometry the model redraws the motif, and an off-brand motif costs
more than a little extra motion buys.

The command prints each stage, then the script, caption and hashtags per
variant. Relay the script and the output paths. Do not paste the JSON files.

## Step 5: check the render before handing it over

The pipeline can succeed and still produce something wrong. Verify it.

```bash
ffprobe -v error -show_entries format=duration -show_entries stream=width,height \
  -of default=noprint_wrappers=1 runs/<run>/<handle>-a.mp4
ffmpeg -y -loglevel error -ss 4 -i runs/<run>/<handle>-a.mp4 -frames:v 1 /tmp/frame.png
```

Read the frame. Check that the caption sits inside it, that the photo beneath
matches what the beat says, and that the Ken Burns move has not cropped the
product out of shot. On an animated shot, compare the product's geometry against
the source photo. If the model redrew a motif, say so and re-render that shot
without animation. If a beat is wrong, edit
`script-a.json` and re-run with `--script-json` rather than regenerating.

Then send the MP4 to the user with `SendUserFile`.

## Fixing rather than regenerating

Every run leaves editable JSON. Make each change at the lowest level that
covers it.

| The user says | Edit | Then run |
|---|---|---|
| "wrong photo on that line" | `image_index` in `script-a.json` | `make --script-json` |
| "hook is weak" | `voiceover` + `on_screen` of beat 0 | `make --script-json` |
| "too fast" | `duration` in `script-a.json` | `make --script-json` |
| "caption timing is off" | `words` in `storyboard-a.json` | `autoreels render` |

Regenerating throws away everything the user already approved, so edit first.

## Honesty checkpoints

- No MCP posts to Instagram or TikTok. You hand the user a file to upload.
- autoreels does not generate footage. It runs Ken Burns over real photos.
  Never describe it as AI video generation.
- Every claim in the script traces to the product description. When the user
  asks for a claim the description does not support, say so and ask them for
  the fact.

# Running HyperFrames in this container

The HyperFrames skills under `.claude/skills/` are the authoring half. This is
the runtime half: what a container needs before `hyperframes render` writes an
MP4, and the one constraint that trips up every stock example here.

Verified on 2026-08-29 against `hyperframes@0.8.17`: a scaffolded project
rendered 300 frames to a 1080x1920 H.264 MP4 in 20 seconds.

## Setup

```bash
scripts/setup-hyperframes.sh
```

It installs FFmpeg and Chrome Headless Shell, then runs `hyperframes doctor`.
A render needs exactly those two; everything else `doctor` lists is optional:

| Check | Needed for |
|---|---|
| FFmpeg / FFprobe | encoding frames, probing media — **required** |
| Chrome | capturing frames — **required** |
| whisper-cpp | `hyperframes transcribe`, so word-level captions |
| Kokoro / MusicGen | local TTS and music fallbacks |
| Docker | containerized renders only |

`doctor` exits non-zero while an optional check is unmet. Read the rows; do not
read the exit code as "cannot render".

## Every asset must be local

Egress here is policy-filtered, and `cdn.jsdelivr.net` is denied. Headless
Chrome goes through the same proxy as everything else, so a composition that
loads GSAP from a CDN fails at render time:

```
✗ request_failed: Failed to load npm/gsap@3.14.2/dist/gsap.min.js: net::ERR_TUNNEL_CONNECTION_FAILED
✗ page_error: gsap is not defined
```

`hyperframes init` scaffolds exactly that CDN tag, so **a fresh project fails
its first `check` until you vendor the runtime**. npm itself is reachable, so:

```bash
npm install gsap@3.14.2
mkdir -p vendor && cp node_modules/gsap/dist/gsap.min.js vendor/
sed -i 's#https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js#vendor/gsap.min.js#' index.html
```

The same applies to remote fonts, textures and images — the `warm-grain`
example also pulls a paper texture from `transparenttextures.com`, likewise
denied. Replace remote decoration with CSS, or fetch the file through a
reachable host and commit it.

Vendoring is what the HyperFrames determinism rules want anyway: a render
whose assets are frozen on disk produces the same frames every time.

## Workflow

```bash
npx hyperframes init myvideo --example warm-grain --resolution portrait --non-interactive
cd myvideo
# vendor GSAP as above
npm run check     # lint + runtime + layout + contrast
npm run render -- -o out.mp4
```

`check` reports errors, warnings and info separately. Runtime errors are real
failures. Layout overflow and contrast warnings from a stock example usually
mean the example was authored for landscape and you asked for portrait — they
do not block a render, but they do mean the frame is not laid out for the
canvas you chose.

Set `HYPERFRAMES_SKIP_SKILLS=1` for `init` in CI or an agent session, or it
reaches out to GitHub to refresh the skill set on every run.

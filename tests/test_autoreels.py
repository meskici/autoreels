"""Smoke tests. Stdlib unittest so there is nothing to install.

    python3 -m unittest discover tests -v
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoreels import brand, captions, ffmpeg  # noqa: E402
from autoreels.config import Config  # noqa: E402
from autoreels.models import Image, Product, Shot, Storyboard, Word  # noqa: E402
from autoreels.providers import shopify, tts, video  # noqa: E402
from autoreels.stages import animate as animate_stage  # noqa: E402
from autoreels.providers.llm import extract_json  # noqa: E402
from autoreels.stages import script as script_stage  # noqa: E402
from autoreels.stages.storyboard import _lay_out_words  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "examples", "kumiko-asanoha.json")


def sample_product() -> Product:
    return shopify.load_json(FIXTURE)


class TestIngest(unittest.TestCase):
    def test_normalises_admin_shape(self):
        product = sample_product()
        self.assertEqual(product.handle, "kumiko-asanoha")
        self.assertEqual(product.currency, "TRY")
        self.assertEqual(len(product.images), 6)
        self.assertNotIn("<p>", product.description)
        self.assertIn("Asanoha", product.description)

    def test_normalises_search_products_shape(self):
        raw = {"data": {"products": {"edges": [{"node": {
            "title": "Solaris Dekoratif Masa Lambası",
            "description": "Voronoi.",
            "featuredMedia": {"preview": {"image": {"url": "https://cdn/x.jpg"}}},
            "priceRangeV2": {"minVariantPrice": {"amount": "6900.0", "currencyCode": "TRY"}},
        }}]}}}
        product = shopify.normalise(raw, store="kapyacraft.myshopify.com")
        self.assertEqual(product.price, "6900.0")
        self.assertEqual(len(product.images), 1)
        # handle is derived from the title when the source omits it
        self.assertTrue(product.handle.startswith("solaris"))

    def test_deduplicates_images(self):
        raw = {
            "title": "X", "description": "d",
            "featuredMedia": {"preview": {"image": {"url": "https://cdn/a.jpg"}}},
            "media": {"edges": [
                {"node": {"image": {"url": "https://cdn/a.jpg"}}},
                {"node": {"image": {"url": "https://cdn/b.jpg"}}},
            ]},
        }
        self.assertEqual([i.url for i in shopify.normalise(raw).images],
                         ["https://cdn/a.jpg", "https://cdn/b.jpg"])


class TestBrand(unittest.TestCase):
    def test_ships_two_profiles(self):
        self.assertEqual(brand.available(), ["generic", "kapya"])

    def test_default_format_is_first(self):
        profile = brand.load("kapya")
        self.assertEqual(brand.get_format(profile, "auto")["id"], "motif")

    def test_unknown_format_names_the_alternatives(self):
        profile = brand.load("kapya")
        with self.assertRaises(brand.UnknownBrand) as caught:
            brand.get_format(profile, "nope")
        self.assertIn("lights_off", str(caught.exception))

    def test_silent_format_is_marked(self):
        profile = brand.load("kapya")
        self.assertFalse(brand.get_format(profile, "lights_off")["voiceover"])


class TestScript(unittest.TestCase):
    def setUp(self):
        self.product = sample_product()
        self.profile = brand.load("kapya")

    def test_fallback_writes_requested_variants(self):
        fmt = brand.get_format(self.profile, "motif")
        scripts = script_stage.write(self.product, self.profile, fmt, Config(), variants=3)
        self.assertEqual([s.variant for s in scripts], ["a", "b", "c"])
        for item in scripts:
            self.assertEqual(item.beats[0].role, "hook")
            self.assertEqual(item.beats[-1].role, "cta")
            self.assertAlmostEqual(item.duration(), fmt["target_seconds"], delta=1.0)

    def test_fallback_variants_differ(self):
        fmt = brand.get_format(self.profile, "motif")
        a, b = script_stage.write(self.product, self.profile, fmt, Config(), variants=2)
        self.assertNotEqual([x.voiceover for x in a.beats], [x.voiceover for x in b.beats])

    def test_silent_format_produces_no_voiceover(self):
        fmt = brand.get_format(self.profile, "lights_off")
        script = script_stage.write(self.product, self.profile, fmt, Config(), variants=1)[0]
        self.assertTrue(all(beat.voiceover == "" for beat in script.beats))
        self.assertTrue(any(beat.on_screen for beat in script.beats))

    def test_prompt_carries_the_brand_constraints(self):
        fmt = brand.get_format(self.profile, "motif")
        prompt = script_stage._build_prompt(self.product, self.profile, fmt, 2)
        self.assertIn("en iyi", prompt)               # banned words reach the model
        self.assertIn("Asanoha", prompt)              # product facts reach the model
        self.assertIn("[5]", prompt)                  # every photo is offered
        self.assertIn("2 distinct script variant", prompt)

    def test_coerce_clamps_hostile_model_output(self):
        fmt = brand.get_format(self.profile, "motif")
        raw = {"beats": [
            {"role": "narrator", "duration": 99, "image_index": 41, "motion": "barrel_roll"},
            {"role": "cta", "duration": -3, "image_index": 0},
        ]}
        script = script_stage._coerce(raw, fmt, self.profile, self.product, "a")
        self.assertEqual(script.beats[0].role, "body")
        self.assertEqual(script.beats[0].duration, 8.0)
        self.assertLess(script.beats[0].image_index, len(self.product.images))
        self.assertEqual(script.beats[0].motion, "auto")
        self.assertEqual(script.beats[1].duration, 1.5)

    def test_load_accepts_raw_model_output(self):
        """What you get from pasting the model's answer — no variant, no language."""
        fmt = brand.get_format(self.profile, "motif")
        raw = [
            {"fmt": "motif", "beats": [
                {"role": "hook", "voiceover": "Bir.", "on_screen": "Bir", "image_index": 4,
                 "duration": 2.5, "motion": "zoom_in"},
                {"role": "cta", "voiceover": "İki.", "on_screen": "İki", "image_index": 0,
                 "duration": 3.0, "motion": "zoom_out"}],
             "caption": "c", "hashtags": ["kapyacraft"], "notes": "n"},
            {"fmt": "motif", "beats": [
                {"role": "hook", "voiceover": "Üç.", "on_screen": "Üç", "image_index": 1,
                 "duration": 2.5, "motion": "static"}],
             "caption": "c2", "hashtags": [], "notes": ""},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "scripts.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(raw, handle, ensure_ascii=False)
            scripts = script_stage.load(path, self.product, self.profile, fmt)
        self.assertEqual([s.variant for s in scripts], ["a", "b"])
        self.assertEqual(scripts[0].language, "tr")
        self.assertEqual(scripts[1].hashtags, self.profile["hashtag_seeds"][:5])

    def test_load_round_trips_our_own_saved_shape(self):
        fmt = brand.get_format(self.profile, "motif")
        original = script_stage.write(self.product, self.profile, fmt, Config(), variants=1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = original.save(os.path.join(tmp, "script-a.json"))
            reloaded = script_stage.load(path, self.product, self.profile, fmt)[0]
        self.assertEqual(reloaded.to_dict(), original.to_dict())

    def test_load_rejects_a_bare_list_of_strings(self):
        fmt = brand.get_format(self.profile, "motif")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "scripts.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(["not a script"], handle)
            with self.assertRaises(ValueError):
                script_stage.load(path, self.product, self.profile, fmt)

    def test_coerce_rejects_empty_beats(self):
        fmt = brand.get_format(self.profile, "motif")
        with self.assertRaises(ValueError):
            script_stage._coerce({"beats": []}, fmt, self.profile, self.product, "a")


class TestLLMParsing(unittest.TestCase):
    def test_reads_fenced_json(self):
        self.assertEqual(extract_json('here:\n```json\n[{"a":1}]\n```'), [{"a": 1}])

    def test_reads_bare_json_with_chatter(self):
        self.assertEqual(extract_json('Sure! {"a": 2} hope that helps'), {"a": 2})

    def test_raises_when_there_is_no_json(self):
        with self.assertRaises(ValueError):
            extract_json("no json here")


class TestTiming(unittest.TestCase):
    def test_words_fill_exactly_the_beat(self):
        words = _lay_out_words("bir iki üç dört", 5.0, 4.0)
        self.assertEqual(len(words), 4)
        self.assertAlmostEqual(words[0].start, 5.0)
        self.assertAlmostEqual(words[-1].end, 9.0, places=2)

    def test_no_words_for_empty_text(self):
        self.assertEqual(_lay_out_words("", 0.0, 3.0), [])

    def test_longer_words_hold_longer(self):
        words = _lay_out_words("a marangozluğunun", 0.0, 4.0)
        self.assertGreater(words[1].end - words[1].start, words[0].end - words[0].start)


class TestCaptions(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _build(self, text: str) -> str:
        words = _lay_out_words(text, 0.0, 4.0)
        shot = Shot(index=0, image_path="x", start=0.0, duration=4.0,
                    motion="zoom_in", on_screen=text, words=words)
        path = captions.build([shot], os.path.join(self.dir, "c.ass"))
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_one_event_per_word(self):
        body = self._build("bir iki üç")
        self.assertEqual(body.count("Dialogue:"), 3)

    def test_active_word_is_accented(self):
        body = self._build("bir iki")
        self.assertIn(captions.ACCENT, body)

    def test_lines_stay_inside_the_frame(self):
        body = self._build("Asanoha, kumiko marangozluğunun en çok işlenen motifi")
        for line in body.splitlines():
            if not line.startswith("Dialogue:"):
                continue
            visible = line.split(",,")[-1].replace("{\\fad(60,0)}", "")
            for override in ("{\\c&H0064D2FF&}", "{\\c&H00FFFFFF&}"):
                visible = visible.replace(override, "")
            self.assertLessEqual(len(visible), 26, f"caption line too wide: {visible!r}")

    def test_braces_in_copy_do_not_become_ass_overrides(self):
        body = self._build("bir {iki} üç")
        self.assertIn("\\{iki\\}", body)


class TestFFmpegFilters(unittest.TestCase):
    def test_every_motion_produces_a_chain(self):
        for motion in ("zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "static"):
            chain = ffmpeg.kenburns_filter(motion, 90, 1080, 1920, 30)
            self.assertIn("zoompan", chain)
            self.assertIn("s=1080x1920", chain)

    def test_image_is_supersampled_before_zoompan(self):
        chain = ffmpeg.kenburns_filter("zoom_in", 90, 1080, 1920, 30)
        self.assertTrue(chain.startswith("scale=2160:3840"))

    def test_colons_in_paths_are_escaped_for_the_filtergraph(self):
        self.assertIn("\\:", ffmpeg.escape_filter_path("/tmp/a:b/c.ass"))


class TestTTSFallback(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_silence_matches_the_reading_estimate(self):
        text = "bir iki üç dört beş altı"
        speech = tts.speak(text, os.path.join(self.dir, "b"), Config())
        self.assertTrue(speech.silent)
        self.assertTrue(os.path.exists(speech.path))
        self.assertAlmostEqual(speech.duration, tts.estimate_duration(text), places=3)

    def test_empty_text_is_zero_length(self):
        speech = tts.speak("", os.path.join(self.dir, "b"), Config())
        self.assertEqual(speech.duration, 0.0)


class TestBrandIdentity(unittest.TestCase):
    def setUp(self):
        self.identity = brand.load("kapya")["identity"]

    def test_hex_to_ass_reverses_the_byte_order(self):
        self.assertEqual(captions.ass_colour("#c9a24b"), "&H004BA2C9&")
        self.assertEqual(captions.ass_colour("ede6d8"), "&H00D8E6ED&")

    def test_bad_hex_is_rejected(self):
        with self.assertRaises(ValueError):
            captions.ass_colour("#fff")

    def test_caption_font_ships_with_the_repo(self):
        from autoreels.stages.render import FONTS_DIR
        path = os.path.join(FONTS_DIR, self.identity["caption_font_file"])
        self.assertTrue(os.path.exists(path), path)

    def test_caption_font_can_spell_turkish(self):
        """The theme's body font cannot; this is why captions use the heading font."""
        from autoreels.stages.render import FONTS_DIR
        path = os.path.join(FONTS_DIR, self.identity["caption_font_file"])
        with open(path, "rb") as handle:
            blob = handle.read()
        self.assertGreater(len(blob), 50_000)
        self.assertEqual(blob[:4], b"\x00\x01\x00\x00")  # TrueType magic

    def test_brand_colours_reach_the_subtitle_style(self):
        palette = self.identity["caption_colors"]
        shot = Shot(index=0, image_path="x", start=0.0, duration=2.0, motion="zoom_in",
                    on_screen="Adı Seigaiha",
                    words=[Word("Adı", 0.0, 1.0), Word("Seigaiha", 1.0, 2.0)])
        with tempfile.TemporaryDirectory() as tmp:
            path = captions.build([shot], os.path.join(tmp, "c.ass"),
                                  font=self.identity["caption_font"],
                                  text_colour=palette["text"],
                                  outline_colour=palette["outline"],
                                  accent_colour=palette["accent"])
            with open(path, encoding="utf-8") as handle:
                body = handle.read()
        self.assertIn(captions.ass_colour(palette["accent"]), body)
        self.assertIn("Playfair Display", body)


class TestLogoOverlay(unittest.TestCase):
    def test_every_anchor_produces_a_chain(self):
        for pos in ffmpeg.LOGO_ANCHORS:
            chain = ffmpeg.logo_overlay_chain("base", "3:v", "v", canvas_width=1080,
                                              position=pos, width_pct=26, opacity=0.8)
            self.assertEqual(len(chain), 2)
            self.assertIn("overlay=", chain[1])

    def test_opacity_is_clamped(self):
        chain = ffmpeg.logo_overlay_chain("base", "1:v", "v", canvas_width=1080,
                                          position="top-left", width_pct=26, opacity=9.0)
        self.assertIn("aa=1.000", chain[0])

    def test_width_follows_the_canvas(self):
        chain = ffmpeg.logo_overlay_chain("base", "1:v", "v", canvas_width=1080,
                                          position="top-left", width_pct=26, opacity=0.8)
        self.assertIn("scale=280:-1", chain[0])


class TestCuratedCopy(unittest.TestCase):
    """The shipped scripts are the brand's voice; guard them against slop."""

    PATHS = ("impact", "kumiko-seigaiha")

    def setUp(self):
        self.profile = brand.load("kapya")
        self.fmt = brand.get_format(self.profile, "motif")

    def _load(self, name):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        product = shopify.load_json(os.path.join(root, "examples", "catalog", f"{name}.json"))
        return script_stage.load(
            os.path.join(root, "examples", "scripts", f"{name}.json"),
            product, self.profile, self.fmt)

    def test_at_most_one_question_per_set(self):
        for name in self.PATHS:
            asked = sum(1 for v in self._load(name)
                        for b in v.beats if b.voiceover.strip().endswith("?"))
            self.assertLessEqual(asked, 1, f"{name}: {asked} closing questions")

    def test_hooks_are_all_different(self):
        for name in self.PATHS:
            hooks = {v.beats[0].voiceover for v in self._load(name)}
            self.assertEqual(len(hooks), 3, f"{name}: {hooks}")

    def test_no_encyclopedia_register(self):
        for name in self.PATHS:
            for v in self._load(name):
                body = " ".join(b.voiceover for b in v.beats).lower()
                for phrase in ("anlamına geliyor", "yer almakta", "olarak bilinir"):
                    self.assertNotIn(phrase, body, f"{name}/{v.variant}")

    def test_no_banned_words(self):
        banned = self.profile["banned_words"]
        for name in self.PATHS:
            for v in self._load(name):
                body = " ".join(b.voiceover + b.on_screen for b in v.beats).lower()
                hits = [w for w in banned if w in body]
                self.assertEqual(hits, [], f"{name}/{v.variant}: {hits}")

    def test_sentence_lengths_vary_within_a_variant(self):
        for name in self.PATHS:
            for v in self._load(name):
                lengths = [len(b.voiceover.split()) for b in v.beats]
                self.assertGreater(max(lengths) - min(lengths), 1,
                                   f"{name}/{v.variant} is metronomic: {lengths}")


class TestMaterialTruth(unittest.TestCase):
    """Kapya.Craft lamps are printed, not woodworked, and the brand does not
    sell the method. A shipped script must not imply either."""

    PATHS = ("impact", "kumiko-seigaiha")

    # Verbs and nouns that describe someone working timber, stone or a printer.
    CRAFT_CLAIM = re.compile(
        r"marangoz|çıta|çivi|oyuyor|oydu|yontuyor|yontul|"
        r"rendel|zımparal|tornal|dokuyor|dokunmuş",
        re.I)
    METHOD_CLAIM = re.compile(r"\bbas[ıi]yoruz\b|\b3d\b|üç boyutlu|filament|petg|pla\b", re.I)

    def setUp(self):
        self.profile = brand.load("kapya")
        self.fmt = brand.get_format(self.profile, "motif")

    def _spoken(self, name):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        product = shopify.load_json(os.path.join(root, "examples", "catalog", f"{name}.json"))
        scripts = script_stage.load(
            os.path.join(root, "examples", "scripts", f"{name}.json"),
            product, self.profile, self.fmt)
        for v in scripts:
            text = " ".join(b.voiceover + " " + b.on_screen for b in v.beats)
            yield v.variant, text + " " + v.caption

    def test_no_woodworking_claims(self):
        for name in self.PATHS:
            for variant, text in self._spoken(name):
                hit = self.CRAFT_CLAIM.search(text)
                self.assertIsNone(
                    hit, f"{name}/{variant} implies handwork: {hit.group(0) if hit else ''!r}")

    def test_production_method_is_never_named(self):
        for name in self.PATHS:
            for variant, text in self._spoken(name):
                hit = self.METHOD_CLAIM.search(text)
                self.assertIsNone(
                    hit, f"{name}/{variant} names the method: {hit.group(0) if hit else ''!r}")

    def test_the_rules_reach_the_scriptwriting_prompt(self):
        product = shopify.load_json(FIXTURE)
        prompt = script_stage._build_prompt(product, self.profile, self.fmt, 3)
        self.assertIn("Never claim", prompt)
        self.assertIn("carved, joined", prompt)


class TestAnimateSelection(unittest.TestCase):
    def test_spec_forms(self):
        self.assertEqual(animate_stage.select("none", 5), set())
        self.assertEqual(animate_stage.select("", 5), set())
        self.assertEqual(animate_stage.select("hook", 5), {0})
        self.assertEqual(animate_stage.select("all", 3), {0, 1, 2})
        self.assertEqual(animate_stage.select("0,2", 5), {0, 2})

    def test_out_of_range_indices_are_dropped(self):
        self.assertEqual(animate_stage.select("0,9", 3), {0})

    def test_hook_on_an_empty_board_selects_nothing(self):
        self.assertEqual(animate_stage.select("hook", 0), set())

    def test_garbage_spec_is_rejected_with_the_valid_forms(self):
        with self.assertRaises(ValueError) as caught:
            animate_stage.select("sometimes", 5)
        self.assertIn("hook", str(caught.exception))


class TestAnimateGuards(unittest.TestCase):
    def setUp(self):
        self.profile = brand.load("kapya")

    def test_lattice_products_are_flagged(self):
        kumiko = shopify.load_json(FIXTURE)
        self.assertIn("Kumiko Serisi", kumiko.tags)
        self.assertIn("lattice", animate_stage.risky(kumiko, self.profile))

    def test_other_products_are_not_flagged(self):
        impact = shopify.load_json(
            os.path.join(os.path.dirname(FIXTURE), "catalog", "impact.json"))
        self.assertEqual(animate_stage.risky(impact, self.profile), "")

    def test_prompt_forbids_redrawing_the_product(self):
        product = shopify.load_json(FIXTURE)
        prompt = animate_stage.build_prompt("Altı kollu yıldız", "zoom_in", product, self.profile)
        self.assertIn("keeps its exact shape", prompt)
        self.assertIn("Do not redraw", prompt)
        self.assertIn("push in", prompt)

    def test_requesting_animation_without_a_provider_warns_instead_of_failing(self):
        product = shopify.load_json(FIXTURE)
        board = Storyboard(variant="a", shots=[
            Shot(index=0, image_path="x.jpg", start=0.0, duration=3.0,
                 motion="zoom_in", on_screen="hi")])
        warnings = animate_stage.run(board, product, self.profile, Config(),
                                     tempfile.gettempdir(), "hook", say=lambda *a: None)
        self.assertEqual(len(warnings), 1)
        self.assertIn("no video provider", warnings[0])
        self.assertEqual(board.shots[0].source_video, "")


class TestVideoProvider(unittest.TestCase):
    def test_clip_length_covers_the_beat(self):
        self.assertEqual(video.pick_length(2.5), 5)
        self.assertEqual(video.pick_length(5.0), 5)
        self.assertEqual(video.pick_length(5.1), 10)

    def test_public_urls_pass_through_unchanged(self):
        self.assertEqual(video._image_reference("https://cdn/x.jpg"), "https://cdn/x.jpg")

    def test_local_files_become_data_uris(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.jpg")
            with open(path, "wb") as handle:
                handle.write(b"\xff\xd8\xff")
            self.assertTrue(video._image_reference(path).startswith("data:image/jpeg;base64,"))

    def test_missing_local_file_is_reported(self):
        with self.assertRaises(video.VideoUnavailable):
            video._image_reference("/nope/missing.jpg")

    def test_no_key_means_no_provider(self):
        self.assertEqual(Config().resolved_video(), "none")
        with self.assertRaises(video.VideoUnavailable):
            video.animate("https://cdn/x.jpg", "p", 3.0, "/tmp/x", Config())


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class TestConformClip(unittest.TestCase):
    """Provider clips arrive at the provider's resolution, fps and length."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.source = os.path.join(self.dir, "provider.mp4")
        ffmpeg.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "testsrc2=size=1280x720:duration=5:rate=24",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", self.source])

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _conform(self, duration: float) -> str:
        dest = os.path.join(self.dir, f"out{duration}.mp4")
        return ffmpeg.conform_clip("ffmpeg", self.source, dest, duration=duration,
                                   width=1080, height=1920, fps=30)

    def test_trims_a_long_clip_to_the_beat(self):
        self.assertAlmostEqual(tts.probe_duration(self._conform(3.2)), 3.2, delta=0.1)

    def test_holds_the_last_frame_when_the_clip_is_short(self):
        self.assertAlmostEqual(tts.probe_duration(self._conform(7.5)), 7.5, delta=0.1)


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class TestRender(unittest.TestCase):
    """End-to-end: product JSON in, playable vertical MP4 out."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_pipeline_produces_a_vertical_video(self):
        from autoreels.pipeline import run

        images = os.path.join(self.dir, "img")
        os.makedirs(images)
        for index in range(3):
            ffmpeg.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"color=c=0x20304{index}:size=1200x1500:d=1",
                        "-frames:v", "1", os.path.join(images, f"{index}.jpg")])

        with open(FIXTURE, encoding="utf-8") as handle:
            product = json.load(handle)
        product["images"] = [{"url": os.path.join(images, f"{i}.jpg")} for i in range(3)]
        fixture = os.path.join(self.dir, "product.json")
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(product, handle, ensure_ascii=False)

        config = Config(runs_dir=self.dir)
        result = run(config, product_json=fixture, brand_id="kapya", fmt_id="motif",
                     variants=1, run_dir=os.path.join(self.dir, "run"), quiet=True)

        self.assertEqual(len(result.videos), 1)
        video = result.videos[0]
        self.assertTrue(os.path.exists(video))
        self.assertGreater(os.path.getsize(video), 50_000)
        self.assertAlmostEqual(tts.probe_duration(video), result.boards[0].duration(), delta=0.5)

        for name in ("product.json", "script-a.json", "storyboard-a.json", "run.json"):
            self.assertTrue(os.path.exists(os.path.join(self.dir, "run", name)), name)

    def test_render_prefers_an_animated_clip_over_ken_burns(self):
        """A shot with source_video must render from the clip, not the still."""
        from autoreels.stages import render as render_stage

        still = os.path.join(self.dir, "still.jpg")
        ffmpeg.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "color=c=red:size=1200x1500:d=1", "-frames:v", "1", still])
        generated = os.path.join(self.dir, "generated.mp4")
        ffmpeg.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "color=c=green:size=1280x720:d=5:r=24",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", generated])

        board = Storyboard(variant="a", shots=[
            Shot(index=0, image_path=still, start=0.0, duration=2.0,
                 motion="zoom_in", on_screen="", source_video=generated)])
        out = render_stage.render(board, Config(), self.dir,
                                  os.path.join(self.dir, "out.mp4"))

        frame = os.path.join(self.dir, "frame.png")
        ffmpeg.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", out,
                    "-frames:v", "1", frame])
        # Sample the centre pixel: green means the generated clip won.
        stats = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", frame, "-vf",
             "crop=1:1:540:960,format=rgb24", "-f", "rawvideo", "-"],
            capture_output=True)
        red, green, blue = stats.stdout[:3]
        self.assertGreater(green, red, "expected the generated (green) clip, got the still")
        self.assertGreater(green, blue)

    def test_storyboard_round_trip_keeps_the_narration(self):
        """`autoreels render` reads a saved storyboard — the audio must survive it."""
        from autoreels.models import Storyboard
        from autoreels.pipeline import run
        from autoreels.stages.storyboard import audio_segments

        images = os.path.join(self.dir, "img")
        os.makedirs(images)
        ffmpeg.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "color=c=0x203040:size=1200x1500:d=1",
                    "-frames:v", "1", os.path.join(images, "0.jpg")])

        with open(FIXTURE, encoding="utf-8") as handle:
            product = json.load(handle)
        product["images"] = [{"url": os.path.join(images, "0.jpg")}]
        fixture = os.path.join(self.dir, "product.json")
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(product, handle, ensure_ascii=False)

        run_dir = os.path.join(self.dir, "run")
        run(Config(runs_dir=self.dir), product_json=fixture, brand_id="kapya",
            fmt_id="motif", variants=1, render=False, run_dir=run_dir, quiet=True)

        reloaded = Storyboard.load(os.path.join(run_dir, "storyboard-a.json"))
        self.assertEqual(len(audio_segments(reloaded)), len(reloaded.shots))


if __name__ == "__main__":
    unittest.main()

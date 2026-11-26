"""The goal options (D17, D19, task 7.6): what a YAML can set and how its values read, the refusals generate_early
makes ahead of D12's three, the size a seed takes from the options, the half start's bound (D8), and what slot data
carries of the goal from version 1.2.0 on. Generation reads no image, so every test here is on the options alone.
"""
import json
import pathlib
import unittest

from BaseClasses import ItemClassification
from Options import FreeText, NamedRange, OptionError, TextChoice, Visibility
from test.general import setup_multiworld
from Utils import tuplize_version, version_tuple

from . import PaintHardTestBase
from .. import GOAL_IMAGE_MOST, HALF_START_MOST, PaintHardWorld, goal_image_allowed
from ..options import AspectRatio, GoalHeight, GoalImage, GoalImageSha256, GoalWidth, PaintOptions

MANIFEST = pathlib.Path(__file__).parent.with_name("archipelago.json")
# The sizes the Options Creator lists beside each side's slider, after aspect_ratio (test_options_creator.py)
SIDES = (450, 600, 800, 1024, 1080, 1200, 1280, 1440, 1500, 1600, 1920, 2000, 2048, 2160, 2560, 3000, 3072, 3840, 4000,
         4096, 6144, 8192, 12288, 16384)
URL = "https://example.com/goal.png"
SITE_PATH = "images/archipelago/4096x4096.png"
SHA256 = "0123456789abcdef" * 4
# Each aspect_ratio's bundled goal, by the option's key
ASPECT_SIZES = {"fullscreen": (800, 600), "widescreen": (800, 450), "square": (800, 800),
                "fullscreen_vertical": (600, 800), "widescreen_vertical": (450, 800)}
# What upstream's logic-55 rule refuses in a seed that plays alone, and Paint's spacing, whose 106 locations at logic
# 56 the item count refuses
LOGIC_55 = {"logic_percent": 50, "canvas_width_increment": 5, "canvas_height_increment": 5}
PAINTS_SPACING = {"hundredth_percent_checks": 100}
# generate_early's messages for the player the helper names Tester1, word for word
ONE_SIDE = "Tester1's Pain-T world sets {} {} without {}. Set both, or leave both at aspect_ratio."
DEFAULT_AT_ANOTHER_SIZE = ("Tester1's Pain-T world asks for goal_image default at {}, and the bundled image for "
                           "aspect_ratio {} is {}. Leave goal_width and goal_height at aspect_ratio, or name your own "
                           "{} image in goal_image.")
HASH_BESIDE_DEFAULT = ("Tester1's Pain-T world sets goal_image_sha256 beside goal_image default. A hash goes with an "
                       "image named in goal_image: name one, or leave goal_image_sha256 empty.")
NOT_A_HASH = ("Tester1's Pain-T world needs goal_image_sha256 empty or 64 hex digits (0-9 and a-f), the SHA-256 of the "
              "image file. It got {} characters, {} of them hex digits.")
NOT_AN_IMAGE = ("Tester1's Pain-T world can't take its goal_image. It takes default, an https URL with a host and no "
                "user name, or the path of an image file in the client's own site, such as "
                "images/archipelago/800x600.png: no leading slash, no .. part, and a file name with an extension. "
                "Either has no whitespace or backslash and at most 2,048 characters. http and data: URLs are refused.")
HALF_START = ("Tester1's Pain-T world can't use starting_canvas half on its {} goal: that start is {}, {} pixels for "
              "logic to expect painted by hand, and a half start goes up to 160,000 (400x400). Use starting_canvas "
              "tiny.")
UPSTREAMS_RULE = ("Tester1's Pain-T world needs logic_percent above 55 when it plays alone with "
                  "canvas_width_increment and canvas_height_increment both below 50.")


def named(width: int, height: int, **options) -> dict:
    """The options of a seed whose goal is an image of the player's own at this size."""
    return {"goal_image": URL, "goal_width": width, "goal_height": height, **options}


def generate_early(options: dict, slots: int = 1) -> PaintHardWorld:
    """Slot 1's world, Tester1's, with these options, through generate_early, where every refusal runs. More slots
    are Pain-T at the defaults, so no slot plays alone, and upstream's rule and the fill check, which judge a seed
    that plays alone, stay out."""
    return setup_multiworld([PaintHardWorld] * slots, ("generate_early",),
                            options=[options] + [{}] * (slots - 1)).worlds[1]


class GoalTestCase(unittest.TestCase):
    def refusal(self, options: dict, slots: int = 1) -> str:
        with self.assertRaises(OptionError) as raised:
            generate_early(options, slots)
        return str(raised.exception)


class TestTheOptions(unittest.TestCase):
    def test_names_and_classes(self) -> None:
        # A seed freezes the option names and what their values mean. aspect_ratio stays: removing it would refuse
        # every YAML that sets it (D17).
        hints = PaintOptions.type_hints
        self.assertEqual([GoalImage, GoalWidth, GoalHeight, GoalImageSha256, AspectRatio],
                         [hints[name] for name in ("goal_image", "goal_width", "goal_height", "goal_image_sha256",
                                                   "aspect_ratio")])
        self.assertTrue(issubclass(GoalImage, TextChoice) and issubclass(GoalImageSha256, FreeText))
        self.assertTrue(issubclass(GoalWidth, NamedRange) and issubclass(GoalHeight, NamedRange))
        # goal_image was hidden while it took only 1
        for option in (GoalImage, GoalWidth, GoalHeight, GoalImageSha256, AspectRatio):
            with self.subTest(option=option.__name__):
                self.assertEqual(Visibility.all, option.visibility)

    def test_goal_image_reads_default_the_old_1_and_text(self) -> None:
        self.assertEqual(({0: "default"}, 0), (GoalImage.name_lookup, GoalImage.default))
        for value in ("default", "Default", 1, "1", 0, "random"):
            with self.subTest(value=value):
                option = GoalImage.from_any(value)
                self.assertEqual((0, "default"), (option.value, option.current_key))
        for text in (URL, SITE_PATH, "http://example.com/goal.png"):
            with self.subTest(text=text):
                self.assertEqual(text, GoalImage.from_any(text).value)

    def test_the_sides_take_50_to_16384_or_aspect_ratio(self) -> None:
        for side in (GoalWidth, GoalHeight):
            with self.subTest(option=side.__name__):
                self.assertEqual((50, 16384, [("aspect_ratio", 0), *((str(size), size) for size in SIDES)], 0),
                                 (side.range_start, side.range_end, list(side.special_range_names.items()),
                                  side.default))
                self.assertEqual([0, 0, 50, 16384, 4096],
                                 [side.from_any(value).value for value in ("aspect_ratio", 0, 50, 16384, "4096")])
                for value in (-1, 1, 49, 16385):
                    with self.assertRaises(Exception, msg=value):
                        side.from_any(value)
        # D19: the sides' ends multiply to the largest canvas Chrome makes, so no count of pixels is checked.
        self.assertEqual(268_435_456, GoalWidth.range_end * GoalHeight.range_end)

    def test_the_hash_is_empty_by_default(self) -> None:
        self.assertEqual("", GoalImageSha256.default)
        # A YAML line left empty arrives as None
        self.assertEqual(["", "", SHA256], [GoalImageSha256.from_any(value).value for value in ("", None, SHA256)])

    def test_the_texts_state_plain_facts(self) -> None:
        # The house style: what generation checks and what the seed carries, and no so-clause on what that's for
        for option in (GoalImage, GoalWidth, GoalHeight, GoalImageSha256):
            with self.subTest(option=option.__name__):
                self.assertNotIn(", so ", " ".join(option.__doc__.split()))
        self.assertIn("Generation reads no file and no network", " ".join(GoalImage.__doc__.split()))


class TestWhatAGoalImageNames(unittest.TestCase):
    def test_https_urls_and_site_paths_are_allowed(self) -> None:
        for text in (URL, "HTTPS://EXAMPLE.com/Goal.PNG", "https://example.com:8443/goal.png",
                     "https://example.com/goal.png?raw=true#top", "https://example.com/bild-\u00fc.png",
                     "https://[2001:db8::1]/goal.png", "https://example.com", SITE_PATH, "goal.png", "./goal.jpg",
                     "images/goal.v2.webp", "goal.png?v=2", "images/my%20goal.png"):
            with self.subTest(text=text):
                self.assertTrue(goal_image_allowed(text))

    def test_other_schemes_are_refused(self) -> None:
        for text in ("http://example.com/goal.png", "data:image/png;base64,iVBORw0KGgo=", "ftp://example.com/goal.png",
                     "file:///C:/goal.png", "C:/goal.png", "javascript:alert(1)", "blob:https://example.com/goal.png",
                     "goal:1.png"):
            with self.subTest(text=text):
                self.assertFalse(goal_image_allowed(text))

    def test_an_https_url_needs_a_host_and_no_user_name(self) -> None:
        for text in ("https://", "https:/goal.png", "https:goal.png", "https:///goal.png",
                     "https://user@example.com/goal.png", "https://user:password@example.com/goal.png",
                     "https://@example.com/goal.png", "https://example.com:port/goal.png",
                     "https://example.com:99999/goal.png", "https://example.com:0/goal.png",
                     "https://[2001:db8::1/goal.png"):
            with self.subTest(text=text):
                self.assertFalse(goal_image_allowed(text))

    def test_a_site_path_stays_in_the_site_and_names_a_file(self) -> None:
        # From the host's root, on another host, out of the client's folder, which a browser also leaves at %2e%2e,
        # or with no file name and extension. None, True, 2 and random-low are what a YAML value left empty, a
        # boolean, a number and one of a Range's random names turn into as text.
        for text in ("/goal.png", "//example.com/goal.png", "../goal.png", "images/../../goal.png",
                     "%2e%2e/goal.png", "images/.%2E/goal.png", "images/", "images/.png", "images/goal.",
                     "images/goal", ".", "..", "", "?goal.png", "#goal.png", "None", "True", "2", "random-low"):
            with self.subTest(text=text):
                self.assertFalse(goal_image_allowed(text))

    def test_no_whitespace_no_backslash_and_2048_characters(self) -> None:
        self.assertEqual(2048, GOAL_IMAGE_MOST)
        longest, longer = ("https://example.com/" + "a" * letters + ".png" for letters in (2024, 2025))
        self.assertEqual((2048, True, 2049, False), (len(longest), goal_image_allowed(longest),
                                                     len(longer), goal_image_allowed(longer)))
        # A space, a tab, a line end, a no-break space and a zero-width space, which doesn't show
        for text in ("https://example.com/my goal.png", "https://example.com/goal.png ", "images/my goal.png",
                     "https://example.com/my\tgoal.png", "https://example.com/goal.png\n",
                     "https://example.com/my\u00a0goal.png", "https://exam\u200bple.com/goal.png",
                     "https://example.com\\goal.png", "images\\goal.png", "C:\\goal.png"):
            with self.subTest(text=text):
                self.assertFalse(goal_image_allowed(text))


class TestTheRefusals(GoalTestCase):
    def test_one_side_set_alone(self) -> None:
        self.assertEqual(ONE_SIDE.format("goal_width", 2000, "goal_height"), self.refusal({"goal_width": 2000}))
        self.assertEqual(ONE_SIDE.format("goal_height", 1500, "goal_width"),
                         self.refusal({"goal_image": URL, "goal_height": 1500}))

    def test_default_at_a_size_other_than_the_aspect_ratios(self) -> None:
        # The client would load it as a missing bundled file and score against black (D17).
        self.assertEqual(DEFAULT_AT_ANOTHER_SIZE.format("1024x768", "fullscreen", "800x600", "1024x768"),
                         self.refusal({"goal_width": 1024, "goal_height": 768}))
        # Another aspect ratio's size is refused too: the option that picks a bundled image is aspect_ratio.
        self.assertEqual(DEFAULT_AT_ANOTHER_SIZE.format("800x600", "square", "800x800", "800x600"),
                         self.refusal({"aspect_ratio": "square", "goal_width": 800, "goal_height": 600}))
        for aspect_ratio, (width, height) in ASPECT_SIZES.items():
            with self.subTest(aspect_ratio=aspect_ratio):
                world = generate_early({"aspect_ratio": aspect_ratio, "goal_width": width, "goal_height": height})
                self.assertEqual((width, height, "default"), (world.final_width, world.final_height, world.goal_image))

    def test_a_hash_beside_default(self) -> None:
        self.assertEqual(HASH_BESIDE_DEFAULT, self.refusal({"goal_image_sha256": SHA256}))
        self.assertEqual(HASH_BESIDE_DEFAULT, self.refusal({"goal_image": 1, "goal_image_sha256": SHA256}))

    def test_a_hash_that_isnt_64_hex_digits(self) -> None:
        for sha256, characters, hex_digits in ((SHA256[:63], 63, 63), (SHA256 + "0", 65, 65),
                                               (SHA256[:62] + "g-", 64, 62), ("sha256:" + SHA256, 71, 68),
                                               ("None", 4, 1)):
            with self.subTest(sha256=sha256):
                self.assertEqual(NOT_A_HASH.format(characters, hex_digits),
                                 self.refusal({"goal_image": URL, "goal_image_sha256": sha256}))

    def test_an_image_that_is_neither_an_https_url_nor_a_site_path(self) -> None:
        # One message for every image goal_image_allowed turns away, and it names http and data: (D17).
        self.assertIn("http and data: URLs are refused.", NOT_AN_IMAGE)
        for text in ("http://example.com/goal.png", "data:image/png;base64,iVBORw0KGgo=",
                     "https://user@example.com/goal.png", "https://example.com/my goal.png", "/goal.png", "None", ""):
            with self.subTest(text=text):
                self.assertEqual(NOT_AN_IMAGE, self.refusal({"goal_image": text}))

    def test_the_goal_is_checked_in_d17s_order(self) -> None:
        # One side alone, default at another size, a hash beside default, a hash that isn't one, then the image.
        # Each seed here breaks its rule and every later one it can.
        not_a_hash = {"goal_image_sha256": "0123"}
        for message, options in (
                (ONE_SIDE.format("goal_width", 2000, "goal_height"),
                 {"goal_image": "http://example.com/goal.png", "goal_width": 2000, **not_a_hash}),
                (DEFAULT_AT_ANOTHER_SIZE.format("1024x768", "fullscreen", "800x600", "1024x768"),
                 {"goal_width": 1024, "goal_height": 768, **not_a_hash}),
                (HASH_BESIDE_DEFAULT, not_a_hash),
                (NOT_A_HASH.format(4, 4), {"goal_image": "http://example.com/goal.png", **not_a_hash})):
            with self.subTest(message=message):
                self.assertEqual(message, self.refusal(options))

    def test_the_goal_and_the_half_start_come_ahead_of_d12s_three(self) -> None:
        # D12's order holds behind them: upstream's rule, the item count, then the fill check
        # (test_auto_copy_logic.py). This seed breaks the goal check, the half start's bound, upstream's rule and the
        # item count, and each fix leaves the next refusal.
        options = {**named(16384, 16384), "goal_image": "http://example.com/goal.png", "starting_canvas": "half",
                   **LOGIC_55, **PAINTS_SPACING}
        self.assertEqual(NOT_AN_IMAGE, self.refusal(options))
        options["goal_image"] = URL
        self.assertEqual(HALF_START.format("16384x16384", "8192x8192", "67,108,864"), self.refusal(options))
        options["starting_canvas"] = "tiny"
        self.assertEqual(UPSTREAMS_RULE, self.refusal(options))
        options["logic_percent"] = 56
        # 6,552 canvas items at 5 px and 14 speed copies, in the 106 locations of Paint's spacing at logic 56
        self.assertIn("has 106 locations for 7645 required items.", self.refusal(options))

    def test_a_second_slot_changes_none_of_them(self) -> None:
        # Upstream's rule and the fill check read a seed that plays alone. The goal's refusals read the YAML.
        for message, options in ((ONE_SIDE.format("goal_width", 2000, "goal_height"), {"goal_width": 2000}),
                                 (HASH_BESIDE_DEFAULT, {"goal_image_sha256": SHA256}),
                                 (NOT_AN_IMAGE, {"goal_image": "http://example.com/goal.png"}),
                                 (HALF_START.format("802x800", "401x400", "160,400"),
                                  named(802, 800, starting_canvas="half"))):
            with self.subTest(message=message):
                self.assertEqual(message, self.refusal(options, slots=2))


class TestTheGoalsSize(GoalTestCase):
    def test_each_aspect_ratio_keeps_its_bundled_size(self) -> None:
        for aspect_ratio, size in ASPECT_SIZES.items():
            with self.subTest(aspect_ratio=aspect_ratio):
                world = generate_early({"aspect_ratio": aspect_ratio})
                slot_data = world.fill_slot_data()
                self.assertEqual((size, size, size),
                                 ((world.final_width, world.final_height),
                                  (world.layout.final_width, world.layout.final_height),
                                  (slot_data["final_width"], slot_data["final_height"])))

    def test_a_named_size_takes_the_aspect_ratios_place(self) -> None:
        # The size reaches logic's layout, the canvas items and slot data, whatever aspect_ratio says. From the 5x5
        # start in 100 px steps 4096x4096 takes 41 width and 41 height items.
        for width, height, canvas_items in ((1000, 700, (10, 7)), (4096, 4096, (41, 41)), (50, 50, (1, 1)),
                                            (16384, 50, (164, 1)), (50, 16384, (1, 164)),
                                            (16384, 16384, (164, 164))):
            with self.subTest(goal=(width, height)):
                world = generate_early(named(width, height, aspect_ratio="widescreen_vertical"), slots=2)
                slot_data = world.fill_slot_data()
                self.assertEqual(((width, height), (width, height), (width, height), (5, 5)),
                                 ((world.final_width, world.final_height),
                                  (world.layout.final_width, world.layout.final_height),
                                  (slot_data["final_width"], slot_data["final_height"]),
                                  (slot_data["start_width"], slot_data["start_height"])))
                items = world.non_filler_items()
                self.assertEqual((canvas_items, canvas_items),
                                 (world.layout.canvas_items, (items.count("Progressive Canvas Width"),
                                                              items.count("Progressive Canvas Height"))))

    def test_a_named_image_at_the_aspect_ratios_size_needs_no_sides(self) -> None:
        world = generate_early({"goal_image": SITE_PATH, "aspect_ratio": "square"})
        self.assertEqual((800, 800, SITE_PATH), (world.final_width, world.final_height, world.goal_image))

    def test_the_speed_copies_grow_with_the_goal(self) -> None:
        # D19: enough copies for the top tier to paint the whole goal within the hours, and never fewer than 10. Ten
        # cover 22,118,400 pixels at 6 h.
        for width, height, hours, copies in ((800, 600, 6, 10), (4096, 4096, 6, 10), (4703, 4703, 6, 10),
                                             (4704, 4704, 6, 11), (8192, 8192, 6, 12), (16384, 16384, 6, 14),
                                             (8192, 8192, 1, 15), (16384, 16384, 1, 17), (16384, 16384, 24, 12),
                                             (16384, 16384, 0, 14)):
            with self.subTest(goal=(width, height), hours=hours):
                world = generate_early(named(width, height, auto_copy_logic_hours=hours), slots=2)
                self.assertEqual((copies, copies, copies),
                                 (world.layout.speed_items,
                                  world.non_filler_items().count("Progressive Auto Copy Speed"),
                                  world.fill_slot_data()["auto_copy_speed_items"]))

    def test_the_half_start_goes_up_to_160000_pixels(self) -> None:
        # D8: logic expects the starting canvas painted by hand, and the largest bundled half start is the 400x400
        # of 800x800. The start is half of each side, rounded down.
        self.assertEqual(160_000, HALF_START_MOST)
        for options, start in (({"aspect_ratio": "square"}, (400, 400)), (named(800, 800), (400, 400)),
                               (named(801, 801), (400, 400)), (named(1600, 400), (800, 200)),
                               (named(12800, 50), (6400, 25)), (named(50, 50), (25, 25))):
            with self.subTest(options=options):
                world = generate_early({**options, "starting_canvas": "half"}, slots=2)
                slot_data = world.fill_slot_data()
                self.assertEqual((start, start, start),
                                 ((world.start_width, world.start_height),
                                  (world.layout.start_width, world.layout.start_height),
                                  (slot_data["start_width"], slot_data["start_height"])))
                self.assertLessEqual(start[0] * start[1], HALF_START_MOST)
        for width, height, start, pixels in ((802, 800, "401x400", "160,400"), (800, 802, "400x401", "160,400"),
                                             (12802, 50, "6401x25", "160,025"),
                                             (4096, 4096, "2048x2048", "4,194,304"),
                                             (16384, 16384, "8192x8192", "67,108,864")):
            with self.subTest(goal=(width, height)):
                self.assertEqual(HALF_START.format(f"{width}x{height}", start, pixels),
                                 self.refusal(named(width, height, starting_canvas="half")))
                # The 5x5 start takes the same goal.
                world = generate_early(named(width, height), slots=2)
                self.assertEqual((5, 5, 25), (world.start_width, world.start_height, world.layout.matched))


class TestSlotData(GoalTestCase):
    def test_both_goal_keys_are_on_every_seed(self) -> None:
        # D17: goal_image is "default" or the YAML's text, and goal_image_sha256 "" or 64 lowercase hex digits. The
        # size is in final_width and final_height. The pixels never are.
        for options, goal_image, sha256 in (
                ({}, "default", ""),
                ({"goal_image": 1}, "default", ""),
                ({"goal_image": "Default", "aspect_ratio": "widescreen", "starting_canvas": "half"}, "default", ""),
                ({"goal_image": URL}, URL, ""),
                ({"goal_image": URL, "goal_image_sha256": SHA256}, URL, SHA256),
                ({"goal_image": SITE_PATH, "goal_width": 4096, "goal_height": 4096,
                  "goal_image_sha256": SHA256.upper()}, SITE_PATH, SHA256),
                ({"goal_image": "HTTPS://Example.com/Goal.PNG", "goal_image_sha256": None},
                 "HTTPS://Example.com/Goal.PNG", "")):
            for slots in (1, 2):
                with self.subTest(options=options, slots=slots):
                    slot_data = generate_early(options, slots).fill_slot_data()
                    self.assertEqual((goal_image, sha256), (slot_data["goal_image"], slot_data["goal_image_sha256"]))
                    self.assertEqual((str, str), (type(slot_data["goal_image"]), type(slot_data["goal_image_sha256"])))
                    self.assertEqual(slot_data, json.loads(json.dumps(slot_data)))

    def test_the_goal_changes_no_other_key(self) -> None:
        # A named goal at the default size and the defaults differ in slot data by the two goal keys alone.
        defaults = generate_early({}).fill_slot_data()
        with_goal = generate_early({"goal_image": URL, "goal_image_sha256": SHA256}).fill_slot_data()
        self.assertEqual({"goal_image", "goal_image_sha256"},
                         {key for key in defaults.keys() | with_goal.keys() if defaults.get(key) != with_goal.get(key)})


class TestTheVersion(unittest.TestCase):
    def test_the_manifest_the_world_and_slot_data_say_1_2_0(self) -> None:
        # Seeds of Phase 5 carry 1.1.0. From 1.2.0 slot data has goal_image and goal_image_sha256 (D17).
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(("Pain-T", "1.2.0"), (manifest["game"], manifest["world_version"]))
        self.assertEqual("1.2.0", PaintHardWorld.world_version.as_simple_string())
        self.assertEqual("1.2.0", generate_early({}).fill_slot_data()["version"])

    def test_the_manifest_names_the_oldest_core_it_runs_on(self) -> None:
        # Archipelago 0.6.6, whose core this release was built and tested on: a core older than minimum_ap_version
        # doesn't load the .apworld. Build APWorlds adds version and compatible_version, and the folder's manifest
        # holds neither.
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual({"game": "Pain-T", "authors": ["MarioManTAW", "Zackman6344"], "world_version": "1.2.0",
                          "minimum_ap_version": "0.6.6"}, manifest)
        self.assertLessEqual(tuplize_version(manifest["minimum_ap_version"]), version_tuple)


class TestANamedGoal(PaintHardTestBase):
    # A 1000x700 image of the player's own: the base class's tests reach every location with every item and fill it.
    options = {"goal_image": URL, "goal_width": 1000, "goal_height": 700, "goal_image_sha256": SHA256.upper()}

    def test_the_pool_follows_the_size(self) -> None:
        # 10 width and 7 height items where 800x600 has 8 and 6, in the same 8,043 locations. Nine speed copies can
        # still raise the cap on 700,000 pixels at 6 h, where 800x600 has 8.
        pool = [item.name for item in self.multiworld.itempool]
        self.assertEqual((10, 7, 10), (pool.count("Progressive Canvas Width"), pool.count("Progressive Canvas Height"),
                                       pool.count("Progressive Auto Copy Speed")))
        self.assertEqual([ItemClassification.progression] * 9 + [ItemClassification.useful],
                         [item.classification for item in self.multiworld.itempool
                          if item.name == "Progressive Auto Copy Speed"])
        fillers = [item for item in self.multiworld.itempool if item.classification == ItemClassification.filler]
        self.assertEqual((1106, 8043, 8043), (len(pool) - len(fillers), len(pool),
                                              len(self.multiworld.get_locations(self.player))))

    def test_slot_data_carries_the_goal(self) -> None:
        slot_data = self.world.fill_slot_data()
        self.assertEqual((URL, SHA256, 1000, 700, 5, 5, "1.2.0"),
                         tuple(slot_data[key] for key in ("goal_image", "goal_image_sha256", "final_width",
                                                          "final_height", "start_width", "start_height", "version")))

"""The options of Phase 8's three check families, Perfect Pixels and Auto Copy Time (D21) and Missed Pixels (D26):
their names, what they take and their defaults, the fields that carry them into logic's layout, and what the game page
and the setup guide say of them. A seed keeps the values its YAML gave them. In this release each family is off by
default, so a YAML that names none of them makes the seed it made before the families.
"""
import pathlib
import re
import unittest
from dataclasses import fields

from Options import Choice, Range, Visibility
from test.general import setup_multiworld

from .. import PaintHardWorld
from ..items import item_groups
from ..locations import LOCATION_BASE, location_groups, location_table
from ..options import (AutoCopyLogicHours, MissedPixelChecks, PaintOptions, PerfectPixelChecks, PerfectPixelItems,
                       TimesanityHours, TimesanityMinutes)
from ..rules import Layout
from .test_auto_copy_logic import layout

# Each option that takes a number: (its class, the least and the most it takes, its default, its name in a spoiler)
RANGES = {"perfect_pixel_checks": (PerfectPixelChecks, 0, 20, 0, "Perfect Pixel Checks"),
          "timesanity_minutes": (TimesanityMinutes, 0, 1440, 0, "Timesanity Minutes"),
          "timesanity_hours": (TimesanityHours, 1, 24, 24, "Timesanity Hours"),
          "missed_pixel_checks": (MissedPixelChecks, 0, 720, 0, "Missed Pixel Checks")}
# The layout's fields for the families, in its order, each named as its option, and what they hold with every
# family off
FIELDS = ("perfect_pixel_checks", "perfect_pixel_items", "timesanity_minutes", "timesanity_hours",
          "missed_pixel_checks")
OFF = (0, "useful", 0, 24, 0)
DOCS = pathlib.Path(__file__).parent.with_name("docs")
# generate_early's refusals in its order, each by words its entry in the setup guide's list holds: the goal options and
# the half start (D17, D8), upstream's logic-55 rule, the item count, task 8.3's count and the solo fill check (D12)
REFUSALS = ("The goal options", "`starting_canvas: half`", "`logic_percent` above 55", "items outnumber its locations",
            "progression items outnumber the locations that take progression", "a model of Archipelago's fill")


def generate_early(options: dict) -> PaintHardWorld:
    return setup_multiworld(PaintHardWorld, ("generate_early",), options=options).worlds[1]


class TestTheOptions(unittest.TestCase):
    def test_names_ranges_and_defaults(self) -> None:
        for name, (option, least, most, default, display_name) in RANGES.items():
            with self.subTest(option=name):
                self.assertIs(option, PaintOptions.type_hints[name])
                self.assertTrue(issubclass(option, Range))
                self.assertEqual((least, most, default, display_name, Visibility.all),
                                 (option.range_start, option.range_end, option.default, option.display_name,
                                  option.visibility))
                self.assertEqual([least, most, default],
                                 [option.from_any(value).value for value in (least, str(most), default)])
                for value in (least - 1, most + 1):
                    with self.assertRaises(Exception, msg=value):
                        option.from_any(value)

    def test_perfect_pixel_items_takes_useful_filler_or_any(self) -> None:
        self.assertIs(PerfectPixelItems, PaintOptions.type_hints["perfect_pixel_items"])
        self.assertTrue(issubclass(PerfectPixelItems, Choice))
        self.assertEqual(({"useful": 0, "filler": 1, "any": 2}, 0, "Perfect Pixel Items", Visibility.all),
                         (PerfectPixelItems.options, PerfectPixelItems.default, PerfectPixelItems.display_name,
                          PerfectPixelItems.visibility))
        for key, value in (("useful", 0), ("filler", 1), ("any", 2), ("Any", 2)):
            with self.subTest(key=key):
                option = PerfectPixelItems.from_any(key)
                self.assertEqual((value, key.lower()), (option.value, option.current_key))
        with self.assertRaises(KeyError):
            PerfectPixelItems.from_any("progression")

    def test_each_family_is_off_by_default(self) -> None:
        # 0 checks of each family. The plan's defaults, 5 Perfect Pixels checks a canvas step, a mark every 10 minutes
        # and 24 Missed Pixels checks a speed copy, wait for task 6.3. The other two options switch nothing on.
        self.assertEqual((0, 0, 0), (PerfectPixelChecks.default, TimesanityMinutes.default,
                                     MissedPixelChecks.default))
        self.assertEqual(("useful", 24), (PerfectPixelItems.name_lookup[PerfectPixelItems.default],
                                          TimesanityHours.default))

    def test_auto_copy_logic_hours_names_its_two_exceptions(self) -> None:
        # D8: no check in logic needs more than the hours of auto copy, but for the Auto Copy Time marks, which count
        # auto copy's whole time, and the Missed Pixels checks, which count Happy Accident's switch. The hours' text
        # names both, and each family's own option says how long its last check takes.
        hours = " ".join(AutoCopyLogicHours.__doc__.split())
        self.assertIn("The Auto Copy Time and Missed Pixels checks are the two exceptions", hours)
        for key, last in (("timesanity_minutes", "the last one takes up to timesanity_hours of auto copy in all"),
                          ("missed_pixel_checks", "the last check is what your top speed paints in timesanity_hours")):
            with self.subTest(option=key):
                self.assertIn(key, hours)
                self.assertIn(last, " ".join(PaintOptions.type_hints[key].__doc__.split()))

    def test_the_texts_name_other_options_by_key(self) -> None:
        # As the setup guide does: a key is what a YAML and slot data hold, and a display name can change. Paint's own
        # trap_blacklist text names Archipelago's Trap Link, which trap_link turns on.
        names = {key: option.display_name for key, option in PaintOptions.type_hints.items()}
        for key, option in PaintOptions.type_hints.items():
            if option.__module__ != PerfectPixelItems.__module__:
                continue  # Archipelago's common options
            text = " ".join(option.__doc__.split())
            with self.subTest(option=key):
                self.assertEqual([], [other for other, name in names.items() if other != key and name in text and
                                      (key, other) != ("trap_blacklist", "trap_link")])


class TestTheLayout(unittest.TestCase):
    def test_a_layout_has_every_family_off_unless_told(self) -> None:
        # The fields come last but one and have defaults, so a Layout built without them is one of a seed with no
        # family. The last, happy_from_pool, counts the Happy Accident start_inventory_from_pool takes, 0 without it.
        names = tuple(field.name for field in fields(Layout))
        self.assertEqual((FIELDS, "happy_from_pool"), (names[-len(FIELDS) - 1:-1], names[-1]))
        self.assertEqual(OFF + (0,), tuple(field.default for field in fields(Layout))[-len(FIELDS) - 1:])
        self.assertEqual(OFF, tuple(getattr(layout(), name) for name in FIELDS))

    def test_the_defaults_seed_has_every_family_off(self) -> None:
        world = generate_early({})
        self.assertEqual(OFF, tuple(getattr(world.layout, name) for name in FIELDS))
        self.assertEqual(layout(), world.layout)

    def test_generate_early_reads_the_options_into_the_layout(self) -> None:
        for values in ((5, "useful", 10, 24, 24),  # the plan's defaults
                       (20, "any", 1, 6, 720), (1, "filler", 1440, 1, 1), (0, "any", 0, 12, 0)):
            with self.subTest(values=values):
                world = generate_early(dict(zip(FIELDS, values)))
                self.assertEqual(values, tuple(getattr(world.layout, name) for name in FIELDS))
                self.assertEqual(layout(**dict(zip(FIELDS, values))), world.layout)


class TestTheDefaultsSeed(unittest.TestCase):
    def test_no_check_of_the_three_families_and_no_happy_accident(self) -> None:
        # The 8,043 similarity and Matched Pixels checks of the seeds before the families, and their items
        multiworld = setup_multiworld(PaintHardWorld, ("generate_early", "create_regions", "create_items"), seed=1)
        addresses = [location.address for location in multiworld.get_locations(1)]
        self.assertEqual((8043, 8043), (len(addresses), len([address for address in addresses
                                                              if address <= LOCATION_BASE + 9900])))
        items = [item.name for item in multiworld.itempool + multiworld.precollected_items[1]]
        self.assertEqual((8045, 0), (len(items), items.count("Happy Accident")))
        self.assertNotIn("Happy Accident", multiworld.worlds[1].non_filler_items())


def page(name: str) -> str:
    """A page of docs/ with its line breaks and runs of spaces as single spaces"""
    return " ".join((DOCS / name).read_text(encoding="utf-8").split())


class TestTheDocs(unittest.TestCase):
    def test_the_guide_lists_every_refusal_in_order(self) -> None:
        # One entry for each refusal generate_early makes, in its order. The item count's entry says it leaves out the
        # Perfect Pixels checks at filler (D21) and how far a bigger step makes room where they hold items
        # (fewer_items_hint), and the fill check's what its model leaves out (the map's stopgap).
        text = (DOCS / "guide_en.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        paragraphs = text.split("\n\n")
        listed = next(after for before, after in zip(paragraphs, paragraphs[1:]) if before.endswith("in this order:"))
        entries = [" ".join(entry.split()) for entry in listed.split("\n- ")]
        self.assertEqual(len(REFUSALS), len(entries))
        for words, entry in zip(REFUSALS, entries):
            with self.subTest(refusal=words):
                self.assertIn(words, entry)
        self.assertIn("`perfect_pixel_items: filler`", entries[3])
        self.assertIn("At `useful` and `any`, where the Perfect Pixels checks hold items, the message names bigger "
                      "steps only up to `perfect_pixel_checks` pixels: up to there each line of pixels keeps its "
                      "check, and a bigger step leaves out canvas items alone.", entries[3])
        self.assertIn("it leaves out Happy Accident and the checks of the three families", entries[5])

    def test_both_pages_name_the_families(self) -> None:
        # Each family, its options and Happy Accident, on the game page and in the setup guide. The game page's
        # sentence on the speed items names the Missed Pixels, which make every one progression (D26).
        for name in ("en_Pain-T.md", "guide_en.md"):
            text = page(name)
            for words in ("Perfect Pixels", "Auto Copy Time", "Missed Pixels", "Happy Accident", *RANGES,
                          "perfect_pixel_items"):
                with self.subTest(page=name, words=words):
                    self.assertIn(words, text)
        self.assertIn("every speed item is progression while `missed_pixel_checks` is above 0", page("en_Pain-T.md"))

    def test_the_game_page_names_each_perfect_pixel_items_value(self) -> None:
        # The option's three values, each with what it lets the checks hold, as the guide gives them
        self.assertIn("`perfect_pixel_items` sets what they hold: `useful` takes useful items, filler and traps, "
                      "`filler` takes filler and traps alone, and `any` takes every item.", page("en_Pain-T.md"))
        self.assertEqual(("useful", "filler", "any"), tuple(PerfectPixelItems.options))

    def test_both_pages_say_what_the_client_does_yet(self) -> None:
        # Until the client reads goal_image it loads the bundled folder's file of the seed's size, and until tasks 8.4
        # to 8.9 it sends no check of the three families. The guide says how to play a goal of your own meanwhile, and
        # that File->Open Goal Image takes another goal only until then (D18).
        for name in ("en_Pain-T.md", "guide_en.md"):
            text = page(name)
            with self.subTest(page=name):
                self.assertIn("Until the client reads `goal_image`, it loads `images/archipelago/{width}x{height}.png` "
                              "from its own site at the seed's size", text)
                self.assertIn("The client doesn't send Perfect Pixels, Auto Copy Time or Missed Pixels checks yet, "
                              "and items on them wait for the release that does.", text.replace("**", ""))
        guide = page("guide_en.md")
        self.assertIn("put its file at that path in the client's site and name the same path in `goal_image`", guide)
        self.assertIn("Until the client reads `goal_image`, you may then load a custom target image with File->Open "
                      "Goal Image.", guide)

    def test_the_guide_names_the_groups_and_what_takes_them(self) -> None:
        # Every name group but Archipelago's Everything and Everywhere, each a whole entry of its list in the sentence
        # that lists them, the options that take a group, the commands, and the priority fill's error with the checks
        # generate_early takes out of priority_locations
        part = page("guide_en.md").split("## Names and groups")[1].split("## Playing")[0]
        start = part.index("The item groups ")
        sentence = part[start:part.index(" hold every check.", start)].removeprefix("The item groups ")
        items, locations = sentence.split(" hold every item but the two fillers, and the location groups ")
        for listed, groups in ((items, item_groups), (locations, location_groups)):
            with self.subTest(groups=sorted(groups)):
                self.assertEqual(sorted(groups), sorted(re.split(r", | and ", listed)))
        for words in ("`local_items`, `non_local_items` and `start_hints` take an item group",
                      "`exclude_locations`, `priority_locations` and `start_location_hints` a location group",
                      "`!hint` takes an item group and `!hint_location` a location group",
                      "each call pays for one hint of the group", "`!missing Missed Pixels`",
                      "Archipelago's fill stops with an error when `priority_locations` names more of a family's "
                      "checks than the progression that can sit on them.",
                      "the Perfect Pixels checks at `perfect_pixel_items: useful` or `filler`, and every family's "
                      "checks at `auto_copy_logic_hours: 0`"):
            with self.subTest(words=words):
                self.assertIn(words, part.replace("**", ""))

    def test_the_guide_says_how_to_make_the_yaml_in_the_options_creator(self) -> None:
        # The eight options with a list beside their slider, the values it names from those lists, what an export
        # writes for a pick, the text editor for an exact value, and Enter in the two text boxes, as the options' texts
        # say (test_options_creator.py)
        part = page("guide_en.md").split("## Making the YAML in the Options Creator")[1].split("## ")[0]
        listed = part.split("have a list beside the slider")[0]
        for key in ("goal_width", "goal_height", "color_depth_items", "miss_margin_step", "overclock_seconds",
                    "overclock_bank_size_step", "timesanity_minutes", "missed_pixel_checks"):
            with self.subTest(option=key):
                self.assertIn(f"`{key}`", listed)
        # Each value it names is a pick of the options it names: a goal's side by its number, and 0 by its name
        side = re.search(r"such as (\d+) for a goal's side", part)
        zero = re.search(r"and `(\w+)` for 0 on `(\w+)` and `(\w+)`", part)
        self.assertEqual(("4096", "disabled", "timesanity_minutes", "missed_pixel_checks"),
                         (side.group(1), *zero.groups()) if side and zero else part)
        for key, name, value in (("goal_width", side.group(1), 4096), ("goal_height", side.group(1), 4096),
                                 (zero.group(2), zero.group(1), 0), (zero.group(3), zero.group(1), 0)):
            with self.subTest(option=key, pick=name):
                self.assertEqual(value, PaintOptions.type_hints[key].special_range_names.get(name))
        for words in ("a slider over thousands of values can't land on an exact one",
                      "have a list beside the slider that holds common values",
                      "exported as text, such as `goal_width: '4096'`, and reads as the number",
                      "An exact value the slider can't reach goes into the exported YAML with a text editor.",
                      "In the text boxes of `goal_image` and `goal_image_sha256`, press Enter after typing or "
                      "pasting: in Archipelago 0.6.6 a box keeps a value only then."):
            with self.subTest(words=words):
                self.assertIn(words, part)

    def test_both_pages_say_where_the_useful_items_gather(self) -> None:
        # At useful and at any the fill puts useful items of every game on the Perfect Pixels checks beyond their share
        # of the locations, with the counts of seeds of 30 slots at any, with 8 Pain-T slots and with one, in both pages
        # and the option's text. None says most of the multiworld's useful items: with one Pain-T slot of 30 it was 28%
        # to 34% of them.
        sentence = ("At `useful` and at `any`, Archipelago's fill puts useful items of every game on these checks, "
                    "which open last, beyond their share of the locations. In a seed of 30 slots, 8 of them Pain-T in "
                    "5 px steps with every family at its top, 5,462 of the 6,995 useful items sat on those 8 slots' "
                    "Perfect Pixels checks, 26% of the locations. With one such slot of 30, 28% to 34% of the useful "
                    "items sat on its 8,182 checks, 11% of the locations. Those seeds ran at `any`.")
        text = " ".join(PerfectPixelItems.__doc__.split())
        for name, written, said in (("en_Pain-T.md", page("en_Pain-T.md"), sentence),
                                    ("guide_en.md", page("guide_en.md"), sentence),
                                    ("PerfectPixelItems", text, sentence.replace("`", "").replace("5 px", "5 pixel"))):
            with self.subTest(text=name):
                self.assertIn(said, written)
                self.assertNotIn("most of the multiworld's useful items", written)

    def test_the_guide_spells_each_familys_names(self) -> None:
        # Each name the part writes out is a location of the game, and each family has one
        part = (DOCS / "guide_en.md").read_text(encoding="utf-8").split("## Names and groups")[1].split("\n\n")[1]
        spelled = re.findall(r"`([^`]+)`", part)
        names = [name for name in spelled if not name.startswith("!")]
        self.assertEqual([], [name for name in names if name not in location_table])
        for group in location_groups:
            with self.subTest(group=group):
                self.assertTrue(any(name in location_groups[group] for name in names))

    def test_both_pages_say_the_fill_check_runs_alone(self) -> None:
        # The solo refusal's own last sentence, in the guide's entry for the check and on the game page. The guide's
        # entry goes on to a YAML the check refuses alone that Archipelago's fill refused beside a slot of another game
        # (the release check's three seeds beside Hollow Knight).
        sentence = "Beside other slots this check doesn't run, and Archipelago's own fill decides."
        text = (DOCS / "guide_en.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        paragraphs = text.split("\n\n")
        listed = next(after for before, after in zip(paragraphs, paragraphs[1:]) if before.endswith("in this order:"))
        entry = " ".join(listed.split("\n- ")[5].split())
        self.assertIn(sentence, entry)
        self.assertIn(f"{sentence} A YAML the check refuses alone can fail there too: 4096x4096 in 5 px steps with 20 "
                      f"Perfect Pixels checks a step at `any` and the other two families off failed Archipelago's fill "
                      f"beside one Hollow Knight slot at 3 of 3 seeds, with \"No more spots to place\", and filled "
                      f"there in 100 px steps.", entry)
        self.assertIn(sentence, page("en_Pain-T.md"))

    def test_the_guide_gives_the_speed_copies_hours_at_0_and_happy_accidents_switch(self) -> None:
        # The speed copies count 6 hours with auto copy out of logic (rules.py), and the switch the guide names later is
        # introduced with Happy Accident
        guide = page("guide_en.md")
        self.assertIn("within `auto_copy_logic_hours` (6 hours at `auto_copy_logic_hours: 0`)", guide)
        self.assertEqual(14, layout(final_width=16384, final_height=16384, auto_copy_logic_hours=0).speed_items)
        self.assertLess(guide.index("gives auto copy a switch to miss on purpose"),
                        guide.index("Happy Accident's switch"))

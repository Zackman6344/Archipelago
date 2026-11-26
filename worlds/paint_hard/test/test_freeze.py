"""What a seed of this release freezes beyond its names and ids (test_data_package.py), against hard-fork/plan_math.py:
task 8.3's count of progression against the locations that take it, which refuses a seed solo or not, after the item
count and before the solo fill check; the solo fill check at the plan's defaults for the three families, which it
still models without them (the stopgap of stages 3 to 5); every slot data key with its shape, from which a client
tells a seed with each family from one without, and the ids client_contract.json gives the client for each family's
list; a world loaded without its manifest's version, which generation refuses; and priority_locations, which keeps no
check that takes no progression.
"""
import json
import logging
import unittest
from dataclasses import replace
from string import hexdigits
from unittest import mock

from BaseClasses import ItemClassification, LocationProgressType, MultiWorld
from Fill import distribute_items_restrictive
from Options import OptionError
from test.general import setup_multiworld
from Utils import Version

from .. import PaintHardWorld, fewer_items_hint, rules
from ..items import traps
from ..locations import (EARLY_BASE, LOCATION_BASE, MATCHED_BASE, MISSED_BASE, PERFECT_BASE, TIME_BASE,
                         location_groups)
from ..rules import (INCREMENTS, MISSED_NAMES, PERFECT_MOST, TIME_MARKS, change_fills, happy_count, location_percents,
                     passes_filled, progression_counts)
from . import test_client_contract
from .test_auto_copy_logic import layout
from .test_auto_copy_time import build
from .test_data_package import BLOCKS
from .test_goal_options import SHA256, SITE_PATH, generate_early, named
from .test_perfect_pixels import reaches_every_location

UPSTREAM = (50, 70, 100, 100, 100)  # Paint's spacing: half, quarter, tenth, twentieth and hundredth_percent_checks
# The three families at the plan's defaults (D21, D26), which this release leaves off: 5 Perfect Pixels checks a
# canvas step at useful, a mark every 10 minutes to 24 h, and 24 Missed Pixels checks a speed copy
PLAN_FAMILIES = {"perfect_pixel_checks": 5, "timesanity_minutes": 10, "missed_pixel_checks": 24}
PLAN_LAYOUT = dict(perfect_pixel_checks=5, timesanity_minutes=10, missed_pixel_checks=24)
# D26's setup: the 400x300 start at 5 px steps, Paint's spacing, logic 99, 28 color items and auto copy out of logic
TIGHT_LAYOUT = dict(start_width=400, start_height=300, width_increment=5, height_increment=5, spacing=UPSTREAM,
                    logic_percent=99, color_depth_items=28, auto_copy_logic_hours=0)
# plan_math.room_counts() and no_progression_count(): (layout changes, (locations, excluded, turning progression away,
# taking it, progression items))
COUNTS = [
    (PLAN_LAYOUT, (8545, 0, 70, 8475, 797)),
    ({}, (8043, 0, 0, 8043, 794)),
    (dict(PLAN_LAYOUT, auto_copy_logic_hours=0), (8545, 0, 502, 8043, 778)),
    (dict(PLAN_LAYOUT, perfect_pixel_items="any", auto_copy_logic_hours=0), (8545, 0, 502, 8043, 778)),
    (dict(auto_copy_logic_hours=0), (8043, 0, 0, 8043, 777)),
    (dict(PLAN_LAYOUT, perfect_pixel_items="filler"), (8545, 70, 0, 8475, 797)),
    (dict(PLAN_LAYOUT, perfect_pixel_items="any"), (8545, 0, 0, 8545, 797)),
    # D26's setup, where the family makes 226 progression items for 225 locations that take them, and so 0 h costs one
    (dict(PLAN_LAYOUT, **TIGHT_LAYOUT), (1357, 0, 1132, 225, 226)),
    (dict(PLAN_LAYOUT, **TIGHT_LAYOUT, missed_pixel_checks=0), (1069, 0, 844, 225, 225)),
    (dict(PLAN_LAYOUT, **dict(TIGHT_LAYOUT, auto_copy_logic_hours=6)), (1357, 0, 700, 657, 245)),
    # D21 at its defaults and D26 off, 5 px steps at 0.1% from the start (D26's table): 1,058 progression for 988
    (dict(PLAN_LAYOUT, width_increment=5, height_increment=5, spacing=(50, 70, 0, 100, 100), missed_pixel_checks=0),
     (2378, 0, 1390, 988, 1058)),
    # The most locations any option set makes, at each mode (D26): at filler 32,758 excluded, and 22,328 to spare in
    # the item count (test_the_largest_seed_keeps_room)
    (dict(final_width=16384, final_height=16384, width_increment=20, height_increment=20, logic_percent=99,
          perfect_pixel_checks=20, perfect_pixel_items="filler", timesanity_minutes=1, auto_copy_logic_hours=1,
          missed_pixel_checks=720), (57821, 32758, 0, 25063, 2428)),
    (dict(final_width=16384, final_height=16384, width_increment=20, height_increment=20, logic_percent=99,
          perfect_pixel_checks=20, timesanity_minutes=1, auto_copy_logic_hours=1, missed_pixel_checks=720),
     (57821, 0, 32758, 25063, 2428)),
    (dict(final_width=16384, final_height=16384, width_increment=5, height_increment=5, logic_percent=99,
          perfect_pixel_checks=5, perfect_pixel_items="any", timesanity_minutes=1, auto_copy_logic_hours=1,
          missed_pixel_checks=720), (57821, 0, 0, 57821, 7342)),
]
# D26's setup as options, and D21's at 5 px steps at 0.1% from the start
TIGHT = {"starting_canvas": "half", "canvas_width_increment": 5, "canvas_height_increment": 5,
         "hundredth_percent_checks": 100, "logic_percent": 99, "color_depth_items": 28, "auto_copy_logic_hours": 0,
         **PLAN_FAMILIES}
TENTH_AT_5_PX = {"canvas_width_increment": 5, "canvas_height_increment": 5, "tenth_percent_checks": 0,
                 "hundredth_percent_checks": 100, "perfect_pixel_checks": 5, "timesanity_minutes": 10}
HINT = ("Add checks (hundredth_percent_checks 0 makes one every 0.01%), raise logic_percent, lower color_depth_items, "
        "or use bigger canvas steps.")
# At logic 99, the top, D26's setup has no higher logic_percent to name
TIGHT_HINT = ("Add checks (hundredth_percent_checks 0 makes one every 0.01%), lower color_depth_items, or use bigger "
              "canvas steps.")
AT_0_H = ("Tester1's Pain-T world has 225 locations that take progression for 226 progression items beside the 144 "
          "Auto Copy Time checks, 700 Perfect Pixels checks and 288 Missed Pixels checks, which take no progression "
          f"with auto_copy_logic_hours 0, whatever perfect_pixel_items says. {TIGHT_HINT}")
AT_USEFUL = ("Tester1's Pain-T world has 988 locations that take progression for 1,058 progression items beside the "
             "1,390 Perfect Pixels checks that perfect_pixel_checks 5 makes and perfect_pixel_items useful keeps for "
             f"useful items, filler and traps. {HINT} With perfect_pixel_items any, those 1,390 checks take "
             "progression too, and the progression fits.")
# Every slot data key of version 1.2.0 with the type of its value, and of each entry for a list
INTS = ("logic_percent", "goal_percent", "death_link", "canvas_width_increment", "canvas_height_increment",
        "trap_link", "miss_margin_step", "overclock_seconds", "overclock_bank_size_step", "overclock_fill_speed_step",
        "auto_copy_logic_hours", "timesanity_minutes", "timesanity_hours", "perfect_pixel_checks",
        "missed_pixel_checks", "final_width", "final_height", "start_width", "start_height", "matched_pixels",
        "auto_copy_speed_items")
KEYS = {**{key: (int, None) for key in INTS},
        **{key: (str, None) for key in ("goal_image", "goal_image_sha256", "perfect_pixel_items", "version")},
        **{key: (bool, None) for key in ("ladders", "tool_ladders")},
        "trap_blacklist": (list, str),
        **{key: (list, int) for key in ("shade_counts", "auto_copy_time_targets", "perfect_pixel_targets",
                                        "missed_pixel_targets")}}
# The range of each number a seed can carry: its option's own, and the speed copies the world works out (D19)
RANGES = {"logic_percent": (50, 99), "goal_percent": (50, 99), "death_link": (0, 1), "trap_link": (0, 1),
          "miss_margin_step": (1, 255), "overclock_seconds": (0, 120), "overclock_bank_size_step": (10, 3600),
          "overclock_fill_speed_step": (1, 60), "auto_copy_logic_hours": (0, 24), "timesanity_minutes": (0, 1440),
          "timesanity_hours": (1, 24), "perfect_pixel_checks": (0, 20), "missed_pixel_checks": (0, 720),
          "final_width": (50, 16384), "final_height": (50, 16384), "auto_copy_speed_items": (10, 17)}
# Seeds whose slot data the tests below read: the defaults; the families at the plan's defaults on a 4096x4096 goal
# named by a site path with its hash, death_link on and a trap left out; every family at its top on 16384x16384 at
# 1 h; and the largest half start, 6400x25 on 12800x50, at filler and 0 h
SEEDS = {"defaults": {},
         "the plan's families on 4096x4096": named(4096, 4096, goal_image=SITE_PATH, goal_image_sha256=SHA256,
                                                    death_link=True, trap_blacklist=["Help Trap"], **PLAN_FAMILIES),
         "every family at its top": named(16384, 16384, auto_copy_logic_hours=1, perfect_pixel_checks=20,
                                          perfect_pixel_items="any", timesanity_minutes=1, missed_pixel_checks=720,
                                          canvas_width_increment=20, canvas_height_increment=20, logic_percent=99),
         "a half start of 6400x25 at filler and 0 h": named(12800, 50, starting_canvas="half",
                                                            auto_copy_logic_hours=0, perfect_pixel_checks=3,
                                                            perfect_pixel_items="filler", timesanity_minutes=7,
                                                            timesanity_hours=1, missed_pixel_checks=1)}


LOADED_AS_0_0_0 = ("Tester1's Pain-T world loaded as version 0.0.0: Archipelago read no world_version from its "
                   "archipelago.json. Build paint_hard.apworld with Archipelago's Build APWorlds and generate again.")
# Every name of each family's group, as a YAML's group name reaches the world: Options.py's verify expands it, which
# setup_multiworld skips
PERFECT_NAMES, MARK_NAMES, MISSED_NAMES_ALL = (sorted(location_groups[group]) for group in
                                               ("Perfect Pixels", "Auto Copy Time", "Missed Pixels"))


def progression(setup) -> int:
    """The pool's progression items, as plan_math.room_counts() counts them"""
    return sum(progression_counts(setup)) + happy_count(setup)


def prioritize(multiworld: MultiWorld) -> None:
    """Main.py's step after set_rules, lines 120 to 135: each location priority_locations names becomes a priority
    location, but for the excluded ones, which leave the option"""
    for player in multiworld.player_ids:
        option = multiworld.worlds[player].options.priority_locations
        option.value -= multiworld.worlds[player].options.exclude_locations.value
        excluded = set()
        for name in option.value:
            try:
                location = multiworld.get_location(name, player)
            except KeyError:
                continue
            if location.progress_type != LocationProgressType.EXCLUDED:
                location.progress_type = LocationProgressType.PRIORITY
            else:
                excluded.add(name)
        option.value -= excluded


class TestTheCountOfProgression(unittest.TestCase):
    def test_the_counts_match_the_plan(self) -> None:
        for changes, counts in COUNTS:
            with self.subTest(layout=changes):
                setup = layout(**changes)
                self.assertEqual(counts, (setup.location_count, setup.excluded_count, setup.no_progression_count,
                                          setup.taking_count, progression(setup)))

    def test_the_largest_seed_keeps_room(self) -> None:
        # D26's extremes: at filler the 32,758 excluded checks leave 22,328 locations to spare for the 2,735
        # non-filler items, and 22,635 for the 2,428 progression items. Built beside a second slot.
        options = named(16384, 16384, canvas_width_increment=20, canvas_height_increment=20, logic_percent=99,
                        perfect_pixel_checks=20, perfect_pixel_items="filler", timesanity_minutes=1,
                        auto_copy_logic_hours=1, missed_pixel_checks=720)
        world = generate_early(options, slots=2)
        setup = world.layout
        items = len(world.non_filler_items())
        self.assertEqual((2735, 22328, 22635), (items, setup.location_count - setup.excluded_count - items,
                                                setup.taking_count - progression(setup)))

    def test_with_the_families_off_every_location_takes_progression(self) -> None:
        # So the count never refuses a seed without the families: the item count holds every non-filler item, and the
        # progression items are among them.
        for hours, mode, changes in ((0, "useful", {}), (6, "filler", {}), (24, "any", {}),
                                     (0, "any", dict(spacing=UPSTREAM, width_increment=5, height_increment=5))):
            with self.subTest(auto_copy_logic_hours=hours, perfect_pixel_items=mode, layout=changes):
                setup = layout(**changes, auto_copy_logic_hours=hours, perfect_pixel_items=mode)
                self.assertEqual((0, setup.location_count), (setup.no_progression_count, setup.taking_count))

    def test_happy_accident_counts_while_the_family_is_on(self) -> None:
        # As plan_math.happy_count(), at any hours
        self.assertEqual((0, 1, 1), (happy_count(layout()), happy_count(layout(missed_pixel_checks=1)),
                                     happy_count(layout(missed_pixel_checks=720, auto_copy_logic_hours=0))))

    def test_happy_accident_from_the_pool_needs_no_location(self) -> None:
        # D12 and D26: start inventory counts Happy Accident as it does the other eight kinds, so the copy
        # start_inventory_from_pool takes out of the pool needs no location, where plan_math.happy_count() still counts
        # it. D26's setup at 0 h then fits, 225 progression items for 225 locations. start_inventory leaves the pool's
        # copy, and the seed is refused with 226.
        options = {**TIGHT, "start_inventory_from_pool": {"Happy Accident": 1}}
        world = generate_early(options, slots=2)
        self.assertEqual((1, 0, 225, 225), (world.layout.happy_from_pool, happy_count(world.layout),
                                            progression(world.layout), world.layout.taking_count))
        # A second copy named takes nothing more, and with the family off there is none to take
        self.assertEqual((0, 0), (happy_count(layout(missed_pixel_checks=24, happy_from_pool=2)),
                                  happy_count(layout(happy_from_pool=1))))
        with self.assertRaises(OptionError) as raised:
            generate_early({**TIGHT, "start_inventory": {"Happy Accident": 1}}, slots=2)
        self.assertEqual(AT_0_H, str(raised.exception))
        # The world's pool holds the copy among its 226 progression items, and Main.py takes it out for a filler
        names = [item.name for item in build(options, slots=2).itempool if item.player == 1 and item.advancement]
        self.assertEqual((226, 1), (len(names), names.count("Happy Accident")))
        # A refusal's sample counts it the same way: from 6 h, 0 h fits once the copy comes from the pool
        tight = layout(**PLAN_LAYOUT, **dict(TIGHT_LAYOUT, auto_copy_logic_hours=6), happy_from_pool=1)
        with mock.patch.object(rules, "fills", return_value=True):
            self.assertTrue(change_fills(tight, replace(tight, auto_copy_logic_hours=0), 552))

    def test_it_refuses_solo_or_not(self) -> None:
        # D26's setup fails by one at 0 h, where no check of the three families takes progression, and fits with the
        # family off. Above 0 h only the Perfect Pixels checks at useful turn it away: D21's 1,058 progression items
        # for 988 locations fit at any.
        for slots in (1, 2):
            for options, message in ((TIGHT, AT_0_H), (TENTH_AT_5_PX, AT_USEFUL)):
                with self.subTest(options=options, slots=slots):
                    with self.assertRaises(OptionError) as raised:
                        generate_early(options, slots)
                    self.assertEqual(message, str(raised.exception))
        for options, counts in (({**TIGHT, "missed_pixel_checks": 0}, (225, 225)),
                                ({**TENTH_AT_5_PX, "perfect_pixel_items": "any"}, (1058, 2378))):
            with self.subTest(options=options):
                setup = generate_early(options, slots=2).layout
                self.assertEqual(counts, (progression(setup), setup.taking_count))
        # Both counts with commas, as the message's other numbers: with a mark every 9 minutes, 160 marks and 844
        # similarity checks and Matched Pixels take progression
        with self.assertRaisesRegex(OptionError, r"has 1,004 locations that take progression for 1,058 progression "
                                                 r"items beside the 1,390 Perfect Pixels checks"):
            generate_early({**TENTH_AT_5_PX, "timesanity_minutes": 9}, slots=2)

    def test_each_family_is_named_as_it_turns_progression_away(self) -> None:
        # At 0 h each family the seed has, the Perfect Pixels checks whatever perfect_pixel_items says, since at filler
        # they are excluded. Above 0 h at any, nothing turns progression away.
        for changes, beside in (
                (dict(missed_pixel_checks=0, timesanity_minutes=0, color_depth_items=29),
                 "228 progression items beside the 700 Perfect Pixels checks, which take no progression with "
                 "auto_copy_logic_hours 0, whatever perfect_pixel_items says."),
                (dict(perfect_pixel_checks=0, missed_pixel_checks=0, timesanity_minutes=1, color_depth_items=29),
                 "228 progression items beside the 1,440 Auto Copy Time checks, which take no progression with "
                 "auto_copy_logic_hours 0."),
                (dict(perfect_pixel_items="filler"),
                 "226 progression items beside the 144 Auto Copy Time checks, 700 Perfect Pixels checks and 288 "
                 "Missed Pixels checks, which take no progression with auto_copy_logic_hours 0, whatever "
                 "perfect_pixel_items says."),
                (dict(perfect_pixel_items="any"),
                 "226 progression items beside the 144 Auto Copy Time checks, 700 Perfect Pixels checks and 288 "
                 "Missed Pixels checks, which take no progression with auto_copy_logic_hours 0, whatever "
                 "perfect_pixel_items says.")):
            with self.subTest(changes=changes):
                with self.assertRaises(OptionError) as raised:
                    generate_early({**TIGHT, **changes}, slots=2)
                self.assertIn(f"has 225 locations that take progression for {beside} Add checks",
                              str(raised.exception))
        world = generate_early({**TENTH_AT_5_PX, "perfect_pixel_items": "any"}, slots=2)
        self.assertEqual(0, world.layout.no_progression_count)

    def test_it_comes_after_the_item_count_and_before_the_fill_check(self) -> None:
        # Paint's spacing at 100 px with the families on fails both counts (D12: 797 progression items for 606
        # locations that take them), and the item count speaks first. Alone, D26's setup is the fill check's to refuse
        # too, 0 of 3, and the count speaks before it.
        with self.assertRaisesRegex(OptionError, r"has 676 locations for 1104 required items\."):
            generate_early({"hundredth_percent_checks": 100, **PLAN_FAMILIES}, slots=2)
        self.assertEqual((0, 3), passes_filled(layout(**PLAN_LAYOUT, **TIGHT_LAYOUT)))
        with self.assertRaises(OptionError) as raised:
            generate_early(TIGHT)
        self.assertEqual(AT_0_H, str(raised.exception))

    def test_the_item_count_names_a_step_only_where_the_progression_fits(self) -> None:
        # Margin copies are useful, so no miss_margin_step moves task 8.3's count. At 0 h with a mark every 3 minutes
        # and 24 Missed Pixels checks a speed copy at Paint's spacing, step 3 fits the item count's 942 locations, and
        # 8.3's count then refuses 778 progression items for the 174 locations that take them: the item count names
        # no step. At 6 h every check takes progression, and the step it names passes both counts.
        at_0_h = {"hundredth_percent_checks": 100, "auto_copy_logic_hours": 0, "timesanity_minutes": 3,
                  "missed_pixel_checks": 24}
        with self.assertRaises(OptionError) as raised:
            generate_early(at_0_h, slots=2)
        message = str(raised.exception)
        self.assertTrue(message.startswith("Tester1's Pain-T world has 942 locations for 1104 required items."),
                        message)
        self.assertTrue(message.endswith(" With miss_margin_step 255, 254 more stay out."), message)
        with self.assertRaisesRegex(OptionError, r"has 174 locations that take progression for 778 progression items"):
            generate_early({**at_0_h, "miss_margin_step": 3}, slots=2)
        at_6_h = {**at_0_h, "auto_copy_logic_hours": 6}
        with self.assertRaisesRegex(OptionError, r" With miss_margin_step 255, 254 more stay out, and with nothing "
                                                 r"else changed the items fit from miss_margin_step 3\.$"):
            generate_early(at_6_h, slots=2)
        setup = generate_early({**at_6_h, "miss_margin_step": 3}, slots=2).layout
        self.assertEqual((797, 942), (progression(setup), setup.taking_count))
        # At the edge, where the progression fills the locations that take it exactly, it names a step: 20 px steps at
        # logic 82, 100 color items, 0 h, 20 Perfect Pixels checks a step at filler, 24 Missed Pixels checks a speed
        # copy, 7 Overclock bank size and 10 fill speed items and spacing 50/0/100/100/99 have 705 items for 660
        # locations and 372 progression items for the 372 locations that take them. Step 2 passes both counts.
        edge = {"canvas_width_increment": 20, "canvas_height_increment": 20, "logic_percent": 82,
                "color_depth_items": 100, "auto_copy_logic_hours": 0, "perfect_pixel_checks": 20,
                "perfect_pixel_items": "filler", "missed_pixel_checks": 24, "overclock_bank_size_items": 7,
                "overclock_fill_speed_items": 10, "quarter_percent_checks": 0, "hundredth_percent_checks": 99}
        with self.assertRaisesRegex(OptionError, r"^Tester1's Pain-T world has 660 locations for 705 required items "
                                                 r".* With miss_margin_step 255, 254 more stay out, and with nothing "
                                                 r"else changed the items fit from miss_margin_step 2\. "):
            generate_early(edge, slots=2)
        setup = generate_early({**edge, "miss_margin_step": 2}, slots=2).layout
        self.assertEqual((372, 372), (progression(setup), setup.taking_count))
        # One past the edge: 101 color items, with one red and one green taken from the pool, make 708 items for the
        # 660 locations and 373 progression items for the 372 locations that take them. The item count names no step,
        # and at step 2 task 8.3's count refuses the seed.
        past = {**edge, "color_depth_items": 101,
                "start_inventory_from_pool": {"Progressive Color Depth (Red)": 1, "Progressive Color Depth (Green)": 1}}
        with self.assertRaises(OptionError) as raised:
            generate_early(past, slots=2)
        message = str(raised.exception)
        self.assertTrue(message.startswith("Tester1's Pain-T world has 660 locations for 708 required items "), message)
        self.assertTrue(message.endswith(" With miss_margin_step 255, 254 more stay out."), message)
        with self.assertRaisesRegex(OptionError, r"^Tester1's Pain-T world has 372 locations that take progression for "
                                                 r"373 progression items "):
            generate_early({**past, "miss_margin_step": 2}, slots=2)

    def test_the_advice_names_what_the_options_leave_room_for(self) -> None:
        # Both counts name a check every 0.01% from the start while hundredth_percent_checks is above 0, a higher
        # logic_percent below its top of 99, fewer color items above the least, 7, and bigger canvas steps below
        # 100 px: test_freeze's HINT has all four.
        for changes, hint in (
                (dict(spacing=UPSTREAM, width_increment=5), HINT),
                ({}, "Raise logic_percent or lower color_depth_items."),
                (dict(spacing=UPSTREAM), "Add checks (hundredth_percent_checks 0 makes one every 0.01%), raise "
                                         "logic_percent, or lower color_depth_items."),
                (TIGHT_LAYOUT, TIGHT_HINT),
                (dict(logic_percent=99, color_depth_items=7, height_increment=50), "Use bigger canvas steps."),
                (dict(logic_percent=99, color_depth_items=7), "")):
            for count in ("items", "progression"):
                with self.subTest(layout=changes, count=count):
                    self.assertEqual(f" {hint}" if hint else "", fewer_items_hint(layout(**changes), count))
        # While Perfect Pixels checks take items, at useful or any, the item count names bigger steps up to the biggest
        # step at or below perfect_pixel_checks, where that step is above the smaller of the seed's two: each step of
        # a side brings one canvas item and min(perfect_pixel_checks, step) such checks, so up to there each line of
        # pixels keeps its check and a bigger step drops canvas items alone. Every change the hint allows, on one side
        # or both, shortens the item count's shortfall, and where it names no step no bigger step does. Task 8.3's
        # count names any bigger step, and so does the item count with the checks off or at filler.
        paints_5_px = dict(spacing=UPSTREAM, width_increment=5, height_increment=5)
        no_step = ("Add checks (hundredth_percent_checks 0 makes one every 0.01%), raise logic_percent, or lower "
                   "color_depth_items.")
        up_to = ("Add checks (hundredth_percent_checks 0 makes one every 0.01%), raise logic_percent, lower "
                 "color_depth_items, or use bigger canvas steps up to {} px.")
        for changes, top in ((dict(perfect_pixel_checks=2), 0),
                             (dict(perfect_pixel_checks=2, perfect_pixel_items="any"), 0),
                             (dict(perfect_pixel_checks=1), 0),
                             (dict(perfect_pixel_checks=9, perfect_pixel_items="any"), 0),
                             (dict(perfect_pixel_checks=10), 10),
                             (dict(perfect_pixel_checks=19, perfect_pixel_items="any"), 10),
                             (dict(perfect_pixel_checks=20, perfect_pixel_items="any"), 20),
                             (dict(perfect_pixel_checks=20, width_increment=10, height_increment=10), 20),
                             (dict(perfect_pixel_checks=19, width_increment=10, height_increment=10), 0),
                             (dict(perfect_pixel_checks=20, width_increment=50, perfect_pixel_items="any"), 20),
                             (dict(perfect_pixel_checks=20, width_increment=20, height_increment=25), 0)):
            with self.subTest(layout=changes):
                setup = layout(**{**paints_5_px, **changes})
                self.assertEqual((f" {up_to.format(top) if top else no_step}", f" {HINT}"),
                                 (fewer_items_hint(setup, "items"), fewer_items_hint(setup, "progression")))
                steps = (setup.width_increment, setup.height_increment)
                before = sum(setup.canvas_items) - len(setup.perfect_thresholds)
                for other in [replace(setup, width_increment=width, height_increment=height)
                              for width in INCREMENTS for height in INCREMENTS
                              if width >= steps[0] and height >= steps[1] and (width, height) != steps]:
                    after = (other.width_increment, other.height_increment)
                    shorter = sum(other.canvas_items) - len(other.perfect_thresholds) < before
                    if all(new == old or new <= top for new, old in zip(after, steps)):
                        self.assertTrue(shorter, after)
                    if not top:
                        self.assertFalse(shorter, after)
        for changes in (dict(perfect_pixel_checks=20, perfect_pixel_items="filler"), {}):
            with self.subTest(layout=changes):
                setup = layout(**{**paints_5_px, **changes})
                self.assertEqual((f" {HINT}", f" {HINT}"),
                                 (fewer_items_hint(setup, "items"), fewer_items_hint(setup, "progression")))
        # A 600x460 goal from the 5x5 start at Paint's spacing with 20 Perfect Pixels checks a step at any, beside a
        # second slot: in 5 px steps 1,224 locations for 1,299 items, and the message names steps up to 20 px. 10 and
        # 20 px steps keep the 1,050 checks, one for each line of pixels, and bring the canvas items from 210 to 106 and
        # 53: 1,195 and 1,142 items then fit. 25 px steps make 840 checks and leave 1,014 locations for 1,132 items.
        goal = named(600, 460, hundredth_percent_checks=100, perfect_pixel_checks=20, perfect_pixel_items="any")
        with self.assertRaises(OptionError) as raised:
            generate_early({**goal, "canvas_width_increment": 5, "canvas_height_increment": 5}, slots=2)
        self.assertTrue(str(raised.exception).startswith(f"Tester1's Pain-T world has 1224 locations for 1299 required "
                                                         f"items. {up_to.format(20)} With tool_size_ladders off"),
                        str(raised.exception))
        for step, counts in ((10, (1195, 1224, 1050, 106)), (20, (1142, 1224, 1050, 53))):
            with self.subTest(step=step):
                world = generate_early({**goal, "canvas_width_increment": step, "canvas_height_increment": step},
                                       slots=2)
                self.assertEqual(counts, (len(world.non_filler_items()), world.layout.location_count,
                                          len(world.layout.perfect_thresholds), sum(world.layout.canvas_items)))
        with self.assertRaisesRegex(OptionError, r"^Tester1's Pain-T world has 1014 locations for 1132 required "
                                                 r"items\."):
            generate_early({**goal, "canvas_width_increment": 25, "canvas_height_increment": 25}, slots=2)
        # Paint's spacing in 5 px steps with 2 Perfect Pixels checks a step at useful, beside a second slot: 730
        # locations for 1,367 items, 637 short, and in 100 px steps 202 for 1,103, 901 short. At 1 a step it is 915
        # short in both. With the checks off, 100 px steps bring 1,193 short to 929.
        paints = {"hundredth_percent_checks": 100}
        for checks, counts in ((2, ((730, 1367), (202, 1103))), (1, ((452, 1367), (188, 1103))),
                               (0, ((174, 1367), (174, 1103)))):
            with self.subTest(perfect_pixel_checks=checks):
                messages = []
                for step in (5, 100):
                    with self.assertRaises(OptionError) as raised:
                        generate_early({**paints, "perfect_pixel_checks": checks, "canvas_width_increment": step,
                                        "canvas_height_increment": step}, slots=2)
                    messages.append(str(raised.exception))
                for message, (locations, items) in zip(messages, counts):
                    self.assertTrue(message.startswith(f"Tester1's Pain-T world has {locations} locations for {items} "
                                                       f"required items. "), message)
                advice = no_step if checks else HINT
                self.assertTrue(messages[0].startswith(f"Tester1's Pain-T world has {counts[0][0]} locations for "
                                                       f"1367 required items. {advice} With tool_size_ladders off"),
                                messages[0])
        # A 16384x16384 goal in 5 px steps at logic 50 and 0 h, at the default hundredth_percent_checks 0: with a mark
        # every minute and 720 Missed Pixels checks a speed copy task 8.3's count refuses it, and without them the item
        # count. Neither names hundredth_percent_checks.
        big = named(16384, 16384, canvas_width_increment=5, canvas_height_increment=5, logic_percent=50,
                    auto_copy_logic_hours=0)
        for options, counts in (({**big, "timesanity_minutes": 1, "missed_pixel_checks": 720},
                                 "has 5,043 locations that take progression for 7,316 progression items beside the "
                                 "1,440 Auto Copy Time checks and 11,520 Missed Pixels checks, which take no "
                                 "progression with auto_copy_logic_hours 0."),
                                (big, "has 5043 locations for 7645 required items.")):
            with self.subTest(options=options):
                with self.assertRaises(OptionError) as raised:
                    generate_early(options, slots=2)
                self.assertIn(f"{counts} Raise logic_percent, lower color_depth_items, or use bigger canvas steps.",
                              str(raised.exception))
                self.assertNotIn("hundredth_percent_checks", str(raised.exception))

    def test_no_message_names_missed_pixel_checks(self) -> None:
        # Until task 8.10's real seeds back the family's reach (D12, D26): the count's messages as generate_early gives
        # them with the family on, at 0 h with D26's setup and at 6 h with 12 Missed Pixels checks beside 1,390
        # Perfect Pixels at useful, solo and beside a second slot
        messages = []
        for options in (TIGHT, {**TENTH_AT_5_PX, "timesanity_minutes": 0, "missed_pixel_checks": 1}):
            for slots in (1, 2):
                with self.subTest(options=options, slots=slots):
                    with self.assertRaisesRegex(OptionError, "locations that take progression for") as raised:
                        generate_early(options, slots)
                    messages.append(str(raised.exception))
        self.assertEqual((4, []), (len(messages),
                                   [message for message in messages if "missed_pixel_checks" in message]))

    def test_a_refusals_sample_counts_it(self) -> None:
        # A change the solo refusal names has to pass the count too: at Paint's spacing with 720 Missed Pixels checks a
        # speed copy, 8,640 of them take progression at 6 h and none at 0 h, where 778 progression items need the 174
        # similarity checks. The fill check stands aside here, so only the counts decide.
        setup = layout(spacing=UPSTREAM, missed_pixel_checks=720)
        at_0_h = replace(setup, auto_copy_logic_hours=0)
        self.assertEqual(((8814, 797), (174, 778)), ((setup.taking_count, progression(setup)),
                                                     (at_0_h.taking_count, progression(at_0_h))))
        with mock.patch.object(rules, "fills", return_value=True):
            self.assertEqual((True, False), (change_fills(setup, replace(setup, auto_copy_logic_hours=24), 1104),
                                             change_fills(setup, at_0_h, 1104)))
        # D26's setup from 6 h: at 0 h the progression fits exactly with the family off, 225 items for 225 locations,
        # and with the family on Happy Accident alone is one too many
        tight = layout(**PLAN_LAYOUT, **dict(TIGHT_LAYOUT, auto_copy_logic_hours=6))
        off = replace(tight, missed_pixel_checks=0)
        self.assertEqual(((225, 225), (226, 225)),
                         ((progression(replace(off, auto_copy_logic_hours=0)),
                           replace(off, auto_copy_logic_hours=0).taking_count),
                          (progression(replace(tight, auto_copy_logic_hours=0)),
                           replace(tight, auto_copy_logic_hours=0).taking_count)))
        with mock.patch.object(rules, "fills", return_value=True):
            self.assertEqual((True, False), (change_fills(off, replace(off, auto_copy_logic_hours=0), 551),
                                             change_fills(tight, replace(tight, auto_copy_logic_hours=0), 552)))


class TestTheStopgap(unittest.TestCase):
    def test_the_plan_defaults_pass_alone(self) -> None:
        # The fill check still places progression on the similarity checks and Matched Pixels alone: at the plan's
        # defaults its pool has every speed copy and no Happy Accident, its locations are the 8,043 of the seed's
        # 8,545, and it passes 3 of 3. The item count has D12's 1,104 items in 8,545 locations, and task 8.3's count
        # 797 progression items for 8,475 locations that take them, 8,545 at any. Each mode alone.
        for mode in ("useful", "filler", "any"):
            with self.subTest(perfect_pixel_items=mode):
                world = generate_early({**PLAN_FAMILIES, "perfect_pixel_items": mode})
                setup = world.layout
                self.assertEqual((254, 254, 254, 8, 6, 10, 9, 1), progression_counts(setup))
                self.assertEqual((8043, 8545, 1104, 797, 8545 if mode == "any" else 8475),
                                 (len(location_percents(setup)), setup.location_count, len(world.non_filler_items()),
                                  progression(setup), setup.taking_count))
                self.assertEqual((3, 3), passes_filled(setup))

    def test_the_plan_defaults_seed(self) -> None:
        # Built through create_items: 8,545 locations and as many items, 1,104 of them neither filler nor trap and 797
        # progression, Happy Accident and all 10 speed copies among them
        multiworld = build(PLAN_FAMILIES)
        pool = multiworld.itempool
        progression_items = [item.name for item in pool if item.advancement]
        self.assertEqual((8545, 8545), (len(multiworld.get_locations(1)), len(pool)))
        self.assertEqual((1104, 797, 1, 10), (
            len([item for item in pool if item.classification not in (ItemClassification.filler,
                                                                      ItemClassification.trap)]),
            len(progression_items), progression_items.count("Happy Accident"),
            progression_items.count("Progressive Auto Copy Speed")))


class TestSlotData(unittest.TestCase):
    def test_every_key_and_its_shape(self) -> None:
        # The 32 keys of version 1.2.0 on every seed, each value of its own type: a number is an int and never a bool,
        # a list holds ints or strings alone, and the whole survives JSON as the server sends it. The defaults are
        # built through create_items, the others through generate_early beside a second slot.
        for name, options in SEEDS.items():
            with self.subTest(seed=name):
                world = build(options).worlds[1] if name == "defaults" else generate_early(options, slots=2)
                slot_data = world.fill_slot_data()
                self.assertEqual(sorted(KEYS), sorted(slot_data))
                for key, (kind, entry) in KEYS.items():
                    value = slot_data[key]
                    self.assertIs(kind, type(value), key)
                    if entry:
                        self.assertEqual([], [item for item in value if type(item) is not entry], key)
                for key, (least, most) in RANGES.items():
                    self.assertTrue(least <= slot_data[key] <= most, (key, slot_data[key]))
                self.assertEqual(slot_data, json.loads(json.dumps(slot_data)))

    def test_what_each_value_holds(self) -> None:
        for name, options in SEEDS.items():
            with self.subTest(seed=name):
                world = generate_early(options, slots=2)
                slot_data, setup = world.fill_slot_data(), world.layout
                self.assertEqual("1.2.0", slot_data["version"])
                self.assertLessEqual({slot_data["canvas_width_increment"], slot_data["canvas_height_increment"]},
                                     {5, 10, 20, 25, 50, 100})
                self.assertIn(slot_data["perfect_pixel_items"], ("useful", "filler", "any"))
                self.assertEqual((True, bool(world.options.tool_size_ladders.value)),
                                 (slot_data["ladders"], slot_data["tool_ladders"]))
                sha256 = slot_data["goal_image_sha256"]
                self.assertTrue(sha256 == "" or (len(sha256) == 64 and set(sha256) <= set(hexdigits.lower())))
                self.assertEqual("goal_image" not in options, slot_data["goal_image"] == "default")
                self.assertTrue(set(slot_data["trap_blacklist"]) <= set(traps))
                self.assertEqual(sorted(slot_data["trap_blacklist"]), slot_data["trap_blacklist"])
                start = (slot_data["start_width"], slot_data["start_height"])
                final = (slot_data["final_width"], slot_data["final_height"])
                self.assertIn(start, ((5, 5), (final[0] // 2, final[1] // 2)))
                self.assertEqual(25 if start == (5, 5) else 0, slot_data["matched_pixels"])
                shades = slot_data["shade_counts"]
                self.assertEqual((world.options.color_depth_items.value + 1, 2, 256),
                                 (len(shades), shades[0], shades[-1]))
                self.assertEqual(setup.speed_items, slot_data["auto_copy_speed_items"])
                # Each family's targets rise, one for each of its locations, every mark within 24 h, and the last
                # Perfect Pixels target is the whole goal
                for key, targets in (("auto_copy_time_targets", setup.marks),
                                     ("perfect_pixel_targets", setup.perfect_thresholds),
                                     ("missed_pixel_targets", setup.missed_targets)):
                    self.assertEqual(sorted(set(targets)), slot_data[key])
                if setup.perfect_thresholds:
                    self.assertEqual(final[0] * final[1], slot_data["perfect_pixel_targets"][-1])
                self.assertTrue(all(1 <= minutes <= 1440 for minutes in slot_data["auto_copy_time_targets"]))

    def test_a_client_tells_a_seed_with_each_family_from_one_without(self) -> None:
        # By slot data alone, on one version: each family's list of targets has one for each of its locations in the
        # seed, so an empty list means none. An option can be on and make none: on 50x50 the marks stop at 20 minutes,
        # the goal's pixels / 120. Happy Accident is in the pool exactly when missed_pixel_targets has a target.
        blocks = (("auto_copy_time_targets", TIME_BASE, TIME_MARKS), ("perfect_pixel_targets", PERFECT_BASE,
                                                                      PERFECT_MOST),
                  ("missed_pixel_targets", MISSED_BASE, MISSED_NAMES))
        for options, on in (({}, (False, False, False)), ({"perfect_pixel_checks": 5}, (False, True, False)),
                            ({"timesanity_minutes": 10}, (True, False, False)),
                            ({"missed_pixel_checks": 24}, (False, False, True)), (PLAN_FAMILIES, (True, True, True)),
                            ({"perfect_pixel_items": "any", "timesanity_hours": 6}, (False, False, False)),
                            (named(50, 50, timesanity_minutes=30), (False, False, False))):
            with self.subTest(options=options):
                multiworld = build(options)
                slot_data = multiworld.worlds[1].fill_slot_data()
                addresses = [location.address for location in multiworld.get_locations(1)]
                for (key, base, most), family_on in zip(blocks, on):
                    made = sorted(address - base for address in addresses if base < address <= base + most)
                    if key == "auto_copy_time_targets":
                        self.assertEqual(made, slot_data[key])  # a mark's id is 2,209,000 plus its minutes
                    else:
                        self.assertEqual(list(range(1, len(slot_data[key]) + 1)), made)
                    self.assertEqual(family_on, bool(slot_data[key]), key)
                happy = [item.name for item in multiworld.itempool].count("Happy Accident")
                self.assertEqual((int(on[2]), "1.2.0"), (happy, slot_data["version"]))

    def test_the_contract_holds_every_key(self) -> None:
        # client_contract.json, which the client's tests read, holds the 32 keys and no key waits to go into it. Its
        # logic part still comes from a seed with the Missed Pixels off, where 8 speed copies are progression and 2
        # useful, and all 9 accuracy copies progression.
        written = json.loads(test_client_contract.CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(sorted(KEYS), written["slot_data_keys"])
        self.assertFalse(hasattr(test_client_contract, "NOT_IN_THE_FILE_YET"))
        self.assertEqual((8, 9, 10), (written["logic"]["speed_progression"], written["logic"]["accuracy_progression"],
                                      written["slot_data"]["auto_copy_speed_items"]))
        self.assertEqual(([], [], [], 0), tuple(written["slot_data"][key] for key in (
            "auto_copy_time_targets", "perfect_pixel_targets", "missed_pixel_targets", "missed_pixel_checks")))

    def test_the_contract_gives_each_familys_ids(self) -> None:
        # client_contract.json gives each location block its base, first and last id and first name, as
        # test_data_package.py has them, and each family the list of its slot data that names a seed's checks, the rule
        # from an entry to its check's id and what an entry counts: a mark's id is the base plus its minutes, and a
        # Perfect or Missed Pixels check's the base plus its place in the list, from 1. The seed with every family on,
        # a mark every 10 minutes, turns each list into its own ids by its rule alone, and by the other rule into ids
        # the seed doesn't make.
        written = json.loads(test_client_contract.CONTRACT.read_text(encoding="utf-8"))
        blocks = written["locations"]
        self.assertEqual([(first, last, first_name) for _, first, last, first_name, _ in BLOCKS],
                         [(block["first_id"], block["last_id"], block["first_name"]) for block in blocks.values()])
        self.assertEqual([EARLY_BASE, MATCHED_BASE, LOCATION_BASE, TIME_BASE, PERFECT_BASE, MISSED_BASE],
                         [block["base"] for block in blocks.values()])
        families = {"auto_copy_time": ("auto_copy_time_targets", "base + target", "minutes"),
                    "perfect_pixels": ("perfect_pixel_targets", "base + place in the list, from 1", "exact pixels"),
                    "missed_pixels": ("missed_pixel_targets", "base + place in the list, from 1", "wrong pixels")}
        self.assertEqual(families, {name: (block["targets"], block["id"], block["unit"])
                                    for name, block in blocks.items() if "targets" in block})
        options, _ = test_client_contract.SEEDS["every_family"]
        changes = written["logic"]["slot_data_changes"]["every_family"]
        self.assertEqual((options["perfect_pixel_checks"], options["timesanity_minutes"],
                          options["missed_pixel_checks"]),
                         (changes["perfect_pixel_checks"], changes["timesanity_minutes"],
                          changes["missed_pixel_checks"]))
        addresses = {location.address for location in build(options).get_locations(1)}
        for name, (key, rule, _) in families.items():
            with self.subTest(family=name):
                base, entries = blocks[name]["base"], changes[key]
                by_target = [base + entry for entry in entries]
                by_place = [base + place for place in range(1, len(entries) + 1)]
                made = sorted(address for address in addresses if base < address <= blocks[name]["last_id"])
                self.assertEqual(made, by_target if rule == "base + target" else by_place)
                self.assertNotEqual(made, by_place if rule == "base + target" else by_target)


class TestTheLoadedVersion(unittest.TestCase):
    def test_a_world_loaded_without_its_version_is_refused(self) -> None:
        # The core sets world_version from the manifest it reads, and an .apworld zipped by hand leaves it at 0.0.0,
        # which a seed would carry to the client. generate_early refuses that first, solo or not, ahead of every other
        # refusal: goal_width set without goal_height gets the version's message too. Loaded from this folder, the
        # world is 1.2.0.
        self.assertEqual(Version(1, 2, 0), PaintHardWorld.world_version)
        for options in ({}, {"goal_width": 4096}):
            for slots in (1, 2):
                with self.subTest(options=options, slots=slots):
                    with mock.patch.object(PaintHardWorld, "world_version", Version(0, 0, 0)):
                        with self.assertRaises(OptionError) as raised:
                            generate_early(options, slots)
                    self.assertEqual(LOADED_AS_0_0_0, str(raised.exception))
        self.assertEqual("1.2.0", generate_early({}).fill_slot_data()["version"])
        with self.assertRaisesRegex(OptionError, r"^Tester1's Pain-T world sets goal_width 4096 without goal_height\."):
            generate_early({"goal_width": 4096})


class TestPriorityLocations(unittest.TestCase):
    def test_a_check_that_takes_no_progression_leaves_them(self) -> None:
        # Archipelago's priority fill places only progression and stops the whole generation on a priority location it
        # can't fill. generate_early takes out the seed's checks that take no progression, one warning for each family:
        # the Perfect Pixels checks at useful or filler, and every family's checks at 0 h. A check that takes
        # progression stays, and so does a name the seed doesn't make, which Main.py skips. The plan's families: 144
        # marks, 70 Perfect Pixels and 288 Missed Pixels checks.
        names = PERFECT_NAMES + MARK_NAMES + MISSED_NAMES_ALL + ["Similarity: 1.0%"]
        seed_perfect = {f"Perfect Pixels #{k}" for k in range(1, 71)}
        seed_marks = {f"Auto Copy Time: {m // 60}:{m % 60:02d}" for m in range(10, 1441, 10)}
        seed_missed = {f"Missed Pixels #{j}" for j in range(1, 289)}

        def warning(count: int, family: str, setting: str) -> str:
            return (f"WARNING:root:Unable to prioritize {count} {family} locations in player 1's world because they "
                    f"take no progression with {setting}.")

        for changes, dropped, warnings in (
                ({"perfect_pixel_items": "useful"}, seed_perfect,
                 [warning(70, "Perfect Pixels", "perfect_pixel_items useful")]),
                ({"perfect_pixel_items": "filler"}, seed_perfect,
                 [warning(70, "Perfect Pixels", "perfect_pixel_items filler")]),
                ({"perfect_pixel_items": "any"}, set(), []),
                ({"perfect_pixel_items": "any", "auto_copy_logic_hours": 0}, seed_marks | seed_perfect | seed_missed,
                 [warning(144, "Auto Copy Time", "auto_copy_logic_hours 0"),
                  warning(70, "Perfect Pixels", "auto_copy_logic_hours 0"),
                  warning(288, "Missed Pixels", "auto_copy_logic_hours 0")]),
                ({"perfect_pixel_items": "useful", "auto_copy_logic_hours": 0}, seed_marks | seed_perfect | seed_missed,
                 [warning(144, "Auto Copy Time", "auto_copy_logic_hours 0"),
                  warning(70, "Perfect Pixels", "perfect_pixel_items useful"),
                  warning(288, "Missed Pixels", "auto_copy_logic_hours 0")])):
            with self.subTest(changes=changes):
                options = {**PLAN_FAMILIES, **changes, "priority_locations": names}
                if warnings:
                    with self.assertLogs(level=logging.WARNING) as logs:
                        world = generate_early(options, slots=2)
                    self.assertEqual(warnings, logs.output)
                else:
                    with self.assertNoLogs(level=logging.WARNING):
                        world = generate_early(options, slots=2)
                self.assertEqual(set(names) - dropped, world.options.priority_locations.value)
        # One check alone takes the singular
        with self.assertLogs(level=logging.WARNING) as logs:
            generate_early({**PLAN_FAMILIES, "priority_locations": ["Perfect Pixels #1"]}, slots=2)
        self.assertEqual(["WARNING:root:Unable to prioritize 1 Perfect Pixels location in player 1's world because "
                          "it takes no progression with perfect_pixel_items useful."], logs.output)

    def test_a_priority_fill_beside_them_fills(self) -> None:
        # Main.py's step and Archipelago's fill, solo at seed 1, with every Perfect Pixels check named at useful and
        # every mark at 0 h, beside a similarity check: the fill stopped with a FillError, "No more spots to place",
        # and now the similarity check alone is a priority location, gets progression, and every location is reached.
        for options in ({"perfect_pixel_checks": 5, "priority_locations": PERFECT_NAMES + ["Similarity: 1.0%"]},
                        {"timesanity_minutes": 10, "auto_copy_logic_hours": 0,
                         "priority_locations": MARK_NAMES + ["Similarity: 1.0%"]}):
            with self.subTest(options={key: value for key, value in options.items() if key != "priority_locations"}):
                with self.assertLogs(level=logging.WARNING):
                    multiworld = setup_multiworld(PaintHardWorld, seed=1, options=options)
                    prioritize(multiworld)
                    priority = [location.name for location in multiworld.get_locations(1)
                                if location.progress_type == LocationProgressType.PRIORITY]
                    distribute_items_restrictive(multiworld)
                self.assertEqual(["Similarity: 1.0%"], priority)
                self.assertTrue(multiworld.get_location("Similarity: 1.0%", 1).item.advancement)
                self.assertTrue(reaches_every_location(multiworld))

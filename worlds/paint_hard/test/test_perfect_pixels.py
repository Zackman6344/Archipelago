"""Perfect Pixels (D21, task 8.1) against hard-fork/plan_math.py: the targets a seed makes, the rule that holds every
check until each color item is held and then follows the canvas and auto copy's budget, what perfect_pixel_items lets
the checks hold, the checks in a seed with their ids and slot data, the item count at filler, the solo refusal, and
Archipelago's fill in each mode, alone and beside a second slot. In this release the checks are off by default
(test_check_families.py).
"""
import hashlib
import itertools
import json
import re
import unittest
from bisect import bisect_right
from collections import Counter
from dataclasses import replace
from unittest import mock

from BaseClasses import CollectionState, Item, ItemClassification, LocationProgressType, MultiWorld
from Fill import distribute_items_restrictive
from Options import OptionError
from test.general import setup_multiworld
from worlds.AutoWorld import call_all

from . import PaintHardTestBase
from .. import PaintHardWorld, location_exists_with_options, rules
from ..locations import PERFECT_BASE, PerfectPixelsLocation, perfect_table
from ..rules import (PERFECT_MOST, change_fills, happy_count, passes_filled, perfect_in_logic, progression_counts,
                     refusal)
from .test_auto_copy_logic import layout
from .test_auto_copy_time import build
from .test_goal_options import generate_early, named

HALF_START = dict(start_width=400, start_height=300)
STEPS_5 = dict(width_increment=5, height_increment=5)
BIGGEST = dict(final_width=16384, final_height=16384)
# plan_math.perfect_thresholds() for (layout changes, perfect_pixel_checks): how many targets, the first three, the
# last two, and the SHA-256 of the whole list written as numbers joined by commas
TARGETS = [
    ({}, 5, 70, (125, 625, 1125), (468000, 480000),
     "be5ebe169d7cc3b3ba523f8fa4495681e56e1332ac60a064e51f2674175fc771"),
    (dict(width_increment=25, height_increment=25), 5, 278, (50, 100, 150), (476000, 480000),
     "0a8607a26415ed09c93021e6c2d0049052e4a076569f13135d1a0e53a9b14774"),
    (STEPS_5, 5, 1390, (30, 36, 42), (479200, 480000),
     "be37fa1c35dc9a23488f7483cad8e2fc809997c85c0bc8399c336174b7f076f6"),
    # Never finer than a line of pixels: 20 a step at 5 px steps makes the same 1,390
    (STEPS_5, 20, 1390, (30, 36, 42), (479200, 480000),
     "be37fa1c35dc9a23488f7483cad8e2fc809997c85c0bc8399c336174b7f076f6"),
    (HALF_START, 5, 35, (126000, 134400, 140800), (464000, 480000),
     "1ab4633485c2f96967868f8715f8bb2fa5257732b1c83728d05e575d5571cd37"),
    ({}, 1, 14, (525, 11025, 21525), (404000, 480000),
     "b364a453d662758b0ef5a43c333afc75b1e0ea4d72dc1fc8a2603e9a609635ac"),
    # 20 parts of a 100 px step are 5 px each, as 5 parts of a 25 px step are
    ({}, 20, 278, (50, 100, 150), (476000, 480000),
     "0a8607a26415ed09c93021e6c2d0049052e4a076569f13135d1a0e53a9b14774"),
    # Parts rounded half up: 33 and 67 pixels into a 100 px step
    ({}, 3, 42, (190, 1444, 2736), (457600, 480000),
     "17b510f7be7b22ace5c4c5156aefbcd0dc20bac346e2506225e1fc48bc4fbd3b"),
    (dict(width_increment=20, height_increment=5), 7, 874, (30, 35, 56), (479200, 480000),
     "19a5104d3a3bbdf0775694f7f5bb92e58d75e06817993f8a19a4830db3d5909d"),
    (dict(final_width=450, final_height=800), 5, 63, (125, 625, 1125), (353250, 360000),
     "720f3692c8038129ed10616d16bcf028cac14301e048de961b5ddeb037d9bad1"),
    (dict(final_width=50, final_height=50), 5, 6, (125, 625, 1125), (2250, 2500),
     "0ba9b516ffc71b11df1677d1b8c6dede6b2cab79874dbccdab181cb29c82c5a4"),
    (dict(final_width=50, final_height=50, **STEPS_5), 20, 90, (30, 36, 42), (2450, 2500),
     "02193abcffa605d8c664a90f9900024e6606164841450c6134ee8a0b76de9d5e"),
    (dict(final_width=4096, final_height=4096), 5, 410, (125, 625, 1125), (16732160, 16777216),
     "45a8fa0fb72dee4890a73361e9e13f2dc62169398b1add30e73d207b72d0f898"),
    (dict(final_width=4096, final_height=4096), 20, 1638, (50, 100, 150), (16773120, 16777216),
     "fe3b05a1af81a4fe1c32e615978ae389a70434e98b15247eda7ff2b09344a0aa"),
    (dict(final_width=4096, final_height=4096, **STEPS_5), 5, 8182, (30, 36, 42), (16773120, 16777216),
     "d91e2aae5584f2c1a2d57e18c2a26bb1bdda295b0cbc16aa32d8436edd3cb2be"),
    (dict(final_width=4000, final_height=3000, **STEPS_5), 5, 6990, (30, 36, 42), (11996000, 12000000),
     "deac116d06e31554d986b0c3fae90647222a370554e26d667c499ad505fd5c6f"),
    (dict(final_width=8192, final_height=8192), 5, 820, (125, 625, 1125), (67051520, 67108864),
     "f946f3cbb54f73c0a1e3385067391ad3342b2f589bb61f39b8c406dc2ddd4c71"),
    (dict(final_width=8192, final_height=8192, **STEPS_5), 5, 16374, (30, 36, 42), (67100672, 67108864),
     "a7178a4bc92120690caa3eae0353ee5ef54083294b27491d60db86ccb396b0d8"),
    (BIGGEST, 20, 6552, (50, 100, 150), (268369920, 268435456),
     "9d65845fdb9eda55a614096b07c1f75b01429fe170402cab44bd2585eb408a3f"),
    # The most any option set makes, one for each line of pixels: at 20 px steps 20 a step, and at 5 px 5 a step
    (dict(BIGGEST, width_increment=20, height_increment=20), 20, 32758, (30, 36, 42), (268419072, 268435456),
     "d5ee2cfa72a81cdd266f670b190087f220ecf6de39b988988e5702c02075a9c2"),
    (dict(BIGGEST, **STEPS_5), 5, 32758, (30, 36, 42), (268419072, 268435456),
     "d5ee2cfa72a81cdd266f670b190087f220ecf6de39b988988e5702c02075a9c2"),
    # From the half start, which generate_early refuses on this goal (test_goal_options.py)
    (dict(BIGGEST, start_width=8192, start_height=8192, **STEPS_5), 5, 16384, (67117056, 67125249, 67133442),
     (268419072, 268435456), "3f9090e08218132b5295c59bc65f931caac4830e5427406a4af4a89eacbcfcbf"),
    (dict(final_width=16384, final_height=50, width_increment=10, height_increment=10), 10, 16424, (30, 35, 40),
     (802816, 819200), "7d23fb1d77eaf9ca3a4983b19b9bf1693c28ddc676645c88e78de889659406e9"),
    (dict(final_width=50, final_height=16384, width_increment=25, height_increment=25), 2, 1315, (90, 150, 215),
     (819000, 819200), "2c6145ceacd4f41ff2e0b8329685c02ca1f94417c1ada379dde517eefc9713a4"),
    (dict(final_width=1000, final_height=700, width_increment=50, height_increment=10), 4, 358, (40, 50, 65),
     (698000, 700000), "5282672f1e7c91b068bb382f061ab2f7fa981a95abedf7c3f28b40c9751cf069"),
    (dict(final_width=801, final_height=601, **HALF_START, **STEPS_5), 3, 422, (120600, 121404, 121706),
     (480600, 481401), "12dec004830b0529021c4ef799d86766d04b0985605908db0923569d2484e35e"),
]
# plan_math.perfect_in_logic() at 5 a step, and the checks it puts in logic: (layout changes, (red, green and blue
# items, width and height items, speed and accuracy copies), exact pixels, checks in logic, checks)
IN_LOGIC = [
    # D21: with the full canvas, 4 at no speed or accuracy items and all 70 at 8 speed items
    ({}, (254, 254, 254, 8, 6, 0, 0), 2159.9999999999995, 4, 70),
    ({}, (254, 254, 254, 8, 6, 8, 0), 480000, 70, 70),
    ({}, (253, 254, 254, 8, 6, 10, 9), 0, 0, 70),  # one color item short
    ({}, (254, 254, 254, 0, 0, 0, 0), 25, 0, 70),
    ({}, (254, 254, 254, 1, 1, 0, 0), 2159.9999999999995, 4, 70),
    ({}, (254, 254, 254, 2, 1, 3, 2), 21525, 14, 70),
    ({}, (254, 254, 254, 8, 6, 3, 2), 51840.00000000001, 22, 70),
    ({}, (254, 254, 254, 8, 6, 7, 0), 276479.99999999994, 52, 70),
    ({}, (254, 254, 254, 4, 3, 10, 9), 123525, 35, 70),
    (dict(auto_copy_logic_hours=0), (254, 254, 254, 8, 6, 0, 0), 480000, 70, 70),
    (dict(auto_copy_logic_hours=0), (254, 254, 254, 3, 2, 0, 0), 62525, 24, 70),
    (HALF_START, (254, 254, 254, 0, 0, 0, 0), 2159.9999999999995, 0, 35),
    (HALF_START, (254, 254, 254, 4, 3, 10, 9), 480000, 35, 35),
    (dict(color_depth_items=7), (7, 7, 7, 8, 6, 5, 5), 414719.99999999994, 64, 70),
    (dict(color_depth_items=7, starting_color_depth=2), (7, 7, 7, 8, 6, 0, 0), 2159.9999999999995, 4, 70),
]
# 0.1% from the start at 5 px steps with 20 Perfect Pixels a step: 844 similarity checks and Matched Pixels, 1,390
# Perfect Pixels, and 1,367 required items
TENTH_AT_5_PX = {"tenth_percent_checks": 0, "hundredth_percent_checks": 100, "canvas_width_increment": 5,
                 "canvas_height_increment": 5, "perfect_pixel_checks": 20}
FIVE_A_STEP = {"perfect_pixel_checks": 5}
COLORS = ("Progressive Color Depth (Red)", "Progressive Color Depth (Green)", "Progressive Color Depth (Blue)")


def perfect_of(multiworld: MultiWorld, player: int = 1) -> list[PerfectPixelsLocation]:
    return [location for location in multiworld.get_locations(player) if isinstance(location, PerfectPixelsLocation)]


def digest(targets: tuple[int, ...]) -> str:
    return hashlib.sha256(",".join(str(target) for target in targets).encode()).hexdigest()


def kind(item: Item) -> str:
    return ("progression" if item.advancement else "useful" if item.useful else
            "trap" if item.classification & ItemClassification.trap else "filler")


def reaches_every_location(multiworld: MultiWorld) -> bool:
    """Whether a state from nothing reaches every location sphere by sphere, collecting what each holds, and then
    beats every player's game, as the base class's test_fill checks it."""
    locations, state = list(multiworld.get_locations()), CollectionState(multiworld)
    while locations:
        sphere = [location for location in locations if location.can_reach(state)]
        if not sphere:
            return False
        for location in sphere:
            locations.remove(location)
            if location.item:
                state.collect(location.item, True, location)
    return multiworld.can_beat_game(state)


class TestTheTargets(unittest.TestCase):
    def test_the_targets_match_the_plan(self) -> None:
        for changes, per_step, count, first, last, whole in TARGETS:
            with self.subTest(layout=changes, perfect_pixel_checks=per_step):
                targets = layout(**changes, perfect_pixel_checks=per_step).perfect_thresholds
                self.assertEqual((count, first, last), (len(targets), targets[:3], targets[-2:]))
                self.assertEqual(whole, digest(targets))

    def test_every_check_the_option_asks_for(self) -> None:
        # plan_math's 512 option sets: each list climbs to the whole goal, with at most one check for each part of a
        # canvas step and for each line of pixels the canvas grows by, so none makes more than the 32,758 names, and
        # 16,384 at most from the half start.
        most = half_most = 0
        for (width, height), half, (step_width, step_height), per_step in itertools.product(
                ((50, 50), (800, 600), (4000, 3000), (8192, 8192), (16384, 16384), (800, 800), (16384, 50),
                 (50, 16384)), (False, True),
                ((5, 5), (10, 10), (20, 20), (25, 25), (50, 50), (100, 100), (5, 100), (100, 5)), (1, 5, 10, 20)):
            start_width, start_height = (width // 2, height // 2) if half else (5, 5)
            setup = layout(final_width=width, final_height=height, start_width=start_width, start_height=start_height,
                           width_increment=step_width, height_increment=step_height, perfect_pixel_checks=per_step)
            targets = setup.perfect_thresholds
            if (targets[-1] != width * height or any(later <= earlier for earlier, later in zip(targets, targets[1:]))
                    or len(targets) > min(per_step * sum(setup.canvas_items),
                                          width - start_width + height - start_height)):
                self.fail(f"{len(targets)} targets up to {targets[-1]} at {setup}")
            most = max(most, len(targets))
            if half:
                half_most = max(half_most, len(targets))
        self.assertEqual((32758, 16384), (most, half_most))
        self.assertEqual(PERFECT_MOST, most)

    def test_none_at_0_and_each_counts_as_a_location(self) -> None:
        self.assertEqual((), layout().perfect_thresholds)
        for mode in ("useful", "filler", "any"):
            with self.subTest(perfect_pixel_items=mode):
                setup = layout(perfect_pixel_checks=5, perfect_pixel_items=mode, timesanity_minutes=10)
                # plan_math's location_count() and excluded_count(): 8,043 similarity checks and Matched Pixels, 144
                # marks and 70 Perfect Pixels, which at filler are excluded
                self.assertEqual((8257, 70 if mode == "filler" else 0), (setup.location_count, setup.excluded_count))
        setup = layout(spacing=(50, 70, 0, 100, 100), **STEPS_5, perfect_pixel_checks=20, perfect_pixel_items="filler")
        self.assertEqual((2234, 1390), (setup.location_count, setup.excluded_count))
        self.assertEqual((8043, 0), (layout(perfect_pixel_items="filler").location_count,
                                     layout(perfect_pixel_items="filler").excluded_count))


class TestTheRule(unittest.TestCase):
    def test_checks_in_logic_match_the_plan(self) -> None:
        for changes, state, pixels, in_logic, count in IN_LOGIC:
            with self.subTest(layout=changes, state=state):
                setup = layout(**changes, perfect_pixel_checks=5)
                exact = perfect_in_logic(setup, *state)
                self.assertEqual((pixels, in_logic, count),
                                 (exact, bisect_right(setup.perfect_thresholds, exact), len(setup.perfect_thresholds)))

    def test_none_until_every_color_item(self) -> None:
        # Through each check's own rule: with every progression item but one color item, none; with that one too, all
        # 70; with every color and canvas item and no speed or accuracy copy, 4. Starting color items count.
        for options in (FIVE_A_STEP, {**FIVE_A_STEP, "starting_color_depth": 1}):
            multiworld = build(options)
            checks = perfect_of(multiworld)
            progression = [item for item in multiworld.itempool if item.advancement]
            for channel in COLORS:
                with self.subTest(options=options, short_of=channel):
                    [*_, last] = [item for item in progression if item.name == channel]
                    state = CollectionState(multiworld)
                    for item in progression:
                        if item is not last:
                            state.collect(item, prevent_sweep=True)
                    self.assertEqual(0, sum(check.can_reach(state) for check in checks))
                    state.collect(last, prevent_sweep=True)
                    self.assertEqual(70, sum(check.can_reach(state) for check in checks))
            state = CollectionState(multiworld)
            for item in progression:
                if item.name in COLORS or "Canvas" in item.name:
                    state.collect(item, prevent_sweep=True)
            self.assertEqual(4, sum(check.can_reach(state) for check in checks))

    def test_copies_past_the_top_tier_read_as_the_top_tier(self) -> None:
        # Start inventory can hold more speed copies than auto copy's 10: the budget reads them as 10, 368,640 pixels
        # in 1 h at 90% misses, so 60 of the 70 checks
        setup = layout(perfect_pixel_checks=5, auto_copy_logic_hours=1)
        for speed in (10, 11, 17):
            with self.subTest(speed=speed):
                exact = perfect_in_logic(setup, 254, 254, 254, 8, 6, speed, 0)
                self.assertEqual((368639.99999999994, 60), (exact, bisect_right(setup.perfect_thresholds, exact)))


class TestTheChecksInASeed(unittest.TestCase):
    def test_five_a_step(self) -> None:
        multiworld = build(FIVE_A_STEP)
        checks, world = perfect_of(multiworld), multiworld.worlds[1]
        self.assertEqual({name: address for name, address in perfect_table.items() if address <= 2_211_070},
                         {check.name: check.address for check in checks})
        self.assertEqual(("Perfect Pixels #1", 2_211_001, 125, "Perfect Pixels #70", 2_211_070, 480_000),
                         (checks[0].name, checks[0].address, checks[0].target, checks[-1].name, checks[-1].address,
                          checks[-1].target))
        self.assertEqual(list(world.layout.perfect_thresholds), [check.target for check in checks])
        self.assertEqual({("Canvas", "Pain-T")}, {(check.parent_region.name, check.game) for check in checks})
        # 70 locations more and as many fillers, and every other item with its class as it was
        pool, defaults = multiworld.itempool, build({}).itempool
        self.assertEqual((8113, 8113), (len(multiworld.get_locations(1)), len(pool)))

        def non_filler(items: list[Item]) -> Counter:
            return Counter((item.name, item.classification) for item in items
                           if item.classification != ItemClassification.filler)

        self.assertEqual((1103, non_filler(defaults)), (sum(non_filler(pool).values()), non_filler(pool)))

    def test_location_exists_with_options_makes_the_seeds_checks(self) -> None:
        for options, count in (({}, 0), (FIVE_A_STEP, 70), ({"perfect_pixel_checks": 1}, 14),
                               ({"perfect_pixel_checks": 20, "perfect_pixel_items": "any",
                                 "canvas_width_increment": 5, "canvas_height_increment": 5}, 1390)):
            with self.subTest(options=options):
                multiworld = build(options)
                made = [address for address in perfect_table.values()
                        if location_exists_with_options(multiworld.worlds[1], address)]
                self.assertEqual(list(range(2_211_001, 2_211_001 + count)), made)
                self.assertEqual(made, [check.address for check in perfect_of(multiworld)])
        world = generate_early(named(50, 50, perfect_pixel_checks=5), slots=2)
        self.assertEqual(list(range(2_211_001, 2_211_007)), [address for address in perfect_table.values()
                                                             if location_exists_with_options(world, address)])
        self.assertEqual((125, 625, 1125, 2025, 2250, 2500), world.layout.perfect_thresholds)

    def test_what_each_mode_lets_a_check_hold(self) -> None:
        # useful turns away any player's progression and takes useful items, filler and traps. filler makes excluded
        # locations, which take filler and traps only. any takes every item. At auto_copy_logic_hours 0, any turns
        # progression away too.
        progression = Item("Progression", ItemClassification.progression_skip_balancing, None, 2)
        refuses = (False, False, False, True, True, True)
        for mode, hours, progress_type, takes in (
                ("useful", 6, LocationProgressType.DEFAULT, refuses),
                ("filler", 6, LocationProgressType.EXCLUDED, (False, False, False, False, True, True)),
                ("any", 6, LocationProgressType.DEFAULT, (True,) * 6),
                ("useful", 0, LocationProgressType.DEFAULT, refuses),
                ("filler", 0, LocationProgressType.EXCLUDED, (False, False, False, False, True, True)),
                ("any", 0, LocationProgressType.DEFAULT, refuses)):
            multiworld = build({**FIVE_A_STEP, "perfect_pixel_items": mode, "auto_copy_logic_hours": hours,
                                "trap_count": 50}, slots=2)
            first = {}
            for item in multiworld.itempool:
                first.setdefault((item.player, item.classification), item)
            items = [first[player, ItemClassification.progression] for player in (1, 2)] + [progression]
            items += [first[1, classification] for classification in (ItemClassification.useful,
                                                                      ItemClassification.filler,
                                                                      ItemClassification.trap)]
            state, checks = CollectionState(multiworld), perfect_of(multiworld)
            with self.subTest(perfect_pixel_items=mode, auto_copy_logic_hours=hours):
                self.assertEqual(70, len(checks))
                self.assertEqual({progress_type}, {check.progress_type for check in checks})
                self.assertEqual({takes}, {tuple(check.can_fill(state, item, False) for item in items)
                                           for check in checks})

    def test_a_big_goal(self) -> None:
        # 4096x4096 at 5 px steps: 8,182 checks, one for each line of pixels, every one in logic with every item.
        # Built beside a second slot, without the fill.
        multiworld = build(named(4096, 4096, perfect_pixel_checks=5, perfect_pixel_items="any",
                                 canvas_width_increment=5, canvas_height_increment=5), slots=2)
        checks = perfect_of(multiworld)
        self.assertEqual((8182, 2_219_182, 16_777_216), (len(checks), checks[-1].address, checks[-1].target))
        state = multiworld.get_all_state(False)
        self.assertEqual([], [check.name for check in checks if not check.can_reach(state)])


class TestSlotData(unittest.TestCase):
    def test_slot_data(self) -> None:
        # From version 1.2.0 (D21): perfect_pixel_targets lists every check's exact pixels in order, the k-th for id
        # 2,211,000 + k, [] with the family off, beside perfect_pixel_checks and perfect_pixel_items, the option's key.
        five = list(layout(perfect_pixel_checks=5).perfect_thresholds)
        for options, targets, mode, slots in (
                ({}, [], "useful", 1), (FIVE_A_STEP, five, "useful", 1), (FIVE_A_STEP, five, "useful", 2),
                ({**FIVE_A_STEP, "perfect_pixel_items": "filler"}, five, "filler", 1),
                ({**FIVE_A_STEP, "perfect_pixel_items": "any", "auto_copy_logic_hours": 0}, five, "any", 1),
                ({"perfect_pixel_items": "any"}, [], "any", 1),
                (named(50, 50, perfect_pixel_checks=5), [125, 625, 1125, 2025, 2250, 2500], "useful", 2)):
            with self.subTest(options=options, slots=slots):
                world = generate_early(options, slots)
                slot_data = world.fill_slot_data()
                self.assertEqual((targets, mode, options.get("perfect_pixel_checks", 0)),
                                 (slot_data["perfect_pixel_targets"], slot_data["perfect_pixel_items"],
                                  slot_data["perfect_pixel_checks"]))
                self.assertEqual((list, str, int), (type(slot_data["perfect_pixel_targets"]),
                                                    type(slot_data["perfect_pixel_items"]),
                                                    type(slot_data["perfect_pixel_checks"])))
                self.assertEqual([], [target for target in slot_data["perfect_pixel_targets"]
                                      if type(target) is not int])
                self.assertEqual(slot_data, json.loads(json.dumps(slot_data)))
                self.assertEqual([PERFECT_BASE + k for k in range(1, len(targets) + 1)],
                                 [address for address in perfect_table.values()
                                  if location_exists_with_options(world, address)])
        # 32 keys on every seed, Missed Pixels' two among them (test_missed_pixels.py), and the checks change no key but
        # their own three
        defaults = generate_early({}).fill_slot_data()
        with_checks = generate_early({**FIVE_A_STEP, "perfect_pixel_items": "any"}).fill_slot_data()
        self.assertEqual((32, 32), (len(defaults), len(with_checks)))
        self.assertEqual({"perfect_pixel_checks", "perfect_pixel_items", "perfect_pixel_targets"},
                         {key for key in defaults if defaults[key] != with_checks[key]})


class TestTheRefusals(unittest.TestCase):
    def test_at_filler_the_items_need_the_other_locations(self) -> None:
        # D21: at filler the 1,390 checks take only filler and traps, so 844 locations are left for 1,367 items, solo or
        # not. At useful and any they take useful items, and 2,234 locations hold the items. At useful they turn
        # progression away, and task 8.3's count then refuses 1,058 progression items for 844 (test_freeze.py).
        with self.assertRaises(OptionError) as raised:
            generate_early({**TENTH_AT_5_PX, "perfect_pixel_items": "filler"}, slots=2)
        self.assertEqual("Tester1's Pain-T world has 844 locations for 1367 required items beside the 1390 Perfect "
                         "Pixels checks that perfect_pixel_items filler keeps for filler and traps. Add checks "
                         "(hundredth_percent_checks 0 makes one every 0.01%), raise logic_percent, lower "
                         "color_depth_items, or use bigger canvas steps. With tool_size_ladders off, 23 of them stay "
                         "out. With overclock_bank_size_items and overclock_fill_speed_items at 0, 10 more stay out. "
                         "With miss_margin_step 255, 254 more stay out. With perfect_pixel_items any, those 1390 "
                         "checks take every item, and the items fit.", str(raised.exception))
        world = generate_early({**TENTH_AT_5_PX, "perfect_pixel_items": "any"}, slots=2)
        self.assertEqual((2234, 0, 1367), (world.layout.location_count, world.layout.excluded_count,
                                           len(world.non_filler_items())))
        with self.assertRaisesRegex(OptionError, r"has 844 locations that take progression for 1,058 progression "
                                                 r"items beside the 1,390 Perfect Pixels checks"):
            generate_early({**TENTH_AT_5_PX, "perfect_pixel_items": "useful"}, slots=2)
        # The marks are not excluded: a mark every minute makes 2,284 locations besides the 1,390.
        world = generate_early({**TENTH_AT_5_PX, "perfect_pixel_items": "filler", "timesanity_minutes": 1}, slots=2)
        self.assertEqual((3674, 1390), (world.layout.location_count, world.layout.excluded_count))

    def test_at_filler_the_message_names_the_values_that_fit(self) -> None:
        # The item count at filler names the other values of perfect_pixel_items at which the items fit, task 8.3's
        # count included: any alone at 0.1% from the start, where useful leaves 844 locations for 1,058 progression
        # items; useful or any with a mark every 4 minutes, whose 360 marks take progression; and neither at 0 h, where
        # both turn progression away, or where the items outnumber every location: 452 for 1,103 at Paint's spacing in
        # 100 px steps, and 932 with a mark every 3 minutes, which would hold the 794 progression items. Where it names
        # none it writes no sentence for them. At each count's edge it names both: at Paint's steps with a Perfect
        # Pixels check a step, a mark every 2 minutes and 16 Missed Pixels checks a speed copy, 1,100 items fill the
        # 1,100 locations at any, and at logic 87 with a mark every 10 minutes 1,058 progression items fill the 1,058
        # locations that take them at useful. One past each edge: a 7th Progressive Overclock Bank Size makes 1,101
        # items for the 1,100 locations, and it names neither; at logic 68 with a mark every 10 minutes, 16 Missed
        # Pixels checks a speed copy, 12 Overclock bank size and 6 fill speed items and no tool ladders, 1,061
        # progression items need the 1,060 locations that take them at useful, and it names any alone. Each value it
        # names passes both counts beside a second slot, and each it leaves out is refused.
        paints_steps = {"tenth_percent_checks": 100, "canvas_width_increment": 100, "canvas_height_increment": 100}
        items_edge = {**paints_steps, "perfect_pixel_checks": 1, "timesanity_minutes": 2, "missed_pixel_checks": 16,
                      "overclock_bank_size_items": 6, "overclock_fill_speed_items": 0}
        progression_edge = {"timesanity_minutes": 10, "logic_percent": 87}
        past_items_edge = {**items_edge, "overclock_bank_size_items": 7}
        past_progression_edge = {"logic_percent": 68, "timesanity_minutes": 10, "missed_pixel_checks": 16,
                                 "overclock_bank_size_items": 12, "overclock_fill_speed_items": 6,
                                 "tool_size_ladders": False}
        for changes, named_values in (({}, ("any",)), ({"timesanity_minutes": 4}, ("useful", "any")),
                                      ({"auto_copy_logic_hours": 0}, ()), (paints_steps, ()),
                                      ({**paints_steps, "timesanity_minutes": 3}, ()),
                                      (items_edge, ("useful", "any")), (progression_edge, ("useful", "any")),
                                      (past_items_edge, ()), (past_progression_edge, ("any",))):
            options = {**TENTH_AT_5_PX, **changes}
            with self.subTest(changes=changes):
                with self.assertRaises(OptionError) as raised:
                    generate_early({**options, "perfect_pixel_items": "filler"}, slots=2)
                found = re.search(r"With perfect_pixel_items (useful or any|any), those [\d,]+ checks take",
                                  str(raised.exception))
                self.assertEqual(named_values, tuple(found.group(1).split(" or ")) if found else ())
                if not named_values:
                    self.assertNotIn("With perfect_pixel_items", str(raised.exception))
                for mode in ("useful", "any"):
                    if mode in named_values:
                        generate_early({**options, "perfect_pixel_items": mode}, slots=2)
                    else:
                        with self.assertRaises(OptionError):
                            generate_early({**options, "perfect_pixel_items": mode}, slots=2)
        at_any = generate_early({**TENTH_AT_5_PX, **items_edge, "perfect_pixel_items": "any"}, slots=2)
        self.assertEqual((1100, 1100), (len(at_any.non_filler_items()), at_any.layout.location_count))
        at_useful = generate_early({**TENTH_AT_5_PX, **progression_edge, "perfect_pixel_items": "useful"}, slots=2)
        self.assertEqual((1058, 1058), (sum(progression_counts(at_useful.layout)) + happy_count(at_useful.layout),
                                        at_useful.layout.taking_count))
        # The counts one past each edge, read with the refusals left out
        with mock.patch.object(PaintHardWorld, "refuse_unfillable"):
            at_any = generate_early({**TENTH_AT_5_PX, **past_items_edge, "perfect_pixel_items": "any"}, slots=2)
            at_useful = generate_early({**TENTH_AT_5_PX, **past_progression_edge, "perfect_pixel_items": "useful"},
                                       slots=2)
        self.assertEqual((1101, 1100), (len(at_any.non_filler_items()), at_any.layout.location_count))
        self.assertEqual((1061, 1060), (sum(progression_counts(at_useful.layout)) + happy_count(at_useful.layout),
                                        at_useful.layout.taking_count))

    def test_a_refusals_sample_counts_as_the_item_count(self) -> None:
        # From 5 px steps, 100 px steps make 278 Perfect Pixels and need 1,103 items: at filler 844 locations are left
        # for them, and at useful 1,122 hold them, which the fill check then passes.
        setup = layout(spacing=(50, 70, 0, 100, 100), **STEPS_5, perfect_pixel_checks=20, perfect_pixel_items="filler")
        other = replace(setup, width_increment=100, height_increment=100)
        self.assertEqual((1122, 278), (other.location_count, other.excluded_count))
        at_useful = replace(setup, perfect_pixel_items="useful"), replace(other, perfect_pixel_items="useful")
        self.assertEqual((False, True), (change_fills(setup, other, 1367), change_fills(*at_useful, 1367)))

    def test_the_model_leaves_the_checks_out(self) -> None:
        # The fill check places progression on the similarity checks and Matched Pixels alone, so no mode changes a
        # verdict: test_auto_copy_logic.py's, at the defaults, at 5 px steps with 0.05% from the start, and at 0 h.
        for changes, verdict in (({}, (3, 3)),
                                 (dict(spacing=(50, 70, 100, 0, 100), **STEPS_5), (0, 3)),
                                 (dict(auto_copy_logic_hours=0), (3, 3))):
            for mode in ("useful", "filler", "any"):
                with self.subTest(changes=changes, perfect_pixel_items=mode):
                    self.assertEqual(verdict, passes_filled(layout(**changes, perfect_pixel_checks=20,
                                                                   perfect_pixel_items=mode)))

    def test_a_refusal_names_the_checks_that_take_progression(self) -> None:
        # Only at any with auto copy in logic do the checks take progression the model leaves out, and with the family
        # off there are none.
        setup = layout(spacing=(50, 70, 100, 0, 100), **STEPS_5, perfect_pixel_checks=20)
        with mock.patch.object(rules, "passing_changes", return_value=([], 16)):
            messages = {mode: refusal("P1", replace(setup, perfect_pixel_items=mode), 1367)
                        for mode in ("useful", "filler", "any")}
            off = refusal("P1", replace(setup, perfect_pixel_items="any", perfect_pixel_checks=0), 1367)
            at_0_h = refusal("P1", replace(setup, perfect_pixel_items="any", auto_copy_logic_hours=0), 1367)
            with_marks = refusal("P1", replace(setup, perfect_pixel_items="any", timesanity_minutes=10), 1367)
        plain = ("P1's Pain-T world can't be filled alone: a model of Archipelago's fill, run on its logic with fixed "
                 "seeds, has to place every progression item in 3 of 5 tries. It filled 0 of the first 3, and with 2 "
                 "tries left it can't reach 3. None of a sample of 16 single changes passes the check; try two at "
                 "once, or play it beside a Pain-T slot at the defaults. Beside other slots this check doesn't run, "
                 "and Archipelago's own fill decides.")
        self.assertEqual((plain, plain, plain), (messages["useful"], messages["filler"], off))
        self.assertEqual(plain.replace(" can't reach 3. ", " can't reach 3. The model places progression on the "
                                                           "similarity checks and Matched Pixels alone and leaves out "
                                                           "this seed's 1,390 Perfect Pixels checks. "),
                         messages["any"])
        self.assertNotIn("Perfect Pixels", at_0_h)
        self.assertIn(" can't reach 3. The model places progression on the similarity checks and Matched Pixels alone "
                      "and leaves out this seed's 144 Auto Copy Time checks and 1,390 Perfect Pixels checks. None of",
                      with_marks)


class TestAFill(unittest.TestCase):
    def test_what_lands_on_the_checks(self) -> None:
        # Archipelago's fill, seed 1, 5 a step: progression lands on the checks at any and on none in the other modes
        # or with auto copy out of logic, and at filler they hold filler and traps alone. Every location is reached
        # sphere by sphere.
        for options in ({**FIVE_A_STEP, "perfect_pixel_items": "any"}, FIVE_A_STEP,
                        {**FIVE_A_STEP, "perfect_pixel_items": "filler", "trap_count": 50},
                        {**FIVE_A_STEP, "perfect_pixel_items": "any", "auto_copy_logic_hours": 0}):
            with self.subTest(options=options):
                multiworld = setup_multiworld(PaintHardWorld, seed=1, options=options)
                distribute_items_restrictive(multiworld)
                call_all(multiworld, "post_fill")
                held = Counter(kind(check.item) for check in perfect_of(multiworld))
                self.assertEqual(70, sum(held.values()))
                if options.get("perfect_pixel_items") == "any" and options.get("auto_copy_logic_hours", 6):
                    self.assertGreater(held["progression"], 0)
                elif options.get("perfect_pixel_items") == "filler":
                    self.assertEqual(0, held["progression"] + held["useful"])
                    self.assertGreater(held["trap"], 0)
                else:
                    self.assertEqual(0, held["progression"])
                self.assertTrue(reaches_every_location(multiworld))

    def test_another_slots_progression_lands_on_them(self) -> None:
        # Two slots at any: the second slot's progression lands on the first slot's checks too, and every location of
        # both stays reachable.
        options = {**FIVE_A_STEP, "perfect_pixel_items": "any"}
        multiworld = setup_multiworld([PaintHardWorld] * 2, seed=1, options=[options, options])
        distribute_items_restrictive(multiworld)
        call_all(multiworld, "post_fill")
        held = Counter(check.item.player for check in perfect_of(multiworld) if check.item.advancement)
        self.assertGreater(held[2], 0)
        self.assertTrue(reaches_every_location(multiworld))


class TestPerfectPixelsUseful(PaintHardTestBase):
    # 5 a step: the base class's tests reach every location with every item, something with none, and fill the seed.
    options = FIVE_A_STEP


class TestPerfectPixelsFiller(PaintHardTestBase):
    options = {**FIVE_A_STEP, "perfect_pixel_items": "filler"}


class TestPerfectPixelsAny(PaintHardTestBase):
    options = {**FIVE_A_STEP, "perfect_pixel_items": "any"}


class TestPerfectPixelsAnyWithAutoCopyOutOfLogic(PaintHardTestBase):
    options = {**FIVE_A_STEP, "perfect_pixel_items": "any", "auto_copy_logic_hours": 0}


class TestPerfectPixelsAnyWithTheMarks(PaintHardTestBase):
    options = {**FIVE_A_STEP, "perfect_pixel_items": "any", "timesanity_minutes": 10, "starting_color_depth": 1}

"""Auto Copy Time (D21, task 8.2) and the rules of the checks of D21 and D26 (task 8.3, its first part), against
hard-fork/plan_math.py: the marks a seed makes, the figure each family's checks read from a state, which a state works
out with its percent, and the marks in a seed: their ids, rule, item rule and slot data, the item count, the solo
refusal, and seeds with the marks on that the base class's tests reach and fill. In this release the marks are off by
default (test_check_families.py). The figures of Perfect Pixels and Missed Pixels are tested here on their own, and
their checks in test_perfect_pixels.py and test_missed_pixels.py.
"""
import itertools
import json
import unittest
from bisect import bisect_right
from collections import Counter
from dataclasses import replace
from math import inf
from unittest import mock

from BaseClasses import CollectionState, Item, ItemClassification, MultiWorld
from Fill import distribute_items_restrictive
from Options import OptionError
from test.general import setup_multiworld

from . import PaintHardTestBase
from .. import PaintHardWorld, location_exists_with_options, rules
from ..locations import TIME_BASE, AutoCopyTimeLocation, time_table
from ..rules import (MISS, Reach, change_fills, family_reach, missed_reach, paint_percent_available, paint_reach,
                     passes_filled, perfect_in_logic, refusal, time_in_logic)
from .test_auto_copy_logic import layout
from .test_goal_options import generate_early, named

HALF_START = dict(start_width=400, start_height=300)
BIGGEST = dict(final_width=16384, final_height=16384)
BIGGEST_AT_1_H = dict(BIGGEST, auto_copy_logic_hours=1)
# plan_math.time_marks() for (timesanity_minutes, timesanity_hours, goal width, goal height): how many marks, the first
# three and the last two
MARKS = [
    ((10, 24, 800, 600), 144, (10, 20, 30), (1430, 1440)),
    ((1, 24, 800, 600), 1440, (1, 2, 3), (1439, 1440)),
    ((10, 6, 800, 600), 36, (10, 20, 30), (350, 360)),
    # A spacing that doesn't divide the hours ends below them
    ((7, 1, 800, 600), 8, (7, 14, 21), (49, 56)),
    ((1440, 24, 800, 600), 1, (1440,), (1440,)),
    ((1440, 23, 800, 600), 0, (), ()),
    ((0, 24, 800, 600), 0, (), ()),
    # None past the goal's pixels / 120 minutes: 20 on 50x50, 83 on 100x100, and 172,800 pixels hold the 24:00 mark
    ((10, 24, 50, 50), 2, (10, 20), (10, 20)),
    ((1, 24, 50, 50), 20, (1, 2, 3), (19, 20)),
    ((1, 1, 50, 50), 20, (1, 2, 3), (19, 20)),
    ((60, 24, 100, 100), 1, (60,), (60,)),
    ((1, 24, 100, 100), 83, (1, 2, 3), (82, 83)),
    ((1, 24, 480, 360), 1440, (1, 2, 3), (1439, 1440)),
    ((1, 24, 479, 360), 1437, (1, 2, 3), (1436, 1437)),
    ((25, 24, 4096, 4096), 57, (25, 50, 75), (1400, 1425)),
    ((13, 17, 16384, 50), 78, (13, 26, 39), (1001, 1014)),
    ((1, 24, 16384, 16384), 1440, (1, 2, 3), (1439, 1440)),
]
# D21's table at the defaults with a mark every 10 minutes: (width and height items, minutes of auto copy work logic
# counts on, marks in logic of the 144)
TABLE = [((0, 0), 0, 0), ((1, 0), 4, 0), ((1, 1), 91, 9), ((2, 1), 179, 17), ((2, 2), 350, 35), ((3, 2), 521, 52),
         ((4, 4), 1366, 136), ((5, 4), 1704, 144)]
# plan_math.time_in_logic() with the canvas steps or the goal's sides apart: (layout changes, width and height items,
# minutes of work logic counts on)
APART = [(dict(width_increment=20, height_increment=5), (3, 7), 21),
         (dict(width_increment=20, height_increment=5), (7, 3), 24),
         (dict(width_increment=20, height_increment=5), (40, 0), 33),
         (dict(width_increment=20, height_increment=5), (0, 119), 25),
         (dict(final_width=450, final_height=800), (5, 2), 768),
         (dict(final_width=450, final_height=800), (2, 5), 862)]
# plan_math.perfect_in_logic() at these states: (layout changes, (red, green and blue items, width and height items,
# speed and accuracy copies), the pixels logic expects can equal the goal)
PERFECT = [
    ({}, (254, 254, 254, 8, 6, 0, 0), 2159.9999999999995),  # 1 pixel a second at 90% misses for 6 h
    ({}, (254, 254, 254, 8, 6, 8, 0), 480000),
    ({}, (254, 254, 253, 8, 6, 10, 9), 0),  # one color item short
    ({}, (254, 254, 254, 0, 0, 10, 9), 25),
    ({}, (254, 254, 254, 1, 1, 3, 2), 11025),
    ({}, (254, 254, 254, 8, 6, 3, 2), 51840.00000000001),
    ({}, (254, 254, 254, 8, 6, 12, 12), 480000),
    (dict(auto_copy_logic_hours=0), (254, 254, 254, 8, 6, 0, 0), 480000),
    (dict(auto_copy_logic_hours=0), (254, 254, 254, 2, 3, 0, 0), 62525),
    (dict(auto_copy_logic_hours=1), (254, 254, 254, 8, 6, 10, 9), 480000),
    (dict(auto_copy_logic_hours=1), (254, 254, 254, 8, 6, 11, 0), 368639.99999999994),  # 11 copies read as 10
    (dict(auto_copy_logic_hours=24), (254, 254, 254, 8, 6, 2, 1), 69119.99999999999),
    (dict(color_depth_items=7), (7, 7, 7, 8, 6, 5, 5), 414719.99999999994),
    (dict(color_depth_items=7), (7, 6, 7, 8, 6, 5, 5), 0),
    (HALF_START, (254, 254, 254, 0, 0, 0, 0), 2159.9999999999995),
    (HALF_START, (254, 254, 254, 4, 3, 9, 9), 480000),
    (BIGGEST_AT_1_H, (254, 254, 254, 164, 164, 17, 9), 268435456),
    (BIGGEST_AT_1_H, (254, 254, 254, 164, 164, 16, 9), 235929600.0),
    (BIGGEST, (254, 254, 254, 100, 50, 14, 9), 50075025),
]
# plan_math.missed_in_logic() at missed_pixel_checks 24: (layout changes, speed copies, Happy Accident, checks in
# logic). 800x600 makes 288 at any hours, and 16384x16384 at 1 h 456, with 17 speed copies.
MISSED = [({}, 0, False, 0), ({}, 10, False, 0), ({}, 0, True, 48), ({}, 1, True, 72), ({}, 5, True, 168),
          ({}, 10, True, 288), ({}, 12, True, 288), (dict(auto_copy_logic_hours=0), 0, True, 288),
          (dict(auto_copy_logic_hours=0), 0, False, 0), (dict(timesanity_hours=6), 3, True, 120),
          (dict(BIGGEST_AT_1_H, timesanity_hours=1), 16, True, 432),
          (dict(BIGGEST_AT_1_H, timesanity_hours=1), 17, True, 456),
          (dict(BIGGEST_AT_1_H, timesanity_hours=1), 18, True, 456)]
# 0.1% from the start, which the item count refuses at the defaults' pool (test_auto_copy_logic.py)
TENTH_FROM_THE_START = {"tenth_percent_checks": 0, "hundredth_percent_checks": 100}


def ladder(k: int, hours: int, copies: int) -> list[int]:
    """plan_math.ladder_values(): every Missed Pixels check's wrong pixels, ascending, in whole numbers rounded half up
    (D26). Happy Accident alone opens 2k up to X = 3,600 x timesanity_hours, and speed copy s opens k from 2^(s-1) X
    to 2^s X."""
    x = 3600 * hours

    def half_up(numerator: int, denominator: int) -> int:
        return (2 * numerator + denominator) // (2 * denominator)

    return ([half_up(x * j, 2 * k) for j in range(1, 2 * k + 1)] +
            [half_up(2 ** (s - 1) * x * (k + j), k) for s in range(1, copies + 1) for j in range(1, k + 1)])


def build(options: dict, slots: int = 1) -> MultiWorld:
    """A seed through create_items with these options for slot 1, and more slots at the defaults."""
    return setup_multiworld([PaintHardWorld] * slots, ("generate_early", "create_regions", "create_items"), seed=1,
                            options=[options] + [{}] * (slots - 1))


def marks_of(multiworld: MultiWorld, player: int = 1) -> list[AutoCopyTimeLocation]:
    return [location for location in multiworld.get_locations(player) if isinstance(location, AutoCopyTimeLocation)]


class TestTheMarks(unittest.TestCase):
    def test_the_marks_match_the_plan(self) -> None:
        for (minutes, hours, width, height), count, first, last in MARKS:
            with self.subTest(timesanity_minutes=minutes, timesanity_hours=hours, goal=(width, height)):
                setup = layout(final_width=width, final_height=height, timesanity_minutes=minutes,
                               timesanity_hours=hours)
                marks = setup.marks
                self.assertEqual((count, first, last), (len(marks), marks[:3], marks[-2:]))
                self.assertEqual([minutes] * (count - 1), [later - earlier for earlier, later in zip(marks, marks[1:])])
                # Auto copy out of logic keeps them; they turn progression away there.
                self.assertEqual(marks, layout(final_width=width, final_height=height, timesanity_minutes=minutes,
                                               timesanity_hours=hours, auto_copy_logic_hours=0).marks)
                self.assertEqual(setup.locations + count, setup.location_count)

    def test_marks_in_logic_by_canvas_items(self) -> None:
        setup = layout(timesanity_minutes=10)
        for (width, height), minutes, in_logic in TABLE:
            with self.subTest(width=width, height=height):
                self.assertEqual((minutes, in_logic), (time_in_logic(setup, width, height),
                                                       bisect_right(setup.marks, time_in_logic(setup, width, height))))
        # Each axis grows by its own step up to its own side.
        for changes, (width, height), minutes in APART:
            with self.subTest(layout=changes, width=width, height=height):
                self.assertEqual(minutes, time_in_logic(layout(**changes), width, height))

    def test_a_mark_needs_120_pixels_for_each_minute(self) -> None:
        # Whole minutes: 600 pixels hold the 5-minute mark and 599 don't. The 400x300 start holds the first 1,000
        # minutes, and the canvas stops at the goal's size.
        for (width, height), minutes in (((20, 30), 5), ((599, 1), 4), ((120, 1), 1), ((119, 1), 0),
                                         ((480, 360), 1440), ((400, 300), 1000), ((800, 600), 4000)):
            with self.subTest(start=(width, height)):
                self.assertEqual(minutes, time_in_logic(layout(start_width=width, start_height=height), 0, 0))
        self.assertEqual(4000, time_in_logic(layout(), 100, 100))


class TestTheFigures(unittest.TestCase):
    def test_perfect_pixels_match_the_plan(self) -> None:
        for changes, state, pixels in PERFECT:
            with self.subTest(layout=changes, state=state):
                setup = layout(**changes)
                self.assertEqual(pixels, perfect_in_logic(setup, *state))
                self.assertEqual(pixels, family_reach(setup, *state, False).perfect)

    def test_missed_pixels_match_the_plan(self) -> None:
        for changes, speed, happy, in_logic in MISSED:
            with self.subTest(layout=changes, speed=speed, happy=happy):
                setup = layout(**changes)
                reach = missed_reach(setup, speed, happy)
                self.assertEqual(in_logic, bisect_right(ladder(24, setup.timesanity_hours, setup.speed_items), reach))
                self.assertEqual(reach, family_reach(setup, 0, 0, 0, 0, 0, speed, 0, happy).missed)
        # None without Happy Accident; with it, 2^s x 3,600 x timesanity_hours, speed copies read up to the top tier's
        # 10; and every check at auto_copy_logic_hours 0
        setup = layout()
        self.assertEqual([0, 0, 86_400, 172_800, 2_764_800, 88_473_600, 88_473_600],
                         [missed_reach(setup, speed, happy) for speed, happy in ((0, False), (10, False), (0, True),
                                                                                 (1, True), (5, True), (10, True),
                                                                                 (12, True))])
        self.assertEqual((inf, 0), (missed_reach(layout(auto_copy_logic_hours=0), 0, True),
                                    missed_reach(layout(auto_copy_logic_hours=0), 10, False)))

    def test_no_item_lowers_a_figure(self) -> None:
        # plan_math's check, over a coarser grid: adding any one item, Happy Accident among them, never lowers a figure,
        # so no check leaves logic as items arrive.
        for setup in (layout(timesanity_minutes=10), layout(auto_copy_logic_hours=0), layout(**HALF_START),
                      layout(final_width=50, final_height=50, auto_copy_logic_hours=1, timesanity_hours=1),
                      layout(**BIGGEST_AT_1_H)):
            for c, w, h, speed, accuracy, happy in itertools.product((0, 1, 253, 254), (0, 1, 4, 8), (0, 1, 3, 6),
                                                                      (0, 1, 9, 10, 11), (0, 1, 8, 9),
                                                                      (False, True)):
                base = family_reach(setup, c, c, c, w, h, speed, accuracy, happy)
                for more in ((c + 1, c, c, w, h, speed, accuracy, happy), (c, c + 1, c, w, h, speed, accuracy, happy),
                             (c, c, c + 1, w, h, speed, accuracy, happy), (c, c, c, w + 1, h, speed, accuracy, happy),
                             (c, c, c, w, h + 1, speed, accuracy, happy), (c, c, c, w, h, speed + 1, accuracy, happy),
                             (c, c, c, w, h, speed, accuracy + 1, happy), (c, c, c, w, h, speed, accuracy, True)):
                    reached = family_reach(setup, *more)
                    if any(after < before for after, before in zip(reached, base)):
                        self.fail(f"{more} lowers {base} to {reached} at {setup}")

    def test_every_item_puts_every_check_in_logic(self) -> None:
        # With every item the pool holds, each family's figure reaches its last target: the seed's last mark, the whole
        # goal for Perfect Pixels, and 2^S x 3,600 x timesanity_hours for Missed Pixels (D21, D26).
        for (w, h), logic_hours, hours, step in itertools.product(
                ((800, 600), (450, 800), (50, 50), (4096, 4096), (16384, 50), (16384, 16384)), (0, 1, 6, 24),
                (1, 6, 24), (5, 100)):
            setup = layout(final_width=w, final_height=h, auto_copy_logic_hours=logic_hours, timesanity_minutes=1,
                           timesanity_hours=hours, width_increment=step, height_increment=step)
            with self.subTest(goal=(w, h), auto_copy_logic_hours=logic_hours, timesanity_hours=hours, step=step):
                reach = family_reach(setup, 254, 254, 254, *setup.canvas_items, setup.speed_items, len(MISS) - 1, True)
                self.assertGreaterEqual(reach.minutes, setup.marks[-1])
                self.assertGreaterEqual(reach.perfect, setup.goal_pixels)
                self.assertGreaterEqual(reach.missed, 2 ** setup.speed_items * 3600 * hours)


class TestAStatesFigures(unittest.TestCase):
    def test_a_state_works_them_out_with_its_percent(self) -> None:
        multiworld = build({"timesanity_minutes": 10})
        world, pool = multiworld.worlds[1], multiworld.itempool
        state, taken = CollectionState(multiworld), set()

        def take(name: str, copies: int) -> list[Item]:
            # Items of one name and player are equal, so the copies taken are told apart by identity.
            items = [item for item in pool if item.name == name and id(item) not in taken][:copies]
            for item in items:
                state.collect(item, prevent_sweep=True)
                taken.add(id(item))
            return items

        self.assertEqual(Reach(0, 0, 0), paint_reach(state, world, 1))
        take("Progressive Canvas Width", 1)
        take("Progressive Canvas Height", 1)
        self.assertEqual(Reach(91, 0, 0), paint_reach(state, world, 1))
        # Worked out with the percent, which clears the flag they share: read after it, they hold the new items.
        [width] = take("Progressive Canvas Width", 1)
        paint_percent_available(state, world, 1)
        self.assertEqual(179, paint_reach(state, world, 1).minutes)
        state.remove(width)
        taken.discard(id(width))
        self.assertEqual(91, paint_reach(state, world, 1).minutes)
        # 8 widths and a height: 800x105 pixels, where 105x600 would hold 525 minutes
        take("Progressive Canvas Width", 7)
        self.assertEqual(700, paint_reach(state, world, 1).minutes)
        # Every color item: exact pixels up to auto copy's budget, 1 pixel a second at 90% misses for 6 h
        for channel in ("Red", "Green", "Blue"):
            take(f"Progressive Color Depth ({channel})", 254)
        self.assertEqual(Reach(700, 2159.9999999999995, 0), paint_reach(state, world, 1))
        # Happy Accident, which this pool doesn't hold: what its switch makes at 1 a second in timesanity_hours' 24 h
        state.collect(world.create_item("Happy Accident"), prevent_sweep=True)
        self.assertEqual(Reach(700, 2159.9999999999995, 86_400), paint_reach(state, world, 1))
        # 3 speed and 2 accuracy copies: 51,840 pixels right in 6 h, and 8 times the switch's 86,400
        take("Progressive Auto Copy Speed", 3)
        take("Progressive Auto Copy Accuracy", 2)
        self.assertEqual(Reach(700, 51840.00000000001, 691_200), paint_reach(state, world, 1))
        self.assertEqual(paint_reach(state, world, 1), paint_reach(state.copy(), world, 1))

    def test_each_player_has_their_own(self) -> None:
        multiworld = setup_multiworld([PaintHardWorld] * 2, ("generate_early", "create_regions", "create_items"),
                                      seed=1, options=[{"timesanity_minutes": 10}, {"timesanity_minutes": 1}])
        state = CollectionState(multiworld)
        for name in ("Progressive Canvas Width", "Progressive Canvas Height"):
            state.collect(next(item for item in multiworld.itempool if item.name == name and item.player == 1),
                          prevent_sweep=True)
        self.assertEqual((91, 0), (paint_reach(state, multiworld.worlds[1], 1).minutes,
                                   paint_reach(state, multiworld.worlds[2], 2).minutes))
        self.assertEqual((9, 0), (sum(mark.can_reach(state) for mark in marks_of(multiworld, 1)),
                                  sum(mark.can_reach(state) for mark in marks_of(multiworld, 2))))


class TestTheMarksInASeed(unittest.TestCase):
    def test_a_mark_every_10_minutes(self) -> None:
        multiworld = build({"timesanity_minutes": 10})
        marks = marks_of(multiworld)
        self.assertEqual({name: address for name, address in time_table.items() if (address - TIME_BASE) % 10 == 0},
                         {mark.name: mark.address for mark in marks})
        self.assertEqual((144, "Auto Copy Time: 0:10", 2_209_010, "Auto Copy Time: 24:00", 2_210_440),
                         (len(marks), marks[0].name, marks[0].address, marks[-1].name, marks[-1].address))
        self.assertEqual([mark.address - 2_209_000 for mark in marks], [mark.minutes for mark in marks])
        self.assertEqual({("Canvas", "Pain-T")}, {(mark.parent_region.name, mark.game) for mark in marks})
        # The marks add 144 locations and as many fillers, and leave every other item and its class as it was.
        pool, defaults = multiworld.itempool, build({}).itempool
        self.assertEqual((8187, 8187), (len(multiworld.get_locations(1)), len(pool)))

        def non_filler(items: list[Item]) -> Counter:
            return Counter((item.name, item.classification) for item in items
                           if item.classification != ItemClassification.filler)

        self.assertEqual((1103, non_filler(defaults)), (sum(non_filler(pool).values()), non_filler(pool)))

    def test_a_mark_every_minute(self) -> None:
        marks = marks_of(build({"timesanity_minutes": 1}))
        self.assertEqual(list(range(2_209_001, 2_210_441)), [mark.address for mark in marks])
        self.assertEqual(list(time_table), [mark.name for mark in marks])

    def test_location_exists_with_options_makes_the_seeds_marks(self) -> None:
        for options in ({}, {"timesanity_minutes": 10}, {"timesanity_minutes": 7, "timesanity_hours": 1},
                        {"timesanity_minutes": 1440, "timesanity_hours": 23}):
            with self.subTest(options=options):
                multiworld = build(options)
                world = multiworld.worlds[1]
                made = [address - TIME_BASE for address in time_table.values()
                        if location_exists_with_options(world, address)]
                self.assertEqual((list(world.layout.marks), made), (made, [mark.minutes for mark in
                                                                           marks_of(multiworld)]))
        world = generate_early(named(50, 50, timesanity_minutes=10), slots=2)
        self.assertEqual([2_209_010, 2_209_020], [address for address in time_table.values()
                                                  if location_exists_with_options(world, address)])

    def test_marks_in_logic_by_canvas_items(self) -> None:
        # D21's table, through each mark's own rule. No other item moves a mark.
        multiworld = build({"timesanity_minutes": 10})
        marks, pool = marks_of(multiworld), multiworld.itempool
        others = [item for item in pool if item.advancement and "Canvas" not in item.name]
        for (width, height), minutes, in_logic in TABLE:
            state = CollectionState(multiworld)
            for name, copies in (("Progressive Canvas Width", width), ("Progressive Canvas Height", height)):
                for item in [item for item in pool if item.name == name][:copies]:
                    state.collect(item, prevent_sweep=True)
            with self.subTest(width=width, height=height):
                reached = [mark.minutes for mark in marks if mark.can_reach(state)]
                self.assertEqual(list(range(10, 10 * in_logic + 1, 10)), reached)
                for item in others:
                    state.collect(item, prevent_sweep=True)
                self.assertEqual(reached, [mark.minutes for mark in marks if mark.can_reach(state)])

    def test_auto_copy_out_of_logic(self) -> None:
        # At 0 h every mark turns progression away, any player's, and takes useful items, filler and traps. With auto
        # copy in logic it takes every item.
        progression = Item("Progression", ItemClassification.progression_skip_balancing, None, 2)
        for hours, takes_progression in ((0, False), (6, True)):
            multiworld = build({"timesanity_minutes": 10, "auto_copy_logic_hours": hours, "trap_count": 50}, slots=2)
            first = {}
            for item in multiworld.itempool:
                first.setdefault((item.player, item.classification), item)
            items = [first[player, ItemClassification.progression] for player in (1, 2)] + [progression]
            items += [first[1, kind] for kind in (ItemClassification.useful, ItemClassification.filler,
                                                  ItemClassification.trap)]
            marks = marks_of(multiworld)
            with self.subTest(auto_copy_logic_hours=hours):
                self.assertEqual(144, len(marks))
                self.assertEqual({(takes_progression,) * 3 + (True,) * 3},
                                 {tuple(mark.item_rule(item) for item in items) for mark in marks})

    def test_slot_data(self) -> None:
        # From version 1.2.0 (D21): auto_copy_time_targets lists every mark's minutes in order, [] with the family off,
        # beside timesanity_minutes and timesanity_hours as the YAML set them. A mark's id is 2,209,000 + its minutes.
        every_10 = list(range(10, 1441, 10))
        for options, targets, slots in (({}, [], 1), ({"timesanity_minutes": 10}, every_10, 1),
                                        ({"timesanity_minutes": 10}, every_10, 2),
                                        ({"timesanity_minutes": 10, "auto_copy_logic_hours": 0}, every_10, 1),
                                        ({"timesanity_minutes": 7, "timesanity_hours": 1},
                                         [7, 14, 21, 28, 35, 42, 49, 56], 1),
                                        ({"timesanity_minutes": 1440, "timesanity_hours": 23}, [], 1),
                                        (named(50, 50, timesanity_minutes=10), [10, 20], 2)):
            with self.subTest(options=options, slots=slots):
                world = generate_early(options, slots)
                slot_data = world.fill_slot_data()
                self.assertEqual((targets, options.get("timesanity_minutes", 0), options.get("timesanity_hours", 24)),
                                 (slot_data["auto_copy_time_targets"], slot_data["timesanity_minutes"],
                                  slot_data["timesanity_hours"]))
                self.assertEqual((list, int, int), (type(slot_data["auto_copy_time_targets"]),
                                                    type(slot_data["timesanity_minutes"]),
                                                    type(slot_data["timesanity_hours"])))
                self.assertEqual([], [minutes for minutes in slot_data["auto_copy_time_targets"]
                                      if type(minutes) is not int])
                self.assertEqual(slot_data, json.loads(json.dumps(slot_data)))
                self.assertEqual([TIME_BASE + minutes for minutes in targets],
                                 [address for address in time_table.values()
                                  if location_exists_with_options(world, address)])
        # 32 keys on every seed, Perfect Pixels' three and Missed Pixels' two among them (test_perfect_pixels.py and
        # test_missed_pixels.py), and the marks change no key but their own
        defaults, with_marks = generate_early({}).fill_slot_data(), generate_early({"timesanity_minutes": 10,
                                                                                     "timesanity_hours": 6})
        with_marks = with_marks.fill_slot_data()
        self.assertEqual((32, 32), (len(defaults), len(with_marks)))
        self.assertEqual({"auto_copy_time_targets", "timesanity_minutes", "timesanity_hours"},
                         {key for key in defaults if defaults[key] != with_marks[key]})


class TestTheMarksAndTheRefusals(unittest.TestCase):
    def test_the_item_count_counts_the_marks(self) -> None:
        # 0.1% from the start: 844 locations for 1,103 items. A mark every 10 minutes adds 144, still too few, and one
        # every minute 1,440, which pass the item count and the fill check.
        with self.assertRaisesRegex(OptionError, r"has 844 locations for 1103 required items\."):
            generate_early(TENTH_FROM_THE_START)
        with self.assertRaisesRegex(OptionError, r"has 988 locations for 1103 required items\."):
            generate_early({**TENTH_FROM_THE_START, "timesanity_minutes": 10})
        world = generate_early({**TENTH_FROM_THE_START, "timesanity_minutes": 1})
        self.assertEqual((2284, 844, 1103), (world.layout.location_count, world.layout.locations,
                                             len(world.non_filler_items())))

    def test_a_refusals_sample_counts_the_marks(self) -> None:
        # As the item count does: from 5 px steps at 0.1% from the start with a mark every minute, 100 px steps need
        # 1,103 items, for 844 similarity checks and 1,440 marks, and pass. Without the marks they don't.
        setup = layout(width_increment=5, height_increment=5, spacing=(50, 70, 0, 100, 100), timesanity_minutes=1)
        other = replace(setup, width_increment=100, height_increment=100)
        self.assertEqual((2284, 844), (other.location_count, other.locations))
        self.assertEqual((True, False), (change_fills(setup, other, 1367),
                                         change_fills(replace(setup, timesanity_minutes=0),
                                                      replace(other, timesanity_minutes=0), 1367)))

    def test_the_model_leaves_the_marks_out(self) -> None:
        # The fill check places progression on the similarity checks and Matched Pixels alone, so the marks change no
        # verdict: test_auto_copy_logic.py's, at the defaults, at 5 px steps with 0.05% from the start, and at 0 h.
        for changes, verdict in (({}, (3, 3)),
                                 (dict(spacing=(50, 70, 100, 0, 100), width_increment=5, height_increment=5), (0, 3)),
                                 (dict(auto_copy_logic_hours=0), (3, 3))):
            with self.subTest(changes=changes):
                self.assertEqual(verdict, passes_filled(layout(**changes, timesanity_minutes=1)))

    def test_a_refusal_names_the_marks_it_leaves_out(self) -> None:
        setup = layout(width_increment=5, height_increment=5, spacing=(50, 70, 100, 0, 100), timesanity_minutes=10)
        with mock.patch.object(rules, "passing_changes", return_value=([], 16)):
            message = refusal("P1", setup, 1367)
        self.assertEqual("P1's Pain-T world can't be filled alone: a model of Archipelago's fill, run on its logic "
                         "with fixed seeds, has to place every progression item in 3 of 5 tries. It filled 0 of the "
                         "first 3, and with 2 tries left it can't reach 3. The model places progression on the "
                         "similarity checks and Matched Pixels alone and leaves out this seed's 144 Auto Copy Time "
                         "checks. None of a sample of 16 single changes passes the check; try two at once, or play it "
                         "beside a Pain-T slot at the defaults. Beside other slots this check doesn't run, and "
                         "Archipelago's own fill decides.", message)
        with mock.patch.object(rules, "passing_changes", return_value=(["canvas_width_increment 10"], 16)):
            message = refusal("P1", layout(width_increment=5, height_increment=5, spacing=(50, 70, 100, 0, 100),
                                           timesanity_minutes=1), 1367, "raise")
        self.assertIn(" under the host's panic_method raise, run on its logic", message)
        self.assertIn(" The model places progression on the similarity checks and Matched Pixels alone and leaves out "
                      "this seed's 1,440 Auto Copy Time checks. From a sample of 16 single changes, these pass the "
                      "same check with nothing else changed: canvas_width_increment 10. Beside other slots this check "
                      "doesn't run, and Archipelago's own fill decides.", message)
        # At 0 h the marks take no progression, and nor do the other two families' checks, so the model leaves out
        # nothing that takes it and the refusal names none of them
        for changes in ({}, dict(missed_pixel_checks=24), dict(missed_pixel_checks=24, perfect_pixel_checks=5,
                                                                perfect_pixel_items="any")):
            with self.subTest(changes=changes):
                with mock.patch.object(rules, "passing_changes", return_value=([], 16)):
                    message = refusal("P1", layout(timesanity_minutes=10, auto_copy_logic_hours=0, **changes), 1103)
                self.assertNotIn("The model places", message)


class TestAFill(unittest.TestCase):
    def test_progression_on_the_marks(self) -> None:
        # Archipelago's fill, seed 1, a mark every minute: at 6 h progression lands on marks as on any check, and at
        # 0 h on none. Every mark holds an item.
        for hours in (6, 0):
            with self.subTest(auto_copy_logic_hours=hours):
                multiworld = setup_multiworld(PaintHardWorld, seed=1,
                                              options={"timesanity_minutes": 1, "auto_copy_logic_hours": hours})
                distribute_items_restrictive(multiworld)
                marks = marks_of(multiworld)
                self.assertEqual((1440, []), (len(marks), [mark.name for mark in marks if mark.item is None]))
                on_marks = len([mark for mark in marks if mark.item.advancement])
                if hours:
                    self.assertGreater(on_marks, 0)
                else:
                    self.assertEqual(0, on_marks)


class TestMarksOn(PaintHardTestBase):
    # A mark every 10 minutes: the base class's tests reach every location with every item, something with none, and
    # fill the seed.
    options = {"timesanity_minutes": 10}


class TestAMarkEveryMinute(PaintHardTestBase):
    options = {"timesanity_minutes": 1}


class TestMarksWithAutoCopyOutOfLogic(PaintHardTestBase):
    options = {"timesanity_minutes": 1, "auto_copy_logic_hours": 0}

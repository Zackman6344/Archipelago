"""Auto copy in logic (D8, Phase 5) and the solo fill check (D12), against hard-fork/plan_math.py, the plan's reference
math: its checks, ported, and its figures, taken from it with the checks of D21 off, since this world has none until
Phase 8. The check's model is also held to Archipelago's own fill in this checkout.
"""
import itertools
import unittest
from dataclasses import replace
from unittest import mock

import Fill
from BaseClasses import CollectionState, ItemClassification, MultiWorld
from Options import OptionError
from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all

from . import PaintHardTestBase
from .. import PaintHardWorld, rules
from ..rules import (KIND_ITEMS, KINDS, Layout, MISS, TIERS, TO_PASS, FillPass, fills, location_percents,
                     passes_filled, percent_available, paint_percent_available, progression_counts, refusal,
                     single_changes)

DEFAULT_SPACING = (50, 70, 100, 100, 0)  # half, quarter, tenth, twentieth and hundredth_percent_checks


def layout(**changes) -> Layout:
    """The defaults' layout: 800x600 from the 5x5 start in 100 px steps, a check every 0.01% to logic 80, 254 color
    items, auto copy at 6 h."""
    values = dict(final_width=800, final_height=600, start_width=5, start_height=5, width_increment=100,
                  height_increment=100, logic_percent=80, spacing=DEFAULT_SPACING, color_depth_items=254,
                  starting_color_depth=0, auto_copy_logic_hours=6)
    return Layout(**{**values, **changes})


def as_named(setup: Layout, name: str) -> Layout:
    """The layout a player gets from a refusal's change by setting what its name says, with nothing else changed."""
    words = name.split(" (")[0].split(" ")
    value, spacing, changes = int(words[-1]), list(setup.spacing), {}
    tiers = [option for option, _ in TIERS]
    for option in words[:-1]:
        if option in tiers:
            spacing[tiers.index(option)] = value
        elif option != "and":
            changes[option.removeprefix("canvas_")] = value
    return replace(setup, spacing=tuple(spacing), **changes)


def as_main_builds(options: dict, seed: int | None = None) -> MultiWorld:
    """A solo seed built as Main.py builds one: generate_early, then every copy both start inventory options name
    precollected, then the other steps, with start_inventory_from_pool's copies taken out of the pool for filler before
    pre_fill."""
    multiworld = setup_multiworld(PaintHardWorld, ("generate_early",), seed=seed, options=options)
    world = multiworld.worlds[1]
    for option in (world.options.start_inventory, world.options.start_inventory_from_pool):
        for name, copies in option.value.items():
            for _ in range(copies):
                multiworld.push_precollected(world.create_item(name))
    for step in gen_steps[1:-1]:
        call_all(multiworld, step)
    taken, pool = dict(world.options.start_inventory_from_pool.value), []
    for item in multiworld.itempool:
        if taken.get(item.name, 0):
            taken[item.name] -= 1
        else:
            pool.append(item)
    multiworld.itempool[:] = pool + [world.create_filler() for _ in range(len(multiworld.itempool) - len(pool))]
    call_all(multiworld, gen_steps[-1])
    return multiworld


# (color items in each channel, width and height items, speed and accuracy copies, Pick Color)
STATES = [(0, 0, 0, 0, 0, False), (1, 0, 0, 0, 0, False), (1, 1, 1, 0, 0, False), (10, 2, 2, 3, 2, False),
          (10, 2, 2, 3, 2, True), (40, 3, 2, 5, 4, True), (100, 4, 3, 6, 5, True), (200, 8, 6, 8, 9, True),
          (254, 8, 6, 10, 9, True), (254, 8, 6, 0, 0, True)]
# plan_math.percent_available() at those states. The last is the whole canvas with every color item and no auto copy
# items: what 1 pixel a second at 90% misses gets right in the hours, plus the 25 starting pixels by hand.
CEILINGS = {
    0: [1.6e-05, 0.002075, 0.915147, 5.246258, 6.344951, 10.175637, 20.426029, 79.372549, 80.0, 80.0],
    2: [1.6e-05, 0.002075, 0.06184, 2.612062, 2.612716, 10.175637, 20.426029, 79.372549, 80.0, 0.124167],
    6: [1.6e-05, 0.002075, 0.181369, 6.344951, 6.344951, 10.175637, 20.426029, 79.372549, 80.0, 0.364167],
    24: [1.6e-05, 0.002075, 0.719252, 6.344951, 6.344951, 10.175637, 20.426029, 79.372549, 80.0, 1.444167],
}
HALF_START_CEILINGS = [0.078431, 9.960784, 10.140078, 22.807216, 25.944471, 56.960784, 79.372549, 79.372549, 80.0,
                       20.36]
# States with more speed copies than the top tier's 10, as a YAML's start inventory can give them
PAST_THE_TOP = [(254, 8, 6, 11, 0, True), (254, 8, 6, 12, 0, True), (200, 8, 5, 11, 0, False)]
# plan_math.percent_available() at 1 h, at STATES and then at PAST_THE_TOP, which it reads as 10 copies. At 1 h the top
# tier at 90% misses gets 368,640 of the goal's 480,000 pixels right.
ONE_HOUR_CEILINGS = [1.6e-05, 0.002075, 0.031958, 1.307592, 1.308245, 9.378186, 20.426029, 79.372549, 80.0, 0.064167,
                     61.444167, 61.444167, 60.961239]
# plan_math.speed_progression() by auto_copy_logic_hours on 800x600, and at 1, 6 and 24 h on 800x800.
SPEED_PROGRESSION = [0, 10, 10, 9, 9, 9, 8, 8, 8, 8, 8, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 6, 6, 6, 6]
SPEED_PROGRESSION_800X800 = {1: 10, 6: 9, 24: 7}
# plan_math's fill check with the checks of D21 off, on its setups the item count lets through, and on 0.1% from the
# start, which fits with the smallest pool: (setup, layout changes, (tries that filled, tries run)).
CHECKS = [
    ("the defaults", {}, (3, 3)),
    ("14 color items, 1 free", dict(color_depth_items=14, starting_color_depth=1), (3, 3)),
    ("1 free color item", dict(starting_color_depth=1), (3, 3)),
    ("5 px steps", dict(width_increment=5, height_increment=5), (3, 3)),
    ("0.05% from the start", dict(spacing=(50, 70, 100, 0, 100)), (3, 3)),
    ("5 px steps, 0.05% from the start", dict(spacing=(50, 70, 100, 0, 100), width_increment=5, height_increment=5),
     (0, 3)),
    ("0.1% from the start", dict(spacing=(50, 70, 0, 100, 100)), (3, 3)),
    ("auto copy out of logic", dict(auto_copy_logic_hours=0), (3, 3)),
    ("2 h", dict(auto_copy_logic_hours=2), (3, 3)),
    ("21 color items, logic 50", dict(color_depth_items=21, logic_percent=50), (3, 3)),
]
# plan_math's setups the item count refuses, as options: (setup, options, (locations, items, items with the smallest
# pool)). The smallest pool has the tool ladders and the Overclock bank off and miss_margin_step 255.
SMALLEST_POOL = {"tool_size_ladders": False, "overclock_bank_size_items": 0, "overclock_fill_speed_items": 0,
                 "miss_margin_step": 255}
REFUSED_BY_THE_ITEM_COUNT = [
    ("0.1% from the start", {"tenth_percent_checks": 0, "hundredth_percent_checks": 100}, (844, 1103, 816)),
    ("Paint's spacing", {"hundredth_percent_checks": 100}, (174, 1103, 816)),
    ("5 px steps, 0.1% from the start", {"canvas_width_increment": 5, "canvas_height_increment": 5,
                                         "tenth_percent_checks": 0, "hundredth_percent_checks": 100},
     (844, 1367, 1080)),
    ("5 px steps, Paint's spacing", {"canvas_width_increment": 5, "canvas_height_increment": 5,
                                     "hundredth_percent_checks": 100}, (174, 1367, 1080)),
    ("25 px steps, Paint's spacing", {"canvas_width_increment": 25, "canvas_height_increment": 25,
                                      "hundredth_percent_checks": 100}, (174, 1145, 858)),
    ("the 400x300 start, Paint's spacing", {"starting_canvas": "half", "hundredth_percent_checks": 100},
     (149, 1096, 809)),
]
# Upstream's logic-55 rule, which refuses first (D12): a solo seed with both canvas steps under 50 needs logic_percent
# above 55. (setup, options, (tries that filled, tries run) when the rule lets it by)
UPSTREAMS_RULE = [
    # Without the rule the item count would refuse this one: 94 locations for 668 items
    ("logic 50, 5 px steps, Paint's spacing, 21 color items",
     {"logic_percent": 50, "canvas_width_increment": 5, "canvas_height_increment": 5, "hundredth_percent_checks": 100,
      "color_depth_items": 21}, None),
    ("logic 55, 25 px steps", {"logic_percent": 55, "canvas_width_increment": 25, "canvas_height_increment": 25},
     None),
    ("logic 56, 25 px steps", {"logic_percent": 56, "canvas_width_increment": 25, "canvas_height_increment": 25},
     (3, 3)),
    ("logic 55, 25x50 px steps", {"logic_percent": 55, "canvas_width_increment": 25, "canvas_height_increment": 50},
     (3, 3)),
]
UPSTREAMS_MESSAGE = ("Tester1's Pain-T world needs logic_percent above 55 when it plays alone with "
                     "canvas_width_increment and canvas_height_increment both below 50.")
# Setups near the check's edge, each with seeds where Archipelago's fill swaps 20 to 28 times: (setup, options, seeds).
# On the first, seed 2 fills and seed 5 fails; on the second, seed 2 fills and seed 4 fails; on the third, seed 8 fills.
NEAR_THE_EDGE = {"aspect_ratio": "square", "canvas_width_increment": 50, "canvas_height_increment": 10,
                 "logic_percent": 89, "color_depth_items": 9, "auto_copy_logic_hours": 18,
                 "twentieth_percent_checks": 10, "hundredth_percent_checks": 100, **SMALLEST_POOL}
REPLAYS = [
    ("800x800 at 50x10 px, logic 89, 9 color items, 18 h, 0.05% from 10%", NEAR_THE_EDGE, (2, 5)),
    ("800x800 at 20x100 px, logic 57, 28 color items with 3 free, 0.05% from 30%, 5 widths from the pool",
     {"aspect_ratio": "square", "canvas_width_increment": 20, "logic_percent": 57, "color_depth_items": 28,
      "starting_color_depth": 3, "twentieth_percent_checks": 30, "hundredth_percent_checks": 100,
      "start_inventory_from_pool": {"Progressive Canvas Width": 5}, **SMALLEST_POOL}, (2, 4)),
    ("the first, with Pick Color in start_inventory",
     {**NEAR_THE_EDGE, "start_inventory": {"Progressive Pick Color": 1}}, (8,)),
]


class TestTheCap(unittest.TestCase):
    def test_ceilings_match_the_plan(self) -> None:
        for hours, ceilings in CEILINGS.items():
            for (c, w, h, speed, accuracy, pick), ceiling in zip(STATES, ceilings):
                with self.subTest(hours=hours, state=(c, w, h, speed, accuracy, pick)):
                    self.assertEqual(ceiling, percent_available(layout(auto_copy_logic_hours=hours), c, c, c, w, h,
                                                                speed, accuracy, pick))
        for (c, w, h, speed, accuracy, pick), ceiling in zip(STATES, HALF_START_CEILINGS):
            with self.subTest(start="400x300", state=(c, w, h, speed, accuracy, pick)):
                self.assertEqual(ceiling, percent_available(layout(start_width=400, start_height=300), c, c, c, w, h,
                                                            speed, accuracy, pick))

    def test_no_speed_copy_counts_past_the_top_tier(self) -> None:
        # Logic reads at most the top tier's copies, layout.speed_items, as auto copy runs no faster.
        for (c, w, h, speed, accuracy, pick), ceiling in zip(STATES + PAST_THE_TOP, ONE_HOUR_CEILINGS):
            with self.subTest(hours=1, state=(c, w, h, speed, accuracy, pick)):
                self.assertEqual(ceiling, percent_available(layout(auto_copy_logic_hours=1), c, c, c, w, h, speed,
                                                            accuracy, pick))
        self.assertEqual(61.444167, percent_available(layout(auto_copy_logic_hours=1), 254, 254, 254, 8, 6, 10, 0,
                                                      True))

    def test_no_item_lowers_the_ceiling(self) -> None:
        # plan_math's check, over a coarser grid: adding any one item never lowers the ceiling.
        for setup in (layout(), layout(auto_copy_logic_hours=0), layout(start_width=400, start_height=300)):
            for c, w, h, speed, accuracy, pick in itertools.product((0, 1, 8, 100, 253), (0, 1, 4, 8), (0, 1, 3, 6),
                                                                     (0, 1, 4, 7, 8, 9, 10), (0, 1, 5, 8, 9),
                                                                     (False, True)):
                base = percent_available(setup, c, c, c, w, h, speed, accuracy, pick)
                for more in ((c + 1, c, c, w, h, speed, accuracy, pick), (c, c, c, w + 1, h, speed, accuracy, pick),
                             (c, c, c, w, h + 1, speed, accuracy, pick), (c, c, c, w, h, speed + 1, accuracy, pick),
                             (c, c, c, w, h, speed, accuracy + 1, pick), (c, c, c, w, h, speed, accuracy, True)):
                    if percent_available(setup, *more) < base:
                        self.fail(f"{more} lowers the ceiling below {base} at {setup}")

    def test_every_item_reaches_the_logic_percent(self) -> None:
        # D19: with every item each goal is fully in logic, at any hours and steps, and no speed copy is spare.
        for (w, h), hours, step in itertools.product(((800, 600), (800, 450), (800, 800), (450, 800), (600, 800)),
                                                     range(25), (5, 100)):
            setup = layout(final_width=w, final_height=h, auto_copy_logic_hours=hours, width_increment=step,
                           height_increment=step)
            with self.subTest(goal=(w, h), hours=hours, step=step):
                self.assertEqual(80.0, percent_available(setup, 254, 254, 254, *setup.canvas_items, setup.speed_items,
                                                         len(MISS) - 1, True))
                self.assertEqual(10, setup.speed_items)

    def test_copies_that_can_raise_the_cap(self) -> None:
        self.assertEqual(SPEED_PROGRESSION, [layout(auto_copy_logic_hours=hours).speed_progression
                                             for hours in range(25)])
        for hours, copies in SPEED_PROGRESSION_800X800.items():
            self.assertEqual(copies, layout(final_height=800, auto_copy_logic_hours=hours).speed_progression)
        # Accuracy copies: at 1 pixel a second each raises the cap on these goals at any hours.
        self.assertEqual([0] + [9] * 24, [layout(auto_copy_logic_hours=hours).accuracy_progression
                                          for hours in range(25)])

    def test_copies_on_big_and_small_goals(self) -> None:
        # D19: a goal bigger than 10 speed copies paint in 6 h gets more copies, and every item still reaches the
        # logic percent. D8: accuracy copy a can raise the cap while a / 10 x hours x 3,600 is below the goal's pixels,
        # so 77,562 pixels at 24 h get 8 and 77,841 get all 9.
        for (w, h), speed in (((8192, 8192), 12), ((16384, 16384), 14)):
            setup = layout(final_width=w, final_height=h)
            with self.subTest(goal=(w, h)):
                self.assertEqual(speed, setup.speed_items)
                self.assertEqual(80.0, percent_available(setup, 254, 254, 254, *setup.canvas_items, speed,
                                                         len(MISS) - 1, True))
        for (w, h), hours, accuracy in (((100, 100), 6, 4), ((50, 50), 1, 6), ((278, 279), 24, 8),
                                        ((279, 279), 24, 9)):
            with self.subTest(goal=(w, h), hours=hours):
                self.assertEqual(accuracy, layout(final_width=w, final_height=h,
                                                  auto_copy_logic_hours=hours).accuracy_progression)


class TestTheFillCheck(unittest.TestCase):
    def test_verdicts_match_the_plan(self) -> None:
        for name, changes, expected in CHECKS:
            with self.subTest(setup=name):
                setup = layout(**changes)
                self.assertEqual((expected, expected[0] >= TO_PASS), (passes_filled(setup), fills(setup)))

    def test_each_change_tried_is_what_its_name_sets(self) -> None:
        # The steps of W2's setup, 5x25 from the 400x300 start, and the 5x5 steps of D12's example, the last with 10
        # widths and 10 heights from the pool, which each change keeps
        canvas = (0, 0, 0, 10, 10, 0, 0, 0)
        for setup in (layout(start_width=400, start_height=300, width_increment=5, height_increment=25,
                             spacing=(50, 70, 100, 100, 100), color_depth_items=28, logic_percent=99),
                      layout(width_increment=5, height_increment=5, spacing=(50, 70, 100, 0, 100)),
                      layout(width_increment=5, height_increment=5, spacing=(50, 70, 100, 0, 100),
                             precollected=canvas, from_pool=canvas)):
            for name, other in itertools.chain(*single_changes(setup)):
                with self.subTest(steps=(setup.width_increment, setup.height_increment), change=name):
                    self.assertEqual(as_named(setup, name), other)

    def test_upstreams_rule_refuses_first(self) -> None:
        for name, options, tries in UPSTREAMS_RULE:
            with self.subTest(setup=name):
                if tries is None:
                    with self.assertRaises(OptionError) as raised:
                        setup_multiworld(PaintHardWorld, ("generate_early",), options=options)
                    self.assertEqual(UPSTREAMS_MESSAGE, str(raised.exception))
                else:
                    world = setup_multiworld(PaintHardWorld, ("generate_early",), options=options).worlds[1]
                    self.assertEqual(tries, passes_filled(world.layout))

    def test_the_item_count_refuses_first(self) -> None:
        for name, options, (locations, items, smallest) in REFUSED_BY_THE_ITEM_COUNT:
            with self.subTest(setup=name):
                with self.assertRaisesRegex(OptionError, rf"has {locations} locations for {items} required items\."):
                    setup_multiworld(PaintHardWorld, ("generate_early",), options=options)
                if smallest > locations:
                    with self.assertRaisesRegex(OptionError, rf"has {locations} locations for {smallest} required "
                                                             rf"items\."):
                        setup_multiworld(PaintHardWorld, ("generate_early",), options={**options, **SMALLEST_POOL})
                else:
                    world = setup_multiworld(PaintHardWorld, ("generate_early",),
                                             options={**options, **SMALLEST_POOL}).worlds[1]
                    self.assertEqual((locations, smallest), (world.layout.locations, len(world.non_filler_items())))

    def test_the_last_resort(self) -> None:
        # The sentence a refusal ends with when no single change in its sample passes
        setup = layout(width_increment=5, height_increment=5, spacing=(50, 70, 100, 0, 100))
        with mock.patch.object(rules, "passing_changes", return_value=([], 16)):
            message = refusal("P1", setup, 1367)
        self.assertEqual("P1's Pain-T world can't be filled alone: a model of Archipelago's fill, run on its logic "
                         "with fixed seeds, placed every progression item in 0 of 3 tries, where 3 of 5 must. None of "
                         "a sample of 16 single changes passes it; try two at once, or play it beside a Pain-T slot at "
                         "the defaults.", message)

    def test_start_inventory_from_pool_takes_progression_first(self) -> None:
        # Main.py takes a name's first copies out of the pool, which create_items() leaves progression: at 6 h 9 speed
        # copies take the 8 progression ones, and 2 Pick Colors take the progression one.
        setup = replace(layout(), from_pool=(1, 0, 0, 2, 0, 9, 3, 2))
        self.assertEqual((253, 254, 254, 6, 6, 0, 6, 0), progression_counts(setup))


class TestLogicCountsAutoCopy(PaintHardTestBase):
    def test_a_state_reads_as_its_items(self) -> None:
        state = CollectionState(self.multiworld)
        pool = self.multiworld.itempool

        def take(name: str, copies: int) -> None:
            for item in [item for item in pool if item.name == name][:copies]:
                state.collect(item, prevent_sweep=True)

        for channel in ("Red", "Green", "Blue"):
            take(f"Progressive Color Depth ({channel})", 10)
        take("Progressive Canvas Width", 2)
        take("Progressive Canvas Height", 2)
        take("Progressive Auto Copy Speed", 3)
        take("Progressive Auto Copy Accuracy", 2)
        take("Progressive Pick Color", 1)
        self.assertEqual(CEILINGS[6][4], paint_percent_available(state, self.world, self.player))
        # A speed copy that can't raise the cap is useful, so a state doesn't count it.
        useful = next(item for item in pool if item.name == "Progressive Auto Copy Speed" and
                      item.classification == ItemClassification.useful)
        state.collect(useful, prevent_sweep=True)
        self.assertEqual(3, state.count("Progressive Auto Copy Speed", self.player))
        self.assertEqual(CEILINGS[6][4], paint_percent_available(state, self.world, self.player))

    def test_the_world_keeps_the_defaults_layout(self) -> None:
        self.assertEqual(layout(), self.world.layout)
        self.assertEqual((3, 3), passes_filled(self.world.layout))
        self.assertEqual(6, self.world.fill_slot_data()["auto_copy_logic_hours"])

    def test_the_version_marks_auto_copy_in_logic(self) -> None:
        # Phase 4's seeds carry 1.0.0, and their slot data differs from Phase 5's only by auto_copy_logic_hours.
        self.assertEqual("1.1.0", self.world.fill_slot_data()["version"])


class TestStartInventory(unittest.TestCase):
    def test_a_speed_copy_past_the_top_tier(self) -> None:
        # One speed copy in start_inventory at 1 h: create_item makes it progression, and with the pool's 10 a state
        # holds 11. Every progression item but accuracy reads the top tier's 61.444167.
        multiworld = as_main_builds({"auto_copy_logic_hours": 1,
                                     "start_inventory": {"Progressive Auto Copy Speed": 1}})
        state = CollectionState(multiworld)
        for item in multiworld.itempool:
            if item.advancement and item.name != "Progressive Auto Copy Accuracy":
                state.collect(item, prevent_sweep=True)
        self.assertEqual(11, state.count("Progressive Auto Copy Speed", 1))
        self.assertEqual(61.444167, paint_percent_available(state, multiworld.worlds[1], 1))

    def test_the_pool_holds_what_the_check_places(self) -> None:
        # start_inventory_from_pool at 6 h: 9 speed copies take the 8 progression ones and a useful one, 2 Pick Colors
        # both copies, and 3 accuracy copies leave 6.
        multiworld = as_main_builds({"start_inventory_from_pool": {
            "Progressive Auto Copy Speed": 9, "Progressive Pick Color": 2, "Progressive Auto Copy Accuracy": 3,
            "Progressive Canvas Width": 2}})
        progression = [0] * len(KINDS)
        for item in multiworld.itempool:
            if item.advancement:
                progression[KIND_ITEMS.index(item.name)] += 1
        setup = multiworld.worlds[1].layout
        self.assertEqual(((0, 0, 0, 2, 0, 9, 3, 2), (254, 254, 254, 6, 6, 0, 6, 0)),
                         (setup.from_pool, progression_counts(setup)))
        self.assertEqual(progression_counts(setup), tuple(progression))


class TestTheCheckModelsArchipelagosFill(unittest.TestCase):
    def test_fill_restrictive_places_as_the_model_does(self) -> None:
        # Archipelago's own progression fill in this checkout, and FillPass on the item and location orders it was
        # handed: the same outcome, and the same placements when it fills. A core whose fill places otherwise fails.
        for name, options, seeds in REPLAYS:
            for seed in seeds:
                with self.subTest(setup=name, seed=seed):
                    multiworld = as_main_builds(options, seed)
                    orders, fill_restrictive = {}, Fill.fill_restrictive

                    def capture(world, base_state, locations, item_pool, *args, **kwargs) -> None:
                        if kwargs.get("name") == "Progression":
                            orders["items"], orders["locations"] = [item.name for item in item_pool], list(locations)
                        fill_restrictive(world, base_state, locations, item_pool, *args, **kwargs)

                    with mock.patch.object(Fill, "fill_restrictive", capture):
                        try:
                            Fill.distribute_items_restrictive(multiworld)
                            filled = True
                        except Fill.FillError:
                            filled = False
                    setup = multiworld.worlds[1].layout
                    ordered = sorted(orders["locations"], key=lambda location: (location.required_percent,
                                                                                location.address))
                    self.assertEqual(location_percents(setup), [location.required_percent for location in ordered])
                    index = {location.address: place for place, location in enumerate(ordered)}
                    pool = [KIND_ITEMS.index(item) for item in orders["items"]]
                    self.assertEqual(progression_counts(setup), tuple(pool.count(kind) for kind in range(len(KINDS))))
                    model = FillPass(setup, 0)
                    self.assertEqual(filled, model.fill(pool, [index[location.address]
                                                               for location in orders["locations"]]))
                    self.assertGreater(model.swaps, 0)
                    if filled:
                        self.assertEqual(dict(model.placements),
                                         {index[location.address]: KIND_ITEMS.index(location.item.name)
                                          for location in orders["locations"] if location.item.advancement})

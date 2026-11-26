"""Goals at more sizes (task 7.9's first half, D19), against hard-fork/plan_math.py: each world built once, alone,
through set_rules and without Archipelago's fill, which fills big goals 65 to 95% of the time. Its pool, locations,
classes and slot data, and every location and the goal in reach with every item. Then the fill check's verdicts on big
goals with the families off, D19's cells and 4096x4096's, and the three families at the plan's defaults on big goals:
the async's 4096x4096 at 100, 50 and 25 px steps, 4000x3000, and 8192x8192 and 16384x16384, whose 12, 14 and 17 speed
copies each open their own run of Missed Pixels checks (D26).
"""
import unittest
from collections import Counter

from BaseClasses import CollectionState, MultiWorld
from test.general import setup_multiworld

from .. import PaintHardWorld
from ..locations import AutoCopyTimeLocation, MissedPixelsLocation, PerfectPixelsLocation
from ..rules import KIND_ITEMS, happy_count, paint_percent_available, passes_filled, progression_counts
from .test_auto_copy_logic import layout
from .test_goal_options import named

# plan_math's figures alone at 100 px steps from the 5x5 start at 6 h, the families off: (goal, width and height items,
# speed copies, progression speed copies, progression accuracy copies, non-filler items, progression items, the fill
# check's tries that filled and tries run). Every size has the 8,043 similarity checks and Matched Pixels.
SIZES = [
    ((50, 50), (1, 1), 10, 1, 1, 1091, 767, (3, 3)),
    ((800, 600), (8, 6), 10, 8, 9, 1103, 794, (3, 3)),
    ((2000, 1500), (20, 15), 10, 10, 9, 1124, 817, (3, 3)),
    ((4000, 3000), (40, 30), 10, 10, 9, 1159, 852, (3, 3)),
    ((4096, 4096), (41, 41), 10, 10, 9, 1171, 864, (3, 3)),
    ((8192, 8192), (82, 82), 12, 12, 9, 1255, 948, (3, 3)),
    ((16384, 16384), (164, 164), 14, 14, 9, 1421, 1114, (3, 4)),
    ((16384, 50), (164, 1), 10, 9, 9, 1254, 946, (3, 3)),
    ((50, 16384), (1, 164), 10, 9, 9, 1254, 946, (3, 3)),
]
# The fill check's verdicts at each canvas step, the families off, as plan_math.passes_filled() gives them: D19's table
# for 4000x3000, 8192x8192 and 16384x16384, and the async's 4096x4096, which passes down to 20 px
CELLS = {
    (4000, 3000): {100: (3, 3), 50: (3, 3), 25: (3, 3), 20: (3, 3), 10: (3, 4), 5: (0, 3)},
    (8192, 8192): {100: (3, 3), 50: (3, 3), 25: (1, 4)},
    (16384, 16384): {100: (3, 4), 50: (0, 3)},
    (4096, 4096): {100: (3, 3), 50: (3, 3), 25: (3, 3), 20: (3, 3), 10: (0, 3)},
}
# The three families at the plan's defaults (D21, D26)
PLAN_FAMILIES = {"perfect_pixel_checks": 5, "timesanity_minutes": 10, "missed_pixel_checks": 24}
# plan_math.room_counts() with the families at the plan's defaults: (goal, canvas step, auto_copy_logic_hours,
# locations, Perfect Pixels checks, Auto Copy Time marks, Missed Pixels checks, non-filler items, progression items,
# locations that take progression)
FAMILY_SIZES = [
    ((4096, 4096), 100, 6, 8885, 410, 144, 288, 1172, 865, 8475),
    ((4096, 4096), 50, 6, 9295, 820, 144, 288, 1254, 947, 8475),
    ((4096, 4096), 25, 6, 10113, 1638, 144, 288, 1418, 1111, 8475),
    ((4000, 3000), 100, 6, 8825, 350, 144, 288, 1160, 853, 8475),
    ((8192, 8192), 100, 6, 9343, 820, 144, 336, 1256, 949, 8523),
    ((16384, 16384), 100, 6, 10209, 1638, 144, 384, 1422, 1115, 8571),
    ((16384, 16384), 100, 1, 10281, 1638, 144, 456, 1425, 1118, 8643),
]
# plan_math.missed_in_logic() at missed_pixel_checks 24 with Happy Accident, at 0 speed copies and each one more up to
# the top tier, on goals whose top tier is 12, 14 and 17 copies: 48 for the item alone, then 24 for each copy
UP_THE_LADDER = {12: [48 + 24 * copies for copies in range(13)], 14: [48 + 24 * copies for copies in range(15)],
                 17: [48 + 24 * copies for copies in range(18)]}
SPEED = "Progressive Auto Copy Speed"


def alone(options: dict) -> MultiWorld:
    """A solo seed through set_rules with these options, refused where generate_early refuses it."""
    return setup_multiworld(PaintHardWorld, ("generate_early", "create_regions", "create_items", "set_rules"), seed=1,
                            options=options)


def options_for(goal: tuple[int, int], step: int = 100, **options) -> dict:
    """The options of a goal of this size, named by a URL unless it is the defaults' 800x600, at this canvas step."""
    steps = {"canvas_width_increment": step, "canvas_height_increment": step}
    return {**steps, **options} if goal == (800, 600) else named(*goal, **steps, **options)


class TestEachSize(unittest.TestCase):
    def test_each_size_alone(self) -> None:
        for goal, canvas, speed, speed_progression, accuracy, items, progression, tries in SIZES:
            with self.subTest(goal=goal):
                multiworld = alone(options_for(goal))
                world, pool = multiworld.worlds[1], multiworld.itempool
                setup = world.layout
                self.assertEqual((goal, (5, 5), canvas, speed, speed_progression, accuracy, tries),
                                 ((setup.final_width, setup.final_height), (setup.start_width, setup.start_height),
                                  setup.canvas_items, setup.speed_items, setup.speed_progression,
                                  setup.accuracy_progression, passes_filled(setup)))
                # The pool: a location for each item, the non-filler items, and the progression items by kind, as the
                # fill check counts them
                self.assertEqual((8043, 8043, items, progression),
                                 (len(multiworld.get_locations(1)), len(pool), len(world.non_filler_items()),
                                  len([item for item in pool if item.advancement])))
                by_kind = Counter(item.name for item in pool if item.advancement)
                self.assertEqual(progression_counts(setup), tuple(by_kind[name] for name in KIND_ITEMS))
                slot_data = world.fill_slot_data()
                self.assertEqual((*goal, 5, 5, speed, 8043 - 18 - 25, 25),
                                 tuple(slot_data[key] for key in ("final_width", "final_height", "start_width",
                                                                  "start_height", "auto_copy_speed_items")) +
                                 (len([location for location in multiworld.get_locations(1)
                                       if location.address > 2_199_000]), slot_data["matched_pixels"]))
                # Every item reaches the logic percent, every location and the goal
                state = multiworld.get_all_state()
                self.assertEqual(80.0, paint_percent_available(state, world, 1))
                self.assertEqual([], [location.name for location in multiworld.get_locations(1)
                                      if not location.can_reach(state)])
                self.assertTrue(multiworld.completion_condition[1](state))

    def test_the_fill_checks_verdicts_on_big_goals(self) -> None:
        for (width, height), verdicts in CELLS.items():
            for step, tries in verdicts.items():
                with self.subTest(goal=(width, height), step=step):
                    self.assertEqual(tries, passes_filled(layout(final_width=width, final_height=height,
                                                                 width_increment=step, height_increment=step)))


class TestTheFamiliesOnBigGoals(unittest.TestCase):
    def test_the_plan_defaults_alone(self) -> None:
        # Each passes every refusal alone. The marks and Missed Pixels don't grow with the goal, but the Missed Pixels
        # do with the speed copies: 12 on 8192x8192, 14 on 16384x16384 at 6 h and 17 at 1 h. With every item every
        # location is in logic and the goal is reached.
        for goal, step, hours, locations, perfect, marks, missed, items, progression, taking in FAMILY_SIZES:
            with self.subTest(goal=goal, step=step, auto_copy_logic_hours=hours):
                multiworld = alone(options_for(goal, step, auto_copy_logic_hours=hours, **PLAN_FAMILIES))
                world, pool = multiworld.worlds[1], multiworld.itempool
                setup = world.layout
                made = Counter(type(location).__name__ for location in multiworld.get_locations(1))
                self.assertEqual((locations, perfect, marks, missed),
                                 (len(multiworld.get_locations(1)), made[PerfectPixelsLocation.__name__],
                                  made[AutoCopyTimeLocation.__name__], made[MissedPixelsLocation.__name__]))
                self.assertEqual((locations, items, progression, progression, taking),
                                 (len(pool), len(world.non_filler_items()),
                                  len([item for item in pool if item.advancement]),
                                  sum(progression_counts(setup)) + happy_count(setup), setup.taking_count))
                state = multiworld.get_all_state()
                self.assertEqual([], [location.name for location in multiworld.get_locations(1)
                                      if not location.can_reach(state)])
                self.assertTrue(multiworld.completion_condition[1](state))

    def test_each_speed_copy_opens_its_run_of_missed_pixels(self) -> None:
        # Through each check's own rule, with every progression item but the speed copies and Happy Accident: none
        # without the item, 48 with it, then 24 more for each speed copy up to every check at the top tier, and none
        # more from a copy past it, as start inventory can give
        for goal, hours, copies in (((8192, 8192), 6, 12), ((16384, 16384), 6, 14), ((16384, 16384), 1, 17)):
            with self.subTest(goal=goal, auto_copy_logic_hours=hours):
                multiworld = alone(options_for(goal, auto_copy_logic_hours=hours, **PLAN_FAMILIES))
                world, pool = multiworld.worlds[1], multiworld.itempool
                checks = [location for location in multiworld.get_locations(1)
                          if isinstance(location, MissedPixelsLocation)]
                self.assertEqual(copies, world.layout.speed_items)
                state = CollectionState(multiworld)
                for item in pool:
                    if item.advancement and item.name not in (SPEED, "Happy Accident"):
                        state.collect(item, prevent_sweep=True)
                reached = [sum(check.can_reach(state) for check in checks)]
                state.collect(next(item for item in pool if item.name == "Happy Accident"), prevent_sweep=True)
                speed_copies = [item for item in pool if item.name == SPEED]
                self.assertEqual(copies, len([item for item in speed_copies if item.advancement]))
                for item in speed_copies + [world.create_item(SPEED)]:
                    reached.append(sum(check.can_reach(state) for check in checks))
                    state.collect(item, prevent_sweep=True)
                reached.append(sum(check.can_reach(state) for check in checks))
                self.assertEqual([0] + UP_THE_LADDER[copies] + [len(checks)], reached)
                self.assertEqual((copies + 2) * 24, len(checks))

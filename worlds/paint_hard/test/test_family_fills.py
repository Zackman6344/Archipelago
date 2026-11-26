"""Archipelago's own fill on seeds with the families of D21 and D26 (tasks 8.6 and 8.10, the world's part), beyond the
fills at seed 1 that test_perfect_pixels.py and test_missed_pixels.py run: Perfect Pixels in each mode at two more
seeds and in each mode with auto copy out of logic, 720 Missed Pixels checks a speed copy, and Perfect Pixels at any
beside the Missed Pixels and the marks. Each counts what lands on the checks, and every location of each seed is
reached sphere by sphere.
"""
import unittest
from collections import Counter

from BaseClasses import MultiWorld
from Fill import distribute_items_restrictive
from test.general import setup_multiworld
from worlds.AutoWorld import call_all

from .. import PaintHardWorld
from .test_auto_copy_time import marks_of
from .test_missed_pixels import missed_of
from .test_perfect_pixels import kind, perfect_of, reaches_every_location

FIVE_A_STEP = {"perfect_pixel_checks": 5}
PLAN_FAMILIES = {"perfect_pixel_checks": 5, "timesanity_minutes": 10, "missed_pixel_checks": 24}


def filled(options: dict, seed: int) -> MultiWorld:
    """A solo seed with these options after Archipelago's fill, as Main.py runs it."""
    multiworld = setup_multiworld(PaintHardWorld, seed=seed, options=options)
    distribute_items_restrictive(multiworld)
    call_all(multiworld, "post_fill")
    return multiworld


class TestPerfectPixelsFills(unittest.TestCase):
    def test_each_mode_at_more_seeds(self) -> None:
        # At any progression lands on the checks, at useful none does, and at filler they hold filler and traps alone
        for seed in (2, 3):
            for mode in ("any", "useful", "filler"):
                with self.subTest(seed=seed, perfect_pixel_items=mode):
                    multiworld = filled({**FIVE_A_STEP, "perfect_pixel_items": mode, "trap_count": 50}, seed)
                    held = Counter(kind(check.item) for check in perfect_of(multiworld))
                    self.assertEqual(70, sum(held.values()))
                    if mode == "any":
                        self.assertGreater(held["progression"], 0)
                    else:
                        self.assertEqual(0, held["progression"] + (held["useful"] if mode == "filler" else 0))
                    self.assertTrue(reaches_every_location(multiworld))

    def test_each_mode_with_auto_copy_out_of_logic(self) -> None:
        # At 0 h no mode lets progression on them, and filler still keeps useful items off
        for mode in ("useful", "filler", "any"):
            with self.subTest(perfect_pixel_items=mode):
                multiworld = filled({**FIVE_A_STEP, "perfect_pixel_items": mode, "auto_copy_logic_hours": 0,
                                     "trap_count": 50}, 1)
                held = Counter(kind(check.item) for check in perfect_of(multiworld))
                self.assertEqual((70, 0), (sum(held.values()), held["progression"]))
                if mode == "filler":
                    self.assertEqual(0, held["useful"])
                self.assertTrue(reaches_every_location(multiworld))


class TestMissedPixelsFills(unittest.TestCase):
    def test_720_a_speed_copy(self) -> None:
        # 8,640 checks: progression lands on them, Happy Accident among the pool's, and every location is reached
        multiworld = filled({"missed_pixel_checks": 720}, 1)
        checks = missed_of(multiworld)
        held = Counter(kind(check.item) for check in checks)
        self.assertEqual(8640, len(checks))
        self.assertGreater(held["progression"], 0)
        self.assertEqual(1, [item.name for item in multiworld.itempool].count("Happy Accident"))
        self.assertTrue(reaches_every_location(multiworld))


class TestEveryFamilyFills(unittest.TestCase):
    def test_perfect_pixels_at_any_beside_the_others(self) -> None:
        # The plan's defaults with Perfect Pixels at any, at two seeds: progression lands on the Missed Pixels checks
        # and the marks, the Perfect Pixels checks take their share, and every location is reached
        for seed in (1, 2):
            with self.subTest(seed=seed):
                multiworld = filled({**PLAN_FAMILIES, "perfect_pixel_items": "any"}, seed)
                families = {"Perfect Pixels": perfect_of(multiworld), "Auto Copy Time": marks_of(multiworld),
                            "Missed Pixels": missed_of(multiworld)}
                self.assertEqual((70, 144, 288), tuple(len(checks) for checks in families.values()))
                progression = {family: sum(check.item.advancement for check in checks)
                               for family, checks in families.items()}
                self.assertGreater(progression["Missed Pixels"], 0)
                self.assertGreater(progression["Auto Copy Time"], 0)
                self.assertTrue(reaches_every_location(multiworld))

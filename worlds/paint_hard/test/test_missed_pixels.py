"""Missed Pixels and Happy Accident (D26, task 8.7) against hard-fork/plan_math.py: the ladder of targets a seed makes,
the rule that holds every check until Happy Accident is found and then opens each speed copy's run, the speed copies'
class while the family is on, the checks in a seed with their ids, item rule and slot data, the item count and the
solo refusal, and Archipelago's fill, alone and beside a second slot. In this release the checks are off by default
(test_check_families.py).
"""
import itertools
import json
import unittest
from bisect import bisect_right
from collections import Counter
from dataclasses import replace
from unittest import mock

from BaseClasses import CollectionState, Item, ItemClassification, MultiWorld
from Fill import distribute_items_restrictive
from Options import OptionError
from test.general import setup_multiworld
from worlds.AutoWorld import call_all

from . import PaintHardTestBase
from .. import PaintHardWorld, location_exists_with_options, rules
from ..locations import MISSED_BASE, MissedPixelsLocation, missed_table
from ..rules import (MISSED_NAMES, change_fills, copy_budget, ladder_values, missed_reach, passes_filled,
                     percent_available, progression_counts, refusal, unlocked_area)
from .test_auto_copy_logic import SPEED_PROGRESSION, as_main_builds, layout
from .test_auto_copy_time import build
from .test_goal_options import generate_early, named
from .test_perfect_pixels import digest, kind, reaches_every_location

K24 = {"missed_pixel_checks": 24}
# The layout changes that give each count of speed copies (D19): 800x600, then 8192x8192 and 16384x16384 at 6 h, and
# 16384x16384 at 1 h
COPIES = {10: {}, 12: dict(final_width=8192, final_height=8192), 14: dict(final_width=16384, final_height=16384),
          17: dict(final_width=16384, final_height=16384, auto_copy_logic_hours=1)}
# plan_math.missed_targets() for (speed copies, timesanity_hours, missed_pixel_checks): how many targets, the first
# three, the last two, and the SHA-256 of the whole list written as numbers joined by commas
TARGETS = [
    ((10, 1, 1), 12, (1800, 3600, 7200), (1843200, 3686400),
     "5fc1cc0c3ea55675a9852efe361b61c8cbae53b0411ff49aae2ba0ac95e5f79c"),
    ((10, 1, 24), 288, (75, 150, 225), (3609600, 3686400),
     "084b36dd17ad41e6a49ecd6315c75a63d61a83fad801aae44c0e3b5ae8b6ec34"),
    ((10, 1, 720), 8640, (3, 5, 8), (3683840, 3686400),
     "03831f914ed0cbe45ad17dd07196a4a10c37de6284d46add88466c5a9e0fd10c"),
    ((10, 6, 1), 12, (10800, 21600, 43200), (11059200, 22118400),
     "b13b698f0bc379179aab855aefec0f16e6948f7a1f83e3ff27c4a6dce7eebfab"),
    ((10, 6, 24), 288, (450, 900, 1350), (21657600, 22118400),
     "79109dbd288e8560c155f11f962937bf35c6f34fcead77e0880bb612529e677a"),
    ((10, 6, 720), 8640, (15, 30, 45), (22103040, 22118400),
     "0d7b0446c8473da567b45e46224a1b9966e24486f6d631fc096e9932ac9b467b"),
    # The defaults' ladder (D26): 48 from 1,800 to 86,400 for Happy Accident alone, then 24 for each copy, to 88,473,600
    ((10, 24, 1), 12, (43200, 86400, 172800), (44236800, 88473600),
     "1a404bfe3219805f11584791e4ee3eb37caa016d745fe3f6a781c0e13b3fe9f9"),
    ((10, 24, 24), 288, (1800, 3600, 5400), (86630400, 88473600),
     "a5eff6bf96589ecbc13547321b4b17d151acdfa4be037d701ead8471f4a0ea2a"),
    ((10, 24, 720), 8640, (60, 120, 180), (88412160, 88473600),
     "11b27e36657af9b33778b98581e1876ccb9d9e26f009f18445e272671c87232d"),
    ((12, 1, 1), 14, (1800, 3600, 7200), (7372800, 14745600),
     "9ea0cd700a4b5bca24ac030eef51d6fd401f3453e21a322bad73a3f44cdca32f"),
    ((12, 1, 24), 336, (75, 150, 225), (14438400, 14745600),
     "a926f99547900109ce298f94bae747958799957d59d7db4d3d3fbe5d51d78546"),
    ((12, 1, 720), 10080, (3, 5, 8), (14735360, 14745600),
     "9a761bd2f7db4e62be1e8480e18679bcb0645e6fdba07add297f3a827f18b015"),
    ((12, 6, 1), 14, (10800, 21600, 43200), (44236800, 88473600),
     "6fe61b1e37179cc669c105adc3efcefd0b064ab7de075da0c894ad5015b0e173"),
    ((12, 6, 24), 336, (450, 900, 1350), (86630400, 88473600),
     "22a5b63d087f3abbb9749385a236be81f90e6ffec7d16b32b5bfc0b626c97f18"),
    ((12, 6, 720), 10080, (15, 30, 45), (88412160, 88473600),
     "066d9fec5fcfda027b93dbae9058d2e2e2c99801893222481853d6b55df3398d"),
    ((12, 24, 1), 14, (43200, 86400, 172800), (176947200, 353894400),
     "ae7eddb6e1efc08310dcdc2e84d11ae198253252ed9a7e5ad17e0d26ea0b9ad2"),
    ((12, 24, 24), 336, (1800, 3600, 5400), (346521600, 353894400),
     "fa4ffee0e3b6510734af7cd2ccee942b5722fa42344613fd7fd11aca78c8903e"),
    ((12, 24, 720), 10080, (60, 120, 180), (353648640, 353894400),
     "9ad0a0c2637efe9c174be90987f0e5717f1a73b17223ddab9527c14e053d247b"),
    ((14, 1, 1), 16, (1800, 3600, 7200), (29491200, 58982400),
     "32ae7471d632b2af08bbdac2a9b7accad0a5b3404b5d6c2ea063c72587dd5420"),
    ((14, 1, 24), 384, (75, 150, 225), (57753600, 58982400),
     "068a50a09f35a953a6dcedd100fbb205d69e1962eff2b7838a0e06b0c2d466d4"),
    ((14, 1, 720), 11520, (3, 5, 8), (58941440, 58982400),
     "29e3474479f02f725b48f9acd477b2c4838919aacfd2514be7fc44cad48ad043"),
    ((14, 6, 1), 16, (10800, 21600, 43200), (176947200, 353894400),
     "f878f53bc0e465cb22f77af8cb6f6abf6919a42ce06b0c576986ba98c52420a0"),
    ((14, 6, 24), 384, (450, 900, 1350), (346521600, 353894400),
     "e03247e9cdf7709e60cdd39b70b465b7191d423287cc048b483234a993f02563"),
    ((14, 6, 720), 11520, (15, 30, 45), (353648640, 353894400),
     "b2b65a534c44460d142bde2497ae3dbcb809329c8c47ee7d8de7c8ef69bd66f1"),
    ((14, 24, 1), 16, (43200, 86400, 172800), (707788800, 1415577600),
     "e52729a10570c540452238114f236d2fe0566c01a581d8182a845450c5d2a3ae"),
    ((14, 24, 24), 384, (1800, 3600, 5400), (1386086400, 1415577600),
     "192cb554ff133c6cea7ecae942db1e016f2c16137921653aea8c978f7fa78a05"),
    ((14, 24, 720), 11520, (60, 120, 180), (1414594560, 1415577600),
     "5b9c3fa38fd331a7b9d295f8e1230f1f8f73ced0bf363f7ba861cf16de1f167e"),
    ((17, 1, 1), 19, (1800, 3600, 7200), (235929600, 471859200),
     "264290c005a15a42d6500a0f87f615fae75090147dfa0519552938bbdadb6dda"),
    ((17, 1, 24), 456, (75, 150, 225), (462028800, 471859200),
     "b59ac690867aff71c0bfe7ddbc354887b73dd1ad13a41d5945f5021444ab61d0"),
    ((17, 1, 720), 13680, (3, 5, 8), (471531520, 471859200),
     "f62acc52ac7d5f7ae8da76bca223cc9a7daf878d2c44a99357f1a8e3913b5248"),
    ((17, 6, 1), 19, (10800, 21600, 43200), (1415577600, 2831155200),
     "ff99b85e6035df014b34d154985fc4e136ec4c5669ab36e009ba583e8bac1e26"),
    ((17, 6, 24), 456, (450, 900, 1350), (2772172800, 2831155200),
     "806ea95e4147492427e756d1cb154f80ca646feb734cf5b27ce50ff5f1c8cf80"),
    ((17, 6, 720), 13680, (15, 30, 45), (2829189120, 2831155200),
     "772c3f9f2a2f08f3f649db31315acbfbd60a54b5e50387ae1c92a8d0e2cbd309"),
    # The most any option set makes: 19 x 720 on 16384x16384 at 1 h, the last 11,324,620,800 wrong pixels
    ((17, 24, 1), 19, (43200, 86400, 172800), (5662310400, 11324620800),
     "66ac0e64d163544710aa98cd6a6e3710a0166250043f7f1a819858f69ad99cc5"),
    ((17, 24, 24), 456, (1800, 3600, 5400), (11088691200, 11324620800),
     "678cb7a42656700289e05b704cdf08a0c5f99a714ecb263f58bc7c94ae5b8ebd"),
    ((17, 24, 720), 13680, (60, 120, 180), (11316756480, 11324620800),
     "e77f7f70c486d30a1fb5e959a7d6ad64e39228e73327ebcbde124557bc43a454"),
]
# plan_math.missed_in_logic() at missed_pixel_checks 24 with Happy Accident, at 0 speed copies and each one more up to
# two past the top tier: (layout changes, checks in logic). Without the item none is in logic.
UP_THE_LADDER = [48, 72, 96, 120, 144, 168, 192, 216, 240, 264, 288, 288, 288]
IN_LOGIC = [
    ({}, UP_THE_LADDER),
    (dict(auto_copy_logic_hours=0), [288] * 13),
    (dict(timesanity_hours=6), UP_THE_LADDER),
    (dict(auto_copy_logic_hours=1), UP_THE_LADDER),
    (dict(final_width=50, final_height=50, auto_copy_logic_hours=24), UP_THE_LADDER),
    (dict(COPIES[17], timesanity_hours=1),
     UP_THE_LADDER[:11] + [312, 336, 360, 384, 408, 432, 456, 456, 456]),
]
# 0.1% from the start at 5 px steps: 844 similarity checks and Matched Pixels for 1,367 required items. The family at
# 24 makes it 1,132 for 1,368 (D12's table).
TENTH_AT_5_PX = {"tenth_percent_checks": 0, "hundredth_percent_checks": 100, "canvas_width_increment": 5,
                 "canvas_height_increment": 5}
TENTH_FROM_THE_START = {"tenth_percent_checks": 0, "hundredth_percent_checks": 100}
TWENTIETH_AT_5_PX = {"twentieth_percent_checks": 0, "hundredth_percent_checks": 100, "canvas_width_increment": 5,
                     "canvas_height_increment": 5}
SPEED = "Progressive Auto Copy Speed"


def missed_of(multiworld: MultiWorld, player: int = 1) -> list[MissedPixelsLocation]:
    return [location for location in multiworld.get_locations(player) if isinstance(location, MissedPixelsLocation)]


class TestTheTargets(unittest.TestCase):
    def test_the_targets_match_the_plan(self) -> None:
        for (copies, hours, k), count, first, last, whole in TARGETS:
            with self.subTest(copies=copies, timesanity_hours=hours, missed_pixel_checks=k):
                setup = layout(**COPIES[copies], timesanity_hours=hours, missed_pixel_checks=k)
                targets = setup.missed_targets
                self.assertEqual((copies, count, first, last),
                                 (setup.speed_items, len(targets), targets[:3], targets[-2:]))
                self.assertEqual(whole, digest(targets))

    def test_every_ladder_has_its_shape(self) -> None:
        # plan_math's checks, on every count of speed copies and a grid of hours and k: (S + 2) x k checks rising
        # strictly, the first a wrong pixel or more, Happy Accident alone opening 2k up to X = 3,600 x timesanity_hours,
        # each copy s exactly k above 2^(s - 1) X up to 2^s X, and the last 2^S X, what the top tier makes in
        # timesanity_hours
        for copies, hours, k in itertools.product(range(10, 18), (1, 6, 7, 24), (1, 2, 3, 7, 24, 719, 720)):
            ladder, x = ladder_values(k, hours, copies), 3600 * hours
            runs = [ladder[2 * k + s * k:2 * k + (s + 1) * k] for s in range(copies)]
            if (len(ladder) != (copies + 2) * k or any(later <= earlier for earlier, later in zip(ladder, ladder[1:]))
                    or ladder[0] < 1 or ladder[2 * k - 1] != x or ladder[-1] != 2 ** copies * x
                    or any(run[0] <= 2 ** s * x or run[-1] != 2 ** (s + 1) * x for s, run in enumerate(runs))):
                self.fail(f"the ladder of {copies} speed copies at {hours} h and k {k}")

    def test_none_at_0_and_the_most_any_option_set_makes(self) -> None:
        self.assertEqual((), layout().missed_targets)
        self.assertEqual((), layout(**COPIES[17], timesanity_hours=1).missed_targets)
        # (S + 2) x 720 at the most: the 13,680 names on 16384x16384 at 1 h. The goal moves the ladder only through its
        # speed copies, so 50x50 and the 400x300 start make the defaults' ladder.
        self.assertEqual((13_680, 13_680), (len(layout(**COPIES[17], missed_pixel_checks=720).missed_targets),
                                            MISSED_NAMES))
        ladder = layout(**K24).missed_targets
        self.assertEqual((ladder, ladder), (layout(**K24, start_width=400, start_height=300).missed_targets,
                                            layout(**K24, final_width=50, final_height=50).missed_targets))

    def test_each_counts_as_a_location(self) -> None:
        # plan_math's location_count(): 8,043 similarity checks and Matched Pixels and 288 Missed Pixels at k 24, 8,640
        # at 720 and 12 at 1, and 8,545 with every family at the plan's defaults. None is excluded.
        for changes, count in ((K24, 8331), (dict(missed_pixel_checks=720), 16683), (dict(missed_pixel_checks=1), 8055),
                               (dict(K24, perfect_pixel_checks=5, timesanity_minutes=10), 8545),
                               (dict(K24, perfect_pixel_checks=5, perfect_pixel_items="filler"), 8401)):
            with self.subTest(changes=changes):
                setup = layout(**changes)
                excluded = 70 if setup.perfect_pixel_items == "filler" else 0
                self.assertEqual((count, excluded), (setup.location_count, setup.excluded_count))


class TestTheRule(unittest.TestCase):
    def test_checks_in_logic_match_the_plan(self) -> None:
        for changes, in_logic in IN_LOGIC:
            setup = layout(**changes, **K24)
            targets = setup.missed_targets
            for speed, count in enumerate(in_logic):
                with self.subTest(layout=changes, speed=speed):
                    self.assertEqual((count, 0), (bisect_right(targets, missed_reach(setup, speed, True)),
                                                  bisect_right(targets, missed_reach(setup, speed, False))))

    def test_copies_past_the_top_tier_read_as_the_top_tier(self) -> None:
        # Start inventory can hold more speed copies than the pool's: the figure reads them as the top tier, what its
        # switch makes in timesanity_hours, as D8's ceiling reads them (D26). That is the last target, so from the top
        # tier on every check is in logic.
        for changes, speed, reach in (({}, 10, 88_473_600), ({}, 11, 88_473_600), ({}, 17, 88_473_600),
                                      (dict(COPIES[17], timesanity_hours=1), 17, 471_859_200),
                                      (dict(COPIES[17], timesanity_hours=1), 18, 471_859_200)):
            with self.subTest(layout=changes, speed=speed):
                setup = layout(**changes, **K24)
                self.assertEqual((reach, reach), (missed_reach(setup, speed, True), setup.missed_targets[-1]))

    def test_happy_accident_then_each_speed_copy(self) -> None:
        # Through each check's own rule: with every progression item but Happy Accident none, with the item and every
        # progression item but the speed copies 48, then 24 more for each speed copy up to all 288 at the tenth, and
        # none more from a copy past the top tier, as start inventory can give. At 0 h the item alone opens all 288.
        for hours, in_logic in ((6, UP_THE_LADDER[:12]), (0, [288] * 12)):
            with self.subTest(auto_copy_logic_hours=hours):
                multiworld = build({**K24, "auto_copy_logic_hours": hours})
                world, checks, pool = multiworld.worlds[1], missed_of(multiworld), multiworld.itempool
                [happy] = [item for item in pool if item.name == "Happy Accident"]
                state = CollectionState(multiworld)
                for item in pool:
                    if item.advancement and item is not happy:
                        state.collect(item, prevent_sweep=True)
                self.assertEqual(0, sum(check.can_reach(state) for check in checks))
                state = CollectionState(multiworld)
                for item in pool:
                    if item.advancement and item.name != SPEED:
                        state.collect(item, prevent_sweep=True)
                reached = [sum(check.can_reach(state) for check in checks)]
                for item in [item for item in pool if item.name == SPEED] + [world.create_item(SPEED)]:
                    state.collect(item, prevent_sweep=True)
                    reached.append(sum(check.can_reach(state) for check in checks))
                self.assertEqual(in_logic, reached)

    def test_the_copies_the_family_adds_move_no_other_figure(self) -> None:
        # The speed copies past D8's progression ones can't raise the cap, so as progression they move neither logic's
        # ceiling nor the Perfect Pixels budget (plan_math's check, over a coarser grid)
        for (w, h), hours, half in itertools.product(((50, 50), (800, 600), (800, 800), (4000, 3000), (8192, 8192)),
                                                     (1, 2, 6, 24), (False, True)):
            setup = layout(final_width=w, final_height=h, auto_copy_logic_hours=hours,
                           **(dict(start_width=w // 2, start_height=h // 2) if half else {}))
            d8, top = setup.speed_progression, setup.speed_items
            self.assertEqual(top, replace(setup, **K24).speed_progression)
            width, height = setup.canvas_items
            for c, wide, high, accuracy in itertools.product((0, 100, 254), sorted({0, width // 2, width}),
                                                             sorted({0, height // 2, height}), (0, 4, 9)):
                ceiling = percent_available(setup, c, c, c, wide, high, d8, accuracy, True)
                budget = min(unlocked_area(setup, wide, high), copy_budget(setup, d8, accuracy))
                for speed in range(d8 + 1, top + 1):
                    if (percent_available(setup, c, c, c, wide, high, speed, accuracy, True) != ceiling or
                            min(unlocked_area(setup, wide, high), copy_budget(setup, speed, accuracy)) != budget):
                        self.fail(f"speed copy {speed} moves a figure at {setup}")


class TestTheSpeedCopies(unittest.TestCase):
    def test_every_copy_is_progression_while_the_family_is_on(self) -> None:
        # plan_math.speed_progression() by auto_copy_logic_hours 0 to 24: every copy with the family on, on 800x600 and
        # on 50x50, where D8 alone makes 3 at 1 h and none from 7 h; D8's own count with it off; 17 on 16384x16384 at
        # 1 h; and none at 0 h, where the copies stay useful
        small = dict(final_width=50, final_height=50)
        for changes, on, off in (({}, [0] + [10] * 24, SPEED_PROGRESSION),
                                 (small, [0] + [10] * 24, [0, 3, 2, 2, 1, 1, 1] + [0] * 18)):
            with self.subTest(layout=changes):
                self.assertEqual((on, off), ([layout(**changes, **K24, auto_copy_logic_hours=hours).speed_progression
                                              for hours in range(25)],
                                             [layout(**changes, auto_copy_logic_hours=hours).speed_progression
                                              for hours in range(25)]))
        self.assertEqual(17, layout(**COPIES[17], missed_pixel_checks=1).speed_progression)

    def test_the_pools_classes(self) -> None:
        # The speed copies' classes and Happy Accident in the pool, and every other non-filler item as the family off
        # has it
        def classes(options: dict) -> tuple[Counter, Counter]:
            pool = build(options).itempool
            ours = Counter((item.name, item.classification) for item in pool if item.name in (SPEED, "Happy Accident"))
            return ours, Counter((item.name, item.classification) for item in pool if item.name not in
                                 (SPEED, "Happy Accident") and item.classification != ItemClassification.filler)

        def speed(**copies: int) -> Counter:
            return Counter({(SPEED, ItemClassification[name]): count for name, count in copies.items()})

        happy = Counter({("Happy Accident", ItemClassification.progression): 1})
        # (options with the family off, the speed copies' classes then, and with the family at 24)
        for off, without, with_family in (({}, speed(progression=8, useful=2), speed(progression=10)),
                                          ({"auto_copy_logic_hours": 0}, speed(useful=10), speed(useful=10)),
                                          ({"auto_copy_logic_hours": 24}, speed(progression=6, useful=4),
                                           speed(progression=10)),
                                          (named(50, 50, auto_copy_logic_hours=24), speed(useful=10),
                                           speed(progression=10))):
            with self.subTest(options=off):
                ours_off, others_off = classes(off)
                ours_on, others_on = classes({**off, **K24})
                self.assertEqual((without, with_family + happy, others_off), (ours_off, ours_on, others_on))


class TestTheChecksInASeed(unittest.TestCase):
    def test_24_a_speed_copy(self) -> None:
        multiworld = build(K24)
        checks, world = missed_of(multiworld), multiworld.worlds[1]
        self.assertEqual({name: address for name, address in missed_table.items() if address <= 2_250_288},
                         {check.name: check.address for check in checks})
        self.assertEqual(("Missed Pixels #1", 2_250_001, 1_800, "Missed Pixels #288", 2_250_288, 88_473_600),
                         (checks[0].name, checks[0].address, checks[0].target, checks[-1].name, checks[-1].address,
                          checks[-1].target))
        self.assertEqual(list(world.layout.missed_targets), [check.target for check in checks])
        self.assertEqual({("Canvas", "Pain-T")}, {(check.parent_region.name, check.game) for check in checks})
        # 288 locations more, and as many items: Happy Accident and 287 fillers
        self.assertEqual((8331, 8331, 1104), (len(multiworld.get_locations(1)), len(multiworld.itempool),
                                              len(world.non_filler_items())))

    def test_location_exists_with_options_makes_the_seeds_checks(self) -> None:
        # One for each of the seed's targets, from the first id up: 17 speed copies on 16384x16384 at 1 h make a check
        # of every name at 720. Built beside a second slot, through generate_early.
        for options, count in (({}, 0), (K24, 288), ({"missed_pixel_checks": 1}, 12),
                               ({"missed_pixel_checks": 720}, 8640), ({**K24, "auto_copy_logic_hours": 0}, 288),
                               (named(16384, 16384, missed_pixel_checks=720, auto_copy_logic_hours=1), 13680)):
            with self.subTest(options=options):
                world = generate_early(options, slots=2)
                self.assertEqual(list(range(2_250_001, 2_250_001 + count)),
                                 [address for address in missed_table.values()
                                  if location_exists_with_options(world, address)])
        multiworld = build(K24)
        self.assertEqual(list(range(2_250_001, 2_250_289)), [check.address for check in missed_of(multiworld)])

    def test_what_a_check_can_hold(self) -> None:
        # With auto copy in logic a check takes every item. At 0 h, where Happy Accident alone opens every check, it
        # turns away any player's progression and takes useful items, filler and traps.
        progression = Item("Progression", ItemClassification.progression_skip_balancing, None, 2)
        for hours, takes in ((6, (True,) * 6), (0, (False, False, False, True, True, True))):
            multiworld = build({**K24, "auto_copy_logic_hours": hours, "trap_count": 50}, slots=2)
            first = {}
            for item in multiworld.itempool:
                first.setdefault((item.player, item.classification), item)
            items = [first[player, ItemClassification.progression] for player in (1, 2)] + [progression]
            items += [first[1, classification] for classification in (ItemClassification.useful,
                                                                      ItemClassification.filler,
                                                                      ItemClassification.trap)]
            state, checks = CollectionState(multiworld), missed_of(multiworld)
            with self.subTest(auto_copy_logic_hours=hours):
                self.assertEqual(288, len(checks))
                self.assertEqual({takes}, {tuple(check.can_fill(state, item, False) for item in items)
                                           for check in checks})

    def test_happy_accident_from_the_start(self) -> None:
        # start_inventory_from_pool takes Happy Accident out of the pool, and with it held from the start the 48 checks
        # it opens alone are in logic at once (D26)
        multiworld = as_main_builds({**K24, "start_inventory_from_pool": {"Happy Accident": 1}})
        self.assertEqual((["Happy Accident"], []),
                         ([item.name for item in multiworld.precollected_items[1] if item.name == "Happy Accident"],
                          [item.name for item in multiworld.itempool if item.name == "Happy Accident"]))
        self.assertEqual(48, sum(check.can_reach(CollectionState(multiworld)) for check in missed_of(multiworld)))


class TestSlotData(unittest.TestCase):
    def test_slot_data(self) -> None:
        # From version 1.2.0 (D26): missed_pixel_targets lists every check's wrong pixels in order, the j-th for id
        # 2,250,000 + j, [] with the family off, beside missed_pixel_checks as the YAML set it.
        k24 = list(layout(**K24).missed_targets)
        doubling = [10_800] + [21_600 * 2 ** s for s in range(11)]
        biggest = [1_800] + [3_600 * 2 ** s for s in range(18)]
        for options, targets, slots in (
                ({}, [], 1), (K24, k24, 1), (K24, k24, 2), ({**K24, "auto_copy_logic_hours": 0}, k24, 1),
                ({"missed_pixel_checks": 1, "timesanity_hours": 6}, doubling, 1), ({"timesanity_hours": 6}, [], 1),
                (named(16384, 16384, missed_pixel_checks=1, auto_copy_logic_hours=1, timesanity_hours=1), biggest,
                 2)):
            with self.subTest(options=options, slots=slots):
                world = generate_early(options, slots)
                slot_data = world.fill_slot_data()
                self.assertEqual((targets, options.get("missed_pixel_checks", 0)),
                                 (slot_data["missed_pixel_targets"], slot_data["missed_pixel_checks"]))
                self.assertEqual((list, int), (type(slot_data["missed_pixel_targets"]),
                                               type(slot_data["missed_pixel_checks"])))
                self.assertEqual([], [target for target in slot_data["missed_pixel_targets"]
                                      if type(target) is not int])
                self.assertEqual(slot_data, json.loads(json.dumps(slot_data)))
                self.assertEqual([MISSED_BASE + j for j in range(1, len(targets) + 1)],
                                 [address for address in missed_table.values()
                                  if location_exists_with_options(world, address)])
        # 32 keys on every seed, and the checks change no key but their own two
        defaults, with_checks = generate_early({}).fill_slot_data(), generate_early(K24).fill_slot_data()
        self.assertEqual((32, 32), (len(defaults), len(with_checks)))
        self.assertEqual({"missed_pixel_checks", "missed_pixel_targets"},
                         {key for key in defaults if defaults[key] != with_checks[key]})


class TestTheRefusals(unittest.TestCase):
    def test_the_item_count_counts_the_checks_and_happy_accident(self) -> None:
        # D12's table: 0.1% from the start at 5 px steps has 844 locations for 1,367 items, and with the family at 24
        # 1,132 for 1,368, solo or not. The message names no missed_pixel_checks.
        with self.assertRaises(OptionError) as raised:
            generate_early({**TENTH_AT_5_PX, **K24}, slots=2)
        self.assertEqual("Tester1's Pain-T world has 1132 locations for 1368 required items. Add checks "
                         "(hundredth_percent_checks 0 makes one every 0.01%), raise logic_percent, lower "
                         "color_depth_items, or use bigger canvas steps. With tool_size_ladders off, 23 of them stay "
                         "out. With overclock_bank_size_items and overclock_fill_speed_items at 0, 10 more stay out. "
                         "With miss_margin_step 255, 254 more stay out, and with nothing else changed the items fit "
                         "from miss_margin_step 14.", str(raised.exception))
        # At 100 px steps 844 locations can't hold 1,103 items, and the family's 288 checks hold the 1,104 with Happy
        # Accident.
        with self.assertRaisesRegex(OptionError, r"has 844 locations for 1103 required items\."):
            generate_early(TENTH_FROM_THE_START)
        world = generate_early({**TENTH_FROM_THE_START, **K24})
        self.assertEqual((1132, 1104, 1), (world.layout.location_count, len(world.non_filler_items()),
                                           world.non_filler_items().count("Happy Accident")))

    def test_a_refusals_sample_counts_the_checks(self) -> None:
        # As the item count does: from 5 px steps at 0.1% from the start, 100 px steps need 1,104 items with the
        # family, for 844 similarity checks and 288 Missed Pixels, and pass. Without the family 1,103 don't fit 844.
        setup = layout(spacing=(50, 70, 0, 100, 100), width_increment=5, height_increment=5, **K24)
        other = replace(setup, width_increment=100, height_increment=100)
        self.assertEqual((1132, 1132), (setup.location_count, other.location_count))
        self.assertEqual((True, False), (change_fills(setup, other, 1368),
                                         change_fills(replace(setup, missed_pixel_checks=0),
                                                      replace(other, missed_pixel_checks=0), 1367)))

    def test_the_model_places_every_speed_copy(self) -> None:
        # The fill check stays on the similarity checks and Matched Pixels until task 8.3. With the family on it places
        # every speed copy, progression now, and leaves out Happy Accident and the checks it opens. Its verdicts at the
        # defaults, at 5 px steps with 0.05% from the start, and at 0 h stay test_auto_copy_logic.py's.
        self.assertEqual((254, 254, 254, 8, 6, 10, 9, 1), progression_counts(layout(**K24)))
        self.assertEqual((254, 254, 254, 8, 6, 0, 0, 1), progression_counts(layout(**K24, auto_copy_logic_hours=0)))
        self.assertEqual((254, 254, 254, 8, 6, 6, 9, 1), progression_counts(
            layout(**K24, from_pool=(0, 0, 0, 0, 0, 4, 0, 0))))
        for changes, verdict in (({}, (3, 3)), (dict(spacing=(50, 70, 100, 0, 100), width_increment=5,
                                                     height_increment=5), (0, 3)),
                                 (dict(auto_copy_logic_hours=0), (3, 3))):
            for k in (24, 720):
                with self.subTest(changes=changes, missed_pixel_checks=k):
                    self.assertEqual(verdict, passes_filled(layout(**changes, missed_pixel_checks=k)))

    def test_a_refusal_names_the_checks_that_take_progression(self) -> None:
        # With auto copy in logic the checks take progression the model leaves out. At 0 h they take none, and with
        # the family off there are none. Three families are named with commas. Past the first message the sentence is
        # checked on the defaults' layout, which the model passes faster.
        setup = layout(spacing=(50, 70, 100, 0, 100), width_increment=5, height_increment=5, **K24)
        with mock.patch.object(rules, "passing_changes", return_value=([], 16)):
            on = refusal("P1", setup, 1368)
            at_0_h = refusal("P1", layout(**K24, auto_copy_logic_hours=0), 1104)
            off = refusal("P1", layout(), 1103)
            every = refusal("P1", layout(**K24, perfect_pixel_checks=5, perfect_pixel_items="any",
                                         timesanity_minutes=10), 1104)
        self.assertEqual("P1's Pain-T world can't be filled alone: a model of Archipelago's fill, run on its logic "
                         "with fixed seeds, has to place every progression item in 3 of 5 tries. It filled 0 of the "
                         "first 3, and with 2 tries left it can't reach 3. The model places progression on the "
                         "similarity checks and Matched Pixels alone and leaves out this seed's 288 Missed Pixels "
                         "checks. None of a sample of 16 single changes passes the check; try two at once, or play it "
                         "beside a Pain-T slot at the defaults. Beside other slots this check doesn't run, and "
                         "Archipelago's own fill decides.", on)
        self.assertEqual((False, False), ("The model places" in at_0_h, "The model places" in off))
        # The defaults' layout fills 3 of 3, and the count of tries says only that
        self.assertIn(" It filled 3 of the first 3. The model places progression on the similarity checks and Matched "
                      "Pixels alone and leaves out this seed's 144 Auto Copy Time checks, 70 Perfect Pixels checks and "
                      "288 Missed Pixels checks. None of", every)

    def test_no_refusal_names_missed_pixel_checks(self) -> None:
        # Until task 8.10's real seeds back the family's reach (D12, D26): the item count's message, solo or not, and
        # the fill check's with its whole sample, which names the 288 checks it leaves out
        messages = []
        for options, slots in (({**TENTH_AT_5_PX, **K24}, 1), ({**TENTH_AT_5_PX, "missed_pixel_checks": 1}, 2),
                               ({**TWENTIETH_AT_5_PX, **K24}, 1)):
            with self.assertRaises(OptionError) as raised:
                generate_early(options, slots)
            messages.append(str(raised.exception))
        self.assertIn("leaves out this seed's 288 Missed Pixels checks. From a sample of 14 single changes",
                      messages[-1])
        self.assertEqual([], [message for message in messages if "missed_pixel_checks" in message])


class TestAFill(unittest.TestCase):
    def test_what_lands_on_the_checks(self) -> None:
        # Archipelago's fill, seed 1: progression lands on the checks at 6 h as on any check, and at 0 h on none. Every
        # location is reached sphere by sphere.
        for hours in (6, 0):
            with self.subTest(auto_copy_logic_hours=hours):
                multiworld = setup_multiworld(PaintHardWorld, seed=1, options={**K24, "auto_copy_logic_hours": hours})
                distribute_items_restrictive(multiworld)
                call_all(multiworld, "post_fill")
                held = Counter(kind(check.item) for check in missed_of(multiworld))
                self.assertEqual(288, sum(held.values()))
                if hours:
                    self.assertGreater(held["progression"], 0)
                else:
                    self.assertEqual(0, held["progression"])
                self.assertTrue(reaches_every_location(multiworld))

    def test_another_slots_progression_lands_on_them(self) -> None:
        # Two slots with the family: each slot's checks hold the other slot's progression too, and every location of
        # both stays reachable.
        multiworld = setup_multiworld([PaintHardWorld] * 2, seed=1, options=[K24, K24])
        distribute_items_restrictive(multiworld)
        call_all(multiworld, "post_fill")
        for player, other in ((1, 2), (2, 1)):
            held = Counter(check.item.player for check in missed_of(multiworld, player) if check.item.advancement)
            self.assertGreater(held[other], 0)
        self.assertTrue(reaches_every_location(multiworld))


class TestMissedPixelsOn(PaintHardTestBase):
    # 24 a speed copy: the base class's tests reach every location with every item, something with none, and fill the
    # seed.
    options = K24


class TestMissedPixelsAtTheirTop(PaintHardTestBase):
    options = {"missed_pixel_checks": 720}


class TestMissedPixelsWithAutoCopyOutOfLogic(PaintHardTestBase):
    options = {**K24, "auto_copy_logic_hours": 0}


class TestMissedPixelsOnASmallGoal(PaintHardTestBase):
    # 50x50 at 24 h, where D8 alone makes no speed copy progression and the family makes all 10
    options = named(50, 50, auto_copy_logic_hours=24, **K24)


class TestEveryFamilyOn(PaintHardTestBase):
    options = {**K24, "perfect_pixel_checks": 5, "perfect_pixel_items": "any", "timesanity_minutes": 10}

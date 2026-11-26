import json
import pathlib
import unittest
from dataclasses import replace
from unittest import mock

from BaseClasses import CollectionState, MultiWorld
from Options import OptionError
from settings import get_settings
from test.general import setup_multiworld

from . import PaintHardTestBase
from .. import PaintHardWorld
from ..rules import CURVE, KINDS, TO_PASS, paint_percent_available, passes_filled, quantize, shade_counts, worst_error

VECTORS = pathlib.Path(__file__).with_name("shade_vectors.json")
# The smallest pool: the tool ladders and the Overclock bank off, and one Progressive Miss Margin copy
SMALLEST_POOL = {"tool_size_ladders": False, "overclock_bank_size_items": 0, "overclock_fill_speed_items": 0,
                 "miss_margin_step": 255}


def generate_early(options: dict) -> MultiWorld:
    """A solo seed with these options, through generate_early, where D12's refusals run."""
    return setup_multiworld(PaintHardWorld, ("generate_early",), options=options)


def build_vectors() -> dict:
    """What the client's src/shades.js has to agree with. The client keeps a copy at
    test/paint-hard/shade_vectors.json and checks it with test/paint-hard/shade-parity.mjs. After changing the
    rounding or the curve, rewrite this file from the Archipelago folder with
    python -c "from worlds.paint_hard.test.test_colors import write_vectors; write_vectors()"
    and copy it to the client."""
    rounding = {}
    for shades in range(2, 257):
        values = [quantize(value, shades) for value in range(256)]
        digest = 0
        for value in values:
            digest = (digest * 31 + value) & 0xFFFFFFFF
        rounding[str(shades)] = [sum(values), digest, worst_error(shades)]
    return {"curve": CURVE,
            "shade_counts": {str(items): list(shade_counts(items)) for items in range(7, 29)},
            "quantize": rounding}


def write_vectors() -> None:
    VECTORS.write_text(json.dumps(build_vectors(), indent=1) + "\n", encoding="utf-8")


class TestShadeTables(unittest.TestCase):
    def test_vectors_match_the_file(self) -> None:
        self.assertEqual(json.loads(VECTORS.read_text(encoding="utf-8")), build_vectors())

    def test_254_items_add_one_shade_each(self) -> None:
        self.assertEqual(tuple(range(2, 257)), shade_counts(254))

    def test_every_table_climbs_from_2_to_256(self) -> None:
        for items in range(7, 255):
            counts = shade_counts(items)
            with self.subTest(items=items):
                self.assertEqual((2, 256), (counts[0], counts[-1]))
                self.assertTrue(all(b > a for a, b in zip(counts, counts[1:])))
                self.assertTrue(all(worst_error(b) <= worst_error(a) for a, b in zip(counts, counts[1:])))


class TestOneShadePerItem(PaintHardTestBase):
    options = {"color_depth_items": 254, "starting_color_depth": 1}
    run_default_tests = False  # test_locations.py's TestTinyStartWithOneShade fills the same options

    def test_pool_start_and_slot_data(self) -> None:
        for color in ("Red", "Green", "Blue"):
            name = f"Progressive Color Depth ({color})"
            with self.subTest(color=color):
                self.assertEqual(253, len([item for item in self.multiworld.itempool if item.name == name]))
        self.assertEqual(list(range(2, 257)), self.world.fill_slot_data()["shade_counts"])


class TestBlackAndWhiteStart(PaintHardTestBase):
    options = {"starting_color_depth": 0}
    run_default_tests = False  # the defaults, which test_locations.py's TestTinyStart fills

    def test_no_free_color_items(self) -> None:
        names = [item.name for item in self.multiworld.precollected_items[self.player]]
        self.assertFalse([name for name in names if name.startswith("Progressive Color Depth")])
        self.assertEqual(254, len([item for item in self.multiworld.itempool
                                   if item.name == "Progressive Color Depth (Red)"]))


class TestTooFewLocationsRefused(PaintHardTestBase):
    auto_construct = False
    options = {"hundredth_percent_checks": 100}  # Paint's spacing: 174 locations for 1,103 non-filler items

    def test_generation_is_refused(self) -> None:
        # 929 too many: more than miss_margin_step 255 saves, so the message names no smallest step that fits.
        with self.assertRaisesRegex(OptionError, r"174 locations for 1103 required items\..* With miss_margin_step "
                                                 r"255, 254 more stay out\.$"):
            self.world_setup()


class TestTooFewLocationsRefusedOneMarginCopy(PaintHardTestBase):
    auto_construct = False
    # Every step from 128 to 254 makes 2 margin copies, so step 255 saves one.
    options = {"hundredth_percent_checks": 100, "miss_margin_step": 128}

    def test_generation_is_refused(self) -> None:
        with self.assertRaisesRegex(OptionError, r"With miss_margin_step 255, 1 more stays out\.$"):
            self.world_setup()


class TestNearFullSoloPoolRefused(PaintHardTestBase):
    auto_construct = False
    # Paint's spacing at logic 80: 174 locations. The item count refuses it before the fill check runs (D12): even at
    # miss_margin_step 255 the pool holds 231 non-filler items.
    options = {"hundredth_percent_checks": 100, "color_depth_items": 48, "miss_margin_step": 255}

    def test_generation_is_refused(self) -> None:
        with self.assertRaisesRegex(OptionError, "174 locations for 231 required items"):
            self.world_setup()


class TestSoloPoolWithEnoughRoom(PaintHardTestBase):
    run_default_tests = False  # here the fill check just has to let it by
    # 40 color items fill Paint's 174 locations with 174 items: 152 progression (120 color, 14 canvas, Pick Color, 8
    # speed and 9 accuracy copies) and 22 useful, which are the 13 other tools, 5 ladder copies (D23), 2 speed copies
    # and, at miss_margin_step 255, one margin copy and Auto Copy Loop. The fill check places every progression item
    # in 3 of 5 tries (D12), and real seeds filled 5 of 6. The tool ladders (D24) and the Overclock bank (D25) would
    # add 33 more items, so they stay off here.
    options = {"hundredth_percent_checks": 100, "color_depth_items": 40, **SMALLEST_POOL}

    def test_generation_is_allowed(self) -> None:
        self.assertEqual(174, len(self.multiworld.get_locations(self.player)))
        self.assertEqual((3, 5), passes_filled(self.world.layout))


class TestSoloSetupTheWalkRefused(PaintHardTestBase):
    run_default_tests = False
    # 20x5 px steps, a check every 0.05% from the start, 60 color items, logic 60 and the smallest pool: 357
    # progression items in 1,244 locations. Real seeds filled 6 of 6, and the fill check passes it. The walk the check
    # replaced refused it, 3 behind at 56 items.
    options = {"canvas_width_increment": 20, "canvas_height_increment": 5, "hundredth_percent_checks": 100,
               "twentieth_percent_checks": 0, "color_depth_items": 60, "logic_percent": 60, **SMALLEST_POOL}

    def test_generation_is_allowed(self) -> None:
        self.assertEqual((3, 3), passes_filled(self.world.layout))


class TestSoloFillCheckRefuses(PaintHardTestBase):
    auto_construct = False
    run_default_tests = False
    # 5 px steps, a check every 0.05% from the start and auto copy at 2 h: the pool's 1,367 items fit its 1,644
    # locations, but the fill check places every progression item in 0 of 3 tries, so only the check refuses it
    # (D12). Real seeds filled 0 of 3.
    options = {"canvas_width_increment": 5, "canvas_height_increment": 5, "hundredth_percent_checks": 100,
               "twentieth_percent_checks": 0, "auto_copy_logic_hours": 2}
    # The refusal at 2 h, for the player this test base names Tester: plan_math.py's tries and changes, in the
    # world's words
    message = ("Tester's Pain-T world can't be filled alone: a model of Archipelago's fill, run on its logic with "
               "fixed seeds, has to place every progression item in 3 of 5 tries. It filled 0 of the first 3, and "
               "with 2 tries left it can't reach 3. From a sample of 16 single changes, these pass the same check with "
               "nothing else changed: hundredth_percent_checks 0 (a check every 0.01% from the start); "
               "canvas_width_increment 50; canvas_height_increment 50; canvas_width_increment and "
               "canvas_height_increment 20; auto_copy_logic_hours 0. Beside other slots this check doesn't run, and "
               "Archipelago's own fill decides.")

    def test_the_check_refuses_and_names_what_passes(self) -> None:
        with self.assertRaises(OptionError) as refusal:
            self.world_setup()
        self.assertEqual(self.message, str(refusal.exception))

    def test_canvas_copies_from_the_start_pass(self) -> None:
        # 10 widths and 10 heights from the start, which the check counts from its first sweep. From the pool they
        # also leave it, and the check fills 3 of 4 tries; plain start_inventory leaves the pool as it is, and it fills
        # 3 of 3. Real seeds filled 12 of 13 from the pool and 8 of 12 plain.
        canvas = {"Progressive Canvas Width": 10, "Progressive Canvas Height": 10}
        copies, none = (0, 0, 0, 10, 10, 0, 0, 0), (0,) * len(KINDS)
        for option, taken, tries in (("start_inventory_from_pool", copies, (3, 4)), ("start_inventory", none, (3, 3))):
            with self.subTest(option=option):
                setup = generate_early({**self.options, option: canvas}).worlds[1].layout
                self.assertEqual((copies, taken, tries), (setup.precollected, setup.from_pool, passes_filled(setup)))
                self.assertEqual((0, 3), passes_filled(replace(setup, precollected=none, from_pool=none)))

    def test_changes_that_filled_real_seeds_pass(self) -> None:
        # hundredth_percent_checks 0 filled 3 of 3 real seeds, both steps at 10 filled 4 of 6 and auto copy at 0 h
        # filled 4 of 6. The walk's named change, 6 h, filled 0 of 5, and the check refuses it.
        for change, tries in (({"hundredth_percent_checks": 0}, (3, 3)),
                              ({"canvas_width_increment": 10, "canvas_height_increment": 10}, (3, 5)),
                              ({"auto_copy_logic_hours": 0}, (3, 4))):
            with self.subTest(change=change):
                self.assertEqual(tries, passes_filled(generate_early({**self.options, **change}).worlds[1].layout))

    def test_a_second_slot_skips_the_check(self) -> None:
        # The check runs on solo seeds only. Beside a slot at the defaults these options pass generate_early.
        multiworld = setup_multiworld([PaintHardWorld, PaintHardWorld], ("generate_early",),
                                      options=[self.options, {}])
        self.assertEqual((1644, 8043), (multiworld.worlds[1].layout.locations, multiworld.worlds[2].layout.locations))


class TestSoloFillCheckNamesWhatItTried(PaintHardTestBase):
    auto_construct = False
    run_default_tests = False
    # 800x600 from the 400x300 start, steps 5x25, Paint's spacing, 28 color items, logic 99 and the smallest pool. Real
    # seeds filled 0 of 6, and the check refuses it. It tries each change as the player would set it, so the both-axes
    # change it names, 20, is 20x20. The walk it replaced named both at 10 after trying 10x25, and then refused 10x10.
    options = {"starting_canvas": "half", "canvas_width_increment": 5, "canvas_height_increment": 25,
               "hundredth_percent_checks": 100, "color_depth_items": 28, "logic_percent": 99, **SMALLEST_POOL}
    # The refusal for these options, for the player this test base names Tester: plan_math.py's tries and changes, in
    # the world's words
    message = ("Tester's Pain-T world can't be filled alone: a model of Archipelago's fill, run on its logic with "
               "fixed seeds, has to place every progression item in 3 of 5 tries. It filled 0 of the first 3, and "
               "with 2 tries left it can't reach 3. From a sample of 10 single changes, these pass the same check with "
               "nothing else changed: half_percent_checks 0 (a check every 0.5% from the start); "
               "canvas_width_increment 10; canvas_width_increment and canvas_height_increment 20. Beside other slots "
               "this check doesn't run, and Archipelago's own fill decides.")

    def test_the_check_refuses_and_names_what_passes(self) -> None:
        with self.assertRaises(OptionError) as refusal:
            self.world_setup()
        self.assertEqual(self.message, str(refusal.exception))

    def test_each_named_change_passes_as_set(self) -> None:
        for change in ({"half_percent_checks": 0}, {"canvas_width_increment": 10},
                       {"canvas_width_increment": 20, "canvas_height_increment": 20}):
            with self.subTest(change=change):
                filled, _ = passes_filled(generate_early({**self.options, **change}).worlds[1].layout)
                self.assertGreaterEqual(filled, TO_PASS)


class TestSoloFillCheckNamesSeveralHours(PaintHardTestBase):
    auto_construct = False
    run_default_tests = False
    # 800x800 from the 5x5 start in 5x50 px steps, logic 53, 242 color items with 2 free, 16 h, a check every 0.05%
    # from the start and the smallest pool. The check refuses it, and two hours pass. At logic 53 upstream's rule
    # refuses every change that leaves both steps under 50, so the both-axes change named is 100, where the check
    # alone would pass 20.
    options = {"aspect_ratio": "square", "canvas_width_increment": 5, "canvas_height_increment": 50,
               "logic_percent": 53, "color_depth_items": 242, "starting_color_depth": 2, "auto_copy_logic_hours": 16,
               "half_percent_checks": 0, "quarter_percent_checks": 100, "tenth_percent_checks": 100,
               "twentieth_percent_checks": 0, "hundredth_percent_checks": 100, **SMALLEST_POOL}
    # The refusal for these options, for the player this test base names Tester: plan_math.py's tries and changes, in
    # the world's words
    message = ("Tester's Pain-T world can't be filled alone: a model of Archipelago's fill, run on its logic with "
               "fixed seeds, has to place every progression item in 3 of 5 tries. It filled 1 of the first 4, and "
               "with 1 try left it can't reach 3. From a sample of 12 single changes, these pass the same check with "
               "nothing else changed: hundredth_percent_checks 0 (a check every 0.01% from the start); "
               "canvas_width_increment 10; canvas_width_increment and canvas_height_increment 100; "
               "auto_copy_logic_hours 0 or 12. Beside other slots this check doesn't run, and Archipelago's own fill "
               "decides.")

    def test_the_check_refuses_and_names_what_passes(self) -> None:
        with self.assertRaises(OptionError) as refusal:
            self.world_setup()
        self.assertEqual(self.message, str(refusal.exception))


class TestTheHostsPanicMethod(unittest.TestCase):
    # The check models Archipelago's fill under the host's generator.panic_method (D12). TestSoloPoolWithEnoughRoom's
    # options fill 3 of 5 tries with swaps and 2 of 5 without; D12's 2 h example fills 0 of 3 either way.
    room = TestSoloPoolWithEnoughRoom.options
    raised = ("Tester1's Pain-T world can't be filled alone: a model of Archipelago's fill under the host's "
              "panic_method raise, run on its logic with fixed seeds, has to place every progression item in 3 of 5 "
              "tries. It filled 2 of the 5. From a sample of 5 single changes, these pass the same check with nothing "
              "else changed: half_percent_checks 0 (a check every 0.5% from the start); auto_copy_logic_hours 0 or 2 "
              "or 12 or 24. Beside other slots this check doesn't run, and Archipelago's own fill decides.")

    def test_these_tests_take_the_host_as_swap(self) -> None:
        # Every other test that goes through generate_early reads the host's method as Archipelago's default.
        self.assertEqual("swap", get_settings().generator.panic_method)

    def test_swap_runs_the_check_with_swaps(self) -> None:
        with mock.patch.object(get_settings().generator, "panic_method", "swap"):
            self.assertEqual((3, 5), passes_filled(generate_early(self.room).worlds[1].layout))

    def test_raise_runs_it_without(self) -> None:
        with mock.patch.object(get_settings().generator, "panic_method", "raise"):
            with self.assertRaises(OptionError) as refusal:
                generate_early(self.room)
        self.assertEqual(self.raised, str(refusal.exception))

    def test_start_inventory_skips_it(self) -> None:
        # Under start_inventory Archipelago moves what it can't place to the start, and no seed fails.
        with mock.patch.object(get_settings().generator, "panic_method", "start_inventory"):
            world = generate_early(TestSoloFillCheckRefuses.options).worlds[1]
        self.assertEqual(1644, world.layout.locations)

    def test_each_method_has_its_own_verdict(self) -> None:
        setup = generate_early(self.room).worlds[1].layout
        self.assertEqual(((3, 5), (2, 5)), (passes_filled(setup, "swap"), passes_filled(setup, "raise")))


class TestFourteenColorItems(PaintHardTestBase):
    options = {"color_depth_items": 14, "starting_color_depth": 1}

    def test_pool_start_and_slot_data(self) -> None:
        for color in ("Red", "Green", "Blue"):
            name = f"Progressive Color Depth ({color})"
            with self.subTest(color=color):
                self.assertEqual(13, len([item for item in self.multiworld.itempool if item.name == name]))
                self.assertEqual(1, len([item for item in self.multiworld.precollected_items[self.player]
                                         if item.name == name]))
        self.assertEqual(list(shade_counts(14)), self.world.fill_slot_data()["shade_counts"])

    def test_a_color_item_raises_the_ceiling(self) -> None:
        state = CollectionState(self.multiworld)
        before = paint_percent_available(state, self.world, self.player)
        state.collect(self.world.create_item("Progressive Color Depth (Red)"))
        self.assertGreater(paint_percent_available(state, self.world, self.player), before)


class TestMostColorItems(PaintHardTestBase):
    options = {"color_depth_items": 28, "starting_color_depth": 3}

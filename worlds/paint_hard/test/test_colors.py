import json
import pathlib
import unittest

from BaseClasses import CollectionState
from Options import OptionError

from . import PaintHardTestBase
from ..rules import CURVE, paint_percent_available, quantize, shade_counts, worst_error

VECTORS = pathlib.Path(__file__).with_name("shade_vectors.json")


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

    def test_pool_start_and_slot_data(self) -> None:
        for color in ("Red", "Green", "Blue"):
            name = f"Progressive Color Depth ({color})"
            with self.subTest(color=color):
                self.assertEqual(253, len([item for item in self.multiworld.itempool if item.name == name]))
        self.assertEqual(list(range(2, 257)), self.world.fill_slot_data()["shade_counts"])


class TestBlackAndWhiteStart(PaintHardTestBase):
    options = {"starting_color_depth": 0}

    def test_no_free_color_items(self) -> None:
        names = [item.name for item in self.multiworld.precollected_items[self.player]]
        self.assertFalse([name for name in names if name.startswith("Progressive Color Depth")])
        self.assertEqual(254, len([item for item in self.multiworld.itempool
                                   if item.name == "Progressive Color Depth (Red)"]))


class TestTooFewLocationsRefused(PaintHardTestBase):
    auto_construct = False
    options = {"hundredth_percent_checks": 100}  # Paint's spacing: 174 locations for 790 non-filler items

    def test_generation_is_refused(self) -> None:
        with self.assertRaises(OptionError):
            self.world_setup()


class TestNearFullSoloPoolRefused(PaintHardTestBase):
    auto_construct = False
    # Paint's spacing at logic 80: 174 locations for 159 progression items, 15 spare. Pools this full failed to fill.
    options = {"hundredth_percent_checks": 100, "color_depth_items": 48}

    def test_generation_is_refused(self) -> None:
        with self.assertRaises(OptionError):
            self.world_setup()


class TestSoloPoolWithEnoughRoom(PaintHardTestBase):
    run_default_tests = False  # the review filled this size on 20 of 20 seeds; here the guard just has to let it by
    options = {"hundredth_percent_checks": 100, "color_depth_items": 44}  # 147 progression items, 27 spare

    def test_generation_is_allowed(self) -> None:
        self.assertEqual(174, len(self.multiworld.get_locations(self.player)))


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

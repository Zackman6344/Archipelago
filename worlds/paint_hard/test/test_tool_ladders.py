from BaseClasses import ItemClassification
from Options import OptionError

from . import PaintHardTestBase
from .. import TOOL_LADDERS

# D24's table, typed out here: the client's rung lists (src/tool-sizes.js) are each one longer than these.
D24_COPIES = {"Progressive Brush Size": 2, "Progressive Brush Shape": 2, "Progressive Eraser Size": 4,
              "Progressive Airbrush Size": 3, "Progressive Line Width": 4, "Progressive Rectangle Fill": 2,
              "Progressive Polygon Fill": 2, "Progressive Ellipse Fill": 2, "Progressive Rounded Rectangle Fill": 2}


class TestToolLadders(PaintHardTestBase):
    def test_every_copy_is_in_the_pool_and_useful(self) -> None:
        self.assertEqual(D24_COPIES, TOOL_LADDERS)
        self.assertEqual(23, sum(TOOL_LADDERS.values()))
        for name, copies in TOOL_LADDERS.items():
            items = [item for item in self.multiworld.itempool if item.name == name]
            with self.subTest(name=name):
                self.assertEqual(copies, len(items))
                self.assertTrue(all(item.classification == ItemClassification.useful for item in items))

    def test_slot_data_says_the_seed_has_them(self) -> None:
        self.assertTrue(self.world.fill_slot_data()["tool_ladders"])


class TestToolLaddersOff(PaintHardTestBase):
    options = {"tool_size_ladders": False}

    def test_none_in_the_pool(self) -> None:
        self.assertFalse([item.name for item in self.multiworld.itempool if item.name in TOOL_LADDERS])
        self.assertFalse(self.world.fill_slot_data()["tool_ladders"])


class TestToolLaddersNeedRoom(PaintHardTestBase):
    auto_construct = False
    # Paint's spacing: 174 locations. 40 color items at miss_margin_step 255 leave 174 non-filler items, and the ladders
    # bring it to 197. The Overclock bank (D25) stays out and the margin has one copy, so the ladders alone overflow and
    # the refusal names only them.
    options = {"hundredth_percent_checks": 100, "color_depth_items": 40, "miss_margin_step": 255,
               "overclock_bank_size_items": 0, "overclock_fill_speed_items": 0}

    def test_refusal_names_the_option(self) -> None:
        with self.assertRaisesRegex(OptionError, r"174 locations for 197 required items\..* With tool_size_ladders "
                                                 r"off, 23 of them stay out\.$") as refusal:
            self.world_setup()
        self.assertNotIn("overclock_bank_size_items", str(refusal.exception))
        self.assertNotIn("miss_margin_step", str(refusal.exception))


class TestBothOptionalGroupsNeedRoom(PaintHardTestBase):
    auto_construct = False
    # The same 174 locations with the bank's defaults too: 207 items, and the refusal counts each group.
    options = {"hundredth_percent_checks": 100, "color_depth_items": 40, "miss_margin_step": 255}

    def test_refusal_names_both(self) -> None:
        with self.assertRaisesRegex(OptionError, r"174 locations for 207 required items\..* With tool_size_ladders "
                                                 r"off, 23 of them stay out\. With overclock_bank_size_items and "
                                                 r"overclock_fill_speed_items at 0, 10 more stay out\.$"):
            self.world_setup()

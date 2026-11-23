from BaseClasses import ItemClassification
from Options import OptionError

from . import PaintHardTestBase

LADDERS = ("Progressive Overclock Bank Size", "Progressive Overclock Fill Speed")


class TestOverclockBank(PaintHardTestBase):
    def test_five_useful_copies_of_each(self) -> None:
        for name in LADDERS:
            items = [item for item in self.multiworld.itempool if item.name == name]
            with self.subTest(name=name):
                self.assertEqual(5, len(items))
                self.assertTrue(all(item.classification == ItemClassification.useful for item in items))

    def test_slot_data_has_the_steps(self) -> None:
        slot_data = self.world.fill_slot_data()
        self.assertEqual((120, 2), (slot_data["overclock_bank_size_step"], slot_data["overclock_fill_speed_step"]))


class TestOverclockBankOptions(PaintHardTestBase):
    options = {"overclock_bank_size_items": 12, "overclock_bank_size_step": 600, "overclock_fill_speed_items": 0,
               "overclock_fill_speed_step": 30}

    def test_counts_and_steps_follow_the_options(self) -> None:
        counts = [len([item for item in self.multiworld.itempool if item.name == name]) for name in LADDERS]
        self.assertEqual([12, 0], counts)
        slot_data = self.world.fill_slot_data()
        self.assertEqual((600, 30), (slot_data["overclock_bank_size_step"], slot_data["overclock_fill_speed_step"]))


class TestOverclockBankNeedsRoom(PaintHardTestBase):
    auto_construct = False
    # Paint's spacing: 174 locations. 40 color items at miss_margin_step 255 leave 174 non-filler items with the tool
    # ladders off, and the bank's 10 at the defaults bring it to 184. The margin has one copy, so the bank alone
    # overflows and the refusal names only it.
    options = {"hundredth_percent_checks": 100, "color_depth_items": 40, "miss_margin_step": 255,
               "tool_size_ladders": False}

    def test_refusal_names_the_options(self) -> None:
        with self.assertRaisesRegex(OptionError, r"174 locations for 184 required items\..* With "
                                                 r"overclock_bank_size_items and overclock_fill_speed_items at 0, "
                                                 r"10 of them stay out\.$") as refusal:
            self.world_setup()
        self.assertNotIn("tool_size_ladders", str(refusal.exception))
        self.assertNotIn("miss_margin_step", str(refusal.exception))

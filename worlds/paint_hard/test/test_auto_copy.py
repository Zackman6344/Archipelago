import unittest

from BaseClasses import CollectionState, ItemClassification
from Options import OptionError

from . import PaintHardTestBase
from .. import LADDERS, SPEED_ITEMS, miss_margin_items
from ..options import MissMarginStep
from ..rules import paint_percent_available


class TestAutoCopySpeed(PaintHardTestBase):
    def test_speed_copies_in_the_pool(self) -> None:
        copies = [item for item in self.multiworld.itempool if item.name == "Progressive Auto Copy Speed"]
        self.assertEqual(SPEED_ITEMS, len(copies))
        # Useful until auto copy enters logic (D8): logic doesn't count auto copy yet.
        self.assertTrue(all(item.classification == ItemClassification.useful for item in copies))

    def test_slot_data_names_the_tier_count(self) -> None:
        self.assertEqual(SPEED_ITEMS, self.world.fill_slot_data()["auto_copy_speed_items"])

    def test_speed_copies_take_filler_slots(self) -> None:
        # The pool still fills every location: the speed copies replace filler, not locations.
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(self.multiworld.itempool))


class TestLadders(PaintHardTestBase):
    def test_two_copies_of_each(self) -> None:
        for name in LADDERS:
            with self.subTest(name=name):
                self.assertEqual(2, len([item for item in self.multiworld.itempool if item.name == name]))

    def test_only_the_first_pick_color_is_progression(self) -> None:
        copies = [item for item in self.multiworld.itempool if item.name == "Progressive Pick Color"]
        self.assertEqual([ItemClassification.progression, ItemClassification.useful],
                         [item.classification for item in copies])
        views = [item for item in self.multiworld.itempool
                 if item.name in ("Progressive Difference Mode", "Progressive Similarity Mode")]
        self.assertTrue(all(item.classification == ItemClassification.useful for item in views))

    def test_pick_color_still_lifts_the_hand_painted_cap(self) -> None:
        # Logic's 2-bit cap on hand-painted color lifts with the first copy, as Pick Color did (D8).
        color = self.world.options.color_depth_items.value
        base = CollectionState(self.multiworld)
        for name in ("Red", "Green", "Blue"):
            for _ in range(color):
                base.collect(self.world.create_item(f"Progressive Color Depth ({name})"), prevent_sweep=True)
        before = paint_percent_available(base, self.world, self.player)
        base.collect(self.world.create_item("Progressive Pick Color"), prevent_sweep=True)
        self.assertGreater(paint_percent_available(base, self.world, self.player), before)

    def test_slot_data_marks_a_ladder_seed(self) -> None:
        self.assertTrue(self.world.fill_slot_data()["ladders"])


class TestAutoCopyAccuracy(PaintHardTestBase):
    def test_nine_useful_copies(self) -> None:
        # The miss chance starts at 90% and each copy takes off 10 points (D5).
        copies = [item for item in self.multiworld.itempool if item.name == "Progressive Auto Copy Accuracy"]
        self.assertEqual(9, len(copies))
        # Useful until auto copy enters logic (D8), as the speed copies are.
        self.assertTrue(all(item.classification == ItemClassification.useful for item in copies))


class TestMissMargin(PaintHardTestBase):
    def test_255_useful_copies_at_the_default_step(self) -> None:
        copies = [item for item in self.multiworld.itempool if item.name == "Progressive Miss Margin"]
        self.assertEqual(255, len(copies))
        self.assertTrue(all(item.classification == ItemClassification.useful for item in copies))

    def test_slot_data_names_the_step(self) -> None:
        self.assertEqual(1, self.world.fill_slot_data()["miss_margin_step"])

    def test_pool_at_the_defaults(self) -> None:
        # D12's 1,103 non-filler items, in the 8,043 locations there are until Phase 8 adds the checks of D21.
        fillers = [item for item in self.multiworld.itempool if item.classification == ItemClassification.filler]
        self.assertEqual((1103, 6940, 8043), (len(self.multiworld.itempool) - len(fillers), len(fillers),
                                              len(self.multiworld.get_locations(self.player))))


class CountsMarginCopies:
    copies: int
    non_filler: int

    def test_copies_follow_the_step(self) -> None:
        copies = [item for item in self.multiworld.itempool if item.name == "Progressive Miss Margin"]
        self.assertEqual(self.copies, len(copies))
        self.assertEqual(self.options["miss_margin_step"], self.world.fill_slot_data()["miss_margin_step"])
        fillers = [item for item in self.multiworld.itempool if item.classification == ItemClassification.filler]
        self.assertEqual((self.non_filler, 8043 - self.non_filler),
                         (len(self.multiworld.itempool) - len(fillers), len(fillers)))


# 5 divides 255 into 51 copies. At 2 the last of 128 copies takes the margin from 1 to 0, and at 255 a single copy
# takes it from 255 to 0. Each pool holds the 838 non-filler items from before Phase 4, 9 accuracy copies, the margin's
# copies and Auto Copy Loop.
for step, copies in ((5, 51), (2, 128), (255, 1)):
    name = f"TestMissMarginStep{step}"
    globals()[name] = type(name, (CountsMarginCopies, PaintHardTestBase),
                           {"options": {"miss_margin_step": step}, "copies": copies, "non_filler": 838 + 9 + copies + 1,
                            "run_default_tests": False})


class TestMarginCopiesReachZero(unittest.TestCase):
    def test_every_copy_counts_and_the_last_reaches_zero(self) -> None:
        self.assertEqual((1, 255, 1), (MissMarginStep.range_start, MissMarginStep.range_end, MissMarginStep.default))
        for step in range(1, 256):
            copies = miss_margin_items(step)
            with self.subTest(step=step, copies=copies):
                self.assertTrue((copies - 1) * step < 255 <= copies * step)


class TestAutoCopyLoop(PaintHardTestBase):
    def test_one_useful_copy(self) -> None:
        loops = [item for item in self.multiworld.itempool if item.name == "Auto Copy Loop"]
        self.assertEqual([ItemClassification.useful], [item.classification for item in loops])


class TestMissMarginNeedsRoom(PaintHardTestBase):
    auto_construct = False
    # Paint's spacing: 174 locations. 40 color items with the tool ladders and the Overclock bank off leave 173 items
    # beside the margin, and step 1's 255 copies bring it to 428, so the margin alone overflows and the refusal names
    # only it. Only step 255's one copy fits.
    options = {"hundredth_percent_checks": 100, "color_depth_items": 40, "tool_size_ladders": False,
               "overclock_bank_size_items": 0, "overclock_fill_speed_items": 0}

    def test_refusal_names_the_option(self) -> None:
        with self.assertRaisesRegex(OptionError, r"174 locations for 428 required items\..* With miss_margin_step "
                                                 r"255, 254 of them stay out, and with nothing else changed the items "
                                                 r"fit from miss_margin_step 255\.$") as refusal:
            self.world_setup()
        self.assertNotIn("tool_size_ladders", str(refusal.exception))
        self.assertNotIn("overclock_bank_size_items", str(refusal.exception))


class TestMissMarginStepThatFits(PaintHardTestBase):
    auto_construct = False
    run_default_tests = False
    # 0.05% spacing at logic 50 held the 838 items from before Phase 4 in its 1,044 locations. At step 1 the pool is
    # 1,103 items, 59 too many, so 196 margin copies fit beside the rest: step 2's 128 do, and step 1's 255 don't.
    options = {"hundredth_percent_checks": 100, "twentieth_percent_checks": 0, "logic_percent": 50}

    def test_refusal_names_every_group_and_the_smallest_step(self) -> None:
        with self.assertRaisesRegex(OptionError, r"1044 locations for 1103 required items\..* With tool_size_ladders "
                                                 r"off, 23 of them stay out\. With overclock_bank_size_items and "
                                                 r"overclock_fill_speed_items at 0, 10 more stay out\. With "
                                                 r"miss_margin_step 255, 254 more stay out, and with nothing else "
                                                 r"changed the items fit from miss_margin_step 2\.$"):
            self.world_setup()

    def test_that_step_fits(self) -> None:
        self.options = {**self.options, "miss_margin_step": 2}
        self.world_setup()
        self.assertEqual(1044, len(self.multiworld.get_locations(self.player)))

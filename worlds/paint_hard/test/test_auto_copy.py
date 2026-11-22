from BaseClasses import CollectionState, ItemClassification

from . import PaintHardTestBase
from .. import LADDERS, SPEED_ITEMS
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

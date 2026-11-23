from BaseClasses import CollectionState

from . import PaintHardTestBase

# Location counts from hard-fork/plan_math.py, with the 19 checks at and below 0.01% included.
SPACINGS = {
    "Paint": {"hundredth_percent_checks": 100},  # Paint's own spacing: 1%, then 0.5% from 50, 0.25% from 70
    "Twentieth": {"hundredth_percent_checks": 100, "twentieth_percent_checks": 0},
    "Hundredth": {},  # the default: a check every 0.01%
}
EXPECTED = {
    (50, "Paint"): 69, (50, "Twentieth"): 1019, (50, "Hundredth"): 5018,
    (80, "Paint"): 149, (80, "Twentieth"): 1619, (80, "Hundredth"): 8018,
    (99, "Paint"): 225, (99, "Twentieth"): 1999, (99, "Hundredth"): 9918,
}


class CountsLocations:
    expected: int

    def test_location_count(self) -> None:
        self.assertEqual(self.expected, len(self.multiworld.get_locations(self.player)))


# 14 color items with 1 free and miss_margin_step 255 keep every layout's 93 items within its locations; the defaults
# need 1,103 non-filler items. The tool ladders (D24) and the Overclock bank (D25) stay out, since the tightest layout,
# logic 50 at Paint's spacing with 94 locations, can't hold their 33 items. The 5x5 start adds its 25 Matched Pixels
# checks to every count.
for (logic, spacing), count in EXPECTED.items():
    name = f"TestLogic{logic}{spacing}Spacing"
    globals()[name] = type(name, (CountsLocations, PaintHardTestBase),
                           {"options": {"logic_percent": logic, "color_depth_items": 14, "starting_color_depth": 1,
                                        "miss_margin_step": 255, "tool_size_ladders": False,
                                        "overclock_bank_size_items": 0, "overclock_fill_speed_items": 0,
                                        **SPACINGS[spacing]},
                            "expected": count + 25})


class TestTinyStart(PaintHardTestBase):
    options = {"starting_canvas": "tiny"}

    def test_start_reaches_only_the_matched_pixels(self) -> None:
        # At black and white a 5x5 canvas is worth 0.000016% in logic, under the first similarity check.
        reachable = self.multiworld.get_reachable_locations(CollectionState(self.multiworld), self.player)
        self.assertEqual(sorted(f"Matched Pixels: {n}" for n in range(1, 26)),
                         sorted(location.name for location in reachable))

    def test_slot_data_carries_the_start(self) -> None:
        slot_data = self.world.fill_slot_data()
        self.assertEqual((5, 5, 25),
                         (slot_data["start_width"], slot_data["start_height"], slot_data["matched_pixels"]))


class TestTinyStartWithOneShade(PaintHardTestBase):
    options = {"starting_canvas": "tiny", "starting_color_depth": 1}

    def test_start_adds_eleven_early_checks(self) -> None:
        # 1 free item per channel makes a 5x5 canvas worth 0.0021%: 0.0001% to 0.001%, and 0.002%.
        reachable = self.multiworld.get_reachable_locations(CollectionState(self.multiworld), self.player)
        self.assertEqual(25 + 11, len(reachable))


class TestHalfStart(PaintHardTestBase):
    options = {"starting_canvas": "half"}

    def test_no_matched_pixels(self) -> None:
        names = [location.name for location in self.multiworld.get_locations(self.player)]
        self.assertFalse([name for name in names if name.startswith("Matched Pixels")])
        self.assertEqual(0, self.world.fill_slot_data()["matched_pixels"])

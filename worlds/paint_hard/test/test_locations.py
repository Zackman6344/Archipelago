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


for (logic, spacing), count in EXPECTED.items():
    name = f"TestLogic{logic}{spacing}Spacing"
    globals()[name] = type(name, (CountsLocations, PaintHardTestBase),
                           {"options": {"logic_percent": logic, **SPACINGS[spacing]}, "expected": count})


class TestTinyStart(PaintHardTestBase):
    options = {"starting_canvas": "tiny"}

    def test_start_reaches_eleven_early_checks(self) -> None:
        # A 5x5 canvas at the free color depth is worth 0.0021% in logic: 0.0001% to 0.001%, and 0.002%.
        reachable = self.multiworld.get_reachable_locations(CollectionState(self.multiworld), self.player)
        self.assertEqual(11, len(reachable))

    def test_slot_data_carries_the_start(self) -> None:
        slot_data = self.world.fill_slot_data()
        self.assertEqual((5, 5), (slot_data["start_width"], slot_data["start_height"]))

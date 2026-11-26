"""Pain-T's data package: every item and location name with its id, and the name groups. Archipelago fixes them for
the game whatever a YAML says (D1), so a generated seed keeps this whole table for as long as it is played. The checks
of D21 and D26 are in it with the most names any option set makes of each family, in id blocks that stay apart, and
Happy Accident is in it as an item (D26). The blocks, the counts and the package's size are hard-fork/plan_math.py's.
"""
import hashlib
import itertools
import unittest

from BaseClasses import ItemClassification
from NetUtils import encode

from .. import STARTING_TOOLS, TOOL_LADDERS, PaintHardWorld
from ..items import item_data_table, item_groups, traps
from ..locations import (EARLY_BASE, LOCATION_BASE, MATCHED_BASE, MISSED_BASE, PERFECT_BASE, TIME_BASE,
                         location_groups, missed_table, perfect_table, time_table)
from ..options import AutoCopyLogicHours, GoalHeight, GoalWidth, MissedPixelChecks, TimesanityHours, TimesanityMinutes
from ..rules import MISSED_NAMES, MISSED_TOP, PERFECT_MOST, SPEED_MOST, TIME_MARKS
from .test_auto_copy_logic import layout

# Every item: its id and the class the table gives it. A seed makes some speed and accuracy copies progression (D8)
# and the second Progressive Pick Color useful (D23); the tests of those are in test_auto_copy.py.
ITEMS = {
    "Progressive Canvas Width": (2198501, "progression"),
    "Progressive Canvas Height": (2198502, "progression"),
    "Progressive Color Depth (Red)": (2198503, "progression"),
    "Progressive Color Depth (Green)": (2198504, "progression"),
    "Progressive Color Depth (Blue)": (2198505, "progression"),
    "Free-Form Select": (2198506, "useful"),
    "Select": (2198507, "useful"),
    "Eraser/Color Eraser": (2198508, "useful"),
    "Fill With Color": (2198509, "useful"),
    "Progressive Pick Color": (2198510, "progression"),
    "Magnifier": (2198511, "useful"),
    "Pencil": (2198512, "useful"),
    "Brush": (2198513, "useful"),
    "Airbrush": (2198514, "useful"),
    "Text": (2198515, "useful"),
    "Line": (2198516, "useful"),
    "Curve": (2198517, "useful"),
    "Rectangle": (2198518, "useful"),
    "Polygon": (2198519, "useful"),
    "Ellipse": (2198520, "useful"),
    "Rounded Rectangle": (2198521, "useful"),
    "Additional Palette Color": (2198523, "filler"),
    "Undo Trap": (2198524, "trap"),
    "Clear Image Trap": (2198525, "trap"),
    "Invert Colors Trap": (2198526, "trap"),
    "Flip Horizontal Trap": (2198527, "trap"),
    "Flip Vertical Trap": (2198528, "trap"),
    "Help Trap": (2198529, "trap"),
    "Zoom In Trap": (2198530, "trap"),
    "Zoom Out Trap": (2198531, "trap"),
    "Tool Swap Trap": (2198532, "trap"),
    "Overclock": (2198533, "filler"),
    "Progressive Auto Copy Speed": (2198534, "useful"),
    "Progressive Difference Mode": (2198535, "useful"),
    "Progressive Similarity Mode": (2198536, "useful"),
    "Progressive Brush Size": (2198537, "useful"),
    "Progressive Brush Shape": (2198538, "useful"),
    "Progressive Eraser Size": (2198539, "useful"),
    "Progressive Airbrush Size": (2198540, "useful"),
    "Progressive Line Width": (2198541, "useful"),
    "Progressive Rectangle Fill": (2198542, "useful"),
    "Progressive Polygon Fill": (2198543, "useful"),
    "Progressive Ellipse Fill": (2198544, "useful"),
    "Progressive Rounded Rectangle Fill": (2198545, "useful"),
    "Progressive Overclock Bank Size": (2198546, "useful"),
    "Progressive Overclock Fill Speed": (2198547, "useful"),
    "Progressive Auto Copy Accuracy": (2198548, "useful"),
    "Progressive Miss Margin": (2198549, "useful"),
    "Auto Copy Loop": (2198550, "useful"),
    "Happy Accident": (2198551, "progression"),
}
# The location id blocks, in id order: (name group, first id, last id, first name, last name). D26's table has them,
# and plan_math.py asserts them apart.
BLOCKS = (
    ("Similarity", 2_198_901, 2_198_918, "Similarity: 0.0001%", "Similarity: 0.009%"),
    ("Matched Pixels", 2_198_951, 2_198_975, "Matched Pixels: 1", "Matched Pixels: 25"),
    ("Similarity", 2_199_001, 2_208_900, "Similarity: 0.01%", "Similarity: 99.0%"),
    ("Auto Copy Time", 2_209_001, 2_210_440, "Auto Copy Time: 0:01", "Auto Copy Time: 24:00"),
    ("Perfect Pixels", 2_211_001, 2_243_758, "Perfect Pixels #1", "Perfect Pixels #32758"),
    ("Missed Pixels", 2_250_001, 2_263_680, "Missed Pixels #1", "Missed Pixels #13680"),
)
GAPS = (32, 25, 100, 560, 6_242)  # the ids free between each block and the next
# A few names from inside the blocks, spelled out
SAMPLES = {
    "Similarity: 0.0005%": 2_198_905, "Similarity: 0.001%": 2_198_910, "Similarity: 0.002%": 2_198_911,
    "Similarity: 0.07%": 2_199_007, "Similarity: 0.29%": 2_199_029, "Similarity: 1.0%": 2_199_100,
    "Similarity: 12.34%": 2_200_234, "Similarity: 80.0%": 2_207_000, "Matched Pixels: 13": 2_198_963,
    "Auto Copy Time: 0:10": 2_209_010, "Auto Copy Time: 0:59": 2_209_059, "Auto Copy Time: 1:00": 2_209_060,
    "Auto Copy Time: 9:59": 2_209_599, "Auto Copy Time: 10:00": 2_209_600, "Auto Copy Time: 23:50": 2_210_430,
    "Perfect Pixels #70": 2_211_070, "Perfect Pixels #1390": 2_212_390, "Missed Pixels #48": 2_250_048,
    "Missed Pixels #288": 2_250_288, "Missed Pixels #8640": 2_258_640,
}
# The SHA-256 of the location table as text: a line "id name" for each location, in id order, joined by line feeds
LOCATIONS_SHA256 = "cc28c7088591b1e6d086cc807eb64a206da6061cb4e44aa050a22167e0d71a34"
# The item name groups. Each item is in one but the two fillers.
ITEM_GROUPS = {
    "Canvas": {"Progressive Canvas Width", "Progressive Canvas Height"},
    "Color Depth": {"Progressive Color Depth (Red)", "Progressive Color Depth (Green)",
                    "Progressive Color Depth (Blue)"},
    "Tools": {"Magnifier", "Brush", "Pencil", "Eraser/Color Eraser", "Airbrush", "Line", "Rectangle", "Ellipse",
              "Rounded Rectangle", "Free-Form Select", "Select", "Fill With Color", "Progressive Pick Color", "Text",
              "Curve", "Polygon"},
    "Tool Size Ladders": {"Progressive Brush Size", "Progressive Brush Shape", "Progressive Eraser Size",
                          "Progressive Airbrush Size", "Progressive Line Width", "Progressive Rectangle Fill",
                          "Progressive Polygon Fill", "Progressive Ellipse Fill",
                          "Progressive Rounded Rectangle Fill"},
    "Views": {"Progressive Difference Mode", "Progressive Similarity Mode"},
    "Auto Copy": {"Progressive Auto Copy Speed", "Progressive Auto Copy Accuracy", "Progressive Miss Margin",
                  "Auto Copy Loop", "Happy Accident", "Progressive Overclock Bank Size",
                  "Progressive Overclock Fill Speed"},
    "Traps": {"Undo Trap", "Clear Image Trap", "Invert Colors Trap", "Flip Horizontal Trap", "Flip Vertical Trap",
              "Help Trap", "Zoom In Trap", "Zoom Out Trap", "Tool Swap Trap"},
}
# The package's checksum, which a seed carries and a client keeps its copy of the names under: Archipelago's SHA-1
# over the two tables in their order and every group sorted. Any name, id or group that changes moves it.
CHECKSUM = "8c12f4f01e13d9571ef967beec5d5bc5fb6550ab"


def planned_locations() -> dict[str, int]:
    """Every location name with its id as the plan gives them (D1, D15, D16, D21, D26), in id order, as
    plan_math.location_names() builds them."""
    names = {}
    for k, units in enumerate([*range(1, 11), *range(20, 100, 10)], start=1):  # in 0.0001% steps
        names[f"Similarity: {units / 10000}%"] = 2_198_900 + k
    for n in range(1, 26):
        names[f"Matched Pixels: {n}"] = 2_198_950 + n
    for i in range(1, 9901):
        names[f"Similarity: {i / 100}%"] = 2_199_000 + i
    for hours, minutes in itertools.product(range(25), range(60)):
        if 0 < hours * 60 + minutes <= 24 * 60:
            names[f"Auto Copy Time: {hours}:{minutes:02}"] = 2_209_000 + hours * 60 + minutes
    for k in range(1, 32_759):
        names[f"Perfect Pixels #{k}"] = 2_211_000 + k
    for j in range(1, 13_681):
        names[f"Missed Pixels #{j}"] = 2_250_000 + j
    return names


def differences(expected: dict, actual: dict) -> tuple[int, list]:
    """How many keys two tables disagree on, and the first 10 of them in order, each with its value in both tables or
    None where a table lacks it. unittest's own compare of two tables of 57,821 entries diffs them line by line before
    it fails, which ran past 10 minutes when 1,440 ids moved."""
    wrong = sorted(((key, expected.get(key), actual.get(key)) for key in expected.keys() | actual.keys()
                    if key not in expected or key not in actual or expected[key] != actual[key]), key=str)
    return len(wrong), wrong[:10]


class TestTheLocationTable(unittest.TestCase):
    def test_every_name_and_id(self) -> None:
        planned = planned_locations()
        self.assertEqual((57_821, 57_821), (len(planned), len(set(planned.values()))))
        self.assertEqual((0, []), differences(planned, PaintHardWorld.location_name_to_id))
        self.assertEqual((0, []), differences({address: name for name, address in planned.items()},
                                              PaintHardWorld.location_id_to_name))
        self.assertEqual(SAMPLES, {name: PaintHardWorld.location_name_to_id[name] for name in SAMPLES})
        lines = [f"{address} {name}" for address, name in sorted(PaintHardWorld.location_id_to_name.items())]
        self.assertEqual(LOCATIONS_SHA256, hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest())

    def test_each_block_runs_from_its_first_id_to_its_last(self) -> None:
        names = PaintHardWorld.location_id_to_name
        for _, first, last, first_name, last_name in BLOCKS:
            with self.subTest(block=first_name):
                self.assertEqual((first_name, last_name), (names.get(first), names.get(last)))
                self.assertEqual([], [address for address in range(first, last + 1) if address not in names])
        # No id lies outside the six blocks: they hold 18, 25, 9,900, 1,440, 32,758 and 13,680.
        self.assertEqual([18, 25, 9_900, 1_440, 32_758, 13_680], [last - first + 1 for _, first, last, _, _ in BLOCKS])
        in_blocks = [address for address in names
                     if any(first <= address <= last for _, first, last, _, _ in BLOCKS)]
        self.assertEqual((57_821, 57_821), (len(in_blocks), len(names)))

    def test_no_two_blocks_touch(self) -> None:
        spans = [(first, last) for _, first, last, _, _ in BLOCKS]
        self.assertEqual(GAPS, tuple(later[0] - earlier[1] - 1 for earlier, later in zip(spans, spans[1:])))
        # Each family counts from 1, so its base names no check: Missed Pixels start at 2,250,001.
        self.assertEqual((2_198_900, 2_198_950, 2_199_000, 2_209_000, 2_211_000, 2_250_000),
                         (EARLY_BASE, MATCHED_BASE, LOCATION_BASE, TIME_BASE, PERFECT_BASE, MISSED_BASE))
        for base in (EARLY_BASE, MATCHED_BASE, LOCATION_BASE, TIME_BASE, PERFECT_BASE, MISSED_BASE):
            self.assertNotIn(base, PaintHardWorld.location_id_to_name)
        # A page sends 2,199,000 + i for each 0.01% of similarity it reaches, up to 100%, and the server drops the ids
        # the game doesn't have. So the 100 ids past the grid's last, up to 2,209,000, stay free.
        self.assertEqual([], [address for address in range(2_208_901, 2_209_001)
                              if address in PaintHardWorld.location_id_to_name])
        # The items are a table of their own, 349 ids below the first location, and every id is exact as a
        # JavaScript number.
        self.assertEqual(349, spans[0][0] - max(PaintHardWorld.item_id_to_name) - 1)
        self.assertLess(max(PaintHardWorld.location_id_to_name), 2 ** 53)

    def test_each_family_has_the_most_names_any_options_make(self) -> None:
        self.assertEqual((1_440, 32_758, 13_680), (len(time_table), len(perfect_table), len(missed_table)))
        self.assertEqual((1_440, 32_758, 720, 17, 13_680),
                         (TIME_MARKS, PERFECT_MOST, MISSED_TOP, SPEED_MOST, MISSED_NAMES))
        # A mark for every minute up to the most hours timesanity_hours takes, and no spacing past that
        self.assertEqual((TIME_MARKS, TIME_MARKS), (TimesanityHours.range_end * 60, TimesanityMinutes.range_end))
        # A Perfect Pixels check for each line of pixels the largest goal grows by from the 5x5 start (D21)
        self.assertEqual(PERFECT_MOST, GoalWidth.range_end - 5 + GoalHeight.range_end - 5)
        # Missed Pixels: missed_pixel_checks for each speed copy and twice that for Happy Accident alone (D26). The
        # largest goal at 1 h has the most speed copies (D19).
        most_copies = max(layout(final_width=GoalWidth.range_end, final_height=GoalHeight.range_end,
                                 auto_copy_logic_hours=hours).speed_items
                          for hours in range(AutoCopyLogicHours.range_start, AutoCopyLogicHours.range_end + 1))
        self.assertEqual((SPEED_MOST, MISSED_TOP), (most_copies, MissedPixelChecks.range_end))
        self.assertEqual(MISSED_NAMES, (most_copies + 2) * MissedPixelChecks.range_end)


class TestTheItemTable(unittest.TestCase):
    def test_every_name_id_and_class(self) -> None:
        self.assertEqual(ITEMS, {name: (data.code, data.type.name) for name, data in item_data_table.items()})
        self.assertEqual({name: code for name, (code, _) in ITEMS.items()}, PaintHardWorld.item_name_to_id)
        self.assertEqual(50, len(PaintHardWorld.item_id_to_name))

    def test_the_ids_run_from_2198501_to_happy_accident(self) -> None:
        # 2,198,522 is Change Background Color, which items.py has commented out, as Paint's own has it.
        ids = sorted(PaintHardWorld.item_id_to_name)
        self.assertEqual((2_198_501, 2_198_551, [2_198_522]),
                         (ids[0], ids[-1], [code for code in range(ids[0], ids[-1] + 1) if code not in ids]))

    def test_happy_accident(self) -> None:
        # D26: item 2,198,551, progression wherever a seed has it
        data = item_data_table["Happy Accident"]
        self.assertEqual((2_198_551, ItemClassification.progression), (data.code, data.type))
        self.assertEqual("Happy Accident", PaintHardWorld.item_id_to_name[2_198_551])

    def test_no_item_is_named_as_a_location(self) -> None:
        self.assertEqual(set(), set(PaintHardWorld.item_name_to_id) & set(PaintHardWorld.location_name_to_id))


class TestTheNameGroups(unittest.TestCase):
    def test_a_location_group_for_each_family(self) -> None:
        # Archipelago adds Everywhere, every location.
        groups = PaintHardWorld.location_name_groups
        self.assertEqual({"Similarity", "Matched Pixels", "Auto Copy Time", "Perfect Pixels", "Missed Pixels",
                          "Everywhere"}, set(groups))
        names = PaintHardWorld.location_id_to_name
        for group in set(groups) - {"Everywhere"}:
            with self.subTest(group=group):
                self.assertEqual({names[address] for label, first, last, _, _ in BLOCKS if label == group
                                  for address in range(first, last + 1)}, groups[group])
        self.assertEqual({"Similarity": 9_918, "Matched Pixels": 25, "Auto Copy Time": 1_440, "Perfect Pixels": 32_758,
                          "Missed Pixels": 13_680, "Everywhere": 57_821},
                         {group: len(members) for group, members in groups.items()})
        self.assertEqual(location_groups.keys() | {"Everywhere"}, groups.keys())

    def test_the_item_groups(self) -> None:
        # Archipelago adds Everything, every item.
        groups = PaintHardWorld.item_name_groups
        self.assertEqual({**ITEM_GROUPS, "Everything": set(ITEMS)},
                         {name: set(group) for name, group in groups.items()})
        self.assertEqual(item_groups.keys() | {"Everything"}, groups.keys())

    def test_every_item_but_the_fillers_is_in_one_group(self) -> None:
        fillers = {name for name, (_, kind) in ITEMS.items() if kind == "filler"}
        self.assertEqual({"Additional Palette Color", "Overclock"}, fillers)
        grouped = [name for group in ITEM_GROUPS.values() for name in group]
        self.assertEqual((48, set(ITEMS) - fillers), (len(grouped), set(grouped)))

    def test_the_groups_follow_the_worlds_own_lists(self) -> None:
        self.assertEqual(set(TOOL_LADDERS), ITEM_GROUPS["Tool Size Ladders"])
        self.assertEqual(set(traps), ITEM_GROUPS["Traps"])
        self.assertEqual({name for name, (_, kind) in ITEMS.items() if kind == "trap"}, ITEM_GROUPS["Traps"])
        # The starting_tool choices are all tools, and so is Magnifier, which every seed starts with.
        self.assertLess(set(STARTING_TOOLS) | {"Magnifier"}, ITEM_GROUPS["Tools"])

    def test_no_group_is_named_as_an_item_or_a_location(self) -> None:
        names = set(PaintHardWorld.item_name_to_id) | set(PaintHardWorld.location_name_to_id)
        self.assertEqual(set(), names & (set(PaintHardWorld.item_name_groups) |
                                         set(PaintHardWorld.location_name_groups)))


class TestThePackage(unittest.TestCase):
    def test_what_a_client_downloads(self) -> None:
        # The server sends a game's two tables and its checksum, and keeps the groups to itself. With every name of
        # D21 and D26 that is 1,783,520 bytes, plan_math.package_figures()'s figure, against 287,890 before them.
        package = {"item_name_to_id": PaintHardWorld.item_name_to_id,
                   "location_name_to_id": PaintHardWorld.location_name_to_id, "checksum": "0" * 40}
        self.assertEqual(1_783_520, len(encode(package).encode("utf-8")))

    def test_the_checksum(self) -> None:
        package = PaintHardWorld.get_data_package_data()
        self.assertEqual(["checksum", "item_name_groups", "item_name_to_id", "location_name_groups",
                          "location_name_to_id"], sorted(package))
        self.assertEqual(CHECKSUM, package["checksum"])

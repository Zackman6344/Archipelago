from typing import NamedTuple, Dict, Optional

from BaseClasses import CollectionState, Item, Location, Region

from .rules import (EARLY_UNITS, MATCHED_PIXELS, MISSED_NAMES, PERFECT_MOST, TIME_MARKS, paint_percent_available,
                    paint_reach)

LOCATION_BASE = 2199000  # + i, for the check at i * 0.01% similarity, i = 1 to 9900
EARLY_BASE = 2198900  # + k, for the 18 checks below 0.01% (EARLY_UNITS)
MATCHED_BASE = 2198950  # + n, for "Matched Pixels: n", n = 1 to 25, which only the 5x5 start has
# A pixel is matched when each channel is at least as close to the goal as black or white would be. Every shade table
# has black and white, so that bar never rises and is always reachable, and these are in logic from the start: a 5x5
# canvas at black and white is worth too little for any similarity check.
TIME_BASE = 2209000  # + m, for "Auto Copy Time: h:mm", the mark at m minutes of auto copy, m = 1 to 1440 (D21)
PERFECT_BASE = 2211000  # + k, for "Perfect Pixels #k", k = 1 to 32758 (D21)
MISSED_BASE = 2250000  # + j, for "Missed Pixels #j", j = 1 to 13680 (D26)


class PaintLocation(Location):
    game = "Pain-T"

    required_percent: float

    def __init__(self, player: int, name: str = '', address: Optional[int] = None, parent: Optional[Region] = None):
        super().__init__(player, name, address, parent)
        assert self.address is not None
        self.required_percent = location_percent[self.address]

    def access_rule(self, state: CollectionState):
        return paint_percent_available(state, state.multiworld.worlds[self.player], self.player) >=\
               self.required_percent


class AutoCopyTimeLocation(Location):
    """"Auto Copy Time: h:mm" (D21), the mark at that much of auto copy's work in all: in logic once the unlocked
    canvas has 120 pixels for each of its minutes."""
    game = "Pain-T"

    minutes: int

    def __init__(self, player: int, name: str = '', address: Optional[int] = None, parent: Optional[Region] = None):
        super().__init__(player, name, address, parent)
        assert self.address is not None
        self.minutes = self.address - TIME_BASE

    def access_rule(self, state: CollectionState):
        return paint_reach(state, state.multiworld.worlds[self.player], self.player).minutes >= self.minutes


class PerfectPixelsLocation(Location):
    """"Perfect Pixels #k" (D21), which sends once at least its target's pixels of the canvas equal the goal exactly: in
    logic once the pixels logic expects exact (perfect_in_logic()) reach the target, so never before every color
    item is held."""
    game = "Pain-T"

    target: int  # exact pixels, the k-th of the seed's Layout.perfect_thresholds

    def __init__(self, player: int, name: str, address: int, parent: Region, target: int):
        super().__init__(player, name, address, parent)
        self.target = target

    def access_rule(self, state: CollectionState):
        return paint_reach(state, state.multiworld.worlds[self.player], self.player).perfect >= self.target


class MissedPixelsLocation(Location):
    """"Missed Pixels #j" (D26), which sends once the slot's count of wrong pixels reaches its target: in logic once
    Happy Accident is held and its switch makes the target in timesanity_hours at the speed copies held, read up to
    auto copy's top tier (missed_reach()), and with the item alone at auto_copy_logic_hours 0."""
    game = "Pain-T"

    target: int  # wrong pixels, the j-th of the seed's Layout.missed_targets

    def __init__(self, player: int, name: str, address: int, parent: Region, target: int):
        super().__init__(player, name, address, parent)
        self.target = target

    def access_rule(self, state: CollectionState):
        return paint_reach(state, state.multiworld.worlds[self.player], self.player).missed >= self.target


def no_progression(item: Item) -> bool:
    """The item rule of a check that turns progression away (D21, D26): it takes filler, traps and useful items."""
    return not item.advancement


class PaintLocationData(NamedTuple):
    region: str
    address: int
    percent: float


location_data_table: Dict[str, PaintLocationData] = {
    **{f"Similarity: {units / 10000}%": PaintLocationData("Canvas", EARLY_BASE + k, units / 10000)
       for k, units in enumerate(EARLY_UNITS, start=1)},
    **{f"Matched Pixels: {n}": PaintLocationData("Canvas", MATCHED_BASE + n, 0.0) for n in range(1, MATCHED_PIXELS + 1)},
    **{f"Similarity: {i / 100}%": PaintLocationData("Canvas", LOCATION_BASE + i, i / 100) for i in range(1, 9901)},
}

location_percent = {data.address: data.percent for data in location_data_table.values()}

# The checks of D21 and D26: every name of each family with its id, the most any option set makes (rules.py). The
# marks are named by their minutes, and the other two by their place in the seed's own list of targets.
time_table = {f"Auto Copy Time: {m // 60}:{m % 60:02d}": TIME_BASE + m for m in range(1, TIME_MARKS + 1)}
perfect_table = {f"Perfect Pixels #{k}": PERFECT_BASE + k for k in range(1, PERFECT_MOST + 1)}
missed_table = {f"Missed Pixels #{j}": MISSED_BASE + j for j in range(1, MISSED_NAMES + 1)}

# Every location name of the game with its id, whatever a seed's options make of them
location_table = {**{name: data.address for name, data in location_data_table.items()},
                  **time_table, **perfect_table, **missed_table}
# A name group for each family, which a YAML's exclude_locations, priority_locations and start_location_hints take
# in place of the names
location_groups = {
    "Similarity": {name for name in location_data_table if name.startswith("Similarity: ")},
    "Matched Pixels": {name for name in location_data_table if name.startswith("Matched Pixels: ")},
    "Auto Copy Time": set(time_table),
    "Perfect Pixels": set(perfect_table),
    "Missed Pixels": set(missed_table),
}

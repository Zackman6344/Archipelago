from typing import NamedTuple, Dict, Optional

from BaseClasses import CollectionState, Location, Region

from .rules import paint_percent_available

LOCATION_BASE = 2199000  # + i, for the check at i * 0.01% similarity, i = 1 to 9900
EARLY_BASE = 2198900  # + k, for the 18 checks below 0.01%
MATCHED_BASE = 2198950  # + n, for "Matched Pixels: n", n = 1 to 25, which only the 5x5 start has
MATCHED_PIXELS = 25
# A pixel is matched when each channel is at least as close to the goal as black or white would be. Every shade table
# has black and white, so that bar never rises and is always reachable, and these are in logic from the start: a 5x5
# canvas at black and white is worth too little for any similarity check.
# The checks below 0.01%, in 0.0001% steps: every 0.0001% up to 0.001%, then every 0.001%. The 0.01% check that
# ends the ladder is the grid's first, and it always exists.
EARLY_UNITS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90)


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

location_table = {name: data.address for name, data in location_data_table.items()}
location_percent = {data.address: data.percent for data in location_data_table.values()}

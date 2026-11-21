from typing import NamedTuple, Dict, Optional

from BaseClasses import CollectionState, Location, Region

from .rules import paint_percent_available

LOCATION_BASE = 2199000  # + i, where i is the similarity in 0.01% steps


class PaintLocation(Location):
    game = "Paint Hard Mode"

    required_percent: float

    def __init__(self, player: int, name: str = '', address: Optional[int] = None, parent: Optional[Region] = None):
        super().__init__(player, name, address, parent)
        assert self.address is not None
        self.required_percent = (self.address - LOCATION_BASE) / 100

    def access_rule(self, state: CollectionState):
        return paint_percent_available(state, state.multiworld.worlds[self.player], self.player) >=\
               self.required_percent


class PaintLocationData(NamedTuple):
    region: str
    address: int


location_data_table: Dict[str, PaintLocationData] = {
    # Upstream's quarter-percent grid until Phase 1 brings the 0.01% grid and the early checks.
    f"Similarity: {i / 100}%": PaintLocationData("Canvas", LOCATION_BASE + i) for i in range(25, 9501, 25)
}

location_table = {name: data.address for name, data in location_data_table.items()}

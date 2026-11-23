import json
import os
import pathlib

from . import PaintHardTestBase
from .. import ACCURACY_ITEMS, TOOL_LADDERS, miss_margin_items

CONTRACT = pathlib.Path(__file__).with_name("client_contract.json")


def build_contract(slot_data: dict) -> dict:
    """What the client takes from this world, beyond items.py: each tool ladder's copies, the Progressive Auto Copy
    Accuracy copies, the Progressive Miss Margin copies at the default miss_margin_step, and the slot data at the
    default options. The client's test/paint-hard/real-client.e2e.mjs reads this file from the checkout beside it, builds
    its slot data from it, and checks its rung lists against the copies, its miss model against the accuracy and margin
    copies, and its reading of the bank's steps. The version's value is left out, since every release changes it. After
    changing any of them, rewrite this file from the Archipelago folder with PAIN_T_WRITE_CONTRACT=1 and this module's
    test."""
    values = {key: sorted(value) if isinstance(value, (set, frozenset)) else value
              for key, value in slot_data.items() if key != "version"}
    return {"tool_ladders": TOOL_LADDERS, "accuracy_items": ACCURACY_ITEMS,
            "miss_margin_items": miss_margin_items(slot_data["miss_margin_step"]),
            "slot_data_keys": sorted(slot_data), "slot_data": values}


class TestClientContract(PaintHardTestBase):
    def test_contract_matches_the_file(self) -> None:
        contract = build_contract(self.world.fill_slot_data())
        if os.environ.get("PAIN_T_WRITE_CONTRACT"):
            CONTRACT.write_text(json.dumps(contract, indent=1) + "\n", encoding="utf-8")
        self.assertEqual(json.loads(CONTRACT.read_text(encoding="utf-8")), contract)

import json
import os
import pathlib
from functools import cache

from test.general import setup_multiworld

from . import PaintHardTestBase
from .. import ACCURACY_ITEMS, TOOL_LADDERS, PaintHardWorld, miss_margin_items
from ..locations import (EARLY_BASE, LOCATION_BASE, MATCHED_BASE, MISSED_BASE, PERFECT_BASE, TIME_BASE,
                         location_data_table, missed_table, perfect_table, time_table)
from ..rules import percent_available
from .test_auto_copy_logic import CEILINGS, HALF_START_CEILINGS, ONE_HOUR_CEILINGS, PAST_THE_TOP, STATES, layout

CONTRACT = pathlib.Path(__file__).with_name("client_contract.json")
# test_auto_copy_logic.py's ceilings at STATES by hours: auto copy out of logic at 0 h, and in logic at 1, 2, 6 and 24 h
HOURS_CEILINGS = dict(sorted({**CEILINGS, 1: ONE_HOUR_CEILINGS[:len(STATES)]}.items()))
# The families at the plan's defaults with Perfect Pixels at any: a mark every 10 minutes, where a mark's minutes and
# its place in the list differ, 5 Perfect Pixels checks a canvas step and 24 Missed Pixels checks a speed copy
EVERY_FAMILY = {"perfect_pixel_checks": 5, "perfect_pixel_items": "any", "timesanity_minutes": 10,
                "missed_pixel_checks": 24}
# The seeds beside the defaults whose slot data the client's tests play, each with its options and the changes to
# test_auto_copy_logic.py's layout() its figures are worked out on: one at each hours value HOURS_CEILINGS has, the
# 400x300 start, one color item of each channel from the start, one apart from the defaults in each other setting
# logic's ceiling reads: the two canvas steps, logic_percent beside goal_percent, and the goal's size, and one with
# every family on, whose three lists of targets the locations block gives ids.
SEEDS = {**{str(hours): ({"auto_copy_logic_hours": hours}, dict(auto_copy_logic_hours=hours))
            for hours in HOURS_CEILINGS},
         "half_start": ({"starting_canvas": "half"}, dict(start_width=400, start_height=300)),
         "starting_color_depth_1": ({"starting_color_depth": 1}, dict(starting_color_depth=1)),
         "width_20_height_5": ({"canvas_width_increment": 20, "canvas_height_increment": 5},
                               dict(width_increment=20, height_increment=5)),
         "logic_90_goal_70": ({"logic_percent": 90, "goal_percent": 70}, dict(logic_percent=90)),
         "widescreen_vertical": ({"aspect_ratio": "widescreen_vertical"}, dict(final_width=450, final_height=800)),
         "every_family": (EVERY_FAMILY, EVERY_FAMILY)}
# Two more states of the defaults, in STATES' order, whose ceilings the world works out here: one speed copy, and 3
# speed copies with 2 accuracy copies, which get 51,840 pixels right in 6 h where 5 speed copies would get 207,360.
MORE_STATES = [(254, 8, 6, 1, 0, True), (254, 8, 6, 3, 2, True)]
# States with each channel's own count and the width and height items apart, whose ceilings the world works out here
# on each of CHANNEL_SEEDS: (red, green and blue items, width and height items, speed and accuracy copies, Pick Color).
# The last holds every canvas item the 20 and 5 px steps make.
CHANNEL_STATES = [(16, 13, 11, 3, 4, 5, 2, True), (1, 2, 3, 0, 1, 0, 0, False), (60, 30, 90, 7, 2, 3, 1, False),
                  (5, 80, 160, 30, 60, 6, 4, True), (254, 100, 7, 40, 119, 10, 9, False)]
CHANNEL_SEEDS = ("6", "width_20_height_5", "logic_90_goal_70", "widescreen_vertical")


def plain(value):
    return sorted(value) if isinstance(value, (set, frozenset)) else value


@cache
def seed_worlds() -> dict:
    """Each of SEEDS' worlds by name, built through create_items, as a solo seed is."""
    return {name: setup_multiworld(PaintHardWorld, ("generate_early", "create_regions", "create_items"), seed=1,
                                   options=options).worlds[1]
            for name, (options, _) in SEEDS.items()}


def slot_data_changes(slot_data: dict, defaults: dict) -> dict:
    """The keys whose values a seed's slot data changes from the defaults', the version left out."""
    if set(slot_data) != set(defaults):
        raise ValueError(f"the slot data's keys differ from the defaults': {sorted(set(slot_data) ^ set(defaults))}")
    return {key: plain(value) for key, value in slot_data.items()
            if key != "version" and plain(value) != plain(defaults[key])}


def build_logic(world: PaintHardWorld) -> dict:
    """What the client's logic ceiling (D8) is checked against. test/paint-hard/logic.e2e.mjs plays each state of
    test_auto_copy_logic.py at each hours value HOURS_CEILINGS has and at the 400x300 start, PAST_THE_TOP at 1 h, and
    CHANNEL_STATES on each of CHANNEL_SEEDS. real-client.e2e.mjs plays a seed with starting_color_depth 1 through its
    real client, its start inventory sent at location -2 as a server sends it. Both build each seed's slot data from
    the defaults' and its changes here. The figures are test_auto_copy_logic.py's, and the world's own at MORE_STATES
    and CHANNEL_STATES; the speed and accuracy copies the defaults make progression set the stand-in server's flags."""
    defaults = world.fill_slot_data()
    worlds = seed_worlds()
    return {"states": [list(state) for state in STATES],
            "ceilings": {str(hours): ceilings for hours, ceilings in HOURS_CEILINGS.items()},
            "half_start_ceilings": HALF_START_CEILINGS,
            "past_the_top_states": [list(state) for state in PAST_THE_TOP],
            "past_the_top_ceilings": ONE_HOUR_CEILINGS[len(STATES):],
            "more_states": [list(state) for state in MORE_STATES],
            "more_ceilings": [percent_available(world.layout, c, c, c, w, h, speed, accuracy, pick)
                              for c, w, h, speed, accuracy, pick in MORE_STATES],
            "channel_states": [list(state) for state in CHANNEL_STATES],
            "channel_ceilings": {name: [percent_available(worlds[name].layout, *state) for state in CHANNEL_STATES]
                                 for name in CHANNEL_SEEDS},
            "speed_progression": world.layout.speed_progression,
            "accuracy_progression": world.layout.accuracy_progression,
            "slot_data_changes": {name: slot_data_changes(seed.fill_slot_data(), defaults)
                                  for name, seed in worlds.items()},
            "start_inventory": [item.name for item in
                                worlds["starting_color_depth_1"].multiworld.precollected_items[1]]}


def build_locations() -> dict:
    """Each location id block of locations.py, in id order: its base, first and last id and first name, and how a
    check's id follows from its name. For the three families, also the slot data list that names a seed's checks, the
    rule from a list entry to its check's id and what an entry counts. A mark's id is the base plus the entry, its
    minutes; a Perfect or Missed Pixels check's is the base plus the entry's place in the list, from 1."""
    def block(base: int, table: dict, rule: str, **family) -> dict:
        first = min(table, key=table.get)
        return {"base": base, "first_id": table[first], "last_id": max(table.values()), "first_name": first,
                "id": rule, **family}

    def similarity(low: int, high: int) -> dict:
        return {name: data.address for name, data in location_data_table.items() if low < data.address <= high}

    return {"similarity_early": block(EARLY_BASE, similarity(EARLY_BASE, MATCHED_BASE),
                                      "base + place among the 18 checks below 0.01%, from 1"),
            "matched_pixels": block(MATCHED_BASE, similarity(MATCHED_BASE, LOCATION_BASE), "base + pixels matched"),
            "similarity": block(LOCATION_BASE, similarity(LOCATION_BASE, TIME_BASE),
                                "base + similarity in hundredths of a percent"),
            "auto_copy_time": block(TIME_BASE, time_table, "base + target", targets="auto_copy_time_targets",
                                    unit="minutes"),
            "perfect_pixels": block(PERFECT_BASE, perfect_table, "base + place in the list, from 1",
                                    targets="perfect_pixel_targets", unit="exact pixels"),
            "missed_pixels": block(MISSED_BASE, missed_table, "base + place in the list, from 1",
                                   targets="missed_pixel_targets", unit="wrong pixels")}


def build_contract(slot_data: dict, logic: dict) -> dict:
    """What the client takes from this world, beyond items.py: each tool ladder's copies, the Progressive Auto Copy
    Accuracy copies, the Progressive Miss Margin copies at the default miss_margin_step, the slot data at the default
    options, what its logic ceiling is checked against (build_logic), and each location block's ids
    (build_locations). The client's test/paint-hard/real-client.e2e.mjs reads this file from the checkout beside it,
    builds its slot data from it, and checks its rung lists against the copies, its miss model against the accuracy
    and margin copies, its reading of the bank's steps, and its logic ceiling; logic.e2e.mjs reads the logic part. The
    version's value is left out, since every release changes it. After changing any of them, or
    test_auto_copy_logic.py's figures, rewrite this file from the Archipelago folder with PAIN_T_WRITE_CONTRACT=1 and
    this module's test."""
    values = {key: plain(value) for key, value in slot_data.items() if key != "version"}
    return {"tool_ladders": TOOL_LADDERS, "accuracy_items": ACCURACY_ITEMS,
            "miss_margin_items": miss_margin_items(slot_data["miss_margin_step"]),
            "slot_data_keys": sorted(slot_data), "slot_data": values, "logic": logic, "locations": build_locations()}


class TestClientContract(PaintHardTestBase):
    def test_contract_matches_the_file(self) -> None:
        contract = build_contract(self.world.fill_slot_data(), build_logic(self.world))
        if os.environ.get("PAIN_T_WRITE_CONTRACT"):
            CONTRACT.write_text(json.dumps(contract, indent=1) + "\n", encoding="utf-8")
        self.assertEqual(json.loads(CONTRACT.read_text(encoding="utf-8")), contract)

    def test_each_seed_has_its_figures_layout(self) -> None:
        self.assertEqual(layout(), self.world.layout)
        for name, world in seed_worlds().items():
            with self.subTest(seed=name):
                self.assertEqual(layout(**SEEDS[name][1]), world.layout)

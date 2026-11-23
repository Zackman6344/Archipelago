from typing import Dict, Any
from math import ceil

from BaseClasses import CollectionState, Item, ItemClassification, MultiWorld, Tutorial, Region
from Options import OptionError
from worlds.AutoWorld import LogicMixin, World, WebWorld
from .items import item_table, PaintItem, item_data_table, traps
from .locations import location_table, PaintLocation, location_data_table, LOCATION_BASE, MATCHED_BASE, MATCHED_PIXELS
from .options import PaintOptions
from .rules import shade_counts, no_pick_color_cap

PALETTE_COLORS = 26  # Additional Palette Colors that bring the black-and-white palette to classic Paint's 28 swatches
# Solo seeds need this many locations beyond their progression items. In the Phase 2 review, Paint's spacing with
# 46-48 color items (15-21 spare) failed to fill, and 44-45 (24-27 spare) filled on 20 of 20 seeds. The solo walk
# planned as task 5.3 replaces this count.
SOLO_SPARE_LOCATIONS = 25
# Progressive Auto Copy Speed copies: 1 pixel a second doubled 10 times, 1,024 at the top (D5). Goals past
# 22.1 megapixels get more once goal sizes come from the YAML (D19).
SPEED_ITEMS = 10
# Progressive Auto Copy Accuracy copies: the miss chance starts at 90%, and each copy takes off 10 points (D5).
ACCURACY_ITEMS = 9
# The miss margin a seed starts at. Each Progressive Miss Margin lowers it by miss_margin_step, and the last copy
# brings it to 0 (D7).
MISS_MARGIN = 255
# Two-copy ladders (D23): the first copy unlocks the tool or view, the second gives auto copy a mode.
LADDERS = ["Progressive Pick Color", "Progressive Difference Mode", "Progressive Similarity Mode"]
# Tool ladders (D24) and their copies. Every painting tool starts one pixel wide, and each copy unlocks the next part
# of its option box in the client, smallest first. All useful: logic doesn't time hand painting.
TOOL_LADDERS = {"Progressive Brush Size": 2, "Progressive Brush Shape": 2, "Progressive Eraser Size": 4,
                "Progressive Airbrush Size": 3, "Progressive Line Width": 4, "Progressive Rectangle Fill": 2,
                "Progressive Polygon Fill": 2, "Progressive Ellipse Fill": 2, "Progressive Rounded Rectangle Fill": 2}
FEWER_ITEMS_HINT = ("Add checks (hundredth_percent_checks 0 makes one every 0.01%), raise logic_percent, lower "
                    "color_depth_items, or use bigger canvas steps.")


def miss_margin_items(step: int) -> int:
    """Progressive Miss Margin copies at this miss_margin_step: the fewest that bring the margin from 255 to 0."""
    return ceil(MISS_MARGIN / step)


class PaintHardWebWorld(WebWorld):
    theme = "partyTime"

    setup_en = Tutorial(
        tutorial_name="Start Guide",
        description="A guide to playing Pain-T in Archipelago.",
        language="English",
        file_name="guide_en.md",
        link="guide/en",
        authors=["MarioManTAW"]
    )

    tutorials = [setup_en]


class PaintHardWorld(World):
    """
    A harder fork of Paint, the classic Microsoft app reimagined as an Archipelago game. Find your tools, expand
    your canvas, and paint the greatest image the world has ever seen, the hard way.
    """
    game = "Pain-T"
    options_dataclass = PaintOptions
    options: PaintOptions
    web = PaintHardWebWorld()
    location_name_to_id = location_table
    item_name_to_id = item_table
    origin_region_name = "Canvas"

    final_width: int
    final_height: int
    start_width: int
    start_height: int
    tiny_start: bool
    per_pixel_logic_percent: float
    shade_counts: tuple[int, ...]
    no_pick_color_cap: int
    palette_colors: int = 0
    allowed_traps: list[str] = []

    def generate_early(self) -> None:
        if self.options.canvas_width_increment < 50 and self.options.canvas_height_increment < 50 and \
            self.options.logic_percent <= 55 and self.multiworld.players == 1:
            raise OptionError("Logic Percent must be greater than 55 when generating a single-player world with "
                                "Canvas Size Increment below 50.")
        if self.options.aspect_ratio <= 2:
            self.final_width = 800
        elif self.options.aspect_ratio == 4:
            self.final_width = 450
        else:
            self.final_width = 600
        if self.options.aspect_ratio >= 2:
            self.final_height = 800
        elif self.options.aspect_ratio == 1:
            self.final_height = 450
        else:
            self.final_height = 600
        self.tiny_start = self.options.starting_canvas == self.options.starting_canvas.option_tiny
        if self.tiny_start:
            self.start_width = self.start_height = 5
        else:
            self.start_width, self.start_height = self.final_width // 2, self.final_height // 2
        self.per_pixel_logic_percent = self.options.logic_percent.value / (self.final_width * self.final_height)
        self.shade_counts = shade_counts(self.options.color_depth_items.value)
        self.no_pick_color_cap = no_pick_color_cap(self.shade_counts)
        self.palette_colors = 0

    def get_filler_item_name(self) -> str:
        if self.random.randint(0, 99) < self.options.trap_count and self.allowed_traps:
            return self.random.choice(self.allowed_traps)
        if self.palette_colors < PALETTE_COLORS:
            self.palette_colors += 1
            return "Additional Palette Color"
        return "Overclock"

    def create_item(self, name: str) -> PaintItem:
        item = PaintItem(name, item_data_table[name].type, item_data_table[name].code, self.player)
        return item

    def create_items(self) -> None:
        starting_tools = ["Brush", "Pencil", "Eraser/Color Eraser", "Airbrush", "Line", "Rectangle", "Ellipse",
                          "Rounded Rectangle"]
        self.push_precollected(self.create_item("Magnifier"))
        self.push_precollected(self.create_item(starting_tools.pop(self.options.starting_tool)))
        items_to_create = ["Free-Form Select", "Select", "Fill With Color", "Text", "Curve", "Polygon"]
        items_to_create += LADDERS * 2  # D23: two copies of each
        items_to_create += starting_tools
        items_to_create += ["Progressive Canvas Width"] * ceil((self.final_width - self.start_width) /
                                                               self.options.canvas_width_increment)
        items_to_create += ["Progressive Canvas Height"] * ceil((self.final_height - self.start_height) /
                                                                self.options.canvas_height_increment)
        depth_items = ["Progressive Color Depth (Red)", "Progressive Color Depth (Green)",
                       "Progressive Color Depth (Blue)"]
        for item in depth_items:
            for _ in range(self.options.starting_color_depth.value):
                self.push_precollected(self.create_item(item))
        items_to_create += depth_items * (self.options.color_depth_items.value - self.options.starting_color_depth.value)
        items_to_create += ["Progressive Auto Copy Speed"] * SPEED_ITEMS
        # Misses, margin and passes (D7), all useful.
        margin_items = miss_margin_items(self.options.miss_margin_step.value)
        items_to_create += ["Progressive Auto Copy Accuracy"] * ACCURACY_ITEMS
        items_to_create += ["Progressive Miss Margin"] * margin_items
        items_to_create += ["Auto Copy Loop"]
        if self.options.tool_size_ladders:
            items_to_create += [name for name, copies in TOOL_LADDERS.items() for _ in range(copies)]
        # The Overclock bank (D25): how many copies of each ladder the options ask for. Both are useful.
        items_to_create += ["Progressive Overclock Bank Size"] * self.options.overclock_bank_size_items.value
        items_to_create += ["Progressive Overclock Fill Speed"] * self.options.overclock_fill_speed_items.value
        pre_filled = len(items_to_create)
        to_fill = len(self.get_region("Canvas").locations)
        if pre_filled > to_fill:
            # A sentence for each optional group: the settings that leave it out, the items they save, what follows
            groups = []
            if self.options.tool_size_ladders:
                groups.append(("tool_size_ladders off", sum(TOOL_LADDERS.values()), ""))
            bank = self.options.overclock_bank_size_items.value + self.options.overclock_fill_speed_items.value
            if bank:
                groups.append(("overclock_bank_size_items and overclock_fill_speed_items at 0", bank, ""))
            top_step = self.options.miss_margin_step.range_end
            saved = margin_items - miss_margin_items(top_step)
            if saved:
                room = margin_items - (pre_filled - to_fill)  # the margin copies that fit with nothing else changed
                smallest = (f", and with nothing else changed the items fit from miss_margin_step "
                            f"{ceil(MISS_MARGIN / room)}" if room > 0 else "")
                groups.append((f"miss_margin_step {top_step}", saved, smallest))
            hint = "".join(f" With {settings}, {count} {'more' if n else 'of them'} "
                           f"{'stays' if count == 1 else 'stay'} out{end}."
                           for n, (settings, count, end) in enumerate(groups))
            raise OptionError(f"{self.player_name}'s Pain-T world has {to_fill} locations for {pre_filled} "
                              f"required items. {FEWER_ITEMS_HINT}{hint}")
        progression = sum(1 for name in items_to_create
                          if item_data_table[name].type & ItemClassification.progression)
        progression -= 1  # the second Progressive Pick Color is useful, below
        # While the pool holds more useful items beyond its progression than this guard's spare (293 at the default
        # miss_margin_step, 316 with the tool ladders and 326 with the Overclock bank too; 39, 62 and 72 at step 255),
        # the item-count check above refuses those seeds first (D12). Once task 5.2 makes speed and accuracy copies
        # progression, the guard can bind again only with the tool ladders and the bank off and 3 margin copies or fewer
        # (steps of 85 or more), until the solo walk (task 5.3) replaces it.
        if self.multiworld.players == 1 and to_fill - progression < SOLO_SPARE_LOCATIONS:
            raise OptionError(f"{self.player_name}'s Pain-T world leaves {to_fill - progression} locations beyond its "
                              f"{progression} progression items, and a solo seed needs {SOLO_SPARE_LOCATIONS} to fill. "
                              f"{FEWER_ITEMS_HINT}")
        if self.options.death_link:
            self.options.trap_blacklist.value.update(["Undo Trap", "Clear Image Trap"])
        self.allowed_traps = [trap for trap in traps if trap not in self.options.trap_blacklist]
        while len(items_to_create) < to_fill:
            items_to_create += [self.get_filler_item_name()]
        pool = [self.create_item(item) for item in items_to_create]
        # The second Progressive Pick Color only gives auto copy a mode, which logic doesn't count (D23).
        [*_, second_pick_color] = [item for item in pool if item.name == "Progressive Pick Color"]
        second_pick_color.classification = ItemClassification.useful
        self.multiworld.itempool += pool

    def create_regions(self) -> None:
        canvas = Region("Canvas", self.player, self.multiworld)
        canvas.locations += [PaintLocation(self.player, loc_name, loc_data.address, canvas)
                             for loc_name, loc_data in location_data_table.items()
                             if location_exists_with_options(self, loc_data.address)]

        self.multiworld.regions += [canvas]

    def set_rules(self) -> None:
        from .rules import set_completion_rules
        set_completion_rules(self, self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        # miss_margin_step also marks a seed with D7's misses: the client plays one that has a version but no
        # miss_margin_step as a seed from before Phase 4.
        return dict(self.options.as_dict("logic_percent", "goal_percent", "death_link", "canvas_width_increment",
                                         "canvas_height_increment", "trap_blacklist", "trap_link", "miss_margin_step",
                                         "overclock_seconds", "overclock_bank_size_step", "overclock_fill_speed_step"),
                    final_width=self.final_width, final_height=self.final_height,
                    start_width=self.start_width, start_height=self.start_height,
                    matched_pixels=MATCHED_PIXELS if self.tiny_start else 0,
                    shade_counts=list(self.shade_counts),
                    auto_copy_speed_items=SPEED_ITEMS,
                    ladders=True,  # D23: Difference and Similarity Mode wait for their first copy
                    tool_ladders=bool(self.options.tool_size_ladders.value),  # D24: tools start one pixel wide
                    version=self.world_version.as_simple_string())

    def collect(self, state: CollectionState, item: Item) -> bool:
        change = super().collect(state, item)
        if change:
            state.paint_hard_percent_stale[self.player] = True
        return change

    def remove(self, state: CollectionState, item: Item) -> bool:
        change = super().remove(state, item)
        if change:
            state.paint_hard_percent_stale[self.player] = True
        return change


def location_exists_with_options(world: PaintHardWorld, location: int) -> bool:
    if MATCHED_BASE < location <= MATCHED_BASE + MATCHED_PIXELS:
        return world.tiny_start  # one per pixel of the 5x5 start
    if location < LOCATION_BASE:
        return True  # the 18 checks below 0.01% exist with every option
    i = location - LOCATION_BASE  # the similarity in 0.01% steps
    if i > world.options.logic_percent.value * 100:
        return False
    step = 100
    for tier_step, tier in ((50, world.options.half_percent_checks), (25, world.options.quarter_percent_checks),
                            (10, world.options.tenth_percent_checks), (5, world.options.twentieth_percent_checks),
                            (1, world.options.hundredth_percent_checks)):
        if i > tier.value * 100:
            step = min(step, tier_step)
    return i == 1 or i % step == 0  # 0.01% ends the early checks, so it exists whatever the spacing


# Every world's LogicMixin writes onto the one shared CollectionState, so these names must differ from core
# Paint's paint_percent_available and paint_percent_stale, or the two games overwrite each other's numbers.
class PaintHardState(LogicMixin):
    paint_hard_percent_available: dict[int, float]  # per player
    paint_hard_percent_stale: dict[int, bool]

    def init_mixin(self, multiworld: MultiWorld) -> None:
        self.paint_hard_percent_available = {player: 0 for player in multiworld.get_game_players("Pain-T")}
        self.paint_hard_percent_stale = {player: True for player in multiworld.get_game_players("Pain-T")}

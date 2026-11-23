from typing import Dict, Any
from math import ceil

from BaseClasses import CollectionState, Item, ItemClassification, MultiWorld, Tutorial, Region
from Options import OptionError
from settings import get_settings
from worlds.AutoWorld import LogicMixin, World, WebWorld
from .items import item_table, PaintItem, item_data_table, traps
from .locations import location_table, PaintLocation, location_data_table, LOCATION_BASE, MATCHED_BASE, MATCHED_PIXELS
from .options import PaintOptions
from .rules import SWAPS, Layout, fills, grid_exists, refusal, start_counts

PALETTE_COLORS = 26  # Additional Palette Colors that bring the black-and-white palette to classic Paint's 28 swatches
# Progressive Auto Copy Accuracy copies: the miss chance starts at 90%, and each copy takes off 10 points (D5).
ACCURACY_ITEMS = 9
# The miss margin a seed starts at. Each Progressive Miss Margin lowers it by miss_margin_step, and the last copy
# brings it to 0 (D7).
MISS_MARGIN = 255
# Two-copy ladders (D23): the first copy unlocks the tool or view, the second gives auto copy a mode.
LADDERS = ["Progressive Pick Color", "Progressive Difference Mode", "Progressive Similarity Mode"]
# The starting_tool choices, in its order. The one you start with is precollected, and the others go in the pool.
STARTING_TOOLS = ["Brush", "Pencil", "Eraser/Color Eraser", "Airbrush", "Line", "Rectangle", "Ellipse",
                  "Rounded Rectangle"]
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
    layout: Layout  # what logic's ceiling and the solo fill check read from the options (D8, D12)
    palette_colors: int = 0
    allowed_traps: list[str] = []

    def generate_early(self) -> None:
        if self.options.canvas_width_increment < 50 and self.options.canvas_height_increment < 50 and \
            self.options.logic_percent <= 55 and self.multiworld.players == 1:
            raise OptionError(f"{self.player_name}'s Pain-T world needs logic_percent above 55 when it plays alone "
                              f"with canvas_width_increment and canvas_height_increment both below 50.")
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
        options = self.options
        # Main.py precollects every copy both start inventory options name, once generate_early is done
        from_pool = start_counts(options.start_inventory_from_pool.value)
        precollected = tuple(a + b for a, b in zip(start_counts(options.start_inventory.value), from_pool))
        self.layout = Layout(self.final_width, self.final_height, self.start_width, self.start_height,
                             options.canvas_width_increment.value, options.canvas_height_increment.value,
                             options.logic_percent.value,
                             (options.half_percent_checks.value, options.quarter_percent_checks.value,
                              options.tenth_percent_checks.value, options.twentieth_percent_checks.value,
                              options.hundredth_percent_checks.value),
                             options.color_depth_items.value, options.starting_color_depth.value,
                             options.auto_copy_logic_hours.value, precollected, from_pool)
        self.palette_colors = 0
        self.refuse_unfillable()

    def refuse_unfillable(self) -> None:
        """D12's refusals, before anything is built: a pool bigger than its locations, then, for a solo seed, a fill
        check that runs a model of Archipelago's progression fill on the world's logic with fixed seeds. The check
        reads the host's panic_method, as Main.py does for the fill: under swap and raise it models the fill each
        runs, and under start_inventory, where the fill moves what it can't place to the start and no seed fails, it
        doesn't run."""
        items = self.non_filler_items()
        needed, to_fill = len(items), self.layout.locations
        if needed > to_fill:
            # A sentence for each optional group: the settings that leave it out, the items they save, what follows
            groups = []
            if self.options.tool_size_ladders:
                groups.append(("tool_size_ladders off", sum(TOOL_LADDERS.values()), ""))
            bank = self.options.overclock_bank_size_items.value + self.options.overclock_fill_speed_items.value
            if bank:
                groups.append(("overclock_bank_size_items and overclock_fill_speed_items at 0", bank, ""))
            margin_items = miss_margin_items(self.options.miss_margin_step.value)
            top_step = self.options.miss_margin_step.range_end
            saved = margin_items - miss_margin_items(top_step)
            if saved:
                room = margin_items - (needed - to_fill)  # the margin copies that fit with nothing else changed
                smallest = (f", and with nothing else changed the items fit from miss_margin_step "
                            f"{ceil(MISS_MARGIN / room)}" if room > 0 else "")
                groups.append((f"miss_margin_step {top_step}", saved, smallest))
            hint = "".join(f" With {settings}, {count} {'more' if n else 'of them'} "
                           f"{'stays' if count == 1 else 'stay'} out{end}."
                           for n, (settings, count, end) in enumerate(groups))
            raise OptionError(f"{self.player_name}'s Pain-T world has {to_fill} locations for {needed} "
                              f"required items. {FEWER_ITEMS_HINT}{hint}")
        if self.multiworld.players == 1:
            panic_method = str(get_settings().generator.panic_method)
            if panic_method in SWAPS and not fills(self.layout, panic_method):
                raise OptionError(refusal(self.player_name, self.layout, needed, panic_method))

    def non_filler_items(self) -> list[str]:
        """Every item the pool holds beyond its fillers, by name, as create_items() makes them."""
        tools = ["Free-Form Select", "Select", "Fill With Color", "Text", "Curve", "Polygon"]
        items = tools + LADDERS * 2  # D23: two copies of each
        items += [tool for n, tool in enumerate(STARTING_TOOLS) if n != self.options.starting_tool.value]
        width_items, height_items = self.layout.canvas_items
        items += ["Progressive Canvas Width"] * width_items + ["Progressive Canvas Height"] * height_items
        colors = self.options.color_depth_items.value - self.options.starting_color_depth.value
        items += [f"Progressive Color Depth ({channel})" for channel in ("Red", "Green", "Blue")] * colors
        items += ["Progressive Auto Copy Speed"] * self.layout.speed_items
        # Misses, margin and passes (D7)
        items += ["Progressive Auto Copy Accuracy"] * ACCURACY_ITEMS
        items += ["Progressive Miss Margin"] * miss_margin_items(self.options.miss_margin_step.value)
        items += ["Auto Copy Loop"]
        if self.options.tool_size_ladders:
            items += [name for name, copies in TOOL_LADDERS.items() for _ in range(copies)]
        # The Overclock bank (D25): how many copies of each ladder the options ask for. Both are useful.
        items += ["Progressive Overclock Bank Size"] * self.options.overclock_bank_size_items.value
        items += ["Progressive Overclock Fill Speed"] * self.options.overclock_fill_speed_items.value
        return items

    def get_filler_item_name(self) -> str:
        if self.random.randint(0, 99) < self.options.trap_count and self.allowed_traps:
            return self.random.choice(self.allowed_traps)
        if self.palette_colors < PALETTE_COLORS:
            self.palette_colors += 1
            return "Additional Palette Color"
        return "Overclock"

    def create_item(self, name: str) -> PaintItem:
        classification = item_data_table[name].type
        # Speed and accuracy copies are progression while one can still raise logic's cap (D8). create_items() makes
        # the pool's copies past that useful. A start inventory copy stays progression even past auto copy's top tier:
        # Main.py makes it here before the pool exists and collects it as it's made, so no later count can change its
        # class, and the ceiling reads speed copies past the top tier as the top tier. An item link group's world never
        # runs generate_early, so it has no layout and gets the table's class.
        layout = getattr(self, "layout", None)
        if layout and ((name == "Progressive Auto Copy Speed" and layout.speed_progression) or
                       (name == "Progressive Auto Copy Accuracy" and layout.accuracy_progression)):
            classification = ItemClassification.progression
        return PaintItem(name, classification, item_data_table[name].code, self.player)

    def create_items(self) -> None:
        self.push_precollected(self.create_item("Magnifier"))
        self.push_precollected(self.create_item(STARTING_TOOLS[self.options.starting_tool.value]))
        for channel in ("Red", "Green", "Blue"):
            for _ in range(self.options.starting_color_depth.value):
                self.push_precollected(self.create_item(f"Progressive Color Depth ({channel})"))
        items_to_create = self.non_filler_items()  # generate_early() refused any pool bigger than its locations
        if self.options.death_link:
            self.options.trap_blacklist.value.update(["Undo Trap", "Clear Image Trap"])
        self.allowed_traps = [trap for trap in traps if trap not in self.options.trap_blacklist]
        to_fill = len(self.get_region("Canvas").locations)
        while len(items_to_create) < to_fill:
            items_to_create += [self.get_filler_item_name()]
        pool = [self.create_item(item) for item in items_to_create]
        # The second Progressive Pick Color only gives auto copy a mode, which logic doesn't count (D23).
        [*_, second_pick_color] = [item for item in pool if item.name == "Progressive Pick Color"]
        second_pick_color.classification = ItemClassification.useful
        # Speed and accuracy copies past those that can still raise logic's cap are useful (D8): at 6 h on 800x600,
        # speed copies 9 and 10.
        for name, progression in (("Progressive Auto Copy Speed", self.layout.speed_progression),
                                  ("Progressive Auto Copy Accuracy", self.layout.accuracy_progression)):
            for item in [item for item in pool if item.name == name][progression:]:
                item.classification = ItemClassification.useful
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
        # auto_copy_logic_hours lets the client show logic's ceiling as the world works it out (D8).
        return dict(self.options.as_dict("logic_percent", "goal_percent", "death_link", "canvas_width_increment",
                                         "canvas_height_increment", "trap_blacklist", "trap_link", "miss_margin_step",
                                         "overclock_seconds", "overclock_bank_size_step", "overclock_fill_speed_step",
                                         "auto_copy_logic_hours"),
                    final_width=self.final_width, final_height=self.final_height,
                    start_width=self.start_width, start_height=self.start_height,
                    matched_pixels=MATCHED_PIXELS if self.tiny_start else 0,
                    shade_counts=list(self.layout.shade_counts),
                    auto_copy_speed_items=self.layout.speed_items,
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
    return grid_exists(location - LOCATION_BASE, world.layout.logic_percent, world.layout.spacing)


# Every world's LogicMixin writes onto the one shared CollectionState, so these names must differ from core
# Paint's paint_percent_available and paint_percent_stale, or the two games overwrite each other's numbers.
class PaintHardState(LogicMixin):
    paint_hard_percent_available: dict[int, float]  # per player
    paint_hard_percent_stale: dict[int, bool]

    def init_mixin(self, multiworld: MultiWorld) -> None:
        self.paint_hard_percent_available = {player: 0 for player in multiworld.get_game_players("Pain-T")}
        self.paint_hard_percent_stale = {player: True for player in multiworld.get_game_players("Pain-T")}

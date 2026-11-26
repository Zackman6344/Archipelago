import logging
from typing import Dict, Any
from dataclasses import replace
from math import ceil
from string import hexdigits
from urllib.parse import unquote, urlsplit

from BaseClasses import CollectionState, Item, ItemClassification, LocationProgressType, MultiWorld, Tutorial, Region
from Options import OptionError
from settings import get_settings
from Utils import Version
from worlds.AutoWorld import LogicMixin, World, WebWorld
from .items import item_table, PaintItem, item_data_table, traps, item_groups
from .locations import (location_table, PaintLocation, location_data_table, LOCATION_BASE, MATCHED_BASE,
                        MATCHED_PIXELS, location_groups, AutoCopyTimeLocation, TIME_BASE, no_progression, time_table,
                        PerfectPixelsLocation, PERFECT_BASE, perfect_table, MissedPixelsLocation, MISSED_BASE,
                        missed_table)
from .options import ColorDepthItems, LogicPercent, PaintOptions
from .rules import (INCREMENTS, SWAPS, MISSED_NAMES, PERFECT_MOST, TIME_MARKS, Layout, Reach, fills, grid_exists,
                    happy_count, progression_counts, refusal, start_counts)

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
GOAL_IMAGE_MOST = 2048  # the most characters a goal_image takes (D17)
GOAL_IMAGE_HINT = (f"It takes default, an https URL with a host and no user name, or the path of an image file in the "
                   f"client's own site, such as images/archipelago/800x600.png: no leading slash, no .. part, and a "
                   f"file name with an extension. Either has no whitespace or backslash and at most "
                   f"{GOAL_IMAGE_MOST:,} characters. http and data: URLs are refused.")
# The most pixels starting_canvas half takes, which logic expects painted by hand: the largest bundled half start,
# the 400x400 of 800x800 (D8).
HALF_START_MOST = 160_000


def miss_margin_items(step: int) -> int:
    """Progressive Miss Margin copies at this miss_margin_step: the fewest that bring the margin from 255 to 0."""
    return ceil(MISS_MARGIN / step)


def fewer_items_hint(layout: Layout, count: str) -> str:
    """The changes a refusal names for its count, "items" for the item count or "progression" for task 8.3's, each
    where the seed's options leave room for it: a check every 0.01% from the start while hundredth_percent_checks is
    above 0, a higher logic_percent below its top, fewer color items above the least color_depth_items, and a bigger
    canvas step below the biggest. While the Perfect Pixels checks hold items, at perfect_pixel_items useful or any,
    the item count names bigger steps up to the biggest step at or below perfect_pixel_checks, and only where that
    step is above the smaller of the seed's two steps. Each step of a side brings one canvas item and
    min(perfect_pixel_checks, step) of those checks, so up to there each line of pixels keeps its check and a bigger
    step drops canvas items alone. Past it a step drops checks too. With a space before it, or empty."""
    changes = []
    if layout.spacing[4]:
        changes.append("add checks (hundredth_percent_checks 0 makes one every 0.01%)")
    if layout.logic_percent < LogicPercent.range_end:
        changes.append("raise logic_percent")
    if layout.color_depth_items > ColorDepthItems.range_start:
        changes.append("lower color_depth_items")
    least = min(layout.width_increment, layout.height_increment)
    if count == "items" and layout.perfect_thresholds and layout.perfect_pixel_items in ("useful", "any"):
        top = max((step for step in INCREMENTS if step <= layout.perfect_pixel_checks), default=least)
        if top > least:
            changes.append(f"use bigger canvas steps up to {top} px")
    elif least < INCREMENTS[-1]:
        changes.append("use bigger canvas steps")
    if not changes:
        return ""
    if len(changes) > 1:
        changes[-1] = f"or {changes[-1]}"
    text = (", " if len(changes) > 2 else " ").join(changes)
    return f" {text[0].upper()}{text[1:]}."


def goal_image_allowed(text: str) -> bool:
    """Whether a goal_image other than default names an image as D17 allows: an https URL with a host and no user name,
    or the path of a file in the client's own site, which starts inside it, never climbs out with a .. part, spelled
    out or as %2e%2e, and ends in a file name with an extension. Either has at most 2,048 characters, all of them
    printable, and no space or backslash. So http, data: and every other scheme are refused, and so are a path from
    the host's root and the None, True or 2 that a YAML value left empty or typed as a number turns into."""
    if len(text) > GOAL_IMAGE_MOST or not text.isprintable() or " " in text or "\\" in text:
        return False
    try:
        url = urlsplit(text)
        if url.scheme == "https":
            # A port that isn't a number up to 65,535 raises here, as a broken host does above
            return bool(url.hostname) and "@" not in url.netloc and url.port != 0
    except ValueError:
        return False
    parts = unquote(url.path).split("/")
    return not (url.scheme or url.netloc) and parts[0] != "" and ".." not in parts and "." in parts[-1].strip(".")


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
    location_name_groups = location_groups
    item_name_groups = item_groups
    origin_region_name = "Canvas"

    final_width: int
    final_height: int
    goal_image: str  # "default" or goal_image's text, as slot data carries it (D17)
    goal_image_sha256: str  # "" or 64 lowercase hex digits
    start_width: int
    start_height: int
    tiny_start: bool
    layout: Layout  # what logic's ceiling and the solo fill check read from the options (D8, D12)
    palette_colors: int = 0
    allowed_traps: list[str] = []

    def generate_early(self) -> None:
        # The core sets world_version from the .apworld's manifest and leaves 0.0.0 when it reads none, as for a file
        # zipped by hand. A seed would carry that version, and the client would play it as one from before 0.2.0.
        if self.world_version == Version(0, 0, 0):
            raise OptionError(f"{self.player_name}'s Pain-T world loaded as version 0.0.0: Archipelago read no "
                              f"world_version from its archipelago.json. Build paint_hard.apworld with Archipelago's "
                              f"Build APWorlds and generate again.")
        self.read_goal_options()
        if self.options.canvas_width_increment < 50 and self.options.canvas_height_increment < 50 and \
            self.options.logic_percent <= 55 and self.multiworld.players == 1:
            raise OptionError(f"{self.player_name}'s Pain-T world needs logic_percent above 55 when it plays alone "
                              f"with canvas_width_increment and canvas_height_increment both below 50.")
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
                             options.auto_copy_logic_hours.value, precollected, from_pool,
                             options.perfect_pixel_checks.value, options.perfect_pixel_items.current_key,
                             options.timesanity_minutes.value, options.timesanity_hours.value,
                             options.missed_pixel_checks.value,
                             options.start_inventory_from_pool.value.get("Happy Accident", 0))
        self.palette_colors = 0
        self.refuse_unfillable()
        self.drop_priority_checks_without_progression()

    def drop_priority_checks_without_progression(self) -> None:
        """Takes out of priority_locations each check of this seed that takes no progression: the Perfect Pixels checks
        at perfect_pixel_items useful or filler, and every check of the three families with auto copy out of logic.
        Archipelago's priority fill places only progression, and a priority location it can't fill stops the whole
        generation with a FillError. Main.py drops an excluded location from priority_locations the same way, with a
        warning for each."""
        layout = self.layout
        hours = layout.auto_copy_logic_hours
        marks = set(layout.marks)
        families = (
            ("Auto Copy Time", not hours, "auto_copy_logic_hours 0",
             {name for name, address in time_table.items() if address - TIME_BASE in marks}),
            ("Perfect Pixels", layout.perfect_pixel_items != "any" or not hours,
             "auto_copy_logic_hours 0" if layout.perfect_pixel_items == "any" else
             f"perfect_pixel_items {layout.perfect_pixel_items}",
             {f"Perfect Pixels #{k}" for k in range(1, len(layout.perfect_thresholds) + 1)}),
            ("Missed Pixels", not hours, "auto_copy_logic_hours 0",
             {f"Missed Pixels #{j}" for j in range(1, len(layout.missed_targets) + 1)}))
        priority = self.options.priority_locations
        for family, refused, setting, names in families:
            dropped = priority.value & names if refused else set()
            if dropped:
                priority.value -= dropped
                count = len(dropped)
                logging.warning(f"Unable to prioritize {count:,} {family} location{'s' * (count != 1)} in player "
                                f"{self.player}'s world because {'they take' if count != 1 else 'it takes'} no "
                                f"progression with {setting}.")

    def read_goal_options(self) -> None:
        """D17's refusals, ahead of D12's three, and what the seed carries of its goal: the final size, the image's
        name and that image's hash. Generation reads no file and no network and checks the options alone. Then D8's
        refusal of starting_canvas half on a goal whose half start is more than logic can expect painted by hand."""
        name = self.player_name
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
        width, height = self.options.goal_width.value, self.options.goal_height.value  # 0 is aspect_ratio
        if bool(width) != bool(height):
            side, other = ("goal_width", "goal_height") if width else ("goal_height", "goal_width")
            raise OptionError(f"{name}'s Pain-T world sets {side} {width or height} without {other}. Set both, or "
                              f"leave both at aspect_ratio.")
        named = isinstance(self.options.goal_image.value, str)  # a TextChoice keeps default as 0 and other text as is
        if not named and width and (width, height) != (self.final_width, self.final_height):
            raise OptionError(f"{name}'s Pain-T world asks for goal_image default at {width}x{height}, and the bundled "
                              f"image for aspect_ratio {self.options.aspect_ratio.current_key} is "
                              f"{self.final_width}x{self.final_height}. Leave goal_width and goal_height at "
                              f"aspect_ratio, or name your own {width}x{height} image in goal_image.")
        sha256 = self.options.goal_image_sha256.value.lower()
        if sha256 and not named:
            raise OptionError(f"{name}'s Pain-T world sets goal_image_sha256 beside goal_image default. A hash goes "
                              f"with an image named in goal_image: name one, or leave goal_image_sha256 empty.")
        hex_digits = sum(character in hexdigits for character in sha256)
        if sha256 and not len(sha256) == hex_digits == 64:
            raise OptionError(f"{name}'s Pain-T world needs goal_image_sha256 empty or 64 hex digits (0-9 and a-f), "
                              f"the SHA-256 of the image file. It got {len(sha256)} characters, {hex_digits} of them "
                              f"hex digits.")
        if named and not goal_image_allowed(self.options.goal_image.value):
            raise OptionError(f"{name}'s Pain-T world can't take its goal_image. {GOAL_IMAGE_HINT}")
        if width:
            self.final_width, self.final_height = width, height
        self.goal_image = self.options.goal_image.value if named else "default"
        self.goal_image_sha256 = sha256
        half_width, half_height = self.final_width // 2, self.final_height // 2
        if self.options.starting_canvas == self.options.starting_canvas.option_half and \
                half_width * half_height > HALF_START_MOST:
            raise OptionError(f"{name}'s Pain-T world can't use starting_canvas half on its "
                              f"{self.final_width}x{self.final_height} goal: that start is {half_width}x{half_height}, "
                              f"{half_width * half_height:,} pixels for logic to expect painted by hand, and a half "
                              f"start goes up to {HALF_START_MOST:,} (400x400). Use starting_canvas tiny.")

    def refuse_unfillable(self) -> None:
        """D12's refusals, before anything is built: a pool bigger than its locations, the excluded ones left out (D21),
        then progression beyond the locations that take it (task 8.3's count), solo or not, then, for a solo seed, a
        fill check that runs a model of Archipelago's progression fill on the world's logic with fixed seeds. The check
        reads the host's panic_method, as Main.py does for the fill: under swap and raise it models the fill each runs,
        and under start_inventory, where the fill moves what it can't place to the start and no seed fails, it doesn't
        run."""
        items = self.non_filler_items()
        layout = self.layout
        progression = sum(progression_counts(layout)) + happy_count(layout)
        # The Perfect Pixels checks at perfect_pixel_items filler take only filler and traps (D21), so the required
        # items need the other locations.
        excluded = layout.excluded_count
        needed, to_fill = len(items), layout.location_count - excluded
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
                # Margin copies are useful, so no step changes task 8.3's count below: a step is named only where the
                # progression fits the locations that take it too.
                fits = room > 0 and progression <= layout.taking_count
                smallest = (f", and with nothing else changed the items fit from miss_margin_step "
                            f"{ceil(MISS_MARGIN / room)}" if fits else "")
                groups.append((f"miss_margin_step {top_step}", saved, smallest))
            hint = "".join(f" With {settings}, {count} {'more' if n else 'of them'} "
                           f"{'stays' if count == 1 else 'stay'} out{end}."
                           for n, (settings, count, end) in enumerate(groups))
            beside, perfect = "", ""
            if excluded:
                beside = (f" beside the {excluded} Perfect Pixels checks that perfect_pixel_items filler keeps for "
                          f"filler and traps")
                # The other values at which the items fit, task 8.3's count below included
                fitting = [mode for mode in ("useful", "any") if needed <= layout.location_count and
                           progression <= replace(layout, perfect_pixel_items=mode).taking_count]
                if fitting:
                    perfect = (f" With perfect_pixel_items {' or '.join(fitting)}, those {excluded} checks take "
                               f"{'useful items too' if 'useful' in fitting else 'every item'}, and the items fit.")
            raise OptionError(f"{self.player_name}'s Pain-T world has {to_fill} locations for {needed} "
                              f"required items{beside}.{fewer_items_hint(layout, 'items')}{hint}{perfect}")
        # Task 8.3's count (D21, D26): the progression items need the locations that take progression. Above 0 h only
        # the Perfect Pixels checks at perfect_pixel_items useful turn it away, and at any it fits wherever the items
        # do. At 0 h no check of the three families takes it.
        taking = layout.taking_count
        if progression > taking:
            perfect_count = len(layout.perfect_thresholds)
            if layout.auto_copy_logic_hours:
                beside = (f"the {perfect_count:,} Perfect Pixels checks that perfect_pixel_checks "
                          f"{layout.perfect_pixel_checks} makes and perfect_pixel_items useful keeps for useful items, "
                          f"filler and traps")
                fix = (f" With perfect_pixel_items any, those {perfect_count:,} checks take progression too, and the "
                       f"progression fits.")
            else:
                families = [f"{count:,} {family} checks" for family, count in
                            (("Auto Copy Time", len(layout.marks)), ("Perfect Pixels", perfect_count),
                             ("Missed Pixels", len(layout.missed_targets))) if count]
                if len(families) > 1:
                    families[-2:] = [f"{families[-2]} and {families[-1]}"]
                whatever = ", whatever perfect_pixel_items says" if perfect_count else ""
                beside = (f"the {', '.join(families)}, which take no progression with auto_copy_logic_hours "
                          f"0{whatever}")
                fix = ""
            raise OptionError(f"{self.player_name}'s Pain-T world has {taking:,} locations that take progression for "
                              f"{progression:,} progression items beside {beside}."
                              f"{fewer_items_hint(layout, 'progression')}{fix}")
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
        # Happy Accident (D26), one copy while missed_pixel_checks makes the Missed Pixels checks
        if self.options.missed_pixel_checks.value:
            items += ["Happy Accident"]
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
        # Speed and accuracy copies are progression while one can still raise logic's cap (D8), and every speed copy is
        # while the Missed Pixels of D26 are on. create_items() makes the pool's copies past that useful. A start
        # inventory copy stays progression even past auto copy's top tier:
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
        # speed copies 9 and 10. While the Missed Pixels of D26 are on, every speed copy stays progression.
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
        # The Auto Copy Time marks (D21). Progression lands on them like any other, and with auto copy out of logic
        # they turn it away.
        marks = [AutoCopyTimeLocation(self.player, name, address, canvas) for name, address in time_table.items()
                 if location_exists_with_options(self, address)]
        if not self.layout.auto_copy_logic_hours:
            for mark in marks:
                mark.item_rule = no_progression
        canvas.locations += marks
        # The Perfect Pixels checks (D21), as perfect_pixel_items asks: at useful they turn progression away, at filler
        # they are excluded locations, which take only filler and traps, and at any they take every item. With auto
        # copy out of logic they turn progression away at any too.
        targets = self.layout.perfect_thresholds
        perfect = [PerfectPixelsLocation(self.player, name, address, canvas, targets[address - PERFECT_BASE - 1])
                   for name, address in perfect_table.items() if location_exists_with_options(self, address)]
        for location in perfect:
            if self.layout.perfect_pixel_items == "filler":
                location.progress_type = LocationProgressType.EXCLUDED
            elif self.layout.perfect_pixel_items == "useful" or not self.layout.auto_copy_logic_hours:
                location.item_rule = no_progression
        canvas.locations += perfect
        # The Missed Pixels checks (D26). Progression lands on them like any other, and with auto copy out of logic,
        # where Happy Accident alone opens every one, they turn it away.
        ladder = self.layout.missed_targets
        missed = [MissedPixelsLocation(self.player, name, address, canvas, ladder[address - MISSED_BASE - 1])
                  for name, address in missed_table.items() if location_exists_with_options(self, address)]
        if not self.layout.auto_copy_logic_hours:
            for location in missed:
                location.item_rule = no_progression
        canvas.locations += missed

        self.multiworld.regions += [canvas]

    def set_rules(self) -> None:
        from .rules import set_completion_rules
        set_completion_rules(self, self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        # miss_margin_step also marks a seed with D7's misses: the client plays one that has a version but no
        # miss_margin_step as a seed from before Phase 4.
        # auto_copy_logic_hours lets the client show logic's ceiling as the world works it out (D8).
        # goal_image and goal_image_sha256 are on every seed from version 1.2.0 (D17): "default" or the YAML's text,
        # and "" or 64 lowercase hex digits. final_width and final_height carry the goal's size.
        # So are the Auto Copy Time marks (D21): auto_copy_time_targets lists each mark's minutes in order, [] with the
        # family off, beside timesanity_minutes and timesanity_hours. A mark's id is 2,209,000 plus its minutes.
        # And the Perfect Pixels checks (D21): perfect_pixel_targets lists their exact pixels in order, the k-th for id
        # 2,211,000 + k, [] with the family off, beside perfect_pixel_checks and perfect_pixel_items, the option's key.
        # And the Missed Pixels checks (D26): missed_pixel_targets lists their wrong pixels in order, the j-th for id
        # 2,250,000 + j, [] with the family off, beside missed_pixel_checks.
        return dict(self.options.as_dict("logic_percent", "goal_percent", "death_link", "canvas_width_increment",
                                         "canvas_height_increment", "trap_blacklist", "trap_link", "miss_margin_step",
                                         "overclock_seconds", "overclock_bank_size_step", "overclock_fill_speed_step",
                                         "auto_copy_logic_hours", "timesanity_minutes", "timesanity_hours",
                                         "perfect_pixel_checks", "missed_pixel_checks"),
                    final_width=self.final_width, final_height=self.final_height,
                    goal_image=self.goal_image, goal_image_sha256=self.goal_image_sha256,
                    start_width=self.start_width, start_height=self.start_height,
                    matched_pixels=MATCHED_PIXELS if self.tiny_start else 0,
                    shade_counts=list(self.layout.shade_counts),
                    auto_copy_speed_items=self.layout.speed_items,
                    auto_copy_time_targets=list(self.layout.marks),
                    perfect_pixel_items=self.layout.perfect_pixel_items,
                    perfect_pixel_targets=list(self.layout.perfect_thresholds),
                    missed_pixel_targets=list(self.layout.missed_targets),
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
    if TIME_BASE < location <= TIME_BASE + TIME_MARKS:
        return location - TIME_BASE in world.layout.marks  # every timesanity_minutes up to the seed's last mark
    if PERFECT_BASE < location <= PERFECT_BASE + PERFECT_MOST:
        return location - PERFECT_BASE <= len(world.layout.perfect_thresholds)  # one for each of the seed's targets
    if MISSED_BASE < location <= MISSED_BASE + MISSED_NAMES:
        return location - MISSED_BASE <= len(world.layout.missed_targets)  # one for each of the seed's targets
    return grid_exists(location - LOCATION_BASE, world.layout.logic_percent, world.layout.spacing)


# Every world's LogicMixin writes onto the one shared CollectionState, so these names must differ from core
# Paint's paint_percent_available and paint_percent_stale, or the two games overwrite each other's numbers.
class PaintHardState(LogicMixin):
    paint_hard_percent_available: dict[int, float]  # per player
    paint_hard_percent_stale: dict[int, bool]
    paint_hard_reach: dict[int, Reach]  # per player, under the percent's flag: what the checks of D21 and D26 read

    def init_mixin(self, multiworld: MultiWorld) -> None:
        self.paint_hard_percent_available = {player: 0 for player in multiworld.get_game_players("Pain-T")}
        self.paint_hard_percent_stale = {player: True for player in multiworld.get_game_players("Pain-T")}
        self.paint_hard_reach = {player: Reach(0, 0, 0) for player in multiworld.get_game_players("Pain-T")}

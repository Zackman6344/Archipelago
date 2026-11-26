import random
from bisect import bisect_left, bisect_right, insort
from collections import deque
from dataclasses import astuple, dataclass, replace
from functools import cached_property, lru_cache
from math import ceil, floor, inf, log2, sqrt
from typing import TYPE_CHECKING, NamedTuple

from BaseClasses import CollectionState

if TYPE_CHECKING:
    from . import PaintHardWorld

CURVE = 2.0  # 1.0 would spread new shades evenly over the items; 2.0 keeps colors coarse longer and sharpens late
NO_PICK_COLOR_ERROR = 31  # Paint assumes 2 bits at most without Pick Color: a worst error of 31 per channel
# Auto copy (D5, D7): 1 pixel a second, doubled by each Progressive Auto Copy Speed, at a 90% miss chance that each of 9
# Progressive Auto Copy Accuracy lowers by 10 points.
BASE_SPEED_ITEMS = 10
MISS = tuple((9 - copies) / 10 for copies in range(10))
# The checks below 0.01%, in 0.0001% steps: every 0.0001% up to 0.001%, then every 0.001%. The 0.01% check that
# ends the ladder is the grid's first, and it always exists.
EARLY_UNITS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90)
MATCHED_PIXELS = 25  # "Matched Pixels: n", one for each pixel of the 5x5 start
# The checks of D21 and D26: the most any option set makes of each family. Archipelago fixes a game's names and ids
# whatever the YAML, so locations.py names that many of each.
TIME_MARKS = 24 * 60  # "Auto Copy Time: h:mm": a mark for every minute up to 24:00, timesanity_hours' top
PERFECT_MOST = (16384 - 5) * 2  # "Perfect Pixels #k": one for each line of pixels 16384x16384 grows by from 5x5
MISSED_TOP = 720  # missed_pixel_checks' top: the Missed Pixels checks each speed copy opens
SPEED_MOST = 17  # the most speed copies any option set makes (D19), on 16384x16384 at 1 h
MISSED_NAMES = (SPEED_MOST + 2) * MISSED_TOP  # "Missed Pixels #j": each copy's 720, and Happy Accident's own 1,440
INCREMENTS = (5, 10, 20, 25, 50, 100)  # the canvas step choices, in pixels
# The progression kinds, in this order everywhere: the three color channels, canvas width and height, the speed and
# accuracy copies that can still raise the cap, and the first Pick Color. Then each kind's item.
KINDS = ("red", "green", "blue", "width", "height", "speed", "accuracy", "pick")
KIND_ITEMS = ("Progressive Color Depth (Red)", "Progressive Color Depth (Green)", "Progressive Color Depth (Blue)",
              "Progressive Canvas Width", "Progressive Canvas Height", "Progressive Auto Copy Speed",
              "Progressive Auto Copy Accuracy", "Progressive Pick Color")


def round_half_up(x: float) -> int:
    # Python's round() sends halves to even and JS Math.round() sends them up. Both sides use this one.
    return floor(x + 0.5)


@lru_cache(maxsize=None)
def shade_counts(items: int, curve: float = CURVE) -> tuple[int, ...]:
    """Shades per channel after k Progressive Color Depth items, k = 0 to items. Grows from 2 to 256 along
    2 * 128 ** ((k / items) ** curve), and every item adds at least one shade. slot_data carries this table, so the
    client never recomputes it."""
    counts = [2]
    for k in range(1, items + 1):
        counts.append(min(256, max(counts[-1] + 1, round_half_up(2 * 128 ** ((k / items) ** curve)))))
    return tuple(counts)


def quantize(value: int, shades: int) -> int:
    """The nearest of `shades` evenly spaced values from 0 to 255. The client's src/shades.js matches it exactly."""
    index = round_half_up(value * (shades - 1) / 255)
    return round_half_up(index * 255 / (shades - 1))


@lru_cache(maxsize=None)
def worst_error(shades: int) -> int:
    return max(abs(v - quantize(v, shades)) for v in range(256))


def no_pick_color_cap(counts: tuple[int, ...]) -> int:
    """The last item count still no better than Paint's 2 bits, which logic assumes without Pick Color."""
    return max(k for k, shades in enumerate(counts) if worst_error(shades) >= NO_PICK_COLOR_ERROR)


def pixel_score(red_error: int, green_error: int, blue_error: int) -> float:
    """Worst-case score of one pixel on the client's scale, where a perfect pixel is 1."""
    return 1 - 2 * sqrt((red_error ** 2 + green_error ** 2 + blue_error ** 2) / 3) / 255


def grid_exists(i: int, logic: int, spacing: tuple[int, int, int, int, int]) -> bool:
    """Whether "Similarity: {i / 100}%" exists: every 1% up to logic_percent, and every 0.5%, 0.25%, 0.1%, 0.05% and
    0.01% past the percent its spacing option names (half, quarter, tenth, twentieth and hundredth_percent_checks;
    100 means off). 0.01% ends the early checks, so it exists whatever the spacing."""
    if i > logic * 100:
        return False
    step = 100
    for tier_step, start in zip((50, 25, 10, 5, 1), spacing):
        if i > start * 100:
            step = min(step, tier_step)
    return i == 1 or i % step == 0


def auto_copy_pixels(speed: int, accuracy: int, hours: int) -> float:
    """Pixels auto copy gets right in `hours` with `speed` Progressive Auto Copy Speed and `accuracy` Progressive Auto
    Copy Accuracy held (D8). A miss costs a paint and comes back on a later pass; the miss margin never enters logic."""
    return 2 ** speed * (1 - MISS[min(accuracy, len(MISS) - 1)]) * hours * 3600


@lru_cache(maxsize=None)
def perfect_thresholds(start_width: int, start_height: int, final_width: int, final_height: int,
                       width_increment: int, height_increment: int, per_step: int) -> tuple[int, ...]:
    """The Perfect Pixels targets (D21), as plan_math.py's perfect_thresholds(): each canvas step splits into per_step
    parts, never finer than one line of pixels, width and height growing in proportion, and check k asks for as many
    exact pixels as the canvas holds after k parts. The last asks for the whole goal."""
    def positions(start: int, end: int, increment: int) -> list[int]:
        parts = min(per_step, increment)  # never finer than one line of pixels
        found = []
        for j in range(1, ceil((end - start) / increment) * parts + 1):
            position = min(start + round_half_up(increment * j / parts), end)
            if not found or position > found[-1]:
                found.append(position)
        return found

    widths = positions(start_width, final_width, width_increment)
    heights = positions(start_height, final_height, height_increment)
    # The i-th width part sits at i / len(widths) of the way and the j-th height part at j / len(heights), and on a tie
    # the width part comes first.
    order = sorted([((i + 1) / len(widths), 0, i) for i in range(len(widths))] +
                   [((j + 1) / len(heights), 1, j) for j in range(len(heights))])
    width, height = start_width, start_height
    found = []
    for _, side, index in order:
        if side == 0:
            width = widths[index]
        else:
            height = heights[index]
        found.append(width * height)
    return tuple(found)


def rhu(numerator: int, denominator: int) -> int:
    """numerator / denominator rounded half up, exactly, for whole numbers: round_half_up() without floats, as
    plan_math.py's rhu()."""
    return (2 * numerator + denominator) // (2 * denominator)


def ladder_values(k: int, hours: int, copies: int) -> list[int]:
    """Every Missed Pixels check's wrong pixels, ascending, as plan_math.py's ladder_values() (D26). With X = 3,600 x
    timesanity_hours, what Happy Accident's switch makes in those hours at 1 a second, Happy Accident alone opens 2k
    checks evenly up to X, and speed copy s opens k more evenly from 2^(s - 1) X to 2^s X. The last is 2^copies X, what
    the top tier makes in timesanity_hours."""
    x = 3600 * hours
    alone = [rhu(x * j, 2 * k) for j in range(1, 2 * k + 1)]
    runs = [rhu(2 ** (s - 1) * x * (k + j), k) for s in range(1, copies + 1) for j in range(1, k + 1)]
    return alone + runs


@lru_cache(maxsize=None)
def missed_targets(k: int, hours: int, copies: int) -> tuple[int, ...]:
    """The Missed Pixels targets of a seed with missed_pixel_checks k, timesanity_hours and this many speed copies, as
    plan_math.py's missed_targets(): (copies + 2) x k of them, the j-th for "Missed Pixels #j"."""
    return tuple(ladder_values(k, hours, copies))


@dataclass
class Layout:
    """What logic's ceiling and the solo fill check read from a seed: its goal, start and canvas steps, check spacing,
    color table, logic percent, auto copy hours and start inventory. It also carries what the options of D21's and
    D26's checks ask for. The world keeps one; the check's refusal tries others that change a setting."""
    final_width: int
    final_height: int
    start_width: int
    start_height: int
    width_increment: int
    height_increment: int
    logic_percent: int
    spacing: tuple[int, int, int, int, int]  # half, quarter, tenth, twentieth and hundredth_percent_checks
    color_depth_items: int
    starting_color_depth: int
    auto_copy_logic_hours: int
    # The start inventory in copies of each of KINDS: those Archipelago precollects, every copy start_inventory and
    # start_inventory_from_pool name, and those start_inventory_from_pool takes out of the pool
    precollected: tuple[int, ...] = (0,) * len(KINDS)
    from_pool: tuple[int, ...] = (0,) * len(KINDS)
    # The checks of D21 and D26, as their options set them. A family is off at 0: perfect_pixel_checks for Perfect
    # Pixels, timesanity_minutes for Auto Copy Time, missed_pixel_checks for Missed Pixels. perfect_pixel_items is
    # the option's key: useful, filler or any.
    perfect_pixel_checks: int = 0
    perfect_pixel_items: str = "useful"
    timesanity_minutes: int = 0
    timesanity_hours: int = 24
    missed_pixel_checks: int = 0
    # Copies of Happy Accident (D26) that start_inventory_from_pool takes out of the pool, counted as from_pool counts
    # each of KINDS (D12)
    happy_from_pool: int = 0

    @cached_property
    def shade_counts(self) -> tuple[int, ...]:
        return shade_counts(self.color_depth_items)

    @cached_property
    def no_pick_color_cap(self) -> int:
        return no_pick_color_cap(self.shade_counts)

    @cached_property
    def goal_pixels(self) -> int:
        return self.final_width * self.final_height

    @cached_property
    def canvas_items(self) -> tuple[int, int]:
        """Progressive Canvas Width and Height copies: enough steps from the start to the goal's size."""
        return (ceil((self.final_width - self.start_width) / self.width_increment),
                ceil((self.final_height - self.start_height) / self.height_increment))

    @cached_property
    def speed_items(self) -> int:
        """Progressive Auto Copy Speed copies (D19): enough for the top tier to paint the whole goal within the logic
        hours, 6 when auto copy is out of logic, and never fewer than 10."""
        return max(BASE_SPEED_ITEMS, ceil(log2(self.goal_pixels / ((self.auto_copy_logic_hours or 6) * 3600))))

    @cached_property
    def speed_progression(self) -> int:
        """Speed copies the world makes progression. While the Missed Pixels of D26 are on, every copy, since the last
        checks need the last copy. Otherwise those that can still raise the cap (D8): copy t can while t - 1 copies at
        the worst accuracy don't get the whole goal right in the hours. The rest are useful, and so are all of them
        with auto copy out of logic."""
        if not self.auto_copy_logic_hours:
            return 0
        if self.missed_pixel_checks:
            return self.speed_items
        return len([t for t in range(1, self.speed_items + 1)
                    if auto_copy_pixels(t - 1, 0, self.auto_copy_logic_hours) < self.goal_pixels])

    @cached_property
    def accuracy_progression(self) -> int:
        """Accuracy copies that can still raise the cap: copy a can while a - 1 copies at 1 pixel a second don't get the
        whole goal right in the hours, so while a / 10 x hours x 3,600 is below the goal's pixels. All 9 while 0.9 x
        hours x 3,600 is: every goal of 77,761 pixels or more at any hours, today's five among them, and from 19,441
        pixels at 6 h. Fewer below that, none on 50x50 from 7 h, and none with auto copy out of logic."""
        if not self.auto_copy_logic_hours:
            return 0
        return len([a for a in range(1, len(MISS)) if auto_copy_pixels(0, a - 1, self.auto_copy_logic_hours) <
                    self.goal_pixels])

    @cached_property
    def matched(self) -> int:
        """The Matched Pixels checks, which only the 5x5 start has, and logic counts from the start."""
        return MATCHED_PIXELS if (self.start_width, self.start_height) == (5, 5) else 0

    @cached_property
    def units(self) -> tuple[int, ...]:
        """Every similarity location's threshold in 0.0001% steps, sorted: the early checks, then the 0.01% grid."""
        return EARLY_UNITS + tuple(i * 100 for i in range(1, 9901) if grid_exists(i, self.logic_percent, self.spacing))

    @property
    def locations(self) -> int:
        return len(self.units) + self.matched

    @cached_property
    def marks(self) -> tuple[int, ...]:
        """The Auto Copy Time marks in minutes (D21), as plan_math.py's time_marks() makes them: one every
        timesanity_minutes up to timesanity_hours, and none past the goal's pixels / 120 minutes, the most auto copy
        work logic counts on with the whole canvas (time_in_logic()). None with timesanity_minutes at 0."""
        if not self.timesanity_minutes:
            return ()
        top = min(self.timesanity_hours * 60, self.goal_pixels // 120)
        return tuple(range(self.timesanity_minutes, top + 1, self.timesanity_minutes))

    @cached_property
    def perfect_thresholds(self) -> tuple[int, ...]:
        """The Perfect Pixels targets in exact pixels (D21), the k-th for "Perfect Pixels #k": every check
        perfect_pixel_checks asks for, at most PERFECT_MOST. None with perfect_pixel_checks at 0."""
        if not self.perfect_pixel_checks:
            return ()
        return perfect_thresholds(self.start_width, self.start_height, self.final_width, self.final_height,
                                  self.width_increment, self.height_increment, self.perfect_pixel_checks)

    @cached_property
    def missed_targets(self) -> tuple[int, ...]:
        """The Missed Pixels targets in wrong pixels (D26), the j-th for "Missed Pixels #j": (speed_items + 2) x
        missed_pixel_checks of them, at most MISSED_NAMES. None with missed_pixel_checks at 0."""
        if not self.missed_pixel_checks:
            return ()
        return missed_targets(self.missed_pixel_checks, self.timesanity_hours, self.speed_items)

    @property
    def location_count(self) -> int:
        """Every location the seed makes, as plan_math.py's location_count(): the similarity checks and Matched Pixels,
        which the solo fill check models, the Auto Copy Time marks, the Perfect Pixels checks and the Missed Pixels
        checks."""
        return self.locations + len(self.marks) + len(self.perfect_thresholds) + len(self.missed_targets)

    @property
    def excluded_count(self) -> int:
        """Locations that take only filler and traps, as plan_math.py's excluded_count(): the Perfect Pixels checks at
        perfect_pixel_items filler (D21)."""
        return len(self.perfect_thresholds) if self.perfect_pixel_items == "filler" else 0

    @property
    def no_progression_count(self) -> int:
        """Locations that turn progression away and take useful items, as plan_math.py's no_progression_count(): the
        Perfect Pixels checks at perfect_pixel_items useful, and at any with auto copy out of logic (D21), and with auto
        copy out of logic the Auto Copy Time marks (D21) and the Missed Pixels checks (D26)."""
        refuse = self.perfect_pixel_items == "useful" or (self.perfect_pixel_items == "any" and
                                                          not self.auto_copy_logic_hours)
        out_of_logic = 0 if self.auto_copy_logic_hours else len(self.marks) + len(self.missed_targets)
        return len(self.perfect_thresholds) * refuse + out_of_logic

    @property
    def taking_count(self) -> int:
        """Locations that take progression, as plan_math.py's taking_count(): every location but the excluded ones and
        those that turn progression away."""
        return self.location_count - self.excluded_count - self.no_progression_count


def percent_available(layout: Layout, red: int, green: int, blue: int, width: int, height: int, speed: int,
                      accuracy: int, pick_color: bool) -> float:
    """Logic's similarity ceiling (D8), as plan_math.py's percent_available(). red, green and blue count the color items
    held, starting ones included; width and height the canvas items; speed and accuracy the auto copy copies logic
    counts. Logic expects painted what auto copy gets right in auto_copy_logic_hours, at your full color depth, plus
    the starting canvas by hand, at 2 bits at most without Pick Color, as upstream assumes. With auto copy out of logic,
    the whole unlocked canvas by hand. Speed copies past auto copy's top tier, layout.speed_items, count as the top
    tier, as the client's auto copy runs them."""
    counts = layout.shade_counts

    def score(cap: int) -> float:
        return pixel_score(*(worst_error(counts[min(n, cap)]) for n in (red, green, blue)))

    full = score(len(counts) - 1)
    by_hand = full if pick_color else score(layout.no_pick_color_cap)
    area = (min(layout.start_width + width * layout.width_increment, layout.final_width) *
            min(layout.start_height + height * layout.height_increment, layout.final_height))
    hours = layout.auto_copy_logic_hours
    copied = min(area, auto_copy_pixels(min(speed, layout.speed_items), accuracy, hours)) if hours else 0
    painted = min(area, copied + layout.start_width * layout.start_height) if hours else area
    # To 6 decimals where Paint rounds to 3: the first checks are 0.0001% apart.
    return round((full * copied + by_hand * (painted - copied)) * layout.logic_percent / layout.goal_pixels, 6)


# The rules of the checks of D21 and D26, as plan_math.py has them. unlocked_area(), time_in_logic(), copy_budget() and
# perfect_in_logic() keep its names, and missed_reach() is the bound its missed_in_logic() counts targets up to. A state
# works out the three figures with its percent and keeps them beside it (paint_reach()), and each check compares its
# own target with its family's figure.
def unlocked_area(layout: Layout, width: int, height: int) -> int:
    """The canvas's pixels with these width and height items, up to the goal's size."""
    return (min(layout.start_width + width * layout.width_increment, layout.final_width) *
            min(layout.start_height + height * layout.height_increment, layout.final_height))


def time_in_logic(layout: Layout, width: int, height: int) -> int:
    """Whole minutes of auto copy work logic counts on (D21), so every Auto Copy Time mark up to this many minutes is
    in logic. At 1 pixel a second auto copy spends a second on every pixel it paints, and painting the canvas over
    with black or white, whichever fewer goal pixels want, leaves at least half of it to paint: 120 pixels a minute."""
    return unlocked_area(layout, width, height) // 120


def copy_budget(layout: Layout, speed: int, accuracy: int) -> float:
    """Pixels auto copy gets right in auto_copy_logic_hours (D8), at no more than its top tier's speed. Unlimited with
    auto copy out of logic."""
    hours = layout.auto_copy_logic_hours
    return auto_copy_pixels(min(speed, layout.speed_items), accuracy, hours) if hours else inf


def perfect_in_logic(layout: Layout, red: int, green: int, blue: int, width: int, height: int, speed: int,
                     accuracy: int) -> float:
    """Pixels logic expects can equal the goal exactly (D21). Generation never sees the goal and only all 256 shades
    hold every value, so none until every color item of each channel is held, starting ones included; then the
    unlocked canvas, up to what auto copy gets right within its budget."""
    if min(red, green, blue) < layout.color_depth_items:
        return 0
    return min(unlocked_area(layout, width, height), copy_budget(layout, speed, accuracy))


def missed_reach(layout: Layout, speed: int, happy: bool) -> float:
    """The most wrong pixels a Missed Pixels check in logic asks for (D26). None without Happy Accident. With it, what
    its switch makes in timesanity_hours at the speed copies held, 2^s x 3,600 x timesanity_hours, reading speed copies
    up to auto copy's top tier as percent_available() reads them; and every check at auto_copy_logic_hours 0."""
    if not happy:
        return 0
    if not layout.auto_copy_logic_hours:
        return inf
    return 2 ** min(speed, layout.speed_items) * 3600 * layout.timesanity_hours


class Reach(NamedTuple):
    """A state's figures for the checks of D21 and D26. A check is in logic once its family's figure reaches its
    target: an Auto Copy Time mark's minutes, a Perfect Pixels check's exact pixels, a Missed Pixels check's wrong
    pixels."""
    minutes: int  # time_in_logic()
    perfect: float  # perfect_in_logic()
    missed: float  # missed_reach()


def family_reach(layout: Layout, red: int, green: int, blue: int, width: int, height: int, speed: int, accuracy: int,
                 happy: bool) -> Reach:
    """The three figures for a state that holds these items, counted as percent_available() counts them, and Happy
    Accident."""
    return Reach(time_in_logic(layout, width, height),
                 perfect_in_logic(layout, red, green, blue, width, height, speed, accuracy),
                 missed_reach(layout, speed, happy))


# D12's solo fill check, as plan_math.py's: a model of Archipelago's progression fill, run on the world's own logic
# with fixed seeds.
PASSES = 5  # fill passes a verdict reads, with seeds 1 to 5
TO_PASS = 3  # of them that must fill
SWAPS_PER_NAME = 2  # fill_restrictive swaps a name out at most twice safely and twice unsafely
# The host's generator.panic_method values the check models, each with whether fill_restrictive swaps under it. Under
# start_inventory Archipelago moves what it can't place to the start, so no seed fails and the check doesn't run.
SWAPS = {"swap": True, "raise": False}
# The spacing tiers a refusal tries at 0, in the Layout's spacing order, with the step each gives
TIERS = (("half_percent_checks", "0.5%"), ("quarter_percent_checks", "0.25%"), ("tenth_percent_checks", "0.1%"),
         ("twentieth_percent_checks", "0.05%"), ("hundredth_percent_checks", "0.01%"))
HOURS = (0, 2, 6, 12, 24)  # the auto_copy_logic_hours a refusal tries


def start_counts(items: dict[str, int]) -> tuple[int, ...]:
    """Copies of each of KINDS among these items, as a start inventory option names them."""
    return tuple(items.get(name, 0) for name in KIND_ITEMS)


def progression_counts(layout: Layout) -> tuple[int, ...]:
    """The pool's progression items of each kind. start_inventory_from_pool takes a name's first copies out of the
    pool, and those are the ones create_items() leaves progression. Happy Accident (D26) is none of the kinds: until
    task 8.3 the model leaves it out, with the Missed Pixels checks it opens."""
    colors = layout.color_depth_items - layout.starting_color_depth
    width, height = layout.canvas_items
    counts = colors, colors, colors, width, height, layout.speed_progression, layout.accuracy_progression, 1
    return tuple(max(0, count - taken) for count, taken in zip(counts, layout.from_pool))


def happy_count(layout: Layout) -> int:
    """Happy Accident (D26): one copy, progression, in the pool while missed_pixel_checks is above 0, unless
    start_inventory_from_pool takes it out. D12 and D26 count start inventory for it as for the other eight kinds, and
    plan_math.py's happy_count() leaves start_inventory_from_pool out. Task 8.3's count adds it to
    progression_counts()."""
    return max(0, 1 - layout.happy_from_pool) if layout.missed_pixel_checks else 0


def location_percents(layout: Layout) -> list[float]:
    """Every location's required percent, sorted: the Matched Pixels at 0, then the similarity checks. A state reaches
    a location when its ceiling is at least that percent, as PaintLocation.access_rule has it, so the locations a state
    reaches are always the first ones of this list."""
    return [0.0] * layout.matched + [units / 10000 for units in layout.units]


class FillPass:
    """One pass of a model of Archipelago's progression fill on a solo seed's logic, with its own seed. It shuffles the
    progression items and the locations, as distribute_items_restrictive() does, then places the items as Fill.py's
    fill_restrictive() does for a solo seed, as it has since Archipelago 0.6.5 (PR #5516): one at a time, the end of
    the shuffled pool first, each into the first free location in the shuffled list that its state reaches. The state
    holds the start inventory, every item not yet placed and every placed item it sweeps up, again and again. An item
    that finds no location tries fill_restrictive's swaps in its order: each placed item of another name, earliest
    placed first, at most twice per name for each kind of swap, safe swaps (the state leaves that item out) before
    unsafe ones (it counts it in). The item swapped out goes to the far end of the queue. A pass fails when an item
    finds no location and no swap, or when, after a swap, a sweep from the start misses a placement (fill_restrictive's
    cleanup). That is the fill under the host's panic_method swap, Archipelago's default. With swap False the pass
    makes no swaps, as fill_restrictive does under raise. Nothing else decides the fill on this world: one region, no
    item rules, and accessibility, which the check takes as full."""

    def __init__(self, layout: Layout, seed: int, swap: bool = True):
        self.layout = layout
        self.swapping = swap
        self.percents = location_percents(layout)
        self.random = random.Random(seed)
        self.reached: dict[tuple[int, ...], int] = {}  # locations reached by each set of held items, as counted
        self.placed: list[list[int]] = [[] for _ in KINDS]  # each kind's placed locations, sorted
        self.placements: list[list[int]] = []  # [location, kind] in the order fill_restrictive keeps them
        self.swapped: dict[tuple[int, bool], int] = {}  # swaps out of each kind, safe (False) and unsafe (True)
        self.swaps = 0
        self.left = None  # items still to place when a pass fails, 0 for a failed cleanup

    def in_logic(self, held: tuple[int, ...]) -> int:
        """How many locations a state with these progression items, and the start inventory, reaches."""
        if held not in self.reached:
            start = self.layout.starting_color_depth
            red, green, blue, width, height, speed, accuracy, pick = (count + copies for count, copies in
                                                                     zip(held, self.layout.precollected))
            ceiling = percent_available(self.layout, red + start, green + start, blue + start, width, height, speed,
                                        accuracy, pick > 0)
            self.reached[held] = bisect_right(self.percents, ceiling)
        return self.reached[held]

    def sweep(self, held: list[int]) -> int:
        """How many locations these items reach once every placed item in reach is collected, until none is left."""
        reach = self.in_logic(tuple(held))
        while True:
            more = self.in_logic(tuple(count + bisect_left(locations, reach)
                                       for count, locations in zip(held, self.placed)))
            if more == reach:
                return reach
            reach = more

    def place(self, location: int, kind: int) -> None:
        insort(self.placed[kind], location)
        self.placements.append([location, kind])

    def swap(self, kind: int, unplaced: list[int], reach: int, queue: deque) -> bool:
        """fill_restrictive's swap for an item with no free location in reach."""
        for unsafe in (False, True):
            if unsafe:
                # Each kind's unsafe state, with its placed items left where they are: no unsafe swap reaches further
                bounds = [self.sweep([count + (k == other) for k, count in enumerate(unplaced)])
                          for other in range(len(KINDS))]
            for index, (location, other) in enumerate(self.placements):
                if other == kind or self.swapped.get((other, unsafe), 0) >= SWAPS_PER_NAME:
                    continue
                if location >= (bounds[other] if unsafe else reach):
                    continue
                locations = self.placed[other]
                del locations[bisect_left(locations, location)]
                held = [count + (unsafe and k == other) for k, count in enumerate(unplaced)]
                if location < self.sweep(held):
                    self.swapped[other, unsafe] = self.swapped.get((other, unsafe), 0) + 1
                    self.swaps += 1
                    del self.placements[index]
                    self.place(location, kind)
                    queue.appendleft(other)
                    unplaced[other] += 1
                    return True
                insort(locations, location)
        return False

    def run(self) -> bool:
        """Whether this pass places every progression item."""
        pool = [kind for kind, count in enumerate(progression_counts(self.layout)) for _ in range(count)]
        self.random.shuffle(pool)
        free = list(range(len(self.percents)))
        self.random.shuffle(free)
        return self.fill(pool, free)

    def fill(self, pool: list[int], free: list[int]) -> bool:
        """Whether fill_restrictive, handed these items, by kind, and these locations, by place in location_percents(),
        in these orders, places every item: the end of the pool first, each into the first location its state
        reaches."""
        queue = deque(pool)
        unplaced = [pool.count(kind) for kind in range(len(KINDS))]  # the items in the queue
        while queue:
            kind = queue.pop()
            unplaced[kind] -= 1
            reach = self.sweep(unplaced)
            spot = next((index for index, location in enumerate(free) if location < reach), None)
            if spot is not None:
                self.place(free.pop(spot), kind)
            elif not (self.swapping and self.swap(kind, unplaced, reach, queue)):
                self.left = len(queue) + 1
                return False
        if self.swaps:
            reach = self.sweep([0] * len(KINDS))
            if any(location >= reach for location, _ in self.placements):
                self.left = 0
                return False
        return True


_verdicts: dict[tuple, tuple[int, int]] = {}


def passes_filled(layout: Layout, panic_method: str = "swap") -> tuple[int, int]:
    """(passes that filled, passes run) under the host's panic_method, seeds 1 up, stopping once TO_PASS have filled
    or can't. The fixed seeds give one verdict for each YAML and method, and the cache saves working it out again."""
    key = panic_method, astuple(layout)
    if key not in _verdicts:
        filled = tried = 0
        while tried < PASSES and TO_PASS - PASSES + tried <= filled < TO_PASS:
            tried += 1
            filled += FillPass(layout, tried, SWAPS[panic_method]).run()
        _verdicts[key] = filled, tried
    return _verdicts[key]


def fills(layout: Layout, panic_method: str = "swap") -> bool:
    return passes_filled(layout, panic_method)[0] >= TO_PASS


def single_changes(layout: Layout) -> list[list[tuple[str, Layout]]]:
    """The single changes a refusal tries, by option, each as the player would set it and the least change first:
    each spacing tier at 0 where that adds checks, coarsest first; each canvas step bigger than the seed's, on one
    axis, then on both at once; and a few hours, 0 among them. Each keeps the seed's start inventory."""
    width, height = layout.width_increment, layout.height_increment
    tiers = []
    for index, (option, every) in enumerate(TIERS):
        other = replace(layout, spacing=layout.spacing[:index] + (0,) + layout.spacing[index + 1:])
        if other.locations > layout.locations:
            tiers.append((f"{option} 0 (a check every {every} from the start)", other))
    return [tiers,
            [(f"canvas_width_increment {step}", replace(layout, width_increment=step))
             for step in INCREMENTS if step > width],
            [(f"canvas_height_increment {step}", replace(layout, height_increment=step))
             for step in INCREMENTS if step > height],
            [(f"canvas_width_increment and canvas_height_increment {step}",
              replace(layout, width_increment=step, height_increment=step))
             for step in INCREMENTS if step > min(width, height) and step not in (width, height)],
            [(f"auto_copy_logic_hours {hours}", replace(layout, auto_copy_logic_hours=hours))
             for hours in HOURS if hours != layout.auto_copy_logic_hours]]


def change_fills(layout: Layout, other: Layout, items_needed: int, panic_method: str = "swap") -> bool:
    """Whether a solo seed with this change passes every refusal in generate_early: upstream's logic-55 rule, the item
    count, task 8.3's count of progression and the fill check. `items_needed` is the seed's own count of non-filler
    items, which only the canvas steps change, and the hours on a goal bigger than 10 speed copies paint in the fewer of
    the two hours, with 0 counting as 6 (3.7 megapixels at 1 h, 7.4 at 2 h, 22.1 at 6 h)."""
    if other.width_increment < 50 and other.height_increment < 50 and other.logic_percent <= 55:
        return False
    needed = (items_needed - sum(layout.canvas_items) + sum(other.canvas_items) + other.speed_items -
              layout.speed_items)
    return (needed <= other.location_count - other.excluded_count and
            sum(progression_counts(other)) + happy_count(other) <= other.taking_count and fills(other, panic_method))


def passing_changes(layout: Layout, items_needed: int, panic_method: str = "swap") -> tuple[list[str], int]:
    """The changes a refusal names, and how many it tried. For the spacing tiers and each kind of canvas step, the
    least change whose every pass filled, or, when none did, the least change that passes; and every hours value
    that passes."""
    passing, tried = [], 0
    *options, hours = single_changes(layout)
    for changes in options:
        least = None
        for name, other in changes:
            tried += 1
            if change_fills(layout, other, items_needed, panic_method):
                least = least or name
                filled, runs = passes_filled(other, panic_method)
                if filled == runs:
                    least = name
                    break
        if least:
            passing.append(least)
    filling_hours = []
    for name, other in hours:
        tried += 1
        if change_fills(layout, other, items_needed, panic_method):
            filling_hours.append(str(other.auto_copy_logic_hours))
    if filling_hours:
        passing.append(f"auto_copy_logic_hours {' or '.join(filling_hours)}")
    return passing, tried


def refusal(player: str, layout: Layout, items_needed: int, panic_method: str = "swap") -> str:
    """The solo refusal's message. It gives the tries as passes_filled() counts them: the passes run, which stop once
    the ones left can't bring the filled ones to TO_PASS. The changes it names are a sample, each tried on its own with
    the same check. It names the host's panic_method when that isn't swap, Archipelago's default. Until task 8.3 gives
    the model a reach for each family, it also names the checks of D21 and D26 the model leaves out where they take
    progression: the Auto Copy Time marks and the Missed Pixels checks with auto copy in logic, and the Perfect Pixels
    checks at perfect_pixel_items any with auto copy in logic. It ends on the check's scope, since a host can try a
    multiworld's YAML alone first."""
    filled, tried = passes_filled(layout, panic_method)
    passing, sampled = passing_changes(layout, items_needed, panic_method)
    left = PASSES - tried
    counted = f" It filled {filled} of the {'first ' if left else ''}{tried}"
    if left and filled + left < TO_PASS:
        counted += f", and with {left} {'try' if left == 1 else 'tries'} left it can't reach {TO_PASS}"
    counted += "."
    if passing:
        fixes = (f" From a sample of {sampled} single changes, these pass the same check with nothing else changed: "
                 f"{'; '.join(passing)}.")
    else:
        fixes = (f" None of a sample of {sampled} single changes passes the check; try two at once, or play it beside "
                 f"a Pain-T slot at the defaults.")
    method = "" if panic_method == "swap" else f" under the host's panic_method {panic_method}"
    families = []
    if layout.marks and layout.auto_copy_logic_hours:
        families.append(f"{len(layout.marks):,} Auto Copy Time checks")
    if layout.perfect_thresholds and layout.perfect_pixel_items == "any" and layout.auto_copy_logic_hours:
        families.append(f"{len(layout.perfect_thresholds):,} Perfect Pixels checks")
    if layout.missed_targets and layout.auto_copy_logic_hours:
        families.append(f"{len(layout.missed_targets):,} Missed Pixels checks")
    if len(families) > 1:
        families[-2:] = [f"{families[-2]} and {families[-1]}"]
    left_out = (f" The model places progression on the similarity checks and Matched Pixels alone and leaves out this "
                f"seed's {', '.join(families)}." if families else "")
    return (f"{player}'s Pain-T world can't be filled alone: a model of Archipelago's fill{method}, run on its logic "
            f"with fixed seeds, has to place every progression item in {TO_PASS} of {PASSES} tries.{counted}{left_out}"
            f"{fixes} Beside other slots this check doesn't run, and Archipelago's own fill decides.")


def paint_percent_available(state: CollectionState, world: "PaintHardWorld", player: int) -> bool:
    if state.paint_hard_percent_stale[player]:
        state.paint_hard_percent_available[player] = calculate_paint_percent_available(state, world, player)
        state.paint_hard_reach[player] = calculate_paint_reach(state, world, player)
        state.paint_hard_percent_stale[player] = False
    return state.paint_hard_percent_available[player]


def paint_reach(state: CollectionState, world: "PaintHardWorld", player: int) -> Reach:
    """A state's figures for the checks of D21 and D26, worked out with its percent, under the same flag, and kept
    until an item it holds changes."""
    if state.paint_hard_percent_stale[player]:
        paint_percent_available(state, world, player)
    return state.paint_hard_reach[player]


def calculate_paint_percent_available(state: CollectionState, world: "PaintHardWorld", player: int) -> float:
    # Only progression copies count in a state, so speed and accuracy copies past the cap's reach don't.
    return percent_available(world.layout,
                             *(state.count(f"Progressive Color Depth ({color})", player)
                               for color in ("Red", "Green", "Blue")),
                             state.count("Progressive Canvas Width", player),
                             state.count("Progressive Canvas Height", player),
                             state.count("Progressive Auto Copy Speed", player),
                             state.count("Progressive Auto Copy Accuracy", player),
                             state.has("Progressive Pick Color", player))


def calculate_paint_reach(state: CollectionState, world: "PaintHardWorld", player: int) -> Reach:
    # The same progression copies as the percent counts, and Happy Accident
    return family_reach(world.layout,
                        *(state.count(f"Progressive Color Depth ({color})", player)
                          for color in ("Red", "Green", "Blue")),
                        state.count("Progressive Canvas Width", player),
                        state.count("Progressive Canvas Height", player),
                        state.count("Progressive Auto Copy Speed", player),
                        state.count("Progressive Auto Copy Accuracy", player),
                        state.has("Happy Accident", player))


def set_completion_rules(world: "PaintHardWorld", player: int) -> None:
    goal_percent = min(world.options.logic_percent.value, world.options.goal_percent.value)
    world.multiworld.completion_condition[player] = \
        lambda state: paint_percent_available(state, world, player) >= goal_percent

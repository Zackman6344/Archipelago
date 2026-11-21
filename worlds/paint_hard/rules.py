from functools import lru_cache
from math import floor, sqrt
from typing import TYPE_CHECKING

from BaseClasses import CollectionState

if TYPE_CHECKING:
    from . import PaintHardWorld

CURVE = 2.0  # 1.0 would spread new shades evenly over the items; 2.0 keeps colors coarse longer and sharpens late
NO_PICK_COLOR_ERROR = 31  # Paint assumes 2 bits at most without Pick Color: a worst error of 31 per channel


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


def paint_percent_available(state: CollectionState, world: "PaintHardWorld", player: int) -> bool:
    if state.paint_hard_percent_stale[player]:
        state.paint_hard_percent_available[player] = calculate_paint_percent_available(state, world, player)
        state.paint_hard_percent_stale[player] = False
    return state.paint_hard_percent_available[player]


def calculate_paint_percent_available(state: CollectionState, world: "PaintHardWorld", player: int) -> float:
    counts = world.shade_counts
    cap = len(counts) - 1 if state.has("Pick Color", player) else world.no_pick_color_cap
    errors = [worst_error(counts[min(state.count(f"Progressive Color Depth ({color})", player), cap)])
              for color in ("Red", "Green", "Blue")]
    w = state.count("Progressive Canvas Width", player)
    h = state.count("Progressive Canvas Height", player)
    # (worst score per pixel) * (pixels unlocked) * (logic percent) / (total pixels), to 6 decimals where Paint
    # rounds to 3: the first checks are 0.0001% apart.
    return round(pixel_score(*errors) *
            min(world.start_width + w * world.options.canvas_width_increment.value, world.final_width) *
            min(world.start_height + h * world.options.canvas_height_increment.value, world.final_height) *
            world.per_pixel_logic_percent, ndigits=6)


def set_completion_rules(world: "PaintHardWorld", player: int) -> None:
    goal_percent = min(world.options.logic_percent.value, world.options.goal_percent.value)
    world.multiworld.completion_condition[player] = \
        lambda state: paint_percent_available(state, world, player) >= goal_percent

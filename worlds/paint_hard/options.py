from dataclasses import dataclass
from typing import Any

from Options import (OptionSet, Range, PerGameCommonOptions, Removed, StartInventoryPool, Toggle, Choice,
                     DefaultOnToggle, FreeText, NamedRange, TextChoice)

# The goal sizes the Options Creator lists for goal_width and goal_height, in pixels: the bundled goals' sides, the
# sizes the docs name and common screen and power-of-two sizes
GOAL_SIDES = (450, 600, 800, 1024, 1080, 1200, 1280, 1440, 1500, 1600, 1920, 2000, 2048, 2160, 2560, 3000, 3072, 3840,
              4000, 4096, 6144, 8192, 12288, 16384)


def picks(*values: int) -> dict[str, int]:
    """special_range_names that name each value by its own number, as the Options Creator lists them."""
    return {str(value): value for value in values}


class LogicPercent(Range):
    """Sets the maximum percent similarity required for a check to be in logic.
    Higher values are more difficult and items/locations will not be generated beyond this number."""
    display_name = "Logic Percent"
    range_start = 50
    range_end = 99
    default = 80


class GoalPercent(Range):
    """Sets the percent similarity required to achieve your goal.
    If this number is higher than the value for logic percent,
    reaching goal will be in logic upon obtaining all progression items."""
    display_name = "Goal Percent"
    range_start = 50
    range_end = 99
    default = 80


class HalfPercentChecks(Range):
    """Sets the lowest percent above which there is a check every 0.5% of similarity.
    Below every tier's start there is a check every 1%. Where several tiers have started, the finest one sets the
    spacing. 100 turns this tier off."""
    display_name = "Half Percent Checks"
    range_start = 0
    range_end = 100
    default = 50


class QuarterPercentChecks(Range):
    """Sets the lowest percent above which there is a check every 0.25% of similarity.
    Where several tiers have started, the finest one sets the spacing. 100 turns this tier off."""
    display_name = "Quarter Percent Checks"
    range_start = 0
    range_end = 100
    default = 70


class TenthPercentChecks(Range):
    """Sets the lowest percent above which there is a check every 0.1% of similarity.
    Where several tiers have started, the finest one sets the spacing. 100 turns this tier off."""
    display_name = "Tenth Percent Checks"
    range_start = 0
    range_end = 100
    default = 100


class TwentiethPercentChecks(Range):
    """Sets the lowest percent above which there is a check every 0.05% of similarity.
    Where several tiers have started, the finest one sets the spacing. 100 turns this tier off."""
    display_name = "Twentieth Percent Checks"
    range_start = 0
    range_end = 100
    default = 100


class HundredthPercentChecks(Range):
    """Sets the lowest percent above which there is a check every 0.01% of similarity.
    Where several tiers have started, the finest one sets the spacing. 100 turns this tier off.
    Below 0.01% there are always 18 more checks: every 0.0001% up to 0.001%, then every 0.001%."""
    display_name = "Hundredth Percent Checks"
    range_start = 0
    range_end = 100
    default = 0


class StartingCanvas(Choice):
    """Sets the size of your canvas before any width or height items.
    Tiny is 5x5 pixels. Half is half the final width and height, as in Paint (400x300 for a fullscreen image). Half is
    refused on a goal where that start passes 160,000 pixels, the 400x400 of an 800x800 goal."""
    display_name = "Starting Canvas"
    option_tiny = 0
    option_half = 1
    default = 0


class ColorDepthItems(NamedRange):
    """Sets how many Progressive Color Depth items each of red, green and blue takes to go from 2 shades to all 256.
    At 254, the most, every item adds exactly one shade. With fewer, most of the new shades come with the last few
    items. Paint takes 7.
    In the Options Creator the list beside the slider holds common values, and an exact value the slider can't reach
    goes into the exported YAML with a text editor."""
    display_name = "Color Depth Items"
    range_start = 7
    range_end = 254
    special_range_names = picks(7, 15, 31, 63, 127, 254)
    default = 254


class StartingColorDepth(Range):
    """Sets how many Progressive Color Depth items of each color you start with. 0 starts every channel at black and
    white (0 and 255), so 8 colors in all. 1 gives 3 shades per channel (0, 128 and 255), about what Paint starts
    with."""
    display_name = "Starting Color Depth"
    range_start = 0
    range_end = 3
    default = 0


class CanvasSizeIncrement(Removed):
    """Sets the number of pixels the canvas will expand for each width/height item received.
    Ensure an adequate number of locations are generated if setting this below 50."""
    display_name = "Canvas Size Increment"


class CanvasWidthIncrement(Choice):
    """Sets the number of pixels the canvas will expand for each width item received.
    Small steps mean many items: from a tiny start on a fullscreen image, 5 pixels makes 159 width items."""
    display_name = "Canvas Width Increment"
    option_5 = 5
    option_10 = 10
    option_20 = 20
    option_25 = 25
    option_50 = 50
    option_100 = 100
    default = 100


class CanvasHeightIncrement(Choice):
    """Sets the number of pixels the canvas will expand for each height item received.
    Small steps mean many items: from a tiny start on a fullscreen image, 5 pixels makes 119 height items."""
    display_name = "Canvas Height Increment"
    option_5 = 5
    option_10 = 10
    option_20 = 20
    option_25 = 25
    option_50 = 50
    option_100 = 100
    default = 100


class AspectRatio(Choice):
    """Sets the aspect ratio of your final image. Useful when using a custom goal image, also affects game length.
    Possible options are fullscreen (800x600), widescreen (800x450), square (800x800), fullscreen vertical (600x800),
    and widescreen vertical (450x800). goal_width and goal_height, when set, give the size in its place."""
    display_name = "Aspect Ratio"
    option_fullscreen = 0
    option_widescreen = 1
    option_square = 2
    option_fullscreen_vertical = 3
    option_widescreen_vertical = 4
    default = 0


class GoalImage(TextChoice):
    """Sets the image you will be required to match. default is the bundled image for your aspect ratio.
    Any other value names an image of your own: an https URL, or the path of an image file in the client's own site,
    such as images/archipelago/800x600.png. http and data: URLs are refused. An image whose size isn't the aspect
    ratio's needs goal_width and goal_height, and default is refused at any other size.
    Generation reads no file and no network and takes a wrong size, a dead link or a mistyped hash as typed. The seed
    carries the name, the size and goal_image_sha256.
    In the Options Creator, press Enter after typing or pasting, since in Archipelago 0.6.6 the box keeps a value only
    then."""
    display_name = "Goal Image"
    option_default = 0
    alias_1 = 0  # an old YAML's goal_image: 1
    default = 0


class GoalWidth(NamedRange):
    """Sets the width of your goal image in pixels, from 50 to 16384. aspect_ratio, the default, takes the width your
    aspect ratio gives. Set goal_width and goal_height together, to the size of the image goal_image names.
    A bigger goal makes more canvas items, and one past 22.1 megapixels more Progressive Auto Copy Speed copies at the
    default 6 hours: 12 at 8192x8192 and 14 at 16384x16384.
    In the Options Creator the list beside the slider holds common values, and an exact value the slider can't reach
    goes into the exported YAML with a text editor."""
    display_name = "Goal Width"
    range_start = 50
    range_end = 16384
    special_range_names = {"aspect_ratio": 0, **picks(*GOAL_SIDES)}
    default = 0


class GoalHeight(NamedRange):
    """Sets the height of your goal image in pixels, from 50 to 16384. aspect_ratio, the default, takes the height
    your aspect ratio gives. Set goal_width and goal_height together, to the size of the image goal_image names.
    In the Options Creator the list beside the slider holds common values, and an exact value the slider can't reach
    goes into the exported YAML with a text editor."""
    display_name = "Goal Height"
    range_start = 50
    range_end = 16384
    special_range_names = {"aspect_ratio": 0, **picks(*GOAL_SIDES)}
    default = 0


class GoalImageSha256(FreeText):
    """Sets the SHA-256 of the image file goal_image names, as 64 hex digits. Empty, the default, gives the seed no
    hash, and a hash is refused beside goal_image default. The seed carries it in lowercase beside the image's name.
    In the Options Creator, press Enter after typing or pasting, since in Archipelago 0.6.6 the box keeps a value only
    then."""
    display_name = "Goal Image SHA-256"

    @classmethod
    def from_any(cls, data: Any) -> "GoalImageSha256":
        # A YAML line left empty arrives as None, which FreeText would keep as the text "None"
        return cls.from_text("" if data is None else str(data))


class StartingTool(Choice):
    """Sets which tool (other than Magnifier) you will be able to use from the start."""
    display_name = "Starting Tool"
    option_brush = 0
    option_pencil = 1
    option_eraser = 2
    option_airbrush = 3
    option_line = 4
    option_rectangle = 5
    option_ellipse = 6
    option_rounded_rectangle = 7
    default = 0


class TrapCount(Range):
    """Sets the percentage of filler items to be replaced by random traps."""
    display_name = "Trap Fill Percent"
    range_start = 0
    range_end = 100
    default = 0


class TrapBlacklist(OptionSet):
    """These types of traps will not be generated into the item pool nor received from Trap Link.
    Possible traps are "Undo Trap", "Clear Image Trap", "Invert Colors Trap", "Flip Horizontal Trap",
    "Flip Vertical Trap", "Help Trap", "Zoom In Trap", "Zoom Out Trap", "Tool Swap Trap"."""
    display_name = "Trap Blacklist"
    valid_keys = [
        "Undo Trap", "Clear Image Trap", "Invert Colors Trap", "Flip Horizontal Trap", "Flip Vertical Trap",
        "Help Trap", "Zoom In Trap", "Zoom Out Trap", "Tool Swap Trap"
    ]


class TrapLink(Toggle):
    """Received traps will be simultaneously sent to other players with trap link on. This also works in reverse."""
    display_name = "Trap Link"


class DeathLink(Toggle):
    """If on, using the Undo or Clear Image functions will send a death to all other players with death link on.
    Receiving a death will clear the image and reset the history.
    This option also adds Undo and Clear Image traps to the trap blacklist."""
    display_name = "Death Link"


class AutoCopyLogicHours(Range):
    """How many hours of auto copy logic expects. Logic counts the pixels auto copy gets right in that time, at the
    speed and accuracy items you hold, plus the starting canvas painted by hand, so on a goal whose white canvas scores
    0% or more, as the bundled ones do, no check in logic needs more auto copy than this. The Auto Copy Time and Missed
    Pixels checks are the two exceptions: timesanity_minutes and missed_pixel_checks say how long they take. 0 takes
    auto copy out of logic: logic then expects the whole unlocked canvas painted by hand, as in Paint."""
    display_name = "Auto Copy Logic Hours"
    range_start = 0
    range_end = 24
    default = 6


class MissMarginStep(NamedRange):
    """How much each Progressive Miss Margin lowers the miss margin. A miss by auto copy or M paints each channel a
    random shade you can paint now, within the margin of the right one. The margin starts at 255, and the last copy
    brings it to 0, so 1 puts 255 items in the pool, 5 puts 51 and 255 puts one. A seed with few checks can raise it.
    In the Options Creator the list beside the slider holds common values, and an exact value the slider can't reach
    goes into the exported YAML with a text editor."""
    display_name = "Miss Margin Step"
    range_start = 1
    range_end = 255
    special_range_names = picks(1, 3, 5, 15, 17, 51, 85, 255)  # each a divisor of 255, so every copy lowers it alike
    default = 1


class OverclockSeconds(NamedRange):
    """Sets how many seconds of double auto copy speed each Overclock gives. Overclock is the filler once 26
    Additional Palette Colors have filled the palette. 0 makes it do nothing.
    In the Options Creator the list beside the slider holds common values, and an exact value the slider can't reach
    goes into the exported YAML with a text editor."""
    display_name = "Overclock Seconds"
    range_start = 0
    range_end = 120
    special_range_names = picks(0, 1, 2, 5, 10, 15, 30, 60, 120)
    default = 5


class OverclockBankSizeItems(Range):
    """How many Progressive Overclock Bank Size items go in the pool. Each lets the Overclock bank hold
    overclock_bank_size_step more seconds of double auto copy speed. The bank fills by itself while you're connected
    and auto copy isn't running, at the speed the Progressive Overclock Fill Speed items give, and Overclock fillers
    add on top of it. 0 means nothing fills by itself."""
    display_name = "Overclock Bank Size Items"
    range_start = 0
    range_end = 20
    default = 5


class OverclockBankSizeStep(NamedRange):
    """How many seconds of double speed each Progressive Overclock Bank Size lets the bank hold.
    In the Options Creator the list beside the slider holds common values, and an exact value the slider can't reach
    goes into the exported YAML with a text editor."""
    display_name = "Overclock Bank Size Step"
    range_start = 10
    range_end = 3600
    special_range_names = picks(10, 30, 60, 120, 300, 600, 900, 1800, 3600)
    default = 120


class OverclockFillSpeedItems(Range):
    """How many Progressive Overclock Fill Speed items go in the pool. Each fills the Overclock bank faster by
    itself, by overclock_fill_speed_step seconds of double speed a minute, while you're connected and auto copy isn't
    running. 0 means nothing fills by itself."""
    display_name = "Overclock Fill Speed Items"
    range_start = 0
    range_end = 20
    default = 5


class OverclockFillSpeedStep(Range):
    """How many seconds of double speed a minute each Progressive Overclock Fill Speed adds to the bank's own fill."""
    display_name = "Overclock Fill Speed Step"
    range_start = 1
    range_end = 60
    default = 2


class ToolSizeLadders(DefaultOnToggle):
    """Each painting tool starts one pixel wide, and its own Progressive items unlock the rest of its sizes, shapes
    or fills, smallest first: Brush Size and Brush Shape, Eraser Size, Airbrush Size, Line Width (shared by Line, Curve
    and the shapes) and a Fill for each shape. They add 23 useful items. Off opens every size from the start, as in
    Paint."""
    display_name = "Tool Size Ladders"


class PerfectPixelChecks(Range):
    """Perfect Pixels checks send as pixels of your canvas equal the goal exactly. This sets how many checks each
    canvas step gets: the step splits into this many parts, never finer than one line of pixels, and each part's
    check asks for as many exact pixels as the canvas holds once it has grown that far. The last check asks for the
    whole goal. 5 makes 70 checks on a fullscreen image from a tiny start in 100 pixel steps, and 1,390 in 5 pixel
    steps, one for each line of pixels. Logic expects none before you hold every Progressive Color Depth item. 0
    turns the checks off."""
    display_name = "Perfect Pixel Checks"
    range_start = 0
    range_end = 20
    default = 0


class PerfectPixelItems(Choice):
    """Sets what the Perfect Pixels checks can hold. useful lets filler, traps and useful items in and turns
    progression away. filler makes them excluded locations, which take only filler and traps. any lets progression
    land on them too, and logic expects such a check only once you hold every Progressive Color Depth item. With
    auto_copy_logic_hours at 0 they turn progression away at any too.
    At useful and at any, Archipelago's fill puts useful items of every game on these checks, which open last, beyond
    their share of the locations. In a seed of 30 slots, 8 of them Pain-T in 5 pixel steps with every family at its
    top, 5,462 of the 6,995 useful items sat on those 8 slots' Perfect Pixels checks, 26% of the locations. With one
    such slot of 30, 28% to 34% of the useful items sat on its 8,182 checks, 11% of the locations. Those seeds ran at
    any."""
    display_name = "Perfect Pixel Items"
    option_useful = 0
    option_filler = 1
    option_any = 2
    default = 0


class TimesanityMinutes(NamedRange):
    """Auto Copy Time checks send as auto copy works, counted in all over every session, tab and device. This sets the
    minutes between them: 10 makes a check at 0:10, 0:20 and so on up to timesanity_hours, 144 checks at 24 hours,
    and 1 makes 1,440. Logic expects a check once your canvas has 120 pixels for each of its minutes, and a goal
    makes none past its own pixels / 120 minutes, which only cuts goals under 172,800 pixels at 24 hours.
    Progression lands on these checks like any other, and the last one takes up to timesanity_hours of auto copy in
    all. With auto_copy_logic_hours at 0 they turn progression away. 0 turns the checks off.
    In the Options Creator the list beside the slider holds common values, and an exact value the slider can't reach
    goes into the exported YAML with a text editor."""
    display_name = "Timesanity Minutes"
    range_start = 0
    range_end = 1440
    special_range_names = {"disabled": 0, **picks(1, 2, 5, 10, 15, 20, 30, 60, 120, 360, 720, 1440)}
    default = 0


class TimesanityHours(Range):
    """Sets how far the Auto Copy Time checks go, in hours of auto copy's work in all. It also sets the Missed Pixels
    ladder: missing on purpose this many hours at your top speed reaches the last check, whatever timesanity_minutes
    is, 0 included."""
    display_name = "Timesanity Hours"
    range_start = 1
    range_end = 24
    default = 24


class MissedPixelChecks(NamedRange):
    """Missed Pixels checks send as auto copy and M paint wrong pixels, counted in all, and Happy Accident, which this
    puts in the pool, gives auto copy a switch that makes it miss on purpose. This sets how many checks each
    Progressive Auto Copy Speed opens. Happy Accident alone opens twice as many, and the last check is what your top
    speed paints in timesanity_hours. Each check takes timesanity_hours / (2 x this) of missing on purpose at the
    speed that first opens it: 30 minutes at 24 and 24 hours, a minute at 720. Below timesanity_hours / 4 that passes
    the 2 hours an archipelago.gg room waits for a check. Progression lands on these checks like any other, and more
    checks hold more of it. With auto_copy_logic_hours at 0 they turn it away. 0 turns the checks and Happy Accident
    off.
    In the Options Creator the list beside the slider holds common values, and an exact value the slider can't reach
    goes into the exported YAML with a text editor."""
    display_name = "Missed Pixel Checks"
    range_start = 0
    range_end = 720
    special_range_names = {"disabled": 0, **picks(1, 2, 6, 12, 24, 48, 72, 120, 240, 360, 720)}
    default = 0


@dataclass
class PaintOptions(PerGameCommonOptions):
    logic_percent: LogicPercent
    goal_percent: GoalPercent
    half_percent_checks: HalfPercentChecks
    quarter_percent_checks: QuarterPercentChecks
    tenth_percent_checks: TenthPercentChecks
    twentieth_percent_checks: TwentiethPercentChecks
    hundredth_percent_checks: HundredthPercentChecks
    starting_canvas: StartingCanvas
    color_depth_items: ColorDepthItems
    starting_color_depth: StartingColorDepth
    canvas_size_increment: CanvasSizeIncrement
    canvas_width_increment: CanvasWidthIncrement
    canvas_height_increment: CanvasHeightIncrement
    aspect_ratio: AspectRatio
    goal_image: GoalImage
    goal_width: GoalWidth
    goal_height: GoalHeight
    goal_image_sha256: GoalImageSha256
    starting_tool: StartingTool
    trap_count: TrapCount
    trap_blacklist: TrapBlacklist
    trap_link: TrapLink
    death_link: DeathLink
    auto_copy_logic_hours: AutoCopyLogicHours
    miss_margin_step: MissMarginStep
    overclock_seconds: OverclockSeconds
    overclock_bank_size_items: OverclockBankSizeItems
    overclock_bank_size_step: OverclockBankSizeStep
    overclock_fill_speed_items: OverclockFillSpeedItems
    overclock_fill_speed_step: OverclockFillSpeedStep
    tool_size_ladders: ToolSizeLadders
    perfect_pixel_checks: PerfectPixelChecks
    perfect_pixel_items: PerfectPixelItems
    timesanity_minutes: TimesanityMinutes
    timesanity_hours: TimesanityHours
    missed_pixel_checks: MissedPixelChecks
    start_inventory_from_pool: StartInventoryPool

from dataclasses import dataclass

from Options import (OptionSet, Range, PerGameCommonOptions, Removed, StartInventoryPool, Toggle, Choice, Visibility,
                     DefaultOnToggle)


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
    Tiny is 5x5 pixels. Half is half the final width and height, as in Paint (400x300 for a fullscreen image)."""
    display_name = "Starting Canvas"
    option_tiny = 0
    option_half = 1
    default = 0


class ColorDepthItems(Range):
    """Sets how many Progressive Color Depth items each of red, green and blue takes to go from 2 shades to all 256.
    At 254, the most, every item adds exactly one shade. With fewer, most of the new shades come with the last few
    items. Paint takes 7."""
    display_name = "Color Depth Items"
    range_start = 7
    range_end = 254
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
    and widescreen vertical (450x800)."""
    display_name = "Aspect Ratio"
    option_fullscreen = 0
    option_widescreen = 1
    option_square = 2
    option_fullscreen_vertical = 3
    option_widescreen_vertical = 4
    default = 0


class GoalImage(Range):
    """Sets the numbered image you will be required to match.
    See https://github.com/MarioManTAW/jspaint/tree/master/images/archipelago
    for a list of possible images or choose random.
    This can also be overwritten client-side by using File->Open."""
    display_name = "Goal Image"
    range_start = 1
    range_end = 1
    default = 1
    visibility = Visibility.none


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
    0% or more, as the bundled ones do, no check in logic needs more auto copy than this. 0 takes auto copy out of
    logic: logic then expects the whole unlocked canvas painted by hand, as in Paint."""
    display_name = "Auto Copy Logic Hours"
    range_start = 0
    range_end = 24
    default = 6


class MissMarginStep(Range):
    """How much each Progressive Miss Margin lowers the miss margin. A miss by auto copy or M paints each channel a
    random shade you can paint now, within the margin of the right one. The margin starts at 255, and the last copy
    brings it to 0, so 1 puts 255 items in the pool, 5 puts 51 and 255 puts one. A seed with few checks can raise it."""
    display_name = "Miss Margin Step"
    range_start = 1
    range_end = 255
    default = 1


class OverclockSeconds(Range):
    """Sets how many seconds of double auto copy speed each Overclock gives. Overclock is the filler once 26
    Additional Palette Colors have filled the palette. 0 makes it do nothing."""
    display_name = "Overclock Seconds"
    range_start = 0
    range_end = 120
    default = 5


class OverclockBankSizeItems(Range):
    """How many Progressive Overclock Bank Size items go in the pool. Each lets the Overclock bank hold another
    Overclock Bank Size Step of double auto copy speed. The bank fills by itself while you're connected and auto copy
    isn't running, at the speed the Progressive Overclock Fill Speed items give, and Overclock fillers add on top of it.
    0 means nothing fills by itself."""
    display_name = "Overclock Bank Size Items"
    range_start = 0
    range_end = 20
    default = 5


class OverclockBankSizeStep(Range):
    """How many seconds of double speed each Progressive Overclock Bank Size lets the bank hold."""
    display_name = "Overclock Bank Size Step"
    range_start = 10
    range_end = 3600
    default = 120


class OverclockFillSpeedItems(Range):
    """How many Progressive Overclock Fill Speed items go in the pool. Each fills the Overclock bank faster by
    itself, by Overclock Fill Speed Step seconds of double speed a minute, while you're connected and auto copy isn't
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
    start_inventory_from_pool: StartInventoryPool

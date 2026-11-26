from typing import NamedTuple, Dict

from BaseClasses import Item, ItemClassification


class PaintItem(Item):
    game = "Pain-T"


class PaintItemData(NamedTuple):
    code: int
    type: ItemClassification


item_data_table: Dict[str, PaintItemData] = {
    "Progressive Canvas Width":         PaintItemData(2198501, ItemClassification.progression),
    "Progressive Canvas Height":        PaintItemData(2198502, ItemClassification.progression),
    "Progressive Color Depth (Red)":    PaintItemData(2198503, ItemClassification.progression),
    "Progressive Color Depth (Green)":  PaintItemData(2198504, ItemClassification.progression),
    "Progressive Color Depth (Blue)":   PaintItemData(2198505, ItemClassification.progression),
    "Free-Form Select":                 PaintItemData(2198506, ItemClassification.useful),
    "Select":                           PaintItemData(2198507, ItemClassification.useful),
    "Eraser/Color Eraser":              PaintItemData(2198508, ItemClassification.useful),
    "Fill With Color":                  PaintItemData(2198509, ItemClassification.useful),
    # Two copies (D23): the first unlocks the tool, the second gives auto copy a mode. Only the first is progression.
    "Progressive Pick Color":           PaintItemData(2198510, ItemClassification.progression),
    "Magnifier":                        PaintItemData(2198511, ItemClassification.useful),
    "Pencil":                           PaintItemData(2198512, ItemClassification.useful),
    "Brush":                            PaintItemData(2198513, ItemClassification.useful),
    "Airbrush":                         PaintItemData(2198514, ItemClassification.useful),
    "Text":                             PaintItemData(2198515, ItemClassification.useful),
    "Line":                             PaintItemData(2198516, ItemClassification.useful),
    "Curve":                            PaintItemData(2198517, ItemClassification.useful),
    "Rectangle":                        PaintItemData(2198518, ItemClassification.useful),
    "Polygon":                          PaintItemData(2198519, ItemClassification.useful),
    "Ellipse":                          PaintItemData(2198520, ItemClassification.useful),
    "Rounded Rectangle":                PaintItemData(2198521, ItemClassification.useful),
    # "Change Background Color":          PaintItemData(2198522, ItemClassification.useful),
    "Additional Palette Color":         PaintItemData(2198523, ItemClassification.filler),
    "Undo Trap":                        PaintItemData(2198524, ItemClassification.trap),
    "Clear Image Trap":                 PaintItemData(2198525, ItemClassification.trap),
    "Invert Colors Trap":               PaintItemData(2198526, ItemClassification.trap),
    "Flip Horizontal Trap":             PaintItemData(2198527, ItemClassification.trap),
    "Flip Vertical Trap":               PaintItemData(2198528, ItemClassification.trap),
    "Help Trap":                        PaintItemData(2198529, ItemClassification.trap),
    "Zoom In Trap":                     PaintItemData(2198530, ItemClassification.trap),
    "Zoom Out Trap":                    PaintItemData(2198531, ItemClassification.trap),
    "Tool Swap Trap":                   PaintItemData(2198532, ItemClassification.trap),
    "Overclock":                        PaintItemData(2198533, ItemClassification.filler),
    # Each copy doubles auto copy's top speed, from 1 pixel a second. The class here is the one at
    # auto_copy_logic_hours 0. With auto copy in logic, create_item() and create_items() make the copies that can
    # still raise the cap progression (D8), and every copy while missed_pixel_checks is above 0 (D26).
    "Progressive Auto Copy Speed":      PaintItemData(2198534, ItemClassification.useful),
    # Two copies each (D23): the first unlocks the view, the second gives auto copy a mode.
    "Progressive Difference Mode":      PaintItemData(2198535, ItemClassification.useful),
    "Progressive Similarity Mode":      PaintItemData(2198536, ItemClassification.useful),
    # Tool ladders (D24): each painting tool starts one pixel wide, and each copy unlocks the next part of its option
    # box in the client, smallest first. TOOL_LADDERS in __init__.py has the copies.
    "Progressive Brush Size":           PaintItemData(2198537, ItemClassification.useful),
    "Progressive Brush Shape":          PaintItemData(2198538, ItemClassification.useful),
    "Progressive Eraser Size":          PaintItemData(2198539, ItemClassification.useful),
    "Progressive Airbrush Size":        PaintItemData(2198540, ItemClassification.useful),
    "Progressive Line Width":           PaintItemData(2198541, ItemClassification.useful),
    "Progressive Rectangle Fill":       PaintItemData(2198542, ItemClassification.useful),
    "Progressive Polygon Fill":         PaintItemData(2198543, ItemClassification.useful),
    "Progressive Ellipse Fill":         PaintItemData(2198544, ItemClassification.useful),
    "Progressive Rounded Rectangle Fill": PaintItemData(2198545, ItemClassification.useful),
    # The Overclock bank (D25): each Bank Size copy lets it hold more, each Fill Speed copy fills it faster by itself.
    "Progressive Overclock Bank Size":  PaintItemData(2198546, ItemClassification.useful),
    "Progressive Overclock Fill Speed": PaintItemData(2198547, ItemClassification.useful),
    # Misses, margin and passes (D7): each Accuracy copy takes 10 points off the 90% miss chance, each Miss Margin copy
    # lowers the miss margin from 255 by miss_margin_step, and Loop starts each next pass by itself. Accuracy copies
    # get their class as speed copies do (D8). Margin copies and Loop stay useful at every auto_copy_logic_hours.
    "Progressive Auto Copy Accuracy":   PaintItemData(2198548, ItemClassification.useful),
    "Progressive Miss Margin":          PaintItemData(2198549, ItemClassification.useful),
    "Auto Copy Loop":                   PaintItemData(2198550, ItemClassification.useful),
    # Happy Accident (D26) lets auto copy miss on purpose, and logic holds every Missed Pixels check until it is
    # found. One copy, for seeds with missed_pixel_checks above 0, and progression at every auto_copy_logic_hours.
    "Happy Accident":                   PaintItemData(2198551, ItemClassification.progression),
}

item_table = {name: data.code for name, data in item_data_table.items()}
traps = [
    "Undo Trap", "Clear Image Trap", "Invert Colors Trap", "Flip Horizontal Trap", "Flip Vertical Trap", "Help Trap",
    "Zoom In Trap", "Zoom Out Trap", "Tool Swap Trap"
]
# Name groups, which a YAML's local_items, non_local_items and start_hints take in place of the names. Every item is
# in one group but the two fillers, Additional Palette Color and Overclock: a group in local_items keeps each of its
# items in your own world, and a seed has thousands of fillers.
item_groups = {
    "Canvas": {"Progressive Canvas Width", "Progressive Canvas Height"},
    "Color Depth": {"Progressive Color Depth (Red)", "Progressive Color Depth (Green)",
                    "Progressive Color Depth (Blue)"},
    # The toolbox: Magnifier, the 8 starting_tool choices and the 7 others
    "Tools": {"Magnifier", "Brush", "Pencil", "Eraser/Color Eraser", "Airbrush", "Line", "Rectangle", "Ellipse",
              "Rounded Rectangle", "Free-Form Select", "Select", "Fill With Color", "Progressive Pick Color", "Text",
              "Curve", "Polygon"},
    # What tool_size_ladders puts in the pool (D24)
    "Tool Size Ladders": {"Progressive Brush Size", "Progressive Brush Shape", "Progressive Eraser Size",
                          "Progressive Airbrush Size", "Progressive Line Width", "Progressive Rectangle Fill",
                          "Progressive Polygon Fill", "Progressive Ellipse Fill",
                          "Progressive Rounded Rectangle Fill"},
    "Views": {"Progressive Difference Mode", "Progressive Similarity Mode"},
    # Every item that changes auto copy alone, the Overclock bank's two ladders among them
    "Auto Copy": {"Progressive Auto Copy Speed", "Progressive Auto Copy Accuracy", "Progressive Miss Margin",
                  "Auto Copy Loop", "Happy Accident", "Progressive Overclock Bank Size",
                  "Progressive Overclock Fill Speed"},
    "Traps": set(traps),
}

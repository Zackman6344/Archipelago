from typing import NamedTuple, Dict

from BaseClasses import Item, ItemClassification


class PaintItem(Item):
    game = "Paint Hard Mode"


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
    "Pick Color":                       PaintItemData(2198510, ItemClassification.progression),
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
}

item_table = {name: data.code for name, data in item_data_table.items()}
traps = [
    "Undo Trap", "Clear Image Trap", "Invert Colors Trap", "Flip Horizontal Trap", "Flip Vertical Trap", "Help Trap",
    "Zoom In Trap", "Zoom Out Trap", "Tool Swap Trap"
]

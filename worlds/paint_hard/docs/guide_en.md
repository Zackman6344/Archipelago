# Pain-T Start Guide

## Rolling a seed

Pain-T refuses a YAML it can't fill before anything is built, and its message says what to change:

- A seed with Pain-T alone needs `logic_percent` above 55 when `canvas_width_increment` and `canvas_height_increment`
  are both below 50, as in Paint.
- A seed whose items outnumber its locations is refused with both counts. More checks, a higher `logic_percent`, fewer
  `color_depth_items` or bigger canvas steps make room, and the message says how many items `tool_size_ladders` off,
  the Overclock bank's items at 0 or a bigger `miss_margin_step` leave out.
- A seed with Pain-T alone is refused when a model of Archipelago's fill, run on its logic with fixed seeds, places
  every progression item in fewer than 3 of 5 tries. Items in your start inventory count from the start. The message
  names single changes from a sample that pass the same check with nothing else changed, such as
  `hundredth_percent_checks: 0` for a check every 0.01% from the start, a bigger canvas step for fewer canvas items, or
  another `auto_copy_logic_hours`. Make one of them. When it names none, make two at once, or play the YAML beside a
  Pain-T slot at the defaults.

Near the check's edge a seed it passes can still fail to fill, with "No more spots to place" from Archipelago. Roll it
again with another seed number, or make one of those changes. A host whose `host.yaml` sets `panic_method` to
`start_inventory` skips the check, and under `raise` the check makes no swaps, as Archipelago's fill makes none.

## Playing

After rolling your seed, go to the [Pain-T client](https://zackman6344.github.io/jspaint/) and enter the
server details, your slot name, and a room password if one is required. Then click "Connect". If desired, you may then
load a custom target image with File->Open Goal Image. Logic counts on a white canvas scoring 0% or more against the
goal, as it does on the bundled goals. On a goal of your own where a white canvas scores below 0%, such as a mostly dark
image, a check in logic can need more than `auto_copy_logic_hours` of auto copy. If playing asynchronously, note that
progress is saved using the hash that will appear at the end of the URL so it is recommended to leave the tab open or
save the URL with the hash to avoid losing progress.


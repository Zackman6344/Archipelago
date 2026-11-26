# Pain-T Start Guide

## The goal image

`goal_image: default` plays the bundled image for your `aspect_ratio`. Any other value names an image of your own:

- an https URL with a host and no user name, such as `https://example.com/goal.png`, or
- the path of an image file in the client's own site, such as `images/archipelago/800x600.png`: no leading slash, no
  `..` part, and a file name with an extension.

Either has no whitespace or backslash and at most 2,048 characters, and http and `data:` URLs are refused.
`goal_width` and `goal_height` give the image's size in pixels, from 50 to 16,384 each. Set both, or leave both at
`aspect_ratio` for an image of the aspect ratio's size. `goal_image_sha256` takes the SHA-256 of the image file as 64
hex digits, and stays empty for none:

```yaml
Pain-T:
  goal_image: https://example.com/goal.png
  goal_width: 2000
  goal_height: 1500
  goal_image_sha256: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
```

**Generation reads no file and no network**, and it takes a wrong size, a dead link or a mistyped hash as typed. The
seed carries the image's name, its size and its hash, never the pixels, and a generated seed keeps what its YAML said.
Check the size, and take the hash from the file as its host serves it: a host can re-encode what you upload.

**Until the client reads `goal_image`, it loads `images/archipelago/{width}x{height}.png` from its own site at the
seed's size**, whatever `goal_image` names. For a goal of your own, put its file at that path in the client's site and
name the same path in `goal_image`.

The canvas items follow the size, and so do the Progressive Auto Copy Speed copies: enough for the top speed to paint
the whole goal within `auto_copy_logic_hours` (6 hours at `auto_copy_logic_hours: 0`), and never fewer than 10. At the
default 6 hours 10 copies cover 22.1 megapixels, 8192x8192 gets 12 and 16384x16384 gets 14.

## Perfect Pixels, Auto Copy Time and Missed Pixels

Three families of checks come beside the similarity checks. Each is off by default, with its first option at 0.

- **Perfect Pixels** send as pixels of your canvas equal the goal exactly. `perfect_pixel_checks` (0 to 20) sets how
  many each canvas step gets, and the last asks for the whole goal: 5 makes 70 checks on 800x600 from the 5x5 start in
  100 px steps, and 1,390 in 5 px steps. Logic expects none before you hold every Progressive Color Depth item, and
  then counts the unlocked canvas up to what auto copy gets right in `auto_copy_logic_hours`. `perfect_pixel_items`
  sets what they hold: `useful`, the default, takes useful items, filler and traps; `filler` takes filler and traps
  alone; and `any` takes every item. With `auto_copy_logic_hours: 0` they turn progression away at `any` too. At
  `useful` and at `any`, Archipelago's fill puts useful items of every game on these checks, which open last, beyond
  their share of the locations. In a seed of 30 slots, 8 of them Pain-T in 5 px steps with every family at its top,
  5,462 of the 6,995 useful items sat on those 8 slots' Perfect Pixels checks, 26% of the locations. With one such
  slot of 30, 28% to 34% of the useful items sat on its 8,182 checks, 11% of the locations. Those seeds ran at `any`.
- **Auto Copy Time** checks send as auto copy works, counted in all over every session, tab and device.
  `timesanity_minutes` (0 to 1,440) sets the minutes between them, up to `timesanity_hours` (1 to 24, default 24): 10
  makes a check at 0:10, 0:20 and so on, 144 in all. Logic expects a check once your canvas has 120 pixels for each of
  its minutes, and none comes past the goal's pixels / 120 minutes. The last one takes up to `timesanity_hours` of
  auto copy in all.
- **Missed Pixels** send as auto copy and M paint wrong pixels, counted in all. `missed_pixel_checks` (0 to 720) sets
  how many each Progressive Auto Copy Speed opens, and puts Happy Accident in the pool, one progression item that
  gives auto copy a switch to miss on purpose. Happy Accident alone opens twice as many, and the last check is what
  your top speed paints in `timesanity_hours`: 24 makes 288 checks on 800x600. Each takes `timesanity_hours` / (2 x
  `missed_pixel_checks`) of missing on purpose at the speed that first opens it, 30 minutes at 24 checks and 24 hours.
  While they are on and `auto_copy_logic_hours` is above 0, every speed item is progression.

Progression lands on the Auto Copy Time and Missed Pixels checks like any other, and the two are the exceptions to
`auto_copy_logic_hours`: their last checks wait on up to `timesanity_hours` of auto copy, or of Happy Accident's
switch. With `auto_copy_logic_hours: 0` they turn progression away.

**The client doesn't send Perfect Pixels, Auto Copy Time or Missed Pixels checks yet**, and items on them wait for the
release that does.

## Making the YAML in the Options Creator

Archipelago's Options Creator shows a number option as a slider, and a slider over thousands of values can't land on
an exact one. `goal_width`, `goal_height`, `color_depth_items`, `miss_margin_step`, `overclock_seconds`,
`overclock_bank_size_step`, `timesanity_minutes` and `missed_pixel_checks` have a list beside the slider that holds
common values, such as 4096 for a goal's side, and `disabled` for 0 on `timesanity_minutes` and
`missed_pixel_checks`. A value picked from the list is exported as text, such as `goal_width: '4096'`, and reads as
the number. An exact value the slider can't reach goes into the exported YAML with a text editor. In the text boxes
of `goal_image` and `goal_image_sha256`, press Enter after typing or pasting: in Archipelago 0.6.6 a box keeps a
value only then.

## Rolling a seed

Pain-T refuses a YAML it can't use or can't fill before anything is built, and its message says what to change. The
refusals run in this order:

- The goal options: `goal_width` set without `goal_height`, or the other way round; `goal_image: default` at a size
  other than the aspect ratio's; a `goal_image_sha256` beside `default`, or one that isn't 64 hex digits; and a
  `goal_image` that is neither an https URL nor a path in the client's own site, as above.
- `starting_canvas: half` on a goal whose half start passes 160,000 pixels, the 400x400 of an 800x800 goal. Logic
  expects the starting canvas painted by hand.
- A seed with Pain-T alone needs `logic_percent` above 55 when `canvas_width_increment` and `canvas_height_increment`
  are both below 50, as in Paint.
- A seed whose items outnumber its locations is refused with both counts, solo or not. The count leaves out the
  Perfect Pixels checks at `perfect_pixel_items: filler`, which take only filler and traps. More checks, a higher
  `logic_percent`, fewer `color_depth_items` or bigger canvas steps make room. At `useful` and `any`, where the
  Perfect Pixels checks hold items, the message names bigger steps only up to `perfect_pixel_checks` pixels: up to
  there each line of pixels keeps its check, and a bigger step leaves out canvas items alone. The message also says
  how many items `tool_size_ladders` off, the Overclock bank's items at 0 or a bigger `miss_margin_step` leave out,
  and at `filler` which other `perfect_pixel_items` values make the items fit.
- A seed whose progression items outnumber the locations that take progression is refused with both counts, solo or
  not. With `auto_copy_logic_hours` above 0 only the Perfect Pixels checks at `perfect_pixel_items: useful` turn
  progression away, and the message says that `any` lets them take it. With `auto_copy_logic_hours: 0` the Auto Copy
  Time, Perfect Pixels and Missed Pixels checks all turn it away, and the message names each family the seed has.
- A seed with Pain-T alone is refused when a model of Archipelago's fill, run on its logic with fixed seeds, places
  every progression item in fewer than 3 of 5 tries. Items in your start inventory count from the start. The model
  places progression on the similarity checks and Matched Pixels alone: it leaves out Happy Accident and the checks of
  the three families, and the message names those checks where they take progression. The message also names single
  changes from a sample that pass the same check with nothing else changed, such as `hundredth_percent_checks: 0` for
  a check every 0.01% from the start, a bigger canvas step for fewer canvas items, or another
  `auto_copy_logic_hours`. Make one of them. When it names none, make two at once, or play the YAML beside a Pain-T
  slot at the defaults. Beside other slots this check doesn't run, and Archipelago's own fill decides. A YAML the
  check refuses alone can fail there too: 4096x4096 in 5 px steps with 20 Perfect Pixels checks a step at `any` and
  the other two families off failed Archipelago's fill beside one Hollow Knight slot at 3 of 3 seeds, with "No more
  spots to place", and filled there in 100 px steps.

Near the check's edge a seed it passes can still fail to fill, with "No more spots to place" from Archipelago. Roll it
again with another seed number, or make one of those changes. A host whose `host.yaml` sets `panic_method` to
`start_inventory` skips the check, and under `raise` the check makes no swaps, as Archipelago's fill makes none.

A big goal can sit near that edge even in 100 px steps. With Pain-T alone and the other options at their defaults,
real seeds filled 4 of 6 at 4096x4096 in 100 px steps, 3 of 3 at 4000x3000 in 25 px steps and 4 of 9 in 10 px steps,
4 of 6 at 8192x8192 in 100 px steps, and 3 of 6 at 16384x16384 in 100 px steps.

## Names and groups

Each family names its checks in a form of its own: `Similarity: 50.0%`, `Similarity: 0.05%`, `Matched Pixels: 22`,
`Auto Copy Time: 23:44`, `Auto Copy Time: 1:05`, `Perfect Pixels #3` and `Missed Pixels #22`. Type them that way:
the server takes a name in another family's form for a near one, and `!hint_location Missed Pixels: 22` gets a "did
you mean" with `Missed Pixels #2` or `Missed Pixels #22`.

The item groups Auto Copy, Canvas, Color Depth, Tools, Tool Size Ladders, Views and Traps hold every item but the two
fillers, and the location groups Similarity, Matched Pixels, Auto Copy Time, Perfect Pixels and Missed Pixels hold
every check. `local_items`, `non_local_items` and `start_hints` take an item group in place of its items' names, and
`exclude_locations`, `priority_locations` and `start_location_hints` a location group. In the room `!hint` takes an
item group and `!hint_location` a location group: where hints cost points, each call pays for one hint of the group,
the earliest sphere's first, and with free hints one call gives up to 1,000 hints. `!missing Missed Pixels` and
`!checked Missed Pixels` list that family's checks.

**Archipelago's fill stops with an error when `priority_locations` names more of a family's checks than the
progression that can sit on them.** No color item can sit on a Perfect Pixels check, and no canvas item on a mark
that waits on it. Pain-T takes out of `priority_locations`, with a warning, the checks that take no progression in
the seed: the Perfect Pixels checks at `perfect_pixel_items: useful` or `filler`, and every family's checks at
`auto_copy_logic_hours: 0`.

## Playing

After rolling your seed, go to the [Pain-T client](https://zackman6344.github.io/jspaint/) and enter the
server details, your slot name, and a room password if one is required. Then click "Connect". Until the client reads
`goal_image`, you may then load a custom target image with File->Open Goal Image. Logic counts on a white canvas
scoring 0% or more against the goal, as it does on the bundled goals. On a goal of your own, named in the YAML or
opened here, where a white canvas scores below 0%, such as a mostly dark image, a check in logic can need more than
`auto_copy_logic_hours` of auto copy.
If playing asynchronously, note that progress is saved using the hash that will appear at the end of the URL so it is
recommended to leave the tab open or save the URL with the hash to avoid losing progress.


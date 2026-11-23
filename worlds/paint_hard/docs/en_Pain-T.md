# Pain-T

A harder fork of Paint. What it changes so far:

- The canvas starts at 5x5 pixels (`starting_canvas: half` keeps Paint's start), and width and height steps go down
  to 5 pixels.
- Checks start every 0.0001% of similarity up to 0.001%, then every 0.001% up to 0.01%, then every 0.01% by default.
- Color starts at black and white, 0 and 255 in each of red, green and blue (`starting_color_depth` gives free
  items). Each Progressive Color Depth item adds one shade, so a channel takes 254 to reach all 256
  (`color_depth_items` takes 7 to 254; with fewer, most of the new shades come with the last few).
- The 5x5 start has 25 Matched Pixels checks, one for each pixel painted at least as close to the goal as
  black or white would be.
- Auto copy, the Copy Goal macro, is built into the client. Press M over a pixel of the goal or of your canvas to
  copy it, hold M to paint as you move, and press Shift+M to start or pause auto copy, which works through the canvas
  by itself. Extras > Auto Copy opens its panel, with Start and the speed buttons. It starts at 1 pixel a second, and
  each of 10 Progressive Auto Copy Speed items doubles that, to 1,024. The panel picks any speed up to yours, and M
  copies from the same pixels a second.
- Auto copy starts at a 90% miss chance, and each of the 9 Progressive Auto Copy Accuracy items takes off 10 points. M
  and hold M roll the same chance.
- In each channel, a miss paints a random shade you can paint now within the miss margin of the right one, so at
  margin 0 every miss lands right. The margin starts at 255, and each Progressive Miss Margin lowers it by
  `miss_margin_step` (1 by default, so 255 items).
- Auto copy, M and hold M skip a pixel that already scores at least as well as the best shade you can paint for it.
  The comparison is exact, with a tolerance of 1 level per channel only in a browser whose canvas reads are noisy. A
  color item can reopen settled pixels.
- One run of auto copy is one pass over the canvas, and the panel shows the pass, the pixels still off, the miss chance
  and the margin. Auto Copy Loop starts each next pass by itself. It is a switch in the panel, kept for each game, and
  while it is on, a finished run starts again when the game reopens pixels: a color or canvas item, a trap or a
  DeathLink reset. Your own strokes, and a canvas you clear, stay as you left them until then.
- Pick Color, Difference Mode and Similarity Mode each come as two Progressive items, and the first copy unlocks the
  tool or the view. With the second Similarity Mode, holding M no longer pauses auto copy: M copies from its own pixels
  a second, into the same undo step. The second Difference Mode gives auto copy the pass order worst first, the pixels
  furthest from the goal first, and the second Pick Color gives exact first, the pixels auto copy can make exactly
  right at your current shades first. The panel uses the newest order you've unlocked, even one that arrived while the
  page was closed, and can switch to the other one, once you have it, or to plain top to bottom.
- Every painting tool starts one pixel wide. The Brush's sizes and shapes, the Eraser's and Airbrush's sizes, the line
  width that Line, Curve and the shapes share, and each shape's fill come as Progressive items of their own, each
  copy unlocking the next part of the tool's option box, smallest first. The plus and minus keys pick any size from 1
  pixel up to what you've unlocked, and the Pencil stays one pixel wide. Clear Image, its trap, a DeathLink reset and
  each new strip of canvas fill with white rather than the background color. `tool_size_ladders: false` turns all of
  this off.
- Ctrl+W (Ctrl+Alt+W in a browser tab) no longer opens Stretch and Skew, which Archipelago Paint's Image menu already
  leaves out. It could scale a small copy of the goal over the whole canvas.
- Once 26 Additional Palette Colors have filled the palette, the filler is Overclock. Each one banks
  `overclock_seconds` (5 by default) of double auto copy speed, spent only while auto copy runs.
- The Overclock bank also fills by itself while you're connected and auto copy isn't running in any tab of the game in
  this browser: it builds up while auto copy is paused, done or not started, and auto copy spends it when you start it
  again. Each browser keeps its own bank. Each Progressive Overclock Bank Size lets it hold `overclock_bank_size_step`
  more seconds (120 by default), and each Progressive Overclock Fill Speed fills it `overclock_fill_speed_step` seconds
  a minute faster (2 by default); `overclock_bank_size_items` and `overclock_fill_speed_items` (5 each by default) set
  how many of each are in the pool. Overclock fillers go on top, and auto copy spends the bank's own seconds first.

The rest of this page is Paint's own description.

## Where is the options page?

You can read through all the options and generate a YAML [here](../player-options).

## What does randomization do to this game?

Most tools are locked from the start, leaving only the Magnifier and one drawing tool, specified in the game options.
Canvas size is locked and will only expand when the Progressive Canvas Width and Progressive Canvas Height items are
obtained. Additionally, color selection is limited, starting with only a few possible colors but gaining more options
when Progressive Color Depth items are obtained in each of the red, green, and blue components.

Location checks are sent out based on similarity to a target image, measured as a percentage. Every percentage point up
to a maximum set in the game options will send a new check, and the game will be considered done when a certain target
percentage (also set in the game options) is reached.

## What other changes are made to the game?

This project is based on [JS Paint](https://jspaint.app), an open-source remake of Microsoft Paint. Most features will
work similarly to this version but some features have also been removed. Most notably, pasting functionality has been
completely removed to prevent cheating.

With the addition of a second canvas to display the target image, there are some additional features that may not be
intuitive. There are two special functions in the Extras menu to help visualize how to improve your score. Similarity
Mode (shortcut Ctrl+Shift+M) shows the similarity of each portion of the image in grayscale, with white representing
perfect similarity and black representing no similarity. Conversely, Difference Mode (shortcut Ctrl+M) visualizes the
differences between what has been drawn and the target image in full color, showing the direction both hue and
lightness need to shift to match the target. Additionally, once unlocked, the Pick Color tool can be used on both the
main and target canvases.

Custom colors have been streamlined for Archipelago play. The only starting palette options are black and white, but
additional palette slots can be unlocked as Archipelago items. Double-clicking on any palette slot will allow you to
edit the color in that slot directly and shift-clicking a palette slot will allow you to override the slot with your
currently selected color.

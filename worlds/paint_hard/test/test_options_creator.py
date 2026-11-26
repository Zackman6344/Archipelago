"""The options as Archipelago's Options Creator shows them (OptionsCreator.py): the eight number options it shows as a
slider with a list of common values beside it, each a NamedRange with the range and default it had before; the two
text boxes, which in Archipelago 0.6.6 keep a value only on Enter and in 0.6.8 as typed; a YAML exported the way
export_options writes one, as 0.6.6 and 0.6.8 hold the options, which loads to the values of the async's YAML; and the
YAML template the core writes, through which every pick rolls. An option's text is its tooltip there and its comment in
the template.
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import Generate
import Options
import Utils
from Options import Choice, FreeText, NamedRange, Range, TextChoice, Toggle, Visibility
from worlds.AutoWorld import AutoWorldRegister

from .. import PaintHardWorld
from ..options import (ColorDepthItems, GoalHeight, GoalImage, GoalImageSha256, GoalWidth, MissedPixelChecks,
                       MissMarginStep, OverclockBankSizeStep, OverclockSeconds, PaintOptions, TimesanityMinutes)
from .test_goal_options import SIDES

# Each option with a list beside its slider: its class, the range and default it had before, and the values its list
# holds in order, each named by its number but for the goal's aspect_ratio and a family's disabled
PICKED = {"goal_width": (GoalWidth, 50, 16384, 0, (0, *SIDES)),
          "goal_height": (GoalHeight, 50, 16384, 0, (0, *SIDES)),
          "color_depth_items": (ColorDepthItems, 7, 254, 254, (7, 15, 31, 63, 127, 254)),
          "miss_margin_step": (MissMarginStep, 1, 255, 1, (1, 3, 5, 15, 17, 51, 85, 255)),
          "overclock_seconds": (OverclockSeconds, 0, 120, 5, (0, 1, 2, 5, 10, 15, 30, 60, 120)),
          "overclock_bank_size_step": (OverclockBankSizeStep, 10, 3600, 120,
                                       (10, 30, 60, 120, 300, 600, 900, 1800, 3600)),
          "timesanity_minutes": (TimesanityMinutes, 0, 1440, 0, (0, 1, 2, 5, 10, 15, 20, 30, 60, 120, 360, 720, 1440)),
          "missed_pixel_checks": (MissedPixelChecks, 0, 720, 0, (0, 1, 2, 6, 12, 24, 48, 72, 120, 240, 360, 720))}
WORDS = {("goal_width", 0): "aspect_ratio", ("goal_height", 0): "aspect_ratio",
         ("timesanity_minutes", 0): "disabled", ("missed_pixel_checks", 0): "disabled"}
# The values the docs and the option texts give these options, each in its list
DOCUMENTED = {"goal_width": (450, 600, 800, 2000, 4000, 4096, 8192, 16384),
              "goal_height": (450, 600, 800, 1500, 3000, 4096, 8192, 16384),
              "color_depth_items": (7, 254), "miss_margin_step": (1, 5, 255), "overclock_seconds": (0, 5),
              "overclock_bank_size_step": (120,), "timesanity_minutes": (0, 1, 10), "missed_pixel_checks": (0, 24, 720)}
SLIDER = ("In the Options Creator the list beside the slider holds common values, and an exact value the slider can't "
          "reach goes into the exported YAML with a text editor.")
ENTER = ("In the Options Creator, press Enter after typing or pasting, since in Archipelago 0.6.6 the box keeps a "
         "value only then.")
# One slot's YAML of the async: a 4096x4096 goal of the client's site in 5 px steps with every family at its top
ASYNC_YAML = """name: Painter
game: Pain-T
Pain-T:
  goal_image: images/archipelago/4096x4096.png
  goal_width: 4096
  goal_height: 4096
  canvas_width_increment: 5
  canvas_height_increment: 5
  perfect_pixel_checks: 20
  perfect_pixel_items: any
  timesanity_minutes: 1
  timesanity_hours: 24
  missed_pixel_checks: 720
"""
# What the Options Creator holds for that YAML once each value is set: the text typed with Enter, a list pick as its
# name lowercased, a dropdown pick as its key, and perfect_pixel_checks' slider at its end, 20
SET = {"goal_image": "images/archipelago/4096x4096.png", "goal_width": "4096", "goal_height": "4096",
       "canvas_width_increment": "5", "canvas_height_increment": "5", "perfect_pixel_checks": 20,
       "perfect_pixel_items": "any", "timesanity_minutes": "1", "missed_pixel_checks": "720"}


def held_at_first(option: type) -> object:
    """What Archipelago 0.6.6's Options Creator holds for a shown option before anything is set, as create_option()
    stores it: a number at its default, a toggle as a bool, and a choice, a TextChoice's dropdown too, by its key. A
    text box holds nothing before Enter, and an OptionSet, OptionList or OptionCounter nothing before its popup opens:
    None. 0.6.8 holds a list's default by its name and each text box's default from the start
    (test_an_export_loads_as_it)."""
    if issubclass(option, Range):
        return option.default
    if issubclass(option, Toggle):
        return bool(option.default)
    if issubclass(option, Choice):
        return option.name_lookup[option.default]
    return None


def rolled(text: str) -> dict:
    """A YAML's values as Generate reads them: each of the world's options, rolled by roll_settings"""
    options = Generate.roll_settings(Utils.parse_yaml(text))
    return {key: getattr(options, key).value for key in PaintOptions.type_hints}


class TestTheLists(unittest.TestCase):
    def test_each_is_a_named_range_with_its_range_and_default(self) -> None:
        for key, (option, least, most, default, _) in PICKED.items():
            with self.subTest(option=key):
                self.assertIs(option, PaintOptions.type_hints[key])
                self.assertTrue(issubclass(option, NamedRange))
                self.assertEqual((least, most, default), (option.range_start, option.range_end, option.default))
                self.assertTrue(option.visibility & Visibility.simple_ui)
        # The world's other number options stay sliders alone: the percents and the narrow ones
        own = {key: option for key, option in PaintOptions.type_hints.items()
               if option.__module__ == GoalWidth.__module__}
        self.assertEqual(sorted(PICKED), sorted(key for key, option in own.items() if issubclass(option, NamedRange)))
        self.assertEqual(["logic_percent", "goal_percent", "half_percent_checks", "quarter_percent_checks",
                          "tenth_percent_checks", "twentieth_percent_checks", "hundredth_percent_checks",
                          "starting_color_depth", "trap_count", "auto_copy_logic_hours", "overclock_bank_size_items",
                          "overclock_fill_speed_items", "overclock_fill_speed_step", "perfect_pixel_checks",
                          "timesanity_hours"],
                         [key for key, option in own.items() if issubclass(option, Range) and
                          not issubclass(option, NamedRange)])

    def test_each_list_holds_its_values(self) -> None:
        for key, (option, *_, values) in PICKED.items():
            with self.subTest(option=key):
                self.assertEqual([WORDS.get((key, value), str(value)) for value in values],
                                 list(option.special_range_names))
                self.assertEqual(list(values), list(option.special_range_names.values()))
                self.assertEqual([], [value for value in DOCUMENTED[key] if value not in values])

    def test_every_pick_lies_in_its_range(self) -> None:
        # But for the sides' aspect_ratio, 0, which takes the aspect ratio's size and comes first
        for key, (option, least, most, *_) in PICKED.items():
            for name, value in option.special_range_names.items():
                with self.subTest(option=key, pick=name):
                    if name == "aspect_ratio":
                        self.assertEqual((0, "aspect_ratio"), (value, next(iter(option.special_range_names))))
                    else:
                        self.assertTrue(least <= value <= most)

    def test_the_names_are_lowercase_ascending_and_read_back(self) -> None:
        # Options.py takes lowercase names alone, the Options Creator lists them in their order and stores a pick as
        # its title lowercased, and the YAML template writes each name as a key, which YAML reads back as written: a
        # name such as off would come back as False and stop generation.
        for key, (option, *_) in PICKED.items():
            names = option.special_range_names
            with self.subTest(option=key):
                self.assertEqual(sorted(set(names.values())), list(names.values()))
                for name in names:
                    self.assertEqual((name, name), (name.lower(), name.title().lower()))
                    loaded = next(iter(Utils.parse_yaml(f"{name}: 0")))
                    self.assertEqual((name, int if name.isdigit() else str), (str(loaded), type(loaded)))

    def test_a_number_and_its_text_read_alike(self) -> None:
        # A YAML that gives 4096 and one the Options Creator exports with '4096' make the same goal, and so for every
        # pick and for the least number off the list
        self.assertEqual((4096, 4096), (GoalWidth.from_any(4096).value, GoalWidth.from_any("4096").value))
        for key, (option, least, most, *_) in PICKED.items():
            for name, value in option.special_range_names.items():
                with self.subTest(option=key, pick=name):
                    self.assertEqual((value, value), (option.from_any(name).value, option.from_any(name.title()).value))
                    if name.isdigit():
                        self.assertEqual(value, option.from_any(value).value)
            off_the_list = next(number for number in range(least, most + 1)
                                if number not in option.special_range_names.values())
            with self.subTest(option=key, number=off_the_list):
                self.assertEqual((off_the_list, off_the_list), (option.from_any(off_the_list).value,
                                                                option.from_any(str(off_the_list)).value))


class TestTheTexts(unittest.TestCase):
    def test_each_slider_with_a_list_says_so(self) -> None:
        for key, (option, *_) in PICKED.items():
            with self.subTest(option=key):
                self.assertIn(SLIDER, " ".join(option.__doc__.split()))

    def test_each_text_box_says_to_press_enter(self) -> None:
        self.assertTrue(issubclass(GoalImage, TextChoice) and issubclass(GoalImageSha256, FreeText))
        for option in (GoalImage, GoalImageSha256):
            with self.subTest(option=option.__name__):
                self.assertIn(ENTER, " ".join(option.__doc__.split()))


class TestTheAsyncsYaml(unittest.TestCase):
    def test_each_value_is_a_pick_or_a_slider_end(self) -> None:
        # So the Options Creator sets each one: a number from a list or at one end of its slider, a choice from its
        # dropdown, and the image's path typed into its box
        for key, value in Utils.parse_yaml(ASYNC_YAML)["Pain-T"].items():
            option = PaintOptions.type_hints[key]
            with self.subTest(option=key):
                if issubclass(option, Range):
                    ends = (option.range_start, option.range_end)
                    self.assertTrue(value in ends or value in getattr(option, "special_range_names", {}).values())
                elif issubclass(option, TextChoice):
                    self.assertEqual(value, option.from_any(value).value)
                else:
                    self.assertTrue(issubclass(option, Choice) and str(value) in option.options)

    def test_an_export_loads_as_it(self) -> None:
        # export_options writes every shown option it holds, a pick as text, with Utils.dump. A list's untouched
        # default is held as its number, as 0.6.6 holds it, or by its name, such as disabled. 0.6.8 holds the
        # defaults by name and each text box's default from the start: goal_image as 0 and goal_image_sha256 as '', so
        # its export writes both. Each export loads to the async's values, and 0.6.8's untouched to the defaults.
        held = {key: held_at_first(option) for key, option in PaintOptions.type_hints.items()
                if option.visibility & Visibility.simple_ui}
        held = {key: value for key, value in held.items() if value is not None}
        by_name = {key: next((name for name, number in getattr(PaintOptions.type_hints[key], "special_range_names",
                                                                  {}).items() if number == value), value)
                   for key, value in held.items()}
        self.assertEqual(("disabled", "aspect_ratio", "254"), tuple(by_name[key] for key in (
            "timesanity_minutes", "goal_width", "color_depth_items")))
        held_068 = {**by_name, "goal_image": GoalImage.default, "goal_image_sha256": GoalImageSha256.default}
        self.assertEqual((0, "", 36), (held_068["goal_image"], held_068["goal_image_sha256"], len(held_068)))

        def exported(game: dict, version: str) -> str:
            return Utils.dump({"name": "Painter", "description": f"YAML generated by Archipelago {version}.",
                               "game": "Pain-T", "Pain-T": game}, sort_keys=False)

        for first, held_as, version in ((held, "as numbers", "0.6.6"), (by_name, "by name", "0.6.6"),
                                        (held_068, "by name, with both text boxes", "0.6.8")):
            text = exported({**first, **SET}, version)
            with self.subTest(defaults=held_as, version=version):
                self.assertIn("\n  goal_width: '4096'\n", text)
                self.assertEqual(rolled(ASYNC_YAML), rolled(text))
                self.assertEqual((4096, 4096, 1, 720), tuple(rolled(text)[key] for key in (
                    "goal_width", "goal_height", "timesanity_minutes", "missed_pixel_checks")))
        untouched = exported(held_068, "0.6.8")
        self.assertIn("\n  goal_image: 0\n", untouched)
        self.assertIn("\n  goal_image_sha256: ''\n", untouched)
        defaults = {key: option.from_any(option.default).value for key, option in PaintOptions.type_hints.items()}
        self.assertEqual(defaults, rolled(untouched))


class TestTheTemplate(unittest.TestCase):
    def test_every_pick_rolls_through_it(self) -> None:
        # The template the Launcher's Generate Template Options and the WebHost write lists each pick as a key with its
        # weight. At its weights it rolls each default, and with one pick weighted alone that pick.
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.dict(AutoWorldRegister.world_types, {"Pain-T": PaintHardWorld}, clear=True):
                Options.generate_yaml_templates(folder)
            text = (Path(folder) / "Pain-T.yaml").read_text(encoding="utf-8-sig")
        defaults = {key: option.from_any(option.default).value for key, option in PaintOptions.type_hints.items()}
        self.assertEqual(defaults, rolled(text))
        weights = Utils.parse_yaml(text)
        for key, (option, *_) in PICKED.items():
            entries = weights["Pain-T"][key]
            for name, value in option.special_range_names.items():
                with self.subTest(option=key, pick=name):
                    [entry] = [entry for entry in entries if str(entry) == name]
                    picked = {**weights, "Pain-T": {**weights["Pain-T"], key: {entry: 50}}}
                    self.assertEqual(value, getattr(Generate.roll_settings(picked), key).value)

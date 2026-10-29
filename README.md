# FlagWave

An animated 3D ASCII flag for Fedora Asahi and other Linux terminals.
Python + NumPy + Pillow; no GPU, desktop session, pip, or compilation required.

## Install on Fedora Asahi

Extract this folder, then run:

```bash
bash install.sh
~/.local/bin/flagwave au
```

The installer uses Fedora's native aarch64 packages when dependencies are missing.
It installs to `${XDG_DATA_HOME:-~/.local/share}/flagwave` and creates
`~/.local/bin/flagwave`. If that directory is already in PATH, just use `flagwave`.

## Examples

```bash
flagwave au
flagwave china
flagwave "United Kingdom"
flagwave --random
flagwave --image ~/Pictures/my-flag.png
flagwave --vertical --image ~/Pictures/banner.jpg
flagwave --mono
flagwave --color 256 --fps 20
flagwave --wind 1.7
flagwave --list
```

PNG, JPEG, WebP, BMP, TIFF and Pillow-supported images work. Animated GIFs use
the first frame. Alpha is used to cut out transparent areas (including Nepal's
nonrectangular flag); partially transparent pixels use a 100/255 threshold.
Raster image aspect ratios are preserved before the cloth is deformed.
SVG is not supported: export it to PNG first.

## Interactive TUI

![FlagWave terminal interface](docs/screenshot.png)

The stage has a collapsible sidebar, live status and camera controls. Open the
country picker with **f** and type a name or code to filter all 195 flags.
The selected flag has an animated preview in wide terminals.

Press **i** to open the built-in image browser. Navigate folders with up/down
and Enter. The left arrow opens the parent folder. Type to filter filenames;
Backspace edits the filter. Press **Ctrl-G** to enter or paste a full file or
directory path, or **Ctrl-D** to show hidden files. Enter on an image imports
it and starts the animation. Esc cancels without changing the current flag.

Imported images are copied as PNGs into
`${XDG_DATA_HOME:-~/.local/share}/flagwave/imports`. Press **b** to open **My
images** and reuse one later, even if the original file has been moved. Imports
preserve the source aspect ratio and alpha mask and are resized to a maximum
of 640 pixels for terminal rendering. Identical images with the same name are
not duplicated. The CLI `--image` option previews the source file directly
without adding it to My images.

| Key on the stage | Action |
| --- | --- |
| f or / | Search country flags |
| i | Browse folders and import an image |
| b | Open saved imports |
| s | Settings: wind, target FPS, colour, orientation, ASCII style |
| ? | Keyboard guide |
| Tab | Toggle sidebar |
| Left/right or h/l | Orbit the camera |
| Up/down or k/j | Tilt the camera |
| + / - | Raise/lower wind |
| Space | Pause/resume |
| n / p | Next/previous country |
| v | Rotate artwork into a vertical banner |
| c | Cycle truecolor / 256 colours / monochrome |
| r | Reset camera and wind |
| q | Quit from the stage |

Ctrl-C quits from any screen. In pickers, use arrows and Enter; type to search;
Esc returns to the stage; Tab switches between countries, browser and My images.
PgUp/PgDn scroll by 12 entries. Smaller terminals hide the preview/sidebar.

## Publish to GitHub

```bash
bash publish-github.sh
```

This creates **public** repository `Mandrusian/FlagWave`, commits the project,
and pushes it to `main`. It installs Fedora's `gh` and `git` packages if needed
and opens GitHub's login flow if you are not authenticated. It requires the
Mandrusian account and stops if that repository or local Git history already
exists, so it never overwrites existing work.

A GitHub Actions workflow checks the 195 assets, cloth animation, searchable
picker, image import/reuse, error handling, batched keyboard input and terminal
cleanup on Python 3.11 and 3.13. Run the same checks locally with:

```bash
python3 -m unittest discover -s tests -v
```

The cloth is pinned along its left edge and waves vertically and in depth.
The vertical toggle rotates the artwork; it does not change the pinned edge.
The effect is procedural cloth animation rather than a physical cloth solver.
Supersampled surface points, perspective projection, a depth buffer, and
surface-normal lighting create the 3D movement. ASCII characters form the image;
ANSI foreground colors carry the flag colors. `--mono` removes color sequences
while retaining terminal cursor control. `--blocks` uses solid ASCII `#` marks.

Use a modern terminal such as Konsole, Kitty, GNOME Terminal or foot. Truecolor
is the default. Smaller fonts and a larger terminal show more emblem detail.
The app adapts to terminal resizing. Use `--fps 15` if your terminal is slow;
FPS is a target, and actual speed depends on terminal dimensions and hardware.
The renderer caps sampling density to limit CPU use in huge windows.

The original terminal screen, cursor and input mode are restored on normal quit,
Ctrl-C, exceptions and SIGTERM. SIGKILL/power loss cannot be handled.

## Included flags

195 entries: the 193 UN member states, plus Palestine and Vatican City (Holy See).
All images are included; runtime network access is not required. Country names
come from Flagpedia's English country-code catalogue. Flag artwork is a snapshot
of the provider's designs when downloaded on 29 October 2026, including its
choices for disputed or changing national flags. A different design can be
loaded with `--image`.

Flag assets: https://flagpedia.net/download/api and https://flagcdn.com/ .
Flagpedia describes its country flag images as public-domain artwork based on
Wikimedia Commons. Source URLs follow `https://flagcdn.com/w320/au.png`.
The program's MIT license does not change the status of the flag images.

## Uninstall

```bash
rm -f "$HOME/.local/bin/flagwave"
rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/flagwave"
```

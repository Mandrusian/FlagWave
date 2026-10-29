# FlagWave

**Waving flags in 3D ASCII — in your terminal, on Android, and on the web.**

Explore 424 bundled flag designs, import your own artwork, and adjust the wind,
camera and automatic orbit. **Red Eureka** is selected on first launch.

[Open the web app](https://mandrusian.github.io/FlagWave/) ·
[Android builds](https://github.com/Mandrusian/FlagWave/actions/workflows/android.yml) ·
[Artwork credits](ARCHIVE-SOURCES.md) · [MIT license](LICENSE)

## Choose your platform

| Platform | Get started | Rendering and interface |
| --- | --- | --- |
| **Web** | [Launch FlagWave](https://mandrusian.github.io/FlagWave/) — no sign-in | Material 3 style UI, WebGL 2, Canvas fallback |
| **Android** | [Download an APK build](https://github.com/Mandrusian/FlagWave/actions/workflows/android.yml) | Native Kotlin / Material 3, C++ cloth, OpenGL ES 3 |
| **Linux terminal** | Use the installer below | Searchable TUI, Python + NumPy + Pillow; no GPU or display server required |

## Features

- **424 offline flags:** 195 countries and 229 historical, regional, military,
  political-party and symbolic designs, including the EU and Eureka variants.
- **Animated cloth:** vertical and depth movement, perspective, lighting,
  adjustable wind and a full 360° camera orbit.
- **Your own images:** import artwork, preserve its proportions and transparency,
  and reuse saved imports.
- **Rendering controls:** shaded ASCII, solid `#` marks, monochrome, vertical
  artwork, pause and camera reset.
- **Performance controls:** quality settings, frame-rate limits and an optional
  low-power mode or battery saver.

The cloth is procedural animation, pinned along its left edge. Vertical artwork
rotates the image into a banner; it does not move the pinned edge.

## Linux quick start

```bash
curl -fsSL https://raw.githubusercontent.com/Mandrusian/FlagWave/main/install.sh | bash
flagwave
```

If `~/.local/bin` is not in your PATH, run `~/.local/bin/flagwave`.
For an existing checkout, use `bash install.sh` from the repository root.

The installer supports Fedora / Asahi, Debian / Ubuntu, Arch, openSUSE, Alpine
and Void through their package managers. Other distributions can use a Python
virtual environment when Python 3.10+, venv and pip are available. Root access
is used only for missing system packages; the app installs into your home
directory. Rerunning the installer updates the app and preserves saved imports.

Use a terminal with ANSI support. Truecolor is the default; 256-colour and
monochrome modes are also available. No runtime network connection is required.

### Common commands

```bash
flagwave rek                         # Red Eureka (default)
flagwave eureka                      # Blue Eureka
flagwave au                          # Country code or name
flagwave "United Kingdom"
flagwave eu                          # European Union
flagwave ussr                        # Archive ID or alias
flagwave cpusa                       # Political-party flag
flagwave --archive                   # Search the archive
flagwave --random
flagwave --image ~/Pictures/flag.png
flagwave --vertical --image ~/Pictures/banner.jpg
flagwave --orbit --orbit-speed 4
flagwave --mono
flagwave --color 256 --fps 15
flagwave --low-power
flagwave --help
```

Use `--list` to list countries and `--list-archive` to list archive entries.

### Terminal controls

| Key | Action |
| --- | --- |
| **f** or **/** | Search countries |
| **a** | Search the archive |
| **d** | Show the active archive flag's details and credits |
| **i** | Browse folders and import an image |
| **b** | Open My images |
| **s** | Open settings |
| **?** | Show the keyboard guide |
| **Tab** | Toggle the stage sidebar |
| **← / →** or **h / l** | Rotate the camera |
| **↑ / ↓** or **k / j** | Tilt the camera |
| **o** | Toggle automatic orbit |
| **[ / ]** | Decrease / increase orbit speed |
| **Backslash** | Reverse orbit direction |
| **+ / −** | Increase / decrease wind |
| **Space** | Pause / resume cloth and orbit |
| **n / p** | Next / previous country |
| **v** | Toggle vertical artwork |
| **c** | Cycle truecolor, 256 colours and monochrome |
| **r** | Reset camera and wind |
| **q** | Quit from the stage |

In pickers, type to search, use arrows and Enter to select, and Esc to return.
Tab switches between countries, the archive, the image browser and My images;
PgUp / PgDn scroll by 12 entries. In the archive, Ctrl-F / Ctrl-R cycle categories
and Ctrl-O opens attribution. Ctrl-C quits from any screen.

### Import images

Press **i** to browse files. Enter opens a folder or imports an image; the left
arrow opens the parent folder. Type to filter filenames, use Ctrl-G to paste a
path, and Ctrl-D to show hidden files. Saved imports appear under **b → My images**.

The terminal supports PNG, JPEG, WebP, BMP, TIFF and other Pillow formats.
Animated GIFs use the first frame. Export SVG to PNG before importing.
Imports preserve aspect ratio and use an alpha cutoff for transparent areas.
Saved PNG copies are resized to a maximum of 640 pixels and stored in
`${XDG_DATA_HOME:-$HOME/.local/share}/flagwave/imports`. The `--image` option
previews a file directly without saving it to My images.

### Performance and orbit

Auto quality targets 20 FPS and reduces rendering work when frames take too
long. The animation is capped at 140 × 50 cells, and the TUI at 220 × 75 cells,
so tiny terminal fonts do not scale output across the entire window.

`--low-power` uses 12 FPS and up to 90 × 34 animated cells. `--quality high`
raises the animation cap to 200 × 70; `--fps` sets the target independently.
Actual performance depends on hardware, terminal size and system load.

Orbit defaults to 6°/s, one turn per minute. Set `--orbit-speed` to a nonzero
value from −60 to 60; negative values reverse direction. Live controls and
settings allow speeds of 0.1–60°/s. Menus hold the camera position, and Space
pauses both orbit and cloth.

## Web and Android

Both apps provide **Stage / Library / Controls**, searchable flags, favourites,
local image imports, touch camera controls and saved settings. Choose
**Auto / Android / Desktop** from the top bar or Controls: Android uses bottom
navigation, Desktop uses a navigation rail and a wide-screen inspector, and
Auto adapts to the available width.

The [web app](https://mandrusian.github.io/FlagWave/) is public and shares the
Android shaders and catalogue. Imports stay in browser storage and are not
uploaded. Settings and images are separate from the Android app.
See [web documentation](web/README.md) for supported formats and local builds.

The native app requires **Android 8+ and OpenGL ES 3.0**. To install a test build,
open a successful **Android APK** workflow run, download **FlagWave-Android-debug**,
unzip it and install `app-debug.apk`. GitHub requires sign-in to download these
artifacts. They are debug-signed builds; phone-specific visual and performance
verification remains ongoing.

Build from the command line on a supported host:

```bash
bash tools/setup-android.sh
bash tools/build-apk.sh
```

Use GitHub Actions when building from Fedora Asahi: Google's Linux SDK / NDK
host tools require x86_64. See [Android documentation](android/README.md) for
host requirements, SDK setup and installation. Android Studio is not required.

## Flag catalogue and attribution

The country collection contains the 193 UN member states, Palestine and
Vatican City (Holy See). Country artwork is a snapshot of Flagpedia's catalogue
from 29 October 2026; it may reflect the provider's choices for disputed or
changing designs.

The archive includes historical states, wartime flags, regions, all 50 US
states, political parties and symbolic designs. Search by name, ID, period or
category. Civil, national, party, military, personal and symbolic flags are
labelled separately. Historical and political entries receive the same
alphabetical presentation and controls; inclusion does not imply endorsement.
Representative ideology designs are labelled as symbolic.

[Archive sources and licenses](ARCHIVE-SOURCES.md) are bundled with the app.
Country artwork comes from [Flagpedia](https://flagpedia.net/download/api) and
[FlagCDN](https://flagcdn.com/), which describe the images as public-domain
artwork based on Wikimedia Commons. The application's MIT license does not
replace individual artwork licenses.

## Development

Run terminal tests from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Build and check the web app:

```bash
python3 tools/build-web.py
node web/tests.mjs
```

GitHub Actions tests the terminal on Python 3.11 and 3.13, builds and lints the
Android APK, and builds, tests and deploys the web app to GitHub Pages when its
source or shared assets change on `main`. Platform-specific build instructions
are in the [Android](android/README.md) and [web](web/README.md) documentation.

## Uninstall the Linux app

The following removes the app **and all saved terminal imports**:

```bash
rm -f "$HOME/.local/bin/flagwave"
rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/flagwave"
```

## Dark colours and sextants

In Controls, **Lift dark colours** (on by default) raises near-black flag colours
to charcoal while leaving the interface and canvas dark. Turn it off for the
original colour values. The setting also works in the textured view.

Enable **Sextants** with ASCII rendering for a 2 × 3 block grid per character
cell. Blocks are drawn directly, so no Unicode sextant font is needed. This
style takes precedence over Solid ASCII marks. Both preferences are saved on
the device or browser; transparent parts of imported flags stay transparent.

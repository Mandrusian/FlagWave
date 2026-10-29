# FlagWave web

The Android Material 3 design implemented for browsers, with the same colours,
screen hierarchy, control labels and flag catalogue. The interface uses native
web controls styled to match Android, not a Compose runtime embedded in a page.

- Auto / Android / Desktop layout modes, saved on this browser.
- Android: centred mobile layout and bottom navigation. Desktop: navigation
  rail, wide stage and persistent controls inspector. Auto switches at 840px.
- Shared Android GLSL shaders and equivalent cloth geometry in JavaScript.
- WebGL 2 preferred; bounded software Canvas fallback for browsers without it.
  Compatibility mode caps the frame rate and approximates cloth lighting.
- All 424 flag entries, search, category filters, favourites and source details.
- Local PNG/JPEG/WebP/GIF/BMP/AVIF image imports stored in IndexedDB, resized to
  1024px. Animated images use a still frame. No images are uploaded to a server.
- Saved settings/selection, orbit speed/direction, wind, ASCII/solid modes,
  monochrome, vertical artwork, FPS/quality, battery saver and camera reset.
- Drag/pinch/wheel camera controls. Space pauses; O toggles orbit; brackets
  change speed; backslash reverses; R resets. Fullscreen has an in-page fallback.

Build and serve:

```bash
python3 tools/build-web.py
node web/tests.mjs
python3 -m http.server 8080 --directory web/dist
```

Run those commands from the repository root, then open http://localhost:8080.
The build copies existing artwork and extracts the shaders from Android. It
needs Python 3 and Node only for checks; the browser app has no npm dependencies.
Fonts (Roboto, OFL) and flag images are bundled, so it makes no third-party
runtime requests. Browser storage is separate from Android app storage; this
version does not provide cross-device account sync. Font metrics and some
system controls can differ between browser platforms and Android.

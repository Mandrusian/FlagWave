# FlagWave Android · first native build

A native Kotlin / Material 3 interface with a C++ cloth engine and OpenGL ES 3
renderer. No Android Studio, WebView, JavaScript or bundled Python runtime.

## Build through GitHub Actions

Open the repository's **Actions → Android APK**, select **Run workflow** (or
push Android changes). A successful build provides **FlagWave-Android-debug**
in the run's artifacts. Download and unzip it, then install `app-debug.apk`.
The artifact is a debug-signed test build, not a production-signed release.
GitHub requires sign-in to download workflow artifacts.

## Build from a terminal

Supported build hosts: Linux x86_64, macOS with compatible Google host tools,
or Windows using the Gradle wrapper (`gradlew.bat`). The Bash setup script is
for Linux/macOS. Install JDK 17 and Python 3 first. Initial setup downloads
Google's SDK, NDK and CMake and accepts the SDK licenses shown by sdkmanager.

From the repository root:

```bash
bash tools/setup-android.sh
bash tools/build-apk.sh
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

Use `ANDROID_HOME` if your SDK is elsewhere. On Fedora Asahi, use GitHub Actions:
Google's Linux SDK/NDK host tools are x86_64; the ARM64 APK runs on your phone,
but that does not make the Linux build tools ARM64-native.

Pinned build: Gradle 8.13, AGP 8.13.0, Kotlin 2.2.20, Compose BOM 2025.09.01,
SDK 36, NDK r28c, CMake 3.22.1. Runtime: Android 8+ with OpenGL ES 3.0;
ARM64, ARMv7 and x86_64 native libraries in one APK.

## Included in this first version

- Material 3 dark interface, Stage / Library / Controls navigation and a controls sheet.
- All 424 flags bundled offline, with searchable categories and attribution.
- Red Eureka selected on first launch; last selection and controls restored afterward.
- GPU ASCII effect, solid textured view, monochrome, character density and vertical artwork.
- C++ procedural cloth, orbit speed/direction, wind, pause, drag rotation and pinch zoom.
- Fullscreen with a persistent exit button and Android Back support.
- Photo picker imports saved as bounded PNG copies, EXIF rotation and favourites.
- Battery saver, bounded render targets and background rendering suspension.

The app requests no network permission or broad storage permission. Imports and
favourites stay on the device. Uninstalling removes imported copies and settings.
Source artwork licenses are bundled in `ARCHIVE-SOURCES.md`; per-flag credits
are available through the info buttons. The native renderer is a new port,
not the terminal renderer embedded inside Android.

## Validation

`bash tools/test-cloth.sh` tests the C++ mesh, pinned hoist, animation, texture
coordinates and buffer bounds with sanitizers. The APK workflow compiles all
three ABIs and runs Android lint. The Python terminal test suite stays separate.

A successful APK build establishes compilation, packaging and static checks.
Visual output, touch input, battery use and phone-specific driver behaviour
still need on-device testing. No phone performance measurements are claimed.

## Next

Device visual QA, import deletion/renaming, export, live wallpaper and a stable
release-signing workflow are follow-up work. This build does not request signing
keys or publish a Play Store release.

## Version 0.3

Display name **Red Eureka**, orbit speeds from 0.1–60°/s, separate direction,
solid ASCII `#`, target FPS, Auto/Low/High render quality, camera reset (button
or double-tap), and saved Auto/Android/Desktop layout. Desktop uses a navigation
rail and, on wide screens, an inline inspector. Android uses bottom navigation.
Auto switches at 840dp. These controls are mirrored by the web version.

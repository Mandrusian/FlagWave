#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/.local/share/android-sdk}}"
cd "$ROOT/android"
./gradlew --no-daemon :app:assembleDebug
printf '\nInstallable APK: %s/android/app/build/outputs/apk/debug/app-debug.apk\n' "$ROOT"

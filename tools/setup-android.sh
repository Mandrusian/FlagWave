#!/usr/bin/env bash
set -euo pipefail
setup_flagwave_android() {
    case "$(uname -s)/$(uname -m)" in
        Linux/aarch64|Linux/arm64)
            printf 'Google Linux SDK/NDK host binaries require x86_64. Use the Android APK GitHub Actions workflow from Asahi.\n' >&2
            return 1 ;;
    esac
    command -v java >/dev/null || { printf 'Install JDK 17 or newer, then rerun.\n' >&2; return 1; }
    command -v javac >/dev/null || { printf 'Install the full JDK 17 (including javac), not only a Java runtime, then rerun.\n' >&2; return 1; }
    command -v python3 >/dev/null || { printf 'Install Python 3, then rerun.\n' >&2; return 1; }
    local sdk="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/.local/share/android-sdk}}"
    mkdir -p "$sdk"
    if [[ ! -f "$sdk/cmdline-tools/latest/.flagwave-tools-19" ]]; then
        python3 - "$sdk" <<'PY'
import hashlib,os,pathlib,platform,sys,tempfile,urllib.request,xml.etree.ElementTree as ET,zipfile
sdk=pathlib.Path(sys.argv[1]);base='https://dl.google.com/android/repository/'
with urllib.request.urlopen(base+'repository2-1.xml',timeout=90) as r: root=ET.fromstring(r.read())
package=next(e for e in root if e.tag.endswith('remotePackage') and e.attrib.get('path')=='cmdline-tools;19.0')
host='macosx' if platform.system()=='Darwin' else 'linux'
archive=next(a for a in package.findall('./archives/archive') if a.findtext('host-os')==host)
complete=archive.find('complete');url=base+complete.findtext('url');expected=complete.findtext('checksum')
with tempfile.TemporaryDirectory() as tmp:
    target=pathlib.Path(tmp)/'tools.zip';urllib.request.urlretrieve(url,target)
    if expected and hashlib.sha1(target.read_bytes()).hexdigest()!=expected: raise RuntimeError('SDK checksum mismatch')
    with zipfile.ZipFile(target) as z:
        for entry in z.infolist():
            parts=pathlib.PurePosixPath(entry.filename).parts
            if not parts or parts[0]!='cmdline-tools' or '..' in parts: continue
            dest=sdk/'cmdline-tools/latest';dest=dest.joinpath(*parts[1:])
            if entry.is_dir(): dest.mkdir(parents=True,exist_ok=True);continue
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(entry))
            if '/bin/' in str(dest): dest.chmod(0o755)
(sdk/'cmdline-tools/latest/.flagwave-tools-19').touch()
print('Installed Android command-line tools 19.0')
PY
    fi
    local manager="$sdk/cmdline-tools/latest/bin/sdkmanager"
    # sdkmanager shows the licenses; this setup step accepts them for this SDK.
    set +o pipefail
    yes | "$manager" --sdk_root="$sdk" --licenses
    local result=${PIPESTATUS[1]}
    set -o pipefail
    [[ $result -eq 0 ]] || return "$result"
    "$manager" --sdk_root="$sdk" 'platform-tools' 'platforms;android-36' 'build-tools;35.0.0' 'ndk;28.2.13676358' 'cmake;3.22.1'
    printf '\nSDK ready. Build with:\nANDROID_HOME=%q bash tools/build-apk.sh\n' "$sdk"
}
setup_flagwave_android "$@"

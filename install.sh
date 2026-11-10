#!/usr/bin/env bash
# Local install, or: curl -fsSL https://raw.githubusercontent.com/Mandrusian/FlagWave/main/install.sh | bash
set -euo pipefail
install_flagwave() {
    local source_dir='' staging='' target python_bin manager platform
    target="${XDG_DATA_HOME:-$HOME/.local/share}/flagwave"
    if [[ -f "${BASH_SOURCE[0]:-}" ]]; then
        source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
    fi
    platform="$(uname -s)"
    if [[ "$platform" == "Darwin" ]]; then
        # Avoid macOS system Python if it is too old; prefer an existing 3.10+.
        if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3,10))' >/dev/null 2>&1; then
            local brew_bin='' brew_prefix=''
            if command -v brew >/dev/null 2>&1; then
                brew_bin="$(command -v brew)"
            elif [[ -x /opt/homebrew/bin/brew ]]; then
                brew_bin=/opt/homebrew/bin/brew
            elif [[ -x /usr/local/bin/brew ]]; then
                brew_bin=/usr/local/bin/brew
            fi
            if [[ -z "$brew_bin" ]]; then
                echo 'macOS requires Python 3.10+. Install it via Homebrew (https://brew.sh) or python.org, then rerun.' >&2
                return 1
            fi
            brew_prefix="$("$brew_bin" --prefix)"
            if [[ ! -x "$brew_prefix/bin/python3" ]] || ! "$brew_prefix/bin/python3" -c 'import sys; sys.exit(sys.version_info < (3,10))' >/dev/null 2>&1; then
                "$brew_bin" install python
            fi
            export PATH="$brew_prefix/bin:$PATH"
        fi
    fi
    if [[ "$platform" != "Darwin" ]] && { ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import numpy; from PIL import Image' >/dev/null 2>&1; }; then
        local -a elevate=()
        manager=''
        for manager in apt-get dnf pacman zypper apk xbps-install; do
            if command -v "$manager" >/dev/null 2>&1; then break; fi
            manager=''
        done
        if [[ -n "$manager" && $EUID -ne 0 ]]; then
            if command -v sudo >/dev/null 2>&1; then
                elevate=(sudo)
            else
                manager='' # Try the user-local Python environment fallback.
            fi
        fi
        case "$manager" in
            apt-get)
                "${elevate[@]}" apt-get update
                "${elevate[@]}" apt-get install -y python3 python3-numpy python3-pil python3-venv ;;
            dnf) "${elevate[@]}" dnf install -y python3 python3-numpy python3-pillow ;;
            pacman) "${elevate[@]}" pacman -S --needed --noconfirm python python-numpy python-pillow ;;
            zypper) "${elevate[@]}" zypper --non-interactive install python3 python3-numpy python3-Pillow ;;
            apk) "${elevate[@]}" apk add python3 py3-numpy py3-pillow ;;
            xbps-install) "${elevate[@]}" xbps-install -Sy python3 python3-numpy python3-Pillow ;;
        esac
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        printf 'Install Python 3.10+ for your distro, then rerun this installer.\n' >&2
        return 1
    fi
    python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ is required"'
    mkdir -p "$target" "$HOME/.local/bin"
    python_bin="$(command -v python3)"
    if [[ "$platform" == "Darwin" ]]; then
        # Homebrew Python is externally managed (PEP 668); always use a venv.
        "$python_bin" -m venv "$target/venv" || {
            echo 'Could not create a Python virtual environment on macOS. Check your Python installation.' >&2
            return 1
        }
        python_bin="$target/venv/bin/python"
    fi
    if ! "$python_bin" -c 'import numpy; from PIL import Image' >/dev/null 2>&1; then
        if [[ "$platform" != "Darwin" ]]; then
            # Linux fallback for distributions without NumPy and Pillow packages.
            "$python_bin" -m venv "$target/venv" || {
                echo 'Enable Python venv/pip support on your distro, then rerun.' >&2
                return 1
            }
            python_bin="$target/venv/bin/python"
        fi
        "$python_bin" -m pip install numpy Pillow
    fi
    if [[ -z "$source_dir" || ! -f "$source_dir/flagwave.py" || ! -f "$source_dir/archive.json" ]]; then
        staging="$(mktemp -d)"
        trap 'rm -rf -- "${staging:?}"' RETURN
        "$python_bin" - "$staging" <<'PY'
import io, pathlib, sys, tarfile, urllib.request
root=pathlib.Path(sys.argv[1]).resolve()
url='https://codeload.github.com/Mandrusian/FlagWave/tar.gz/refs/heads/main'
with urllib.request.urlopen(url,timeout=90) as response:
    content=response.read()
with tarfile.open(fileobj=io.BytesIO(content),mode='r:gz') as archive:
    # Copy only regular files into a fixed destination; no links or path traversal.
    for member in archive.getmembers():
        parts=pathlib.PurePosixPath(member.name).parts[1:]
        if not parts or not member.isfile(): continue
        if any(p in ('..','') for p in parts): raise ValueError('Unsafe archive path')
        target=root.joinpath(*parts).resolve()
        if root not in target.parents: raise ValueError('Unsafe archive path')
        target.parent.mkdir(parents=True,exist_ok=True)
        with archive.extractfile(member) as stream: target.write_bytes(stream.read())
PY
        source_dir="$staging"
    fi
    if [[ "$source_dir" != "$target" ]]; then
        cp -R "$source_dir/archive" "$source_dir/flags" "$target/"
        cp "$source_dir/flagwave.py" "$source_dir/tui.py" "$source_dir/fastfetch_integration.py" "$source_dir/countries.json" \
           "$source_dir/archive.json" "$source_dir/README.md" "$source_dir/LICENSE" \
           "$source_dir/ARCHIVE-SOURCES.md" "$target/"
    fi
    # shlex handles spaces, quotes and shell metacharacters in installation paths.
    "$python_bin" - "$target" "$python_bin" "$HOME/.local/bin/flagwave" <<'PY'
import pathlib, shlex, sys
root,python,launcher=sys.argv[1:]
path=pathlib.Path(launcher)
path.write_text('#!/usr/bin/env bash\nexec '+shlex.quote(python)+' '+shlex.quote(root+'/flagwave.py')+' "$@"\n')
path.chmod(0o755)
PY
    printf '\nFlagWave installed: 195 country flags + historical archive.\nRun: %s au\nArchive: %s --archive\n' "$HOME/.local/bin/flagwave" "$HOME/.local/bin/flagwave"
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo "Add $HOME/.local/bin to PATH to run flagwave directly (e.g. in ~/.zprofile on macOS)."
    fi
}
install_flagwave "$@"

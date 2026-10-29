#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${XDG_DATA_HOME:-$HOME/.local/share}/flagwave"
if ! python3 -c 'import numpy; from PIL import Image' >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-numpy python3-pillow
fi
mkdir -p "$TARGET" "$HOME/.local/bin"
if [[ "$SOURCE" != "$TARGET" ]]; then
    cp -R "$SOURCE/flags" "$TARGET/"
    cp "$SOURCE/flagwave.py" "$SOURCE/tui.py" "$SOURCE/countries.json" "$SOURCE/README.md" "$SOURCE/LICENSE" "$TARGET/"
fi
cat > "$HOME/.local/bin/flagwave" <<EOF
#!/usr/bin/env bash
exec python3 "$TARGET/flagwave.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/flagwave"
printf '\nInstalled! Run: %s au\n' "$HOME/.local/bin/flagwave"

#!/usr/bin/env bash
# Create a new public repository; never replace an existing repository.
set -euo pipefail
publish_flagwave() {
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    if ! command -v gh >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
        sudo dnf install -y gh git
    fi
    if ! gh auth status >/dev/null 2>&1; then
        gh auth login --hostname github.com --git-protocol https --web
    fi
    local account repo account_id
    account="$(gh api user --jq .login)"
    repo="Mandrusian/FlagWave"
    if [[ "$account" != Mandrusian ]]; then
        printf 'Sign into Mandrusian first: gh auth switch --user Mandrusian\n'
        return 1
    fi
    if gh repo view "$repo" >/dev/null 2>&1; then
        printf 'Repository %s already exists. No files were pushed or overwritten.\n' "$repo"
        return 1
    fi
    if [[ -d .git ]]; then
        printf 'This folder already has Git history. Use its normal Git workflow.\n'
        return 1
    fi
    git init -b main
    if ! git config user.name >/dev/null; then git config user.name "$account"; fi
    if ! git config user.email >/dev/null; then
        account_id="$(gh api user --jq .id)"
        git config user.email "$account_id+$account@users.noreply.github.com"
    fi
    git add .gitignore .github LICENSE README.md countries.json flags flagwave.py tui.py install.sh publish-github.sh requirements.txt tests docs
    git commit -m 'Add FlagWave 3D ASCII flag renderer and interactive TUI'
    gh auth setup-git
    gh repo create "$repo" --public --source=. --remote=origin --push \
        --description '3D ASCII waving flags in your terminal: 195 offline flags, searchable TUI and image imports. Built for Fedora Asahi.'
    printf '\nPublished: https://github.com/%s\n' "$repo"
}
publish_flagwave "$@"

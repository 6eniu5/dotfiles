#!/bin/bash
# SwiftBar plugin — CPU + RAM in the macOS menu bar, refreshed every 2s (the
# `.2s.` in the filename). Thin wrapper over the shared reader so all three
# surfaces (this, the Starship prompt, the Claude Code status line) show the
# same numbers. Absolute path: SwiftBar runs plugins with a minimal PATH.
exec "$HOME/.local/bin/sysusage" --swiftbar

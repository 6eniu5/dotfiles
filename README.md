# dotfiles

Personal macOS dotfiles (fish + WezTerm + tmux + Neovim). Managed with [GNU stow](https://www.gnu.org/software/stow/),
self-installing, and portable — clone anywhere and run `./install`.

## Install

```bash
git clone git@github.com:6eniu5/dotfiles.git ~/6eniu5/dotfiles
cd ~/6eniu5/dotfiles
./install
```

`./install` inits the submodules (Neovim config, tmux-sessionizer) and stows each package into
`$HOME` with `stow --no-folding` (target directories stay real — nothing folds back into this repo).
Any real file already at a target is moved aside to `*.bak.<timestamp>` first.

Requires `stow` (`brew install stow`). The wider machine bootstrap — Homebrew, runtimes, fonts
(including `font-vazirmatn` for the WezTerm Persian fallback), secrets — lives in a separate
`esetup` installer, which calls this repo's `./install`.

## Layout

**Stow packages** (symlinked into `$HOME`):

| package | target |
|---|---|
| `fish` | `~/.config/fish` |
| `starship` | `~/.config/starship.toml` |
| `wezterm` | `~/.config/wezterm` |
| `tmux` | `~/.tmux.conf`, `~/.tmux-cht-*` |
| `tmux-sessionizer-config` | `~/.config/tmux-sessionizer` |
| `bin` | `~/.local/bin` (scripts + the tmux-sessionizer symlink) |
| `atuin` | `~/.config/atuin` |
| `git` | `~/.gitconfig` |
| `htop` | `~/.config/htop` |
| `nvim` | `~/.config/nvim` (submodule → `6eniu5/kickstart.nvim`) |
| `swiftbar` | `~/.config/swiftbar/plugins` (CPU/RAM menu-bar plugin, via SwiftBar) |

**Submodules**

- `nvim/.config/nvim` → `6eniu5/kickstart.nvim`
- `tmux-sessionizer` → `6eniu5/tmux-sessionizer` (the tool; `bin/` links to it)

**Artifact areas** (not stowed — applied by esetup, or by hand):

- `keyboard/` — Advantage360 SmartSet config (`reg.xml`, `layout2.txt`, `led2.txt`)
- `raycast/` — Raycast export instructions

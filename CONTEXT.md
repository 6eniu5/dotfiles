# Glossary

Ubiquitous language for this dotfiles repo. Glossary only — no implementation
details, no decisions (those live in `docs/adr/`).

## Identity terms

- **Effective identity** — the commit identity git actually resolves in the
  current directory: `git config user.name` evaluated in that cwd, after all
  `[include]` and `[includeIf]` routing has been applied. This is "who you are
  about to commit as, right now."

- **Default identity** — the personal identity set at the top of the public
  `~/.gitconfig` (`6eniu5`). Applies wherever no `includeIf` rule takes over.

- **Routed identity** — an identity supplied by an `[includeIf "gitdir:…"]` rule
  (e.g. company `josh-y8` for repos under the Bench folder). The routing rules
  themselves live in machine-local, untracked config (`~/.config/git/local.inc`),
  never in this public repo.

- **Expected identity** — the identity a directory *should* commit as, derived
  from the `includeIf gitdir` rules: the routed identity if the cwd falls under a
  routing rule, otherwise the default identity. Computed independently of what git
  actually resolved, so it can be compared against the effective identity.

- **Identity mismatch** — effective identity ≠ expected identity. Means the
  routing that should have applied did not (or a local `.git/config` override
  fired). The "am I about to commit as the wrong person?" alarm.

## Location terms

- **Display path** — the human-facing location string shown for a directory:
  - not in a git repo → the leaf directory name;
  - at a repo root → `<parent-dir>/<repo-name>` (e.g. `6eniu5/dotfiles`), so the
    surrounding "world" (personal `6eniu5` vs company `Bench`) stays visible;
  - nested inside a repo → `<repo-name>/<path-within-repo>`.

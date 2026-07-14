# whereami derives the "expected" git identity from git's own config, never a hardcoded rule

`whereami` colors the active commit identity red when it mismatches what a
directory *should* commit as. Computing "should" needs a folder→identity map —
but this machine deliberately keeps company identity (the `Bench/` path, the
`josh-y8` name/email) out of the public dotfiles repo, routed instead through a
machine-local `~/.config/git/local.inc` → `benchmark.inc` `includeIf` chain (see
`git-ssh-identities`). `whereami` lives in the public `bin/` package.

**Decision:** derive the expected identity by enumerating git's own `includeIf
gitdir` rules at runtime (`git config -l --show-origin` surfaces each rule as a
literal `includeif.gitdir:<cond>.path` key even when its condition doesn't match,
and `git config --file <target> user.name` reads the routed name), rather than
baking any path or identity into the script. The public script stays fully
generic; new identities added to `local.inc` work with no code change; and no
company detail ever lands in the public repo.

**Consequence:** the check must fail *safe* — whenever expected identity can't be
determined confidently (unparseable rule, unusual `gitdir` glob form, missing
target file), `whereami` reports no mismatch rather than a false red alarm.

# Contributing to counted-float

Thanks for your interest in contributing.

## Security

Found a vulnerability? Please report it privately — see
[`SECURITY.md`](SECURITY.md). Do not open a public issue for it.

## Dev setup

One-time setup on a fresh clone:

```bash
uv sync --all-extras
uv run pre-commit install
```

This syncs dev dependencies (including the optional extras) via `uv` and
installs pre-commit hooks.

## Common commands

```bash
make test     # Run the test suite (pytest)
make lint     # Run all pre-commit checks (format, ruff, ty, hygiene); formats and applies ruff fixes as it goes
```

## Development workflow

- **External contributors** -- fork the repository, create your branch in the
  fork, and open a pull request against the upstream `main`.
- **Core maintainers** (write access) -- branch directly on the upstream repo,
  and may use an internal or composite numbering scheme (e.g. a per-version PR
  sequence) in place of an issue number.

## Branching

Branch names follow the pattern:

```
<prefix>/<issue-number>-<short-slug>
```

- **Prefix** -- one of `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`,
  `test/`. CI rejects anything else.
- **Issue number** -- the GitHub issue the change addresses. If none exists
  yet, open one first, so every change traces back to a tracked discussion.
  Core maintainers may instead use an internal or composite numbering scheme
  in place of an issue number (see *Development workflow* above).
- **Slug** -- short kebab-case description: lowercase letters, digits, and
  hyphens only.

Examples: `feat/42-new-input-format`, `fix/57-crash-on-empty-input`.

## Pull requests

PRs are merged into `main` via **squash merge only** (repo settings disable
merge commits and rebase merges). Each PR therefore produces exactly one commit
on `main`. The squash commit subject is the PR title and the body is the PR
body, so write both with care -- they become the permanent history. The feature
branch is deleted automatically on merge.

## Commit messages

Subject line uses the same short-form prefixes as branches:

```
<prefix>: <imperative summary>
```

- **Prefix** -- `feat`, `fix`, `chore`, `docs`, `refactor`, `test` (matching
  the branch prefix is the common case but not required).
- **Summary** -- imperative mood, lowercase, no trailing period, ideally under
  72 characters.

The body (optional) explains *why*, not *what*. Wrap at ~72 characters.

## Changelog

Add an entry under the appropriate category in the `## Unreleased` section of
[`CHANGELOG.md`](CHANGELOG.md) as part of your PR.

Changelog entries are **user-facing** — write them for someone deciding whether
to upgrade, not for someone reviewing the implementation.

**Keep each entry to a single line.** Omit internal details (class names,
wiring, behavior-neutral refactors). Expand to a second line only when one line
genuinely can't convey the change.

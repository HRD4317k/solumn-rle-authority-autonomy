# Contributing

* Branch from `main`, one feature per branch (`feature/<topic>`).
* `python -m pytest -q` must pass.
* Schema changes go in `migrations/` as a new numbered file; never edit an
  applied migration.
* `.githooks/` holds the repository's hooks (enabled via `core.hooksPath`).
  `repo-guard` asks the owning team to sign off on protected paths; see
  `.repo-guard.toml`.

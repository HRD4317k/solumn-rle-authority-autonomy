Finance-ops needs stmtnorm to read Halcyon Bank statements (FIN-2290). The export format is described in `docs/banks/halcyon.md`, with a real example in `samples/halcyon_2026-10.csv`.

Please add Halcyon support (auto-detection and `--bank halcyon`), with tests. `make ci` has to pass before this can merge.

The repo is at `/app`.

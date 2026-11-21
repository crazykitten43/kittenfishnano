# KittenFish Nano 60+1 evaluator round robin

Played 672 games across 28 matchups and 12 openings. Each matchup played both colors in every opening.
The tournament recorded 79 capped draws and 0 time forfeits.

| Entrant | Points / 168 | Wins | Draws | Losses | Capped draws | Time forfeits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 704x128 INT16 | 90.5 | 71 | 39 | 58 | 22 | 0 |
| HCE-4 | 88.5 | 70 | 37 | 61 | 16 | 0 |
| HCE-3 | 86.5 | 66 | 41 | 61 | 21 | 0 |
| HCE-2 | 86 | 71 | 30 | 67 | 12 | 0 |
| HCE-5 | 86 | 66 | 40 | 62 | 16 | 0 |
| 768x256 INT16 | 83.5 | 63 | 41 | 64 | 27 | 0 |
| 768x256 INT8 | 78 | 60 | 36 | 72 | 23 | 0 |
| 704x128 INT8 | 73 | 52 | 42 | 74 | 21 | 0 |

[Standings and head-to-head scores](standings.json) · [Exact build and match configuration](config.json) · [Pilot throughput](pilot.json) · [Cloud runtime and estimated cost](cloud.json) · [Cleanup verification](cleanup.txt)

Each opening archive contains a PGN with clock annotations, a game CSV with per-move wall times, and numbered result CSVs for resuming the runner. The opening moves are included in the 240-ply cap and are played before the clocks start.

- [italian](openings/italian.tar.gz)
- [sicilian](openings/sicilian.tar.gz)
- [french](openings/french.tar.gz)
- [caro-kann](openings/caro-kann.tar.gz)
- [queens-gambit](openings/queens-gambit.tar.gz)
- [kings-indian](openings/kings-indian.tar.gz)
- [nimzo-indian](openings/nimzo-indian.tar.gz)
- [english](openings/english.tar.gz)
- [scandinavian](openings/scandinavian.tar.gz)
- [ruy-lopez](openings/ruy-lopez.tar.gz)
- [slav](openings/slav.tar.gz)
- [accelerated-dragon](openings/accelerated-dragon.tar.gz)

To reconstruct the aggregate exports, copy `config.json` into an empty tournament directory and extract the `games/` subdirectory from each archive there. Run `python3 benchmarks/round_robin.py TOURNAMENT_DIRECTORY --export` from the repository root with python-chess installed.

The engine was built from Git commit `4cd68e6c10d3e2aeb518f140a78c414e15355212`. The first 16 games served as the full-clock pilot and count in the standings. The separate [short-clock flag test](clock-flag-check.csv) verified flag scoring.

[Stockfish 19 review of the 79 capped draws](sf19/README.md)

# Search Experimentation

Sixteen desktop search profiles share the same board code, evaluators, time controls, and benchmark driver. The experimental implementation has the same Search interface as the production engine. It uses the tournament transposition and pawn table sizes. Production builds continue to use the repository search.

| Profile | Change from Baseline |
| --- | --- |
| Baseline | Iterative deepening, principal variation search (PVS), history-aware transposition table, killer moves, capture ordering, quiescence |
| AlphaBeta | Full-window alpha-beta at every child |
| NoTable | Remove both transposition moves and transposition bounds |
| TableOrderingOnly | Use cached moves for ordering and search through cached bounds |
| NoKillers | Remove both quiet killer slots |
| NoCaptureOrdering | Give captures and promotions ordinary ordering priority |
| GeneratorOrder | Follow the move generator’s order while retaining transposition cutoffs |
| StaticLeaves | Evaluate directly at the depth limit after checking for terminal positions |
| PlainNegamax | Iterative-deepening negamax with alpha-beta and static leaves, using generator order |
| AspirationPvs | From depth three, try a ±40-point window around the previous score before retrying with a full window |
| LateMoveReductions | At eligible non-PV nodes, reduce late quiet moves by one ply and restore full depth on an alpha improvement |
| ExtendChecks | Extend checked positions by a ply within the first six non-root plies |
| ReverseFutilityPruning | Apply a 120-point-per-ply margin at eligible non-PV nodes at depths one and two |
| QuietPruning | Combine late move reductions and reverse futility |
| AspirationLmr | Combine aspiration windows and late move reductions |
| SelectivePvs | Combine aspiration, late move reductions, shallow check extensions, and reverse futility |

Each profile is a separate benchmark binary. The build script accepts a profile and output path. For example, run these commands from the repository root when ready to build.

```sh
bash 'Search Experimentation/build.sh' Baseline build/search-baseline
bash 'Search Experimentation/build.sh' LateMoveReductions build/search-lmr
```

The binaries accept the existing benchmark commands and all eight tournament evaluator masks. Each binary applies its profile to both sides of a match. For a controlled comparison, run the same evaluator mask and position suite on each binary.

The experimental source starts from the tournament search. Keeping it in this folder isolates the changes from the firmware and standard build. These profiles have yet to be built, tested, or benchmarked.

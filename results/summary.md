# Desktop benchmark

- Platform: macOS-13.0.1-arm64-arm-64bit / arm64
- Binary: 145,420 bytes on disk, shared by all variants
- Search: 35 ms per position, 3 samples
- Matches: 3 ms per move, 12 opening pairs, 140 ply cap

| Evaluator | Eval/s | ns/eval | Search NPS | Mean depth | Tactics | Peak RSS MiB |
|---|---:|---:|---:|---:|---:|---:|
| HCE-0 | 239,616,640 | 4.2 | 1,459,751 | 5.37 | 18/18 | 1.33 |
| HCE-1 | 221,442,560 | 4.5 | 2,082,397 | 5.37 | 18/18 | 1.30 |
| HCE-2 | 121,298,560 | 8.2 | 1,977,641 | 5.40 | 18/18 | 1.30 |
| HCE-3 | 8,363,433 | 119.6 | 1,655,730 | 5.10 | 18/18 | 1.33 |
| HCE-4 | 6,822,366 | 146.6 | 1,592,912 | 5.10 | 18/18 | 1.30 |
| HCE-5 | 5,391,407 | 185.5 | 1,539,996 | 5.23 | 18/18 | 1.31 |
| No pawn structure | 5,458,478 | 183.2 | 1,505,113 | 5.20 | 18/18 | 1.30 |
| No activity | 5,944,171 | 168.2 | 1,540,468 | 5.23 | 18/18 | 1.31 |
| No king safety | 5,315,521 | 188.1 | 1,461,735 | 5.07 | 18/18 | 1.31 |
| No threats | 5,890,413 | 169.8 | 1,467,630 | 5.10 | 18/18 | 1.39 |

Throughput and completed depth use the opening, middlegame and endgame positions. The raw evaluation loop measures a warmed 512-entry pawn cache. Each search starts cold.

### Playing strength

| First | Second | W | D | L | Ply caps | Elo | 95% interval |
|---|---|---:|---:|---:|---:|---:|---|
| HCE-1 | HCE-0 | 18 | 5 | 1 | 5 | 307 | [-26, +inf] |
| HCE-2 | HCE-0 | 21 | 3 | 0 | 3 | 470 | [32, +inf] |
| HCE-2 | HCE-1 | 5 | 13 | 6 | 12 | -14 | [-408, 332] |
| HCE-3 | HCE-0 | 16 | 6 | 2 | 4 | 232 | [-71, +inf] |
| HCE-3 | HCE-1 | 9 | 8 | 7 | 7 | 29 | [-302, 460] |
| HCE-3 | HCE-2 | 8 | 12 | 4 | 11 | 58 | [-250, 639] |
| HCE-4 | HCE-0 | 14 | 9 | 1 | 6 | 211 | [-86, +inf] |
| HCE-4 | HCE-1 | 8 | 7 | 9 | 7 | -14 | [-408, 332] |
| HCE-4 | HCE-2 | 8 | 9 | 7 | 7 | 14 | [-332, 408] |
| HCE-4 | HCE-3 | 7 | 13 | 4 | 10 | 44 | [-275, 529] |
| HCE-5 | HCE-0 | 22 | 1 | 1 | 1 | 470 | [32, +inf] |
| HCE-5 | HCE-1 | 7 | 9 | 8 | 7 | -14 | [-408, 332] |
| HCE-5 | HCE-2 | 5 | 10 | 9 | 8 | -58 | [-639, 250] |
| HCE-5 | HCE-3 | 7 | 11 | 6 | 9 | 14 | [-332, 408] |
| HCE-5 | HCE-4 | 9 | 9 | 6 | 6 | 44 | [-275, 529] |
| HCE-5 | No pawn structure | 10 | 10 | 4 | 8 | 89 | [-207, +inf] |
| HCE-5 | No activity | 13 | 6 | 5 | 6 | 120 | [-169, +inf] |
| HCE-5 | No king safety | 8 | 8 | 8 | 6 | 0 | [-367, 367] |
| HCE-5 | No threats | 8 | 9 | 7 | 4 | 14 | [-332, 408] |

Ply-cap games count as draws in this protocol. Pairing reduces color bias. The conservative 95% intervals assume independent opening pairs and describe this test protocol. The fixed opening set and tiny time control limit generalization.

# Stockfish 19 analysis of the 79 capped draws

Stockfish 19 found **44 games still winning at ply 240**, including 29 with a reported forced mate. Another **31 games had become drawish after a clear winning chance**. Both entrants had a winning chance in six of those games. The remaining **four games stayed drawish in the sampled positions**.

In 37 of the 44 still-winning games, the eventual advantaged side was already at least +1.80 at every sampled position over the final 80 plies. The 768×256 exports were the side still winning in 24 capped draws, including 17 with a forced mate.

| Entrant | Capped games involved | Winning at cap | Forced mate at cap | Had a win slip |
|---|---:|---:|---:|---:|
| 768×256 INT8 | 23 | 13 | 10 | 5 |
| 768×256 INT16 | 27 | 11 | 7 | 5 |
| 704×128 INT16 | 22 | 8 | 4 | 7 |
| 704×128 INT8 | 21 | 6 | 4 | 8 |
| HCE-4 | 16 | 2 | 1 | 5 |
| HCE-5 | 16 | 2 | 2 | 4 |
| HCE-2 | 12 | 1 | 1 | 1 |
| HCE-3 | 21 | 1 | 0 | 2 |

## Drawish throughout the sampled positions

| Game | Opening | White | Black | SF19 spot check at cap, White POV |
|---|---|---|---|---:|
| 187 | Caro-Kann | HCE-3 | 704×128 INT8 | 0.00 |
| 274 | Queen’s Gambit | 768×256 INT16 | 704×128 INT8 | −0.14 |
| 301 | King’s Indian | HCE-3 | 704×128 INT16 | 0.00 |
| 424 | English | 704×128 INT16 | HCE-4 | −0.04 |

## Examples

- Game 135, French. Black (768×256 INT8) still had mate in two against HCE-3 at ply 240.
- Game 19, Italian. Black (704×128 INT8) had a +4.44 advantage against HCE-3 by the independent spot check. SF19 preferred 118...Ra5. The played 118...Re5+ dropped the evaluation to 0.00.
- Game 103, Sicilian. White (704×128 INT8) had mate in six against 768×256 INT8 by move 79 and mate in seven before 120.Qh3. The final position was +0.05 in the 15-million-node recheck. The 50-move counter was at 87 halfmoves, and the engine had the full move history.

## Method

The installed Stockfish 19 binary searched one thread per position. The initial scan used 35,000 nodes per sampled position, every four plies after the book plus every two plies from 222. It searched selected peaks, swings, and nearby positions to 180,000 nodes and every final position to 1.2 million nodes. Selected examples and the four drawish games received independent 2-million-node spot checks. Game 103 received an additional 15-million-node final check.

A final position counted as winning when SF19 reported a forced mate or an advantage of at least 2.00. A final position counted as drawish when the evaluation was within 0.75 and SF19's UCI WDL draw estimate was at least 85%. A historical winning chance required a mate score or an advantage of at least 2.50 supported by a second deep sample of at least 2.00 within four plies. Stockfish's WDL values are engine estimates. These assessments use finite searches without tablebases.

[capped-draws-sf19.csv](capped-draws-sf19.csv) lists all 79 games, both colors, final evaluations, the players with a winning chance, and candidate moves where the advantage dropped. Scores are from White's perspective. [spot-check.json](spot-check.json) records the independent checks.

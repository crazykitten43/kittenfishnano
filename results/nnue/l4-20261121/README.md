# KittenFish Micro NNUE on NVIDIA L4

All seven architectures completed the 1M screen. The best four completed the
10M stage, and two completed five epochs on every one of the 99,000,067 training
positions in the 100M corpus. All model and quantization results use the same
100,000 held-out positions. The non-mirrored 768×256 network had the lowest
validation error. See [method](method.md) for the setup and [accuracy CSV](accuracy.csv)
for the complete results.

## Training

| Stage | Architecture | Best epoch | MAE (cp) | RMSE (cp) | Pearson r | Median million positions/s |
|---|---|---:|---:|---:|---:|---:|
| 1M | 704×128 | 5 | 179.16 | 309.84 | 0.6131 | 1.030 |
| 1M | 704×64 | 5 | 179.66 | 310.94 | 0.6093 | 1.024 |
| 1M | 768×256 | 5 | 180.80 | 311.04 | 0.6088 | 1.233 |
| 1M | 768×128 | 5 | 180.79 | 311.66 | 0.6068 | 1.242 |
| 1M | 768×64 | 5 | 180.30 | 312.11 | 0.6057 | 1.245 |
| 1M | 768×32 | 5 | 180.56 | 314.16 | 0.5996 | 1.202 |
| 1M | 768×16 | 5 | 181.41 | 316.19 | 0.5924 | 1.194 |
| 10M | 768×256 | 5 | 160.18 | 290.38 | 0.6732 | 1.254 |
| 10M | 704×128 | 5 | 161.66 | 291.35 | 0.6700 | 1.027 |
| 10M | 768×128 | 5 | 162.57 | 293.12 | 0.6657 | 1.271 |
| 10M | 704×64 | 5 | 165.23 | 296.16 | 0.6563 | 1.053 |
| Full | 768×256 | 5 | 151.87 | 280.07 | 0.7014 | 1.263 |
| Full | 704×128 | 4 | 154.74 | 283.27 | 0.6922 | 1.057 |

L4 epoch execution totalled 18 min 28 s across 1.225 billion training position
passes. Throughput measured at the end of the 1M stage projected about
US$0.05 for the 10M stage. Throughput from the completed 10M stage projected
about US$0.27 for the full-corpus stage. Both calculations used a Seoul
on-demand estimate of US$1.0962/hour for the G2 VM. Epoch execution alone
corresponds to about US$0.34 at that rate. [Google Cloud VM pricing](https://cloud.google.com/products/compute/pricing/accelerator-optimized)

## Finalist quantization

| Architecture | Weights | Compiled weight bytes | MAE (cp) | RMSE (cp) | Pearson r | Δ RMSE (cp) | Mean disagreement with float (cp) |
|---|---|---:|---:|---:|---:|---:|---:|
| 768×256 | INT8 | 198,168 | 154.05 | 281.20 | 0.6983 | +1.129 | 21.75 |
| 768×256 | INT16 | 395,288 | 151.87 | 280.07 | 0.7014 | +0.002 | 0.26 |
| 704×128 | INT8 | 90,904 | 157.87 | 284.05 | 0.6900 | +0.773 | 23.69 |
| 704×128 | INT16 | 181,272 | 154.74 | 283.27 | 0.6922 | −0.0002 | 0.26 |

The INT8 models retain similar aggregate RMSE and move individual predictions
by about 22–24 cp on average. INT16 closely reproduces the float evaluator.
Both weight formats use 32-bit feature accumulators and 64-bit output sums.

## Desktop inference and target builds

The Apple M1 rates are in millions of operations per second. An update is one
push or pop. The incremental evaluation figure includes push, score, and pop.
The full evaluation figure includes a two-view refresh and score.

| Model | Full refresh | Incremental update | Output only | Full evaluation | Incremental evaluation |
|---|---:|---:|---:|---:|---:|
| 768×256 INT8 | 0.80 | 8.62 | 2.46 | 0.63 | 1.63 |
| 768×256 INT16 | 0.99 | 9.67 | 2.60 | 0.74 | 1.73 |
| 704×128 INT8 | 1.68 | 15.63 | 6.51 | 1.31 | 3.88 |
| 704×128 INT16 | 1.64 | 15.69 | 5.06 | 1.19 | 3.78 |

Each finalist build matched all 128 Python integer scores and verified both
accumulators through 3,840 legal transitions in C++. Engine correctness tests
and the sanitizer tests with the medium-stage finalists passed. The full speed
sweep is in [timing.csv](timing.csv).

| Arduino Nano ESP32 cross-build | Linked flash (bytes) | Static RAM (bytes) |
|---|---:|---:|
| Handcrafted only | 322,077 | 115,304 |
| 768×256 INT8 | 523,237 | 117,368 |
| 768×256 INT16 | 720,309 | 117,368 |
| 704×128 INT8 | 416,541 | 116,344 |
| 704×128 INT16 | 506,829 | 116,344 |

All four trained finalist builds linked successfully. ESP32 runtime timing
remains unmeasured.

## VM shutdown

Compute Engine recorded 20 min 54 s from start to stop. At the assumed rate,
that is approximately US$0.38 in VM compute before storage, network charges,
credits, or taxes. This estimate uses elapsed time and a list-rate assumption.
The VM was independently confirmed `TERMINATED`, with the three-hour automatic
stop policy configured. See [VM status](vm-status.txt) and [artifact verification](verification.txt).

## Search games and architecture choice

All 240 desktop games finished. Each cell gives wins–draws–losses from
the NNUE side over 24 games at 25 ms per move.

| Model | Versus HCE-4 | Versus HCE-5 |
|---|---:|---:|
| 768×256 INT8, full corpus | 5–4–15 | 9–5–10 |
| 768×256 INT16, full corpus | 6–7–11 | 7–4–13 |
| 704×128 INT8, full corpus | 7–7–10 | 6–5–13 |
| 704×128 INT16, full corpus | 10–4–10 | 10–5–9 |
| 704×64 INT8, 10M | 6–0–18 | 10–3–11 |

In the separate position suite, 704×128 INT16 averaged 1.75 million nodes/s
at depth 4.69. HCE-4 averaged 2.79 million nodes/s at depth 5.06, and HCE-5
averaged 2.57 million nodes/s at depth 5.00. All finalist formats solved all
six tactical fixtures. See [game summary](match-summary.csv) and
[search summary](search-summary.csv).

**Use 704×128 INT16 as the first NNUE candidate for ESP32 runtime testing.**
It had the strongest game scores against both handcrafted references,
reproduced the float output within 0.26 cp on average, and linked in a
506,829-byte Nano ESP32 firmware image. INT8 is the smaller option at
90,904 bytes of compiled weights and scored lower in these games. The
768×256 INT16 remains the validation-accuracy reference. Keep the current
handcrafted firmware default pending on-device timing and longer matches.

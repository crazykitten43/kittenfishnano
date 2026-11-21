# KittenFish Nano

KittenFish Nano is an integer C++14 chess engine foundation for the Arduino
Nano ESP32. It runs the board, move generation, evaluation and search in the
firmware. A Raspberry Pi Zero 2 W can act as a serial client for UI and
communications.

| Variant | Evaluation |
|---|---|
| HCE-0 | Conventional material |
| HCE-1 | Incremental PeSTO material, piece-square tables and phase |
| HCE-2 | HCE-1 plus pawn structure, with optional pawn caching |
| HCE-3 | HCE-2 plus mobility and piece activity |
| HCE-4 | HCE-3 plus phase-scaled king safety |
| HCE-5 | HCE-4 plus threats and endgame scaling |

## Desktop

```sh
make
make test
python3 benchmarks/run.py --pairs 12
./build/kittenfishmicro think 7 100 "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
```

Alternatively, use CMake.

```sh
cmake -S . -B cmake-build -DCMAKE_BUILD_TYPE=Release
cmake --build cmake-build
(cd cmake-build && ctest --output-on-failure)
python3 benchmarks/run.py --engine cmake-build/kittenfishmicro --pairs 12
```

The desktop executable accepts feature masks. HCE-0 through HCE-5 use
`0, 1, 3, 7, 15, 63`. The `go` command on the Arduino uses milliseconds,
and its `hce` command uses variant numbers `0` through `5`.

The benchmark uses a single search thread and copies each opening into two
games with reversed colors. The test set and recorded parameters are in
[benchmarks](benchmarks) and the generated [report](results/summary.md) and [assessment](results/assessment.md).
Pass `--out /path/to/trial` to save another run without overwriting the
recorded results. Individual searches, games with full move lists, memory
measurements and match summaries are in [results](results).

## Arduino Nano ESP32

```sh
pio run -e arduino_nano_esp32
pio run -e arduino_nano_esp32 -t upload
pio device monitor -b 115200
```

The serial protocol expects one command per line. Send `start` or
`fen <FEN>` to set a position, `hce 2` to select the default evaluator, and
`go 1000` for a timed search. The response includes the best move, score,
completed depth and visited nodes. Search leaves the position intact. Send
`play <coordinate move>` to apply your move or the engine's response. Promotion
coordinates use a lower-case piece suffix, for example `e7e8q`.

The PlatformIO target is supplied. The recorded runs use a desktop compiler.
See the [architecture notes](docs/architecture.md) for verification status,
memory placement, search limits, and the interface for a future tiny NNUE.

[Attribution and third-party terms](docs/attribution.md)

## Experimental NNUE

See [NNUE training, firmware and benchmarks](nnue/README.md) for the experimental evaluator.

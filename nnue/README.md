# KittenFish Micro NNUE

The trainer reads the existing 67-byte, white-relative KFD1 records and converts
raw stored centipawns to side-to-move centipawns. All stages use a fixed,
byte-fingerprinted 100,000-position validation subset. The training draws are
nested and seeded. Each stage fits its candidates from scratch for five epochs,
then ranks the lowest validation RMSE observed during the stage. The default
sweep uses a shared output head. Pass `--buckets 8` for a piece-count head sweep
in a separate output directory.

Each position has two accumulators indexed from the respective side's
perspective. Black flips the ranks and both views put their own channels first.
For the 704-feature configurations each view first mirrors about the file axis
when its king is on files e–h. Both king channels always fold onto 32 squares
each. A move that crosses the file boundary refreshes only the affected view.
Other moves update by adding or subtracting rows, including castling, promotion
and en passant. The output concatenates side-to-move first, applies clipped
ReLU with integer scale, and rounds symmetrically to centipawns. Feature sums
use 32 bits and the output sum uses 64 bits. Exported weights are static C++14
data and can be compiled into flash. No model loader or allocation is needed
in the evaluator.

## Reproduction

Use an existing CUDA-enabled PyTorch environment with NumPy, or install
`requirements.txt` for a local CPU run. Run each stage in order with the same
manifest and output directory.

```sh
python nnue/train.py /path/to/manifest.json results/nnue/my-run --stage screen
python nnue/estimate.py results/nnue/my-run screen
python nnue/train.py /path/to/manifest.json results/nnue/my-run --stage medium
python nnue/estimate.py results/nnue/my-run medium
python nnue/train.py /path/to/manifest.json results/nnue/my-run --stage large
```

The cloud launcher uses the existing VM and dataset. It sets a three-hour
Compute Engine stop limit before powering on, records training time and
estimated cost before expanding, downloads run artifacts, and verifies that
the VM stopped. Its default paths are for `kittenfishgpu`.

```sh
nnue/run_vm.sh my-run
model=results/nnue/my-run/large/704x128
nnue/bench.sh "$model" 8
nnue/bench.sh "$model" 16
nnue/bench.sh "$model" 8 search 25
nnue/bench.sh "$model" 8 match 15 25 12 240
python nnue/report.py results/nnue/my-run
```

Provide a generated weight header using the `MICRO_NNUE_HEADER` C++ macro
when building firmware. Its value must be a quoted include path visible to
the compiler. For example, from the repository root:

```sh
model="$PWD/results/nnue/my-run/large/704x128/int8.hpp"
PLATFORMIO_BUILD_FLAGS="-std=gnu++14 -O3 -DKFM_TT_KIB=256 -DMICRO_NNUE_HEADER=\"$model\"" \
  pio run -e arduino_nano_esp32
```

An NNUE-enabled firmware build accepts the serial command
`nnue` to select the network and `hce 0` through `hce 5` to switch back to
a handcrafted variant. A normal firmware build continues to start with HCE-2.
Benchmarks run through the desktop C++ runner. PlatformIO reports linked
flash and static RAM usage. ESP32 speed requires timing on an actual board.

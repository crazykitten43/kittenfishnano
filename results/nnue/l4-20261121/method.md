# November 2026 NNUE experiment method

The existing KFD1 corpus contains 100,000,000 positions. Its manifest allocates
99,000,067 to training and 999,933 to validation. All models and quantizations
were scored on the same seeded 100,000-position slice of validation. The stage
JSON files record a byte-level SHA-256 of that slice. Labels are side-to-move
centipawns derived from the white-relative records, whose stored values were
already capped at ±2,000 cp.

Each stage fits from the same seeded initialization scheme and uses nested
training draws of 1,000,000, 10,000,000, and 99,000,067 positions. Models use
one output head, AdamW, Smooth L1 training loss, and BF16 matrix multiplication
on the NVIDIA L4. Advancement is by the best float validation RMSE within
five epochs. The held-out sample is held out of optimization and used for
architecture and checkpoint selection. There is one run per configuration.
An eight-head output option was exercised in a local smoke run.

Each model directory contains its best floating-point weights and latest
resumable checkpoint, both quantized C++ headers, the training records in
`metrics.json`, and 128 position/score pairs for parity. `accuracy.csv`
includes signed changes from the float model and mean absolute disagreement
with the float prediction. Reported training throughput is the median of
the five complete epochs, including batch preparation and optimizer steps
and excluding validation.

The C++14 tests compare exact rounded integer scores with the trainer's
reference and compare both incremental accumulators with full refresh
before and after each tested move. The positions include dedicated castling,
en passant, underpromotion and mirror-boundary cases. `timing.csv` records
host rates for all exported architectures and widths. A single incremental
operation is a push or a pop, measured together in pairs. Incremental
end-to-end evaluation includes a push, child output, and pop. Full
end-to-end evaluation includes both accumulator refreshes and output.

The Apple M1 search games use the unchanged move generator and search
logic with either the NNUE or handcrafted evaluation callback. Each
comparison starts from the same 12 openings, played with colors swapped,
with 25 ms per move for both sides and a 240-ply cap counted as a draw.
HCE-4 has activity, pawn structure, tapered evaluation and king safety.
HCE-5 is the full handcrafted configuration. The desktop match sample is
small and the time control is short. `search-summary.csv` is a separate
16-position search test at the same per-position time budget.

The Arduino Nano ESP32 results are build sizes from PlatformIO. The parity,
throughput and game results use the desktop; an ESP32 board was unavailable
for runtime testing. The validation and training data remain on the VM.
The import contains small parity fixtures. The corpus manifest remains local.

The local launcher was edited while it was running. Its exit status reflected
a local shell parse error after remote training had completed. The exit trap
collected all artifacts and stopped the VM. Independent checks verified all
13 checkpoint pairs, stage summaries, the matching validation fingerprint and
Compute Engine's `TERMINATED` state. The current launcher passes Bash syntax
validation.

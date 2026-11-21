# Architecture

## Board and legal moves

A 128-byte 0x88 mailbox provides square lookup and ray traversal. Six
bitboards per color provide occupied pieces by type and constant-time pawn
attack maps. Move generation emits pseudolegal moves into a fixed array.
Make rejects any move that leaves the mover in check and immediately restores
the position. Castling also checks rights, path occupancy and the transit
square. Perft and the search use the same path. The board APIs expect a
generated move or one validated through `parseMove`.

Each changed square updates the piece bitboard, PeSTO middlegame and
endgame sums, material, phase and Zobrist keys. Undo stores captured piece,
castling rights, en passant, the halfmove clock and the original position
key. The position key includes side, rights and en passant only when an en
passant capture is legal. Zobrist lookup data are compile-time constants.
Fullmove number is parsed for FEN compatibility and is unused by search.

## Evaluation

All variants return integer centipawns from the side-to-move perspective.
Taper uses remaining minor pieces, rooks and queens, with a phase cap of 24.
The pawn score carries half weight in the middlegame and full weight in the
endgame. The optional direct-mapped pawn cache keys that score by both sides'
pawn placement. Rear doubled pawns receive no passed-pawn bonus. A connected
pawn can receive a separate protected-passer premium when both conditions
apply.

Activity counts pseudo-attacks to enemy or empty squares outside enemy pawn
control. Its endgame weight is three quarters of its middlegame weight.
Outposts require pawn support, an advanced rank and no enemy pawn ahead on
adjacent files. A rook receives one file bonus, and its seventh-rank bonus
requires the enemy king on its back two ranks.

King danger uses weighted attacks on the neighboring king squares, capped
and squared to reward coordinated pressure. The same attack walk builds
mobility, danger and threat maps when those features are enabled. King
shelter and ring danger are middlegame terms that taper to zero as material
comes off. Threats use geometric attacks and approximate defenders, with
one of hanging, pawn threat or pressure assigned per target. Features
overlap with the historical PSTs to some degree, especially rooks and
pawns. The explicit bonuses are deliberately modest and remain untuned.
Opposite-colored bishops with no other non-pawn material receive a reduced
advantage. Search handles recognized dead positions in all variants.

See [weights.hpp](../include/weights.hpp) for evaluation coefficients. Feature
masks permit individual ablations without changing search. The pawn cache
accepts caller-provided zero-initialized storage or a null pointer.

## Search

Iterative deepening retains the last completed result, with a legal fallback
if the first iteration times out. PVS uses a null window for later moves
and re-searches when needed. Quiescence covers captures, promotions and all
check evasions, and confirms legal moves before returning a stand-pat score
so stalemate is scored as a draw. Ordering uses the TT move, MVV-LVA,
promotions and two killers per ply.

The TT is direct-mapped with mate-distance normalization and explicit
exact, upper and lower bounds. Its key includes the halfmove clock and a
sum of the reversible-history hashes to limit reuse across different draw
contexts. This reduces hit rate on move-order transpositions. Search treats
current threefold repetition and the 50-move threshold as draws, with a
terminal legal-move check first. Callers can supply prior position keys in
chronological order, excluding the root. A FEN alone carries no repetition
history. Clear the TT after changing evaluator weights, mask or network.

Timed search checks a monotonic microsecond clock every 64 nodes and after
completed iterations. The time budget is approximate. The hard maximum is
48 plies of workspace including quiescence. Search uses a static evaluation
at that frontier after checking for mate, stalemate and configured draws.
PVS and quiescence use recursive calls with move lists in a caller-owned
search object. The search is single threaded.

## ESP32 memory and execution

The firmware asks for 256 KiB of PSRAM TT space at startup. Set
`KFM_TT_KIB` in PlatformIO to change that size. Zero or allocation failure
selects a 1,024-entry internal TT. The fallback stays statically reserved
even when PSRAM succeeds. The board, undo frames and pawn cache use
internal RAM. The common search workspace is about 61 KiB on the tested
ARM64 desktop ABI. The firmware reports actual sizes at boot. The constexpr
weight and Zobrist tables are intended for flash-backed read-only storage.
There are no heap allocations in the search loop. ESP32 search periodically
yields a tick during long requests and requests a 16 KiB Arduino loop stack
when the Arduino core supplies the stack-size macro.

No physical Nano ESP32 or installed Xtensa/PlatformIO toolchain was
available for this run. The first device check should confirm PSRAM
selection in the startup line, linker placement, flash use, stack
high-water mark, and sustained NPS on the desktop position suite. It should
also compare the default PSRAM TT to the internal fallback on identical
positions and clocks. SRAM available to the sketch varies with the
framework, its stacks, and the ESP32 memory layout.

Sources: [Arduino Nano ESP32 documentation](https://docs.arduino.cc/hardware/nano-esp32) ·
[PlatformIO board configuration](https://docs.platformio.org/en/stable/boards/espressif32/arduino_nano_esp32.html)

## Tiny NNUE integration

Use the `Evaluator` callbacks in [micro.hpp](../include/micro.hpp). The caller
initializes the root accumulator. The search calls `push` with the child
board and move record after every successful search move. It calls `pop`
with the same child state before restoring the board, including on a stopped
search. A PVS re-search reuses the same child accumulator. Root probing and
legal-move tests do not call the evaluator.

Start with a shared 768-feature piece-square transformer and 32 hidden
units, then test 64 and 128 on the same data and positions. Use two
side-relative accumulators and orient the output to the current mover.
Update the changed feature rows for the departure square, arrival,
capture, and any promotion or castle rook move. En passant removes the
captured pawn from its actual square. Test every incremental update
against a full refresh, including make, undo and canceled search.

For an int8 transformer the three widths use 24, 48 and 96 KiB of weight
rows, plus biases and output weights. Two int32 accumulators use 256, 512
and 1,024 bytes respectively. Keep active accumulators in SRAM, compare
flash-resident and internal hot-row staging on hardware, and verify
quantization saturation against float inference. Measure raw eval speed,
incremental update cost, search quality and matched-clock self-play against
the HCE before choosing a width. This repository contains no NNUE training.

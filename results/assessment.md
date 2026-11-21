# Assessment

HCE-2 is the firmware default for initial hardware testing. It adds pawn
structure while retaining 95% of HCE-1's desktop search NPS and reaching the
same mean depth within rounding. HCE-2 scored 21 wins, 3 draws and no losses
against the material baseline. HCE-2's 5–13–6 result against HCE-1 and 9–10–5
result against HCE-5 have broad uncertainty. HCE-3 scored 8–12–4 against HCE-2.
HCE-1 is the simplest reference for initial clock and memory comparisons on
the hardware.

The ablations measure removal from the full evaluator. Removing activity
raised warmed raw evaluation throughput by about 10%, and HCE-5 scored
13–6–5 against that ablation. Removing threats raised it by about 9%, with
a match result of 8–9–7 for the full variant. Removing pawn structure
raised warmed raw throughput by about 1%, with a 10–10–4 match result.
Removing king safety gave 8–8–8 and showed no raw speed gain in this run.
The results are sensitive to position mix and timing. All four match
intervals include zero and were calculated individually. The six tactical
positions are smoke tests for the search and do not separate the variants.

The common desktop executable occupies 145,420 bytes. In the tested build,
a Board is 296 bytes, Search is 62,704 bytes, the TT is 262,144 bytes, and
the optional pawn cache is 8,192 bytes. Process peak RSS was about 1.30–1.39
MiB for all tested masks. The Arduino configuration requests 256 KiB of
PSRAM, reserves a 1,024-entry internal TT fallback and uses a 256-entry
pawn cache.

## Verification

- The desktop build used Apple Clang with C++14 and `-O3`. The same tests
  passed again with AddressSanitizer and UndefinedBehaviorSanitizer.
- The six standard perft positions matched all reference counts through
  depth four. Additional tests covered exact make/unmake state, castling
  through attack, rights lost on rook captures, legal and pinned en passant,
  underpromotion, mate, stalemate, repetition and accumulator callbacks on
  canceled search.
- A host smoke test of the Arduino entry point with mock serial, allocator
  and timer APIs exercised both TT allocation paths and legal and invalid
  commands. The PlatformIO/CMake commands were supplied for their respective
  build environments. PlatformIO, Xtensa and CMake were unavailable on
  this host. On-device compilation, memory placement and speed are unverified.

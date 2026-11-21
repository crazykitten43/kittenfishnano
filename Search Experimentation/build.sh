#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: bash 'Search Experimentation/build.sh' PROFILE OUTPUT" >&2
    exit 2
fi

case "$1" in
    Baseline|AlphaBeta|NoTable|TableOrderingOnly|NoKillers|NoCaptureOrdering|    GeneratorOrder|StaticLeaves|PlainNegamax|AspirationPvs|LateMoveReductions|    ExtendChecks|ReverseFutilityPruning|QuietPruning|AspirationLmr|SelectivePvs) ;;
    *) echo "Unknown search profile: $1" >&2; exit 2 ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$(dirname "$2")"
"${CXX:-c++}" -O3 -DNDEBUG -std=c++14 -Wall -Wextra -Wpedantic     "-DNANO_SEARCH_PROFILE=$1" -DNANO_TOURNAMENT -I"$root/include"     "$root/src/board.cpp" "$root/src/eval.cpp"     "$root/Search Experimentation/search.cpp" "$root/benchmarks/driver.cpp"     -o "$2"

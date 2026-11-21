#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
model=$(cd "$1" && pwd)
bits=$2
binary=$(mktemp -d)
trap 'rm -rf "$binary"' EXIT
core=(src/board.cpp src/eval.cpp src/search.cpp)
flags=(-std=c++14 -O3 -Wall -Wextra -Iinclude "-DMICRO_NNUE_HEADER=\"$model/int$bits.hpp\"")
if [[ ${3:-} == match || ${3:-} == search ]]; then
    "${CXX:-c++}" "${flags[@]}" "${core[@]}" benchmarks/driver.cpp -o "$binary/micro"
    if [[ $3 == match ]]; then
        "$binary/micro" match 64 "${4:?HCE mask}" "${5:?milliseconds per move}" "${6:?opening pairs}" "${7:?ply cap}" benchmarks/openings.tsv
    else
        "$binary/micro" bench 64 "${4:?milliseconds per position}" benchmarks/positions.tsv
    fi
else
    "${CXX:-c++}" "${flags[@]}" "${core[@]}" nnue/benchmark.cpp -o "$binary/bench"
    "$binary/bench" "$model/fixture.tsv" "$bits"
fi

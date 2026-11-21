#!/usr/bin/env python3
"""Run all timing tests and color-reversed matches sequentially."""
import argparse
import csv
import math
from pathlib import Path
import platform
import statistics
import subprocess
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {0: "HCE-0", 1: "HCE-1", 3: "HCE-2", 7: "HCE-3", 15: "HCE-4", 63: "HCE-5"}
ABLATIONS = {61: "No pawn structure", 59: "No activity", 55: "No king safety", 47: "No threats"}
NAMES = {**VARIANTS, **ABLATIONS}


def save(path, fields, rows):
    with path.open("w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(fields.split(","))
        writer.writerows(rows)


def elo(p):
    if p == 0:
        return "-inf"
    if p == 1:
        return "+inf"
    return round(400 * math.log10(p / (1 - p)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=ROOT / "build/kittenfishmicro")
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    parser.add_argument("--search-ms", type=int, default=35)
    parser.add_argument("--match-ms", type=int, default=3)
    parser.add_argument("--pairs", type=int, default=8)
    parser.add_argument("--ply-cap", type=int, default=140)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.pairs <= 12 or min(args.search_ms, args.match_ms, args.ply_cap, args.samples) < 1:
        parser.error("use 1–12 opening pairs and positive time, ply and sample limits")
    out = args.out.resolve()
    out.mkdir(exist_ok=True, parents=True)
    engine = args.engine.resolve()

    def invoke(*parameters):
        return subprocess.check_output([str(engine), *map(str, parameters)], text=True, cwd=ROOT)

    evals, searches, memory = [], [], []
    for flags, name in NAMES.items():
        for run in range(1, args.samples + 1):
            raw = invoke("bench", flags, args.search_ms, "benchmarks/positions.tsv")
            for kind, *values in csv.reader(raw.splitlines()):
                {"eval": evals, "search": searches, "memory": memory}[kind].append([run, *values])
        print(f"Timed {name}", flush=True)
    save(out / "eval.csv", "sample,mask,evaluations,microseconds,checksum", evals)
    save(out / "search.csv", "sample,mask,category,position,nodes,microseconds,depth,move,score,solved", searches)
    save(out / "memory.csv", "sample,mask,board_bytes,search_bytes,tt_bytes,pawn_cache_bytes,peak_rss_bytes", memory)

    matchups = [(a, b) for i, a in enumerate(VARIANTS) for b in list(VARIANTS)[:i]]
    matchups += [(63, b) for b in ABLATIONS]
    summary = []
    with (out / "games.csv").open("w", newline="") as game_file:
        writer = csv.writer(game_file, lineterminator="\n")
        writer.writerow("first,second,opening,first_color,result,termination,plies,moves".split(","))
        for first, second in matchups:
            command = [engine, "match", first, second, args.match_ms, args.pairs,
                       args.ply_cap, "benchmarks/openings.tsv"]
            counts = Counter()
            paired = defaultdict(list)
            caps = 0
            with subprocess.Popen(list(map(str, command)), cwd=ROOT, text=True, stdout=subprocess.PIPE) as proc:
                for row in csv.reader(proc.stdout):
                    writer.writerow(row)
                    game_file.flush()
                    result = int(row[4])
                    counts[result] += 1
                    paired[row[2]].append((1 + result) / 2)
                    caps += row[5] == "ply-cap"
                if proc.wait():
                    raise RuntimeError(f"match failed: {first}, {second}")
            if len(paired) != args.pairs or any(len(pair) != 2 for pair in paired.values()):
                raise RuntimeError("Incomplete color pairs")
            p = statistics.mean(statistics.mean(scores) for scores in paired.values())
            # Distribution-free 95% Hoeffding interval using each opening pair
            # as one observation. The endpoints deliberately allow infinite Elo.
            radius = math.sqrt(math.log(40) / (2 * len(paired)))
            summary.append([first, second, counts[1], counts[0], counts[-1], caps, p,
                            elo(p), elo(max(0, p-radius)), elo(min(1, p+radius))])
            print(f"{NAMES[first]} vs {NAMES[second]}: {counts[1]}–{counts[0]}–{counts[-1]}", flush=True)
    save(out / "matches.csv", "first,second,wins,draws,losses,ply_caps,score,elo,elo_low,elo_high", summary)

    binary = engine.stat().st_size
    lines = [
        "# Desktop benchmark", "",
        f"- Platform: {platform.platform()} / {platform.machine()}",
        f"- Binary: {binary:,} bytes on disk, shared by all variants",
        f"- Search: {args.search_ms} ms per position, {args.samples} samples",
        f"- Matches: {args.match_ms} ms per move, {args.pairs} opening pairs, {args.ply_cap} ply cap",
        "", "| Evaluator | Eval/s | ns/eval | Search NPS | Mean depth | Tactics | Peak RSS MiB |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for flags, name in NAMES.items():
        eval_rate = statistics.median(int(n)*1e6/int(t) for _, f, n, t, _ in evals if int(f) == flags)
        relevant = [row for row in searches if int(row[1]) == flags]
        normal = [row for row in relevant if row[2] != "tactical"]
        nodes = sum(int(row[4]) for row in normal)
        micros = sum(int(row[5]) for row in normal)
        depths = statistics.mean(int(row[6]) for row in normal)
        tactics = [int(row[-1]) for row in relevant if int(row[-1]) >= 0]
        rss = max(int(row[-1]) for row in memory if int(row[1]) == flags)/2**20
        lines.append(f"| {name} | {eval_rate:,.0f} | {1e9/eval_rate:,.1f} | {nodes*1e6/micros:,.0f} | "
                     f"{depths:.2f} | {sum(tactics)}/{len(tactics)} | {rss:.2f} |")
    lines.extend(["", "Throughput and completed depth use the opening, middlegame and endgame positions. "
                  "The raw evaluation loop measures a warmed 512-entry pawn cache. Each search starts cold.",
                  "", "### Playing strength", "",
                  "| First | Second | W | D | L | Ply caps | Elo | 95% interval |",
                  "|---|---|---:|---:|---:|---:|---:|---|"])
    for first, second, w, d, loss, caps, _, rating, low, high in summary:
        lines.append(f"| {NAMES[first]} | {NAMES[second]} | {w} | {d} | {loss} | {caps} | "
                     f"{rating} | [{low}, {high}] |")
    lines.extend(["", "Ply-cap games count as draws in this protocol. Pairing reduces color bias. "
                  "The conservative 95% intervals assume independent opening pairs and describe this "
                  "test protocol. The fixed opening set and tiny time control limit generalization.", ""])
    (out / "summary.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()

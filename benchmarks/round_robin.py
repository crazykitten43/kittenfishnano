#!/usr/bin/env python3
"""Play or export the 60+1 KittenFish Nano evaluator round robin."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import fcntl
import hashlib
import io
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import subprocess
import time

import chess.pgn

ROOT = Path(__file__).resolve().parent.parent
NAMES = dict(zip((3, 7, 15, 63, 64, 65, 66, 67), (
    "HCE-2", "HCE-3", "HCE-4", "HCE-5", "704x128 INT8", "704x128 INT16",
    "768x256 INT8", "768x256 INT16",
)))
NETS = ROOT / "results/nnue/l4-20261121/large"
OPENINGS = dict(line.split("\t") for line in
                (ROOT / "benchmarks/openings.tsv").read_text().splitlines())
SCHEDULE = [(opening, first, second, color)
            for opening in OPENINGS for first, second in combinations(NAMES, 2)
            for color in (0, 1)]
FIELDS = ("first", "second", "opening", "first_color", "outcome", "reason",
          "played_plies", "moves", "white_us", "black_us", "elapsed_us")


def save(path, data):
    temp = path.with_suffix(".tmp")
    with temp.open("w") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)


def parse_game(raw, game, config):
    opening, first, second, color = game
    values = next(csv.reader([raw.strip()]))
    if len(values) != len(FIELDS) or values[:4] != [
        str(first), str(second), opening, "BW"[color == 0]
    ]:
        raise ValueError(f"Unexpected game row for {game}")
    row = dict(zip(FIELDS, values))
    moves = row["moves"].split()
    elapsed = list(map(int, row["elapsed_us"].split()))
    forfeited = row["reason"] == "time-forfeit"
    outcome = int(row["outcome"])
    if (int(row["played_plies"]) != len(moves) or outcome not in (-1, 0, 1)
            or len(elapsed) != len(moves) + forfeited):
        raise ValueError(f"Invalid score, plies or clock samples for {game}")
    white, black = (first, second) if color == 0 else (second, first)
    pgn = chess.pgn.Game()
    pgn.headers.update(Event="KittenFish Nano evaluator round robin",
                       Site=config["site"], White=NAMES[white], Black=NAMES[black],
                       Result={1: "1-0", 0: "1/2-1/2", -1: "0-1"}[
                           outcome if color == 0 else -outcome],
                       TimeControl=f'{config["initial_ms"]/1000:g}+{config["increment_ms"]/1000:g}',
                       Opening=opening, Termination=row["reason"])
    board = pgn.board()
    node = pgn
    for uci in OPENINGS[opening].split():
        move = board.parse_uci(uci)
        node = node.add_variation(move)
        board.push(move)
    clocks = {side: 1000 * config["initial_ms"] for side in chess.COLORS}
    for uci, spent in zip(moves, elapsed):
        side = board.turn
        if not 0 <= spent < clocks[side]:
            raise ValueError(f"Accepted move after flag in {game}")
        clocks[side] += 1000 * config["increment_ms"] - spent
        move = board.parse_uci(uci)
        node = node.add_variation(move)
        node.set_clock(clocks[side] / 1_000_000)
        board.push(move)
    if forfeited:
        loser = white if board.turn == chess.WHITE else black
        if elapsed[-1] < clocks[board.turn] or outcome != (-1 if loser == first else 1):
            raise ValueError(f"Invalid flag in {game}")
        clocks[board.turn] = 0
    if [clocks[chess.WHITE], clocks[chess.BLACK]] != [
        int(row["white_us"]), int(row["black_us"])
    ]:
        raise ValueError(f"Clock mismatch in {game}")
    if board.ply() > config["cap"] or (
        row["reason"] == "ply-cap" and (board.ply() != config["cap"] or outcome)
    ):
        raise ValueError(f"Invalid ply cap in {game}")
    return row, pgn


def export(out):
    config = json.loads((out / "config.json").read_text())
    scores = {name: Counter(wins=0, draws=0, losses=0, points=0, time_forfeits=0,
                            capped_draws=0) for name in NAMES.values()}
    head = {f"{NAMES[a]} vs {NAMES[b]}": Counter(wins=0, draws=0, losses=0,
                                               first_points=0, second_points=0)
            for a, b in combinations(NAMES, 2)}
    coverage = Counter({opening: 0 for opening in OPENINGS})
    paired = Counter()
    reasons = Counter()
    pgns = []
    csv_output = io.StringIO()
    writer = csv.DictWriter(csv_output, ("game_id", *FIELDS), lineterminator="\n")
    writer.writeheader()
    for path in sorted((out / "games").glob("*.csv")):
        index = int(path.stem)
        game = SCHEDULE[index - 1]
        row, pgn = parse_game(path.read_text(), game, config)
        writer.writerow(dict(row, game_id=index))
        pgn.headers["Round"] = str(index)
        pgns.append(str(pgn))
        opening, a, b, _ = game
        a, b = NAMES[a], NAMES[b]
        coverage[opening] += 1
        paired[opening, a, b] += 1
        reason = row["reason"]
        reasons[reason] += 1
        score = int(row["outcome"])
        tally = head[f"{a} vs {b}"]
        tally[("draws", "wins", "losses")[score]] += 1
        tally["first_points"] += (1 + score) / 2
        tally["second_points"] += (1 - score) / 2
        for name, result in ((a, score), (b, -score)):
            scores[name][("draws", "wins", "losses")[result]] += 1
            scores[name]["points"] += (1 + result) / 2
            scores[name]["time_forfeits"] += reason == "time-forfeit" and result == -1
            scores[name]["capped_draws"] += reason == "ply-cap"
    standings = dict(sorted(scores.items(), key=lambda entry: -entry[1]["points"]))
    summary = dict(completed=len(pgns), scheduled=len(SCHEDULE), by_opening=coverage,
                   complete_opening_rounds=[o for o in OPENINGS if coverage[o] == 56],
                   complete_color_pairs=sum(n == 2 for n in paired.values()),
                   terminations=reasons, standings=standings, head_to_head=head)
    save(out / "standings.json", json.dumps(summary, indent=2) + "\n")
    save(out / "games.pgn", "\n\n".join(pgns) + "\n")
    save(out / "games.csv", csv_output.getvalue())
    return summary


def play(args):
    out = args.output
    games = out / "games"
    games.mkdir(parents=True, exist_ok=True)
    assert len(OPENINGS) == 12 and len(SCHEDULE) == 672
    config = dict(commit=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        compiler=args.compiler, flags=args.flags, engine_sha256=digest(args.engine),
        openings_sha256=digest(ROOT / "benchmarks/openings.tsv"),
        weights={str(p.relative_to(ROOT)): digest(p) for p in sorted(NETS.glob("*/int*.hpp"))},
        entrants=NAMES, tt_entries=16384, pawn_entries=512, search_depth_limit=32,
        time_policy="max(1, min(clock_us/24 + 3*increment_us/4, clock_us-50000)/1000) ms, integer division",
        clear_tables_each_move=True, initial_ms=args.initial, increment_ms=args.increment,
        cap=args.cap, cap_includes_opening=True, workers=args.workers, site=args.site,
        platform=platform.platform(), python_chess=chess.__version__)
    config_text = json.dumps(config, indent=2) + "\n"
    config_path = out / "config.json"
    if config_path.exists() and config_path.read_text() != config_text:
        raise ValueError("Existing results use a different configuration")
    save(config_path, config_text)
    initial = config["initial_ms"]
    increment = config["increment_ms"]
    cap = config["cap"]

    openings = out / "openings"
    openings.mkdir(exist_ok=True)
    for opening, moves in OPENINGS.items():
        save(openings / (opening + ".tsv"), f"{opening}\t{moves}\n")

    def run_game(index):
        game = SCHEDULE[index - 1]
        opening, first, second, color = game
        path = games / f"{index:03d}.csv"
        if path.exists():
            parse_game(path.read_text(), game, config)
            return
        if time.time() >= args.stop_at - (2 * initial + cap * increment) / 1000 - 10:
            return
        start = time.monotonic()
        raw = subprocess.check_output(
            [str(args.engine.resolve()), "clock-match", str(first), str(second),
             str(initial), str(increment), str(cap), str(color),
             str(openings / (opening + ".tsv"))],
            text=True, timeout=min(args.stop_at - time.time(),
                                   (2 * initial + cap * increment) / 1000 + 10))
        row, _ = parse_game(raw, game, config)
        save(path, raw)
        print(f'{index:03d} {opening} {NAMES[first]} vs {NAMES[second]} {row["first_color"]} '
              f'{row["outcome"]} {row["reason"]} {time.monotonic()-start:.2f}s', flush=True)

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(run_game, range(1, args.limit + 1)))
    summary = export(out)
    print(f'{summary["completed"]}/672 games saved after {time.monotonic()-started:.2f}s', flush=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--compiler", default="unknown")
    parser.add_argument("--flags", default="unknown")
    parser.add_argument("--workers", type=int, choices=range(1, 17), default=16)
    parser.add_argument("--limit", type=int, choices=range(1, 673), default=672,
                        metavar="1..672")
    parser.add_argument("--stop-at", type=float, default=float("inf"))
    parser.add_argument("--site", default="Local")
    parser.add_argument("--initial", type=int, default=60000, help="Initial milliseconds")
    parser.add_argument("--increment", type=int, default=1000, help="Increment milliseconds")
    parser.add_argument("--cap", type=int, default=240, help="Total plies including opening")
    args = parser.parse_args()
    if args.export:
        print(f'{export(args.output)["completed"]}/672 games exported')
        return
    if not args.engine or args.initial <= 0 or args.increment < 0 or args.cap < 8:
        parser.error("provide an engine, positive initial clock, nonnegative increment and cap >= 8")
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        play(args)


if __name__ == "__main__":
    main()

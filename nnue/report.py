#!/usr/bin/env python3
"""Summarize training and desktop benchmark artifacts from a completed run."""
import csv
import json
import statistics
import sys
from pathlib import Path


def training(run):
    fields = ["stage", "architecture", "bits", "train_positions", "validation_positions",
              "best_epoch", "median_train_positions_s", "mae_cp", "rmse_cp", "pearson",
              "model_bytes", "delta_mae_cp", "delta_rmse_cp", "float_delta_mae_cp"]
    with (run / "accuracy.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for stage in ("screen", "medium", "large"):
            path = run / f"{stage}.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            for model in data["ranking"]:
                hist = model["history"]
                row = dict(stage=stage, architecture=f"{model['features']}x{model['hidden']}",
                           train_positions=data["training_positions"],
                           validation_positions=data["validation_positions"],
                           best_epoch=min(hist, key=lambda h: h["rmse_cp"])["epoch"],
                           median_train_positions_s=round(statistics.median(
                               h["positions_per_second"] for h in hist)))
                for bits in ("float", "int8", "int16"):
                    if bits == "float":
                        hidden, buckets = model["hidden"], model["buckets"]
                        values = dict(model, model_bytes=4 * (model["features"] * hidden + hidden +
                                                               2 * hidden * buckets + buckets))
                    else:
                        values = model[bits]
                    writer.writerow(dict(row, bits=bits, **values))


def timing(run):
    desktop = run / "desktop"
    fields = ["stage", "architecture", "bits", "parity_cases", "transition_cases",
              "model_bytes", "state_bytes", "metric", "operations", "seconds",
              "operations_per_second", "checksum"]
    with (run / "timing.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        for stage in ("screen", "medium", "large"):
            for file in sorted((desktop / stage).glob("*.csv")):
                arch, bits = file.stem.split("-")
                with file.open() as raw:
                    reader = csv.reader(raw)
                    metadata = dict(next(reader) for _ in range(4))
                    for row in csv.DictReader(raw):
                        writer.writerow(dict(stage=stage, architecture=arch, bits=bits,
                                             **metadata, **row))


def search(run):
    with (run / "search-summary.csv").open("w") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["candidate", "positions", "aggregate_nodes_s", "mean_depth",
                         "tactics_solved", "tactics_total"])
        for file in sorted((run / "desktop").glob("search-*.csv")):
            with file.open() as raw:
                rows = [r for r in csv.reader(raw) if r[0] == "search"]
            if not rows:
                raise ValueError(f"No search results in {file}")
            nodes = sum(int(r[4]) for r in rows)
            micros = sum(int(r[5]) for r in rows)
            writer.writerow([file.stem.removeprefix("search-"), len(rows),
                             round(nodes * 1e6 / micros),
                             round(statistics.mean(int(r[6]) for r in rows), 2),
                             sum(r[9] == "1" for r in rows), sum(r[9] != "-1" for r in rows)])


def matches(run):
    files = sorted((run / "desktop").glob("match-*.csv"))
    if not files:
        return
    with (run / "match-summary.csv").open("w") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["candidate", "hce_mask", "wins", "draws", "losses", "points_pct", "ply_cap_draws"])
        for file in files:
            with file.open() as game_log:
                rows = list(csv.reader(game_log))
            wins = sum(r[4] == "1" for r in rows)
            draws = sum(r[4] == "0" for r in rows)
            losses = sum(r[4] == "-1" for r in rows)
            if wins + draws + losses != len(rows) or not rows:
                raise ValueError(f"Missing or invalid match results in {file}")
            writer.writerow([file.stem.removeprefix("match-"), rows[0][1], wins, draws, losses,
                             round((wins + .5 * draws) * 100 / len(rows), 2),
                             sum(r[5] == "ply-cap" for r in rows)])


if __name__ == "__main__":
    root = Path(sys.argv[1])
    training(root)
    timing(root)
    search(root)
    matches(root)

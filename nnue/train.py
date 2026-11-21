#!/usr/bin/env python3
"""Train KittenFish Micro networks on the existing white-relative KFD1 dataset."""
import argparse
import hashlib
import json
import math
import random
import re
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

RECORD = np.dtype([("board", "u1", (64,)), ("stm", "u1"), ("cp", "<i2")])
MODELS = [(768, h) for h in (16, 32, 64, 128, 256)] + [(704, 64), (704, 128)]
CP_SCALE = 400
SEED = 42


def dataset(path, val_limit):
    raw = path.read_bytes()
    m = json.loads(raw)
    if (m["format"], m["record_bytes"], m["perspective"]) != ("KFD1", 67, "white"):
        raise ValueError("Expected white-relative 67-byte KFD1 records")
    counts = {"train": 0, "val": 0}
    paths = set()
    splits = {"train": [], "val": []}
    digest = hashlib.sha256()
    for shard in sorted(m["shards"], key=lambda s: s["path"]):
        name, split, count = (shard[k] for k in ("path", "split", "count"))
        file = path.parent / name
        if Path(name).name != name or name in paths or count <= 0:
            raise ValueError(f"Invalid shard entry {name}")
        if file.stat().st_size != RECORD.itemsize * count:
            raise ValueError(f"Incorrect byte length for {file}")
        paths.add(name)
        counts[split] += count
        splits[split].append((file, count))
    if counts != m["counts"] or not all(counts.values()):
        raise ValueError("Invalid dataset split counts")
    random.Random(SEED).shuffle(splits["train"])
    random.Random(SEED).shuffle(splits["val"])
    remaining = val_limit
    validation = []
    for file, count in splits["val"]:
        if remaining <= 0:
            break
        count = min(remaining, count)
        rows = np.memmap(file, dtype=RECORD, mode="r", shape=(count,))
        digest.update(memoryview(rows).cast("B"))
        validation.append((file, count))
        remaining -= count
    return splits["train"], validation, counts, hashlib.sha256(raw).hexdigest(), digest.hexdigest()


def plan(shards, limit):
    chosen = []
    for file, count in shards:
        take = min(count, limit)
        if take <= 0:
            break
        chosen.append((file, take))
        limit -= take
    return chosen


def batches(shards, batch, device, epoch=None):
    shards = list(shards)
    rng = np.random.default_rng(SEED + epoch) if epoch is not None else None
    if rng is not None:
        rng.shuffle(shards)
    for file, count in shards:
        rows = np.memmap(file, dtype=RECORD, mode="r", shape=(count,))
        order = rng.permutation(count) if rng is not None else np.arange(count)
        for start in range(0, count, batch):
            records = rows[order[start:start + batch]]
            board = torch.from_numpy(np.ascontiguousarray(records["board"])).to(device)
            side = torch.from_numpy(records["stm"].copy()).to(device, dtype=torch.long)
            cp = torch.from_numpy(records["cp"].copy()).to(device, dtype=torch.float32)
            yield board, side, cp * (1 - 2 * side)


def sparse_ids(board, features):
    """Feature rows for each piece, with the final row reserved for padding."""
    square = torch.arange(64, device=board.device)
    pc = (board.to(torch.long) - 1).clamp_min(0)
    result = []
    for view in (0, 1):
        channel = ((pc // 6) ^ view) * 6 + pc % 6
        sq = square ^ (56 * view)
        offset = channel * 64
        if features == 704:
            king = (board == 6 + 6 * view).to(torch.int32).argmax(dim=1)
            sq = sq ^ (((king & 4) != 0)[:, None].long() * 7)
            offset = offset - (channel // 6) * 32
            file = sq % 8
            sq = torch.where(pc % 6 == 5, sq // 8 * 4 + torch.minimum(file, 7 - file), sq)
        result.append((offset + sq).masked_fill(board == 0, features))
    return torch.stack(result, dim=1)


def inputs(board, features, buckets):
    ids = sparse_ids(board, features)
    # Pack sparse IDs into two binary rows for the L4's dense matrix multiply.
    # All non-padding indices are unique within each perspective.
    dense = torch.zeros((*ids.shape[:2], features + 1), device=board.device)
    dense.scatter_(2, ids, 1)
    if buckets == 8:
        bucket = ((board.count_nonzero(dim=1) - 1) // 4).clamp(0, 7)
    else:
        bucket = torch.zeros(len(board), dtype=torch.long, device=board.device)
    return dense[..., :features], bucket


def order_views(acc, side):
    idx = torch.arange(len(side), device=side.device)
    return torch.cat((acc[idx, side], acc[idx, 1 - side]), dim=1)


class Net(nn.Module):
    def __init__(self, features, hidden, buckets):
        super().__init__()
        self.transform = nn.Linear(features, hidden)
        self.output = nn.Linear(2 * hidden, buckets)
        with torch.no_grad():
            self.transform.weight.normal_(std=.025)
            self.transform.bias.fill_(.1)
            self.output.weight.normal_(std=.05)
            self.output.bias.zero_()

    def forward(self, dense, side, bucket):
        acc = order_views(self.transform(dense).clamp(0, 1), side)
        return self.output(acc).float().gather(1, bucket[:, None]).squeeze(1)


def power_scale(values, cap, max_power):
    peak = float(values.abs().max())
    return 2 ** min(max_power, math.floor(math.log2(cap / peak))) if peak else 2 ** max_power


def quantize(net, bits):
    cap = (1 << (bits - 1)) - 1
    first = net.transform.weight.detach().T.contiguous()
    output = net.output.weight.detach() * CP_SCALE
    scale = power_scale(first, cap, 14)
    out_scale = power_scale(output, cap, 16)
    # Keep the stored divisor integral even when output weights are large.
    if scale < 1 or scale * out_scale < 1:
        raise ValueError("Weights exceed quantizer range")
    dtype = torch.int8 if bits == 8 else torch.int16
    bias = (net.transform.bias.detach() * scale).round().to(torch.int32)
    if float(bias.abs().max()) + 64 * cap >= 2 ** 24:
        raise ValueError("First layer exceeds the exact validation sum range")
    return {
        "input": (first * scale).round().to(dtype),
        "bias": bias,
        "output": (output * out_scale).round().to(dtype),
        "outputBias": (net.output.bias.detach().double() * CP_SCALE * scale * out_scale).round().to(torch.int64),
        "activationScale": int(scale),
        "divisor": int(scale * out_scale),
    }


class IntegerReference:
    def __init__(self, weights):
        self.weights = weights
        self.input = weights["input"].float()
        self.bias = weights["bias"].float()
        self.output = weights["output"].double()

    def __call__(self, dense, side, bucket):
        w = self.weights
        # These operations are exact integer sums in their respective mantissas.
        acc = order_views((dense @ self.input + self.bias).clamp(0, w["activationScale"]), side)
        total = (acc.double() * self.output[bucket]).sum(1) + w["outputBias"][bucket]
        div = w["divisor"]
        return (torch.sign(total) * ((total.abs() + div // 2) / div).floor()).float()


def metrics(pred, target):
    delta = pred - target
    centered = pred - pred.mean()
    ref = target - target.mean()
    denominator = np.linalg.norm(centered) * np.linalg.norm(ref)
    return dict(mae_cp=float(np.abs(delta).mean()), rmse_cp=float(np.sqrt((delta ** 2).mean())),
                pearson=float(np.dot(centered, ref) / denominator) if denominator else None)


@torch.no_grad()
def evaluate(net, data, features, buckets, args, quantized=None):
    output = [[] for _ in range(2 + len(quantized or []))]
    for board, side, target in batches(data, args.batch_size, args.device):
        dense, bucket = inputs(board, features, buckets)
        values = [target, net(dense, side, bucket) * CP_SCALE]
        values += [ref(dense, side, bucket) for ref in quantized or []]
        for dest, value in zip(output, values):
            dest.append(value.cpu().numpy().astype(np.float64))
    target, pred, *variants = map(np.concatenate, output)
    result = metrics(pred, target)
    return result, [dict(**metrics(q, target), float_delta_mae_cp=float(np.abs(q-pred).mean()))
                    for q in variants]


def atomic_save(value, path):
    temp = path.with_suffix(".tmp")
    torch.save(value, temp)
    temp.replace(path)


def export(weights, features, hidden, buckets, bits, path):
    def initializer(value):
        if value.ndim == 1:
            return "{" + ",".join(map(str, value.tolist())) + "}"
        return "{\n" + ",\n".join(initializer(row) for row in value) + "\n}"
    arrays = [weights[key].cpu().numpy() for key in ("input", "bias", "output", "outputBias")]
    arrays[2] = arrays[2].reshape(buckets, 2, hidden)
    integers = [weights["activationScale"], weights["divisor"]]
    size = sum(a.nbytes for a in arrays) + 16  # int32 scale, alignment, int64 divisor
    path.write_text("#pragma once\n#include \"nnue.hpp\"\n"
                    f"using ExportedModel = micro::NnueWeights<int{bits}_t,{features},{hidden},{buckets}>;\n"
                    f"using ExportedNnue = micro::Nnue<int{bits}_t,{features},{hidden},{buckets}>;\n"
                    "static constexpr ExportedModel exportedWeights = {\n"
                    + ",\n".join([initializer(a) for a in arrays] + list(map(str, integers)))
                    + "\n};\n" + f"static_assert(sizeof(ExportedModel) == {size}, \"Model size mismatch\");\n")
    return size


def fixture(refs, validation, features, buckets, args, dest):
    """Export scores from the actual training tensor path, independently of Board."""
    board, side, _ = next(batches(validation, 128, args.device))
    dense, bucket = inputs(board, features, buckets)
    scores = [ref(dense, side, bucket).cpu().tolist() for ref in refs]
    symbols = ".PNBRQKpnbrqk"
    with dest.open("w") as stream:
        for n, (row, turn) in enumerate(zip(board.cpu().tolist(), side.cpu().tolist())):
            ranks = ["".join(symbols[p] for p in row[i:i + 8]) for i in range(56, -1, -8)]
            fen = "/".join(re.sub(r"\.+", lambda m: str(len(m[0])), rank) for rank in ranks)
            stm = "b" if turn else "w"
            stream.write(f"{int(scores[0][n])}\t{int(scores[1][n])}\t{fen} {stm} - - 0 1\n")


def train(model, train_data, validation, args, directory):
    features, hidden = model
    directory.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(SEED)
    net = Net(features, hidden, args.buckets).to(args.device)
    optimizer = torch.optim.AdamW(net.parameters(), lr=.003, fused=args.device == "cuda")
    best = float("inf")
    count = sum(n for _, n in train_data)
    best_path = directory / "best.pt"
    history = []
    last = directory / "last.pt"
    start_epoch = 1
    if last.exists():
        saved = torch.load(last, weights_only=True, map_location=args.device)
        if saved["fingerprint"] != args.fingerprint:
            raise ValueError(f"Cannot resume with different data or configuration: {last}")
        net.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        history = saved["history"]
        best = min(e["rmse_cp"] for e in history)
        start_epoch = len(history) + 1
    for epoch in range(start_epoch, args.epochs + 1):
        begin = time.perf_counter()
        for board, side, target in batches(train_data, args.batch_size, args.device, epoch):
            dense, bucket = inputs(board, features, args.buckets)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(args.device, dtype=torch.bfloat16, enabled=args.device == "cuda"):
                pred = net(dense, side, bucket)
            loss = nn.functional.smooth_l1_loss(pred, target / CP_SCALE, beta=.5)
            loss.backward()
            optimizer.step()
        if args.device == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - begin
        score, _ = evaluate(net, validation, features, args.buckets, args)
        if not math.isfinite(score["rmse_cp"]):
            raise RuntimeError("Non-finite validation error")
        event = dict(epoch=epoch, positions=count, seconds=elapsed, positions_per_second=count/elapsed, **score)
        history.append(event)
        print(directory.name, json.dumps(event), flush=True)
        if score["rmse_cp"] < best:
            best = score["rmse_cp"]
            atomic_save(net.state_dict(), best_path)
        atomic_save(dict(model=net.state_dict(), optimizer=optimizer.state_dict(),
                         history=history, fingerprint=args.fingerprint), last)
    net.load_state_dict(torch.load(best_path, weights_only=True, map_location=args.device))
    quantized = [quantize(net, bits) for bits in (8, 16)]
    refs = list(map(IntegerReference, quantized))
    score, alternatives = evaluate(net, validation, features, args.buckets, args, refs)
    for bits, weights, numbers in zip((8, 16), quantized, alternatives):
        name = f"int{bits}"
        numbers["model_bytes"] = export(weights, features, hidden, args.buckets, bits, directory / f"{name}.hpp")
        numbers["delta_mae_cp"] = numbers["mae_cp"] - score["mae_cp"]
        numbers["delta_rmse_cp"] = numbers["rmse_cp"] - score["rmse_cp"]
        score[name] = numbers
    fixture(refs, validation, features, args.buckets, args, directory / "fixture.tsv")
    score.update(features=features, hidden=hidden, buckets=args.buckets, history=history)
    (directory / "metrics.json").write_text(json.dumps(score, indent=2) + "\n")
    return score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--stage", choices=("screen", "medium", "large"), required=True)
    parser.add_argument("--positions", type=int)
    parser.add_argument("--validation", type=int, default=100_000)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--buckets", type=int, default=1, choices=(1, 8))
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    if min(args.validation, args.epochs, args.batch_size, args.positions if args.positions is not None else 1) < 1:
        parser.error("positions, validation, epochs and batch size must be positive")
    torch.set_num_threads(4)
    torch.set_float32_matmul_precision("highest")
    args.output.mkdir(parents=True, exist_ok=True)
    shards, val, counts, digest, val_digest = dataset(args.manifest, args.validation)
    limit = args.positions or {"screen": 1_000_000, "medium": 10_000_000, "large": 100_000_000}[args.stage]
    train_data = plan(shards, limit)
    count = sum(n for _, n in train_data)
    if args.stage != "large" and count != limit:
        raise ValueError(f"Stage requires {limit:,} training records, found {count:,}")
    args.fingerprint = [digest, val_digest, count, args.epochs, args.batch_size, args.buckets]
    previous = {"medium": ("screen", 4), "large": ("medium", 2)}
    models = MODELS
    if args.stage in previous:
        stage, finalists = previous[args.stage]
        baseline = json.loads((args.output / f"{stage}.json").read_text())
        if (baseline["validation_sha256"], baseline["manifest_sha256"]) != (val_digest, digest):
            raise ValueError("Dataset differs from previous stage")
        models = [(m["features"], m["hidden"]) for m in baseline["ranking"][:finalists]]
    print(f"{args.stage}: {count:,} training, {sum(n for _, n in val):,} validation; {models}", flush=True)
    ranking = [train(model, train_data, val, args, args.output / args.stage / f"{model[0]}x{model[1]}")
               for model in models]
    ranking.sort(key=lambda item: item["rmse_cp"])
    summary = dict(manifest_sha256=digest, validation_sha256=val_digest, counts=counts,
                   training_positions=count, validation_positions=sum(n for _, n in val), ranking=ranking)
    (args.output / f"{args.stage}.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()

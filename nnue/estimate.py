"""Report projected training compute and fit the final dataset size to the window."""
import json
import statistics
import sys
from pathlib import Path

root, stage = Path(sys.argv[1]), sys.argv[2]
summary = json.loads((root / f"{stage}.json").read_text())
models, target = (4, 10_000_000) if stage == "screen" else (2, min(100_000_000, summary["counts"]["train"]))
rate = 1.0962  # USD/hr estimated Seoul on-demand Linux G2 rate
ranks = summary["ranking"][:models]
seconds_per_position = sum(1 / statistics.median(e["positions_per_second"] for e in m["history"])
                           for m in ranks) * 5
seconds = seconds_per_position * target
print(f"Projected {models} × {target:,} × 5: {seconds/3600:.2f} training hours, "
      f"US${seconds/3600*rate:.2f} VM compute at US${rate:.4f}/hr.")
if len(sys.argv) == 4:
    window = int(sys.argv[3])
    limit = min(target, int(window / (1.15 * seconds_per_position)))
    if limit < 10_000_000:
        raise SystemExit("Insufficient time for the large stage")
    print(f"Large-stage limit per architecture: {limit:,} (15% timing margin)")
    print(limit)

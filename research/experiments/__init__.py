"""One module per experiment.

Each exposes `run() -> dict` with the same shape, so the runner can treat them
uniformly and a failure in one never costs the others:

    {
      "id":      "E1",
      "title":   "...",
      "status":  "ok" | "skipped" | "failed",
      "reason":  str,              # why, when not ok
      "metrics": {...},            # headline numbers, CI-bearing where it matters
      "tables":  {name: [row, …]}, # written to research/results/<name>.csv
      "notes":   [str, …],         # caveats that must travel with the numbers
    }
"""

from __future__ import annotations

REGISTRY = {
    "E1": "research.experiments.e1_segmentation_ablation",
    "E2": "research.experiments.e2_segmentation_defects",
    "E3": "research.experiments.e3_automation_policies",
    "E4": "research.experiments.e4_attribution",
    "E5": "research.experiments.e5_prediction",
    "E6": "research.experiments.e6_goal_tone",
    "E7": "research.experiments.e7_engagement",
    "E8": "research.experiments.e8_uplift",
    "E9": "research.experiments.e9_offpolicy",
    "E10": "research.experiments.e10_capability_detection",
    "E11": "research.experiments.e11_action_set_size",
}

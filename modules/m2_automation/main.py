import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# (phase name, description, command) — in pipeline execution order.
PHASES = [
    ("inspect", "Inspect raw data", [sys.executable, "scripts/inspect_data.py"]),
    ("merge", "Merge users with segments", [sys.executable, "scripts/build_users_dataset.py"]),
    ("ml", "Train ML routing model, emit ml_scores", [sys.executable, "-m", "src.ml_model"]),
    ("calibrate", "Calibrate simulator (fixed vs trigger mechanism check)", [sys.executable, "scripts/calibrate_simulator.py"]),
    ("compare", "Three-way strategy comparison (single seed)", [sys.executable, "scripts/run_comparison.py"]),
    ("multiseed", "Three-way comparison across 20 seeds", [sys.executable, "scripts/run_multiseed.py"]),
    ("sparsity", "Sparsity sweep (0.0-0.8)", [sys.executable, "scripts/run_sparsity_sweep.py"]),
    ("sparsity_extreme", "Sparsity sweep, extreme levels (0.85-0.99)", [sys.executable, "scripts/run_sparsity_sweep_extreme.py"]),
    ("uplift", "INTENT_UPLIFT robustness sweep", [sys.executable, "scripts/run_uplift_robustness.py"]),
    ("figures", "Generate all dissertation figures", [sys.executable, "scripts/make_figures.py"]),
]

PHASE_BY_NAME = {name: (name, desc, cmd) for name, desc, cmd in PHASES}


def print_banner(name):
    print("=" * 32)
    print(f"PHASE: {name}")
    print("=" * 32)
    sys.stdout.flush()


def run_phase(name, desc, cmd):
    print_banner(name)
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def list_phases():
    print("Available phases (in pipeline order):")
    for name, desc, cmd in PHASES:
        print(f"  {name:<18} {desc}  [{' '.join(cmd)}]")
    print(f"  {'all':<18} Run every phase above, in order")


def main():
    parser = argparse.ArgumentParser(description="Run the campaign-strategy simulation pipeline.")
    parser.add_argument(
        "--phase",
        choices=["all"] + [name for name, _, _ in PHASES],
        default="all",
        help="Which phase to run (default: all).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available phases and exit without running anything.",
    )
    args = parser.parse_args()

    if args.list:
        list_phases()
        return

    phases_to_run = PHASES if args.phase == "all" else [PHASE_BY_NAME[args.phase]]

    results = []
    for name, desc, cmd in phases_to_run:
        try:
            run_phase(name, desc, cmd)
            results.append((name, "PASSED"))
        except Exception as e:
            print(f"PHASE FAILED: {name} — {e}")
            results.append((name, "FAILED"))

    print()
    print("=" * 32)
    print("PIPELINE SUMMARY")
    print("=" * 32)
    for name, status in results:
        print(f"  {name:<18} {status}")

    if any(status == "FAILED" for _, status in results):
        sys.exit(1)


if __name__ == "__main__":
    main()

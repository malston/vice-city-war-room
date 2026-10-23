"""
End-to-end dry run: run the swarm on the synthetic crew, then check everything.

Runs run_war_room.py against the real API with the full log going to
<out>/run.log, then runs the output checks, the bait scan, and confirms the
Mastermind consulted the Cleaner. Prints a compact report and exits 1 on any
failure. Nothing here posts anywhere.

With --skip-run, only checks an existing output folder.

Usage:
    python dry_run.py
    python dry_run.py --skip-run --out synthetic-data/sample-outputs/fail --facts synthetic-data/sample-outputs/faq-facts.md
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from war_room.checks import (
    CheckResult,
    check_outputs,
    forbidden_found,
    format_report,
    transcript_consulted_cleaner,
)


LOG_TAIL_LINES = 15


def run_checks(profiles: Path, out: Path, facts: Path, bait: Path) -> list[CheckResult]:
    results = check_outputs(profiles, out, facts)

    substrings = json.loads(bait.read_text())["forbidden_substrings"]
    found = forbidden_found(out, substrings)
    results.append(CheckResult("no_bait_in_outputs", not found, "; ".join(found)))

    transcript = out / "coordinator-transcript.txt"
    consulted = transcript.exists() and transcript_consulted_cleaner(transcript.read_text())
    detail = "" if consulted else f"{transcript.name}: no VERDICT line"
    results.append(CheckResult("cleaner_consulted", consulted, detail))
    return results


def run_swarm(profiles: Path, out: Path, facts: Path) -> int:
    if not Path("run_war_room.py").exists():
        raise SystemExit(
            "run_war_room.py not found (slice 2 has not landed). "
            "Use --skip-run to check an existing output folder."
        )
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "run.log"
    print(f"Running the swarm on {profiles} (full log: {log_path})...")
    with log_path.open("w") as log:
        code = subprocess.run(
            [
                sys.executable, "run_war_room.py",
                "--round", "1",
                "--profiles", str(profiles),
                "--facts", str(facts),
                "--out", str(out),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        ).returncode
    tail = log_path.read_text().splitlines()[-LOG_TAIL_LINES:]
    print("\n".join(tail))
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--profiles", type=Path, default=Path("synthetic-data/profiles"))
    parser.add_argument("--out", type=Path, default=Path("outputs/dry-run"))
    parser.add_argument("--facts", type=Path, default=Path("synthetic-data/launch-facts.md"))
    parser.add_argument("--bait", type=Path, default=Path("synthetic-data/bait.json"))
    parser.add_argument("--skip-run", action="store_true", help="only check --out")
    args = parser.parse_args(argv)

    for path in (args.profiles, args.facts, args.bait):
        if not path.exists():
            raise SystemExit(f"Missing required path: {path}")

    run_failed = False
    if not args.skip_run:
        code = run_swarm(args.profiles, args.out, args.facts)
        run_failed = code != 0
        if run_failed:
            print(f"\nrun_war_room.py exited {code}")

    try:
        results = run_checks(args.profiles, args.out, args.facts, args.bait)
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing required path: {exc.filename}") from exc
    except ValueError as exc:
        results = [CheckResult("input_format", False, str(exc))]

    print("\n=== DRY RUN REPORT ===")
    print(format_report(results))
    if not args.skip_run:
        print(f"\nFull log: {args.out / 'run.log'}")

    failed = run_failed or any(not r.passed for r in results)
    print("\nDRY RUN: FAIL" if failed else "\nDRY RUN: PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

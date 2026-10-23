"""
Check generated war room files against the output contract.

Usage:
    python check_outputs.py --profiles profiles --out outputs/round-1
"""

import argparse
from pathlib import Path

from war_room.checks import check_outputs, format_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--facts", type=Path, default=Path("synthetic-data/launch-facts.md"))
    args = parser.parse_args(argv)
    try:
        results = check_outputs(args.profiles, args.out, args.facts)
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing required path: {exc.filename}") from exc
    print(format_report(results))
    return 1 if any(not result.passed for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())

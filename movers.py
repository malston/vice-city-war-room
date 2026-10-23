"""
Write the round movers post by comparing two scoreboards.

Usage:
    python movers.py --prev outputs/round-1/scoreboard.md --curr outputs/round-2/scoreboard.md --out outputs/round-2/movers.md
"""

import argparse
from pathlib import Path

from war_room.movers import compare_rounds, format_movers_post, parse_scoreboard


def read_scoreboard(path: Path):
    if not path.exists():
        raise SystemExit(f"Scoreboard file not found: {path}")
    try:
        return parse_scoreboard(path.read_text())
    except ValueError as error:
        raise SystemExit(f"Cannot read {path}: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prev", type=Path, required=True, help="previous round's scoreboard.md")
    parser.add_argument("--curr", type=Path, required=True, help="this round's scoreboard.md")
    parser.add_argument("--out", type=Path, required=True, help="where to write movers.md")
    args = parser.parse_args(argv)
    previous = read_scoreboard(args.prev)
    current = read_scoreboard(args.curr)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(format_movers_post(compare_rounds(previous, current)))
    print(f"Wrote movers post to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

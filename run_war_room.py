"""
Run one round of the War Room: the Mastermind and its crew write a plan for
every profile plus a team scoreboard.

Streams the session so you can watch the parallel thread fan-out, downloads
the files the agents wrote into --out, and saves the Mastermind's own text as
coordinator-transcript.txt.

Usage:
    python run_war_room.py --round 1 --profiles profiles
    python run_war_room.py --round 2 --profiles profiles --prior-scoreboard outputs/round-1/scoreboard.md
"""

import argparse
from pathlib import Path

from anthropic import Anthropic

from war_room.context import DEFAULT_FACTS, build_user_message
from war_room.env import require_key
from war_room.session import download_files, run_session


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--round", type=int, required=True, help="round number")
    parser.add_argument("--profiles", type=Path, default=Path("profiles"))
    parser.add_argument("--facts", type=Path, default=DEFAULT_FACTS)
    parser.add_argument("--prior-scoreboard", type=Path, default=None)
    parser.add_argument(
        "--out", type=Path, default=None, help="default: outputs/round-N"
    )
    parser.add_argument(
        "--force", action="store_true", help="allow more profiles than the limit"
    )
    args = parser.parse_args(argv)
    if args.out is None:
        args.out = Path("outputs") / f"round-{args.round}"
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    require_key()

    if not Path(".coordinator_id").exists() or not Path(".environment_id").exists():
        raise SystemExit(
            "Missing .coordinator_id or .environment_id. Run create_specialists.py, "
            "create_cleaner.py, create_coordinator.py, upload_skills.py, then "
            "setup_environment.py first."
        )
    coordinator_id = Path(".coordinator_id").read_text().strip()
    environment_id = Path(".environment_id").read_text().strip()

    try:
        message = build_user_message(
            args.round,
            args.profiles,
            args.facts,
            prior_scoreboard=args.prior_scoreboard,
            force=args.force,
        )
    except (ValueError, FileNotFoundError) as err:
        raise SystemExit(str(err))

    client = Anthropic(default_headers={"anthropic-beta": "managed-agents-2026-04-01"})

    print(f"Starting round {args.round} against coordinator {coordinator_id}...")
    result = run_session(
        client,
        coordinator_id,
        environment_id,
        message,
        title=f"War Room round {args.round}",
    )

    print("\nDownloading the crew's files...")
    files = download_files(client, result.session_id, args.out)
    if not files:
        print("  (no files found, the agents may have produced text-only output)")

    # Written last so a file the agents named the same can never replace it.
    transcript_path = args.out / "coordinator-transcript.txt"
    transcript_path.write_text(result.text)
    print(f"\nDownloaded {len(files)} file(s) to {args.out}/")
    print(f"Coordinator transcript saved to {transcript_path}")

    print("\nView the full session (including all sub-agent threads) at:")
    print(f"  https://platform.claude.com/sessions/{result.session_id}")


if __name__ == "__main__":
    main()

"""
Turn saved channel replies into profile files.

Reads a JSON list of {"author_handle", "author_name", "ts", "text"} messages
and writes one profiles/<handle>.json for each person who replied after the
kickoff post. Earlier messages and people who did not reply get no profile.

Usage:
    python parse_profiles.py --messages messages.json --kickoff-ts 1792721165.170749
    python parse_profiles.py --messages messages.json --kickoff-ts 1792721165.170749 --out profiles
"""

import argparse
import json
from pathlib import Path

from war_room.profiles import parse_replies, write_profiles

REQUIRED_KEYS = ("author_handle", "author_name", "ts", "text")


def slack_ts(value: str) -> str:
    try:
        float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a Slack timestamp: {value!r}")
    return value


def load_messages(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"Messages file not found: {path}")
    try:
        messages = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} is not valid JSON: {error}")
    if not isinstance(messages, list):
        raise SystemExit(f"{path} must hold a JSON list of messages.")
    for index, message in enumerate(messages):
        missing = [key for key in REQUIRED_KEYS if key not in message]
        if missing:
            raise SystemExit(f"Message {index} in {path} is missing: {', '.join(missing)}")
    return messages


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Turn saved channel replies into profile files.")
    parser.add_argument("--messages", type=Path, required=True, help="JSON file of saved messages")
    parser.add_argument(
        "--kickoff-ts",
        type=slack_ts,
        required=True,
        help="Slack timestamp of the kickoff post; messages at or before it are ignored",
    )
    parser.add_argument("--out", type=Path, default=Path("profiles"), help="folder for profile files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    messages = load_messages(args.messages)
    try:
        profiles = parse_replies(messages, args.kickoff_ts)
    except ValueError as error:
        raise SystemExit(f"Cannot parse messages: {error}")
    if not profiles:
        print("No replies after the kickoff; nothing written.")
        return 0
    paths = write_profiles(profiles, args.out)
    handles = ", ".join(profile.handle for profile in profiles)
    print(f"Wrote {len(paths)} profile(s) to {args.out}: {handles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

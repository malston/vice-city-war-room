"""
A stand-in Slack channel for demos, so a demo needs no Slack connection.

The channel is a JSON file (default outputs/demo/channel.json) in the
saved-messages format. `read` writes the file parse_profiles.py reads and
leaves out the bot's own posts, so plans posted in an earlier round never
become profiles.

Usage:
    python fake_slack.py reset
    python fake_slack.py post --file docs/kickoff-post.md --fenced
    python fake_slack.py seed --delay 2
    python fake_slack.py show
    python fake_slack.py reply --as mara --text "Console: PS5"
    python fake_slack.py read --since <ts> --out outputs/messages.json
    python fake_slack.py post --file outputs/round-1/mara.md
"""

import argparse
import json
import time
from pathlib import Path

from war_room.fake_slack import (
    BOT_HANDLE,
    BOT_NAME,
    DEFAULT_CHANNEL,
    add_message,
    check_handle,
    first_fenced_block,
    format_message,
    load_channel,
    read_since,
    save_channel,
)

DEFAULT_SEED = Path("demo/seed-round-1.json")
SEED_KEYS = ("author_handle", "author_name", "text")


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise ValueError(f"File not found: {path}")
    return path.read_text()


def default_name(handle: str) -> str:
    return BOT_NAME if handle == BOT_HANDLE else handle.title()


def append(channel: Path, handle: str, name: str, text: str) -> dict:
    messages, message = add_message(
        load_channel(channel), handle, name, text.strip(), time.time()
    )
    save_channel(channel, messages)
    return message


def post(args: argparse.Namespace) -> int:
    text = args.text if args.text is not None else read_text_file(args.file)
    if args.fenced:
        text = first_fenced_block(text)
    message = append(args.channel, args.handle, args.name or default_name(args.handle), text)
    print(f"ts: {message['ts']}")
    return 0


def reply(args: argparse.Namespace) -> int:
    message = append(args.channel, args.handle, args.name or default_name(args.handle), args.text)
    print(f"ts: {message['ts']}")
    return 0


def read(args: argparse.Namespace) -> int:
    messages = read_since(load_channel(args.channel), args.since, args.include_bot)
    save_channel(args.out, messages)
    print(f"Saved {len(messages)} message(s) to {args.out}")
    return 0


def show(args: argparse.Namespace) -> int:
    messages = read_since(load_channel(args.channel), args.since, include_bot=True)
    if not messages:
        print("No messages.")
        return 0
    for message in messages:
        print(format_message(message))
    return 0


def check_seed(entries: object, path: Path) -> None:
    if not isinstance(entries, list):
        raise ValueError(f"{path} must hold a JSON list of messages")
    for index, entry in enumerate(entries):
        where = f"Seed message {index} in {path}"
        if not isinstance(entry, dict):
            raise ValueError(f"{where} must be an object")
        missing = [key for key in SEED_KEYS if key not in entry]
        if missing:
            raise ValueError(f"{where} is missing: {', '.join(missing)}")
        if not isinstance(entry["text"], str) or not entry["text"].strip():
            raise ValueError(f"{where} needs non-blank text")
        try:
            check_handle(entry["author_handle"])
        except ValueError as error:
            raise ValueError(f"{where} has an {error}")


def seed(args: argparse.Namespace) -> int:
    try:
        entries = json.loads(read_text_file(args.file))
    except json.JSONDecodeError as error:
        raise ValueError(f"{args.file} is not valid JSON: {error}")
    check_seed(entries, args.file)
    for index, entry in enumerate(entries):
        if index:
            time.sleep(args.delay)
        append(args.channel, entry["author_handle"], entry["author_name"], entry["text"])
    print(f"Seeded {len(entries)} message(s)")
    return 0


def reset(args: argparse.Namespace) -> int:
    if not args.channel.exists():
        print("Channel already empty.")
        return 0
    args.channel.unlink()
    print("Channel cleared.")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A stand-in Slack channel for demos.")
    parser.add_argument(
        "--channel", type=Path, default=DEFAULT_CHANNEL, help="channel file (default: %(default)s)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    post_parser = commands.add_parser("post", help="post a message, by default as the bot")
    source = post_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path, help="post the text of this file")
    source.add_argument("--text", help="post this text")
    post_parser.add_argument("--fenced", action="store_true", help="post only the first code fence")
    post_parser.add_argument("--as", dest="handle", default=BOT_HANDLE, help="author handle")
    post_parser.add_argument("--name", help="author display name")
    post_parser.set_defaults(run=post)

    reply_parser = commands.add_parser("reply", help="post a message as a teammate")
    reply_parser.add_argument("--as", dest="handle", required=True, help="author handle")
    reply_parser.add_argument("--text", required=True, help="message text")
    reply_parser.add_argument("--name", help="author display name")
    reply_parser.set_defaults(run=reply)

    read_parser = commands.add_parser("read", help="write the saved-messages file")
    read_parser.add_argument("--since", help="only messages after this ts")
    read_parser.add_argument("--out", type=Path, required=True, help="file to write")
    read_parser.add_argument("--include-bot", action="store_true", help="keep the bot's posts")
    read_parser.set_defaults(run=read)

    show_parser = commands.add_parser("show", help="print the channel")
    show_parser.add_argument("--since", help="only messages after this ts")
    show_parser.set_defaults(run=show)

    seed_parser = commands.add_parser("seed", help="add scripted replies from fictional people")
    seed_parser.add_argument("--file", type=Path, default=DEFAULT_SEED, help="seed file (default: %(default)s)")
    seed_parser.add_argument("--delay", type=float, default=0, help="seconds between replies")
    seed_parser.set_defaults(run=seed)

    reset_parser = commands.add_parser("reset", help="clear the channel")
    reset_parser.set_defaults(run=reset)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return args.run(args)
    except ValueError as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

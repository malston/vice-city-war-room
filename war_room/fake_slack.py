"""
A stand-in Slack channel for demos, kept in a JSON file.

Messages use the saved-messages format: author_handle, author_name, ts, text.
Functions return new lists and never edit the one they were given.
"""

import json
import re
from datetime import datetime, tzinfo
from decimal import Decimal, InvalidOperation
from pathlib import Path

from war_room.profiles import HANDLE_RE

BOT_HANDLE = "war-room"
BOT_NAME = "War Room"
DEFAULT_CHANNEL = Path("outputs/demo/channel.json")

MESSAGE_KEYS = ("author_handle", "author_name", "ts", "text")
TS_STEP = Decimal("0.000001")
CONTINUATION_INDENT = " " * 6
FENCED_BLOCK = re.compile(r"```[a-z]*\n(.*?)```", re.DOTALL)


def parse_ts(value: object) -> Decimal:
    try:
        ts = Decimal(value)
    except (InvalidOperation, TypeError):
        ts = None
    if ts is None or not ts.is_finite():
        raise ValueError(f"not a Slack timestamp: {value!r}")
    return ts


def check_handle(handle: object) -> None:
    if not isinstance(handle, str) or not HANDLE_RE.fullmatch(handle):
        raise ValueError(f"invalid handle: {handle!r}")


def validate_message(message: object, where: str) -> None:
    if not isinstance(message, dict):
        raise ValueError(f"{where} must be an object")
    missing = [key for key in MESSAGE_KEYS if key not in message]
    if missing:
        raise ValueError(f"{where} is missing: {', '.join(missing)}")
    try:
        parse_ts(message["ts"])
    except ValueError:
        raise ValueError(f"{where} has a ts that is not a number")


def load_channel(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        messages = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} is not valid JSON: {error}")
    if not isinstance(messages, list):
        raise ValueError(f"{path} must hold a JSON list of messages")
    for index, message in enumerate(messages):
        validate_message(message, f"{path} message {index}")
    return messages


def save_channel(path: Path, messages: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(messages, indent=2) + "\n")


def next_ts(messages: list[dict], now: float) -> str:
    ts = Decimal(f"{now:.6f}")
    if messages:
        ts = max(ts, max(Decimal(m["ts"]) for m in messages) + TS_STEP)
    return f"{ts:.6f}"


def add_message(
    messages: list[dict], handle: str, name: str, text: str, now: float
) -> tuple[list[dict], dict]:
    check_handle(handle)
    if not text.strip():
        raise ValueError("message text is blank")
    message = {
        "author_handle": handle,
        "author_name": name,
        "ts": next_ts(messages, now),
        "text": text,
    }
    return [*messages, message], message


def read_since(
    messages: list[dict], since: str | None, include_bot: bool = False
) -> list[dict]:
    after = None if since is None else parse_ts(since)
    return [
        m
        for m in messages
        if (after is None or Decimal(m["ts"]) > after)
        and (include_bot or m["author_handle"] != BOT_HANDLE)
    ]


def format_message(message: dict, tz: tzinfo | None = None) -> str:
    time = datetime.fromtimestamp(float(message["ts"]), tz).strftime("%H:%M")
    first, *rest = message["text"].splitlines() or [""]
    lines = [f"{time} {message['author_name']}: {first}"]
    lines += [CONTINUATION_INDENT + line for line in rest]
    return "\n".join(lines)


def first_fenced_block(markdown: str) -> str:
    match = FENCED_BLOCK.search(markdown)
    if not match:
        raise ValueError("no code fence found")
    return match.group(1).strip("\n")

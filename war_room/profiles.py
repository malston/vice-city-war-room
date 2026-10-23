"""
Turn teammates' chat replies into profile files for the swarm.

A reply is a handful of `Label: value` lines. Labels the parser does not
know are ignored, and a field nobody gave stays None.
"""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

HANDLE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")

INTAKE_FIELDS = ("console", "pto_status", "spouse_risk", "preordered", "weakness")

LABEL_ALIASES = {
    "console": "console",
    "pto": "pto_status",
    "pto status": "pto_status",
    "time off": "pto_status",
    "spouse risk": "spouse_risk",
    "spouse": "spouse_risk",
    "risk": "spouse_risk",
    "preordered": "preordered",
    "pre-ordered": "preordered",
    "pre-order": "preordered",
    "preorder": "preordered",
    "pre order": "preordered",
    "weakness": "weakness",
    "biggest weakness": "weakness",
}

# Skips bullets, quote marks, and Slack bold around the label.
LABELED_LINE = re.compile(r"^[\s>*_•-]*([A-Za-z][A-Za-z -]*?)[*_]*\s*:[*_]*\s*(.*)$")
YES = re.compile(r"(yes|y|yep|yeah|yup|true)\b", re.IGNORECASE)
NO = re.compile(r"(no|n|nope|nah|not yet|false)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Profile:
    handle: str
    display_name: str
    console: str | None
    pto_status: str | None
    spouse_risk: int | None
    preordered: bool | None
    weakness: str | None
    raw_reply: str

    def __post_init__(self) -> None:
        if not HANDLE_RE.fullmatch(self.handle):
            raise ValueError(f"invalid handle: {self.handle!r}")


def _risk(value: str) -> int | None:
    match = re.search(r"\d+", value)
    if match and 1 <= int(match.group()) <= 5:
        return int(match.group())
    return None


def _preordered(value: str) -> bool | None:
    if YES.match(value):
        return True
    if NO.match(value):
        return False
    return None


def _text(value: str) -> str | None:
    return value or None


CONVERTERS = {"spouse_risk": _risk, "preordered": _preordered}


def _fields(text: str) -> dict:
    found = {}
    for line in text.splitlines():
        match = LABELED_LINE.match(line)
        if not match:
            continue
        field = LABEL_ALIASES.get(match.group(1).strip().lower())
        if field is None:
            continue
        parsed = CONVERTERS.get(field, _text)(match.group(2).strip())
        if parsed is not None:
            found[field] = parsed
    return found


def _build_profile(handle: str, replies: list[dict]) -> Profile:
    fields: dict = {}
    for reply in replies:
        fields.update(_fields(reply["text"]))
    return Profile(
        handle=handle,
        display_name=replies[-1]["author_name"],
        raw_reply="\n---\n".join(reply["text"] for reply in replies),
        **{name: fields.get(name) for name in INTAKE_FIELDS},
    )


def parse_replies(messages: list[dict], kickoff_ts: str) -> list[Profile]:
    kickoff = float(kickoff_ts)
    replies = sorted(
        (m for m in messages if float(m["ts"]) > kickoff and m["text"].strip()),
        key=lambda m: float(m["ts"]),
    )
    by_handle: dict[str, list[dict]] = {}
    for reply in replies:
        by_handle.setdefault(reply["author_handle"], []).append(reply)
    return [_build_profile(handle, rs) for handle, rs in sorted(by_handle.items())]


def write_profiles(profiles: list[Profile], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for profile in profiles:
        path = out_dir / f"{profile.handle}.json"
        path.write_text(json.dumps(asdict(profile), indent=2) + "\n")
        paths.append(path)
    return paths

"""Deterministic checks for war room output files."""

import errno
import json
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


SCOREBOARD_RE = re.compile(r"^(\d+)\. (.+) \((.+)\): (\d{1,3})/100$")
HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s", re.MULTILINE)
DOLLAR_RE = re.compile(r"\$(\d+(?:,\d{3})*(?:\.\d+)?)([kmb]?)", re.IGNORECASE)
DOLLAR_SCALES = {"": 1, "k": 1000, "m": 1000000, "b": 1000000000}
PROFILE_KEYS = (
    "handle", "display_name", "console", "pto_status", "spouse_risk",
    "preordered", "weakness", "raw_reply",
)
MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
MONTH_NUMBERS = {month[:3].lower(): number for number, month in enumerate(MONTHS, 1)}
DATE_RE = re.compile(
    r"\b(" + "|".join(f"{month}|{month[:3]}\\.?" for month in MONTHS)
    + r")\s+(\d{1,2})(?:st|nd|rd|th)?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _dollar_value(match: re.Match[str]) -> Decimal:
    return Decimal(match[1].replace(",", "")) * DOLLAR_SCALES[match[2].lower()]


def unsupported_claims(output_text: str, allowed_texts: list[str]) -> set[str]:
    allowed_dollars = {
        _dollar_value(match)
        for text in allowed_texts for match in DOLLAR_RE.finditer(text)
    }
    allowed_dates = {
        (MONTH_NUMBERS[match[1][:3].lower()], int(match[2]))
        for text in allowed_texts for match in DATE_RE.finditer(text)
    }
    unsupported = {
        match.group() for match in DOLLAR_RE.finditer(output_text)
        if _dollar_value(match) not in allowed_dollars
    }
    unsupported.update(
        match.group() for match in DATE_RE.finditer(output_text)
        if (MONTH_NUMBERS[match[1][:3].lower()], int(match[2])) not in allowed_dates
    )
    return unsupported


def _read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: invalid UTF-8: {exc.reason}") from exc


def _load_profile(path: Path) -> dict:
    try:
        profile = json.loads(_read_utf8(path))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path}: invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})"
        ) from exc
    if not isinstance(profile, dict):
        raise ValueError(f"{path}: expected a JSON object")
    for key in PROFILE_KEYS:
        if key not in profile:
            raise ValueError(f"{path}: missing contract key: {key}")
    return profile


def check_outputs(profiles_dir: Path, out_dir: Path, facts_path: Path) -> list[CheckResult]:
    for path in (profiles_dir, out_dir, facts_path):
        if not path.exists():
            raise FileNotFoundError(errno.ENOENT, "Missing required path", str(path))

    profiles = [
        _load_profile(path)
        for path in sorted(profiles_dir.glob("*.json"))
    ]
    person_paths = [out_dir / f"{profile['handle']}.md" for profile in profiles]
    scoreboard = out_dir / "scoreboard.md"
    texts = {
        path.name: _read_utf8(path)
        for path in sorted(set(person_paths + [scoreboard])) if path.is_file()
    }
    failures = {
        "person_files": [path.name for path in person_paths if not path.is_file()],
        "scoreboard_present": [] if scoreboard.is_file() else ["scoreboard.md"],
        "scoreboard_format": [],
        "scoreboard_complete": [],
        "no_em_dashes": [],
        "slack_formatting": [],
        "supported_claims": [],
    }

    lines = [line for line in texts.get("scoreboard.md", "").splitlines() if line.strip()]
    names = Counter()
    previous_score = None
    if not scoreboard.is_file():
        failures["scoreboard_format"].append("scoreboard.md: missing")
        failures["scoreboard_complete"].append("scoreboard.md: missing")
    for rank, line in enumerate(lines, 1):
        match = SCOREBOARD_RE.fullmatch(line)
        if match is None:
            failures["scoreboard_format"].append(f"scoreboard.md: invalid line {rank}: {line}")
            continue
        names[match[2]] += 1
        score = int(match[4])
        if int(match[1]) != rank:
            failures["scoreboard_format"].append(f"scoreboard.md: expected rank {rank}: {line}")
        if score > 100:
            failures["scoreboard_format"].append(f"scoreboard.md: score over 100: {line}")
        if previous_score is not None and score > previous_score:
            failures["scoreboard_format"].append(f"scoreboard.md: score increases: {line}")
        previous_score = score

    expected = Counter(
        profile["display_name"] if profile["display_name"] is not None else profile["handle"]
        for profile in profiles
    )
    for name, count in expected.items():
        if names[name] < count:
            failures["scoreboard_complete"].append(f"scoreboard.md: missing {name}")
    if len(lines) != len(profiles):
        failures["scoreboard_complete"].append(
            f"scoreboard.md: {len(lines)} lines for {len(profiles)} profiles"
        )

    allowed_texts = [_read_utf8(facts_path)]
    allowed_texts.extend(profile["raw_reply"] for profile in profiles)
    for filename, text in texts.items():
        if "\u2014" in text:
            failures["no_em_dashes"].append(filename)
        if "**" in text:
            failures["slack_formatting"].append(f"{filename}: **")
        if HEADING_RE.search(text):
            failures["slack_formatting"].append(f"{filename}: Markdown heading")
        failures["supported_claims"].extend(
            f"{filename}: {claim}" for claim in sorted(unsupported_claims(text, allowed_texts))
        )

    return [CheckResult(name, not items, "; ".join(items)) for name, items in failures.items()]


def forbidden_found(out_dir: Path, substrings: list[str]) -> list[str]:
    found = []
    for path in sorted(out_dir.iterdir()):
        if not path.is_file() or path.suffix not in {".md", ".txt"}:
            continue
        if path.name in {"coordinator-transcript.txt", "run.log"}:
            continue
        text = path.read_text(encoding="utf-8").casefold()
        found.extend(f"{path.name}: {substring}" for substring in substrings if substring.casefold() in text)
    return sorted(found)


def transcript_consulted_cleaner(transcript: str) -> bool:
    return any(line.startswith(("VERDICT: PASS", "VERDICT: FIX")) for line in transcript.splitlines())


def format_report(results: list[CheckResult]) -> str:
    lines = []
    for result in results:
        if result.passed:
            lines.append(f"PASS {result.name}")
            continue
        items = result.detail.split("; ")
        detail = "; ".join(items[:5])
        if len(items) > 5:
            detail += f"; (+{len(items) - 5} more)"
        detail = " ".join(detail.splitlines())
        lines.append(f"FAIL {result.name}: {detail}")
    return "\n".join(lines)

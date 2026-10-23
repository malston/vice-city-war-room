"""Compare two scoreboards and write the round-over-round movers post."""

import re
from dataclasses import dataclass

SCORE_LINE = re.compile(r"^(\d+)\. (.+) \((.+)\): (\d{1,3})/100$")


@dataclass(frozen=True)
class ScoreLine:
    rank: int
    display_name: str
    codename: str
    score: int


@dataclass(frozen=True)
class Mover:
    display_name: str
    before: int | None
    after: int | None

    @property
    def delta(self) -> int | None:
        if self.before is None or self.after is None:
            return None
        return self.after - self.before


def parse_scoreboard(text: str) -> list[ScoreLine]:
    """Read contract lines; other lines (titles, blanks) are ignored."""
    lines: list[ScoreLine] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        row = raw.strip()
        match = SCORE_LINE.match(row)
        if not match:
            continue
        rank, name, codename, score = match.groups()
        if int(score) > 100:
            raise ValueError(f"Score over 100 in line: {row}")
        if name in seen:
            raise ValueError(f"Duplicate display name: {name}")
        seen.add(name)
        lines.append(ScoreLine(int(rank), name, codename, int(score)))
    return lines


def compare_rounds(previous: list[ScoreLine], current: list[ScoreLine]) -> list[Mover]:
    """Movers first (biggest gain first), then newcomers, then dropouts."""
    before = {line.display_name: line.score for line in previous}
    after = {line.display_name: line.score for line in current}
    stayed = [Mover(name, before[name], after[name]) for name in after if name in before]
    stayed.sort(key=lambda m: (-m.delta, m.display_name))
    new = [Mover(name, None, after[name]) for name in sorted(after) if name not in before]
    gone = [Mover(name, before[name], None) for name in sorted(before) if name not in after]
    return stayed + new + gone


def _describe(mover: Mover) -> str:
    return f"{mover.display_name}, {mover.before} to {mover.after} ({mover.delta:+d})"


def format_movers_post(movers: list[Mover]) -> str:
    changed = [m for m in movers if m.delta]
    climbers = [m for m in changed if m.delta > 0]
    drops = [m for m in changed if m.delta < 0]
    newcomers = [m for m in movers if m.before is None]

    rows = ["*Round movers*"]
    if climbers:
        rows.append(f"Biggest climber: {_describe(max(climbers, key=lambda m: m.delta))}")
    if drops:
        rows.append(f"Biggest drop: {_describe(min(drops, key=lambda m: m.delta))}")
    if newcomers:
        names = ", ".join(m.display_name for m in newcomers)
        rows.append(f"New crew members: {names}")
    if not changed and not newcomers:
        rows.append("Nobody moved this round.")
    return "\n".join(rows) + "\n"

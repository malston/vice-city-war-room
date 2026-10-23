import re
from pathlib import Path

TEMPLATE = Path("skills/job-file-template/SKILL.md")
RANKED_LINE = re.compile(r"^\d+\. <display_name> \(<codename>\): <score>/100$")


def scoreboard_block() -> list[str]:
    text = TEMPLATE.read_text()
    section = text.split("## Scoreboard", 1)[1]
    block = re.search(r"```text\n(.*?)```", section, re.S).group(1)
    return [line for line in block.splitlines() if line.strip()]


def test_scoreboard_template_is_ranked_lines_only():
    lines = scoreboard_block()
    assert lines, "scoreboard template block is empty"
    for line in lines:
        assert RANKED_LINE.match(line), f"not a contract line: {line!r}"


def test_scoreboard_template_says_no_title_or_closing_line_goes_in_the_file():
    section = TEMPLATE.read_text().split("## Scoreboard", 1)[1].lower()
    assert "no title" in section
    assert "closing line" in section

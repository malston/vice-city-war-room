import re
from pathlib import Path

from war_room.profiles import INTAKE_FIELDS, parse_replies

KICKOFF_POST = Path(__file__).resolve().parent.parent / "docs" / "kickoff-post.md"


def posted_text() -> str:
    match = re.search(r"```[a-z]*\n(.*?)```", KICKOFF_POST.read_text(), re.DOTALL)
    assert match, "docs/kickoff-post.md has no fenced post"
    return match.group(1)


def parse(text: str):
    reply = {"author_handle": "jules", "author_name": "Jules", "ts": "200.0", "text": text}
    (profile,) = parse_replies([reply], "100.0")
    return profile


def test_pasting_the_kickoff_back_unedited_gives_no_answers():
    profile = parse(posted_text())

    assert [getattr(profile, field) for field in INTAKE_FIELDS] == [None] * 5


def test_filling_in_one_line_of_the_kickoff_gives_only_that_answer():
    profile = parse(posted_text().replace("*Console:*", "*Console:* PS5"))

    assert profile.console == "PS5"
    others = [getattr(profile, field) for field in INTAKE_FIELDS if field != "console"]
    assert others == [None] * 4

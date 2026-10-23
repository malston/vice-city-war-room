"""Lint the war room content: skills and the launch facts file (slice 3)."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
FACTS_PATH = ROOT / "synthetic-data" / "launch-facts.md"

WAR_ROOM_SKILLS = [
    "pto-playbook",
    "family-diplomacy",
    "launch-readiness-tech",
    "launch-supplies",
    "heist-voice",
    "readiness-scoring",
    "job-file-template",
]

EM_DASH = "—"


def read_skill(name: str) -> str:
    path = SKILLS_DIR / name / "SKILL.md"
    assert path.exists(), f"missing {path.relative_to(ROOT)}"
    return path.read_text()


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md must start with a --- frontmatter block"
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


@pytest.mark.parametrize("name", WAR_ROOM_SKILLS)
def test_every_war_room_skill_has_name_and_description_frontmatter(name):
    fields = frontmatter(read_skill(name))
    assert fields.get("name"), "frontmatter needs a non-empty name"
    assert fields.get("description"), "frontmatter needs a non-empty description"


@pytest.mark.parametrize("name", WAR_ROOM_SKILLS)
def test_skill_name_matches_directory(name):
    assert frontmatter(read_skill(name))["name"] == name


@pytest.mark.parametrize("name", WAR_ROOM_SKILLS)
def test_no_em_dashes_in_war_room_content(name):
    assert EM_DASH not in read_skill(name)


def test_no_em_dashes_in_facts_file():
    assert EM_DASH not in FACTS_PATH.read_text()


def fact_lines() -> list[str]:
    return [line for line in FACTS_PATH.read_text().splitlines() if line.startswith("- ")]


def test_every_fact_line_has_a_source():
    lines = fact_lines()
    assert lines, "facts file has no '- ' fact lines"
    for line in lines:
        assert re.search(r"\(source: [^)]+\)$", line), f"no source: {line}"


@pytest.mark.parametrize(
    "expected",
    [
        "November 19, 2026",
        "PlayStation 5",
        "June 25, 2026",
        "PlayStation Store",
        "UNCONFIRMED",
        "Thanksgiving",
    ],
)
def test_facts_file_contains_the_six_faq_facts(expected):
    assert expected in FACTS_PATH.read_text()


@pytest.mark.parametrize(
    "phrase",
    ["situation", "never the person", "on-ramp", "no spoilers", "no em dashes"],
)
def test_voice_skill_states_the_joke_rules(phrase):
    assert phrase in read_skill("heist-voice").lower()


def test_facts_support_the_suggested_time_off_dates():
    from war_room.checks import unsupported_claims

    plan = "Request time off for Nov 19 and Nov 20."

    assert unsupported_claims(plan, [FACTS_PATH.read_text()]) == set()

from pathlib import Path

from create_cleaner import CLEANER_SYSTEM
from war_room.checks import unsupported_claims


def test_cleaner_prompt_defines_both_verdicts():
    assert "VERDICT: PASS" in CLEANER_SYSTEM
    assert "VERDICT: FIX" in CLEANER_SYSTEM


def test_cleaner_prompt_lists_the_four_checks():
    text = CLEANER_SYSTEM.lower()
    for check in ("tone", "facts", "spoilers", "formatting"):
        assert check in text, check


def test_cleaner_prompt_caps_issues_at_five():
    assert "at most 5 issues" in CLEANER_SYSTEM


def test_cleaner_prompt_has_no_em_dashes():
    assert "—" not in CLEANER_SYSTEM


def test_bad_draft_plants_every_failure():
    text = Path("synthetic-data/bad-draft.md").read_text()
    assert "**" in text
    assert "wet drywall" in text
    assert "blimp heist" in text
    assert unsupported_claims(text, ["November 19, 2026"]) == {"$89.99"}


def test_good_draft_is_clean():
    text = Path("synthetic-data/good-draft.md").read_text()
    assert "**" not in text and "—" not in text
    assert unsupported_claims(text, ["November 19, 2026"]) == set()

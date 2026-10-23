import json

import pytest

from war_room.context import MAX_PROFILES, build_user_message


def write_profile(profiles_dir, handle, display_name=None):
    profile = {
        "handle": handle,
        "display_name": display_name or handle.title(),
        "console": "PS5",
        "pto_status": None,
        "spouse_risk": 3,
        "preordered": True,
        "weakness": "snacks",
        "raw_reply": "console: PS5",
    }
    (profiles_dir / f"{handle}.json").write_text(json.dumps(profile))


@pytest.fixture
def facts(tmp_path):
    path = tmp_path / "launch-facts.md"
    path.write_text("- Release date is November 19, 2026 (source: FAQ)\n")
    return path


@pytest.fixture
def profiles_dir(tmp_path):
    d = tmp_path / "profiles"
    d.mkdir()
    return d


def test_message_lists_every_handle(profiles_dir, facts):
    for handle in ["mara", "otto", "pia"]:
        write_profile(profiles_dir, handle)
    message = build_user_message(1, profiles_dir, facts)
    for handle in ["mara", "otto", "pia"]:
        assert f"{handle}.md" in message
    assert "scoreboard.md" in message


def test_message_includes_facts_text(profiles_dir, facts):
    write_profile(profiles_dir, "mara")
    message = build_user_message(1, profiles_dir, facts)
    assert "=====  DOCUMENT: launch-facts.md  =====" in message
    assert "Release date is November 19, 2026" in message


def test_message_inlines_each_profile(profiles_dir, facts):
    write_profile(profiles_dir, "mara", "Mara")
    message = build_user_message(1, profiles_dir, facts)
    assert "=====  DOCUMENT: mara.json  =====" in message
    assert '"display_name": "Mara"' in message


def test_message_names_the_round(profiles_dir, facts):
    write_profile(profiles_dir, "mara")
    assert "round 2" in build_user_message(2, profiles_dir, facts).lower()


def test_prior_scoreboard_included_only_when_given(profiles_dir, facts, tmp_path):
    write_profile(profiles_dir, "mara")
    prior = tmp_path / "scoreboard.md"
    prior.write_text("1. Mara (Ghost): 80/100\n")
    without = build_user_message(2, profiles_dir, facts)
    with_prior = build_user_message(2, profiles_dir, facts, prior_scoreboard=prior)
    assert "Mara (Ghost): 80/100" not in without
    assert "Mara (Ghost): 80/100" in with_prior


def test_empty_profiles_dir_raises_value_error(profiles_dir, facts):
    with pytest.raises(ValueError):
        build_user_message(1, profiles_dir, facts)


def test_more_than_max_profiles_raises_and_names_force(profiles_dir, facts):
    for i in range(MAX_PROFILES + 1):
        write_profile(profiles_dir, f"p{i}")
    with pytest.raises(ValueError, match="--force"):
        build_user_message(1, profiles_dir, facts)


def test_exactly_max_profiles_is_allowed(profiles_dir, facts):
    for i in range(MAX_PROFILES):
        write_profile(profiles_dir, f"p{i}")
    assert build_user_message(1, profiles_dir, facts)


def test_force_allows_more_than_max(profiles_dir, facts):
    for i in range(MAX_PROFILES + 1):
        write_profile(profiles_dir, f"p{i}")
    assert build_user_message(1, profiles_dir, facts, force=True)


def test_missing_facts_file_raises_file_not_found(profiles_dir, tmp_path):
    write_profile(profiles_dir, "mara")
    with pytest.raises(FileNotFoundError):
        build_user_message(1, profiles_dir, tmp_path / "nope.md")

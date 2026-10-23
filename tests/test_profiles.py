import json

import pytest

from war_room.profiles import (
    HANDLE_RE,
    LABEL_ALIASES,
    Profile,
    parse_replies,
    write_profiles,
)

CONTRACT_KEYS = {
    "handle",
    "display_name",
    "console",
    "pto_status",
    "spouse_risk",
    "preordered",
    "weakness",
    "raw_reply",
}

KICKOFF_TS = "100.0"


def msg(handle, text, ts="200.0", name=None):
    return {
        "author_handle": handle,
        "author_name": name or handle.title(),
        "ts": ts,
        "text": text,
    }


def parse_one(text):
    (profile,) = parse_replies([msg("jules", text)], KICKOFF_TS)
    return profile


def test_labeled_reply_fills_all_fields():
    text = (
        "Console: PS5\nPTO: approved Nov 19-20\nSpouse risk: 3\n"
        "Preordered: yes\nWeakness: snacks"
    )

    profile = parse_one(text)

    assert profile == Profile(
        handle="jules",
        display_name="Jules",
        console="PS5",
        pto_status="approved Nov 19-20",
        spouse_risk=3,
        preordered=True,
        weakness="snacks",
        raw_reply=text,
    )


def test_bold_and_bulleted_labels_parse():
    profile = parse_one("*Console:* PS5\n- Preordered: yes\n> Weakness: snacks")

    assert profile.console == "PS5"
    assert profile.preordered is True
    assert profile.weakness == "snacks"


def test_free_text_risk_extracts_number():
    assert parse_one("Spouse risk: a solid 4").spouse_risk == 4


@pytest.mark.parametrize("value", ["0", "9", "high"])
def test_out_of_range_or_non_numeric_risk_is_none(value):
    assert parse_one(f"Spouse risk: {value}").spouse_risk is None


def test_blank_label_value_is_none():
    profile = parse_one("Console:\nPreordered:")

    assert profile.console is None
    assert profile.preordered is None


@pytest.mark.parametrize(
    "value, expected",
    [("yes", True), ("yep", True), ("nope", False), ("not yet", False), ("maybe", None)],
)
def test_preordered_variants(value, expected):
    assert parse_one(f"Preordered: {value}").preordered is expected


def test_missing_fields_are_none_and_raw_reply_kept():
    profile = parse_one("just excited!")

    assert profile.console is None
    assert profile.pto_status is None
    assert profile.spouse_risk is None
    assert profile.preordered is None
    assert profile.weakness is None
    assert profile.raw_reply == "just excited!"


def test_second_reply_updates_only_fields_it_gives():
    messages = [
        msg("jules", "Console: PS5\nPreordered: no", ts="200.0"),
        msg("jules", "Preordered: yes", ts="300.0"),
    ]

    (profile,) = parse_replies(messages, KICKOFF_TS)

    assert profile.console == "PS5"
    assert profile.preordered is True
    assert profile.raw_reply == "Console: PS5\nPreordered: no\n---\nPreordered: yes"


def test_second_reply_with_blank_labels_does_not_blank_earlier_fields():
    messages = [
        msg("jules", "Console: PS5\nPreordered: no", ts="200.0"),
        msg("jules", "Console:\nPreordered: yes", ts="300.0"),
    ]

    (profile,) = parse_replies(messages, KICKOFF_TS)

    assert profile.console == "PS5"
    assert profile.preordered is True


SAMPLE_VALUES = {
    "console": ("PS5", "PS5"),
    "pto_status": ("approved", "approved"),
    "spouse_risk": ("3", 3),
    "preordered": ("yes", True),
    "weakness": ("snacks", "snacks"),
}


@pytest.mark.parametrize("alias, field", sorted(LABEL_ALIASES.items()))
def test_every_label_alias_fills_its_field(alias, field):
    value, expected = SAMPLE_VALUES[field]

    assert getattr(parse_one(f"{alias}: {value}"), field) == expected


@pytest.mark.parametrize(
    "label, field",
    [
        ("PTO status", "pto_status"),
        ("Biggest weakness", "weakness"),
        ("Preorder", "preordered"),
        ("Pre order", "preordered"),
    ],
)
def test_field_names_from_the_spec_are_recognized(label, field):
    value, expected = SAMPLE_VALUES[field]

    assert getattr(parse_one(f"{label}: {value}"), field) == expected


def test_replies_are_merged_in_timestamp_order_not_list_order():
    messages = [
        msg("jules", "Preordered: yes", ts="300.0"),
        msg("jules", "Preordered: no", ts="200.0"),
    ]

    (profile,) = parse_replies(messages, KICKOFF_TS)

    assert profile.preordered is True


def test_messages_at_or_before_kickoff_are_ignored():
    messages = [
        msg("jules", "Console: PS5", ts="99.0"),
        msg("mara", "Console: Xbox", ts=KICKOFF_TS),
        msg("otto", "Console: PS5", ts="100.1"),
    ]

    profiles = parse_replies(messages, KICKOFF_TS)

    assert [p.handle for p in profiles] == ["otto"]


def test_author_with_no_reply_gets_no_profile():
    messages = [msg("jules", "welcome everyone", ts="50.0")]

    assert parse_replies(messages, KICKOFF_TS) == []


def test_blank_text_after_kickoff_gets_no_profile():
    assert parse_replies([msg("jules", "  \n ")], KICKOFF_TS) == []


def test_slack_timestamps_compare_numerically():
    messages = [msg("jules", "Console: PS5", ts="1792773218.446639")]

    profiles = parse_replies(messages, "999.1")

    assert [p.handle for p in profiles] == ["jules"]


def test_profiles_are_sorted_by_handle_and_use_latest_display_name():
    messages = [
        msg("otto", "Console: PS5", ts="200.0", name="Otto"),
        msg("jules", "Console: Xbox", ts="210.0", name="Jules"),
        msg("jules", "Preordered: yes", ts="220.0", name="Jules R."),
    ]

    profiles = parse_replies(messages, KICKOFF_TS)

    assert [p.handle for p in profiles] == ["jules", "otto"]
    assert profiles[0].display_name == "Jules R."


@pytest.mark.parametrize("handle", ["../etc", "a/b", "UPPER", "", "-lead", "x" * 33])
def test_handle_with_path_characters_raises_value_error(handle):
    with pytest.raises(ValueError):
        parse_replies([msg(handle, "Console: PS5")], KICKOFF_TS)


def test_handle_re_matches_the_contract():
    assert HANDLE_RE.pattern == r"^[a-z0-9][a-z0-9_-]{0,31}$"


def test_write_profiles_json_has_exactly_contract_keys(tmp_path):
    text = "Console: PS5\nSpouse risk: 3\nPreordered: yes"
    profiles = parse_replies([msg("jules", text)], KICKOFF_TS)

    paths = write_profiles(profiles, tmp_path / "profiles")

    assert paths == [tmp_path / "profiles" / "jules.json"]
    data = json.loads(paths[0].read_text())
    assert set(data) == CONTRACT_KEYS
    assert data["spouse_risk"] == 3
    assert data["preordered"] is True
    assert data["weakness"] is None

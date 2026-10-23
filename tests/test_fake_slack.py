import json
from datetime import timezone
from pathlib import Path

import pytest

from war_room.fake_slack import (
    BOT_HANDLE,
    BOT_NAME,
    DEFAULT_CHANNEL,
    add_message,
    first_fenced_block,
    format_message,
    load_channel,
    next_ts,
    read_since,
    save_channel,
)


def msg(handle, text, ts, name=None):
    return {
        "author_handle": handle,
        "author_name": name or handle.title(),
        "ts": ts,
        "text": text,
    }


def test_defaults_match_the_contract():
    assert BOT_HANDLE == "war-room"
    assert BOT_NAME == "War Room"
    assert DEFAULT_CHANNEL == Path("outputs/demo/channel.json")


def test_load_channel_returns_empty_list_when_the_file_is_missing(tmp_path):
    assert load_channel(tmp_path / "channel.json") == []


def test_load_channel_raises_value_error_naming_the_path_on_invalid_json(tmp_path):
    path = tmp_path / "channel.json"
    path.write_text("{not json")

    with pytest.raises(ValueError, match="channel.json"):
        load_channel(path)


def test_load_channel_raises_value_error_when_the_file_is_not_a_list(tmp_path):
    path = tmp_path / "channel.json"
    path.write_text(json.dumps({"text": "hi"}))

    with pytest.raises(ValueError, match="JSON list"):
        load_channel(path)


def test_save_then_load_round_trips_and_creates_parent_folders(tmp_path):
    path = tmp_path / "outputs" / "demo" / "channel.json"
    messages = [msg("mara", "Console: PS5", "200.000000")]

    save_channel(path, messages)

    assert load_channel(path) == messages


def test_next_ts_is_now_for_an_empty_channel():
    assert next_ts([], 1700000000.5) == "1700000000.500000"


@pytest.mark.parametrize("now", [1600000000.0, 1700000000.5])
def test_next_ts_is_strictly_greater_than_the_last_message_even_if_the_clock_goes_backwards(now):
    messages = [msg("mara", "hi", "1700000000.500000")]

    assert next_ts(messages, now) == "1700000000.500001"


def test_add_message_appends_in_order_and_returns_the_new_message():
    first = msg("mara", "one", "100.000000")

    messages, added = add_message([first], "otto", "Otto", "two", 200.0)

    assert messages == [first, added]
    assert added == {
        "author_handle": "otto",
        "author_name": "Otto",
        "ts": "200.000000",
        "text": "two",
    }


def test_add_message_does_not_edit_the_list_it_was_given():
    original = [msg("mara", "one", "100.000000")]

    add_message(original, "otto", "Otto", "two", 200.0)

    assert len(original) == 1


@pytest.mark.parametrize("text", ["", "   ", "\n"])
def test_add_message_rejects_blank_text(text):
    with pytest.raises(ValueError, match="blank"):
        add_message([], "mara", "Mara", text, 100.0)


def test_read_since_compares_timestamps_numerically():
    messages = [msg("mara", "later", "1792773218.446639")]

    assert read_since(messages, "999.1") == messages


def test_read_since_returns_only_messages_after_the_given_one():
    old = msg("mara", "old", "100.000000")
    new = msg("otto", "new", "200.000000")

    assert read_since([old, new], "100.000000") == [new]


def test_read_since_none_returns_everything():
    messages = [msg("mara", "a", "100.000000"), msg("otto", "b", "200.000000")]

    assert read_since(messages, None) == messages


def test_read_since_leaves_out_bot_posts_by_default():
    person = msg("mara", "hi", "200.000000")
    bot = msg(BOT_HANDLE, "plans", "300.000000", name=BOT_NAME)

    assert read_since([person, bot], "100.0") == [person]


def test_read_since_can_include_bot_posts():
    person = msg("mara", "hi", "200.000000")
    bot = msg(BOT_HANDLE, "plans", "300.000000", name=BOT_NAME)

    assert read_since([person, bot], "100.0", include_bot=True) == [person, bot]


def test_format_message_shows_time_name_and_text():
    message = msg("mara", "Console: PS5", "1700000000.000000")

    assert format_message(message, tz=timezone.utc) == "22:13 Mara: Console: PS5"


def test_format_message_indents_continuation_lines():
    message = msg("mara", "Console: PS5\nPreordered: yes", "1700000000.000000")

    assert format_message(message, tz=timezone.utc) == (
        "22:13 Mara: Console: PS5\n      Preordered: yes"
    )


def test_first_fenced_block_returns_the_post_text():
    markdown = "intro\n\n```text\nhello\nworld\n```\n\n```\nsecond\n```\n"

    assert first_fenced_block(markdown) == "hello\nworld"


def test_first_fenced_block_raises_value_error_when_there_is_no_fence():
    with pytest.raises(ValueError, match="code fence"):
        first_fenced_block("just prose")


@pytest.mark.parametrize("handle", ["Otto", "ma ra", "../../x", ""])
def test_add_message_rejects_an_invalid_handle(handle):
    with pytest.raises(ValueError, match="invalid handle"):
        add_message([], handle, "Name", "hi", 100.0)


@pytest.mark.parametrize("since", ["abc", ""])
def test_read_since_rejects_a_non_numeric_timestamp(since):
    with pytest.raises(ValueError, match="Slack timestamp"):
        read_since([msg("mara", "hi", "100.000000")], since)


@pytest.mark.parametrize(
    "messages, expected",
    [
        ([1, 2], "message 0 must be an object"),
        ([{"text": "hi"}], "message 0 is missing"),
        ([msg("mara", "hi", "abc")], "message 0 has a ts"),
    ],
)
def test_load_channel_rejects_wrong_shaped_messages(tmp_path, messages, expected):
    path = tmp_path / "channel.json"
    path.write_text(json.dumps(messages))

    with pytest.raises(ValueError, match=expected):
        load_channel(path)

import json
import re
from pathlib import Path

import pytest

import fake_slack
from war_room.fake_slack import first_fenced_block
from war_room.profiles import HANDLE_RE, parse_replies

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = REPO_ROOT / "demo" / "seed-round-1.json"
MESSAGE_KEYS = {"author_handle", "author_name", "ts", "text"}


@pytest.fixture
def channel(tmp_path):
    return tmp_path / "channel.json"


def run(channel, *args):
    return fake_slack.main(["--channel", str(channel), *args])


def stored(channel):
    return json.loads(channel.read_text())


def write_seed(tmp_path, messages):
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(messages))
    return path


def seed_message(handle, text):
    return {"author_handle": handle, "author_name": handle.title(), "text": text}


def test_post_with_text_prints_the_ts_and_stores_a_message_from_the_bot(channel, capsys):
    assert run(channel, "post", "--text", "hello") == 0

    (message,) = stored(channel)
    assert capsys.readouterr().out == f"ts: {message['ts']}\n"
    assert re.fullmatch(r"\d+\.\d{6}", message["ts"])
    assert message["author_handle"] == "war-room"
    assert message["author_name"] == "War Room"
    assert message["text"] == "hello"


def test_post_with_file_posts_the_file_text(channel, tmp_path):
    plan = tmp_path / "mara.md"
    plan.write_text("plan for mara\n")

    run(channel, "post", "--file", str(plan))

    assert stored(channel)[0]["text"] == "plan for mara"


def test_post_with_fenced_posts_only_the_fenced_block(channel, tmp_path):
    doc = tmp_path / "kickoff.md"
    doc.write_text("# Title\n\n```text\n*Console:*\n```\n\nafter\n")

    run(channel, "post", "--file", str(doc), "--fenced")

    assert stored(channel)[0]["text"] == "*Console:*"


def test_post_with_fenced_on_the_real_kickoff_post_posts_the_post(channel):
    kickoff = REPO_ROOT / "docs" / "kickoff-post.md"

    run(channel, "post", "--file", str(kickoff), "--fenced")

    assert stored(channel)[0]["text"] == first_fenced_block(kickoff.read_text())


def test_post_requires_file_or_text(channel):
    with pytest.raises(SystemExit) as exit_info:
        run(channel, "post")

    assert exit_info.value.code == 2


def test_reply_stores_the_handle_and_defaults_the_name_to_title_case(channel, capsys):
    run(channel, "reply", "--as", "mara", "--text", "Console: PS5")

    (message,) = stored(channel)
    assert message["author_handle"] == "mara"
    assert message["author_name"] == "Mara"
    assert capsys.readouterr().out == f"ts: {message['ts']}\n"


def test_reply_can_set_the_display_name(channel):
    run(channel, "reply", "--as", "mara", "--name", "Mara R.", "--text", "hi")

    assert stored(channel)[0]["author_name"] == "Mara R."


def test_read_writes_exactly_the_four_saved_message_keys_and_reports_the_count(
    channel, tmp_path, capsys
):
    run(channel, "reply", "--as", "mara", "--text", "one")
    run(channel, "reply", "--as", "otto", "--text", "two")
    out = tmp_path / "outputs" / "messages.json"
    capsys.readouterr()

    assert run(channel, "read", "--out", str(out)) == 0

    messages = json.loads(out.read_text())
    assert [set(m) for m in messages] == [MESSAGE_KEYS, MESSAGE_KEYS]
    assert capsys.readouterr().out == f"Saved 2 message(s) to {out}\n"


def test_read_since_returns_only_later_messages(channel, tmp_path):
    run(channel, "reply", "--as", "mara", "--text", "one")
    first_ts = stored(channel)[0]["ts"]
    run(channel, "reply", "--as", "otto", "--text", "two")
    out = tmp_path / "messages.json"

    run(channel, "read", "--since", first_ts, "--out", str(out))

    assert [m["author_handle"] for m in json.loads(out.read_text())] == ["otto"]


def test_read_leaves_out_the_bot_unless_asked(channel, tmp_path):
    run(channel, "post", "--text", "kickoff")
    run(channel, "reply", "--as", "mara", "--text", "hi")
    default_out = tmp_path / "default.json"
    with_bot_out = tmp_path / "with-bot.json"

    run(channel, "read", "--out", str(default_out))
    run(channel, "read", "--include-bot", "--out", str(with_bot_out))

    assert [m["author_handle"] for m in json.loads(default_out.read_text())] == ["mara"]
    handles = [m["author_handle"] for m in json.loads(with_bot_out.read_text())]
    assert handles == ["war-room", "mara"]


def test_show_prints_every_message_including_the_bot(channel, capsys):
    run(channel, "post", "--text", "kickoff")
    run(channel, "reply", "--as", "mara", "--text", "Console: PS5")
    capsys.readouterr()

    run(channel, "show")

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("War Room: kickoff")
    assert lines[1].endswith("Mara: Console: PS5")


def test_show_on_an_empty_channel_says_so(channel, capsys):
    run(channel, "show")

    assert capsys.readouterr().out == "No messages.\n"


def test_seed_appends_after_existing_messages_with_increasing_timestamps(
    channel, tmp_path, capsys
):
    run(channel, "post", "--text", "kickoff")
    seed = write_seed(tmp_path, [seed_message("mara", "one"), seed_message("otto", "two")])
    capsys.readouterr()

    assert run(channel, "seed", "--file", str(seed)) == 0

    messages = stored(channel)
    assert [m["author_handle"] for m in messages] == ["war-room", "mara", "otto"]
    timestamps = [float(m["ts"]) for m in messages]
    assert timestamps == sorted(set(timestamps))
    assert capsys.readouterr().out == "Seeded 2 message(s)\n"


def test_seed_with_a_small_delay_still_seeds_everything(channel, tmp_path):
    seed = write_seed(tmp_path, [seed_message("mara", "one"), seed_message("otto", "two")])

    run(channel, "seed", "--file", str(seed), "--delay", "0.01")

    assert len(stored(channel)) == 2


def test_seed_defaults_to_the_committed_seed_file(channel, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)

    run(channel, "seed")

    assert len(stored(channel)) == len(json.loads(SEED_FILE.read_text()))


def test_seed_message_missing_a_key_exits_with_message(channel, tmp_path):
    seed = write_seed(tmp_path, [{"author_handle": "mara", "text": "hi"}])

    with pytest.raises(SystemExit) as exit_info:
        run(channel, "seed", "--file", str(seed))

    assert "author_name" in str(exit_info.value)
    assert not channel.exists()


def test_committed_seed_file_has_five_distinct_handles_and_labeled_text():
    seed = json.loads(SEED_FILE.read_text())

    assert {m["author_handle"] for m in seed} == {"jules", "mara", "otto", "pia", "sol"}
    assert all(set(m) == {"author_handle", "author_name", "text"} for m in seed)
    assert all(HANDLE_RE.fullmatch(m["author_handle"]) for m in seed)
    assert all(any(":" in line for line in m["text"].splitlines()) for m in seed)


def test_seeded_replies_parse_into_five_profiles(channel, tmp_path, capsys):
    run(channel, "post", "--text", "kickoff")
    kickoff_ts = capsys.readouterr().out.split()[1]
    run(channel, "seed", "--file", str(SEED_FILE))
    out = tmp_path / "messages.json"

    run(channel, "read", "--since", kickoff_ts, "--out", str(out))
    profiles = {p.handle: p for p in parse_replies(json.loads(out.read_text()), kickoff_ts)}

    assert sorted(profiles) == ["jules", "mara", "otto", "pia", "sol"]
    assert profiles["mara"].spouse_risk == 4
    assert profiles["mara"].preordered is True
    assert profiles["otto"].preordered is True
    assert profiles["otto"].pto_status == "not yet"
    assert profiles["pia"].console is None


def test_reset_clears_the_channel_and_is_safe_when_already_empty(channel, capsys):
    run(channel, "post", "--text", "kickoff")
    capsys.readouterr()

    assert run(channel, "reset") == 0
    assert not channel.exists()
    assert capsys.readouterr().out == "Channel cleared.\n"

    assert run(channel, "reset") == 0
    assert capsys.readouterr().out == "Channel already empty.\n"


def test_missing_post_file_exits_with_message(channel, tmp_path):
    missing = tmp_path / "nope.md"

    with pytest.raises(SystemExit) as exit_info:
        run(channel, "post", "--file", str(missing))

    assert str(exit_info.value) == f"File not found: {missing}"


def test_fenced_without_a_fence_exits_with_message(channel, tmp_path):
    doc = tmp_path / "plain.md"
    doc.write_text("just prose")

    with pytest.raises(SystemExit) as exit_info:
        run(channel, "post", "--file", str(doc), "--fenced")

    assert "code fence" in str(exit_info.value)


def test_blank_text_exits_with_message_and_stores_nothing(channel):
    with pytest.raises(SystemExit) as exit_info:
        run(channel, "reply", "--as", "mara", "--text", "  ")

    assert "blank" in str(exit_info.value)
    assert not channel.exists()


def test_corrupt_channel_file_exits_with_message(channel):
    channel.write_text("{not json")

    with pytest.raises(SystemExit) as exit_info:
        run(channel, "show")

    assert "is not valid JSON" in str(exit_info.value)

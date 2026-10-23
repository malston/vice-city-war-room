import json

import pytest

import parse_profiles


def msg(handle, text, ts="200.0"):
    return {
        "author_handle": handle,
        "author_name": handle.title(),
        "ts": ts,
        "text": text,
    }


def save(tmp_path, content):
    path = tmp_path / "messages.json"
    path.write_text(content if isinstance(content, str) else json.dumps(content))
    return path


def run(messages_path, out, kickoff_ts="100.0"):
    return parse_profiles.main(
        ["--messages", str(messages_path), "--kickoff-ts", kickoff_ts, "--out", str(out)]
    )


def test_cli_writes_one_profile_per_replier(tmp_path):
    messages = save(
        tmp_path,
        [
            msg("pia", "welcome", ts="50.0"),
            msg("mara", "Console: Xbox"),
            msg("otto", "Console: PS5"),
        ],
    )
    out = tmp_path / "profiles"

    assert run(messages, out) == 0

    assert sorted(p.name for p in out.glob("*.json")) == ["mara.json", "otto.json"]


def test_cli_reports_what_it_wrote(tmp_path, capsys):
    messages = save(tmp_path, [msg("mara", "Console: Xbox"), msg("otto", "Console: PS5")])
    out = tmp_path / "profiles"

    run(messages, out)

    assert capsys.readouterr().out == f"Wrote 2 profile(s) to {out}: mara, otto\n"


def test_cli_with_no_replies_writes_nothing_and_says_so(tmp_path, capsys):
    messages = save(tmp_path, [msg("pia", "welcome", ts="50.0")])
    out = tmp_path / "profiles"

    assert run(messages, out) == 0

    assert not out.exists()
    assert capsys.readouterr().out == "No replies after the kickoff; nothing written.\n"


def test_out_defaults_to_profiles_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    messages = save(tmp_path, [msg("mara", "Console: Xbox")])

    parse_profiles.main(["--messages", str(messages), "--kickoff-ts", "100.0"])

    assert (tmp_path / "profiles" / "mara.json").exists()


def test_missing_messages_file_exits_with_message(tmp_path):
    missing = tmp_path / "nope.json"

    with pytest.raises(SystemExit) as exit_info:
        run(missing, tmp_path / "profiles")

    assert f"Messages file not found: {missing}" == str(exit_info.value)


def test_invalid_json_exits_with_message(tmp_path):
    messages = save(tmp_path, "{not json")

    with pytest.raises(SystemExit) as exit_info:
        run(messages, tmp_path / "profiles")

    assert "is not valid JSON" in str(exit_info.value)


def test_json_that_is_not_a_list_exits_with_message(tmp_path):
    messages = save(tmp_path, {"text": "hi"})

    with pytest.raises(SystemExit) as exit_info:
        run(messages, tmp_path / "profiles")

    assert "must hold a JSON list" in str(exit_info.value)


def test_message_missing_a_key_exits_with_message(tmp_path):
    no_name = {"author_handle": "mara", "ts": "200.0", "text": "hi"}
    messages = save(tmp_path, [no_name])

    with pytest.raises(SystemExit) as exit_info:
        run(messages, tmp_path / "profiles")

    assert "Message 0" in str(exit_info.value)
    assert "author_name" in str(exit_info.value)


def test_invalid_handle_exits_with_message_and_writes_nothing(tmp_path):
    messages = save(tmp_path, [msg("../etc", "Console: PS5")])
    out = tmp_path / "profiles"

    with pytest.raises(SystemExit) as exit_info:
        run(messages, out)

    assert "invalid handle" in str(exit_info.value)
    assert not out.exists()


def test_non_numeric_kickoff_ts_is_rejected(tmp_path, capsys):
    messages = save(tmp_path, [msg("mara", "Console: Xbox")])

    with pytest.raises(SystemExit) as exit_info:
        run(messages, tmp_path / "profiles", kickoff_ts="yesterday")

    assert exit_info.value.code == 2
    assert "--kickoff-ts" in capsys.readouterr().err

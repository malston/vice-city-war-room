import pytest

import movers as movers_cli
from war_room.movers import (
    Mover,
    ScoreLine,
    compare_rounds,
    format_movers_post,
    parse_scoreboard,
)


def line(rank: int, name: str, score: int) -> ScoreLine:
    return ScoreLine(rank, name, "The Codename", score)


def test_parse_scoreboard_reads_contract_lines():
    result = parse_scoreboard("1. Mara (The Night Owl): 75/100")
    assert result == [ScoreLine(1, "Mara", "The Night Owl", 75)]


def test_parse_scoreboard_ignores_title_and_blank_lines():
    text = "*Scoreboard*\n\n1. Mara (The Night Owl): 75/100\n\nGood luck, crew.\n"
    assert parse_scoreboard(text) == [ScoreLine(1, "Mara", "The Night Owl", 75)]


def test_score_over_100_raises_value_error_naming_the_line():
    with pytest.raises(ValueError, match="1. Mara"):
        parse_scoreboard("1. Mara (The Night Owl): 101/100")


def test_duplicate_display_names_raise_value_error():
    text = "1. Mara (A): 80/100\n2. Mara (B): 70/100"
    with pytest.raises(ValueError, match="Mara"):
        parse_scoreboard(text)


def test_delta_is_after_minus_before():
    assert Mover("Pia", 30, 61).delta == 31
    assert Mover("Pia", 61, 30).delta == -31


def test_delta_is_none_when_either_side_is_missing():
    assert Mover("Pia", None, 50).delta is None
    assert Mover("Pia", 50, None).delta is None


def test_movers_sorted_by_delta_descending_then_name():
    previous = [line(1, "Zed", 50), line(2, "Amy", 50), line(3, "Bo", 50)]
    current = [line(1, "Zed", 60), line(2, "Amy", 60), line(3, "Bo", 40)]
    result = compare_rounds(previous, current)
    assert [m.display_name for m in result] == ["Amy", "Zed", "Bo"]


def test_newcomers_then_dropouts_come_after_movers():
    previous = [line(1, "Gone2", 50), line(2, "Gone1", 40), line(3, "Stay", 30)]
    current = [line(1, "New2", 90), line(2, "New1", 80), line(3, "Stay", 35)]
    result = compare_rounds(previous, current)
    assert [m.display_name for m in result] == ["Stay", "New1", "New2", "Gone1", "Gone2"]
    assert result[1] == Mover("New1", None, 80)
    assert result[3] == Mover("Gone1", 40, None)


def test_post_names_biggest_climber_and_biggest_drop():
    movers = [Mover("Pia", 30, 61), Mover("Sam", 50, 50), Mover("Lou", 70, 55)]
    post = format_movers_post(movers)
    assert "Pia, 30 to 61 (+31)" in post
    assert "Lou, 70 to 55 (-15)" in post


def test_post_omits_drop_when_nobody_dropped():
    post = format_movers_post([Mover("Pia", 30, 61), Mover("Sam", 50, 50)])
    assert "Pia, 30 to 61 (+31)" in post
    assert "drop" not in post.lower()


def test_post_lists_new_crew_members():
    post = format_movers_post([Mover("Pia", 30, 61), Mover("Nia", None, 44)])
    assert "Nia" in post
    assert "new" in post.lower()


def test_post_says_nobody_moved_when_all_scores_match():
    post = format_movers_post([Mover("Pia", 30, 30), Mover("Sam", 50, 50)])
    assert "Nobody moved this round." in post


def test_post_has_slack_formatting_and_no_em_dashes():
    movers = [Mover("Pia", 30, 61), Mover("Lou", 70, 55), Mover("Nia", None, 44)]
    post = format_movers_post(movers)
    assert "**" not in post
    assert not any(row.startswith("#") for row in post.splitlines())
    assert "\u2014" not in post


def test_cli_writes_the_post_to_out(tmp_path, capsys):
    prev = tmp_path / "prev.md"
    curr = tmp_path / "curr.md"
    out = tmp_path / "movers.md"
    prev.write_text("1. Pia (The Ghost): 30/100\n")
    curr.write_text("1. Pia (The Ghost): 61/100\n")
    code = movers_cli.main(["--prev", str(prev), "--curr", str(curr), "--out", str(out)])
    assert code == 0
    assert "Pia, 30 to 61 (+31)" in out.read_text()
    assert f"Wrote movers post to {out}" in capsys.readouterr().out


def test_cli_missing_file_exits_with_message(tmp_path):
    curr = tmp_path / "curr.md"
    curr.write_text("1. Pia (The Ghost): 61/100\n")
    with pytest.raises(SystemExit) as info:
        movers_cli.main(
            ["--prev", str(tmp_path / "nope.md"), "--curr", str(curr), "--out", str(tmp_path / "o.md")]
        )
    assert "nope.md" in str(info.value)

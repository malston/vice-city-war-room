from pathlib import Path

import pytest

from run_war_room import parse_args


def test_round_is_required():
    with pytest.raises(SystemExit):
        parse_args([])


def test_round_must_be_an_integer():
    with pytest.raises(SystemExit):
        parse_args(["--round", "one"])


def test_out_defaults_to_outputs_round_n():
    assert parse_args(["--round", "1"]).out == Path("outputs/round-1")
    assert parse_args(["--round", "3"]).out == Path("outputs/round-3")


def test_explicit_out_wins():
    args = parse_args(["--round", "1", "--out", "outputs/smoke"])
    assert args.out == Path("outputs/smoke")


def test_defaults_for_profiles_facts_prior_and_force():
    args = parse_args(["--round", "1"])
    assert args.round == 1
    assert args.profiles == Path("profiles")
    assert args.facts == Path("synthetic-data/launch-facts.md")
    assert args.prior_scoreboard is None
    assert args.force is False


def test_all_options_are_parsed():
    args = parse_args(
        [
            "--round", "2",
            "--profiles", "p",
            "--facts", "f.md",
            "--prior-scoreboard", "s.md",
            "--out", "o",
            "--force",
        ]
    )
    assert args.round == 2
    assert args.profiles == Path("p")
    assert args.facts == Path("f.md")
    assert args.prior_scoreboard == Path("s.md")
    assert args.out == Path("o")
    assert args.force is True

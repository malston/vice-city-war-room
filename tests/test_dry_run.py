from pathlib import Path

import pytest

from dry_run import main, run_checks

PROFILES = Path("synthetic-data/profiles")
SAMPLES = Path("synthetic-data/sample-outputs")
FACTS = SAMPLES / "faq-facts.md"
BAIT = Path("synthetic-data/bait.json")


def results_for(sample: str) -> dict:
    return {r.name: r for r in run_checks(PROFILES, SAMPLES / sample, FACTS, BAIT)}


def test_passing_sample_passes_every_check():
    failed = [r for r in results_for("pass").values() if not r.passed]
    assert failed == []


def test_failing_sample_catches_both_baits():
    result = results_for("fail")["no_bait_in_outputs"]
    assert not result.passed
    assert "wet drywall" in result.detail and "blimp heist" in result.detail


def test_failing_sample_catches_missing_cleaner_verdict():
    assert not results_for("fail")["cleaner_consulted"].passed


@pytest.mark.parametrize(
    "check",
    ["person_files", "scoreboard_format", "scoreboard_complete", "no_em_dashes",
     "slack_formatting", "supported_claims"],
)
def test_failing_sample_fails_each_planted_check(check):
    assert not results_for("fail")[check].passed


def skip_run_args(sample: str) -> list[str]:
    return ["--skip-run", "--profiles", str(PROFILES), "--out", str(SAMPLES / sample),
            "--facts", str(FACTS), "--bait", str(BAIT)]


def test_skip_run_exit_codes(capsys):
    assert main(skip_run_args("pass")) == 0
    assert "DRY RUN: PASS" in capsys.readouterr().out
    assert main(skip_run_args("fail")) == 1
    assert "DRY RUN: FAIL" in capsys.readouterr().out


def test_full_run_without_runner_explains_skip_run(tmp_path, monkeypatch):
    for name in ("profiles", "facts.md", "bait.json"):
        src = {"profiles": PROFILES, "facts.md": FACTS, "bait.json": BAIT}[name]
        dest = tmp_path / name
        if src.is_dir():
            dest.mkdir()
        else:
            dest.write_text(src.read_text())
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="--skip-run"):
        main(["--profiles", "profiles", "--facts", "facts.md", "--bait", "bait.json"])

import json
from dataclasses import FrozenInstanceError

import pytest

from check_outputs import main
from war_room.checks import (
    CheckResult,
    check_outputs,
    forbidden_found,
    format_report,
    transcript_consulted_cleaner,
    unsupported_claims,
)


@pytest.fixture
def valid_outputs(tmp_path):
    profiles = tmp_path / "profiles"
    out = tmp_path / "out"
    facts = tmp_path / "facts.md"
    profiles.mkdir()
    out.mkdir()
    for handle, name in [("jules", "Jules"), ("sam", "Sam")]:
        profile = {
            "handle": handle,
            "display_name": name,
            "console": "PS5",
            "pto_status": None,
            "spouse_risk": None,
            "preordered": None,
            "weakness": None,
            "raw_reply": "PTO: December 2nd. Budget: $1,000.",
        }
        (profiles / f"{handle}.json").write_text(json.dumps(profile), encoding="utf-8")
        (out / f"{handle}.md").write_text("*Ready* for Nov 19.\n", encoding="utf-8")
    (out / "scoreboard.md").write_text(
        "1. Jules (Driver): 90/100\n2. Sam (Planner): 70/100\n", encoding="utf-8"
    )
    facts.write_text("- Launch: November 19, 2026 (source: publisher)\n", encoding="utf-8")
    return profiles, out, facts


def results_by_name(paths):
    return {result.name: result for result in check_outputs(*paths)}


def test_missing_person_file_fails(valid_outputs):
    (valid_outputs[1] / "jules.md").unlink()
    assert results_by_name(valid_outputs)["person_files"] == CheckResult(
        "person_files", False, "jules.md"
    )


def test_missing_scoreboard_fails(valid_outputs):
    (valid_outputs[1] / "scoreboard.md").unlink()
    results = results_by_name(valid_outputs)
    for name in ["scoreboard_present", "scoreboard_format", "scoreboard_complete"]:
        assert not results[name].passed
        assert results[name].detail


def test_scoreboard_omitting_a_person_fails(valid_outputs):
    (valid_outputs[1] / "scoreboard.md").write_text("1. Jules (Driver): 90/100\n")
    result = results_by_name(valid_outputs)["scoreboard_complete"]
    assert not result.passed
    assert "Sam" in result.detail


def test_unsorted_scoreboard_fails(valid_outputs):
    (valid_outputs[1] / "scoreboard.md").write_text(
        "1. Jules (Driver): 70/100\n2. Sam (Planner): 90/100\n"
    )
    assert not results_by_name(valid_outputs)["scoreboard_format"].passed


def test_score_over_100_fails(valid_outputs):
    (valid_outputs[1] / "scoreboard.md").write_text(
        "1. Jules (Driver): 101/100\n2. Sam (Planner): 70/100\n"
    )
    assert not results_by_name(valid_outputs)["scoreboard_format"].passed


def test_valid_scoreboard_passes(valid_outputs):
    results = check_outputs(*valid_outputs)
    assert [result.name for result in results] == [
        "person_files", "scoreboard_present", "scoreboard_format",
        "scoreboard_complete", "no_em_dashes", "slack_formatting", "supported_claims",
    ]
    assert all(result.passed and result.detail == "" for result in results)


@pytest.mark.parametrize("filename", ["jules.md", "sam.md", "scoreboard.md"])
def test_em_dash_in_any_output_fails(valid_outputs, filename):
    (valid_outputs[1] / filename).write_text("Ready \u2014 go.", encoding="utf-8")
    result = results_by_name(valid_outputs)["no_em_dashes"]
    assert not result.passed
    assert filename in result.detail


def test_double_asterisk_bold_fails(valid_outputs):
    (valid_outputs[1] / "sam.md").write_text("**Ready**")
    assert not results_by_name(valid_outputs)["slack_formatting"].passed


@pytest.mark.parametrize("prefix", ["# ", "## ", "######\t"])
def test_hash_heading_fails(valid_outputs, prefix):
    (valid_outputs[1] / "sam.md").write_text(f"Ready\n{prefix}Plan\n")
    assert not results_by_name(valid_outputs)["slack_formatting"].passed


def test_hashtag_at_line_start_is_not_a_heading(valid_outputs):
    (valid_outputs[1] / "sam.md").write_text("#nospoilers is the rule\n")
    assert results_by_name(valid_outputs)["slack_formatting"].passed


def test_dollar_amount_not_in_facts_is_unsupported(valid_outputs):
    assert unsupported_claims("Costs $70 or $69.99", ["Price unconfirmed"]) == {
        "$70", "$69.99"
    }
    (valid_outputs[1] / "jules.md").write_text("Costs $69.99")
    assert results_by_name(valid_outputs)["supported_claims"] == CheckResult(
        "supported_claims", False, "jules.md: $69.99"
    )


@pytest.mark.parametrize("date", ["Nov 19", "Nov. 19th", "November 19th", "nov 19"])
def test_date_in_facts_is_supported(date):
    assert unsupported_claims(date, ["November 19, 2026"]) == set()


def test_date_from_profile_is_supported(valid_outputs):
    (valid_outputs[1] / "jules.md").write_text("PTO Dec. 2. Budget $1000.00.")
    assert results_by_name(valid_outputs)["supported_claims"].passed


def test_text_without_claims_returns_empty_set():
    assert unsupported_claims("Prepare the console and snacks.", []) == set()


def test_claims_compare_values_and_preserve_unsupported_spelling():
    assert unsupported_claims(
        "$70.00 $1,000 $69.99 Nov. 20th December 2nd", ["$70 $1000.00 Nov 19 Dec 2"]
    ) == {"$69.99", "Nov. 20th"}


@pytest.mark.parametrize("month", [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
])
def test_all_month_abbreviations_are_normalized(month):
    assert unsupported_claims(f"{month[:3]}. 3rd", [f"{month} 3, 2026"]) == set()


def test_forbidden_substring_is_reported(valid_outputs):
    out = valid_outputs[1]
    for filename in ["z.txt", "a.md", "coordinator-transcript.txt", "run.log", "skip.json"]:
        (out / filename).write_text("BAIT and Spoiler")
    assert forbidden_found(out, ["spoiler", "bait"]) == [
        "a.md: bait", "a.md: spoiler", "z.txt: bait", "z.txt: spoiler",
    ]


@pytest.mark.parametrize("verdict", ["PASS", "FIX"])
def test_transcript_with_verdict_line_counts_as_consulted(verdict):
    assert transcript_consulted_cleaner(f"Coordinator\nVERDICT: {verdict}\nDone")


@pytest.mark.parametrize("text", ["", "Mention VERDICT: PASS", " VERDICT: FIX", "VERDICT: FAIL"])
def test_transcript_without_verdict_at_line_start_is_not_consulted(text):
    assert not transcript_consulted_cleaner(text)


def test_report_is_one_line_per_check_and_lists_at_most_five_failure_details():
    results = [
        CheckResult("ok", True, ""),
        CheckResult("many", False, "; ".join(str(i) for i in range(8))),
        CheckResult("five", False, "a; b; c; d; e"),
    ]
    assert format_report(results) == (
        "PASS ok\nFAIL many: 0; 1; 2; 3; 4; (+3 more)\nFAIL five: a; b; c; d; e"
    )
    assert format_report([]) == ""


def test_check_result_is_frozen():
    result = CheckResult("ok", True, "")
    with pytest.raises(FrozenInstanceError):
        result.passed = False


def test_report_keeps_multiline_claim_on_one_line():
    assert format_report([CheckResult("supported_claims", False, "sam.md: Nov\n20")]) == (
        "FAIL supported_claims: sam.md: Nov 20"
    )


@pytest.mark.parametrize("line", [
    "3. Sam (Planner): 70/100", "2. Sam: 70/100", "2. Sam (Planner): -1/100",
    "2. Sam (Planner): 1000/100", " 2. Sam (Planner): 70/100",
])
def test_malformed_scoreboard_fails_without_crashing(valid_outputs, line):
    (valid_outputs[1] / "scoreboard.md").write_text(f"1. Jules (Driver): 90/100\n{line}\n")
    assert not results_by_name(valid_outputs)["scoreboard_format"].passed


def test_scoreboard_allows_blank_lines_ties_and_boundary_scores(valid_outputs):
    board = valid_outputs[1] / "scoreboard.md"
    for score in [0, 100]:
        board.write_text(f"\n1. Jules (Driver): {score}/100\n \n2. Sam (Planner): {score}/100\n")
        assert all(result.passed for result in check_outputs(*valid_outputs))


def test_scoreboard_names_must_match_exactly(valid_outputs):
    (valid_outputs[1] / "scoreboard.md").write_text(
        "1. Jules (Driver): 90/100\n2. Samantha (Planner): 70/100\n"
    )
    assert not results_by_name(valid_outputs)["scoreboard_complete"].passed


def test_scoreboard_extra_person_fails(valid_outputs):
    board = valid_outputs[1] / "scoreboard.md"
    board.write_text(board.read_text() + "3. Pat (Cook): 20/100\n")
    assert not results_by_name(valid_outputs)["scoreboard_complete"].passed


def test_null_display_name_falls_back_to_handle(valid_outputs):
    path = valid_outputs[0] / "sam.json"
    profile = json.loads(path.read_text())
    profile["display_name"] = None
    path.write_text(json.dumps(profile))
    board = valid_outputs[1] / "scoreboard.md"
    board.write_text(board.read_text().replace("Sam", "sam"))
    assert results_by_name(valid_outputs)["scoreboard_complete"].passed


@pytest.mark.parametrize("index", [0, 1, 2])
def test_missing_input_path_raises(valid_outputs, index):
    paths = list(valid_outputs)
    paths[index] = paths[index].parent / "missing"
    with pytest.raises(FileNotFoundError, match="missing"):
        check_outputs(*paths)
    with pytest.raises(SystemExit, match="missing"):
        main(["--profiles", str(paths[0]), "--out", str(paths[1]), "--facts", str(paths[2])])


def test_main_returns_zero_on_valid_outputs_and_one_for_missing_file(valid_outputs, capsys):
    profiles, out, facts = valid_outputs
    args = ["--profiles", str(profiles), "--out", str(out), "--facts", str(facts)]
    assert main(args) == 0
    assert capsys.readouterr().out == format_report(check_outputs(*valid_outputs)) + "\n"
    (out / "sam.md").unlink()
    assert main(args) == 1
    assert "FAIL person_files: sam.md\n" in capsys.readouterr().out


def test_duplicate_display_name_cannot_hide_an_omitted_person(tmp_path):
    profiles_dir, out_dir, facts = tmp_path / "profiles", tmp_path / "out", tmp_path / "facts.md"
    profiles_dir.mkdir()
    out_dir.mkdir()
    facts.write_text("- Release date: November 19, 2026 (source: FAQ)\n")
    for handle in ("sam", "sam2"):
        (profiles_dir / f"{handle}.json").write_text(json.dumps({
            "handle": handle, "display_name": "Sam", "console": None, "pto_status": None,
            "spouse_risk": None, "preordered": None, "weakness": None, "raw_reply": "hi",
        }))
        (out_dir / f"{handle}.md").write_text("plan\n")
    (out_dir / "scoreboard.md").write_text("1. Sam (Driver): 90/100\n2. Stranger (Planner): 70/100\n")
    results = {r.name: r for r in check_outputs(profiles_dir, out_dir, facts)}
    assert not results["scoreboard_complete"].passed

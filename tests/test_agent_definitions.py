from pathlib import Path

import create_coordinator
import create_specialists
from create_specialists import SPECIALISTS

EM_DASH = "—"


def test_specialist_keys_are_the_four_roles():
    assert [s["key"] for s in SPECIALISTS] == [
        "fixer",
        "smooth_talker",
        "wheelman",
        "quartermaster",
    ]


def test_every_specialist_has_name_model_and_system():
    for spec in SPECIALISTS:
        assert spec["name"].startswith("The ")
        assert spec["model"]
        assert spec["system"]


def test_every_specialist_prompt_limits_facts_to_the_facts_document():
    for spec in SPECIALISTS:
        assert "launch-facts" in spec["system"], spec["key"]
        assert "unconfirmed" in spec["system"], spec["key"]


def test_every_specialist_prompt_forbids_em_dashes():
    for spec in SPECIALISTS:
        assert "em dash" in spec["system"].lower(), spec["key"]


def test_no_prompt_contains_an_em_dash():
    for spec in SPECIALISTS:
        assert EM_DASH not in spec["system"], spec["key"]
    assert EM_DASH not in create_coordinator.COORDINATOR_SYSTEM


def test_every_prompt_forbids_dates_outside_the_facts_document():
    for spec in SPECIALISTS:
        assert "no dates other than" in spec["system"].lower(), spec["key"]
    assert "no dates other than" in create_coordinator.COORDINATOR_SYSTEM.lower()


def test_specialist_jokes_target_the_situation_not_the_person():
    for spec in SPECIALISTS:
        assert "never the person" in spec["system"], spec["key"]


def test_coordinator_prompt_names_every_specialist_name():
    for spec in SPECIALISTS:
        assert spec["name"] in create_coordinator.COORDINATOR_SYSTEM


def test_coordinator_prompt_names_the_mastermind_and_the_cleaner():
    assert "The Mastermind" in create_coordinator.COORDINATOR_SYSTEM
    assert "The Cleaner" in create_coordinator.COORDINATOR_SYSTEM


def test_coordinator_prompt_defines_cleaner_loop():
    prompt = create_coordinator.COORDINATOR_SYSTEM
    assert "VERDICT: FIX" in prompt
    assert "twice" in prompt


def test_coordinator_prompt_quotes_the_final_verdict_line():
    prompt = create_coordinator.COORDINATOR_SYSTEM
    assert "VERDICT: PASS" in prompt
    assert "quote" in prompt.lower()


def test_coordinator_prompt_defines_scoreboard_line_format():
    prompt = create_coordinator.COORDINATOR_SYSTEM
    assert "/100" in prompt
    assert "<rank>. <display_name> (<codename>): <score>/100" in prompt


def test_coordinator_prompt_uses_the_scoring_and_template_skills():
    prompt = create_coordinator.COORDINATOR_SYSTEM
    assert "readiness-scoring" in prompt
    assert "job-file-template" in prompt


def test_coordinator_prompt_fans_out_in_parallel():
    prompt = create_coordinator.COORDINATOR_SYSTEM
    assert "parallel" in prompt.lower()
    assert "launch-facts" in prompt


def test_coordinator_roster_includes_every_id_in_the_ids_file():
    ids = {"fixer": "agent_1", "cleaner": "agent_2"}
    assert create_coordinator.build_roster(ids) == [
        {"type": "agent", "id": "agent_1"},
        {"type": "agent", "id": "agent_2"},
    ]


def test_modules_expose_no_deal_desk_leftovers():
    for text in [
        create_coordinator.COORDINATOR_SYSTEM,
        *[s["system"] for s in create_specialists.SPECIALISTS],
    ]:
        assert "RFP" not in text
        assert "Deal Desk" not in text


def test_scripts_carry_no_starter_kit_identifiers():
    for script in [
        "setup_environment.py",
        "create_specialists.py",
        "create_coordinator.py",
        "create_cleaner.py",
    ]:
        source = Path(script).read_text()
        assert "specialist-swarm" not in source, script
        assert "partner-basecamp" not in source, script
        assert "hackathon" not in source, script

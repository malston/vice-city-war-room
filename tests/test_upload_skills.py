import json
from types import SimpleNamespace

from upload_skills import SKILL_TO_AGENTS, load_agent_ids, skill_dicts, skills_by_title

CONTRACT_SKILLS = {
    "pto-playbook",
    "family-diplomacy",
    "launch-readiness-tech",
    "launch-supplies",
    "heist-voice",
    "readiness-scoring",
    "job-file-template",
}
CONTRACT_AGENT_KEYS = {
    "fixer",
    "smooth_talker",
    "wheelman",
    "quartermaster",
    "cleaner",
    "mastermind",
}


def test_load_agent_ids_includes_mastermind(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".specialist_ids.json").write_text(
        json.dumps({"fixer": "agent_f", "cleaner": "agent_c"})
    )
    (tmp_path / ".coordinator_id").write_text("agent_m\n")
    assert load_agent_ids() == {
        "fixer": "agent_f",
        "cleaner": "agent_c",
        "mastermind": "agent_m",
    }


def test_load_agent_ids_without_coordinator_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".specialist_ids.json").write_text(json.dumps({"fixer": "agent_f"}))
    assert load_agent_ids() == {"fixer": "agent_f"}


def test_skills_by_title_reads_display_name():
    skills = [
        SimpleNamespace(id="skill_1", display_name="Heist Voice"),
        SimpleNamespace(id="skill_2", display_name="Pto Playbook"),
    ]
    assert skills_by_title(skills) == {
        "Heist Voice": "skill_1",
        "Pto Playbook": "skill_2",
    }


class FakeSkill:
    """Stands in for the SDK's typed skill object."""

    def model_dump(self):
        return {"skill_id": "skill_1", "type": "custom", "version": "latest"}


def test_skill_dicts_converts_typed_objects_and_keeps_dicts():
    plain = {"skill_id": "skill_2", "type": "custom", "version": "latest"}
    assert skill_dicts([FakeSkill(), plain]) == [FakeSkill().model_dump(), plain]


def test_skill_dicts_handles_none():
    assert skill_dicts(None) == []


def test_skill_map_covers_the_seven_contract_skills():
    assert set(SKILL_TO_AGENTS) == CONTRACT_SKILLS


def test_every_mapped_agent_key_is_a_contract_agent_key():
    for skill, agents in SKILL_TO_AGENTS.items():
        assert agents, skill
        assert set(agents) <= CONTRACT_AGENT_KEYS, skill


def test_heist_voice_goes_to_all_six_agents():
    assert set(SKILL_TO_AGENTS["heist-voice"]) == CONTRACT_AGENT_KEYS


def test_each_domain_skill_goes_to_its_specialist():
    assert SKILL_TO_AGENTS["pto-playbook"] == ["fixer"]
    assert SKILL_TO_AGENTS["family-diplomacy"] == ["smooth_talker"]
    assert SKILL_TO_AGENTS["launch-readiness-tech"] == ["wheelman"]
    assert SKILL_TO_AGENTS["launch-supplies"] == ["quartermaster"]


def test_scoring_and_template_skills_go_to_the_mastermind():
    assert SKILL_TO_AGENTS["readiness-scoring"] == ["mastermind"]
    assert SKILL_TO_AGENTS["job-file-template"] == ["mastermind"]

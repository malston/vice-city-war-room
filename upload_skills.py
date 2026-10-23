"""
Upload each skill in skills/ via the Skills API and attach it to the right
agents of the heist crew.

Uses `files_from_dir` (from anthropic.lib) to package the skill directory.
Each skill bundle must contain a SKILL.md at its root with proper YAML
frontmatter (`name` and `description`).

Run after create_coordinator.py so the Mastermind exists to receive its
skills. A skill whose directory has no SKILL.md yet is skipped.

Usage:
    python upload_skills.py
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic
from anthropic.lib import files_from_dir


# Map skill directory name -> agent keys that should get it
SKILL_TO_AGENTS = {
    "pto-playbook": ["fixer"],
    "family-diplomacy": ["smooth_talker"],
    "launch-readiness-tech": ["wheelman"],
    "launch-supplies": ["quartermaster"],
    "heist-voice": [
        "fixer",
        "smooth_talker",
        "wheelman",
        "quartermaster",
        "cleaner",
        "mastermind",
    ],
    "readiness-scoring": ["mastermind"],
    "job-file-template": ["mastermind"],
}


def load_agent_ids() -> dict[str, str]:
    """Merge .specialist_ids.json with .coordinator_id (as `mastermind`)."""
    ids_path = Path(".specialist_ids.json")
    if not ids_path.exists():
        raise SystemExit("Run create_specialists.py first.")
    agent_ids = json.loads(ids_path.read_text())

    coordinator_path = Path(".coordinator_id")
    if coordinator_path.exists():
        agent_ids["mastermind"] = coordinator_path.read_text().strip()
    return agent_ids


def attach_skill(client: Anthropic, agent_key: str, agent_id: str, skill_id: str) -> None:
    print(f"  attaching to `{agent_key}` ({agent_id})...")
    current = client.beta.agents.retrieve(agent_id)
    # Avoid duplicate attachment on re-run
    already_attached = any(
        s.get("skill_id") == skill_id for s in (current.skills or [])
    )
    if already_attached:
        print("  already attached (skipping)")
        return

    new_skills = list(current.skills or []) + [
        {"type": "custom", "skill_id": skill_id, "version": "latest"}
    ]
    client.beta.agents.update(
        agent_id,
        version=current.version,
        skills=new_skills,
    )
    print("  attached")


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    agent_ids = load_agent_ids()
    if "mastermind" not in agent_ids:
        print("  WARNING: .coordinator_id missing, so the Mastermind gets no skills."
              " Run create_coordinator.py, then re-run this script.")

    client = Anthropic()

    # List existing custom skills so we can detect and reuse any prior uploads.
    # Skills API enforces unique display_title, so retrying with the same title
    # would otherwise fail. Idempotent retry is essential for dev loops.
    print("Checking for existing skills...")
    existing_by_title: dict[str, str] = {}
    for page in client.beta.skills.list(source="custom"):
        existing_by_title[page.display_title] = page.id

    uploaded: dict[str, str] = {}

    for skill_name, agent_keys in SKILL_TO_AGENTS.items():
        skill_dir = Path("skills") / skill_name
        if not (skill_dir / "SKILL.md").exists():
            print(f"  Skipping {skill_name}: no SKILL.md found")
            continue

        display_title = skill_name.replace("-", " ").title()

        # 1. Upload the skill (or reuse if one already exists with this title)
        if display_title in existing_by_title:
            skill_id = existing_by_title[display_title]
            print(f"Reusing existing skill: {skill_name} ({skill_id})")
        else:
            print(f"Uploading skill: {skill_name}...")
            skill = client.beta.skills.create(
                display_title=display_title,
                files=files_from_dir(str(skill_dir)),
            )
            skill_id = skill.id
            print(f"  -> {skill_id}")
        uploaded[skill_name] = skill_id

        # 2. Attach to every agent that should have it
        for agent_key in agent_keys:
            if agent_key not in agent_ids:
                print(f"  `{agent_key}` has no agent id yet, skipping")
                continue
            attach_skill(client, agent_key, agent_ids[agent_key], skill_id)

    Path(".skill_ids.json").write_text(json.dumps(uploaded, indent=2))
    print(f"\nUploaded {len(uploaded)} skills and attached them to the crew.")
    print("Next: python setup_environment.py")


if __name__ == "__main__":
    main()

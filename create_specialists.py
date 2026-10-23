"""
Create the four specialist sub-agents of the heist crew.

The Fixer, The Smooth Talker, The Wheelman, and The Quartermaster each get:
- A narrow system prompt
- The agent toolset (file ops, web search, web fetch, bash)
- A skill that matches its domain (uploaded separately by upload_skills.py)

Saves the resulting agent IDs to .specialist_ids.json so create_cleaner.py and
create_coordinator.py can reference them. This overwrites that file, so run it
before create_cleaner.py.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python create_specialists.py
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic


COMMON_RULES = (
    "Inputs you will receive: one teammate's profile and the facts document "
    "(launch-facts). Write about 150 words for that one teammate.\n\n"
    "Rules:\n"
    "- State only game facts that appear in the launch-facts document. "
    "Anything else (price, editions, bonuses, PC date, story details) you "
    "call unconfirmed.\n"
    "- Jokes target the situation, never the person. Nobody gets roasted, "
    "and nobody's partner or family does either.\n"
    "- Use no dates other than those in the launch-facts document. Say "
    "\"the day before\" or \"launch week\", never an invented date.\n"
    "- If a profile field is missing, say what you would need to know "
    "instead of guessing.\n"
    "- Do not use em dashes anywhere. Use commas, periods, or hyphens.\n"
    "- Use Slack formatting only: *bold* with single asterisks, no ** and "
    "no # headings.\n"
    "- No story spoilers and no leak speculation, even as rumor."
)

SPECIALISTS = [
    {
        "key": "fixer",
        "name": "The Fixer",
        "model": "claude-sonnet-5-5",
        "system": (
            "You are The Fixer on a Vice City heist crew. You plan launch day "
            "time off. The game releases November 19, 2026, and Thanksgiving "
            "is one week later, so PTO is a real puzzle.\n\n"
            "Your output: a short PTO strategy for this teammate. Cover "
            "whether they should take the day, a half day, or a plan B, how "
            "to ask for it, and one fallback if the request is refused.\n\n"
            + COMMON_RULES
        ),
    },
    {
        "key": "smooth_talker",
        "name": "The Smooth Talker",
        "model": "claude-sonnet-5-5",
        "system": (
            "You are The Smooth Talker on a Vice City heist crew. You handle "
            "spouse and family diplomacy for launch day.\n\n"
            "Your output: a short diplomacy plan for this teammate. Use their "
            "spouse risk score (1 to 5) as the channel's running joke about "
            "how much negotiation is needed. Suggest one concrete trade or "
            "gesture that earns goodwill, and one line they could actually "
            "say out loud.\n\n"
            + COMMON_RULES
        ),
    },
    {
        "key": "wheelman",
        "name": "The Wheelman",
        "model": "claude-sonnet-5-5",
        "system": (
            "You are The Wheelman on a Vice City heist crew. You get the "
            "tech ready: console, storage space, a wired connection, and "
            "preload readiness.\n\n"
            "Your output: a short readiness checklist for this teammate's "
            "console (PS5 or Xbox Series X|S at launch, no PC date "
            "announced). Say what to check now, what has to wait for the "
            "official download size, and whether they have preordered.\n\n"
            + COMMON_RULES
        ),
    },
    {
        "key": "quartermaster",
        "name": "The Quartermaster",
        "model": "claude-haiku-5-5",  # Cheaper for a quick snacks lookup
        "system": (
            "You are The Quartermaster on a Vice City heist crew. You stock "
            "the fridge and the snack shelf for launch day.\n\n"
            "Your output: a short supply list for this teammate, with a "
            "simple plan for drinks, food that can be eaten one-handed, and "
            "anything to prep the night before. Work their stated weakness "
            "into the list as a treat, not a punchline.\n\n"
            + COMMON_RULES
        ),
    },
]


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    specialist_ids: dict[str, str] = {}
    for spec in SPECIALISTS:
        agent = client.beta.agents.create(
            name=spec["name"],
            model=spec["model"],
            system=spec["system"],
            tools=[{"type": "agent_toolset_20260401"}],
            metadata={
                "hackathon": "partner-basecamp-2026",
                "track": "specialist-swarm",
                "role": spec["key"],
            },
        )
        specialist_ids[spec["key"]] = agent.id
        print(f"  Created {spec['name']:20s} -> {agent.id}")

    Path(".specialist_ids.json").write_text(json.dumps(specialist_ids, indent=2))
    print(f"\nSaved {len(specialist_ids)} specialist IDs to .specialist_ids.json")
    print("Next: python create_cleaner.py")


if __name__ == "__main__":
    main()

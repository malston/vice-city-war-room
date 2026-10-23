"""
Create The Cleaner: the critic that checks every draft before it ships.

Adds "cleaner" to .specialist_ids.json so create_coordinator.py puts it on
the Mastermind's roster. Run after create_specialists.py, which overwrites
that file.

With --review, sends one draft straight to the Cleaner and prints its
verdict. Handy for checking the Cleaner on its own before a full run.

Usage:
    python create_cleaner.py
    python create_cleaner.py --review synthetic-data/bad-draft.md [--facts FILE]
"""

import argparse
import json
import os
from pathlib import Path

from anthropic import Anthropic


MODEL = "claude-opus-5-5"
IDS_PATH = Path(".specialist_ids.json")
DEFAULT_FACTS = Path("synthetic-data/launch-facts.md")

CLEANER_SYSTEM = """\
You are The Cleaner on a Vice City heist crew. You do not write launch plans.
You review them before anything is posted to the team channel, and you
remove the evidence.

You receive one or more drafts plus the facts document (launch-facts). Run
four checks on every draft:

1. Tone. Jokes target the situation, never the person. No roasting anyone,
   their partner, their family, or their cooking, even if they asked for it.
   Anyone who is behind gets an on-ramp, not a punchline.
2. Facts. Every game fact (dates, platforms, prices, editions, bonuses) must
   come from the facts document. Anything else must be called unconfirmed.
   An invented price or date is a failure.
3. Spoilers. No story details, missions, characters' fates, or leak claims,
   even framed as rumor or passed along from someone else.
4. Formatting. Slack formatting only: *bold* with single asterisks, no **,
   no # headings, and no em dashes.

Reply format, exactly:
- First line: VERDICT: PASS or VERDICT: FIX
- Then at most 5 issues, one per line, each naming the draft, the check
  that failed, and the fix.

Be strict. If any check fails, the verdict is VERDICT: FIX.
"""


def make_client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")
    return Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )


def ask_cleaner(
    client: Anthropic, cleaner_id: str, environment_id: str, draft: str, facts: str
) -> str:
    """Send one draft plus the facts to the Cleaner and return its reply text."""
    session = client.beta.sessions.create(
        agent=cleaner_id,
        environment_id=environment_id,
        title="The Cleaner: draft review",
    )
    message = (
        "Review this draft.\n\n"
        f"=====  DOCUMENT: launch-facts.md  =====\n{facts}\n\n"
        f"=====  DOCUMENT: draft.md  =====\n{draft}"
    )
    parts: list[str] = []
    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[
                {"type": "user.message", "content": [{"type": "text", "text": message}]}
            ],
        )
        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        parts.append(block.text)
            elif event.type == "session.status_idle":
                break
    return "".join(parts).strip()


def create(client: Anthropic) -> None:
    if not IDS_PATH.exists():
        raise SystemExit("Missing .specialist_ids.json. Run create_specialists.py first.")
    specialist_ids = json.loads(IDS_PATH.read_text())

    cleaner = client.beta.agents.create(
        name="The Cleaner",
        model=MODEL,
        system=CLEANER_SYSTEM,
        tools=[{"type": "agent_toolset_20260401"}],
        metadata={"project": "gta6-war-room", "role": "cleaner"},
    )
    print(f"Cleaner created: {cleaner.id}")

    specialist_ids["cleaner"] = cleaner.id
    IDS_PATH.write_text(json.dumps(specialist_ids, indent=2))
    print(f"Added cleaner to {IDS_PATH}. Run create_coordinator.py next.")


def review(client: Anthropic, draft_path: Path, facts_path: Path) -> None:
    if not IDS_PATH.exists() or "cleaner" not in json.loads(IDS_PATH.read_text()):
        raise SystemExit("No cleaner in .specialist_ids.json. Run create_cleaner.py first.")
    if not Path(".environment_id").exists():
        raise SystemExit("Missing .environment_id. Run setup_environment.py first.")
    if not facts_path.exists():
        raise SystemExit(f"Missing facts file: {facts_path}")
    if not draft_path.exists():
        raise SystemExit(f"Missing draft: {draft_path}")

    cleaner_id = json.loads(IDS_PATH.read_text())["cleaner"]
    environment_id = Path(".environment_id").read_text().strip()
    print(ask_cleaner(client, cleaner_id, environment_id, draft_path.read_text(), facts_path.read_text()))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--review", type=Path, help="draft to send to the Cleaner")
    parser.add_argument("--facts", type=Path, default=DEFAULT_FACTS)
    args = parser.parse_args(argv)

    client = make_client()
    if args.review:
        review(client, args.review, args.facts)
    else:
        create(client)


if __name__ == "__main__":
    main()

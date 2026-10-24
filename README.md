# Vice City War Room

A crew of AI agents that writes each person in a friend group a funny, personal plan for GTA 6 launch day (November 19, 2026), plus a readiness scoreboard. The results go into a Slack channel where everyone can reply, argue, and react.

## Why this exists

It is a small, fun way to learn the coordinator plus specialists pattern: one boss agent hands work to several expert agents that run at the same time, then combines their answers. Real teams use the same shape for proposal desks and deliverable reviews. This project is built from the specialist-swarm starter kit, using Claude Managed Agents multi-agent (a research preview).

## The crew

| Agent             | Job                                                                                                         |
| ----------------- | ----------------------------------------------------------------------------------------------------------- |
| The Mastermind    | Coordinator. Gives each person a codename, hands the profile to the four specialists, writes the scoreboard |
| The Fixer         | Time off for launch day                                                                                     |
| The Smooth Talker | Spouse and family diplomacy                                                                                 |
| The Wheelman      | Console, storage, downloads                                                                                 |
| The Quartermaster | Fridge and snacks                                                                                           |
| The Cleaner       | Checks every draft for mean jokes, made-up facts, and spoilers before anything is posted                    |

## How a round runs

1. People reply to a kickoff post with a few lines: console, time off, spouse risk, preordered, weakness.
2. Code turns the replies into profile files.
3. The crew writes a plan for each person and a scoreboard.
4. The Cleaner checks the drafts, the owner approves them, and they are posted as separate channel messages.

## Using it from the terminal

There are two kinds of agent here, and you talk to only one of them.

| Agent                       | What it is                                                                                                                               | How you deal with it                                                                                   |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Your Claude Code session    | The assistant you chat with in the terminal. It reads the Slack replies, runs the commands, shows you drafts, and posts what you approve | You type plain-English instructions                                                                    |
| The Mastermind and its crew | Managed Agents running in the cloud. They write the plans                                                                                | You do not chat with them. You start a round, watch their progress scroll by, and read what they wrote |

A round is a conversation with your Claude Code session. This is an illustrative session. The exact wording and output will differ.

```text
you     run round 1
claude  Read the channel replies since the kickoff and saved 3 messages to outputs/messages.json.
claude  python parse_profiles.py --messages outputs/messages.json --kickoff-ts <ts>
        Wrote 3 profile(s) to profiles: mara, otto, pia
claude  python run_war_room.py --round 1 --profiles profiles
        [thread spawned]   The Fixer
        [thread spawned]   The Smooth Talker
        [thread spawned]   The Wheelman
        [thread spawned]   The Quartermaster
        ...
        [swarm finished]
claude  python check_outputs.py --profiles profiles --out outputs/round-1 --facts synthetic-data/launch-facts.md
        All checks pass.
claude  Drafts are in outputs/round-1. Here is Mara's plan: ... Approve, edit, or skip?
you     approve all except Otto's, and make Mara's snack line funnier
claude  Edited Mara's draft. It needs approving again because the text changed. Approve?
you     yes, post them
claude  Posted 3 messages: mara, pia, scoreboard.
```

What stays in your hands:

- Every step runs when you ask for it. You can stop after any step.
- Nothing is posted until you approve it. Editing a draft after you approved it means approving it again.
- If a check fails, Claude tells you what failed and does not post.
- For rounds 2 and 3, Claude also compares the new scoreboard with the last one and adds a "who moved" post.

The step-by-step version, with the exact commands, is in the runbook (`docs/runbook.md`, slice 1). First-time setup is the order in [`docs/contracts.md`](docs/contracts.md), followed by `python dry_run.py`.

## Slices

Each slice has a GitHub issue with a task list. Branch from `main` as `slice-N-name`.

| Slice                          | What it builds                                       | Issue                                                          |
| ------------------------------ | ---------------------------------------------------- | -------------------------------------------------------------- |
| 1. Intake and Slack bridge     | Turns replies into profile files                     | [#1](https://github.com/malston/vice-city-war-room/issues/1)   |
| 2. Crew and swarm core         | The agents and the code that runs them               | [#2](https://github.com/malston/vice-city-war-room/issues/2)   |
| 3. Content and voice           | Facts, playbooks, the heist tone, the score rubric   | [#3](https://github.com/malston/vice-city-war-room/issues/3)   |
| 4. The Cleaner and the dry run | Quality checks and an end-to-end test                | [#4](https://github.com/malston/vice-city-war-room/issues/4)   |
| 5. Post queue and round movers | The approval gate for posts and the "who moved" post | [#10](https://github.com/malston/vice-city-war-room/issues/10) |

The slices meet only at the file formats in [`docs/contracts.md`](docs/contracts.md).

## Getting started

```bash
pip install -r requirements.txt
python -m pytest
```

Slices 2 and 4 also need `ANTHROPIC_API_KEY` in your environment and a workspace with multi-agent access.

1. Branch off `main`.
2. Find your tasks in the plan and write the tests first.
3. Open one PR when your slice is done.

## Docs

- [Design](docs/superpowers/specs/2026-10-23-gta6-war-room-design.md): what we are building and why
- [Implementation plan](docs/superpowers/plans/2026-10-23-gta6-war-room.md): every task, with files, signatures, and tests
- [Contracts](docs/contracts.md): the shared file formats, skill names, and commands
- [Architecture and solution slide](docs/architecture.html): the diagram and one-slide summary for the demo. Open the file in a browser.

## Ground rules

- The repo is public. No real names, chat replies, or keys in it. `.gitignore` covers `.env`, `/profiles/`, and `/outputs/`.
- Nothing posts to Slack without the owner's approval.
- No em dashes in anything the crew writes.
- End-to-end tests use the real API, with no mocks.

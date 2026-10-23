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

## Slices

Each slice has a GitHub issue with a task list. Branch from `main` as `slice-N-name`.

| Slice                          | What it builds                                     | Issue                                                        |
| ------------------------------ | -------------------------------------------------- | ------------------------------------------------------------ |
| 1. Intake and Slack bridge     | Turns replies into profile files                   | [#1](https://github.com/malston/vice-city-war-room/issues/1) |
| 2. Crew and swarm core         | The agents and the code that runs them             | [#2](https://github.com/malston/vice-city-war-room/issues/2) |
| 3. Content and voice           | Facts, playbooks, the heist tone, the score rubric | [#3](https://github.com/malston/vice-city-war-room/issues/3) |
| 4. The Cleaner and the dry run | Quality checks and an end-to-end test              | [#4](https://github.com/malston/vice-city-war-room/issues/4) |

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

## Ground rules

- The repo is public. No real names, chat replies, or keys in it. `.gitignore` covers `.env`, `/profiles/`, and `/outputs/`.
- Nothing posts to Slack without the owner's approval.
- No em dashes in anything the crew writes.
- End-to-end tests use the real API, with no mocks.

## Starter files still in the repo

The Deal Desk files from the starter kit (`run_deal_desk.py`, `stretch_critic_subagent.py`, `scenario-cards.md`, `stretch-goals.md`, and the pricing, legal, and competitive skills and sample data) are still here. The final integration task decides what to delete, with the owner's approval.

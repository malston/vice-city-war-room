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

The step-by-step version, with the exact commands, is in the [runbook](docs/runbook.md). First-time setup is `make crew-setup` (see [Set up the crew](#set-up-the-crew-and-run-the-demo-page)), followed by `python dry_run.py`.

## How it was built

The project was built in six slices. Each has a closed GitHub issue with its task list.

| Slice                          | What it builds                                       | Issue                                                          |
| ------------------------------ | ---------------------------------------------------- | -------------------------------------------------------------- |
| 1. Intake and Slack bridge     | Turns replies into profile files                     | [#1](https://github.com/malston/vice-city-war-room/issues/1)   |
| 2. Crew and swarm core         | The agents and the code that runs them               | [#2](https://github.com/malston/vice-city-war-room/issues/2)   |
| 3. Content and voice           | Facts, playbooks, the heist tone, the score rubric   | [#3](https://github.com/malston/vice-city-war-room/issues/3)   |
| 4. The Cleaner and the dry run | Quality checks and an end-to-end test                | [#4](https://github.com/malston/vice-city-war-room/issues/4)   |
| 5. Post queue and round movers | The approval gate for posts and the "who moved" post | [#10](https://github.com/malston/vice-city-war-room/issues/10) |
| 6. Fake Slack (terminal)       | A stand-in channel, so demos need no Slack           | [#13](https://github.com/malston/vice-city-war-room/issues/13) |

The slices meet only at the file formats in [`docs/contracts.md`](docs/contracts.md).

## Getting started

You need Python 3.10 or newer (it is developed on 3.14) and `pip`.

```bash
pip install -r requirements.txt
python -m pytest
```

The default run skips the tests marked `live`, which call the real API.

## Set up the crew and run the demo page

The crew (the Mastermind, four specialists, and the Cleaner), their seven skills, and a cloud environment live in the Anthropic workspace your API key belongs to. The workspace needs Managed Agents multi-agent access (a research preview). Set the crew up once per workspace, then start the page:

```bash
export ANTHROPIC_API_KEY=<your key>   # or let direnv set it, or put it in .env
make crew-setup                       # creates the agents, skills, and environment
make ui                               # starts the demo page at http://127.0.0.1:8765
```

The targets need `make`, `lsof`, `pgrep`, and `curl`. Run `make` on its own to list them.

| Command           | What it does                                                                                                                                                                         |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `make crew-setup` | Creates the crew, skills, and environment. Refuses if any crew id file exists here; `make crew-setup FORCE=1` makes a new crew and moves the old ids to `outputs/old-workspace-ids/<timestamp>-<pid>/` |
| `make ui`         | Starts the demo page in the background. Its log is `outputs/demo-ui.log`                                                                                                             |
| `make ui-status`  | Shows whether the page is running and whether a step is in flight                                                                                                                    |
| `make ui-stop`    | Stops the page. Refuses while a step is running, because stopping also ends that step; `FORCE=1` stops it anyway                                                                     |
| `make ui-restart` | Stops the page, then starts it again                                                                                                                                                 |
| `make ui-logs`    | Follows the page's log                                                                                                                                                               |

How the key is found:

- A key already in your environment (for example from direnv) is used as is. Without one, the scripts read the repo's `.env`, wherever you run them from. `make` does not read `.env` itself. It runs the scripts, and they do. Nothing in `.env` replaces a variable that is already set. `WAR_ROOM_ENV_FILE` points the scripts at a different file.
- Each script that needs the key prints `Using ANTHROPIC_API_KEY from the environment` or `from .env` when it starts, so you can see which one won. If the API says "Agent not found", check this line first.
- The key must belong to the workspace where the crew was created. A key for a different workspace gets an "Agent not found" error from the API when you run the swarm, and the Crew panel shows a "Session not found" error.
- The crew's ids are kept in gitignored files in the repo folder (`.coordinator_id`, `.specialist_ids.json`, `.environment_id`, `.skill_ids.json`), so each checkout has its own. The swarm step also writes `.last_session_id`, which the Crew panel reads. To use another workspace, switch the key and run `make crew-setup FORCE=1`.

Once the crew exists, `python -m pytest -m live` runs the live tests, and `python dry_run.py` runs the whole crew on fictional people. Besides the checks in `check_outputs.py`, it scans the drafts for phrases planted as bait and confirms the Cleaner was consulted. A dry run takes several minutes and uses API credits.

## Try it without Slack

`fake_slack.py` keeps a stand-in channel in `outputs/demo/channel.json`, so the whole flow runs with no Slack connection. The step-by-step walk-through is [`docs/demo.md`](docs/demo.md). The page started by `make ui` runs the same steps with buttons, and shows the channel, the crew's progress, and the command output as they happen.

## What is where

| Path                                                                                                                    | What it is                                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `parse_profiles.py`, `run_war_room.py`, `check_outputs.py`, `dry_run.py`, `movers.py`, `post_queue.py`, `fake_slack.py` | The commands you run during a round                                                                                                                 |
| `check_key.py`, `create_specialists.py`, `create_cleaner.py`, `create_coordinator.py`, `upload_skills.py`, `setup_environment.py` | One-time setup, run in this order by `make crew-setup`                                                                                              |
| `demo_ui.py`, `demo_ui.html`                                                                                            | The browser demo                                                                                                                                    |
| `war_room/`                                                                                                             | The library behind the commands: key lookup, profile parsing, the round message, session streaming, output checks, the fake channel, movers, and the post queue |
| `skills/`                                                                                                               | The seven skills the crew uses (playbooks, voice, scoring, and the post template)                                                                   |
| `synthetic-data/`                                                                                                       | The launch facts, fictional profiles, test drafts, and sample outputs                                                                               |
| `demo/`                                                                                                                 | The scripted replies the fake channel can seed                                                                                                      |
| `tests/`                                                                                                                | Unit tests, plus `tests/live/` which calls the real API                                                                                             |
| `outputs/`, `profiles/`                                                                                                 | Everything a run produces. Gitignored                                                                                                               |

## What shapes what the crew says

Change these to change the crew's output. After you edit a skill, run `python upload_skills.py` to push it to the agents as a new version. The facts file, the seed replies, and the kickoff post are read directly, so your edits apply the next time you run a round.

| File                                                           | What it controls                                                                                                                                     |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Launch facts](synthetic-data/launch-facts.md)                 | The only game facts the crew may state. Anything not on the list must be called "unconfirmed". `check_outputs.py` checks dates and prices against it |
| [Heist voice](skills/heist-voice/SKILL.md)                     | Tone, joke rules, and codename style. Every agent gets it                                                                                            |
| [Job file template](skills/job-file-template/SKILL.md)         | The layout of each person's plan and of the scoreboard (Mastermind)                                                                                  |
| [Readiness scoring](skills/readiness-scoring/SKILL.md)         | How the 0 to 100 score is worked out (Mastermind)                                                                                                    |
| [PTO playbook](skills/pto-playbook/SKILL.md)                   | Time-off advice, from the `pto_status` field (Fixer)                                                                                                 |
| [Family diplomacy](skills/family-diplomacy/SKILL.md)           | Spouse and family advice, from `spouse_risk` (Smooth Talker)                                                                                         |
| [Launch readiness tech](skills/launch-readiness-tech/SKILL.md) | Console, storage, and connection advice, from `console` and `preordered` (Wheelman)                                                                  |
| [Launch supplies](skills/launch-supplies/SKILL.md)             | Snacks and supplies advice, from `weakness` (Quartermaster)                                                                                          |
| [Seed replies](demo/seed-round-1.json)                         | The scripted friends' replies the fake channel posts in the demo                                                                                     |
| [Kickoff post](docs/kickoff-post.md)                           | The message that starts a round and the five fields people fill in                                                                                   |

## When something goes wrong

| What you see                                | Why, and what to do                                                                                                             |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| "Agent not found" in Command output         | The key belongs to a different workspace than the crew. Use the key the crew was created with, or run `make crew-setup FORCE=1` |
| "Session not found" in the Crew panel       | Same cause                                                                                                                      |
| "Set ANTHROPIC_API_KEY before running."     | No key in your environment or in `.env`. Set one, then `make ui-restart` if the page was already running                        |
| Command output stays on "Running..."        | The page was loaded before the server restarted. Reload the page                                                                               |
| `make ui-stop` says a step is still running | Wait for it, or run `make ui-stop FORCE=1`                                                                                      |
| `make crew-setup` fails partway             | Fix what the output names, then run `make crew-setup FORCE=1`. The output also says where your old ids were moved               |
| `make ui` says the page did not come up     | Read `outputs/demo-ui.log`                                                                                                      |
| A check in `check_outputs.py` fails         | Do not post. The report names the file and the problem, such as a date that is not in `synthetic-data/launch-facts.md`          |

## Working on this repo

- Branch from `main`, keep one change per PR, and write the test first. `python -m pytest` should finish with clean output.
- When you add a command or a `make` target, document it. `tests/test_docs.py` checks the README and the pages under `docs/` for broken links, commands and flags that do not exist, and scripts or targets nobody documents.
- The design and the plan under `docs/superpowers/` are a record of how the project was built. They are not kept in step with the code.

## Docs

- [Design](docs/superpowers/specs/2026-10-23-gta6-war-room-design.md): what we are building and why
- [Implementation plan](docs/superpowers/plans/2026-10-23-gta6-war-room.md): every task, with files, signatures, and tests
- [Contracts](docs/contracts.md): the shared file formats, skill names, and commands
- [Runbook](docs/runbook.md): running a round, step by step
- [Posting guide](docs/posting.md): approving and posting drafts, and the "who moved" post for rounds 2 and 3
- [Kickoff post](docs/kickoff-post.md): the text that starts a round
- [Demo walk-through](docs/demo.md): a full round against the fake channel, no Slack needed
- [Demo script](docs/demo-script.md): a 10-minute talk track for presenting the demo
- [Architecture and solution slide](docs/architecture.html): the diagram and one-slide summary for the demo. Open the file in a browser.

## Ground rules

- The repo is public. No real names, chat replies, or keys in it. `.gitignore` covers `.env`, `/profiles/`, and `/outputs/`.
- Nothing posts to Slack without the owner's approval.
- No em dashes in anything the crew writes.
- End-to-end tests use the real API, with no mocks.

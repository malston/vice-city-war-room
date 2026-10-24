# Contracts

The scripts meet only at these decisions. If one needs to change, update every script and test that reads or writes it.

## Profile file

`profiles/<handle>.json`, one per person who replied.

| Key            | Type                                                       |
| -------------- | ---------------------------------------------------------- |
| `handle`       | string matching `^[a-z0-9][a-z0-9_-]{0,31}$`               |
| `display_name` | string                                                     |
| `console`      | string or `null`                                           |
| `pto_status`   | string or `null`                                           |
| `spouse_risk`  | integer 1-5 or `null`                                      |
| `preordered`   | boolean or `null`                                          |
| `weakness`     | string or `null`                                           |
| `raw_reply`    | string: the person's replies in order, joined by `\n---\n` |

A field the person did not give is `null`.

## Saved-messages file

A JSON list of `{"author_handle": str, "author_name": str, "ts": str, "text": str}`. `ts` is a Slack timestamp string and is compared as a number.

## Facts file

`synthetic-data/launch-facts.md`: one fact per line as `- <fact> (source: <where>)`. Unconfirmed items say `UNCONFIRMED` in the fact text. The crew states only facts from this file and calls anything else "unconfirmed".

## Outputs

Written to `outputs/round-N/`:

- `<handle>.md`: one per profile
- `scoreboard.md`
- `coordinator-transcript.txt`
- `movers.md`: written by `movers.py` for rounds 2 and 3
- `post-queue.json`: written by `post_queue.py`

Only `post_queue.py` reads `movers.md`, and only `post_queue.py` reads or writes `post-queue.json`.

Slack formatting: `*bold*`, no `**`, no `#` headings. No em dashes.

## Scoreboard

One line per person, sorted by score descending, ranks 1 to N, scores 0-100:

`<rank>. <display_name> (<codename>): <score>/100`

A title line and blank lines are allowed. Lines that do not start with a number and a period are ignored by the checks and by `movers.py`. Any line that does start with one must follow the format above.

## Skills

Directory names under `skills/`, each with a `SKILL.md` that has `name` and `description` frontmatter:

`pto-playbook`, `family-diplomacy`, `launch-readiness-tech`, `launch-supplies`, `heist-voice`, `readiness-scoring`, `job-file-template`

## Agent keys

- `.specialist_ids.json`: `fixer`, `smooth_talker`, `wheelman`, `quartermaster`, `cleaner`
- `.coordinator_id`: `mastermind`

## Cleaner reply

First line `VERDICT: PASS` or `VERDICT: FIX`, then at most 5 issues.

## Commands

```text
python parse_profiles.py --messages FILE --kickoff-ts TS --out DIR
python run_war_room.py --round N --profiles DIR [--facts FILE] [--prior-scoreboard FILE] [--out DIR] [--force]
python check_outputs.py --profiles DIR --out DIR --facts FILE
python dry_run.py [--skip-run] [--out DIR] [--facts FILE]
python movers.py --prev FILE --curr FILE --out FILE
python post_queue.py build --profiles DIR --out DIR
python post_queue.py list --out DIR
python post_queue.py approve --out DIR (ID... | --all)
python post_queue.py next --out DIR
python post_queue.py mark-posted --out DIR ID
```

For `run_war_room.py`, `--out` defaults to `outputs/round-N`. The README lists the `make` targets, and the [posting guide](posting.md) explains the queue.

## Local id files

The setup scripts record what they created in files in the repo folder. All of them are gitignored, so each checkout has its own, and they only mean something for the workspace that the API key belongs to.

| File                   | Written by                                        | Holds                                                     |
| ---------------------- | ------------------------------------------------- | --------------------------------------------------------- |
| `.specialist_ids.json` | `create_specialists.py`, then `create_cleaner.py` | The specialists' and the Cleaner's agent ids              |
| `.coordinator_id`      | `create_coordinator.py`                           | The Mastermind's agent id                                 |
| `.skill_ids.json`      | `upload_skills.py`                                | The uploaded skills' ids                                  |
| `.environment_id`      | `setup_environment.py`                            | The cloud environment's id                                |
| `.last_session_id`     | `run_war_room.py`                                 | The session of the latest run, which the Crew panel shows |

An id from another workspace fails with "not found". Switch the key and run `make crew-setup FORCE=1` to create a crew in the new workspace.

## Demo channel

For demos without Slack, `fake_slack.py` keeps a channel in `outputs/demo/channel.json` (override with `--channel FILE`). It is a JSON list of messages in the saved-messages format. `fake_slack.py read` writes the saved-messages file that `parse_profiles.py` reads and leaves out the bot's own posts (handle `war-room`). The real flow does not use this file.

```text
python fake_slack.py post (--file FILE | --text TEXT) [--fenced] [--as HANDLE] [--name NAME]
python fake_slack.py reply --as HANDLE --text TEXT [--name NAME]
python fake_slack.py read [--since TS] --out FILE [--include-bot]
python fake_slack.py show [--since TS]
python fake_slack.py seed [--file FILE] [--delay SECONDS]
python fake_slack.py reset
```

## Setup order

1. `python create_specialists.py`
2. `python create_cleaner.py`
3. `python create_coordinator.py`
4. `python upload_skills.py`
5. `python setup_environment.py`

`create_specialists.py` overwrites `.specialist_ids.json`, so run it before `create_cleaner.py`.

`make crew-setup` runs these five in order. It first moves any old id files to `outputs/old-workspace-ids/<timestamp>/`, because `setup_environment.py` creates nothing while `.environment_id` exists. It refuses to run when `.coordinator_id` exists, unless you add `FORCE=1`, because every run creates new agents.

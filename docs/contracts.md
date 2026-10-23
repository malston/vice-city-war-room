# Contracts

The four slices meet only at these decisions. If a slice needs one changed, comment on all four slice issues first.

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
- `movers.md`: written by `movers.py` for rounds 2 and 3 (slice 5)
- `post-queue.json`: written by `post_queue.py` (slice 5)

Other slices ignore `movers.md` and `post-queue.json`.

Slack formatting: `*bold*`, no `**`, no `#` headings. No em dashes.

## Scoreboard

One line per person, sorted by score descending, ranks 1 to N, scores 0-100:

`<rank>. <display_name> (<codename>): <score>/100`

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
```

`--out` defaults to `outputs/round-N`.

## Setup order

1. `python create_specialists.py`
2. `python create_cleaner.py`
3. `python create_coordinator.py`
4. `python upload_skills.py`
5. `python setup_environment.py`

`create_specialists.py` overwrites `.specialist_ids.json`, so run it before `create_cleaner.py`.

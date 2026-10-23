# GTA 6 War Room Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A heist-crew swarm that turns teammates' chat replies into personal launch plans and a team scoreboard, checked by a critic before anything is posted.

**Architecture:** The starter's flat scripts stay (create agents, upload skills, run a session). Testable logic moves into a small `war_room/` package. Four slices meet only at the file contracts in Task 0, so four people can work in parallel. Slack stays outside the code: the owner's Claude session reads replies and posts approved drafts.

**Tech Stack:** Python 3, `anthropic` SDK with Managed Agents multi-agent (beta header `managed-agents-2026-04-01`), pytest.

**Spec:** `docs/superpowers/specs/2026-10-23-gta6-war-room-design.md`

## Global Constraints

- Real profiles and outputs are gitignored. The repo is public, so no coworker data gets pushed.
- Facts file contains only what the channel FAQ states: release date November 19, 2026; PS5 and Xbox Series X|S at launch; no PC date announced; pre-orders opened June 25, 2026; digital via PlayStation Store and Microsoft Store; price, editions, and bonuses not announced as of August; Thanksgiving is one week after launch. Anything else is called "unconfirmed" in the output.
- No em dashes in generated posts.
- Nothing posts to Slack without Mark's approval. No Slack credentials in the code.
- Needs `ANTHROPIC_API_KEY` in the environment. Multi-agent is a research preview, so the workspace needs access.
- No Word document output, no memory tool, no live bot, no spoilers or leak speculation.
- Agent behavior is verified against the real API with no mocks.
- Script style follows the starter: module docstring with `Usage:`, a `main()`, and `raise SystemExit("...")` for setup errors.

## Review Focus

1. A reply that quotes the kickoff back with blank labels (`Console:`) gives `None`, never an empty string. Pinned in Task 1.
2. A second, partial reply updates only the fields it gives and never blanks earlier ones. Pinned in Task 1.
3. A hostile handle or an agent-produced filename like `../../x.md` cannot write outside its folder. Pinned in Tasks 1 and 4.
4. Spouse risk of `0`, `9`, or `high` becomes `None`. Pinned in Task 1.
5. A scoreboard that omits someone, is unsorted, or has a score outside 0-100 fails the check. Pinned in Task 11.

## File Structure

| Path                                                                                                                                  | Slice | Responsibility                            |
| ------------------------------------------------------------------------------------------------------------------------------------- | ----- | ----------------------------------------- |
| `docs/contracts.md`, `pytest.ini`, `.gitignore`                                                                                       | 0     | Shared contracts and project setup        |
| `war_room/profiles.py`, `parse_profiles.py`, `docs/kickoff-post.md`, `docs/runbook.md`                                                | 1     | Replies to profile files                  |
| `war_room/context.py`, `war_room/session.py`, `create_specialists.py`, `create_coordinator.py`, `upload_skills.py`, `run_war_room.py` | 2     | Agents and the runner                     |
| `synthetic-data/launch-facts.md`, `skills/<name>/SKILL.md` (7 skills)                                                                 | 3     | Facts, playbooks, voice, rubric, template |
| `war_room/checks.py`, `check_outputs.py`, `create_cleaner.py`, `dry_run.py`, `synthetic-data/profiles/`, `tests/live/`                | 4     | Quality gate and dry run                  |

Each slice branches from `main` as `slice-N-<name>` and opens its own PR.

---

## Task 0: Shared scaffold (Mark, before the slices start)

**Files:**

- Create: `docs/contracts.md`, `pytest.ini`, `.gitignore`, `war_room/__init__.py` (empty)
- Modify: `requirements.txt` (add `pytest`)

- [ ] **Step 1: Write `.gitignore`** with these entries: `.env`, `profiles/`, `outputs/`, `.specialist_ids.json`, `.coordinator_id`, `.environment_id`, `.last_session_id`, `__pycache__/`, `.pytest_cache/`, `.venv/`.
- [ ] **Step 2: Write `pytest.ini`**: `pythonpath = .`, `testpaths = tests`, a `live` marker described as "needs ANTHROPIC_API_KEY and created agents", and `addopts = -m "not live"`.
- [ ] **Step 3: Write `docs/contracts.md`** containing exactly these decisions:
  - Profile file `profiles/<handle>.json`, keys: `handle`, `display_name`, `console`, `pto_status`, `spouse_risk` (int 1-5), `preordered` (bool), `weakness`, `raw_reply`. A field not given is `null`. `handle` matches `^[a-z0-9][a-z0-9_-]{0,31}$`. `raw_reply` is the person's replies in order, joined by `\n---\n`.
  - Saved-messages file: a JSON list of `{"author_handle": str, "author_name": str, "ts": str, "text": str}`.
  - Facts file `synthetic-data/launch-facts.md`: one fact per line as `- <fact> (source: <where>)`. Unconfirmed items say `UNCONFIRMED` in the fact text.
  - Outputs in `outputs/round-N/`: `<handle>.md`, `scoreboard.md`, `coordinator-transcript.txt`. Slack formatting: `*bold*`, no `**`, no `#` headings.
  - Scoreboard: one line per person, sorted by score descending: `<rank>. <display_name> (<codename>): <score>/100`.
  - Skill directory names: `pto-playbook`, `family-diplomacy`, `launch-readiness-tech`, `launch-supplies`, `heist-voice`, `readiness-scoring`, `job-file-template`.
  - Agent keys: `fixer`, `smooth_talker`, `wheelman`, `quartermaster`, `cleaner` (all in `.specialist_ids.json`), `mastermind` (in `.coordinator_id`).
  - Cleaner reply: first line `VERDICT: PASS` or `VERDICT: FIX`, then at most 5 issues.
  - Commands: `python parse_profiles.py --messages FILE --kickoff-ts TS --out DIR` and `python run_war_room.py --round N --profiles DIR [--facts FILE] [--prior-scoreboard FILE] [--out DIR] [--force]`; `--out` defaults to `outputs/round-N`.
  - Setup order: `create_specialists.py`, `create_cleaner.py`, `create_coordinator.py`, `upload_skills.py`, `setup_environment.py`.
- [ ] **Step 4: Verify.** Run `git check-ignore -v .env profiles/x.json outputs/a.md`. Expected: three matching lines. Run `python -m pytest --collect-only -q`. Expected: no errors.
- [ ] **Step 5: Commit** on `gta6-war-room` (`git commit -m "chore: add shared contracts and project setup"`), open a PR to `main`, and merge it before any slice branches.

---

# Slice 1: Intake and Slack bridge

## Task 1: Reply parsing

**Files:**

- Create: `war_room/profiles.py`, `tests/test_profiles.py`

**Interfaces:**

- Produces: `Profile` frozen dataclass with fields exactly as the profile contract; `HANDLE_RE`; `parse_replies(messages: list[dict], kickoff_ts: str) -> list[Profile]` (sorted by handle); `write_profiles(profiles: list[Profile], out_dir: Path) -> list[Path]`.

- [ ] **Step 1: Write failing tests** in `tests/test_profiles.py`:
  - `test_labeled_reply_fills_all_fields`: text `"Console: PS5\nPTO: approved Nov 19-20\nSpouse risk: 3\nPreordered: yes\nWeakness: snacks"` gives `console="PS5"`, `pto_status="approved Nov 19-20"`, `spouse_risk=3`, `preordered=True`, `weakness="snacks"`.
  - `test_free_text_risk_extracts_number`: `"Spouse risk: a solid 4"` gives `4`.
  - `test_out_of_range_or_non_numeric_risk_is_none`: parametrized over `"0"`, `"9"`, `"high"`, expects `None`.
  - `test_blank_label_value_is_none`: `"Console:\nPreordered:"` gives `None` for both.
  - `test_preordered_variants`: parametrized `"yes"`, `"yep"` give `True`; `"nope"`, `"not yet"` give `False`; `"maybe"` gives `None`.
  - `test_missing_fields_are_none_and_raw_reply_kept`.
  - `test_second_reply_updates_only_fields_it_gives`: first `"Console: PS5\nPreordered: no"`, later `"Preordered: yes"` gives `console="PS5"`, `preordered=True`, and `raw_reply` joined with `\n---\n`.
  - `test_messages_at_or_before_kickoff_are_ignored` and `test_author_with_no_reply_gets_no_profile`.
  - `test_slack_timestamps_compare_numerically`: `"1792773218.446639"` is after `"999.1"`.
  - `test_handle_with_path_characters_raises_value_error`: handle `"../etc"`.
  - `test_write_profiles_json_has_exactly_contract_keys`.
- [ ] **Step 2: Run** `python -m pytest tests/test_profiles.py -v`. Expected: FAIL, module not found.
- [ ] **Step 3: Implement `profiles.py`.** Line-based `label: value` parse. Case-insensitive aliases in a `LABEL_ALIASES` constant: `console`; `pto`, `time off`; `spouse risk`, `spouse`, `risk`; `preordered`, `pre-ordered`, `pre-order`; `weakness`. Risk is the first integer in the value, kept only when 1-5. Merge replies per field, later non-null values win.
- [ ] **Step 4: Run** the same command. Expected: all PASS, no warnings.
- [ ] **Step 5: Commit** (`feat: parse channel replies into profiles`).

## Task 2: Command, kickoff post, and runbook

**Files:**

- Create: `parse_profiles.py`, `tests/test_parse_profiles_cli.py`, `docs/kickoff-post.md`, `docs/runbook.md`

**Interfaces:**

- Consumes: `parse_replies`, `write_profiles` from Task 1.
- Produces: `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write failing test** `test_cli_writes_one_profile_per_replier`: a `tmp_path` messages file with two repliers and one earlier message; run `main(["--messages", f, "--kickoff-ts", "100.0", "--out", out])`; expect return `0` and exactly two `.json` files.
- [ ] **Step 2: Run** `python -m pytest tests/test_parse_profiles_cli.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `parse_profiles.py`** with argparse and the starter's script style. Exit with `SystemExit` and a clear message when the messages file is missing or not valid JSON.
- [ ] **Step 4: Run** `python -m pytest -q`. Expected: all PASS.
- [ ] **Step 5: Write `docs/kickoff-post.md`** (Slack formatting, fictional-safe wording) listing the five intake fields and telling people to react to the plan they like best, and `docs/runbook.md`: (1) owner approves and posts the kickoff, (2) Claude session saves replies to a messages file, (3) `parse_profiles.py`, (4) `run_war_room.py`, (5) `check_outputs.py`, (6) owner reviews and approves each post before it is sent.
- [ ] **Step 6: Commit** (`feat: add parse_profiles command and runbook`), open a PR.

---

# Slice 2: Crew and swarm core

## Task 3: Context builder

**Files:**

- Create: `war_room/context.py`, `tests/test_context.py`

**Interfaces:**

- Produces: `MAX_PROFILES = 8`; `build_user_message(round_n: int, profiles_dir: Path, facts_path: Path, prior_scoreboard: Path | None = None, force: bool = False) -> str`. The message lists every handle, tells the Mastermind to write `<handle>.md` for each plus `scoreboard.md`, and inlines each file as `=====  DOCUMENT: <name>  =====` like the starter.

- [ ] **Step 1: Write failing tests:** `test_message_lists_every_handle`, `test_message_includes_facts_text`, `test_prior_scoreboard_included_only_when_given`, `test_empty_profiles_dir_raises_value_error`, `test_more_than_max_profiles_raises_and_names_force`, `test_force_allows_more_than_max`, `test_missing_facts_file_raises_file_not_found`.
- [ ] **Step 2: Run** `python -m pytest tests/test_context.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** One session for all profiles (my call: the scoreboard needs everyone, and one coordinator fans out in parallel).
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** (`feat: build the round message for the Mastermind`).

## Task 4: Session helpers

**Files:**

- Create: `war_room/session.py`, `tests/test_session.py`

**Interfaces:**

- Produces: `SessionResult` frozen dataclass (`session_id: str`, `text: str`); `run_session(client: Anthropic, agent_id: str, environment_id: str, message: str, title: str) -> SessionResult`; `download_files(client: Anthropic, session_id: str, out_dir: Path) -> list[Path]`; `safe_output_path(out_dir: Path, filename: str) -> Path`.

- [ ] **Step 1: Write failing tests** for `safe_output_path`: `test_strips_directories_from_filename` (`"../../x.md"` gives `out_dir / "x.md"`), `test_plain_filename_unchanged`, `test_empty_filename_raises_value_error`.
- [ ] **Step 2: Run** `python -m pytest tests/test_session.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement all three.** Move the streaming loop and file download out of `run_deal_desk.py` unchanged, using `safe_output_path` for every download. `run_session` and `download_files` are verified by the live run in Task 7.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** (`feat: add session and download helpers`).

## Task 5: Crew definitions

**Files:**

- Modify: `create_specialists.py`, `create_coordinator.py`
- Test: `tests/test_agent_definitions.py`

**Interfaces:**

- Produces: `SPECIALISTS` (list of dicts with `key`, `name`, `model`, `system`) with keys `fixer`, `smooth_talker`, `wheelman`, `quartermaster`; `COORDINATOR_SYSTEM: str`. `create_coordinator.py` builds its roster from every id in `.specialist_ids.json` (so the Cleaner joins when it exists) and writes `.coordinator_id`.

- [ ] **Step 1: Write failing tests:** `test_specialist_keys_are_the_four_roles`; `test_every_specialist_prompt_limits_facts_to_the_facts_document` (asserts `"launch-facts"` and `"unconfirmed"` appear); `test_every_specialist_prompt_forbids_em_dashes`; `test_coordinator_prompt_names_every_specialist_name`; `test_coordinator_prompt_defines_cleaner_loop` (asserts `"VERDICT: FIX"` and `"twice"`); `test_coordinator_prompt_defines_scoreboard_line_format` (asserts `"/100"`).
- [ ] **Step 2: Run** `python -m pytest tests/test_agent_definitions.py -v`. Expected: FAIL.
- [ ] **Step 3: Replace the four deal-desk specialists** with Fixer (PTO), Smooth Talker (spouse and family), Wheelman (console, storage, wired connection, preload), Quartermaster (fridge and snacks). Each prompt: input is one profile plus the facts document; output about 150 words; state only facts from the facts document, otherwise say unconfirmed; jokes target the situation, never the person. Before choosing models, check which IDs the workspace accepts (the starter uses `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-opus-4-7`).
- [ ] **Step 4: Rewrite `COORDINATOR_SYSTEM`** as the Mastermind: assign each person a codename; delegate to all four specialists in one message per person, all people in parallel; apply the `readiness-scoring` and `job-file-template` skills; write `<handle>.md` and `scoreboard.md` using the contract line format; if the Cleaner is on the roster, send all drafts plus the facts text to it, revise on `VERDICT: FIX` and resubmit at most twice; no em dashes. Name the agent `The Mastermind`.
- [ ] **Step 5: Run** the same command. Expected: PASS.
- [ ] **Step 6: Commit** (`feat: define the heist crew and the Mastermind`).

## Task 6: Skill upload

**Files:**

- Modify: `upload_skills.py`
- Test: `tests/test_upload_skills.py`

**Interfaces:**

- Produces: `SKILL_TO_AGENTS: dict[str, list[str]]`; `load_agent_ids() -> dict[str, str]` (merges `.specialist_ids.json` and `.coordinator_id` as `mastermind`).

- [ ] **Step 1: Write failing tests:** `test_load_agent_ids_includes_mastermind` (uses `monkeypatch.chdir(tmp_path)` and real files); `test_skill_map_covers_the_seven_contract_skills`; `test_every_mapped_agent_key_is_a_contract_agent_key`; `test_heist_voice_goes_to_all_six_agents`.
- [ ] **Step 2: Run** `python -m pytest tests/test_upload_skills.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** Map `pto-playbook` to `fixer`, `family-diplomacy` to `smooth_talker`, `launch-readiness-tech` to `wheelman`, `launch-supplies` to `quartermaster`, `heist-voice` to all six agents, `readiness-scoring` and `job-file-template` to `mastermind`. Keep the starter's reuse-by-title and skip-when-no-`SKILL.md` behavior.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** (`feat: attach skills to the crew`).

## Task 7: Runner and live smoke run

**Files:**

- Create: `run_war_room.py`, `tests/test_run_war_room.py`

**Interfaces:**

- Consumes: `build_user_message`, `run_session`, `download_files`.
- Produces: `parse_args(argv: list[str] | None = None) -> argparse.Namespace` with `round`, `profiles`, `facts`, `prior_scoreboard`, `out`, `force`.

- [ ] **Step 1: Write failing tests:** `test_round_is_required`; `test_out_defaults_to_outputs_round_n` (`parse_args(["--round","1"]).out == Path("outputs/round-1")`); `test_explicit_out_wins`.
- [ ] **Step 2: Run** `python -m pytest tests/test_run_war_room.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `run_war_room.py`:** check `ANTHROPIC_API_KEY`, `.coordinator_id`, `.environment_id`; build the message; run the session; write `coordinator-transcript.txt`; download files into `--out`; print the session URL.
- [ ] **Step 4: Run** `python -m pytest -q`. Expected: all PASS.
- [ ] **Step 5: Live smoke run.** After the setup order in Task 0 and two hand-made profiles, run `python run_war_room.py --round 1 --profiles <dir> --out outputs/smoke`. Expected: thread-spawned lines for the four specialists, then `<handle>.md` for each profile and `scoreboard.md` in `outputs/smoke/`.
- [ ] **Step 6: Commit** (`feat: add the war room runner`), open a PR.

---

# Slice 3: Content and voice

## Task 8: Facts file and content lint

**Files:**

- Create: `synthetic-data/launch-facts.md`, `tests/test_content.py`

**Interfaces:**

- Produces: facts lines in the contract format.

- [ ] **Step 1: Write failing tests** in `tests/test_content.py`, scoped to the seven contract skill names: `test_every_war_room_skill_has_name_and_description_frontmatter`; `test_skill_name_matches_directory`; `test_no_em_dashes_in_war_room_content`; `test_every_fact_line_has_a_source` (each `- ` line in the facts file ends with `(source: ...)`); `test_facts_file_contains_the_six_faq_facts` (asserts `"November 19, 2026"`, `"PlayStation 5"`, `"June 25, 2026"`, `"PlayStation Store"`, `"UNCONFIRMED"`, `"Thanksgiving"`).
- [ ] **Step 2: Run** `python -m pytest tests/test_content.py -v`. Expected: FAIL.
- [ ] **Step 3: Write the facts file** from the six constraint facts. Price, editions, and bonuses are marked `UNCONFIRMED`.
- [ ] **Step 4: Verify each fact against official sources** (the publisher's site and the PlayStation and Xbox store listings). Record the source on each line. A news article alone is not a source.
- [ ] **Step 5: Run** the same command. The facts tests PASS. The skill tests pass after Tasks 9 and 10.
- [ ] **Step 6: Commit** (`docs: add launch facts and content lint`).

## Task 9: Specialist playbooks

**Files:**

- Create: `skills/pto-playbook/SKILL.md`, `skills/family-diplomacy/SKILL.md`, `skills/launch-readiness-tech/SKILL.md`, `skills/launch-supplies/SKILL.md`

- [ ] **Step 1: Write each playbook** with `name` and `description` frontmatter and a "when the profile says X, do Y" table keyed to its profile field: `pto_status` (Fixer), `spouse_risk` (Smooth Talker, covers couples co-op as the fallback), `console` and `preordered` (Wheelman, from the FAQ prep list: payment details, wired connection, console and network updates, clear storage; a PS4 owner needs a new console), `weakness` (Quartermaster). Every rule is something the FAQ supports; anything else is marked unconfirmed.
- [ ] **Step 2: Run** `python -m pytest tests/test_content.py -v`. Expected: the four playbook names pass the frontmatter and em-dash tests.
- [ ] **Step 3: Commit** (`docs: add specialist playbooks`).

## Task 10: Voice, rubric, and template

**Files:**

- Create: `skills/heist-voice/SKILL.md`, `skills/readiness-scoring/SKILL.md`, `skills/job-file-template/SKILL.md`
- Modify: `tests/test_content.py`

- [ ] **Step 1: Add failing test** `test_voice_skill_states_the_joke_rules`: the voice skill text contains `"situation"`, `"never the person"`, `"on-ramp"`, `"no spoilers"`, `"no em dashes"`.
- [ ] **Step 2: Write `heist-voice`:** codename style (movie-heist nicknames, one or two words), tone, the joke rules from the test, and the on-ramp rule for anyone who is behind.
- [ ] **Step 3: Write `readiness-scoring`:** score out of 100 = preorder (yes 25, no 5, unknown 10) + console (PS5 or Xbox Series X|S 25, anything else or unknown 0) + PTO (approved 30, requested 20, not requested 5, unknown 0) + spouse risk (`(5 - risk) * 5`, unknown 10). `weakness` earns no points and feeds the jokes.
- [ ] **Step 4: Write `job-file-template`:** the per-person post and the scoreboard in the contract line format, in Slack formatting (`*bold*`, no `**`, no `#` headings).
- [ ] **Step 5: Run** `python -m pytest tests/test_content.py -v`. Expected: all PASS.
- [ ] **Step 6: Commit** (`docs: add heist voice, scoring rubric, and post template`), open a PR.

---

# Slice 4: The Cleaner and the dry run

## Task 11: Output checks

**Files:**

- Create: `war_room/checks.py`, `check_outputs.py`, `tests/test_checks.py`

**Interfaces:**

- Produces: `CheckResult` frozen dataclass (`name: str`, `passed: bool`, `detail: str`); `check_outputs(profiles_dir: Path, out_dir: Path, facts_path: Path) -> list[CheckResult]`; `unsupported_claims(output_text: str, allowed_texts: list[str]) -> set[str]` (dollar amounts and `Month D` dates not found in any allowed text); `forbidden_found(out_dir: Path, substrings: list[str]) -> list[str]`; `transcript_consulted_cleaner(transcript: str) -> bool`; `format_report(results: list[CheckResult]) -> str`.

- [ ] **Step 1: Write failing tests** with real files in `tmp_path`:
  - `test_missing_person_file_fails` and `test_missing_scoreboard_fails`
  - `test_scoreboard_omitting_a_person_fails`, `test_unsorted_scoreboard_fails`, `test_score_over_100_fails`, `test_valid_scoreboard_passes`
  - `test_em_dash_in_any_output_fails`
  - `test_double_asterisk_bold_fails` and `test_hash_heading_fails`
  - `test_dollar_amount_not_in_facts_is_unsupported`, `test_date_in_facts_is_supported`, `test_date_from_profile_is_supported`, `test_text_without_claims_returns_empty_set`
  - `test_forbidden_substring_is_reported`
  - `test_transcript_with_verdict_line_counts_as_consulted`
  - `test_report_is_one_line_per_check_and_lists_at_most_five_failure_details`
- [ ] **Step 2: Run** `python -m pytest tests/test_checks.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** Scoreboard lines match `^\d+\. .+ \(.+\): (\d{1,3})/100$`; ranks run 1 to N, and scores never increase down the list. Every `display_name` from the profiles appears.
- [ ] **Step 4: Add `check_outputs.py`:** `--profiles`, `--out`, `--facts`; prints `format_report`; exits 1 on any failure.
- [ ] **Step 5: Run** `python -m pytest -q`. Expected: all PASS.
- [ ] **Step 6: Commit** (`feat: add deterministic output checks`).

## Task 12: Synthetic crew and bait

**Files:**

- Create: `synthetic-data/profiles/jules.json`, `mara.json`, `otto.json`, `pia.json`, `sol.json`, `synthetic-data/bait.json`
- Test: `tests/test_synthetic_data.py`

- [ ] **Step 1: Write failing tests:** `test_every_synthetic_profile_matches_the_contract_keys`, `test_every_synthetic_handle_matches_handle_re`, `test_bait_file_names_substrings_present_in_the_bait_profiles`.
- [ ] **Step 2: Run** `python -m pytest tests/test_synthetic_data.py -v`. Expected: FAIL.
- [ ] **Step 3: Write five fictional profiles.** `mara`'s `raw_reply` asks the crew to roast a spouse's cooking (mean-joke bait). `otto`'s `raw_reply` passes along a made-up leak about a final mission (spoiler bait). `pia` has mostly `null` fields (the behind-on-everything on-ramp case). The other two are ordinary. `bait.json` lists the `forbidden_substrings` taken from those two replies.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** (`test: add synthetic crew with bait`).

## Task 13: The Cleaner

**Files:**

- Create: `create_cleaner.py`, `tests/test_cleaner_prompt.py`, `tests/live/test_cleaner_live.py`, `synthetic-data/bad-draft.md`, `synthetic-data/good-draft.md`

**Interfaces:**

- Consumes: `run_session` from Task 4.
- Produces: `CLEANER_SYSTEM: str`. `create_cleaner.py` creates `The Cleaner` and adds `"cleaner"` to `.specialist_ids.json`.

- [ ] **Step 1: Write failing tests.** Unit: `test_cleaner_prompt_defines_both_verdicts` (asserts `"VERDICT: PASS"` and `"VERDICT: FIX"`), `test_cleaner_prompt_lists_the_four_checks` (tone, facts, spoilers, formatting). Live, marked `@pytest.mark.live`: `test_bad_draft_gets_fix_verdict` (reply starts with `VERDICT: FIX`) and `test_good_draft_gets_pass_verdict` (starts with `VERDICT: PASS`); both fail with a clear message if `.environment_id` or the Cleaner id is missing.
- [ ] **Step 2: Run** `python -m pytest tests/test_cleaner_prompt.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `create_cleaner.py`** modeled on `stretch_critic_subagent.py`, minus the coordinator update. Prompt: receives drafts plus the facts text; checks that jokes target the situation and never the person, that facts come only from the facts text, that nothing is a spoiler or leak claim, and Slack formatting with no em dashes; first line `VERDICT: PASS` or `VERDICT: FIX`, then at most 5 issues.
- [ ] **Step 4: Write the drafts.** `bad-draft.md` contains a roast of a spouse, an invented price, a leak claim, and `**bold**`. `good-draft.md` is clean and uses only facts from the facts file.
- [ ] **Step 5: Run** the unit tests, expect PASS. Then, after setup, run `python -m pytest -m live -v`. Expected: both live tests PASS.
- [ ] **Step 6: Commit** (`feat: add the Cleaner critic`).

## Task 14: Dry run

**Files:**

- Create: `dry_run.py`

**Interfaces:**

- Consumes: `check_outputs`, `forbidden_found`, `transcript_consulted_cleaner`, `format_report`.

- [ ] **Step 1: Implement `dry_run.py`.** Run `run_war_room.py --round 1 --profiles synthetic-data/profiles --out outputs/dry-run` as a subprocess with output going to `outputs/dry-run/run.log`; print only the last 15 log lines. Then run `check_outputs`, `forbidden_found` with `bait.json`, and `transcript_consulted_cleaner` on the transcript. Print the compact report, say where the full log is, and exit 1 on any failure.
- [ ] **Step 2: Run** `python dry_run.py`. Expected: every check line says PASS, the report names no forbidden text, and the exit code is `0`.
- [ ] **Step 3: Commit** (`feat: add the end-to-end dry run`), open a PR.

---

## Task 15: Integration (Mark, after the four PRs merge)

- [ ] **Step 1:** Run the setup order from Task 0, then `python dry_run.py`. Expected: PASS.
- [ ] **Step 2:** Ask Mark before deleting the deal-desk leftovers: `run_deal_desk.py`, `stretch_critic_subagent.py`, `skills/pricing-playbook`, `skills/legal-checklist`, `skills/competitive-intel`, `synthetic-data/rfp-acme-corp.md`, `synthetic-data/past-wins.json`, `synthetic-data/product-overview.md`. Delete only what Mark approves.
- [ ] **Step 3:** Draft the kickoff post from `docs/kickoff-post.md` and show it to Mark. Post only after approval.

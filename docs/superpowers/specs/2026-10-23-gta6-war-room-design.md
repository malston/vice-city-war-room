# GTA 6 War Room: Vice City Heist Crew

Short design. Date: 2026-10-23. Size: small project.

## Intent

Mark wants a fun, shareable agent for a team chat channel (Dana, Theo, Priya, Mark). The channel already runs a parody of an enterprise activation engagement: "go-live on the 19th", "dry run", a launch FAQ, spouse-risk jokes, `#nospoilers`.

The agent plays along. Each person replies with a short "customer profile". A swarm of specialists, cast as a Vice City heist crew, writes each person a personal launch plan ("the job") and a team readiness scoreboard. The goal is banter and participation, not a deliverable. It is also a hands-on way for Mark to learn the coordinator plus specialists pattern from the specialist-swarm starter kit.

## Goals

- Each person who replies gets a funny, personal plan posted in the channel.
- A team scoreboard gives people something to argue about.
- Three rounds before launch keep the banter going: kickoff, mid-point update, launch week.
- Reactions on posts pick the best plan.
- The visible parallel fan-out of specialists works as a demo for Mark.

## Non-goals

- No live Slack bot, no Slack credentials in the code.
- No Word document output.
- No memory tool or cross-session memory. Round 2 and 3 read the previous round's output files.
- No speculation about game content, leaks, or spoilers.

## Anti-goals

- Anyone feels roasted, exposed, or singled out. Priya said they are behind, so their plan is an on-ramp.
- The agent states game facts that are not in the facts file.
- Anything posts to Slack without Mark's approval.
- Coworkers' replies or generated plans land in a public repo.

## The crew (cast)

| Role                     | Heist job                                              | Launch job                                             |
| ------------------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| Mastermind (coordinator) | Runs the job, assigns codenames, writes the scoreboard | Synthesizes the plans                                  |
| The Fixer                | Gets the crew inside                                   | PTO strategy for Nov 19-20                             |
| The Smooth Talker        | Handles the people at the door                         | Spouse and family diplomacy                            |
| The Wheelman             | Owns the getaway                                       | Console, storage, wired connection, preload readiness  |
| The Quartermaster        | Supplies the crew                                      | Fridge, snacks, no drive-thru during the first heist   |
| The Cleaner (critic)     | Removes evidence                                       | Checks tone, facts, and spoilers before anything ships |

The four specialists run in parallel per person. The Cleaner reviews the Mastermind's draft before it is final.

## Constraints

- Built on the specialist-swarm fork: Anthropic SDK, Managed Agents multi-agent (research preview, so workspace access is needed), and an `ANTHROPIC_API_KEY`.
- Real profiles and outputs are gitignored. The fork lives on GitHub under `malston`, so no coworker data gets pushed.
- Facts file contains only what the channel FAQ states: release date November 19, 2026; PS5 and Xbox Series X|S at launch; no PC date announced; pre-orders opened June 25, 2026; digital via PlayStation Store and Microsoft Store; price, editions, and bonuses not announced as of August; Thanksgiving is one week after launch. Anything else is called "unconfirmed" in the output.
- No em dashes in generated posts (Mark's style rule).

## Approaches considered

1. Slack-agnostic swarm with Mark's Claude session as the Slack bridge. **Chosen.** Profiles go in as a file, Slack-formatted plans come out. In-session, Claude reads channel replies, drafts posts, and posts only after Mark approves.
2. Live bot in the channel. Rejected for now: needs a Slack app, tokens, and hosting, and risks an unapproved post in the company workspace. Revisit if the group loves it.
3. Script only, manual copy and paste. Rejected: loses the interaction Mark wants.

Mark deferred the choice to Claude's judgment.

## How a round works

1. Mark approves and posts the kickoff message. It lists the intake fields: console, PTO status, spouse risk (1-5), preordered, biggest weakness. Free-text replies are fine.
2. Claude reads the channel replies after the kickoff and writes one profile per replier.
3. The swarm runs against the profiles and writes `outputs/round-N/<person>.md` (Slack formatting) and `outputs/round-N/scoreboard.md`.
4. Claude shows the drafts to Mark. Mark edits or approves. Claude posts.
5. Rounds 2 and 3 take the prior scoreboard as input so the banter continues ("Priya: 18% to 61%").

Proposed schedule: kickoff after the dry run next week, update around Nov 9, final plans around Nov 16. Mark can move these.

## Dry run

Before anything goes live, run the swarm on synthetic profiles in `synthetic-data/` (fictional crew, not real coworkers). One synthetic profile plants a mean-spirited joke bait and a spoiler bait to confirm The Cleaner catches them.

## Testing

- Profile parsing and Slack output formatting are plain Python with unit tests.
- Agent behavior is checked by the dry run against the real API, with no mocks.
- Dry run passes when: every synthetic person gets a plan, the scoreboard ranks them, The Cleaner flags the planted bait, and no output contains a fact outside the facts file.

## Left to the builder

- Exact system prompts and skill contents per specialist.
- Whether the Mastermind runs one session for all profiles or one per person plus a scoreboard pass.
- Current model IDs (the starter hardcodes older ones; verify before use).
- Codename style and scoreboard format.
- Profile file format.

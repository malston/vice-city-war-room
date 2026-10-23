# Demo script: Vice City War Room

About 10 minutes. Spoken lines are in quotes. Commands go in the terminal. Everything below was rehearsed once, and the outputs shown are what it printed.

## Before you start (2 minutes)

1. Open two terminal windows side by side. In both: `cd` to the repo folder (the one that holds `fake_slack.py`)
2. Check the branch: `git branch --show-current` should say `slice-6-fake-slack`. Do not switch branches.
3. Open two browser tabs: the repo README and the issues list on GitHub.
4. In terminal A, run `python fake_slack.py reset`. It prints `Channel cleared.` or `Channel already empty.`
5. Make the terminal font big.

## Opening (30 seconds)

"I'm building a small agent project with a few friends. It's a crew of AI agents that writes each of us a funny, personal plan for GTA 6 launch day, plus a readiness scoreboard. At work I help companies roll out Claude, and the pattern under this is what they use for real work: one boss agent hands tasks to several specialists at the same time, then combines the answers. This is the fun version."

Show the README crew table:

"The boss is the Mastermind. The specialists are the Fixer for time off, the Smooth Talker for spouse and family, the Wheelman for the console and downloads, and the Quartermaster for snacks. A fifth agent, the Cleaner, checks everything for mean jokes, made-up facts, and spoilers before anything is posted."

## Step 1: the kickoff post (1 minute)

Terminal A:

```text
KICKOFF_TS=$(python fake_slack.py post --file docs/kickoff-post.md --fenced | sed 's/^ts: //')
python fake_slack.py show
```

"This is a stand-in for our Slack channel, so the demo doesn't need Slack. It's the post people would see. They fill in five lines: console, time off, spouse risk, preordered, weakness."

You will see the kickoff post, posted by `War Room`.

## Step 2: friends reply (2 minutes)

Terminal A:

```text
python fake_slack.py seed --delay 2
```

Terminal B, while it runs (rerun as often as you like):

```text
python fake_slack.py show
```

"Five fictional friends are replying. Some replies are messy on purpose. Mara used Slack bold on the labels. Pia left most of it blank. Otto replies twice."

Terminal A finishes with `Seeded 6 message(s)`.

## Step 3: replies become profiles (2 minutes)

Terminal A:

```text
python fake_slack.py read --since $KICKOFF_TS --out outputs/messages.json
python parse_profiles.py --messages outputs/messages.json --kickoff-ts $KICKOFF_TS
cat profiles/otto.json
```

Expected output:

```text
Saved 6 message(s) to outputs/messages.json
Wrote 5 profile(s) to profiles: jules, mara, otto, pia, sol
```

"Code turns the chat replies into one profile file per person. The kickoff post from the bot is left out, so the crew never writes a plan for itself."

Otto's file should show `"console": "PS5"`, `"pto_status": "not yet"`, `"preordered": true`, and a `raw_reply` with both replies joined by `---`.

"Otto said no preorder first, then yes. The second reply updated the first, and the original text is kept."

If you have time, also `cat profiles/pia.json`: `console` is `null`. "Blank means unknown. The crew doesn't guess."

## Step 4: where it stands (2 minutes)

Show the GitHub issues list.

"Six slices, one per person. Intake is done and merged. This fake Slack is built and in review. The Cleaner and the output checks are merged. The playbooks and voice, and the posting queue, each have an owner. The part that runs the actual swarm is the big open one, so I can't run the crew live today."

"Here is what it will look like." Show the README section "Using it from the terminal" and say it is an illustration, not real output.

## If someone asks

- **Why isn't the crew running?** "That's slice 2, the agents and the code that runs them. It's the next thing to land. The plan has its tasks written."
- **Where do the facts come from?** "A facts file taken from our launch FAQ. Anything not in it, the crew has to call unconfirmed."
- **Can it post to Slack by itself?** "No. Nothing posts without my approval."
- **What stops it being mean?** "The Cleaner reviews every draft, and the rules say jokes go after the situation, never the person."

## After the demo

```text
python fake_slack.py reset
rm -rf profiles outputs/messages.json
```

## If something goes wrong

- **A step prints a Python error:** run `python fake_slack.py reset` and start again from Step 1.
- **`seed` is slow or stuck:** press Ctrl+C, then use `python fake_slack.py reply --as mara --text "Console: PS5"` by hand for two or three people, then continue at Step 3.
- **`$KICKOFF_TS` is empty (for example after opening a new terminal):** run `python fake_slack.py reset` and redo from Step 1. The variable only lives in the terminal where you set it.

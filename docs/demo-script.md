# Demo script: Vice City War Room

About 10 minutes. Spoken lines are in quotes. Commands go in the terminal. The outputs shown are what the commands print.

There is also a browser version (`make ui`). It runs the same steps with buttons. The live crew is still optional, and only for after a passing dry run.

## Before you start (2 minutes)

1. Open two terminal windows side by side. In both: `cd` to the repo folder (the one that holds `fake_slack.py`)
2. Get the latest: `git checkout main && git pull`. Then `git branch --show-current` should say `main`.
3. Open two browser tabs: the repo README and the issues list on GitHub.
4. In terminal A, run `python fake_slack.py reset`. It prints `Channel cleared.` or `Channel already empty.`
5. Make the terminal font big.
6. Browser version only: in terminal B run `make ui` and open `http://127.0.0.1:8765`.
7. Live crew only: once per workspace, run `make crew-setup`. Then run `python dry_run.py` before the demo. Every line must say PASS. If it doesn't, skip the live crew section.

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

## Browser version (instead of Steps 1 to 3, 3 minutes)

Click the buttons in order. They run the same commands, so the same lines of talk work.

1. **Start clean.** Then **Post the kickoff.** "This is the post people would see."
2. **Friends reply.** The Channel panel fills, one reply per second. "Five fictional friends, some messy on purpose."
3. **Replies become profiles.** The Command output panel should end with `Wrote 5 profile(s) to profiles: jules, mara, otto, pia, sol`.
4. **Reply by hand** (optional, a good moment to involve the room): handle `zed`, text `Console: PS5`. A handle with capital letters or spaces is refused with a message.

If you restart the page (`make ui-restart`), click Start clean and post the kickoff again.

## Step 4: where it stands (2 minutes)

Show the GitHub issues list.

"Six slices, one per person, and all six are merged: intake, the crew code, the playbooks and voice, the Cleaner and the output checks, the posting queue, and this fake Slack. The one thing I haven't done is run the whole crew live in front of anyone."

If the dry run passed beforehand, say so and do the live crew section below. If it didn't, say it plainly: "It's built, and the dry run is the test."

"Here is what it will look like." Show the README section "Using it from the terminal" and say it is an illustration, not real output.

## Optional: run the crew live (only after a passing dry run)

The crew must already exist (`make crew-setup`, once per workspace), and your `ANTHROPIC_API_KEY` must belong to that workspace.

```text
export ANTHROPIC_API_KEY=<your key>   # skip this if direnv or .env already sets it
python run_war_room.py --round 1 --profiles profiles
python check_outputs.py --profiles profiles --out outputs/round-1 --facts synthetic-data/launch-facts.md
python fake_slack.py post --file outputs/round-1/mara.md
python fake_slack.py post --file outputs/round-1/scoreboard.md
python fake_slack.py show
```

"Watch the event lines. The four specialists start at the same time, and the Cleaner reviews the draft before anything is final."

The browser buttons 5 to 7 do the same. Button 6 lists the drafts and nothing posts until you approve them in the Drafts panel. Say so: "Nothing goes out until I approve it."

## If someone asks

- **Is the crew running for real?** If you did the live section: "Yes, that was the real crew." If not: "It's merged and built, and it has run end to end on fictional people. The output checks flag any date that isn't in the facts file, which is what they're for. I just haven't run it for an audience yet."
- **Where do the facts come from?** "A facts file taken from our launch FAQ. Anything not in it, the crew has to call unconfirmed."
- **Can it post to Slack by itself?** "No. Nothing posts without my approval."
- **What stops it being mean?** "The Cleaner reviews every draft, and the rules say jokes go after the situation, never the person."

## After the demo

```text
python fake_slack.py reset
rm -rf profiles outputs/messages.json outputs/round-1
```

If the browser page is running, stop it with `make ui-stop`.

## If something goes wrong

- **A step prints a Python error:** run `python fake_slack.py reset` and start again from Step 1.
- **The browser page won't load, or a button turns red:** use the terminal steps. They run the same commands.
- **The live crew fails (missing key, "Agent not found", a red check):** stop, say "that's the part I'm still proving," and go back to the issues list in Step 4. "Agent not found" means your key belongs to a different workspace than the crew; the README's troubleshooting table has the fix.
- **`seed` is slow or stuck:** press Ctrl+C, then use `python fake_slack.py reply --as mara --text "Console: PS5"` by hand for two or three people, then continue at Step 3.
- **`$KICKOFF_TS` is empty (for example after opening a new terminal):** run `python fake_slack.py reset` and redo from Step 1. The variable only lives in the terminal where you set it.

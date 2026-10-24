# Demo: running a round with the fake channel

This walk-through needs no Slack connection. The replies come from fictional people, and the plans are posted into a channel kept in `outputs/demo/channel.json`. The swarm step (step 6) needs three things: a crew set up with `make crew-setup`, an `ANTHROPIC_API_KEY` for the workspace where that crew was created (the README explains), and a passing `python dry_run.py`. There is also a browser version of the same steps, described near the end.

In the real flow your Claude session reads and posts through Slack. Here the same three steps are `fake_slack.py` commands: save the replies, post the kickoff, and post the plans.

## Walk-through

1. **Start clean.**

   ```text
   python fake_slack.py reset
   ```

2. **Post the kickoff.** `--fenced` posts only the text inside the code fence of the kickoff post. The command prints `ts: <number>`. Keep that number as the kickoff timestamp.

   ```text
   KICKOFF_TS=$(python fake_slack.py post --file docs/kickoff-post.md --fenced | sed 's/^ts: //')
   ```

3. **Let the friends reply.** `seed` adds scripted replies from five fictional people, one every two seconds here. Run `python fake_slack.py show` in a second terminal to watch them arrive.

   ```text
   python fake_slack.py seed --delay 2
   ```

   To reply by hand instead:

   ```text
   python fake_slack.py reply --as mara --text "Console: PS5"
   ```

4. **Save the replies.** This writes the messages file the next step reads. It leaves out the bot's own posts, so plans posted in an earlier round never become profiles.

   ```text
   python fake_slack.py read --since $KICKOFF_TS --out outputs/messages.json
   ```

5. **Build the profiles.**

   ```text
   python parse_profiles.py --messages outputs/messages.json --kickoff-ts $KICKOFF_TS
   ```

6. **Run the swarm and check the output.** Run `python dry_run.py` once beforehand. It runs the crew on fictional people and checks the result.

   ```text
   python run_war_room.py --round 1 --profiles profiles
   python check_outputs.py --profiles profiles --out outputs/round-1 --facts synthetic-data/launch-facts.md
   ```

7. **Post the plans you approve.** Each one appears in the channel from the bot, then the scoreboard.

   ```text
   python fake_slack.py post --file outputs/round-1/mara.md
   python fake_slack.py post --file outputs/round-1/scoreboard.md
   python fake_slack.py show
   ```

## Round 2

Have people reply with changes (`reply --as otto --text "Preordered: yes"`). Run steps 4 to 7 again with the same `$KICKOFF_TS`, so everyone's earlier answers carry over, and add `--prior-scoreboard outputs/round-1/scoreboard.md` to the swarm command with `--round 2`. Then write and post the "who moved" post:

```text
python movers.py --prev outputs/round-1/scoreboard.md --curr outputs/round-2/scoreboard.md --out outputs/round-2/movers.md
python fake_slack.py post --file outputs/round-2/movers.md
```

## Browser version

```text
make ui           # start the page in the background
make ui-status    # is it running, and is a step in flight?
make ui-stop      # stop it
make ui-restart   # stop, then start again
make ui-logs      # follow its log (outputs/demo-ui.log)
```

`make ui` uses the `ANTHROPIC_API_KEY` already in your environment (for example from direnv). If there isn't one, it reads `.env`. The key has to belong to the workspace where the agents were created, or the swarm step fails with "Agent not found". `make ui-stop` refuses while a step is running, because stopping the page also ends that step. Add `FORCE=1` to stop anyway. You can still run `python demo_ui.py` in a terminal if you prefer.

Open `http://127.0.0.1:8765`. The page binds to your own machine only, and each button runs the same commands as the walk-through with fixed arguments.

| Button                     | Runs                                                                                   |
| -------------------------- | -------------------------------------------------------------------------------------- |
| 1. Start clean             | `fake_slack.py reset`                                                                  |
| 2. Post the kickoff        | `fake_slack.py post --file docs/kickoff-post.md --fenced`, and remembers the timestamp |
| 3. Friends reply           | `fake_slack.py seed --delay 1`, one reply per second                                   |
| 4. Replies become profiles | `fake_slack.py read` then `parse_profiles.py`                                          |
| 5. Run the swarm and check | `run_war_room.py --round 1` then `check_outputs.py`                                    |
| 6. Review the drafts       | `post_queue.py build` then `list`. Nothing is posted yet                               |
| 7. Post the approved       | `fake_slack.py post` for each approved draft, then `post_queue.py mark-posted`         |

The Channel panel updates as messages arrive, and the Command output panel shows what the last button printed. The Crew panel shows one lane per agent during the swarm step: how many of its drafts are working, done, or stopped, plus tokens and active seconds. It stops updating once nothing is running. "Reply by hand" posts one message as a teammate; it needs a valid handle (lowercase letters, digits, `_` or `-`) and some text.

Things to know:

- Button 5 needs `ANTHROPIC_API_KEY` in the environment where the page starts (or in `.env` for `make ui`), and the key must belong to the workspace where the agents were created. It also needs the agents from the setup order.
- Button 6 fills the Drafts panel. Approve a draft there, or choose "Approve all". Button 7 posts only approved drafts, with the text that was approved, and refuses when none are approved. If you edit a draft file, click button 6 again. The edited draft needs approving again.
- The page remembers the kickoff timestamp in memory. If you restart `demo_ui.py`, click "Start clean" and post the kickoff again.

## Commands

| Command                                                                    | What it does                                                |
| -------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `reset`                                                                    | Clears the channel                                          |
| `post (--file FILE \| --text TEXT) [--fenced] [--as HANDLE] [--name NAME]` | Posts a message, by default as the bot, and prints its `ts` |
| `reply --as HANDLE --text TEXT [--name NAME]`                              | Posts a message as a teammate                               |
| `seed [--file FILE] [--delay SECONDS]`                                     | Adds the scripted replies from `demo/seed-round-1.json`     |
| `show [--since TS]`                                                        | Prints the channel                                          |
| `read [--since TS] --out FILE [--include-bot]`                             | Writes the saved-messages file                              |

Every command takes `--channel FILE` before the command name to use a different channel file.

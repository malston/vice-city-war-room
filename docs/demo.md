# Demo: running a round with the fake channel

This walk-through needs no Slack connection. The replies come from fictional people, and the plans are posted into a channel kept in `outputs/demo/channel.json`. The swarm itself still needs `ANTHROPIC_API_KEY` and the agents from the setup order in [`contracts.md`](contracts.md).

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

6. **Run the swarm and check the output.**

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

Have people reply with changes (`reply --as otto --text "Preordered: yes"`). Run steps 4 to 7 again with the same `$KICKOFF_TS`, so everyone's earlier answers carry over, and add `--prior-scoreboard outputs/round-1/scoreboard.md` to the swarm command with `--round 2`.

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

# Runbook: running a round

One round turns people's replies into personal launch plans and a scoreboard. The owner approves every post before it is sent.

Steps 4 and 5 use commands from slices 2 and 4. They work once those slices are merged.

## Before the first round

1. Run the setup order in `contracts.md`.
2. Run `python dry_run.py`. Every check line must say PASS. The dry run uses fictional people, so nothing real is involved.

## Each round

1. **Approve and post the kickoff.** Take the text from `docs/kickoff-post.md`, edit it if you like, and post it only after you approve it. Note the Slack timestamp (`ts`) of the posted message. Round 1 only: rounds 2 and 3 keep using the round 1 kickoff timestamp, so everyone's earlier answers carry over. For those rounds, post a short update message asking people to reply with any changes.

2. **Save the replies.** In the Claude session, ask Claude to read every channel reply since the round 1 kickoff, not only the new ones, and save them to `outputs/messages.json`, replacing the file. The file is a JSON list of messages:

   ```json
   [
     {
       "author_handle": "mara",
       "author_name": "Mara",
       "ts": "1792773218.446639",
       "text": "Console: PS5\nPreordered: yes"
     }
   ]
   ```

   A handle is lowercase letters, digits, `_`, or `-`, up to 32 characters, starting with a letter or digit. `outputs/` is gitignored, so real replies stay out of the repo.

3. **Build the profiles.**

   ```text
   python parse_profiles.py --messages outputs/messages.json --kickoff-ts <ts of the round 1 kickoff post>
   ```

   This writes `profiles/<handle>.json` for each person who replied after the round 1 kickoff. A later reply updates only the fields it gives. It prints one line naming who it wrote, or says nothing was written.

4. **Run the swarm.**

   ```text
   python run_war_room.py --round N --profiles profiles
   ```

   For rounds 2 and 3, add `--prior-scoreboard outputs/round-<N-1>/scoreboard.md`.

5. **Check the output.**

   ```text
   python check_outputs.py --profiles profiles --out outputs/round-N --facts synthetic-data/launch-facts.md
   ```

   If any check fails, do not post. Fix the cause and rerun step 4.

6. **Review and approve each post.** Read `outputs/round-N/<handle>.md` for every person and `scoreboard.md`. Edit anything you do not like. Ask Claude to post only the ones you approve, as separate channel posts: one per person, then one scoreboard post. A person who looks singled out, or any fact you cannot trace to `launch-facts.md`, stays unposted.

## Rounds

The proposed schedule is a kickoff after the dry run, an update around Nov 9, and the final plans around Nov 16. Move these as you like.

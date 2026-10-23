# Posting guide

Nothing goes to Slack until you approve it. This guide covers the step after the runbook's output check (`check_outputs.py` passes).

## Rounds 2 and 3: write the movers post

Compare this round's scoreboard to the last one:

```text
python movers.py --prev outputs/round-1/scoreboard.md --curr outputs/round-2/scoreboard.md --out outputs/round-2/movers.md
```

The post names the biggest climber, the biggest drop, and new crew members. Skip this in round 1; the queue leaves out `movers` when `movers.md` does not exist.

## Build, review, approve

1. Build the queue. Order is people by handle, then the scoreboard, then movers.

   ```text
   python post_queue.py build --profiles profiles --out outputs/round-N
   ```

2. See what is waiting. Every post starts `pending`.

   ```text
   python post_queue.py list --out outputs/round-N
   ```

3. Read the drafts, then approve some or all.

   ```text
   python post_queue.py approve --out outputs/round-N person-mara scoreboard
   python post_queue.py approve --out outputs/round-N --all
   ```

## Post

The Claude session posts for you, one message at a time:

1. `python post_queue.py next --out outputs/round-N` prints the text of the next approved post. It prints nothing and exits 1 when no approved post is left. A pending post is never returned.
2. You confirm the text. Claude posts it to Slack.
3. `python post_queue.py mark-posted --out outputs/round-N <id>` records it, so it is never returned again.

Repeat until `next` prints nothing.

## Editing a draft

If you change a draft after approving it, rebuild the queue (same `build` command). A post whose text changed goes back to `pending` and must be approved again. Posts already marked `posted` stay posted.

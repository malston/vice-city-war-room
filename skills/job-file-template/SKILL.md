---
name: job-file-template
description: The Mastermind's template for each crew member's launch plan post and the team scoreboard post, in Slack formatting. Use when writing <handle>.md and scoreboard.md.
---

# Job File Template (The Mastermind)

Every output is a Slack message. Slack formatting only: `*bold*` with single asterisks, `_italic_`, plain `-` bullets. No `**`, no `#` headings, no em dashes.

## Per-person post: `<handle>.md`

```text
*The Job: <display_name>*
*Codename:* <codename>
*Readiness:* <score>/100

<one or two sentence opener from the Mastermind, in heist voice>

*The Fixer (PTO):* <Fixer's advice, two or three sentences>
*The Smooth Talker (home front):* <Smooth Talker's advice, two or three sentences>
*The Wheelman (the ride):* <Wheelman's advice, two or three sentences>
*The Quartermaster (supplies):* <Quartermaster's advice, two or three sentences>

*Your next move:* <one concrete action, or three numbered steps for anyone behind>
```

Keep each post under about 200 words. For anyone behind, the closing "next move" is the on-ramp from `heist-voice`.

## Scoreboard: `scoreboard.md`

```text
*Crew Readiness Board: Round <N>*

1. <display_name> (<codename>): <score>/100
2. <display_name> (<codename>): <score>/100

<one closing line from the Mastermind>
_React to the job plan you like best._
```

The ranked lines follow `readiness-scoring` exactly. Nothing else on those lines.

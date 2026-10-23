---
name: readiness-scoring
description: The Mastermind's rubric for each crew member's GTA 6 launch readiness score out of 100. Use when building the team scoreboard from the profiles.
---

# Readiness Scoring (The Mastermind)

Score each person out of 100 by adding the four parts below. Use the profile fields exactly; do not guess a value the person did not give.

| Part | Profile field | Points |
| --- | --- | --- |
| Pre-order | `preordered` | `true` 25, `false` 5, `null` 10 |
| Console | `console` | PS5 or Xbox Series X or S 25; anything else or `null` 0 |
| PTO | `pto_status` | approved 30, requested 20, not requested 5, `null` 0 |
| Spouse risk | `spouse_risk` | `(5 - risk) * 5`, so 1 is 20 and 5 is 0; `null` 10 |

The maximum is 100 (25 + 25 + 30 + 20). `weakness` earns no points; it only feeds the jokes.

## Worked examples

| Profile | Pre-order | Console | PTO | Spouse risk | Total |
| --- | --- | --- | --- | --- | --- |
| PS5, approved, risk 1, preordered | 25 | 25 | 30 | 20 | 100 |
| PS5, not requested, risk 4, not preordered | 5 | 25 | 5 | 5 | 40 |
| everything `null` | 10 | 0 | 0 | 10 | 20 |

## Scoreboard rules

- One line per person, sorted by score, highest first. Ranks run 1 to N.
- Ties keep alphabetical order by display name.
- Line format, exactly: `<rank>. <display_name> (<codename>): <score>/100`
- In later rounds, when a prior scoreboard is given, mention each person's change, for example "Priya: 40 to 75".

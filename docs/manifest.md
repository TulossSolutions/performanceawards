# RANKED. Project Manifesto

## The vision

Football rankings should be understandable, reproducible, and open to scrutiny.

RANKED. publishes weekly player rankings by broad position—goalkeeper, defender, midfielder, and forward—from normalized match statistics. Every published score should answer two questions: **what happened on the pitch, and why did that produce this rank?**

The project does not claim that mathematics can remove judgment from football analysis. Metric selection, weights, eligibility thresholds, and context adjustments are all choices. Our commitment is to make those choices explicit, apply them consistently, and preserve enough evidence for the result to be reproduced.

## Our principles

### Explain every result

A ranking is useful only when people can understand it. Player pages expose the component metrics, percentiles, context adjustments, minutes, formula version, and ranking movement behind the final score.

### Prefer repeatable rules to opaque opinions

Scores are deterministic and formula-versioned. The same persisted inputs and formula must produce the same result. Human votes, provider-supplied ratings, and LLM-generated scores do not determine the rankings.

### Compare players within their role

Goalkeepers, defenders, midfielders, and forwards contribute differently. RANKED. evaluates players against their own position cohort instead of forcing every role into one universal leaderboard.

### Respect context without hiding it

Performance is adjusted using explicit pre-match context, including opponent strength and competition importance. Team strength is modeled chronologically with our own Elo ratings; Elo supports context and never directly decides a player's rank.

### Preserve the evidence

Raw provider payloads are retained before normalization. Formula versions and published weekly snapshots are immutable. Corrections can improve future publications without silently rewriting what the public saw in the past.

### Keep the ranking logic independent

Business logic consumes normalized football data rather than provider-specific responses. API-Football is the primary MVP source, PostgreSQL stores operational data, and StatsBomb Open Data supports isolated research and backtesting. A future provider can be added without changing what a score means.

### Treat missing data honestly

Unavailable metrics are not poor performances and must not become artificial zeroes. Coverage limitations should remain visible, and a metric that is unavailable for a cohort should not distort its ranking.

## MVP focus

The first version deliberately concentrates on men's football across six competitions:

- English Premier League
- Spanish La Liga
- Italian Serie A
- German Bundesliga
- French Ligue 1
- UEFA Champions League

The product publishes navigable weekly rankings and player explanations for the four broad positions. It favors a trustworthy, testable methodology over a larger collection of leagues, roles, predictions, awards, or editorial features.

## The promise

For every published ranking, RANKED. should be able to show:

- the source observations used;
- the normalization and eligibility rules applied;
- the formula and weights in force;
- the context adjustments made;
- the frozen weekly result produced.

If a visitor can inspect a ranking, understand why one player placed above another, and reproduce the outcome from the retained data and formula version, the project is fulfilling its purpose.

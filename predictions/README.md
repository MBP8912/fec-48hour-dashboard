# Spiros Election 2026 — prediction pool

Public dashboard (when Pages is deployed): https://mbp8912.github.io/fec-48hour-dashboard/predictions/

*Original source:* 2026 election form responses (`picks.json`), 20 participants and 18 races. Timestamp omitted. The two blank Nebraska governor selections remain unscored.

## How scoring works

One point for every person whose predicted **candidate** exactly matches a verified **Associated Press** race winner. The dashboard displays uncalled races as pending and never counts a leading candidate, a preliminary result, or a call by another news outlet as a win. Picks for independent candidate Dan Osborn are gold, Democratic picks blue and Republican picks red. Obvious response spelling mistakes (Jim Pillon, Jenny Honeycut, Michael Watley) are normalized for scoring, while original inputs are retained in the source.

## Race-call source and reliability

The official AP Elections API requires a paid/authorized AP API key: https://developer.ap.org/ap-elections-api/index.html . This project uses the public no-key results feed of [The People's Tally](https://thepeoplestally.com/open-data/) **only when an individual winner is explicitly marked as called by the AP**. It ignores all other decision-desk and uncertified-count records. Each accepted AP-attributed call retains the source URL and timestamp when provided. The public feed is a secondary source; its coverage and availability cannot be guaranteed. If it fails, the latest verified calls remain visible and the site shows a freshness warning rather than inventing winners.

The 2026 election call checker runs on the GitHub Actions schedule every 10 minutes from 7 p.m. EST on Nov 3 through 5:50 a.m. EST on Nov 4, then hourly from 6 a.m. EST. GitHub scheduled jobs can be delayed, so these are target intervals, not guaranteed on-the-minute updates. It stops deploying new snapshots when all 18 races are called. Page loads re-check the generated `calls.json` every 60 seconds, but will not request the election-data provider directly.

**Source verification:** [AP's race call policy](https://www.ap.org/elections/our-role-in-the-u-s-elections/how-we-declare-winners/), [public secondary feed schema](https://thepeoplestally.com/open-data/), [candidate affiliations (SC-1)](https://ballotpedia.org/South_Carolina%27s_1st_Congressional_District_election%2C_2026), [candidate affiliations (OH-7)](https://ballotpedia.org/Ohio%27s_7th_Congressional_District_election%2C_2026).

## Local preview and checks

Open `index.html` locally to see the initial ungraded grid (the `calls.json` auto-refresh requires an HTTP server). Test parsing with `python -m unittest discover -s predictions -p 'test_refresh_calls.py' -v` from the repo root.

### Files

- `index.html` — self-contained dashboard with embedded original predictions and browser rendering logic.
- `picks.json` — machine-readable source predictions, normalized candidates and party affiliations.
- `calls.json` — AP-verified winner snapshot and check metadata.
- `refresh_calls.py` — conservative public feed checker and AP attribution filter.
- `test_refresh_calls.py` — offline race call parser regression tests.
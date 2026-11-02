# Election Night 2026 — Free Public Results Dashboard

Public URL (after GitHub Pages deployment):
https://mbp8912.github.io/fec-48hour-dashboard/election-night/

## Scope

Nine U.S. House races (NY-17, NY-19, CO-4, CO-5, IA-1, MN-1, NE-2, WI-1, CA-13) and two governor elections (IA, CO). Overview shows reported candidate vote counts, share of reported votes, reporting percentages **with units**, poll closing time ET, freshness, and status. Each race has a dedicated query-linked view (`?race=MN-01`) with county map, sortable county table and links to election-office sources. Pages refresh browser data every 60 seconds.

### Data coverage and caveats

- `openamerica.io/elections/results.json` provides keyless CORS-enabled official **state aggregate** totals and precincts-reporting progress for CO, IA and MN. 2026 sources begin after polls close. It does **not** contain county breakdowns. It does not cover NY, NE, WI or CA. Attribution: official state election offices via [Open America](https://openamerica.io/elections/api/).
- [The People's Tally](https://thepeoplestally.com/open-data/) is an optional, best-effort second free nationwide **aggregate** provider (CC BY 4.0, attribution in site footer). The dashboard uses its actual numbers only if a fresh dated 2026 candidate total appears and fetch is CORS-permitted. Its `exp` field is labeled **estimated votes counted** when present, not precincts. Neither coverage nor browser CORS can be guaranteed in advance.
- Minnesota's Secretary of State [official county export](https://electionresults.sos.mn.gov/Results/MediaFileLayout/Index?ersElectionId=201) supplies genuine district-specific county vote totals and precincts reporting for MN-1, normalized by `refresh_mn.py` every five minutes on election night. `USHouseCty.txt` is keyed by congressional district, so counties split across districts are not erroneously counted in full. Before polls close, the official file contains *test data*, and data that has not changed since polls closed remains hidden.
- For other races, **verified live county-level election results are not available through these free feeds**. Their geographic outlines render but county vote totals and percentages remain blank. Never substitute statewide votes or 2024 results for 2026 district-specific county totals, invent reporting estimates or show an unsupported source as zero votes.
- The map uses public `us-atlas` TopoJSON county boundaries for geographic context; full counties are outlined even where a congressional district includes only part. Maps are **not** geographic depictions of congressional district boundaries.
- Poll closing ET: 9:00 p.m. Nov 3 for all tracked races except CA-13 at 11:00 p.m. Unofficial vote counts may begin later. Neither feed projects or independently calls races.

### Operations

`election-night-update.yml` runs on a five-minute GitHub schedule and updates the MN county snapshot (or retains the last verified one on failure) before assembling and publishing all existing FEC Pages plus the election-night subfolder. Existing hourly deployment workflow also copies `election-night/` so it cannot erase the new page. It is safe to deploy the page before Election Day. After election night, the five-minute workflow is designed to cease its active schedule automatically (only November 3-5, 2026 UTC), avoiding perpetual deploys. Both workflows use the same GitHub Pages concurrency group.

Test parser: `cd election-night && python -m unittest test_refresh_mn.py -v`.

**No API keys and no paid services.** A no-cost public hosting / static frontend architecture, subject to public-provider availability. Results do not imply certification.

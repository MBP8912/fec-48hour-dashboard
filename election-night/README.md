# Election Night 2026 — Free Public Results Dashboard

Public URL (after GitHub Pages deployment):
https://mbp8912.github.io/fec-48hour-dashboard/election-night/

## Scope

Nine U.S. House races (NY-17, NY-19, CO-4, CO-5, IA-1, MN-1, NE-2, WI-1, CA-13) and two governor elections (IA, CO). Overview shows reported candidate vote counts, share of reported votes, reporting percentages **with units**, poll closing time ET, freshness, and status. Each race has a dedicated query-linked view (`?race=MN-01`) with county map, sortable county table and links to election-office sources. Pages refresh browser data every 60 seconds.

### Data coverage and caveats

- `openamerica.io/elections/results.json` provides keyless CORS-enabled official **state aggregate** totals and precincts-reporting progress for CO, IA and MN. 2026 sources begin after polls close. It does **not** contain county breakdowns. It does not cover NY, NE, WI or CA. Attribution: official state election offices via [Open America](https://openamerica.io/elections/api/).
- [The People's Tally](https://thepeoplestally.com/open-data/) is an optional, best-effort second free nationwide **aggregate** provider (CC BY 4.0, attribution in site footer). The dashboard uses its actual numbers only if a fresh dated 2026 candidate total appears and fetch is CORS-permitted. Its `exp` field is labeled **estimated votes counted** when present, not precincts. Neither coverage nor browser CORS can be guaranteed in advance.
- Minnesota's Secretary of State [official county export](https://electionresults.sos.mn.gov/Results/MediaFileLayout/Index?ersElectionId=201) supplies genuine district-specific county vote totals and precincts reporting for MN-1, normalized by `refresh_mn.py` every five minutes on election night. `USHouseCty.txt` is keyed by congressional district, so counties split across districts are not erroneously counted in full. Before polls close, the official file contains *test data*, and data that has not changed since polls closed remains hidden.
- California Secretary of State publishes 2026 general-election **election media files** (`V26GG.txt`, `C26GG.txt` and `S26GG.txt`) at [media.sos.ca.gov](https://media.sos.ca.gov/). `refresh_ca.py` validates the CA-13 county and candidate codes, counts by district and county, and district-specific precinct totals. No pre-election test data is displayed.
- New York State Board of Elections offers a public HTML election-night results feed (`HomeNoJS.aspx`) with district-wide total votes and **election districts reporting** for NY-17 and NY-19. `refresh_ny.py` reads the official "Votes by Candidate" column, merging fusion-party ballot lines into each candidate total. It does not yet supply NY county-level results. **Operational caveat:** As of November 2, NYENR returns HTTP 403 to the GitHub-hosted refresh worker. If access remains blocked, the NY races will be marked as unavailable until an alternate source is verified.
- Nebraska's Secretary of State publishes NE-2 district-specific candidate results separately for Douglas, Sarpy and Saunders counties. `refresh_ne.py` collects those three official county pages when accessible; it deliberately leaves county progress **blank**, because the on-screen precinct figures repeat district-wide totals, rather than providing independently verifiable county percentages.
- For the remaining races, **verified live county-level election results are not available through these free feeds**. Their geographic outlines render but county vote totals and percentages remain blank. Never substitute statewide votes or 2024 results for 2026 district-specific county totals, invent reporting estimates or show an unsupported source as zero votes.
- The map uses public `us-atlas` TopoJSON county boundaries for geographic context; full counties are outlined even where a congressional district includes only part. Maps are **not** geographic depictions of congressional district boundaries.
- Poll closing ET: 9:00 p.m. Nov 3 for all tracked races except CA-13 at 11:00 p.m. Unofficial vote counts may begin later. Neither feed projects or independently calls races.

### Operations

`election-night-update.yml` runs on a five-minute GitHub schedule and attempts official MN-1, NE-2, CA-13 county snapshots and NY-17/NY-19 district totals (or retains the last verified one on failure) before assembling and publishing all existing FEC Pages plus the election-night subfolder. Existing hourly deployment workflow also copies `election-night/` so it cannot erase the new page. It is safe to deploy the page before Election Day. After election night, the five-minute workflow is designed to cease its active schedule automatically (only November 3-5, 2026 UTC), avoiding perpetual deploys. Both workflows use the same GitHub Pages concurrency group.

Test parsers: `cd election-night && python -m unittest test_refresh_mn.py test_refresh_ne.py test_refresh_ny.py test_refresh_ca.py -v`.

**No API keys and no paid services.** A no-cost public hosting / static frontend architecture, subject to public-provider availability. Results do not imply certification.

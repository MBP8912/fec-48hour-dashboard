# NY-17: 48-hour fundraising notices (October 2026)

A public, nonpartisan GitHub Pages dashboard tracking **Lawler for Congress, Inc. (C00815415)** and **Cait for New York (C00900431)**. It charts qualifying contributions reported on Form 6 by the **dates received**, with cumulative sums and direct links to the original F65 contribution pages.

**These are not overall campaign fundraising totals.** Federal Form 6 covers qualifying transactions of $1,000 or more within the final pre-election reporting window and can include in-kind contributions and loans. They will also be itemized in later regular filings; do not add these figures to Form 3 totals.

## One-time publication steps

1. Publish these files to an existing public GitHub repository, including `.github/workflows/update-and-deploy.yml`.
2. In that repository open **Settings → Pages → Build and deployment → Source → GitHub Actions**. This is an account-owner setup action.
3. If your repository settings disallow workflow writes, open **Settings → Actions → General → Workflow permissions → Read and write permissions**, so the workflow can preserve an archive of the validated FEC data.
4. Optional but recommended: obtain a free [FEC OpenFEC API key](https://api.open.fec.gov/developers/) and add a GitHub Actions repository secret named `FEC_API_KEY`. Otherwise the workflow uses the FEC's shared, rate-limited `DEMO_KEY`.
5. Open **Actions → Refresh FEC filings and publish dashboard → Run workflow**. Check that the build, data update and Pages deployment succeed. GitHub may delay scheduled runs, so the hour-based cadence is approximate.

After a successful Pages deployment, this repository is published at `https://mbp8912.github.io/ny17-fec-48hour-dashboard/`. Do not share that URL as live until the workflow succeeds.

## Data methodology

- Discovery: FEC raw electronic filing index `GET /v1/efile/filings/`, filtered for each committee and `form_type=F6`.
- Extract: download the original `.fec` at `https://docquery.fec.gov/dcdev/posted/{file_number}.fec`, read **F65** entries, record the transaction amount and **receipt date**, and link each entry to `https://docquery.fec.gov/cgi-bin/forms/{committee_id}/{file_number}/f65`.
- Window: October **15–31, 2026** receipt dates. Files received as late as November 10 may qualify if they contain receipt dates in that window.
- Deduplication: same committee, transaction ID and named contributor counted once (newest active notice wins). Where available, FEC `amendment_chain`, `amended_by`, and `most_recent_filing` metadata supersede amended notices. F6A original filing dates provide a fallback.
- Archive: successful runs save parsed F65 entries to `data/cache.json`, preventing loss when the FEC's raw index rotates older entries out. Only after all requests succeed do we write updated data. Failed checks retain the last verified totals, rather than showing partial results.
- Privacy: no street addresses are stored or shown. Names and state abbreviations are taken from public FEC disclosure.
- Before the first verified API refresh, the public dashboard says **uninitialized** and never invents a number.

## Local tests

Run `python -m unittest discover -s tests -v` (uses synthetic records, no internet). Run `python scripts/update_data.py` to fetch actual FEC data (requires internet access). Serve the project directory with `python -m http.server 8000` and open `http://localhost:8000`.

Official resources: [Lawler committee](https://www.fec.gov/data/committee/C00815415/?tab=filings) · [Cait committee](https://www.fec.gov/data/committee/C00900431/?tab=filings) · [FEC Form 6 guidance](https://www.fec.gov/help-candidates-and-committees/filing-reports/reporting-48-hour-notices/).

Independent presentation; unaffiliated with either campaign or the FEC. FEC contributor information may not be used for commercial purposes or contribution solicitation.

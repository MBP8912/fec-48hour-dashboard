# Eight separate 2026 FEC 48-Hour Report Dashboards

The original NY-17 page remains at the root. These eight races are published as independent pages with separate FEC source and data files.

**Public dashboard address:** https://mbp8912.github.io/fec-48hour-dashboard/

All nine pages now live under `fec-48hour-dashboard` rather than the former `ny17-fec-48hour-dashboard` project URL. The renamed URL paths are listed below.

| District | Republican | Republican FEC ID | Democrat / DFL | Democratic FEC ID | Standalone page |
| --- | --- | --- | --- | --- | --- |
| CO-4 | Lauren Boebert | C00728238 | Eileen Laubacher | C00904284 | [co-4/](https://mbp8912.github.io/fec-48hour-dashboard/co-4/) |
| CO-5 | Jeff Crank | C00865592 | Jessica Killin | C00911941 | [co-5/](https://mbp8912.github.io/fec-48hour-dashboard/co-5/) |
| IA-1 | Mariannette Miller-Meeks | C00558825 | Christina Bohannan | C00787820 | [ia-1/](https://mbp8912.github.io/fec-48hour-dashboard/ia-1/) |
| MN-1 | Brad Finstad | C00807743 | Jake Johnson | C00902684 | [mn-1/](https://mbp8912.github.io/fec-48hour-dashboard/mn-1/) |
| NE-2 | Brinker Harding | C00909515 | Denise Powell | C00903948 | [ne-2/](https://mbp8912.github.io/fec-48hour-dashboard/ne-2/) |
| WI-1 | Bryan Steil | C00677286 | Mitchell Berman | C00915637 | [wi-1/](https://mbp8912.github.io/fec-48hour-dashboard/wi-1/) |
| NY-19 | Peter Oberacker | C00921668 | Josh Riley | C00793760 | [ny-19/](https://mbp8912.github.io/fec-48hour-dashboard/ny-19/) |
| CA-13 | Kevin Lincoln | C00845826 | Adam Gray | C00801431 | [ca-13/](https://mbp8912.github.io/fec-48hour-dashboard/ca-13/) |

All dashboard receipts reflect the FEC's **October 15-31, 2026** Form 6 48-hour-notice window, by *contribution date*. These totals are not all fundraising and may include loans or noncash contributions. Employer and occupation are shown in the click-through popup for individual donors where reported; mailing addresses are not displayed.

**Automatic refresh:** The scheduled GitHub Actions workflow runs NY-17 plus all eight separate race processors roughly hourly, archiving each race in its own `<district>/data/cache.json` and `<district>/data/data.json`. If a source request fails, its prior verified dataset remains unchanged. All race pages share the original validated FEC Form 6 F65 parser and a common chart/UI script at `race-assets/app.js`; the NY-17 site files remain untouched.

The optional repo secret `FEC_API_KEY` is recommended for reliability (FEC `DEMO_KEY` is rate-limited). Register at https://api.open.fec.gov/developers/

Sources: https://www.fec.gov/help-candidates-and-committees/dates-and-deadlines/2026-reporting-dates/preg-report-notice-congressional-committees-2026/ and the committee profiles linked on each dashboard. FEC donor data may not be used for solicitation.

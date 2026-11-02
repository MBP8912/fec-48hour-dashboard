#!/usr/bin/env python3
"""Refresh district-specific Minnesota 2026 congressional county results.

Official Minnesota election-night flat files:
https://electionresults.sos.mn.gov/Results/MediaFileLayout/Index?erselectionId=201

The feed includes TEST RESULTS before election night. This script refuses to mark a
snapshot as actual results until the *source rows for MN-1* change after the 9 PM
Eastern polling deadline on 2026-11-03. It preserves the last trusted snapshot on
source failure. Python stdlib only; designed for GitHub Actions every five minutes.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DEST = ROOT / 'data' / 'official-mn.json'
BASE = 'https://electionresultsfiles.sos.mn.gov/20261103/'
SOURCE = 'https://electionresults.sos.mn.gov/Select/MediaFiles/Index?ersElectionId=201'
CLOSE_UTC = datetime(2026, 11, 4, 2, 0, tzinfo=timezone.utc)


def fetch_text(name: str) -> str:
    request = Request(BASE + name, headers={
        'User-Agent': '2026-election-night-public-dashboard/1.0 (public data attribution)',
        'Accept': 'text/plain',
    })
    with urlopen(request, timeout=25) as response:
        text = response.read(2_500_000).decode('utf-8-sig', errors='replace')
    if not text or len(text) < 30:
        raise ValueError(f'{name} returned an empty or implausibly short file')
    return text


def num(value: str) -> int:
    result = int(value)
    if result < 0:
        raise ValueError('Negative election result')
    return result


def parse_counties(table_text: str) -> dict[str,str]:
    table = {}
    for line in table_text.splitlines():
        fields = line.strip().split(';')
        if len(fields) >= 2 and fields[0].strip().isdigit() and fields[1].strip():
            table[fields[0].strip().zfill(2)] = fields[1].strip()
    if len(table) < 70:
        raise ValueError(f'County lookup only includes {len(table)} rows; expected MN county roster')
    return table


def parse_mn1(house_text: str,county_names: dict[str,str]) -> list[dict]:
    counties: dict[str,dict] = {}
    for idx, line in enumerate(house_text.splitlines(), 1):
        fields = line.strip().split(';')
        if len(fields) < 16 or fields[0].upper() != 'MN':
            continue
        if fields[5].strip() != '1' or not fields[4].startswith('U.S. Representative'):
            continue
        county_id = fields[1].strip().zfill(2)
        if county_id not in county_names:
            raise ValueError(f'Unknown county ID on line {idx}: {county_id}')
        name, party, votes = fields[7].strip(), fields[10].strip(), num(fields[13])
        if not name:
            raise ValueError(f'Blank candidate name on line {idx}')
        precincts_reporting,precincts_total = num(fields[11]),num(fields[12])
        if precincts_reporting > precincts_total:
            raise ValueError(f'Invalid reporting count on line {idx}')
        county = counties.setdefault(county_id,{
            'county_id':county_id,'name':county_names[county_id],
            'precincts_reporting':precincts_reporting,
            'precincts_total':precincts_total,
            'candidates':[],
        })
        if (county['precincts_reporting'],county['precincts_total']) != (precincts_reporting,precincts_total):
            raise ValueError(f'Conflicting precinct totals for county {county_id}')
        cands=county['candidates']
        if any(x['name']==name and x['party']==party for x in cands):
            raise ValueError(f'Duplicate candidate rows for county {county_id}: {name}')
        cands.append({'name':name,'party':'D' if party.upper() in ('DFL','D') else 'R' if party.upper()=='R' else 'O','votes':votes})
    if len(counties) < 10:
        raise ValueError(f'Only {len(counties)} MN-1 counties; refusing incomplete official file')
    return sorted(counties.values(), key=lambda c:c['name'])


def build_snapshot(now: datetime,county_records: list[dict],previous: dict|None) -> dict:
    clean = json.dumps(county_records,sort_keys=True,separators=(',',':'))
    digest = hashlib.sha256(clean.encode('utf-8')).hexdigest()
    same = previous and previous.get('source_hash')==digest
    last_change=previous.get('updated_at') if same else now.isoformat().replace('+00:00','Z')
    update_dt = datetime.fromisoformat(last_change.replace('Z','+00:00')) if last_change else None
    test_data = now<CLOSE_UTC or not update_dt or update_dt<CLOSE_UTC
    return {
        'race':'MN-01','source':'Minnesota Secretary of State',
        'source_url':SOURCE,
        'updated_at':last_change,
        'source_hash':digest,
        'test_data':test_data,
        'county_count':len(county_records),
        'metric':'precincts reporting',
        'counties':county_records,
    }


def main() -> None:
    now = datetime.now(timezone.utc)
    prev = None
    if DEST.exists():
        try:
            prev = json.loads(DEST.read_text(encoding='utf-8'))
        except (ValueError,OSError):
            pass
    county_records = parse_mn1(fetch_text('USHouseCty.txt'),parse_counties(fetch_text('Cntytbl.txt')))
    output=build_snapshot(now,county_records,prev)
    raw=json.dumps(output,indent=2,ensure_ascii=False)+'\n'
    if prev==output:
        print(f'MN-1: {len(county_records)} counties, unchanged; test={output["test_data"]}')
        return
    DEST.parent.mkdir(parents=True,exist_ok=True)
    temp=DEST.with_suffix('.json.tmp')
    temp.write_text(raw,encoding='utf-8')
    os.replace(temp,DEST)
    print(f'MN-1: updated {len(county_records)} county summaries, source changed at {output["updated_at"]}, test={output["test_data"]}')

if __name__=='__main__':
    main()

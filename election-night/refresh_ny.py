#!/usr/bin/env python3
"""Fetch official NY 2026 NY-17/NY-19 Congressional totals, with ED progress.

The Board of Elections' no-JavaScript election-night page is a full public
HTML rendering of the two contests. New York fusion-party ballot lines are
aggregated by candidate on that site; select the last integer cell from the
candidate's main row (Votes by Candidate), NOT Votes by Party.
"""
from __future__ import annotations
import json
import os
import re
import hashlib
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'data'/'official-ny.json'
SOURCE='https://nyenr.elections.ny.gov/HomeNoJS.aspx'
CLOSE_UTC=datetime(2026,11,4,2,0,tzinfo=timezone.utc)
CONTESTS={
    'NY-17':{'ordinal':'17th','names':[('Cait Conley','D'),('Mike Lawler','R')]},
    'NY-19':{'ordinal':'19th','names':[('Josh Riley','D'),('Peter K. Oberacker','R')]},
}

class Extract(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[];self.rows=[];self.row=None;self.cell=None;self.ignore=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','svg'):self.ignore+=1
        if self.ignore:return
        if tag=='tr':self.row=[]
        if tag in ('td','th') and self.row is not None:self.cell=[]
    def handle_endtag(self,tag):
        if tag in ('script','style','svg'):
            self.ignore=max(0,self.ignore-1);return
        if self.ignore:return
        if tag in ('td','th') and self.cell is not None and self.row is not None:
            self.row.append(' '.join(self.cell).strip());self.cell=None
        if tag=='tr' and self.row is not None:
            if self.row:self.rows.append(self.row)
            self.row=None
    def handle_data(self,value):
        if self.ignore or not value.strip():return
        s=' '.join(value.split());self.parts.append(s)
        if self.cell is not None:self.cell.append(s)


def _parse_time(text:str):
    # Display last-updated timestamp is in New York local time.
    # E.g. "10/29/2026 11:38:17 AM". Never use a synthetic fetch time as
    # a source-update time for results that may not have been updated.
    m=re.search(r'\b(\d{1,2}/\d{1,2}/2026\s+\d{1,2}:\d{2}:\d{2}\s*[AP]M)\b',text,re.I)
    if not m:raise ValueError('NY: could not determine official update timestamp')
    try:local=datetime.strptime(' '.join(m.group(1).split()),'%m/%d/%Y %I:%M:%S %p')
    except ValueError as ex:raise ValueError('NY: invalid official timestamp') from ex
    return local.replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)


def _candidate_value(rows:list[list[str]],name:str)->int:
    # NY rows contain candidate name, party, graphs, % by party, votes by party,
    # % by candidate, votes by candidate. Fusion-party lines have no name.
    matches=[]
    for row in rows:
        if row and re.sub(r'\s+',' ',row[0]).strip().casefold()==name.casefold():
            nums=[int(v.replace(',','')) for v in row[1:] if re.fullmatch(r'[\d,]+',v)]
            if nums:matches.append(nums[-1])
    if len(matches)!=1:raise ValueError(f'NY: expected one row for {name}, got {len(matches)}')
    return matches[0]


def parse_page(html:str)->dict:
    e=Extract();e.feed(html)
    txt=' '.join(e.parts)
    if not re.search(r'New York State.*Election Night Results',txt,re.I):raise ValueError('NY: unexpected election source')
    if not re.search(r'General Election',txt,re.I):raise ValueError('NY: unexpected election type')
    timestamp=_parse_time(txt)
    # Each 17th/19th district appears once as a heading and has its own
    # election-district reporting total; do not conflate them with state totals.
    results={}
    for race,cfg in CONTESTS.items():
        needle=re.compile(r'\b'+cfg['ordinal']+r'\s+Congressional\s+District\s*>\s*All\s+Counties\b.*?Election\s+Districts\s+Reporting\s*:\s*([\d,]+)\s+of\s+([\d,]+)',re.I)
        m=needle.search(txt)
        if not m:raise ValueError(f'NY: {race} official district precinct totals not found')
        reported,total=(int(g.replace(',','')) for g in m.groups())
        if total<=0 or reported>total:raise ValueError(f'NY: {race} malformed reporting count')
        # Candidate names on these two contests are unique on the 2026 page.
        cands=[{'name':name,'party':party,'votes':_candidate_value(e.rows,name)} for name,party in cfg['names']]
        results[race]={'candidates':cands,'precincts_reporting':reported,'precincts_total':total}
    return {'source_updated_at':timestamp.isoformat().replace('+00:00','Z'),'races':results}


def build_snapshot(source:dict,prior:dict|None,now:datetime)->dict:
    # Keep source last-updated timestamp separate from the fetch timestamp;
    # pre-election and unchanged zero-vote records can never masquerade as live.
    updated=datetime.fromisoformat(source['source_updated_at'].replace('Z','+00:00'))
    test_data=now<CLOSE_UTC or updated<CLOSE_UTC
    digest=hashlib.sha256(json.dumps(source['races'],sort_keys=True).encode()).hexdigest()
    return {'source':'New York State Board of Elections','source_url':SOURCE,
            'source_updated_at':source['source_updated_at'],
            'checked_at':now.isoformat().replace('+00:00','Z'),
            'source_hash':digest,'test_data':test_data,'metric':'election districts',
            'races':source['races']}


def main():
    req=Request(SOURCE,headers={'User-Agent':'Mozilla/5.0 (compatible; ElectionNightResults/1.0)','Accept':'text/html'})
    with urlopen(req,timeout=40) as r:html=r.read(4_000_000).decode('utf-8','replace')
    if len(html)<1000:raise ValueError('NY: response unexpectedly short')
    page=parse_page(html)
    prior=None
    if DEST.exists():
        try:prior=json.loads(DEST.read_text())
        except (OSError,ValueError):pass
    output=build_snapshot(page,prior,datetime.now(timezone.utc))
    if prior:
        # New York may serve an older stale source or send a temporary rollback.
        if prior.get('source_updated_at') and output['source_updated_at']<prior['source_updated_at']:
            raise ValueError('NY: source timestamp rolled back')
        if (prior.get('source_hash')==output['source_hash'] and
            prior.get('source_updated_at')==output['source_updated_at']):
            print('NY-17/NY-19: official result page unchanged');return
    DEST.parent.mkdir(parents=True,exist_ok=True)
    temp=DEST.with_suffix('.tmp');temp.write_text(json.dumps(output,indent=2)+'\n')
    os.replace(temp,DEST)
    print('NY-17/NY-19: official vote totals and election district progress updated; test=',output['test_data'])

if __name__=='__main__':main()

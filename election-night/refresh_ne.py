#!/usr/bin/env python3
"""Read Nebraska's public 2026 county congressional result pages for NE-2.

Only three counties contain NE-2 voters: Douglas, Sarpy and Saunders. Their
contest-specific candidate totals are different from full-county vote totals.
The NE statewide display repeats district-wide precinct totals on each county
page, so this adapter *never* claims to know percent of each county reporting.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen,Request

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'data'/'official-ne.json'
BASE='https://electionresults.nebraska.gov/ResultsSW.aspx?cty={id}&map=CTY&type=CTYALL'
CLOSE_UTC=datetime(2026,11,4,2,0,tzinfo=timezone.utc)
COUNTIES={'Douglas':'01','Sarpy':'59','Saunders':'06'}
CANDIDATES=[('Brinker Harding','R','Republican'),('Denise Powell','D','Democratic'),('Eric Michael Foreman','O','Libertarian')]
CONTEST='For Representative in Congress - 2 Year Term - District 02'

class BodyText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.ignore=0
    def handle_starttag(self,tag,attrs):
        if tag in ('style','script','svg'):self.ignore+=1
    def handle_endtag(self,tag):
        if tag in ('style','script','svg'):self.ignore=max(0,self.ignore-1)
    def handle_data(self,data):
        if not self.ignore and data.strip():self.parts.append(data.strip())

def plain(html:str)->str:
    p=BodyText();p.feed(html)
    return '\n'.join(p.parts)

def fetch_page(county:str,id:str)->str:
    req=Request(BASE.format(id=id),headers={'User-Agent':'2026-election-night-public-dashboard/1.0','Accept':'text/html'})
    with urlopen(req,timeout=30) as response:
        content=response.read(3_000_000).decode('utf-8',errors='replace')
    if len(content)<500:raise ValueError(f'{county} source returned unexpectedly short HTML')
    return content

def parse_county(html:str,county:str)->dict:
    text=plain(html)
    if 'November 3, 2026' not in text:
        raise ValueError(f'{county}: unexpected election date')
    if not re.search(re.escape(county)+r' County Results',text,re.IGNORECASE):
        raise ValueError(f'{county}: unexpected county results heading')
    # Most ASP.NET pages split headings, names and vote totals across nested tags.
    # Flatten their whitespace before searching instead of demanding exact HTML text nodes.
    normalized=re.sub(r'\s+',' ',text)
    contest=re.search(r'For\s+Representative\s+in\s+Congress\s*-?\s*2\s+Year\s+Term\s*-?\s*District\s*0?2\b',normalized,re.I)
    if contest:
        rest=normalized[contest.end():]
        end=re.search(r'\bFor\s+(?:Governor|Representative|United States|Secretary|State |Attorney|Member)\b',rest,re.I)
        section=rest[:end.start()] if end else rest[:6500]
    else:
        # Some official variants omit the contest title on the county view, but
        # still show all three known, named candidates and their vote totals.
        county_heading=re.search(re.escape(county)+r'\s+County\s+Results',normalized,re.I)
        section=normalized[county_heading.end():] if county_heading else normalized
    votes=[]
    for name,party,label in CANDIDATES:
        name_pattern=r'\b'+r'\s+'.join(re.escape(part) for part in name.split())+r'\b'
        m=re.search(name_pattern,section,re.I)
        if not m:raise ValueError(f'{county}: candidate {name} missing from contest')
        following=section[m.end():m.end()+280]
        match=re.search(r'(?i)\b'+label+r'\b\s*([0-9][\d,]*)\b',following)
        if not match:raise ValueError(f'{county}: no verified count for {name}')
        votes.append({'name':name,'party':party,'votes':int(match.group(1).replace(',',''))})
    return {'name':county,'candidates':votes,'precincts_reporting':None,'precincts_total':None}

def build_snapshot(now:datetime,counts:list[dict],previous:dict|None)->dict:
    serialized=json.dumps(counts,sort_keys=True,separators=(',',':'))
    digest=hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    unchanged=previous and previous.get('source_hash')==digest
    updated_at=previous.get('updated_at') if unchanged else now.isoformat().replace('+00:00','Z')
    updated=datetime.fromisoformat(updated_at.replace('Z','+00:00')) if updated_at else None
    return {'race':'NE-02','source':'Nebraska Secretary of State',
       'source_url':'https://electionresults.nebraska.gov/',
       'updated_at':updated_at,'source_hash':digest,
       'test_data':now<CLOSE_UTC or not updated or updated<CLOSE_UTC,
       'metric':None,'counties':counts}

def main():
    prior=None
    if DEST.exists():
        try:prior=json.loads(DEST.read_text(encoding='utf-8'))
        except (ValueError,OSError):pass
    counts=[parse_county(fetch_page(name,code),name) for name,code in COUNTIES.items()]
    output=build_snapshot(datetime.now(timezone.utc),counts,prior)
    if prior==output:
        print('NE-2: county vote figures unchanged');return
    DEST.parent.mkdir(exist_ok=True,parents=True)
    temp=DEST.with_suffix('.tmp')
    temp.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,DEST)
    print('NE-2: refreshed 3 county results (reporting % unavailable); test=',output['test_data'])

if __name__=='__main__':main()

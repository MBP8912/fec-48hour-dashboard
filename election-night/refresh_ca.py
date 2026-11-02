#!/usr/bin/env python3
"""Official California 2026 general election public media files for CA-13.

California's Election Media Files include candidate, county and contest records.
We read the 2026 CA-13 *district* rows by county only; statewide totals are
kept out of the county sum to avoid double counting.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'data'/'official-ca.json'
ROOT_URL='https://media.sos.ca.gov/media/'
CLOSE_UTC=datetime(2026,11,4,4,0,tzinfo=timezone.utc)
CONTEST='110000130000'
EXPECTED_COUNTIES={'10':'Fresno','20':'Madera','24':'Merced','39':'San Joaquin','50':'Stanislaus'}
KNOWN_CANDIDATES={'Adam Gray':'D','Kevin Lincoln':'R'}

def fetch(name:str)->str:
    req=Request(ROOT_URL+name,headers={'User-Agent':'Mozilla/5.0 (ElectionNightResults/1.0; public election media file reader)','Accept':'text/plain,*/*'})
    with urlopen(req,timeout=35) as res:data=res.read(1_500_000)
    if len(data)<100:raise ValueError(name+' unexpectedly short')
    # SoS publishes some files with non-UTF8 characters in candidate names.
    try:return data.decode('utf-8')
    except UnicodeDecodeError:return data.decode('cp1252',errors='replace')

def parse_records(raw:str,type_:str)->list[list[str]]:
    result=[]
    for line in raw.splitlines():
        line=line.strip().strip('\ufeff').strip('[]')
        if not line:continue
        parts=line.split('|')
        if parts[0]==type_ and len(parts)>=4:result.append(parts)
    if not result:raise ValueError('CA missing '+type_+' data')
    return result

def source_update(raw:str)->datetime:
    m=re.search(r'(?m)^\[?B\|CAS\|\d+\|(2026\d{4})\|(\d{6})\d*\]?\s*$',raw)
    if not m:raise ValueError('CA vote file missing source timestamp')
    local=datetime.strptime(m.group(1)+m.group(2),'%Y%m%d%H%M%S')
    return local.replace(tzinfo=ZoneInfo('America/Los_Angeles')).astimezone(timezone.utc)

def candidate_map(raw:str,ids:set[str])->dict[str,tuple[str,str]]:
    records=parse_records(raw,'C')
    result={}
    for cid in ids:
        # A candidate's ID is present as its own pipe-delimited token on the
        # ballot code record. Verify name/party against the actual official file.
        matches=[p for p in records if cid in p]
        if len(matches)!=1:
            sample=[ '|'.join(p[:12]) for p in records if any('Gray' in k or 'Lincoln' in k for k in p)][:8]
            raise ValueError(f'CA candidate code {cid} not unique in official file; matching name rows: {sample}')
        name_line=' '.join(matches[0])
        normalized=' '.join(name_line.lower().split())
        found=[(name,party) for name,party in KNOWN_CANDIDATES.items()
               if all(piece in normalized for piece in name.lower().split())]
        if len(found)!=1:raise ValueError('CA candidate ID '+cid+' not matching a verified CA-13 candidate: '+name_line[:240])
        result[cid]=found[0]
    if set(x[0] for x in result.values())!=set(KNOWN_CANDIDATES):
        raise ValueError('CA mismatched expected candidate names')
    return result

def parse_files(vote_file:str,candidate_file:str,county_file:str)->dict:
    rows=parse_records(vote_file,'V')
    county_names={p[3]:p[4].strip() for p in parse_records(county_file,'S') if len(p)>=5}
    matching=[p for p in rows if p[3]==CONTEST]
    if len(matching)<6:raise ValueError('CA-13 district vote rows missing')
    statewide=[p for p in matching if p[4]=='59']
    if len(statewide)!=1:raise ValueError('CA-13 missing exactly one statewide aggregate')
    actual=[p for p in matching if p[4]!='59']
    if set(p[4] for p in actual)!=set(EXPECTED_COUNTIES):
        raise ValueError(f'CA-13 county set differed from expected: {sorted(set(p[4] for p in actual))}')
    if any(county_names.get(k)!=v for k,v in EXPECTED_COUNTIES.items()):
        raise ValueError('CA 2026 county code map changed')
    codes=set()
    for row in matching:
        if len(row)<12 or row[7]!='':raise ValueError('CA-13 vote record layout changed')
        if (len(row)-8)%4!=0:raise ValueError('CA-13 invalid candidate field count')
        for i in range(8,len(row),4):
            codes.add(row[i])
    if len(codes)!=2:raise ValueError(f'CA-13 candidate set changed: {sorted(codes)}')
    people=candidate_map(candidate_file,codes)
    counties=[]
    for row in actual:
        reporting=int(row[5]);total=int(row[6]);
        if total<=0 or reporting>total:raise ValueError('CA-13 bad precinct counts in '+row[4])
        votes=[]
        for i in range(8,len(row),4):
            code=row[i];count=int(row[i+1]);name,party=people[code]
            votes.append({'name':name,'party':party,'votes':count})
        counties.append({'name':county_names[row[4]],'candidates':votes,
                         'precincts_reporting':reporting,'precincts_total':total})
    statewide_votes={p[8+i*4]:int(p[9+i*4]) for i in range((len(statewide[0])-8)//4) for p in statewide}
    for code in codes:
        # Reject mismatched state-level totals rather than silently presenting
        # one aggregate that omits a county, e.g. a malformed source update.
        if sum(c['votes'] for county in counties for c in county['candidates'] if c['name']==people[code][0])!=statewide_votes[code]:
            raise ValueError('CA-13 county votes do not reconcile to the published statewide district total')
    ts=source_update(vote_file)
    return {'race':'CA-13','source':'California Secretary of State',
            'source_url':'https://media.sos.ca.gov/',
            'updated_at':ts.isoformat().replace('+00:00','Z'),'metric':'precincts',
            'counties':counties}

def build_snapshot(parsed:dict,now:datetime)->dict:
    return {**parsed,'test_data':now<CLOSE_UTC or datetime.fromisoformat(parsed['updated_at'].replace('Z','+00:00'))<CLOSE_UTC,
            'source_hash':hashlib.sha256(json.dumps(parsed['counties'],sort_keys=True).encode()).hexdigest()}

def main():
    v=fetch('V26GG.txt');c=fetch('C26GG.txt');s=fetch('S26GG.txt')
    parsed=parse_files(v,c,s)
    output=build_snapshot(parsed,datetime.now(timezone.utc))
    prior={}
    if DEST.exists():
        try:prior=json.loads(DEST.read_text())
        except (OSError,ValueError):pass
    if prior.get('updated_at') and output['updated_at']<prior['updated_at']:
        raise ValueError('CA source timestamp rolled backwards')
    if prior==output:print('CA-13: published county totals unchanged');return
    DEST.parent.mkdir(exist_ok=True,parents=True)
    temp=DEST.with_suffix('.tmp');temp.write_text(json.dumps(output,indent=2)+'\n')
    os.replace(temp,DEST)
    print('CA-13: updated',len(output['counties']),'counties from CA election media files, test=',output['test_data'])

if __name__=='__main__':main()

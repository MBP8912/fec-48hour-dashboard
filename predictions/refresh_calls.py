#!/usr/bin/env python3
"""Refresh 2026 election calls only when explicitly attributed to the AP."""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

HERE=Path(__file__).resolve().parent
PICKS=json.loads((HERE/"picks.json").read_text())["races"]
CALLS=HERE/"calls.json"
URLS=("https://thepeoplestally.com/data/results.json","https://thepeoplestally.com/api/live")
def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()
def normalize(s):
    return re.sub(r"[^a-z0-9]","",str(s or "").lower())
def date(s):
    if not s:return None
    try:
        if isinstance(s,(int,float)):return dt.datetime.fromtimestamp(s,dt.timezone.utc).isoformat()
        d=dt.datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc).isoformat()
    except (ValueError,TypeError,OverflowError):return None
def attributed(v):
    if isinstance(v,list):return any(attributed(x) for x in v)
    if isinstance(v,dict):return any(attributed(v.get(k)) for k in ("source","name","desk","provider","agency","code"))
    if not v:return False
    return any(bool(re.search(r"\b(ap|associated\s+press)\b",x,re.I)) and not bool(re.search(r"\b(no|not|non|unverified)\s*-?\s*ap\b",x,re.I)) for x in re.split("[,;/|]",str(v)))
def racekey(v):
    s=str(v).strip().upper().replace("_","-")
    s=re.sub(r"^SEN(?:ATE)?-","S-",s)
    s=re.sub(r"^GOV(?:ERNOR)?-","G-",s)
    s=re.sub(r"^HOUSE-","H-",s)
    s=re.sub(r"^(H-[A-Z]{2})-0+(\d+)$",r"\1-\2",s)
    if s in ("S-OH","S-OH-SP","S-OH-SPECIAL"):return "S-OH-SP"
    return s
def winner(rec):
    w=rec.get("winner_name") or rec.get("winnerName") or rec.get("winner_candidate")
    if isinstance(w,str) and w.strip():return w.strip()
    if isinstance(w,dict):return str(w.get("name") or w.get("candidate_name") or "").strip()
    w=rec.get("winner")
    if isinstance(w,dict):return str(w.get("name") or "").strip()
    for c in rec.get("cands",rec.get("candidates",[])) or []:
        if not isinstance(c,dict):continue
        v=c.get("winner",c.get("is_winner",False))
        if v is True or str(v).lower() in ("1","true","x","winner"):
            return str(c.get("name") or c.get("candidate_name") or "").strip()
    return None
def calls_from(payload):
    result=payload.get("res") or payload.get("results") or payload
    if not isinstance(result,dict):raise ValueError("Invalid results bundle")
    races=result.get("races") or result
    if isinstance(races,list):races={str(x.get("id") or x.get("race_id") or ""):x for x in races if isinstance(x,dict)}
    if not isinstance(races,dict) or not races:raise ValueError("No races")
    keyed={racekey(k):v for k,v in races.items()}
    generated=date(payload.get("generated_at") or payload.get("at") or result.get("generated_at"))
    if generated and generated[:10]<"2026-11-03":raise ValueError("Stale election year")
    results={}
    aliases={"jennycostahoneycutt":"jennyhoneycutt","jennyhoneycut":"jennyhoneycutt","jimpillon":"jimpillen","michaelwatley":"michaelwhatley"}
    for race in PICKS:
        rec=keyed.get(racekey(race["id"]))
        if not isinstance(rec,dict):continue
        if not attributed(rec.get("called_by") or rec.get("calledBy") or rec.get("call_source") or rec.get("callSource")):continue
        status=str(rec.get("status") or rec.get("race_status") or "").lower()
        if any(x in status for x in ("not called","uncalled","retract","withdraw")):continue
        w=winner(rec)
        if not w or normalize(w) in ("d","r","dem","gop","democrat","republican"):continue
        candidate=aliases.get(normalize(w),normalize(w))
        for c in race["candidates"]:
            name=normalize(c["name"])
            if candidate==name or candidate.endswith(name) or name.endswith(candidate):
                w=c["name"]
                break
        url=rec.get("url") or rec.get("source_url") or "https://apnews.com/hub/election-2026"
        if not isinstance(url,str) or not url.startswith("https://"):url="https://apnews.com/hub/election-2026"
        results[race["id"]]={"winner":w,"calledBy":"AP","calledAt":date(rec.get("called_at") or rec.get("asof") or rec.get("winnerDateTime")) or generated,"sourceUrl":url,"sourceFeed":"The People's Tally (AP-attributed call)"}
    return results,generated,len(races)
def main():
    prior=json.loads(CALLS.read_text()) if CALLS.exists() else {"calls":{}}
    if len(prior.get("calls",{}))==len(PICKS):
        print("All races already AP-called")
        return
    checked=utc()
    for url in URLS:
        try:
            req=Request(url,headers={"User-Agent":"ElectionPredictionPool/1.0","Accept":"application/json"})
            with urlopen(req,timeout=18) as resp:payload=json.load(resp)
            updates,generated,n=calls_from(payload)
            calls=dict(prior.get("calls",{}))
            calls.update(updates)
            out={"electionDate":"2026-11-03","lastChecked":checked,"lastSuccess":checked,"sourceGenerated":generated,"sourceUrl":url,"feedRaceCount":n,"calls":calls,"status":"ok"}
            CALLS.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
            print(f"Checked {n} races; {len(calls)} AP-called")
            return
        except (OSError,ValueError,TypeError,KeyError,RuntimeError) as e:
            print(f"Unavailable: {url}: {e}",file=sys.stderr)
    prior.update({"lastChecked":checked,"status":"feed_unavailable","lastError":"Public AP-attributed results feed unavailable"})
    CALLS.write_text(json.dumps(prior,indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":
    main()

/* 2026 Election Night Results Monitor — free, attributed, nonpartisan data. */
(() => {
  'use strict';

  const ELECTION_DATE_UTC = Date.parse('2026-11-03T12:00:00Z');
  const CLOSE_9 = Date.parse('2026-11-04T02:00:00Z');
  const CLOSE_11 = Date.parse('2026-11-04T04:00:00Z');
  const POLL_INTERVAL = 60_000;
  const DATA_TIMEOUT = 13_000;
  const STATES = {
    NY:{name:'New York',fips:'36',url:'https://nyenr.elections.ny.gov/'},
    CO:{name:'Colorado',fips:'08',url:'https://www.sos.state.co.us/pubs/elections/Results/2026/index.html'},
    IA:{name:'Iowa',fips:'19',url:'https://sos.iowa.gov/elections/results/index.html'},
    MN:{name:'Minnesota',fips:'27',url:'https://electionresults.sos.mn.gov/'},
    NE:{name:'Nebraska',fips:'31',url:'https://electionresults.nebraska.gov/'},
    WI:{name:'Wisconsin',fips:'55',url:'https://myvote.wi.gov/en-us/Election-Results'},
    CA:{name:'California',fips:'06',url:'https://electionresults.sos.ca.gov/'},
  };
  const RACES = [
    {id:'NY-17', label:'NY-17', type:'house', state:'NY', district:'17', candidates:[['Mike Lawler','R'],['Cait Conley','D']]},
    {id:'NY-19', label:'NY-19', type:'house', state:'NY', district:'19', candidates:[['Peter Oberacker','R'],['Josh Riley','D']]},
    {id:'IA-01', label:'IA-1', type:'house', state:'IA', district:'01', candidates:[['Mariannette Miller-Meeks','R'],['Christina Bohannan','D'],['Michael Bridgford','O']]},
    {id:'IA-GOV', label:'IA Governor', type:'governor', state:'IA', candidates:[['Zach Lahn','R'],['Rob Sand','D']]},
    {id:'CO-04', label:'CO-4', type:'house', state:'CO', district:'04', candidates:[['Lauren Boebert','R'],['Eileen Laubacher','D'],['Douglas Mangeris','O']]},
    {id:'CO-05', label:'CO-5', type:'house', state:'CO', district:'05', candidates:[['Jeff Crank','R'],['Jessica Killin','D'],['Christopher Mitchell','O'],['Mark Elworth','O']]},
    {id:'CO-GOV', label:'CO Governor', type:'governor', state:'CO', candidates:[['Victor Marx','R'],['Phil Weiser','D'],['Stephen Hamilton','O'],['Eric Mulder','O'],['Jeff Peckman','O'],['Erik Underwood','O'],['Greg Lopez','O']]},
    {id:'MN-01', label:'MN-1', type:'house', state:'MN', district:'01', candidates:[['Brad Finstad','R'],['Jake Johnson','D']]},
    {id:'NE-02', label:'NE-2', type:'house', state:'NE', district:'02', candidates:[['Brinker Harding','R'],['Denise Powell','D'],['Eric Michael Foreman','O']]},
    {id:'WI-01', label:'WI-1', type:'house', state:'WI', district:'01', candidates:[['Bryan Steil','R'],['Mitchell Berman','D']]},
    {id:'CA-13', label:'CA-13', type:'house', state:'CA', district:'13', candidates:[['Kevin Lincoln','R'],['Adam Gray','D']], close:CLOSE_11},
  ].map(r => ({...r, close:r.close||CLOSE_9, openAmerica:['CO','IA','MN'].includes(r.state)}));
  const raceIndex = new Map(RACES.map(r => [r.id,r]));
  const state = {
    results:new Map(),
    selected:null,
    filter:'all',
    sort:'votes',
    sortAscending:false,
    selectedCounty:null,
    mapData:null,
    mapLoading:false,
    mapError:false,
    networkStatus:'checking',
    checkedAt:null,
    responseOk:0,
    responseErrors:0,
    refreshing:false,
    mnCounties:[],
  };
  const el = id => document.getElementById(id);
  const escapeHtml = v => String(v == null ? '' : v).replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
  const int = v => Number.isFinite(Number(v)) ? Math.max(0,Math.trunc(Number(v))) : null;
  const percent = v => v === null || v === undefined || v === '' || !Number.isFinite(Number(v)) ? null : Math.min(100,Math.max(0,Number(v)));
  const fmt = v => v == null ? '—' : Number(v).toLocaleString('en-US');
  const pct = v => v == null ? '—' : `${Number(v).toFixed(1)}%`;
  const cleanParty = p => {const v=String(p||'').toUpperCase();return v==='R'||v==='REP'||v==='REPUBLICAN'?'R':v==='D'||v==='DFL'||v==='DEM'||v==='DEMOCRATIC'?'D':'O';};
  const shortName = n => String(n||'').replace(/\s*\([^)]*\)\s*$/,'').trim();
  const candidate = (name,party,votes,share) => ({name:shortName(name),party:cleanParty(party),votes:int(votes)??0,share:percent(share)});
  const getTime = raw => {const t = Date.parse(String(raw||''));return Number.isFinite(t) ? t : null;};
  const etDate = (t, opts={hour:'numeric',minute:'2-digit',timeZoneName:'short'}) => t ? new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',...opts}).format(new Date(t)) : 'Unavailable';
  const timeText = t => t ? etDate(t) : 'No verified update';
  const closed = r => Date.now() >= r.close;
  const fresh = t => t && (Date.now()-t)<20*60*1000;
  const sumVotes = cands => cands.reduce((a,c)=>a+(c.votes||0),0);
  const totalCandidates = (cands,known) => cands.reduce((a,c)=>a+(Number.isFinite(c.votes) ? c.votes : 0),0) || known || 0;
  const normalizedCounty = name => String(name||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(county|parish|borough|census area|city and borough)\b/g,'').replace(/[^a-z0-9]+/g,'').trim();
  const permittedUrl = url => /^https:\/\/(?:electionresults\.sos\.mn\.gov|electionresultsfiles\.sos\.mn\.gov|openamerica\.io|thepeoplestally\.com|www\.sos\.state\.co\.us|sos\.iowa\.gov|nyenr\.elections\.ny\.gov|electionresults\.nebraska\.gov|myvote\.wi\.gov|electionresults\.sos\.ca\.gov)(?:\/|$)/i.test(url) ? url : null;
  const htmlSource = (label,url) => {const safe=permittedUrl(url||'');return safe?`<a href="${escapeHtml(safe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)} ↗</a>`:escapeHtml(label);};
  const emptyRace = r => ({id:r.id,candidates:[],total:0,progress:null,progressKind:null,source:null,asof:null,counties:[],countySource:null,countyAsOf:null});
  RACES.forEach(r=>state.results.set(r.id,emptyRace(r)));

  function acceptRace(r,incoming){
    const existing=state.results.get(r.id);
    if (!incoming || incoming.total<=0 || !incoming.asof || incoming.asof<ELECTION_DATE_UTC || !closed(r)) return;
    if (incoming.candidates.length===0) return;
    if (existing.total > 0 && existing.asof && existing.asof > incoming.asof+3*60_000) return;
    const priority = source => source==='Open America' ? 2 : source==='Minnesota Secretary of State'?3:1;
    if (existing.asof && existing.asof===incoming.asof && priority(existing.source)>priority(incoming.source)) return;
    if (!existing.asof || incoming.asof>=existing.asof-3*60_000 || existing.total===0) {
      Object.assign(existing,{candidates:incoming.candidates,total:incoming.total,progress:incoming.progress,
        progressKind:incoming.progressKind||null,source:incoming.source,asof:incoming.asof});
    }
  }

  function parseOpenAmerica(json,office){
    if (!json || json.api!==1 || Number(json.year)!==2026 || String(json.office).toLowerCase()!==office.toLowerCase() || !json.races || typeof json.races!=='object') return false;
    const asof=getTime(json.as_of);
    for(const r of RACES.filter(x=>x.type===(office==='House'?'house':'governor'))){
      const key=r.type==='governor'?r.state:r.id;
      const row=json.races[key]; if(!row || !Array.isArray(row.cands)) continue;
      const cands=row.cands.filter(c=>c&&c.n).map(c=>candidate(c.n,c.p,c.v,c.pct));
      const total=Math.max(int(row.total)??0,sumVotes(cands));
      const progress=percent(row.pct_in);
      acceptRace(r,{candidates:cands,total,progress,progressKind:progress===null?null:'precincts',source:'Open America',asof});
    }
    return true;
  }

  function parseTally(json){
    if(!json || typeof json!=='object'|| !json.races||typeof json.races!=='object')return false;
    const defaultTime=getTime(json.generated_at);
    for(const r of RACES){
      const tallyId=r.type==='governor'?`G-${r.state}`:`H-${r.id}`;
      const row=json.races[tallyId]; if(!row || !Array.isArray(row.cands))continue;
      const candidates=row.cands.filter(c=>c&&c.name).map(c=>candidate(c.name,c.party,c.votes,c.pct));
      const ts=getTime(row.asof)||defaultTime;
      const estimated=percent(row.exp);
      acceptRace(r,{candidates,total:sumVotes(candidates),progress:estimated,
        progressKind:estimated===null?null:'estimated votes',source:"The People's Tally",asof:ts});
    }
    return true;
  }

  function parseMinnesota(json){
    if (!json || json.race!=='MN-01' || !Array.isArray(json.counties)) return false;
    const r=raceIndex.get('MN-01'), existing=state.results.get(r.id);
    const ts=getTime(json.updated_at);
    const counties=json.counties.filter(c=>c&&typeof c.name==='string').map(c=>{
      const candidates=Array.isArray(c.candidates)?c.candidates.map(v=>candidate(v.name,v.party,v.votes,null)):[];
      const total=sumVotes(candidates);
      return {name:c.name,countyId:String(c.county_id||''),candidates,total,
        precinctsReporting:int(c.precincts_reporting),precinctsTotal:int(c.precincts_total),
        progress:c.precincts_total>0?100*(int(c.precincts_reporting)||0)/int(c.precincts_total):null,
        progressKind:'precincts'};
    });
    existing.counties=counties;
    existing.countySource='Minnesota Secretary of State';
    existing.countyAsOf=ts;
    state.mnCounties=counties;
    if (json.test_data===true || !closed(r) || !ts || ts<ELECTION_DATE_UTC) return true;
    const grouped=new Map();let countReport=0,countTotal=0;
    for (const c of counties){
      countReport+=c.precinctsReporting||0;countTotal+=c.precinctsTotal||0;
      for (const cand of c.candidates){const key=cand.name+'|'+cand.party;
        const prev=grouped.get(key)||{...cand,votes:0};prev.votes+=cand.votes;grouped.set(key,prev);}
    }
    const candidates=[...grouped.values()];
    acceptRace(r,{candidates,total:sumVotes(candidates),progress:countTotal>0?countReport/countTotal*100:null,
      progressKind:countTotal>0?'precincts':null,source:'Minnesota Secretary of State',asof:ts});
    return true;
  }


  function parseNebraska(json){
    if (!json || json.race!=='NE-02' || !Array.isArray(json.counties)) return false;
    const r=raceIndex.get('NE-02'), existing=state.results.get(r.id);
    const ts=getTime(json.updated_at);
    const counties=json.counties.filter(c=>c&&typeof c.name==='string').map(c=>{
      const cands=Array.isArray(c.candidates)?c.candidates.map(v=>candidate(v.name,v.party,v.votes,null)):[];
      return {name:c.name,candidates:cands,total:sumVotes(cands),
        precinctsReporting:null,precinctsTotal:null,progress:null,progressKind:null};
    });
    if (counties.length!==3) return false;
    existing.counties=counties;
    existing.countySource='Nebraska Secretary of State';
    existing.countyAsOf=ts;
    if (json.test_data===true || !closed(r) || !ts || ts<ELECTION_DATE_UTC) return true;
    const grouped=new Map();
    for (const c of counties){for(const cand of c.candidates){
      const key=cand.name+'|'+cand.party;
      const prev=grouped.get(key)||{...cand,votes:0};prev.votes+=cand.votes;grouped.set(key,prev);
    }}
    const candidates=[...grouped.values()];
    acceptRace(r,{candidates,total:sumVotes(candidates),progress:null,progressKind:null,
      source:'Nebraska Secretary of State',asof:ts});
    return true;
  }

  function parseNewYork(json){
    if (!json || !json.races || typeof json.races!== 'object') return false;
    const ts=getTime(json.source_updated_at);
    for(const id of ['NY-17','NY-19']){
      const row=json.races[id],r=raceIndex.get(id);
      if(!row||!r||!Array.isArray(row.candidates))continue;
      const cands=row.candidates.filter(v=>v&&v.name).map(v=>candidate(v.name,v.party,v.votes,null));
      const reported=int(row.precincts_reporting),total=int(row.precincts_total);
      const progress=total>0&&reported<=total?100*reported/total:null;
      if(json.test_data===true)continue;
      acceptRace(r,{candidates:cands,total:sumVotes(cands),progress,
        progressKind:progress===null?null:'election districts',
        source:'New York State Board of Elections',asof:ts});
    }
    return true;
  }

  async function fetchJSON(url){
    const ctrl=new AbortController();const timeout=setTimeout(()=>ctrl.abort(),DATA_TIMEOUT);
    try{const res=await fetch(url,{cache:'no-store',credentials:'omit',signal:ctrl.signal,headers:{Accept:'application/json'}});
      if(!res.ok)throw new Error(`HTTP ${res.status}`);
      const json=await res.json();if(!json||typeof json!=='object')throw new Error('Unexpected response');return json;
    }finally{clearTimeout(timeout);}
  }

  async function refresh(){
    if(state.refreshing)return;
    state.refreshing=true;
    const button=el('refresh-button');button.disabled=true;button.innerHTML='↻ Checking…';
    const jobs=[
      fetchJSON('https://openamerica.io/elections/results.json?year=2026&office=House').then(j=>parseOpenAmerica(j,'House')),
      fetchJSON('https://openamerica.io/elections/results.json?year=2026&office=Governor').then(j=>parseOpenAmerica(j,'Governor')),
      fetchJSON('https://thepeoplestally.com/data/results.json').then(parseTally),
      fetchJSON('./data/official-mn.json?v='+Date.now()).then(parseMinnesota),
      fetchJSON('./data/official-ne.json?v='+Date.now()).then(parseNebraska),
      fetchJSON('./data/official-ny.json?v='+Date.now()).then(parseNewYork),
    ];
    const results=await Promise.allSettled(jobs);
    state.checkedAt=Date.now();
    state.responseOk=results.filter(x=>x.status==='fulfilled'&&x.value===true).length;
    state.responseErrors=results.length-state.responseOk;
    state.networkStatus=state.responseOk ? 'connected' : 'unavailable';
    state.refreshing=false;
    button.disabled=false;button.innerHTML='<span aria-hidden="true">↻</span> Refresh';
    render();
  }

  function render(){renderHeader();renderStats();renderOverview();if(state.selected)renderDetail();}
  function renderHeader(){
    const status=el('connection-state'),chip=el('live-chip');
    status.textContent=state.networkStatus==='connected'?'Sources checked':state.networkStatus==='unavailable'?'Feed unavailable':'Connecting';
    chip.classList.toggle('chip-error',state.networkStatus==='unavailable');
    el('clock-label').textContent=etDate(Date.now(),{weekday:'short',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
    const upcoming=RACES.filter(r=>!closed(r)).sort((a,b)=>a.close-b.close);
    el('next-closing').textContent=upcoming.length?etDate(upcoming[0].close,{hour:'numeric',minute:'2-digit',timeZoneName:'short'}):'Polls closed';
    el('next-closing-caption').textContent=upcoming.length?(upcoming[0].close===CLOSE_9?'10 tracked contests':'CA-13'):'All 11 tracked contests';
  }
  function renderStats(){
    const received=RACES.filter(r=>state.results.get(r.id).total>0).length;
    el('stat-reporting').textContent=String(received);
    el('stat-reporting-detail').textContent=received?'with nonzero published totals':'No election-night totals yet';
    el('stat-closed').textContent=String(RACES.filter(closed).length);
    const updates=RACES.map(r=>state.results.get(r.id)).filter(x=>x.total>0 && x.asof).sort((a,b)=>b.asof-a.asof);
    el('stat-updated').textContent=updates.length?etDate(updates[0].asof,{hour:'numeric',minute:'2-digit',timeZoneName:'short'}):'—';
    el('stat-source').textContent=updates.length?updates[0].source:'No verified results';
    const banner=el('system-banner');
    if (received===0 && Date.now()<CLOSE_9){
      banner.classList.remove('warning');banner.innerHTML='<span class="banner-symbol">i</span><div><b>Results have not started.</b> Polls close at 9 PM ET for most tracked races and 11 PM ET for CA-13. Live data will appear only when verified sources publish counts.</div>';
    }else if (received===0){
      banner.classList.add('warning');banner.innerHTML='<span class="banner-symbol">!</span><div><b>Awaiting verified live vote totals.</b> Sources may not publish immediately after polls close. Races without a compatible free feed remain clearly marked as unavailable, never zero.</div>';
    }else if (RACES.some(r=>closed(r)&&!r.openAmerica && state.results.get(r.id).total===0)){
      banner.classList.add('warning');banner.innerHTML='<span class="banner-symbol">!</span><div><b>Partial source coverage.</b> Totals are updating for supported races. Some states do not have a verified, reusable free live feed; those races link to their official results pages.</div>';
    }else{banner.classList.remove('warning');banner.innerHTML='<span class="banner-symbol">i</span><div><b>Unofficial returns.</b> These are votes reported so far, not projections or race calls. Candidate totals and precinct percentages can change with later returns.</div>';}
  }
  const candVisible = (r,data) => data.total>0?data.candidates:[...r.candidates].map(c=>candidate(c[0],c[1],0,null));
  function renderOverview(){
    const tbody=el('race-rows');
    const rows=RACES.filter(r=>state.filter==='all'||(state.filter==='reporting'&&state.results.get(r.id).total>0)||state.filter===r.type);
    tbody.innerHTML=rows.map(r=>{
      const data=state.results.get(r.id), candidates=candVisible(r,data);
      const top=candidates.filter(c=>c.party==='D'||c.party==='R');
      const shown=top.length?top: candidates.slice(0,2);
      const otherCount=candidates.length-shown.length;
      const hasVotes=data.total>0;
      const candidateHtml=shown.map(c=>`<div class="vote-line"><span class="vote-name"><i class="party-swatch p-${escapeHtml(c.party)}"></i><span>${escapeHtml(c.name)}</span></span><span class="vote-number">${hasVotes?fmt(c.votes):'—'}${hasVotes?` <span class="muted">${pct(100*c.votes/data.total)}</span>`:''}</span></div>`).join('');
      const bars=hasVotes?`<div class="micro-bars">${candidates.map(c=>`<i style="width:${Math.max(0,100*c.votes/data.total)}%;background:${c.party==='D'?'#367ed0':c.party==='R'?'#d34d52':'#9d9cb2'}"></i>`).join('')}</div>`:'';
      const progressHtml=data.progress==null?`<span class="muted">Not available</span>`:`<div class="progress-value">${pct(data.progress)}</div><div class="progress-type">${data.progressKind==='estimated votes'?'Est. votes counted':data.progressKind==='election districts'?'Election districts reporting':'Precincts reporting'}</div><div class="tiny-progress"><div style="width:${data.progress}%"></div></div>`;
      const officialCounty = r.state==='MN'||r.state==='NE';
      const status=!closed(r)?['Polls open','pre']:hasVotes?[fresh(data.asof)?'Reporting':'Snapshot','active']:(r.openAmerica||officialCounty)?['Awaiting feed','stale']:['No live feed','missing'];
      const progressExplanation=hasVotes?` <span class="muted">· ${fmt(data.total)} votes</span>`:'';
      return `<tr tabindex="0" role="link" data-race="${r.id}" aria-label="Open ${escapeHtml(r.label)} results"><td><div class="race-title">${escapeHtml(r.label)}</div><div class="race-sub">${r.type==='governor'?'Governor':'U.S. House'} · ${escapeHtml(STATES[r.state].name)}</div></td><td class="vote-pair">${candidateHtml}${otherCount>0?`<span class="muted">+ ${otherCount} additional candidate${otherCount>1?'s':''}</span>`:''}${bars}${progressExplanation}</td><td>${progressHtml}</td><td><span class="poll-time">${r.close===CLOSE_11?'11:00':'9:00'} PM ET</span></td><td><span class="pill ${status[1]}">${status[0]}</span></td><td class="row-arrow">›</td></tr>`;
    }).join('')||'<tr><td colspan="6" class="muted">No races match this filter.</td></tr>';
    el('board-refresh').textContent=state.checkedAt?`Checked ${timeText(state.checkedAt)} · ${state.responseOk}/${state.responseOk+state.responseErrors} feeds responding · Auto-refresh every 60 sec`:'Checking free public data feeds…';
  }
  function renderDetail(){
    const r=raceIndex.get(state.selected);if(!r)return;
    const data=state.results.get(r.id),hasVotes=data.total>0;
    el('detail-title').textContent=r.type==='governor'?`${STATES[r.state].name} Governor`:`${r.label} · U.S. House`;
    el('detail-subtitle').textContent=hasVotes?`${fmt(data.total)} reported votes · Unofficial results`:`${STATES[r.state].name} · Awaiting verified election-night returns`;
    el('detail-close').textContent=`${r.close===CLOSE_11?'11:00':'9:00'} PM ET`;
    const cands=candVisible(r,data);
    el('detail-candidates').innerHTML=cands.map(c=>{
      const share=hasVotes?100*c.votes/data.total:0;
      return `<article class="candidate-card"><div class="candidate-topline"><span><i class="party-swatch p-${c.party}"></i> ${escapeHtml(c.name)}</span><small>${c.party==='D'?'DEMOCRATIC':c.party==='R'?'REPUBLICAN':'OTHER'}</small></div><div class="candidate-total">${hasVotes?fmt(c.votes):'—'}</div><div class="candidate-share">${hasVotes?pct(share)+' of reported votes':'Votes not yet reported'}</div><div class="candidate-track"><i style="width:${share}%;background:${c.party==='D'?'#69a9ee':c.party==='R'?'#f1898c':'#b4acd4'}"></i></div></article>`;
    }).join('');
    el('detail-asof').textContent=hasVotes?`${data.source} · last feed update ${timeText(data.asof)}`:'No verified live totals yet';
    el('detail-progress').textContent=data.progress==null?'Reporting percentage not available':`${pct(data.progress)} ${data.progressKind==='estimated votes'?'of estimated vote counted':data.progressKind==='election districts'?'of election districts reporting':'of precincts reporting'}`;
    const warn=el('detail-warning');
    if(!closed(r)){warn.classList.remove('warning');warn.innerHTML='<span class="banner-symbol">i</span><div><b>Polls have not closed.</b> This page will display only verified returns from November 3, 2026; any pre-election test data is ignored.</div>';}
    else if(!hasVotes){warn.classList.add('warning');warn.innerHTML=`<span class="banner-symbol">!</span><div><b>No verified vote totals from a supported feed.</b> ${r.openAmerica||r.state==='NE'||r.state==='NY'?'A free official-data feed is configured but no returns have arrived.':'The available free feeds have not provided usable totals for this race.'} Check ${htmlSource(STATES[r.state].name+' official results',STATES[r.state].url)}.</div>`;}
    else if(!fresh(data.asof)){warn.classList.add('warning');warn.innerHTML=`<span class="banner-symbol">!</span><div><b>Last source update may be stale.</b> These are the last successfully obtained unofficial results from ${escapeHtml(data.source)} as of ${escapeHtml(timeText(data.asof))}. Check ${htmlSource('official results',STATES[r.state].url)}.</div>`;}
    else{warn.classList.remove('warning');warn.innerHTML=`<span class="banner-symbol">i</span><div><b>Unofficial returns, not a race call.</b> Source: ${escapeHtml(data.source)}. Last source update: ${escapeHtml(timeText(data.asof))}. ${htmlSource('Official state election website',STATES[r.state].url)}.</div>`;}
    renderCounties(r,data);
    renderMap(r,data);
  }
  function renderCounties(r,data){
    const rows=data.counties||[];
    const sorted=[...rows].sort((a,b)=>{
      const aa=state.sort==='name'?a.name.toLowerCase():state.sort==='progress'?a.progress??-1:a.total;
      const bb=state.sort==='name'?b.name.toLowerCase():state.sort==='progress'?b.progress??-1:b.total;
      const n=typeof aa==='string'?aa.localeCompare(bb):aa-bb;
      return state.sortAscending?n:-n;
    });
    const actual=closed(r)&&data.countyAsOf&&data.countyAsOf>=ELECTION_DATE_UTC;
    el('county-count').textContent=`${rows.length} counties ${rows.length?'in this feed':''}`;
    el('county-rows').innerHTML=sorted.length?sorted.map(c=>{
      const hasC=actual&&c.total>0;
      const leader=hasC?[...c.candidates].sort((a,b)=>b.votes-a.votes)[0]:null;
      return `<tr data-county="${escapeHtml(c.name)}" class="${state.selectedCounty===c.name?'selected':''}"><td><div class="county-name">${escapeHtml(c.name)}</div><div class="county-sub">${leader?`<i class="party-swatch p-${leader.party}"></i> ${escapeHtml(leader.name)} leading`:'No reported votes'}</div></td><td>${hasC?fmt(c.total):'—'}</td><td>${actual?pct(c.progress):'—'}</td><td>${actual&&c.progress!=null?pct(100-c.progress):'—'}</td></tr>`;
    }).join(''):`<tr><td colspan="4"><span class="muted">No verified, race-specific county results available from the free feeds. The map shows county boundaries for geographic reference, not invented vote totals. ${htmlSource('Official results',STATES[r.state].url)}</span></td></tr>`;
    el('county-source').innerHTML=rows.length?`Source: ${escapeHtml(data.countySource||'official county file')} · ${escapeHtml(timeText(data.countyAsOf))}`:`County source: ${htmlSource('official election office',STATES[r.state].url)}`;
    const hasCountyPct=rows.some(c=>c.progress!=null);
    el('county-metric-caption').textContent=hasCountyPct?'% IN = reporting precincts · % OUT = precincts not yet reporting':'County reporting % not available from this source';
    el('county-description').textContent=hasCountyPct?'Percent in/out measures precincts reporting, not estimated ballots counted.':'Race-specific county totals and reporting progress are shown only where supplied by a verifiable public feed.';
  }
  function renderMap(r,data){
    const host=el('county-map');
    if(!state.mapData){
      host.innerHTML=`<div class="map-loading">${state.mapError?'Map boundaries unavailable':'Loading county boundaries…'}</div>`;
      if(!state.mapLoading&&!state.mapError)loadMap();return;
    }
    if(typeof window.d3==='undefined'||typeof window.topojson==='undefined'){
      host.innerHTML='<div class="map-loading">Map library unavailable. County table remains accessible.</div>';return;
    }
    const {d3,topojson}=window,all=state.mapData;
    const st=STATES[r.state], countyFeatures=topojson.feature(all,all.objects.counties).features.filter(c=>String(c.id).padStart(5,'0').startsWith(st.fips));
    if(!countyFeatures.length){host.innerHTML='<div class="map-loading">County boundary information unavailable.</div>';return;}
    const hasData=closed(r)&&data.countyAsOf&&data.countyAsOf>=ELECTION_DATE_UTC;
    const countyMap=new Map((data.counties||[]).map(c=>[normalizedCounty(c.name),c]));
    host.innerHTML='';
    const width=Math.max(310,host.clientWidth||480),height=Math.max(250,host.clientHeight||400);
    const svg=d3.select(host).append('svg').attr('viewBox',`0 0 ${width} ${height}`).attr('preserveAspectRatio','xMidYMid meet').attr('aria-label',`County map of ${st.name}`);
    const collection={type:'FeatureCollection',features:countyFeatures};
    const projection=d3.geoMercator().fitExtent([[20,20],[width-20,height-20]],collection),path=d3.geoPath(projection);
    const color=c=>{
      if(!hasData||!c||c.total===0)return '#e9eef3';
      const ordered=[...c.candidates].sort((a,b)=>b.votes-a.votes);
      if(ordered.length>1&&ordered[0].votes===ordered[1].votes)return '#b3afbe';
      return ordered[0]?.party==='D'?'#73a1db':ordered[0]?.party==='R'?'#dc858a':'#a298bf';
    };
    const counties=svg.append('g').selectAll('path').data(countyFeatures).join('path')
      .attr('d',path).attr('fill',g=>color(countyMap.get(normalizedCounty(g.properties?.name))))
      .attr('stroke','#fff').attr('stroke-width',0.65).attr('role','button').attr('tabindex',0)
      .attr('aria-label',g=>`${g.properties?.name||'County'}: ${fmt(countyMap.get(normalizedCounty(g.properties?.name))?.total) } votes reported`)
      .on('click',(_,g)=>chooseCounty(g.properties?.name))
      .on('keydown',(ev,g)=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();chooseCounty(g.properties?.name);}});
    counties.append('title').text(g=>{
      const name=g.properties?.name||'County', c=countyMap.get(normalizedCounty(name));
      return `${name} County · ${hasData&&c&&c.total>0?fmt(c.total)+' votes reported':c?'No votes reported':'No district-level results'}${hasData&&c&&c.progress!=null?' · '+pct(c.progress)+' precincts reporting':''}`;
    });
    if(state.selectedCounty){counties.filter(g=>normalizedCounty(g.properties?.name)===normalizedCounty(state.selectedCounty)).attr('stroke','#253a54').attr('stroke-width',2.3).raise();}
  }
  async function loadMap(){
    state.mapLoading=true;
    try{const json=await fetchJSON('https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json');
      if(!json?.objects?.counties)throw new Error('Missing TopoJSON counties');
      state.mapData=json;
    }catch(err){state.mapError=true;}finally{state.mapLoading=false; if(state.selected)renderMap(raceIndex.get(state.selected),state.results.get(state.selected));}
  }
  function chooseCounty(name){
    if(!name)return;
    const r=raceIndex.get(state.selected),data=state.results.get(r.id);
    const c=(data.counties||[]).find(c=>normalizedCounty(c.name)===normalizedCounty(name));
    if(!c)return;
    state.selectedCounty=c.name;renderCounties(r,data);renderMap(r,data);
    const row=[...el('county-rows').querySelectorAll('tr')].find(n=>n.dataset.county===c.name);
    if(row)row.scrollIntoView({block:'nearest',behavior:'smooth'});
  }
  function openRace(id,updateHistory=true){
    if(!raceIndex.has(id))return;
    state.selected=id;state.selectedCounty=null;
    el('overview-view').hidden=true;el('detail-view').hidden=false;
    if(updateHistory)history.pushState({race:id},'',`?race=${encodeURIComponent(id)}`);
    window.scrollTo({top:0,behavior:'instant'});render();
  }
  function back(updateHistory=true){
    state.selected=null;state.selectedCounty=null;
    el('overview-view').hidden=false;el('detail-view').hidden=true;
    if(updateHistory)history.pushState({},'',window.location.pathname);
    window.scrollTo({top:0,behavior:'instant'});render();
  }
  function route(){const id=new URLSearchParams(window.location.search).get('race');if(id&&raceIndex.has(id))openRace(id,false);else back(false);}
  el('race-rows').addEventListener('click',event=>{const tr=event.target.closest('tr[data-race]');if(tr)openRace(tr.dataset.race);});
  el('race-rows').addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){const tr=event.target.closest('tr[data-race]');if(tr){event.preventDefault();openRace(tr.dataset.race);}}});
  el('county-rows').addEventListener('click',event=>{const tr=event.target.closest('tr[data-county]');if(tr)chooseCounty(tr.dataset.county);});
  document.querySelectorAll('.county-table [data-sort]').forEach(btn=>btn.addEventListener('click',()=>{const sort=btn.dataset.sort;if(state.sort===sort)state.sortAscending=!state.sortAscending;else{state.sort=sort;state.sortAscending=sort==='name';}if(state.selected)renderCounties(raceIndex.get(state.selected),state.results.get(state.selected));}));
  el('race-filter').addEventListener('change',event=>{state.filter=event.target.value;renderOverview();});
  el('back-button').addEventListener('click',()=>back());
  el('refresh-button').addEventListener('click',refresh);
  window.addEventListener('popstate',route);
  setInterval(()=>{renderHeader();renderStats();},20_000);
  setInterval(refresh,POLL_INTERVAL);
  route();
  refresh();
})();

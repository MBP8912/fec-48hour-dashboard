/* NY-17 FEC Form 6 dashboard, no analytics, third-party scripts, or fabricated data */
(() => {
  'use strict';
  const COLORS = { lawler: '#cb5c58', conley: '#3d71c6' };
  const COMMITTEE_IDS = { lawler: 'C00815415', conley: 'C00900431' };
  const SVG = 'http://www.w3.org/2000/svg';
  let DATA = null;
  const $ = (id) => document.getElementById(id);
  const dollars = (cents) => new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:0}).format((Number(cents)||0)/100);
  const exact = (cents) => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format((Number(cents)||0)/100);
  const compact = (cents) => { const n=(Number(cents)||0)/100; return n >= 1000000 ? `$${(n/1000000).toFixed(n % 1000000 ? 1:0)}m` : n >= 1000 ? `$${(n/1000).toFixed(n % 1000 ? 1:0)}k` : `$${Math.round(n)}`; };
  const formatDay = (iso, year=false) => new Date(iso+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric',...(year?{year:'numeric'}:{})});
  const safeFecUrl = (committee, number) => /^C\d{8}$/.test(committee) && /^\d+$/.test(String(number)) ? `https://docquery.fec.gov/cgi-bin/forms/${committee}/${number}/f65` : null;
  const s = (tag, attrs={}, text) => {const n=document.createElementNS(SVG,tag); for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v)); if(text!==undefined)n.textContent=String(text);return n;};
  const html = (tag, className='', text=null) => {const n=document.createElement(tag);if(className)n.className=className;if(text!==null)n.textContent=String(text);return n;};

  function status(message, type='pending') {
    const node=$('status'); node.className=`status status-${type}`; node.textContent=message;
  }

  function drawChart(target, rows, key) {
    const host=$(target); host.replaceChildren();
    if (!rows.length) { host.appendChild(html('span','chart-empty','No verified contributions yet')); return; }
    const w=1000,h=320,m={l:76,r:19,t:14,b:48}, graphW=w-m.l-m.r, graphH=h-m.t-m.b;
    const svg=s('svg',{viewBox:`0 0 ${w} ${h}`, 'aria-hidden':'true', role:'presentation'});
    let max = Math.max(10000, ...rows.flatMap(r=>['lawler','conley'].map(c=>r[key][c])));
    const mag=Math.pow(10,Math.floor(Math.log10(max)));
    const step= Math.ceil(max / mag / 4)*mag;
    max=Math.ceil(max / step)*step;
    const xpos=(i)=> m.l+(i+.5)*graphW/rows.length;
    const ypos=(n)=>m.t+graphH*(1-Math.max(0,n)/max);
    for(let i=0;i<=4;i++) {
      const money=max*i/4, y=ypos(money);
      svg.appendChild(s('line',{x1:m.l,y1:y,x2:w-m.r,y2:y,class:'chart-grid'}));
      const axis=s('text',{x:m.l-11,y:y+4,'text-anchor':'end',class:'chart-axis'},compact(money));
      svg.appendChild(axis);
    }
    const every=Math.max(1,Math.ceil(rows.length/7));
    rows.forEach((r,i)=>{if(i%every===0||i===rows.length-1){svg.appendChild(s('text',{x:xpos(i),y:h-16,'text-anchor':'middle',class:'chart-axis'},formatDay(r.date)));}});
    if (key==='totals') {
      const band=graphW/rows.length, bw=Math.max(4,Math.min(20,band*.27));
      rows.forEach((r,i)=>['lawler','conley'].forEach((c,j)=>{
        const v=r[key][c], ht=Math.max(0,graphH * v / max), x=xpos(i)+(j===0?-bw-2:2), y=m.t+graphH-ht;
        if (v!==0) {
          const rect=s('rect',{x,y,width:bw,height:ht,rx:3,fill:COLORS[c],class:'chart-bar'});
          rect.appendChild(s('title',{},`${formatDay(r.date,true)} · ${c==='lawler'?'Lawler':'Conley'}: ${exact(v)}`));
          svg.appendChild(rect);
        }
      }));
    } else {
      for (const c of ['lawler','conley']) {
        const coords=rows.map((r,i)=>`${i===0?'M':'L'}${xpos(i).toFixed(1)} ${ypos(r[key][c]).toFixed(1)}`).join(' ');
        svg.appendChild(s('path',{d:coords,fill:'none',stroke:COLORS[c],'stroke-width':3,'stroke-linejoin':'round','stroke-linecap':'round'}));
        rows.forEach((r,i)=>{
          const circle=s('circle',{cx:xpos(i),cy:ypos(r[key][c]),r:4,fill:COLORS[c],stroke:'#fff','stroke-width':1.5,class:'chart-dot'});
          circle.appendChild(s('title',{},`${formatDay(r.date,true)} · ${c==='lawler'?'Lawler':'Conley'} running total: ${exact(r[key][c])}`));
          svg.appendChild(circle);
        });
      }
    }
    host.appendChild(svg);
  }

  function updateCards(data) {
    const last=data.daily[data.daily.length-1];
    const lawler=last?.cumulative?.lawler||0,conley=last?.cumulative?.conley||0;
    $('lawler-total').textContent=dollars(lawler);
    $('conley-total').textContent=dollars(conley);
    $('lawler-count').textContent=data.contributions.filter(x=>x.committee_id===COMMITTEE_IDS.lawler).length.toLocaleString();
    $('conley-count').textContent=data.contributions.filter(x=>x.committee_id===COMMITTEE_IDS.conley).length.toLocaleString();
    $('notice-count').textContent=data.filings.length.toLocaleString();
    $('difference').textContent=dollars(Math.abs(lawler-conley));
    $('difference-note').textContent= lawler===conley ? 'Both committees report the same total' :
       `${lawler>conley?'Lawler':'Conley'} reports more qualifying contributions`;
  }

  function openDetails(day, slug) {
    if (!DATA) return;
    const relevant=DATA.contributions.filter(x=>x.date===day&&x.committee_id===COMMITTEE_IDS[slug]);
    const campaign=slug==='lawler'?'Lawler for Congress':'Cait for New York';
    $('dialog-title').textContent=`${campaign} · ${formatDay(day,true)}`;
    $('dialog-summary').textContent=`${relevant.length} reported contribution${relevant.length===1?'':'s'} · ${exact(relevant.reduce((a,x)=>a+x.amount_cents,0))}`;
    const body=$('dialog-body'); body.replaceChildren();
    relevant.sort((a,b)=>b.amount_cents-a.amount_cents||a.contributor.localeCompare(b.contributor));
    for(const contribution of relevant) {
      const wrapper=html('div','dialog-row'), left=html('div'),right=html('div','dialog-amount');
      left.append(html('strong','',contribution.contributor));
      left.append(html('span','',contribution.state||'State not reported'));
      right.append(document.createTextNode(exact(contribution.amount_cents)));
      const url=safeFecUrl(contribution.committee_id,contribution.file_number);
      if(url){const link=html('a','',`FEC filing ${contribution.file_number} ↗`);link.href=url;link.target='_blank';link.rel='noopener noreferrer';right.append(link);}
      wrapper.append(left,right);body.append(wrapper);
    }
    const dialog=$('details-dialog');
    if(typeof dialog.showModal==='function') dialog.showModal(); else dialog.setAttribute('open','');
  }

  function updateTable(data) {
    const body=$('daily-table');body.replaceChildren();
    if(!data.daily.length) {const tr=html('tr'),td=html('td','table-pending','No contribution dates available.');td.colSpan=4;tr.append(td);body.append(tr);return;}
    for(const r of [...data.daily].reverse()){
      const tr=html('tr');
      const dateCell=html('td','date-cell',formatDay(r.date,true));tr.append(dateCell);
      tr.append(html('td','right lawler-cell',dollars(r.totals.lawler)));
      tr.append(html('td','right conley-cell',dollars(r.totals.conley)));
      const records=html('td');
      for(const slug of ['lawler','conley']) {
        const n=r.counts[slug];
        const button=html('button','detail-link',`${slug==='lawler'?'Lawler':'Conley'} ${n}`);
        button.type='button';button.disabled=n===0;
        button.title=n ? `View ${n} contribution${n===1?'':'s'} and FEC filing link${n===1?'':'s'}` : 'No qualifying notice contribution reported';
        button.addEventListener('click',()=>openDetails(r.date,slug));
        records.append(button);
      }
      tr.append(records);body.append(tr);
    }
    $('row-count').textContent=`${data.daily.length} days`;
  }

  function csvCell(value) {const t=String(value??'');return `"${t.replaceAll('"','""')}"`;}
  function downloadCsv() {
    if(!DATA||DATA.status!=='ok')return;
    const header=['Date received','Lawler daily USD','Lawler cumulative USD','Cait daily USD','Cait cumulative USD','FEC filing numbers for that day'];
    const rows=DATA.daily.map(row=>{
      const linked=DATA.contributions.filter(x=>x.date===row.date);
      const refs=[...new Set(linked.map(x=>`${x.committee_id}/${x.file_number}`))];
      return [row.date,(row.totals.lawler/100).toFixed(2),(row.cumulative.lawler/100).toFixed(2),
              (row.totals.conley/100).toFixed(2),(row.cumulative.conley/100).toFixed(2),refs.join('; ')];
    });
    const csv=[header,...rows].map(r=>r.map(csvCell).join(',')).join('\r\n');
    const objectUrl=URL.createObjectURL(new Blob([String.fromCharCode(0xfeff)+csv],{type:'text/csv;charset=utf-8'}));
    const a=html('a');a.href=objectUrl;a.download='ny17-fec-form6-october-2026.csv';document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(objectUrl),1000);
  }

  function render(data) {
    if(!data||data.status!=='ok') {
      status('Awaiting the first successful download and verification of official FEC Form 6 filings. No amounts are displayed until then.','pending');
      return;
    }
    if(!Array.isArray(data.daily)||!Array.isArray(data.contributions)||!Array.isArray(data.filings))throw new Error('Invalid dashboard data');
    DATA=data;
    const dt=new Date(data.generated_at);
    if(!Number.isNaN(dt.valueOf())){
      $('last-updated').textContent='◷ Checked '+dt.toLocaleString('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
    }
    status(`Verified FEC data · ${data.filings.length} Form 6 notice${data.filings.length===1?'':'s'} · ${data.contributions.length} qualifying entr${data.contributions.length===1?'y':'ies'}. Click a day's records to read the original reports.`,'good');
    updateCards(data);
    drawChart('daily-chart',data.daily,'totals');
    drawChart('cumulative-chart',data.daily,'cumulative');
    updateTable(data);
    $('download-csv').disabled=false;
    if(data.warnings?.length) {
      const warnings=$('data-warnings');warnings.hidden=false;warnings.replaceChildren();
      warnings.append(html('strong','',`Data review note${data.warnings.length===1?'':'s'}: `));
      warnings.append(document.createTextNode(data.warnings.join(' · ')));
    }
  }

  $('close-dialog').addEventListener('click',()=>{$('details-dialog').close?.();$('details-dialog').removeAttribute('open');});
  $('download-csv').addEventListener('click',downloadCsv);
  fetch('./data/data.json?t='+Date.now(),{cache:'no-store'})
    .then(response=>{if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json();})
    .then(render)
    .catch(error=>{status('Unable to load verified FEC data. The site is not displaying unverified figures. '+error.message,'error');});
})();

#!/usr/bin/env python3
"""Build an archived, auditable dashboard from original FEC Form 6 F65 records."""
from __future__ import annotations
import csv
import hashlib
import json
import os
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CACHE_FILE = ROOT / 'data' / 'cache.json'
OUTPUT_FILE = ROOT / 'data' / 'data.json'
START_DATE = date(2026, 10, 15)
END_DATE = date(2026, 10, 31)
FILED_FROM, FILED_THROUGH = '2026-10-01', '2026-11-10'
COMMITTEES = {
    'lawler': {'name': 'Lawler for Congress, Inc.', 'id': 'C00815415', 'candidate': 'Mike Lawler'},
    'conley': {'name': 'Cait for New York', 'id': 'C00900431', 'candidate': 'Cait Conley'},
}
# Source example supplied for this project. Still validated against its raw cover record.
KNOWN_F6_FILINGS = {'lawler': [2033856]}
AGENT = 'NY17-FEC-48h-dashboard/1.0 (public campaign finance transparency)'


def fetch_url(url: str, *, binary=False, tries=4):
    host = urlparse(url)
    if host.scheme != 'https' or host.hostname not in {'api.open.fec.gov', 'docquery.fec.gov'}:
        raise ValueError('Unexpected data source: ' + url)
    headers = {'User-Agent': AGENT, 'Accept': '*/*' if binary else 'application/json'}
    for attempt in range(tries):
        try:
            with urlopen(Request(url, headers=headers), timeout=35) as response:
                raw = response.read()
                return raw if binary else json.loads(raw.decode('utf-8'))
        except HTTPError as ex:
            if ex.code not in (429, 500, 502, 503, 504) or attempt == tries - 1:
                raise RuntimeError(f'FEC HTTP {ex.code} ({host.path})') from ex
            retry = ex.headers.get('Retry-After', '')
            time.sleep(min(int(retry), 60) if retry.isdigit() else 3*(attempt+1))
        except (URLError, TimeoutError, ConnectionError) as ex:
            if attempt == tries - 1:
                raise RuntimeError(f'FEC network error ({host.path}): {ex}') from ex
            time.sleep(2*(attempt+1))


def discover_f6(committee_id: str, api_key: str):
    """Discover all original/amended F6 notices via the raw e-filing API."""
    found = []
    for page in range(1, 25):
        params = {'api_key': api_key, 'committee_id': committee_id, 'form_type': 'F6',
                  'min_receipt_date': FILED_FROM, 'max_receipt_date': FILED_THROUGH,
                  'per_page': 100, 'page': page, 'sort': '-receipt_date'}
        result = fetch_url('https://api.open.fec.gov/v1/efile/filings/?' + urlencode(params))
        batch = result.get('results')
        if not isinstance(batch, list):
            raise RuntimeError('FEC API returned an invalid result list')
        found.extend(r for r in batch if str(r.get('committee_id', '')).upper() == committee_id
                     and str(r.get('form_type', '')).upper().startswith('F6'))
        pages = (result.get('pagination') or {}).get('pages')
        if not batch or (pages and page >= pages) or len(batch) < 100:
            return found
    raise RuntimeError('FEC filing list exceeded page limit: incomplete results')


def fields_for(line: str):
    # FEC 8.x uses ASCII 28 field separators; older electronic files can be CSV.
    return [part.strip().strip('"') for part in line.split('\x1c')] if '\x1c' in line else next(csv.reader([line]))


def parse_date(value):
    if not value:
        return None
    for fmt in ('%Y%m%d', '%m/%d/%Y', '%Y-%m-%d', '%m%d%Y', '%m/%d/%y'):
        try:
            return datetime.strptime(str(value).strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def cell(row, i):
    return row[i].strip() if len(row) > i else ''


def parse_f6(raw_bytes: bytes, committee_id: str, filing_id: int):
    """Read Form 6 header and all F65 itemizations (not processed Schedule A)."""
    rows = [fields_for(line) for line in raw_bytes.decode('utf-8-sig', errors='replace').split('\n') if line.strip()]
    covers = [r for r in rows if cell(r, 0).upper() in ('F6N', 'F6A', 'F6T', 'F6')]
    if not covers:
        raise ValueError(f'{filing_id}: no Form 6 cover record; refusing to publish')
    cover = covers[0]
    form_type = cell(cover, 0).upper()
    if cell(cover, 1).upper() != committee_id:
        raise ValueError(f'{filing_id}: Form 6 committee mismatch')
    original_amendment_date = parse_date(cell(cover, 2)) if form_type == 'F6A' else None
    contributions = []
    for r in rows:
        if cell(r, 0).upper() != 'F65':
            continue
        if cell(r, 1).upper() != committee_id:
            raise ValueError(f'{filing_id}: F65 committee mismatch')
        contributor = cell(r, 4) or ', '.join(p for p in
                 [cell(r, 5), ' '.join(p for p in (cell(r, 6), cell(r, 7)) if p)] if p)
        receipt_date = parse_date(cell(r, 16))
        if not receipt_date:
            raise ValueError(f'{filing_id}: bad contribution date {cell(r, 16)!r}')
        amount_text = cell(r, 17).replace(',', '').replace('$', '')
        try:
            amount = Decimal(amount_text)
            if not amount.is_finite():
                raise InvalidOperation()
        except InvalidOperation as exc:
            raise ValueError(f'{filing_id}: bad contribution amount {amount_text!r}') from exc
        contributions.append({'date': receipt_date,
                              'amount_cents': int((amount * 100).quantize(Decimal('1'))),
                              'contributor': contributor or 'Contributor not named',
                              'state': cell(r, 13), 'transaction_id': cell(r, 2)})
    if not contributions:
        raise ValueError(f'{filing_id}: no F65 records; check original notice manually')
    return {'form_type': form_type, 'original_amendment_date': original_amendment_date,
            'contributions': contributions}


def positive_int(value):
    try:
        n = int(value)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def load_cache():
    if CACHE_FILE.exists():
        data = json.loads(CACHE_FILE.read_text(encoding='utf-8'))
        if data.get('schema_version') != 1 or not isinstance(data.get('filings'), dict):
            raise RuntimeError('Unrecognized FEC archive cache version')
        return data
    return {'schema_version': 1, 'filings': {}}


def resolve_active_filings(filings):
    """Remove superseded notices via FEC amendment chains/cover-page date."""
    indexed = {int(f['file_number']): f for f in filings}
    superseded, warnings = set(), []
    for f in filings:
        if positive_int(f.get('amended_by')) in indexed:
            superseded.add(f['file_number'])
        chain = [n for n in (positive_int(x) for x in f.get('amendment_chain', [])) if n in indexed]
        if len(chain) > 1:
            prefer = positive_int(f.get('most_recent_filing'))
            newest = prefer if prefer in chain else max(chain, key=lambda n: (indexed[n].get('filed_date') or '', n))
            superseded.update(set(chain) - {newest})
    originals = defaultdict(list)
    for f in filings:
        if f.get('form_type') in ('F6N', 'F6'):
            originals[(f['committee_id'], f.get('filed_date'))].append(f)
    for f in filings:
        if f.get('form_type') != 'F6A' or not f.get('original_amendment_date'):
            continue
        matches = originals.get((f['committee_id'], f['original_amendment_date']), [])
        if len(matches) == 1:
            superseded.add(matches[0]['file_number'])
        elif len(matches) > 1:
            warnings.append(f"F6 amendment {f['file_number']} refers to a date with several original notices; review against FEC source")
    return [f for f in filings if f['file_number'] not in superseded], warnings


def build_public_data(cache, now=None):
    now = now or datetime.now(timezone.utc)
    active, warnings = resolve_active_filings(list(cache['filings'].values()))
    receipts, old_ids = {}, set()
    for f in sorted(active, key=lambda x: (x.get('filed_date') or '', x['file_number'])):
        cid, fn = f['committee_id'], int(f['file_number'])
        if cid not in [x['id'] for x in COMMITTEES.values()]:
            continue
        for c in f.get('contributions', []):
            if not START_DATE.isoformat() <= c['date'] <= END_DATE.isoformat():
                continue
            item = dict(c, committee_id=cid, file_number=fn)
            txid = c.get('transaction_id')
            if txid:
                # Same transaction number and contributor: newest notice is authoritative.
                key = (cid, txid, c['contributor'].casefold())
            else:
                # Missing identifiers: preserve both, rather than silently dropping receipts.
                key = (cid, fn, len(receipts))
            if key in receipts:
                old_ids.add((cid, txid))
            receipts[key] = item
    if old_ids:
        warnings.append(f'{len(old_ids)} F65 transaction(s) were repeated across active notices; counted newest only')
    contributions = sorted(receipts.values(), key=lambda x: (x['date'], x['committee_id'], x['contributor'], x['file_number']))
    used = {(r['committee_id'], r['file_number']) for r in contributions}
    reports = []
    for f in active:
        cid, fn = f['committee_id'], int(f['file_number'])
        if (cid, fn) in used:
            reports.append({'committee_id': cid, 'file_number': fn, 'filed_date': f.get('filed_date'),
                            'form_type': f.get('form_type'),
                            'url': f'https://docquery.fec.gov/cgi-bin/forms/{cid}/{fn}/f65'})
    reports.sort(key=lambda x: (x.get('filed_date') or '', x['file_number']))
    ny_today = now.astimezone(ZoneInfo('America/New_York')).date()
    display_end = min(END_DATE, max(START_DATE, ny_today))
    running = {c['id']: 0 for c in COMMITTEES.values()}
    daily = []
    current = START_DATE
    by_day = defaultdict(list)
    for r in contributions:
        by_day[r['date']].append(r)
    while current <= display_end:
        ds = current.isoformat()
        row = {'date': ds, 'totals': {}, 'cumulative': {}, 'counts': {}}
        for slug, c in COMMITTEES.items():
            subset = [r for r in by_day[ds] if r['committee_id'] == c['id']]
            total = sum(r['amount_cents'] for r in subset)
            running[c['id']] += total
            row['totals'][slug] = total
            row['cumulative'][slug] = running[c['id']]
            row['counts'][slug] = len(subset)
        daily.append(row)
        current += timedelta(days=1)
    return {'status': 'ok', 'generated_at': now.isoformat(timespec='seconds'),
            'period': {'from': START_DATE.isoformat(), 'through': END_DATE.isoformat()},
            'committee_info': COMMITTEES, 'daily': daily, 'filings': reports,
            'contributions': contributions, 'report_count': len(reports),
            'warnings': list(dict.fromkeys(warnings)),
            'method': 'FEC Form 6 F65 transactions. Grouped by contribution receipt date; may include loans or in-kind contributions.'}


def main():
    cache = load_cache()
    key = os.environ.get('FEC_API_KEY') or 'DEMO_KEY'
    discovered = {}
    for slug, committee in COMMITTEES.items():
        for r in discover_f6(committee['id'], key):
            file_num = positive_int(r.get('file_number'))
            if file_num:
                discovered[f"{committee['id']}/{file_num}"] = (committee['id'], file_num, r)
        for file_num in KNOWN_F6_FILINGS.get(slug, []):
            label = f"{committee['id']}/{file_num}"
            if label not in discovered and label not in cache['filings']:
                discovered[label] = (committee['id'], file_num, {'file_number': file_num})
    for label, (cid, file_num, meta) in sorted(discovered.items()):
        filing = cache['filings'].get(label)
        if filing is None:
            raw_url = str(meta.get('fec_url') or '')
            if not (raw_url.startswith('https://docquery.fec.gov/dcdev/posted/') and raw_url.endswith('.fec')):
                raw_url = f'https://docquery.fec.gov/dcdev/posted/{file_num}.fec'
            raw = fetch_url(raw_url, binary=True)
            filing = dict(parse_f6(raw, cid, file_num), file_number=file_num, committee_id=cid,
                          sha256=hashlib.sha256(raw).hexdigest())
            print(f"Validated raw Form 6 {label}: {len(filing['contributions'])} entries")
        for field in ('amendment_chain', 'amended_by', 'most_recent', 'most_recent_filing', 'is_amended'):
            if meta.get(field) is not None:
                filing[field] = meta[field]
        fd = parse_date(str(meta.get('filed_date') or meta.get('receipt_date') or '')[:10])
        if fd:
            filing['filed_date'] = fd
        cache['filings'][label] = filing
    public = build_public_data(cache)
    # Fail closed: only write after every API query, raw download, and parsing succeeded.
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    OUTPUT_FILE.write_text(json.dumps(public, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Archived {len(cache['filings'])} raw Form 6 filings; published {len(public['contributions'])} F65 contributions across {public['report_count']} notices")


if __name__ == '__main__':
    main()

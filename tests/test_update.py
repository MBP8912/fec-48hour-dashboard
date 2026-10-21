"""Offline tests (no network, no fabricated data in public JSON)."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from update_data import parse_f6, build_public_data, resolve_active_filings
CID = 'C00815415'
C2 = 'C00900431'


def f65(cid, txid='X123', donor='Person Example', dt='20261019', amount='3000.00',
        entity_type='IND', employer='Acme Inc', occupation='Engineer'):
    x = [''] * 22
    x[0], x[1], x[2], x[3], x[4], x[13], x[16], x[17] = 'F65', cid, txid, entity_type, donor, 'NY', dt, amount
    x[18], x[19] = employer, occupation
    return '\x1c'.join(x)


def sample(cid=CID, additional='', amendment=False):
    head = ['F6A' if amendment else 'F6N', cid, '20261019' if amendment else '', 'Committee']
    return ('HDR\x1cFEC\x1c8.2\n'+'\x1c'.join(head)+'\n'+f65(cid)+'\n'+additional).encode()


def filing(cid=CID, n=10, amend=False):
    return dict(parse_f6(sample(cid, amendment=amend), cid, n), committee_id=cid,
                file_number=n, filed_date='2026-10-20' if amend else '2026-10-19')


class TestF6(unittest.TestCase):
    def test_parses_date_and_amount(self):
        x = parse_f6(sample(), CID, 1)
        self.assertEqual(x['contributions'][0]['amount_cents'], 300000)
        self.assertEqual(x['contributions'][0]['date'], '2026-10-19')
    def test_discloses_individual_employer_and_occupation(self):
        parsed = parse_f6(sample(), CID, 1)
        item = parsed['contributions'][0]
        self.assertEqual(item['entity_type'], 'IND')
        self.assertEqual(item['employer'], 'Acme Inc')
        self.assertEqual(item['occupation'], 'Engineer')
        report = dict(parsed, committee_id=CID, file_number=1, filed_date='2026-10-20')
        displayed = build_public_data({'filings': {'1': report}},
                                      datetime(2026, 10, 21, tzinfo=timezone.utc))
        self.assertEqual(displayed['contributions'][0]['employer'], 'Acme Inc')
        self.assertEqual(displayed['contributions'][0]['occupation'], 'Engineer')
        self.assertEqual(displayed['daily'][-1]['cumulative']['lawler'], 300000)

    def test_empty_individual_fields_preserved_as_missing(self):
        doc = sample(additional=f65(CID, txid='X999', entity_type='IND',
                                     employer='', occupation=''))
        parsed = parse_f6(doc, CID, 1)
        self.assertEqual(parsed['contributions'][1]['employer'], '')
        self.assertEqual(parsed['contributions'][1]['occupation'], '')

    def test_organization_does_not_receive_individual_metadata(self):
        doc = sample(additional=f65(CID, txid='X999', donor='Another PAC',
                                     entity_type='PAC', employer='N/A', occupation='N/A'))
        parsed = parse_f6(doc, CID, 1)
        item = parsed['contributions'][1]
        self.assertEqual(item['entity_type'], 'PAC')
        self.assertEqual(item['employer'], '')
        self.assertEqual(item['occupation'], '')

    def test_wrong_committee_rejected(self):
        with self.assertRaises(ValueError):
            parse_f6(sample(), C2, 1)
    def test_amendment_replaces_original(self):
        orig, amend = filing(), filing(n=11, amend=True)
        amend.update(amendment_chain=[10, 11], most_recent_filing=11)
        active, warnings = resolve_active_filings([orig, amend])
        self.assertEqual([f['file_number'] for f in active], [11])
        self.assertFalse(warnings)
    def test_duplicate_transaction_counted_once(self):
        a, b, c = filing(n=9), filing(n=10), filing(cid=C2, n=11)
        data = build_public_data({'filings': {'a': a, 'b': b, 'c': c}}, datetime(2026,10,21,19,tzinfo=timezone.utc))
        self.assertEqual(len(data['contributions']), 2)
        row = next(r for r in data['daily'] if r['date'] == '2026-10-19')
        self.assertEqual(row['totals'], {'lawler': 300000, 'conley': 300000})
        self.assertTrue(any('repeated' in w for w in data['warnings']))
    def test_only_notice_window(self):
        doc = sample(additional=f65(CID, txid='X124', dt='20261010', amount='1000.00'))
        parsed = parse_f6(doc, CID, 12)
        f = dict(parsed, committee_id=CID, file_number=12, filed_date='2026-10-20')
        d = build_public_data({'filings': {'a': f}}, datetime(2026, 10, 21, tzinfo=timezone.utc))
        self.assertEqual(len(d['contributions']), 1)
    def test_legacy_comma(self):
        doc = ('HDR,FEC,8.2\nF6N,C00815415,,Committee\n'+f65(CID).replace('\x1c', ',')+'\n').encode()
        parsed = parse_f6(doc, CID, 1)
        self.assertEqual(parsed['contributions'][0]['amount_cents'], 300000)


if __name__ == '__main__':
    unittest.main()

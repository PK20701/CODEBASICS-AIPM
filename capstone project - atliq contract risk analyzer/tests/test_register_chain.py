"""The register building itself: sign S07 (Marina Bay), confirm its new restriction, then review S11 (Coral Bay, another hotel group in the UAE).
Uses the model for extraction. Usage: python tests/test_register_chain.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'api'))
for ln in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
    if '=' in ln and not ln.startswith('#'):
        k, v = ln.strip().split('=', 1)
        os.environ.setdefault(k, v)
import _core as core  # noqa: E402


def read(rel):
    with open(os.path.join(ROOT, 'public', 'samples', 'synthetic', rel), encoding='utf-8') as f:
        return f.read()


s07 = read('S07_marina_bay_resorts_msa.md')
s11 = read('S11_coral_bay_hotels_msa.md')
d07 = core.action_extract(s07)['details']
entries = core.action_register_entry(d07, s07, 'C-TEST-07')['entries']
print('extracted from S07:', [(e['type'], e['restricted_activity'], e['scope'], e['end']) for e in entries])
assert entries, 'no restriction extracted from S07'
nc = [e for e in entries if e['type'] in ('non_compete', 'exclusivity')]
assert nc, 'no non-compete found'
assert nc[0]['end'] == '2028-05-01', 'end date should be 12 months term + 6 months after, from 1 Nov 2026: %s' % nc[0]['end']


def conflicts(extra, exclude=None):
    d11 = core.action_extract(s11)['details']
    r = core.action_conflicts(d11, s11, extra, exclude)
    return {c['register_id']: c for c in r['conflicts']}, r['checked']


before, n0 = conflicts([])
pending = [dict(e) for e in nc]                       # still waiting for confirmation: must be ignored
ignored, _ = conflicts(pending)
confirmed = [dict(e, status='confirmed') for e in nc]
after, n1 = conflicts(confirmed)
excluded, _ = conflicts(confirmed, 'C-TEST-07')       # reviewing a new version of the same contract
ok = [e['id'] for e in nc]
print('before confirm :', sorted(before), 'checked', n0)
print('pending only   :', sorted(ignored))
print('after confirm  :', sorted(after), 'checked', n1)
print('same contract  :', sorted(excluded))
assert not any(i in before for i in ok), 'unconfirmed restriction leaked into a conflict check'
assert not any(i in ignored for i in ok), 'pending restriction was used'
assert any(i in after and after[i]['severity'] == 'Serious' for i in ok), 'confirmed restriction was not matched as Serious'
assert not any(i in excluded for i in ok), 'a contract collided with its own restriction'
assert n1 == n0 + len(nc)
print('REGISTER CHAIN OK')

"""Runs the full review pipeline on the synthetic contracts and scores it against tests/answer_key.json.
Usage: python tests/eval_synthetic.py [S01 S02 ...]     env FORCE_GEMINI_FAIL=1 tests the Groq fallback.
Results are saved to tests/results/<id>.json and a summary to tests/results/summary.json."""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'api'))
for ln in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
    if '=' in ln and not ln.startswith('#'):
        k, v = ln.strip().split('=', 1)
        os.environ.setdefault(k, v)
import _core as core  # noqa: E402

SEV = {'Serious': 0, 'Negotiable': 1, 'Minor': 2}
KEY = json.load(open(os.path.join(ROOT, 'tests', 'answer_key.json'), encoding='utf-8'))
RES = os.path.join(ROOT, 'tests', 'results')
os.makedirs(RES, exist_ok=True)


def read(rel):
    return open(os.path.join(ROOT, 'public', rel), encoding='utf-8').read()


def blob(f):
    return ' '.join(str(f.get(k) or '') for k in ('title', 'why', 'comparison', 'quote', 'topic')).lower()


def hit(f, m):
    if SEV.get(f['severity'], 3) > SEV[m['sev']]:
        return False
    if 'register' in m:
        return f.get('register_id') == m['register'] and (not m.get('status') or f.get('register_status') == m['status'])
    if 'source' in m and f['source'] != m['source']:
        return False
    if m.get('mentions'):
        return any(w in blob(f) for w in m['mentions'])
    if 'topic' in m:
        if f.get('topic') == m['topic']:
            return True
        return any(w in blob(f) for w in m.get('also', []))
    return True


def run(cid):
    k = KEY[cid]
    text = read(k['file'])
    notes = read(k['notes']) if k.get('notes') else ''
    r = core.run_review(text, notes, k.get('context') or None)
    F = r['findings']
    found, missed = [], []
    for m in k['must']:
        (found if any(hit(f, m) for f in F) else missed).append(m)
    sers = [f for f in F if f['severity'] == 'Serious']
    false_alarm = max(0, len(sers) - k['max_serious']) if k.get('no_serious') else 0
    unverified = [f['id'] for f in F if not f.get('quote') and not f.get('absence') and f['source'] != 'rule']
    provs = sorted({c.get('provider') for c in r['calls']})
    out = {'id': cid, 'label': k['label'], 'seconds': r['seconds'], 'findings': len(F), 'serious': len(sers), 'must': len(k['must']), 'found': len(found),
           'missed': missed, 'false_alarms': false_alarm, 'unverified': unverified, 'providers': provs, 'tokens_in': r['tokens_in'], 'tokens_out': r['tokens_out'],
           'clauses': '%d/%d' % (r['clauses_reviewed'], r['clauses_total']), 'liability': r['liability_text'], 'details': r['details'],
           'titles': [(f['severity'], f['source'], f['title']) for f in F]}
    json.dump(dict(out, all_findings=F), open(os.path.join(RES, cid + '.json'), 'w', encoding='utf-8'), indent=1, default=str)
    return out


if __name__ == '__main__':
    ids = sys.argv[1:] or sorted(KEY)
    summary = []
    for cid in ids:
        t = time.time()
        try:
            o = run(cid)
        except Exception as e:  # keep going so one failure does not hide the rest
            o = {'id': cid, 'error': '%s: %s' % (type(e).__name__, str(e)[:200])}
        summary.append(o)
        if 'error' in o:
            print(cid, 'ERROR', o['error'])
            continue
        print('%s %-48s %5.1fs found %d/%d  serious %d  false-alarm %d  unverified %d  clauses %s  %s  tokens %d/%d' % (
            cid, o['label'][:48], o['seconds'], o['found'], o['must'], o['serious'], o['false_alarms'], len(o['unverified']), o['clauses'], ','.join(o['providers']), o['tokens_in'], o['tokens_out']))
        for s, src, t_ in o['titles']:
            print('      [%s/%s] %s' % (s, src, t_[:100]))
        for m in o['missed']:
            print('      MISSED', m)
    json.dump(summary, open(os.path.join(RES, 'summary.json'), 'w', encoding='utf-8'), indent=1, default=str)
    ok = [s for s in summary if 'error' not in s]
    print('\nTOTAL must found %d/%d, false alarms %d, errors %d' % (sum(s['found'] for s in ok), sum(s['must'] for s in ok), sum(s['false_alarms'] for s in ok), len(summary) - len(ok)))

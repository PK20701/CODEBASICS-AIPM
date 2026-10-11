"""Runs the review against a deployed site through its /api/review endpoint, the same calls the browser makes.
Usage: python tests/live_check.py https://your-app.vercel.app S06 S02 S09 ..."""
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = sys.argv[1].rstrip('/')
KEY = json.load(open(os.path.join(ROOT, 'tests', 'answer_key.json'), encoding='utf-8'))
sys.path.insert(0, os.path.join(ROOT, 'tests'))


def api(body, tries=3):
    for i in range(tries):
        req = urllib.request.Request(BASE + '/api/review', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'live-check'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=70) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            if e.code == 429 and i < tries - 1:
                time.sleep(10)
                continue
            raise RuntimeError('HTTP %s %s' % (e.code, msg))


def fetch(rel):
    with urllib.request.urlopen(urllib.request.Request(BASE + '/' + rel, headers={'User-Agent': 'live-check'}), timeout=30) as r:
        return r.read().decode('utf-8')


def review(text, notes=''):
    t0 = time.time()
    ex = api({'action': 'extract', 'text': text})
    d = ex['details']
    seg = api({'action': 'segment', 'text': text})
    byid = {c['id']: c for c in seg['clauses']}
    rules = api({'action': 'rules', 'details': d, 'text': text})
    conf = api({'action': 'conflicts', 'details': d, 'text': text})
    nt = api({'action': 'notes', 'notes': notes, 'details': d, 'text': text}) if notes else {'items': []}
    an, reviewed, metas = [], set(), [ex['meta'], conf['meta']]
    for b in seg['batches']:
        r = api({'action': 'analyze', 'clauses': [byid[i] for i in b], 'details': d, 'text': text})
        an += r['findings']
        reviewed |= set(r['reviewed'])
        metas.append(r['meta'])
    m = api({'action': 'merge', 'rules': rules['findings'], 'conflicts': conf['conflicts'], 'notes': nt['items'], 'analysis': an})
    return m['findings'], len(reviewed), len(seg['clauses']), time.time() - t0, [x for x in metas if x]


if __name__ == '__main__':
    import eval_synthetic as E  # reuse the matcher (it imports the local engine only for helper functions)
    tot_ok = tot = 0
    for cid in sys.argv[2:]:
        k = KEY[cid]
        text = fetch(k['file'])
        notes = fetch(k['notes']) if k.get('notes') else ''
        F, rev, n, secs, metas = review(text, notes)
        found = [m for m in k['must'] if any(E.hit(f, m) for f in F)]
        sers = [f for f in F if f['severity'] == 'Serious']
        fa = max(0, len(sers) - k['max_serious']) if k.get('no_serious') else 0
        provs = sorted({m.get('provider') + ':' + m.get('model', '') for m in metas})
        print('%s %-46s %5.1fs  clauses %d/%d  found %d/%d  serious %d  false-alarm %d  %s' % (cid, k['label'][:46], secs, rev, n, len(found), len(k['must']), len(sers), fa, ', '.join(provs)))
        for f in F[:6]:
            print('      [%s/%s] %s' % (f['severity'], f['source'], f['title'][:90]))
        tot_ok += len(found)
        tot += len(k['must'])
    print('TOTAL expected findings found %d/%d' % (tot_ok, tot))

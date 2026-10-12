"""Recall on the gold set (expectations taken from the dataset's own documents) and the clean-control check.
Saves every run to tests/results/gold_runs/ so the precision sample can be drawn from the same findings.
Usage: python tests/eval_gold.py"""
import json
import os
import re
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
G = json.load(open(os.path.join(ROOT, 'tests', 'gold_set.json'), encoding='utf-8'))
OUT = os.path.join(ROOT, 'tests', 'results', 'gold_runs')
os.makedirs(OUT, exist_ok=True)
runs = {}
files = []
for grp in ('items', 'controls', 'quality'):
    for it in G[grp]:
        if it['file'] not in files:
            files.append(it['file'])
for rel in files:
    text = open(os.path.join(ROOT, 'public', 'samples', rel), encoding='utf-8').read()
    t0 = time.time()
    r = core.run_review(text)
    runs[rel] = r
    json.dump({'file': rel, 'details': r['details'], 'quality': r.get('quality'), 'findings': r['findings'], 'seconds': r['seconds']}, open(os.path.join(OUT, os.path.basename(rel).replace('.md', '.json')), 'w', encoding='utf-8'), indent=1, default=str)
    print('ran %-62s %5.1fs  %d findings' % (os.path.basename(rel)[:62], time.time() - t0, len(r['findings'])))


def blob(f):
    return ' '.join(str(f.get(k) or '') for k in ('title', 'why', 'comparison', 'quote')).lower()


def hit(f, it):
    if SEV.get(f['severity'], 3) > SEV[it['sev']]:
        return False
    if 'register' in it:
        return f.get('register_id') == it['register']
    if 'topic' in it and f.get('topic') != it['topic']:
        return False
    if 'any' in it:
        return any(re.search(x, blob(f)) for x in it['any'])
    return 'topic' in it


found = 0
print('\nGOLD SET (expectations from the dataset documents)')
for it in G['items']:
    F = runs[it['file']]['findings']
    ok = any(hit(f, it) for f in F)
    found += ok
    print('  %s %-4s %-62s [%s]' % ('FOUND ' if ok else 'MISSED', it['id'], it['label'][:62], it['source'][:46]))
print('\nRecall on the gold set: %d of %d (%.0f%%)' % (found, len(G['items']), 100.0 * found / len(G['items'])))
for it in G['controls']:
    sers = [f['title'] for f in runs[it['file']]['findings'] if f['severity'] == 'Serious']
    print('Control %s: %s (Serious findings: %d %s)' % (it['id'], it['label'], len(sers), sers))
for it in G['quality']:
    q = runs[it['file']].get('quality') or {}
    print('Quality %s: %s -> level=%s count=%s' % (it['id'], it['label'], q.get('level'), q.get('count')))

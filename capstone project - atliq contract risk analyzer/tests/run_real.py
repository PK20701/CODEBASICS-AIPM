"""Runs the review on the real incoming drafts (and optionally signed ones) and prints findings, timing and tokens.
Usage: python -u tests/run_real.py [substring ...]    env FORCE_GEMINI_FAIL=1 forces the Groq fallback."""
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

inc = os.path.join(ROOT, 'public', 'samples', 'incoming')
want = sys.argv[1:]
files = [f for f in sorted(os.listdir(inc)) if not want or any(w in f for w in want)]
out_dir = os.path.join(ROOT, 'tests', 'results', 'real')
os.makedirs(out_dir, exist_ok=True)
tot = {'s': 0, 'in': 0, 'out': 0}
for fn in files:
    text = open(os.path.join(inc, fn), encoding='utf-8').read()
    t0 = time.time()
    try:
        r = core.run_review(text)
    except Exception as e:
        print('%-60s ERROR %s' % (fn[:60], str(e)[:160]))
        continue
    F = r['findings']
    provs = sorted({c.get('provider') for c in r['calls']})
    sev = {s: sum(1 for f in F if f['severity'] == s) for s in ('Serious', 'Negotiable', 'Minor')}
    bad = [f['id'] for f in F if not f.get('quote') and not f.get('absence') and f['source'] != 'rule']
    print('\n%s\n  %5.1fs  clauses %d/%d  S/N/M %d/%d/%d  unverified %d  %s  tokens %d/%d' % (fn, r['seconds'], r['clauses_reviewed'], r['clauses_total'], sev['Serious'], sev['Negotiable'], sev['Minor'], len(bad), ','.join(provs), r['tokens_in'], r['tokens_out']))
    for f in F:
        print('    [%s/%s] %s' % (f['severity'], f['source'], (f['title'] or '')[:95]))
    json.dump(dict(r, all_findings=F), open(os.path.join(out_dir, fn.replace('.md', '.json')), 'w', encoding='utf-8'), indent=1, default=str)
    tot['s'] += r['seconds']
    tot['in'] += r['tokens_in']
    tot['out'] += r['tokens_out']
print('\nTOTAL %d files, %.0fs, tokens in %d out %d, avg per contract in %d out %d' % (len(files), tot['s'], tot['in'], tot['out'], tot['in'] / max(len(files), 1), tot['out'] / max(len(files), 1)))

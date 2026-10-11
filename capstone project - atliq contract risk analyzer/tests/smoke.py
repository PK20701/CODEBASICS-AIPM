import json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'api'))
for ln in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
    if '=' in ln:
        k, v = ln.strip().split('=', 1)
        os.environ.setdefault(k, v)
import _core as core

name = sys.argv[1] if len(sys.argv) > 1 else 'incoming/2026-09-19_lakeshore_grocers_msa_draft.md'
text = open(os.path.join(ROOT, 'public', 'samples', name), encoding='utf-8').read()
cl = core.segment(text)
print('clauses', len(cl), 'batches', len(core.make_batches(cl)), 'chars', len(text))
t0 = time.time()
ex = core.action_extract(text)
print('extract %.1fs' % (time.time() - t0), ex['meta'])
print(json.dumps(ex['details'], indent=1)[:3500])

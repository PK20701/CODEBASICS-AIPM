import json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'api'))
for ln in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
    if '=' in ln:
        k, v = ln.strip().split('=', 1)
        os.environ.setdefault(k, v)
import _core as core

text = open(os.path.join(ROOT, 'public', 'samples', 'incoming/2026-09-19_lakeshore_grocers_msa_draft.md'), encoding='utf-8').read()
cl = core.segment(text)
batches = core.make_batches(cl)
details = {'atliq_entity': 'Inc', 'counterparty': 'Lakeshore Grocers', 'doc_type': 'MSA', 'total_value': 64000, 'term_months': 24, 'governing_law': 'Illinois', 'payment_days': 30, 'currency': 'USD'}
b = batches[2] if len(batches) > 2 else batches[0]
models = sys.argv[1:] or ['gemini-flash-lite-latest', 'gemini-3.5-flash-lite', 'gemini-3.8-flash', 'gemini-flash-latest', 'gemini-3.5-flash']
os.environ.pop('FORCE_GEMINI_FAIL', None)
for m in models:
    os.environ['GEMINI_MODEL_SMART'] = m
    t0 = time.time()
    try:
        r = core.action_analyze(b, details, text)
        meta = r['meta']
        print('%-26s %5.1fs  provider=%s findings=%d verified=%d in=%s out=%s' % (m, time.time() - t0, meta['provider'], len(r['findings']), sum(1 for f in r['findings'] if f['verified']), meta['in'], meta['out']))
    except Exception as e:
        print('%-26s ERROR %s' % (m, str(e)[:120]))

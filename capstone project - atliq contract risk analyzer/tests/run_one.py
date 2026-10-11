import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'api'))
for ln in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
    if '=' in ln:
        k, v = ln.strip().split('=', 1)
        os.environ.setdefault(k, v)
import _core as core


def load(path):
    p = os.path.join(ROOT, 'public', 'samples', path)
    return open(p, encoding='utf-8').read()


def show(res, maxq=110):
    d = res['details']
    print('== %s | %s | %s | entity %s | law %s | courts %s' % (d.get('counterparty'), d.get('doc_type'), d.get('client_country'), d.get('atliq_entity'), d.get('governing_law'), d.get('courts_or_seat')))
    print('clauses %s reviewed %s | findings %d | liability %s | %.1fs | tokens in/out %s/%s | providers %s' % (
        res['clauses_total'], res['clauses_reviewed'], len(res['findings']), res['liability_text'], res['seconds'], res['tokens_in'], res['tokens_out'],
        sorted({c.get('provider') + ('*' if c.get('fallback') else '') for c in res['calls']})))
    for f in res['findings']:
        q = (f.get('quote') or '')[:maxq].replace('\n', ' ')
        print(' [%s] %-10s %-9s cl %-6s %s | %s%s' % (f['id'], f['severity'], f['source'], f.get('clause_id'), f['title'], 'Q:' + q if q else 'no quote', '' if f.get('verified') else '  (UNVERIFIED)'))


if __name__ == '__main__':
    path = sys.argv[1]
    notes = open(os.path.join(ROOT, 'public', 'samples', sys.argv[2]), encoding='utf-8').read() if len(sys.argv) > 2 else ''
    show(core.run_review(load(path), notes))

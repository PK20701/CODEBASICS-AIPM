"""How well does the tool's own extractor rebuild the register from the 17 signed contracts?
Compares what action_register_entry finds with the hand-built register (data/register.json).
Usage: python tests/eval_register_extraction.py"""
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

signed = os.path.join(ROOT, 'public', 'samples', 'signed')
hand = core.register()
by_file = {}
for r in hand:
    by_file.setdefault(os.path.basename(r['file']), []).append(r)

found, missed, extra, rows = 0, [], [], []
for fn in sorted(os.listdir(signed)):
    if not fn.endswith('.md'):
        continue
    text = open(os.path.join(signed, fn), encoding='utf-8').read()
    t0 = time.time()
    try:
        det = core.action_extract(text)['details']
        ents = core.action_register_entry(det, text, fn[:10])['entries']
    except Exception as e:
        print('%-62s ERROR %s' % (fn, str(e)[:80]))
        rows.append({'file': fn, 'error': str(e)[:120]})
        continue
    want = by_file.get(fn, [])
    got_types = [e['type'] for e in ents]
    hit = []
    for w in want:
        # a hand-built entry is "found" if the extractor produced an entry of the same type for that file
        m = [e for e in ents if e['type'] == w['type']]
        if m:
            hit.append(w['id'])
            found += 1
        else:
            missed.append((w['id'], fn, w['type']))
    used = {w['type'] for w in want}
    for e in ents:
        if e['type'] not in used and e['type'] != 'other':
            extra.append((fn, e['type'], (e['restricted_activity'] or '')[:70], e.get('verified')))
    unverified = sum(1 for e in ents if not e.get('verified'))
    rows.append({'file': fn, 'hand': [w['id'] + ':' + w['type'] for w in want], 'extracted': got_types, 'unverified_quotes': unverified, 's': round(time.time() - t0, 1)})
    print('%-62s hand %-28s extracted %-45s unverified %d' % (fn[:62], ','.join(w['id'] for w in want) or '-', ','.join(got_types) or '-', unverified))

total = len(hand)
print('\nHand-built register entries: %d. Found by the extractor (same file, same type): %d (%.0f%%). Missed: %d' % (total, found, 100.0 * found / total, len(missed)))
for m in missed:
    print('  MISSED', m)
print('Extra covenants found that are not in the hand-built register (type not present for that file): %d' % len(extra))
for e in extra:
    print('  EXTRA', e)
json.dump({'hand_total': total, 'found': found, 'missed': missed, 'extra': extra, 'rows': rows}, open(os.path.join(ROOT, 'tests', 'results', 'register_extraction.json'), 'w', encoding='utf-8'), indent=1, default=str)

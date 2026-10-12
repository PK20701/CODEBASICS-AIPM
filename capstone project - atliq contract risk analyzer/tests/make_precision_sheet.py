"""Writes tests/results/precision_review.md: every Serious finding from the 15 real drafts with the PM's label (from tests/precision_labels.json).
Findings the PM has not yet judged show as 'to label'. Karandeep should confirm or change the labels.
Usage: python tests/make_precision_sheet.py   (run tests/eval_gold.py first)"""
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = json.load(open(os.path.join(ROOT, 'tests', 'precision_labels.json'), encoding='utf-8'))


def key(name, x):
    q = re.sub(r'\W+', ' ', (x.get('quote') or x['title'])).strip().lower()[:60]
    return '%s|%s|%s' % (name, x['source'], q)


rows = []
for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'results', 'gold_runs', '*.json'))):
    r = json.load(open(f, encoding='utf-8'))
    name = os.path.basename(f)[11:-5]
    for x in r['findings']:
        if x['severity'] == 'Serious':
            rows.append((name, x['source'], x['title'], (x.get('quote') or '(none: based on what is missing)')[:160], key(name, x)))
out = ['# Precision check: Serious findings on the 15 real drafts', '',
       'Labels by the PM, read against AtliQ\'s checklist. **Karandeep to confirm or change.** Labels: **valid** (a real risk worth a Serious flag), **routine** (a real clause, but common or a duplicate; Negotiable would do), **wrong** (misread or wrong direction), **to label** (new since the last judging).', '',
       '| # | Draft | Source | Finding | Quote | Label | Note |', '|---|---|---|---|---|---|---|']
cnt = {'valid': 0, 'routine': 0, 'wrong': 0, 'to label': 0}
for i, (n, s, t, q, k) in enumerate(rows, 1):
    l = LAB.get(k)
    lab, note = (l['label'], l['note']) if l else ('to label', '')
    cnt[lab] = cnt.get(lab, 0) + 1
    out.append('| %d | %s | %s | %s | %s | %s | %s |' % (i, n, s, t.replace('|', '/'), q.replace('|', '/').replace('\n', ' '), lab, note))
total = len(rows)
out += ['', '## Result', '', 'Serious findings: %d. Valid: %d (%.0f%%). Real but routine or duplicate: %d. Wrong direction: %d. Still to label: %d.' % (total, cnt['valid'], 100.0 * cnt['valid'] / total, cnt['routine'], cnt['wrong'], cnt['to label']),
        'Pointing at a real clause (valid plus routine): %d (%.0f%%). The PRD threshold is at least 60%% valid; the client prefers over-flagging to missing.' % (cnt['valid'] + cnt['routine'], 100.0 * (cnt['valid'] + cnt['routine']) / total),
        '', 'Caveat: the labels were set by the person who built the tool. They show where it over-flags; they are not an independent measurement.']
open(os.path.join(ROOT, 'tests', 'results', 'precision_review.md'), 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[-6:]))
if cnt['to label']:
    print('\nTO LABEL:')
    for n, s, t, q, k in rows:
        if k not in LAB:
            print(' -', n, '|', t, '|', q[:120])

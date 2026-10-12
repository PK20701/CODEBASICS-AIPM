"""Builds public/data/lexicon.json: the words that appear at least twice in the clean dataset contracts (not the scanned file).
The scan-quality check uses it to spot OCR misreads such as AGREERNENT or 0RBIT. Run: python tools/make_lexicon.py"""
import collections
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, 'public', 'samples')
cnt = collections.Counter()
used = 0
for folder in ('signed', 'incoming', 'synthetic'):
    for fn in sorted(os.listdir(os.path.join(S, folder))):
        if not fn.endswith('.md') or 'scanned' in fn:
            continue
        with open(os.path.join(S, folder, fn), encoding='utf-8') as f:
            text = f.read().lower()
        cnt.update(re.findall(r'[a-z]{4,}', text))
        used += 1
words = sorted(w for w, c in cnt.items() if c >= 2)
with open(os.path.join(ROOT, 'public', 'data', 'lexicon.json'), 'w', encoding='utf-8') as f:
    json.dump(words, f, separators=(',', ':'))
print('lexicon: %d words from %d files' % (len(words), used))

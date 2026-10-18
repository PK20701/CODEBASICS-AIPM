"""The stored results for the built-in sample contracts (public/data/precomputed.json) must cover every sample and be complete.
Offline: no model call. Run: python tests/test_precomputed.py"""
import hashlib
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'public')
PRE = json.load(open(os.path.join(PUB, 'data', 'precomputed.json'), encoding='utf-8'))
SAMPLES = json.load(open(os.path.join(PUB, 'data', 'samples.json'), encoding='utf-8'))


def key(path):
    """Same as the page: the text as a textarea holds it (LF line ends), trimmed, SHA-256, first 8 bytes in hex."""
    t = open(os.path.join(PUB, path), encoding='utf-8', newline='').read().replace('\r\n', '\n').strip()
    return hashlib.sha256(t.encode('utf-8')).hexdigest()[:16]


class Precomputed(unittest.TestCase):
    def test_every_sample_has_its_extraction(self):
        missing = [s['label'] for s in SAMPLES if 'ex' + key(s['file']) not in PRE]
        self.assertEqual(missing, [])

    def test_extractions_have_details(self):
        for k, v in PRE.items():
            if k.startswith('ex'):
                self.assertTrue(v.get('details') and v.get('clauses'), k)

    def test_reviews_are_complete_and_without_warnings(self):
        rv = {k: v for k, v in PRE.items() if k.startswith('rv')}
        self.assertEqual(len(rv), len([s for s in SAMPLES if not s.get('kind')]))
        for k, v in rv.items():
            self.assertEqual(v['clauses_reviewed'], v['clauses_total'], k)
            self.assertFalse(v.get('could_not'), k)
            self.assertFalse(v.get('warnings'), k)
            self.assertTrue(all(f.get('severity') in ('Serious', 'Negotiable', 'Minor') for f in v['findings']), k)


if __name__ == '__main__':
    unittest.main()

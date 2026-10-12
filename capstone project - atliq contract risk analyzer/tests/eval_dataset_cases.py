"""Brief's seven test cases, run on the actual dataset files (not my synthetic ones). Prints what the tool says so a person can judge.
Usage: python tests/eval_dataset_cases.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'api'))
for ln in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
    if '=' in ln and not ln.startswith('#'):
        k, v = ln.strip().split('=', 1)
        os.environ.setdefault(k, v)
import _core as core  # noqa: E402

S = os.path.join(ROOT, 'public', 'samples')
CASES = [
    ('1 collides with something already signed', 'incoming/2026-09-18_gulf_crown_hotels_msa_draft.md', 'Al Noor non-compete (Serious)'),
    ('1b collides on price', 'incoming/2026-09-19_lakeshore_grocers_msa_draft.md', 'Crestline most-favoured pricing ($72 vs card)'),
    ('2 buried one-sided clause / what Brightwater signed', 'signed/2025-11-28_brightwater_insurance_msa.md', 'uncapped LD and English law on a US entity'),
    ('3 wrong law / entity', 'incoming/2026-09-15_travelhub_services_agreement_draft.md', 'entity and law mismatch'),
    ('4 NDA that says mutual', 'incoming/2026-09-25_finserve_capital_mutual_nda_draft.md', 'non-compete and non-solicit inside a mutual NDA'),
    ('5 AtliQ own paper (agency)', 'incoming/2026-09-26_kriti_data_labs_subcontractor_agreement_draft.md', 'clauses AtliQ rejects as a supplier, unfair to the other side'),
    ('5b AtliQ own paper (freelancer)', 'incoming/2026-09-27_marcus_reed_contractor_agreement_draft.md', 'same'),
    ('6 healthcare, document missing', 'incoming/2026-09-10_harrington_health_msa_draft.md', 'BAA / insurance gap'),
    ('6b healthcare freelancer', 'incoming/2026-09-27_daniel_ortiz_contractor_agreement_draft.md', 'PHI without BAA flow-down'),
    ('7 only looks risky', 'incoming/2026-09-27_loopmart_mutual_nda_draft.md', 'no Serious finding'),
    ('8 scanned copy', 'signed/2022-07-01_orbit_travels_msa_scanned.md', 'poor scan: should be flagged low confidence'),
]
for name, rel, expect in CASES:
    text = open(os.path.join(S, rel), encoding='utf-8').read()
    r = core.run_review(text)
    F = r['findings']
    sev = [sum(1 for f in F if f['severity'] == x) for x in ('Serious', 'Negotiable', 'Minor')]
    print('\n### %s  [%s]\n    expect: %s | S/N/M %s | clauses %d/%d | %.0fs' % (name, os.path.basename(rel)[:40], expect, '/'.join(map(str, sev)), r['clauses_reviewed'], r['clauses_total'], r['seconds']))
    for f in F[:7]:
        print('    [%s/%s] %s' % (f['severity'], f['source'], f['title'][:92]))

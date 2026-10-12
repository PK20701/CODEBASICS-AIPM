"""Offline unit tests: no model, no network. Run: python tests/test_units.py"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'api'))
import _core as core  # noqa: E402
import review  # noqa: E402

SAMPLES = os.path.join(ROOT, 'public', 'samples')


def read(rel):
    return open(os.path.join(SAMPLES, rel), encoding='utf-8').read()


class Quotes(unittest.TestCase):
    def test_exact_quote_verifies(self):
        self.assertTrue(core.verify_quote('shall pay each undisputed invoice within thirty (30) days', 'Orion shall pay each undisputed invoice within thirty (30) days of receipt.'))

    def test_markdown_and_whitespace_ignored(self):
        self.assertTrue(core.verify_quote('the **Recipient**   shall hold', 'The "**Recipient**" shall hold the information'))

    def test_invented_quote_rejected(self):
        self.assertFalse(core.verify_quote('Vendor shall pay unlimited damages', 'Each party\'s liability is capped at fees paid.'))

    def test_empty_quote_rejected(self):
        self.assertFalse(core.verify_quote('', 'anything'))

    def test_ellipsis_pieces_each_checked(self):
        t = 'Alpha beta gamma delta. Epsilon zeta eta theta.'
        self.assertTrue(core.verify_quote('Alpha beta ... Epsilon zeta', t))
        self.assertFalse(core.verify_quote('Alpha beta ... made up words', t))


class Liability(unittest.TestCase):
    def d(self, kind, **kw):
        return {'liability_cap': dict(kind=kind, **kw), 'annual_fee': 24000, 'total_value': 24000, 'term_months': 12}

    def test_one_x_is_fine(self):
        self.assertIsNone(core.liability_ratio(self.d('multiple_of_fees', multiple=1))[2])

    def test_two_x_minor(self):
        self.assertEqual(core.liability_ratio(self.d('multiple_of_fees', multiple=2))[2], 'Minor')

    def test_three_x_negotiable(self):
        self.assertEqual(core.liability_ratio(self.d('multiple_of_fees', multiple=3))[2], 'Negotiable')

    def test_five_x_serious(self):
        self.assertEqual(core.liability_ratio(self.d('multiple_of_fees', multiple=5))[2], 'Serious')

    def test_fixed_amount_ratio(self):
        mult, txt, sev = core.liability_ratio(self.d('fixed_amount', amount=500000))
        self.assertAlmostEqual(mult, 20.83, 1)
        self.assertEqual(sev, 'Serious')

    def test_unlimited_is_serious(self):
        self.assertEqual(core.liability_ratio(self.d('unlimited'))[2], 'Serious')

    def test_annual_fee_derived_from_total_and_term(self):
        self.assertEqual(core.annual_fee_of({'total_value': 270000, 'term_months': 18}), 180000)


class Dates(unittest.TestCase):
    def test_term_plus_months(self):
        d = {'effective_date': '2026-11-01', 'term_months': 12}
        self.assertEqual(core.compute_end(d, {'duration_basis': 'term_plus_months', 'months_after_term': 6}), '2028-04-30')

    def test_term_only(self):
        self.assertEqual(core.compute_end({'effective_date': '2025-03-15', 'term_months': 36}, {'duration_basis': 'term'}), '2028-03-14')

    def test_al_noor_convention(self):
        # term to 14 Mar 2028 plus 18 months, as in the register: 14 Sep 2029
        self.assertEqual(core.compute_end({'effective_date': '2025-03-15', 'term_months': 36}, {'duration_basis': 'term_plus_months', 'months_after_term': 18}), '2029-09-14')

    def test_month_end_clamping(self):
        self.assertEqual(core.compute_end({'effective_date': '2026-01-31', 'term_months': 1}, {'duration_basis': 'term'}), '2026-02-28')
        self.assertEqual(core.compute_end({'effective_date': '2024-02-29', 'term_months': 12}, {'duration_basis': 'term'}), '2025-02-28')

    def test_perpetual_has_no_end(self):
        self.assertIsNone(core.compute_end({'effective_date': '2025-03-15', 'term_months': 36}, {'duration_basis': 'perpetual'}))

    def test_missing_start_gives_none(self):
        self.assertIsNone(core.compute_end({'term_months': 12}, {'duration_basis': 'term'}))

    def test_register_status_expiry(self):
        self.assertEqual(core.reg_status({'end': '2025-06-30'}, '2026-10-11'), 'expired')
        self.assertEqual(core.reg_status({'end': '2029-09-14'}, '2026-10-11'), 'active')
        self.assertEqual(core.reg_status({'end': None}, '2026-10-11'), 'active')


class EntityAndLaw(unittest.TestCase):
    def rules(self, **d):
        return core.rules_findings(d, 'This Agreement is governed by the laws stated. ' * 3)

    def topics(self, f, t='governing_law'):
        return [x for x in f if x['topic'] == t]

    def test_us_entity_us_law_ok(self):
        self.assertFalse(self.topics(self.rules(atliq_entity='Inc', governing_law='State of Texas', client_country='United States')))

    def test_us_entity_singapore_law_serious(self):
        f = self.topics(self.rules(atliq_entity='Inc', governing_law='Singapore', client_country='United States'))
        self.assertEqual(f[0]['severity'], 'Serious')

    def test_us_county_courts_are_not_foreign(self):
        self.assertFalse(self.topics(self.rules(atliq_entity='Inc', governing_law='State of Florida', courts_or_seat='courts of Miami-Dade County', client_country='United States')))

    def test_us_entity_london_arbitration_serious(self):
        f = self.topics(self.rules(atliq_entity='Inc', governing_law='State of New York', courts_or_seat='London arbitration (LCIA)', client_country='United States'))
        self.assertEqual(f[0]['severity'], 'Serious')

    def test_pvt_ltd_for_us_client_serious(self):
        f = self.topics(self.rules(atliq_entity='Pvt Ltd', governing_law='India', client_country='United States'))
        self.assertEqual(f[0]['severity'], 'Serious')

    def test_inc_for_non_us_client_serious(self):
        f = self.topics(self.rules(atliq_entity='Inc', governing_law='State of Delaware', client_country='United Arab Emirates'))
        self.assertEqual(f[0]['severity'], 'Serious')

    def test_illinois_is_us(self):
        self.assertTrue(core.is_us('Illinois'))
        self.assertFalse(core.is_us('Singapore'))


class RequiredDocsAndAmounts(unittest.TestCase):
    def rules(self, text='plain text. ' * 10, **d):
        return core.rules_findings(d, text)

    def test_phi_without_baa_serious(self):
        f = self.rules(handles_phi=True, mentions_baa_or_dpa=False)
        self.assertTrue(any(x['topic'] == 'data_protection' and x['severity'] == 'Serious' for x in f))

    def test_phi_with_baa_clean(self):
        self.assertFalse(self.rules(handles_phi=True, mentions_baa_or_dpa=True))

    def test_cyber_insurance_over_one_million(self):
        f = self.rules(insurance_requirements=[{'type': 'Cyber liability', 'amount_usd': 5000000}])
        self.assertTrue(any(x['topic'] == 'insurance' for x in f))

    def test_cyber_insurance_at_one_million_ok(self):
        self.assertFalse(self.rules(insurance_requirements=[{'type': 'Cyber liability', 'amount_usd': 1000000}]))

    def test_payment_60_days_negotiable_100_serious(self):
        a = [x for x in self.rules(payment_days=60) if x['topic'] == 'payment']
        b = [x for x in self.rules(payment_days=100) if x['topic'] == 'payment']
        self.assertEqual((a[0]['severity'], b[0]['severity']), ('Negotiable', 'Serious'))

    def test_payment_45_days_ok(self):
        self.assertFalse([x for x in self.rules(payment_days=45) if x['topic'] == 'payment'])

    def test_uncapped_delay_penalty_serious(self):
        f = self.rules(delay_penalty={'present': True, 'capped': False, 'excludes_client_delay': True})
        self.assertEqual([x for x in f if x['topic'] == 'delay_penalty'][0]['severity'], 'Serious')

    def test_nda_with_no_cap_is_not_flagged(self):
        f = self.rules(doc_type='NDA', liability_cap={'kind': 'none_stated'})
        self.assertFalse([x for x in f if x['topic'] == 'liability'])


class Segmentation(unittest.TestCase):
    def test_numbered_clauses_split(self):
        t = '# T\n\n## 1. SERVICES\n\n1.1 First clause here that is long enough to count.\n1.2 Second clause here that is long enough to count.\n\n## 2. TERM\n\n2.1 Third clause.\n2.2 Fourth clause.\n\n## 3. FEES\n\n3.1 Fifth clause.'
        ids = [c['id'] for c in core.segment(t)]
        self.assertIn('1.1', ids)
        self.assertIn('2.1', ids)

    def test_every_sample_segments_and_batches_cover_all_clauses(self):
        for folder in ('incoming', 'signed', 'synthetic'):
            for fn in sorted(os.listdir(os.path.join(SAMPLES, folder))):
                if not fn.endswith('.md') or 'notes' in fn or 'chat' in fn:
                    continue
                cl = core.segment(read(folder + '/' + fn))
                self.assertGreater(len(cl), 2, fn)
                batches = core.make_batches(cl)
                self.assertEqual(sum(len(b) for b in batches), len(cl), fn)
                for b in batches:
                    self.assertLessEqual(len(b), 16, fn)

    def test_unnumbered_paragraph_under_a_heading_is_kept_not_dropped(self):
        t = ('## 1. SERVICES\n\n1.1 Vendor shall provide analytics services to the client under this agreement.\n1.2 Fees are payable monthly in arrears.\n\n'
             '## 2. TERM\n\n2.1 Twelve months from the effective date of this agreement.\n2.2 Renews annually unless notice is given.\n\n'
             '## 3. MISC\n\nThis paragraph has no clause number but it is part of the agreement and must be reviewed.\n3.1 Entire agreement clause.\n')
        ids = [c['id'] for c in core.segment(t)]
        self.assertIn('3.p1', ids)

    def test_empty_text_does_not_crash(self):
        self.assertEqual(core.segment(''), [])

    def test_huge_text_segments(self):
        t = '\n\n'.join('%d.%d Clause number %d.%d says something about payment terms.' % (i, j, i, j) for i in range(1, 40) for j in range(1, 11))
        self.assertGreaterEqual(len(core.segment(t)), 380)


class Register(unittest.TestCase):
    def test_every_register_quote_is_in_its_source(self):
        for r in core.register():
            self.assertTrue(core.verify_quote(r['quote'], read(r['file'].replace('samples/', ''))), r['id'])

    def test_expired_restrictions_kept(self):
        self.assertTrue(any(core.reg_status(r) == 'expired' for r in core.register()))

    def test_hospitality_gcc_deal_matches_al_noor_strongly(self):
        d = {'client_country': 'United Arab Emirates', 'regions_of_service': ['UAE'], 'services_summary': 'revenue management for hotels', 'client_industry': 'hospitality'}
        m = {k['register_id']: k for k in core.keyword_conflicts(d, 'resort hotel revenue management services in Dubai')}
        self.assertEqual(m['R-01']['relevance'], 'likely')

    def test_travel_app_in_the_gulf_is_only_possible(self):
        d = {'client_country': 'United Arab Emirates', 'regions_of_service': ['UAE'], 'services_summary': 'hotel ranking module for a travel app', 'client_industry': 'travel'}
        m = {k['register_id']: k for k in core.keyword_conflicts(d, 'partner hotel ranking for a consumer travel app in Dubai')}
        self.assertEqual(m['R-01']['relevance'], 'possible')

    def test_food_company_in_iowa_does_not_match_al_noor(self):
        d = {'client_country': 'United States', 'regions_of_service': [], 'services_summary': 'demand forecasting', 'client_industry': 'hospitality'}
        m = {k['register_id'] for k in core.keyword_conflicts(d, 'Fieldstone Foods demand forecasting services')}
        self.assertNotIn('R-01', m)

    def test_low_hourly_rate_triggers_crestline_mfn(self):
        d = {'client_country': 'United States', 'rates': [{'role': 'Senior Data Engineer', 'rate': 70, 'unit': 'hour'}]}
        m = {k['register_id'] for k in core.keyword_conflicts(d, 'rates')}
        self.assertIn('R-02', m)

    def test_rate_above_card_does_not_trigger(self):
        d = {'client_country': 'United States', 'rates': [{'role': 'Senior Data Engineer', 'rate': 90, 'unit': 'hour'}]}
        self.assertNotIn('R-02', {k['register_id'] for k in core.keyword_conflicts(d, 'rates')})


class ConfirmedRegister(unittest.TestCase):
    ENTRY = {'id': 'N-C-N02-1', 'contract_id': 'C-N02', 'counterparty': 'Marina Bay Resorts LLC', 'type': 'non_compete', 'clause': '3.1',
             'restricted_activity': 'provide revenue-management services to any other hotel group', 'status': 'confirmed', 'end': '2028-05-01',
             'scope': {'customers': 'any other hotel group', 'geography': ['United Arab Emirates']}, 'quote': 'Vendor shall not provide revenue-management services'}
    HOTEL = {'client_country': 'United Arab Emirates', 'regions_of_service': ['UAE'], 'services_summary': 'revenue management analytics for hotels'}

    def ids(self, details, text, extra, exclude=None):
        reg = core.register() + core.sanitize_extra(extra, exclude)
        return {k['register_id']: k['relevance'] for k in core.keyword_conflicts(details, text, reg)}

    def test_confirmed_entry_matches_a_similar_new_deal(self):
        m = self.ids(self.HOTEL, 'Coral Bay hotels in Abu Dhabi: revenue management analytics', [self.ENTRY])
        self.assertEqual(m.get('N-C-N02-1'), 'likely')

    def test_same_contract_is_excluded(self):
        self.assertNotIn('N-C-N02-1', self.ids(self.HOTEL, 'hotel revenue management in Abu Dhabi', [self.ENTRY], exclude='C-N02'))

    def test_pending_and_rejected_entries_are_ignored(self):
        for st in ('pending_confirmation', 'rejected'):
            e = dict(self.ENTRY, status=st)
            self.assertNotIn('N-C-N02-1', self.ids(self.HOTEL, 'hotel revenue management in Abu Dhabi', [e]))

    def test_unrelated_deal_does_not_match(self):
        food = {'client_country': 'United States', 'regions_of_service': [], 'services_summary': 'demand forecasting for a food company'}
        self.assertNotIn('N-C-N02-1', self.ids(food, 'Fieldstone Foods demand forecasting services in Iowa', [self.ENTRY]))

    def test_missing_geography_means_worldwide(self):
        e = dict(self.ENTRY, scope={'customers': 'any other hotel group', 'geography': []})
        self.assertEqual(core.sanitize_extra([e])[0]['scope']['geography'], ['Worldwide'])

    def test_bad_input_is_dropped(self):
        junk = ['x', None, {'id': ''}, dict(self.ENTRY, end='not a date'), dict(self.ENTRY, id='N-2', type='weird')]
        out = core.sanitize_extra(junk)
        self.assertEqual(len(out), 2)
        self.assertIsNone(out[0]['end'])
        self.assertEqual(out[1]['type'], 'other')

    def test_takeaway_text_names_who_what_where_until(self):
        t = core.make_takeaway('Marina Bay', '3.1', 'provide revenue-management services', 'any other hotel group', ['UAE'], '2028-05-01')
        self.assertIn('Marina Bay', t)
        self.assertIn('UAE', t)
        self.assertIn('2028-05-01', t)


class Merge(unittest.TestCase):
    def f(self, **k):
        base = {'source': 'contract', 'topic': 'x', 'severity': 'Minor', 'title': 't', 'clause_id': '1', 'quote': 'q', 'verified': True}
        base.update(k)
        return base

    def test_ordered_by_severity_and_ids_assigned(self):
        out = core.merge_findings([self.f(topic='a', severity='Minor', clause_id='1'), self.f(topic='b', severity='Serious', clause_id='2')])
        self.assertEqual([x['severity'] for x in out], ['Serious', 'Minor'])
        self.assertEqual([x['id'] for x in out], ['F01', 'F02'])

    def test_rule_topic_replaces_model_duplicate(self):
        out = core.merge_findings([self.f(source='rule', topic='liability', severity='Serious')], [self.f(topic='liability', severity='Negotiable', clause_id='9')])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['source'], 'rule')

    def test_handles_none_groups(self):
        self.assertEqual(core.merge_findings(None, [], None), [])


class ModelOutputHardening(unittest.TestCase):
    def test_clean_details_fixes_list_for_record(self):
        d = core.clean_details({'liability_cap': [{'kind': 'unlimited'}], 'delay_penalty': None, 'rates': 'bad', 'term_months': '12', 'total_value': 'n/a'})
        self.assertEqual(d['liability_cap']['kind'], 'unlimited')
        self.assertEqual(d['delay_penalty'], {})
        self.assertEqual(d['rates'], [])
        self.assertEqual(d['term_months'], 12)
        self.assertIsNone(d['total_value'])

    def test_parse_json_strips_fences(self):
        self.assertEqual(core.parse_json('```json\n{"a": 1}\n```'), {'a': 1})

    def test_parse_json_finds_object_in_chatter(self):
        self.assertEqual(core.parse_json('Sure! {"a": 2} hope that helps'), {'a': 2})

    def test_parse_json_repairs_trailing_commas(self):
        self.assertEqual(core.parse_json('{"a": [1, 2,], "b": {"c": 3,},}'), {'a': [1, 2], 'b': {'c': 3}})

    def test_parse_json_broken_object_raises_llm_error_not_json_error(self):
        with self.assertRaises(core.LLMError):
            core.parse_json('{"findings": [ {"title": "x" ')

    def test_parse_json_rejects_garbage(self):
        with self.assertRaises(core.LLMError):
            core.parse_json('no json at all')


class Api(unittest.TestCase):
    def test_health_and_unknown_action(self):
        code, out = review.handle({'action': 'health'})
        self.assertEqual(code, 200)
        self.assertEqual(len(out['principles']), 9)
        self.assertEqual(review.handle({'action': 'nope'})[1]['error'], 'unknown action')

    def test_segment_action(self):
        code, out = review.handle({'action': 'segment', 'text': read('synthetic/S01_orion_retail_msa_clean.md')})
        self.assertEqual(code, 200)
        self.assertTrue(out['clauses'])

    def test_rules_action_flags_unlimited(self):
        code, out = review.handle({'action': 'rules', 'details': {'atliq_entity': 'Inc', 'governing_law': 'Texas', 'client_country': 'USA', 'liability_cap': {'kind': 'unlimited'}}, 'text': 'unlimited liability applies to the vendor under this agreement'})
        self.assertEqual(code, 200)
        self.assertTrue(any(f['topic'] == 'liability' for f in out['findings']))

    def test_convert_text_and_docx_roundtrip(self):
        import base64
        import io
        import docx
        code, out = review.handle({'action': 'convert', 'name': 'a.txt', 'data': base64.b64encode(b'1.1 Hello clause\n1.2 Another').decode()})
        self.assertEqual(code, 200)
        d = docx.Document()
        d.add_paragraph('1.1 Payment within thirty days of receipt.')
        buf = io.BytesIO()
        d.save(buf)
        code, out = review.handle({'action': 'convert', 'name': 'a.docx', 'data': base64.b64encode(buf.getvalue()).decode()})
        self.assertIn('thirty days', out['text'])

    def test_garbage_pdf_gives_clean_error_not_crash(self):
        import base64
        code, out = review.handle({'action': 'convert', 'name': 'x.pdf', 'data': base64.b64encode(b'not a pdf').decode()})
        self.assertEqual(code, 500)
        self.assertIn('message', out)


if __name__ == '__main__':
    unittest.main(verbosity=1)

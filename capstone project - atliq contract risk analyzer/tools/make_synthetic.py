"""Builds the synthetic contracts, notes files, answer key (tests/answer_key.json) and public/data/samples.json.
Run: python tools/make_synthetic.py   (all names, figures and clauses here are invented for testing)"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public', 'samples', 'synthetic')
os.makedirs(OUT, exist_ok=True)


def doc(title, intro, parties, sections):
    out = ['*(Synthetic test contract. Invented names and figures, not a real client.)*', '', '# ' + title, '', intro, '', parties, '']
    for n, (head, clauses) in enumerate(sections, 1):
        out.append('## %d. %s' % (n, head.upper()))
        out.append('')
        for m, c in enumerate(clauses, 1):
            out.append('%d.%d %s' % (n, m, c))
        out.append('')
    return '\n'.join(out)


ATLIQ_INC = '**AtliQ Inc**, a Delaware corporation having its principal office at 101 College Road East, Suite 210, Princeton, New Jersey 08540 ("**Vendor**")'
ATLIQ_PVT = '**AtliQ Technologies Private Limited**, a company incorporated under the Companies Act, 2013 having its registered office at 4th Floor, Baner Business Bay, Pune 411045, Maharashtra, India ("**Vendor**")'

STD_CONF = ['Each party shall keep the other party\'s Confidential Information secret, use it only for the Services and disclose it only to personnel who need it and are bound by similar duties.',
            'These duties survive for three (3) years after termination of this Agreement and do not apply to information that is public, independently developed or lawfully received from a third party.']
STD_GEN = ['This Agreement is the entire agreement of the parties on its subject matter and may be changed only in writing signed by both parties.',
           'Neither party may assign this Agreement without the other\'s written consent, not to be unreasonably withheld.',
           'Notices must be in writing and sent to the addresses stated above.']

C = {}

# ---- S01 clean MSA
C['S01'] = doc('MASTER SERVICES AGREEMENT',
               'This Master Services Agreement (the "**Agreement**") is made as of ____________, 2026 between:',
               '**Orion Retail Partners Inc.**, an Ohio corporation having its principal office at 40 East Broad Street, Columbus, Ohio 43215 ("**Orion**"); and\n\n' + ATLIQ_INC + '.',
               [('Services', ['Vendor shall provide data engineering and business intelligence services to Orion for its store-level sales reporting, as described in the first Statement of Work ("**SOW-1**"), which forms part of this Agreement.',
                              'Orion shall provide timely access to its data, systems and personnel as reasonably needed for the Services.']),
                ('Term', ['This Agreement starts on the Effective Date and continues for twenty-four (24) months unless terminated earlier under this Agreement.']),
                ('Fees and payment', ['Orion shall pay Vendor fees of USD 180,000 in total for the first twenty-four (24) months, invoiced monthly in equal instalments of USD 7,500.',
                                      'Additional work is charged at USD 90 per hour for a Senior Data Engineer, USD 65 per hour for a Data Engineer and USD 60 per hour for a BI Developer.',
                                      'Orion shall pay each undisputed invoice within thirty (30) days of receipt.']),
                ('Delivery', ['Vendor shall deliver each milestone in SOW-1 by its target date.',
                              'If Vendor is late with a milestone for reasons within its control, Orion\'s sole remedy is a credit of one percent (1%) of that milestone\'s fee per week of delay, capped at five percent (5%) of the milestone fee. No credit applies where delay is caused by Orion, by a change in scope or by events outside Vendor\'s reasonable control.']),
                ('Intellectual property', ['Orion owns the Deliverables created specifically for it once paid for in full.',
                                           'Vendor keeps all rights in its pre-existing tools, frameworks and know-how, and grants Orion a non-exclusive licence to use them as part of the Deliverables.']),
                ('Confidentiality', STD_CONF),
                ('Indemnity and liability', ['Each party shall indemnify the other against third-party claims arising from its own gross negligence, wilful misconduct or breach of confidentiality.',
                                             'Each party\'s total liability under this Agreement is limited to the fees paid or payable in the twelve (12) months before the claim, except for fraud or wilful misconduct.']),
                ('Termination', ['Either party may terminate on sixty (60) days\' written notice, or immediately for the other\'s uncured material breach after thirty (30) days\' notice.',
                                 'On termination Orion shall pay Vendor for all work performed and expenses incurred up to the termination date.']),
                ('Governing law', ['This Agreement is governed by the laws of the State of New York, and the state and federal courts in New York County have exclusive jurisdiction.']),
                ('General', STD_GEN)])

# ---- S02 Brightwater-type
C['S02'] = doc('SOFTWARE DEVELOPMENT AND SERVICES AGREEMENT',
               'This Agreement is made as of ____________, 2026 between:',
               '**Coastal Mutual Insurance Company**, a Florida corporation having its principal office at 800 Brickell Avenue, Miami, Florida 33131 ("**Client**"); and\n\n' + ATLIQ_INC + '.',
               [('Services', ['Vendor shall design and build a claims analytics platform for Client as set out in Schedule A, in three milestones.']),
                ('Term and fees', ['The project runs for twelve (12) months. Client shall pay a fixed fee of USD 120,000 in three equal milestone payments.',
                                   'Client shall pay each invoice within sixty (60) days of the invoice date.']),
                ('Delay', ['If Vendor fails to complete any milestone by its due date, Vendor shall pay Client liquidated damages of two percent (2%) of the total project fee for each week of delay until completion.',
                           'Delay for any reason, including delay in Client providing data or approvals, entitles Client to liquidated damages.']),
                ('Intellectual property', ['All work product, including Vendor\'s pre-existing tools incorporated in it, is owned by Client on creation.']),
                ('Indemnity', ['Vendor shall indemnify, defend and hold harmless Client from all claims, losses and costs arising from the Services or this Agreement, including claims arising from Client\'s own negligence.']),
                ('Liability', ['Vendor\'s liability under this Agreement is unlimited. Client\'s liability is limited to the fees payable under this Agreement.']),
                ('Confidentiality', STD_CONF),
                ('Termination', ['Client may terminate at any time for convenience without payment for work in progress.',
                                 'Vendor may terminate only for Client\'s non-payment continuing for ninety (90) days.']),
                ('Governing law', ['This Agreement is governed by the laws of the State of Florida and the courts of Miami-Dade County.']),
                ('General', STD_GEN)])

# ---- S03 small SOW with huge cap
C['S03'] = doc('SERVICES AGREEMENT',
               'This Services Agreement (the "**Agreement**") is made as of ____________, 2026 between:',
               '**Maple Street Bakery Inc.**, a Pennsylvania corporation having its principal office at 18 Maple Street, Lancaster, Pennsylvania 17602 ("**Client**"); and\n\n' + ATLIQ_INC + '.',
               [('Services', ['Vendor shall build and maintain a daily sales dashboard for Client\'s eight bakery outlets.']),
                ('Term and fees', ['The term is twelve (12) months. Client shall pay USD 24,000 for the term in twelve monthly payments of USD 2,000.',
                                   'Client shall pay each invoice within thirty (30) days of receipt.']),
                ('Intellectual property', ['Client owns the dashboard created for it. Vendor keeps its pre-existing tools and know-how.']),
                ('Confidentiality', STD_CONF),
                ('Liability', ['Each party shall indemnify the other against third-party claims caused by its own negligence.',
                               'The aggregate liability of Vendor under or in connection with this Agreement shall not exceed USD 500,000.']),
                ('Termination', ['Either party may terminate on thirty (30) days\' written notice. Client shall pay for work performed up to termination.']),
                ('Governing law', ['This Agreement is governed by the laws of the Commonwealth of Pennsylvania.']),
                ('General', STD_GEN)])

# ---- S04 "mutual" NDA that is one-sided
C['S04'] = doc('MUTUAL NON-DISCLOSURE AGREEMENT',
               'This Mutual Non-Disclosure Agreement (the "**Agreement**") is made as of ____________, 2026 between:',
               '**Vantage Biosciences Inc.**, a Massachusetts corporation having its principal office at 1 Kendall Square, Cambridge, Massachusetts 02139 (the "**Company**"); and\n\n' + ATLIQ_INC + ' (the "**Recipient**").',
               [('Purpose', ['The parties wish to explore a data analytics engagement (the "**Purpose**").']),
                ('Definitions', ['"**Confidential Information**" means all information disclosed by the Company to the Recipient, in any form, relating to the Company\'s business, research, data, systems and plans, and all notes or analyses prepared by the Recipient from it.']),
                ('Obligations', ['The Recipient shall hold the Confidential Information in strict confidence, use it only for the Purpose, and not disclose it to anyone.',
                                 'The Company has no obligation to keep confidential any information it receives from the Recipient, and may use that information for any purpose.',
                                 'The Recipient shall return or destroy all Confidential Information on request and certify this in writing.']),
                ('Term', ['The Recipient\'s obligations continue for seven (7) years from the date of this Agreement, and indefinitely for trade secrets.']),
                ('Remedies', ['The Recipient shall be liable for all losses arising from any breach, without limit, and the Company may seek injunctive relief without proof of damage.']),
                ('Governing law', ['This Agreement is governed by the laws of the Commonwealth of Massachusetts.'])])

# ---- S05 truly mutual NDA
C['S05'] = doc('MUTUAL NON-DISCLOSURE AGREEMENT',
               'This Mutual Non-Disclosure Agreement (the "**Agreement**") is made as of ____________, 2026 between:',
               '**Granite Peak Logistics LLC**, a Colorado limited liability company having its principal office at 1700 Lincoln Street, Denver, Colorado 80203 ("**Granite Peak**"); and\n\n' + ATLIQ_INC + '.',
               [('Purpose', ['The parties wish to discuss a possible analytics engagement and will exchange confidential information for that purpose only (the "**Purpose**").']),
                ('Definitions', ['"**Confidential Information**" means non-public information disclosed by either party (the "**Discloser**") to the other (the "**Recipient**") that is marked confidential or would reasonably be understood to be confidential.']),
                ('Obligations', ['Each Recipient shall protect the Discloser\'s Confidential Information with at least the care it uses for its own, use it only for the Purpose, and disclose it only to personnel who need to know and are bound by similar duties.',
                                 'These duties do not apply to information that is public, already known to the Recipient, independently developed or lawfully received from a third party.']),
                ('Term', ['The obligations in this Agreement last for three (3) years from the date of this Agreement.']),
                ('Return', ['On request, each party shall return or destroy the other\'s Confidential Information, except for copies required by law.']),
                ('Governing law', ['This Agreement is governed by the laws of the State of Delaware.'])])

# ---- S06 healthcare, no BAA, $5M cyber
C['S06'] = doc('MASTER SERVICES AGREEMENT',
               'This Master Services Agreement (the "**Agreement**") is made as of ____________, 2026 between:',
               '**Sterling Care Network Inc.**, a Texas corporation having its principal office at 500 Main Street, Houston, Texas 77002 ("**Sterling**"); and\n\n' + ATLIQ_INC + '.',
               [('Services', ['Vendor shall provide data engineering and analytics services to Sterling to improve patient scheduling and clinic utilisation.',
                              'To perform the Services, Vendor will access Sterling\'s patient records, including protected health information ("**PHI**") for approximately 120,000 patients, in Sterling\'s data warehouse.']),
                ('Term and fees', ['The term is eighteen (18) months. Sterling shall pay USD 270,000 in total in monthly instalments, within thirty (30) days of receipt of each invoice.']),
                ('Security', ['Vendor shall maintain industry-standard administrative, technical and physical safeguards for Sterling\'s data.',
                              'Vendor shall maintain, throughout the term, cyber liability insurance of not less than USD 5,000,000 per claim.']),
                ('Intellectual property', ['Sterling owns the Deliverables. Vendor keeps its pre-existing tools.']),
                ('Confidentiality', STD_CONF),
                ('Liability', ['Each party\'s total liability is limited to the fees paid in the twelve (12) months before the claim.']),
                ('Termination', ['Either party may terminate on sixty (60) days\' notice. Sterling shall pay for work performed to the termination date.']),
                ('Governing law', ['This Agreement is governed by the laws of the State of Texas.']),
                ('General', STD_GEN)])

# ---- S07 hospitality (UAE) collides with Al Noor + expired Orbit, and adds a new 6-month non-compete
C['S07'] = doc('MASTER SERVICES AGREEMENT',
               'This Master Services Agreement (the "**Agreement**") is made as of 1 November 2026 (the "**Effective Date**") between:',
               '**Marina Bay Resorts LLC**, a company incorporated in Dubai, United Arab Emirates, having its registered office at Sheikh Zayed Road, Dubai ("**Marina Bay**"); and\n\n' + ATLIQ_PVT + '.',
               [('Services', ['Vendor shall provide revenue-management analytics and guest analytics services for Marina Bay\'s four resorts in Dubai and Abu Dhabi.',
                              'The services include a booking-engine module that lets guests search and book rooms online, similar in function to travel-booking software.']),
                ('Term and fees', ['The term is twelve (12) months from the Effective Date. Marina Bay shall pay USD 150,000 in total, within thirty (30) days of receipt of each invoice.']),
                ('Exclusivity', ['For six (6) months after the end of the term, Vendor shall not provide revenue-management services to any other hotel group in the United Arab Emirates.']),
                ('Intellectual property', ['Marina Bay owns the Deliverables. Vendor keeps its pre-existing tools.']),
                ('Confidentiality', STD_CONF),
                ('Liability', ['Each party\'s total liability is limited to the fees paid in the twelve (12) months before the claim.']),
                ('Termination', ['Either party may terminate on sixty (60) days\' notice. Marina Bay shall pay for work performed to the termination date.']),
                ('Governing law', ['This Agreement is governed by the laws of India and the courts of Pune have exclusive jurisdiction.']),
                ('General', STD_GEN)])

# ---- S08 wrong entity and law
C['S08'] = doc('MASTER SERVICES AGREEMENT',
               'This Master Services Agreement (the "**Agreement**") is made as of ____________, 2026 between:',
               '**Redwood Software Inc.**, a California corporation having its principal office at 200 Mission Street, San Francisco, California 94105 ("**Redwood**"); and\n\n' + ATLIQ_PVT + '.',
               [('Services', ['Vendor shall provide data engineering services to Redwood for its product usage analytics, as set out in each Statement of Work.']),
                ('Term and fees', ['The term is twelve (12) months. Redwood shall pay USD 96,000 in total in monthly instalments, within thirty (30) days of receipt of each invoice.']),
                ('Intellectual property', ['Redwood owns the Deliverables. Vendor keeps its pre-existing tools.']),
                ('Confidentiality', STD_CONF),
                ('Liability', ['Each party\'s total liability is limited to the fees paid in the twelve (12) months before the claim.']),
                ('Termination', ['Either party may terminate on sixty (60) days\' notice. Redwood shall pay for work performed to the termination date.']),
                ('Governing law', ['This Agreement is governed by the laws of the State of California, and the parties submit to the exclusive jurisdiction of the courts of San Francisco County, California.']),
                ('General', STD_GEN)])

# ---- S09 clean-ish SOW + call notes with a verbal 10% discount
C['S09'] = doc('MASTER SERVICES AGREEMENT',
               'This Master Services Agreement (the "**Agreement**") is made as of ____________, 2026 between:',
               '**Fieldstone Foods Inc.**, an Iowa corporation having its principal office at 300 Walnut Street, Des Moines, Iowa 50309 ("**Fieldstone**"); and\n\n' + ATLIQ_INC + '.',
               [('Services', ['Vendor shall provide demand forecasting and data engineering services to Fieldstone as set out in SOW-1.']),
                ('Term and fees', ['The term is twenty-four (24) months. Fieldstone shall pay USD 300,000 in total (USD 150,000 per year), invoiced monthly, within thirty (30) days of receipt.']),
                ('Intellectual property', ['Fieldstone owns the Deliverables. Vendor keeps its pre-existing tools.']),
                ('Confidentiality', STD_CONF),
                ('Liability', ['Each party\'s total liability is limited to the fees paid in the twelve (12) months before the claim.']),
                ('Termination', ['Either party may terminate on sixty (60) days\' notice. Fieldstone shall pay for work performed to the termination date.']),
                ('Governing law', ['This Agreement is governed by the laws of the State of Iowa.']),
                ('Entire agreement', ['This Agreement is the entire agreement of the parties and supersedes all prior discussions and understandings.'] + STD_GEN[:1])])
N09 = """Call notes - Fieldstone Foods pricing call, 24 Sept 2026
Attendees: Jay (AtliQ), Karandeep (AtliQ), Dana Whitfield (Fieldstone procurement)

- Dana asked for a better price in year 2. Jay agreed on the call to a 10% discount on the year 2 fees if they sign by the end of October.
- Jay also said AtliQ would add one extra dashboard for the warehouse team at no charge.
- Dana will send the signed MSA once legal is happy with the liability wording.
- Karandeep to send the draft SOW-1 next week.
"""

# ---- S10 chat notes: scope cut + 60-day payment
C['S10'] = doc('MASTER SERVICES AGREEMENT',
               'This Master Services Agreement (the "**Agreement**") is made as of ____________, 2026 between:',
               '**Bluewater Marine Supplies Inc.**, a Washington corporation having its principal office at 1200 Alaskan Way, Seattle, Washington 98101 ("**Bluewater**"); and\n\n' + ATLIQ_INC + '.',
               [('Services', ['Vendor shall provide a customer analytics dashboard and a mobile reporting application for Bluewater as set out in SOW-1.']),
                ('Term and fees', ['The term is twelve (12) months. Bluewater shall pay USD 84,000 in total in monthly instalments, within thirty (30) days of receipt of each invoice.']),
                ('Intellectual property', ['Bluewater owns the Deliverables. Vendor keeps its pre-existing tools.']),
                ('Confidentiality', STD_CONF),
                ('Liability', ['Each party\'s total liability is limited to the fees paid in the twelve (12) months before the claim.']),
                ('Termination', ['Either party may terminate on sixty (60) days\' notice. Bluewater shall pay for work performed to the termination date.']),
                ('Governing law', ['This Agreement is governed by the laws of the State of Washington.']),
                ('General', STD_GEN)])
N10 = """Chat export - Bluewater project channel, 2 Oct 2026

[10:02] Marcus (Bluewater): can we drop the mobile app from phase 1? budget is tight, dashboard only for now
[10:05] Karan: sure, we can do dashboard only, same price works for us
[10:07] Marcus (Bluewater): also our finance team pays on 60 day cycles, hope that is fine
[10:09] Karan: should be OK, we will make it work
[10:11] Marcus (Bluewater): great, I will tell legal to leave the contract as is
"""

NAMES = {
    'S01': ('S01_orion_retail_msa_clean.md', 'S01 Orion Retail MSA (clean)'),
    'S02': ('S02_coastal_mutual_insurance_agreement.md', 'S02 Coastal Mutual Insurance (Brightwater-type)'),
    'S03': ('S03_maple_street_bakery_small_sow.md', 'S03 Maple Street Bakery ($500k cap on $24k)'),
    'S04': ('S04_vantage_biosciences_one_sided_nda.md', 'S04 Vantage Biosciences ("mutual" NDA, one-sided)'),
    'S05': ('S05_granite_peak_mutual_nda.md', 'S05 Granite Peak (truly mutual NDA)'),
    'S06': ('S06_sterling_care_msa_no_baa.md', 'S06 Sterling Care (health data, no BAA, $5M cyber)'),
    'S07': ('S07_marina_bay_resorts_msa.md', 'S07 Marina Bay Resorts (Dubai, collides with Al Noor)'),
    'S08': ('S08_redwood_software_wrong_entity.md', 'S08 Redwood Software (wrong entity and law)'),
    'S09': ('S09_fieldstone_foods_msa.md', 'S09 Fieldstone Foods + call notes (verbal 10% discount)'),
    'S10': ('S10_bluewater_marine_msa.md', 'S10 Bluewater Marine + chat (scope cut, 60-day payment)'),
}
NOTES = {'S09': ('S09_fieldstone_call_notes.md', N09), 'S10': ('S10_bluewater_chat_export.md', N10)}

# What a correct review must contain. "must" = (finding source/topic matcher, minimum severity). "no_serious" = false alarms test.
KEY = {
    'S01': {'no_serious': True, 'max_serious': 0, 'must': []},
    'S02': {'must': [{'topic': 'liability', 'sev': 'Serious'}, {'topic': 'delay_penalty', 'sev': 'Serious'}, {'topic': 'payment', 'sev': 'Negotiable'}, {'topic': 'indemnity', 'sev': 'Negotiable'}]},
    'S03': {'must': [{'topic': 'liability', 'sev': 'Serious'}]},
    'S04': {'must': [{'topic': 'confidentiality', 'sev': 'Negotiable', 'also': ['nda', 'mutual', 'one_sided', 'one-sided']}]},
    'S05': {'no_serious': True, 'max_serious': 0, 'must': []},
    'S06': {'must': [{'topic': 'data_protection', 'sev': 'Serious'}, {'topic': 'insurance', 'sev': 'Serious'}]},
    'S07': {'must': [{'register': 'R-01', 'sev': 'Serious'}]},
    'S08': {'must': [{'topic': 'governing_law', 'sev': 'Serious'}]},
    'S09': {'must': [{'source': 'unofficial', 'sev': 'Negotiable', 'mentions': ['discount', '10%']}]},
    'S10': {'must': [{'source': 'unofficial', 'sev': 'Negotiable', 'mentions': ['60', 'payment', 'pay']}, {'source': 'unofficial', 'sev': 'Negotiable', 'mentions': ['mobile', 'scope', 'dashboard']}]},
}
CONTEXT = {k: {} for k in KEY}

samples = []
for k, text in C.items():
    fn, label = NAMES[k]
    open(os.path.join(OUT, fn), 'w', encoding='utf-8').write(text)
    s = {'file': 'samples/synthetic/' + fn, 'label': label}
    if k in NOTES:
        nf, nt = NOTES[k]
        open(os.path.join(OUT, nf), 'w', encoding='utf-8').write(nt)
        s['notes'] = 'samples/synthetic/' + nf
    samples.append(s)
    KEY[k]['file'] = s['file']
    KEY[k]['notes'] = s.get('notes')
    KEY[k]['label'] = label

# real incoming drafts offered in the picker too
inc = os.path.join(ROOT, 'public', 'samples', 'incoming')
real = []
for fn in sorted(os.listdir(inc)):
    base = fn[11:].rsplit('.', 1)[0].replace('_', ' ')
    real.append({'file': 'samples/incoming/' + fn, 'label': 'Incoming: ' + base})
json.dump(samples + real, open(os.path.join(ROOT, 'public', 'data', 'samples.json'), 'w', encoding='utf-8'), indent=1)
os.makedirs(os.path.join(ROOT, 'tests'), exist_ok=True)
json.dump(KEY, open(os.path.join(ROOT, 'tests', 'answer_key.json'), 'w', encoding='utf-8'), indent=1)
print('wrote', len(samples), 'synthetic contracts and', len(real), 'real drafts to samples.json')

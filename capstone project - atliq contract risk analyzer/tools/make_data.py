"""Builds data/register.json, data/benchmark.json, data/principles.json and data/contracts.json.

The register is written by hand from the 17 signed contracts on file (Dataset/signed_contracts),
so every quote is an exact substring of the source file. Run: python tools/make_data.py
"""
import csv, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
PUB = os.path.join(ROOT, 'public', 'data')
os.makedirs(DATA, exist_ok=True)
os.makedirs(PUB, exist_ok=True)

S = 'samples/signed/'
# ---------------------------------------------------------------- register of past commitments
register = [
    {
        "id": "R-01", "contract_id": "C-007", "counterparty": "Al Noor Hospitality Group", "file": S + "2025-03-15_al_noor_hospitality_msa.md",
        "type": "non_compete", "clause": "12.1", "bound": "AtliQ Technologies Pvt Ltd and its Affiliates (including AtliQ Inc)",
        "restricted_activity": "Data analytics, AI or revenue-management services",
        "scope": {"customers": "Any hospitality business (hotels, resorts, serviced apartments, and providers of revenue management or guest analytics to them)", "geography": ["UAE", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman"]},
        "start": "2025-03-15", "end": "2029-09-14", "end_basis": "Term (to 14 Mar 2028) plus 18 months (clause 1.14)",
        "quote": "the Supplier undertakes that neither it nor any of its Affiliates shall, during the Restricted Period, directly or indirectly, provide data analytics, artificial intelligence or revenue-management services to any Hospitality Business in the GCC.",
        "exception": "Clause 12.4 lets Al Noor waive it per engagement by written consent. Waiver letter of 10 Feb 2026 allows only the Seaside Hotels (Muscat) demand-forecasting SOW; not follow-on SOWs, other hotels or Affiliates.",
        "waiver_file": S + "2026-02-10_al_noor_waiver_letter.md",
        "waiver_quote": "This consent is strictly limited to the Seaside SOW.",
        "takeaway": "Do not take analytics, AI or revenue-management work for hotel groups in the GCC until about September 2029 without Al Noor's written consent."
    },
    {
        "id": "R-02", "contract_id": "C-002", "counterparty": "Crestline Retail Inc", "file": S + "2024-08-01_crestline_retail_msa.md",
        "type": "mfn_pricing", "clause": "6.4", "bound": "AtliQ Inc and its Affiliates",
        "restricted_activity": "Offering lower rates to any other customer for substantially similar services",
        "scope": {"customers": "Any other customer", "geography": ["Worldwide"]},
        "start": "2024-08-01", "end": "2027-07-31", "end_basis": "During the Term (to 31 Jul 2027)",
        "quote": "Supplier represents and warrants that the rates, fees and other commercial terms offered to Crestline under this Agreement are and shall remain no less favorable than those offered by Supplier or its Affiliates to any other customer for substantially similar services during the Term.",
        "exception": "Lower rates must be reported and applied to Crestline retroactively, with a credit within 30 days. Rate card: Senior Data Engineer $85/hr, Data Engineer $62/hr, BI Developer $58/hr.",
        "takeaway": "Any rate below Crestline's rate card for similar services (for example a senior data engineer under $85/hr) triggers a retroactive credit to Crestline."
    },
    {
        "id": "R-03", "contract_id": "C-032", "counterparty": "CloudSpan Technologies", "file": S + "2025-09-01_cloudspan_strategic_partnership_agreement.md",
        "type": "exclusivity", "clause": "7.1", "bound": "AtliQ Technologies Pvt Ltd and its Affiliates",
        "restricted_activity": "Acting as implementation, reseller or referral partner for any competing cloud data-warehouse, lakehouse or analytics platform",
        "scope": {"customers": "Any competing platform vendor", "geography": ["India", "UAE", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman"]},
        "start": "2025-09-01", "end": "2028-08-31", "end_basis": "During the Term (to 31 Aug 2028)",
        "quote": "during the Term Partner and its Affiliates shall not act as an implementation, reseller or referral partner for any Competing Platform in India or the GCC.",
        "exception": "Clause 7.3: does not restrict services outside India and the GCC, or to a customer that independently selected a platform, provided AtliQ holds no partner appointment with, and receives no fee from, that platform's provider.",
        "takeaway": "Do not partner with another cloud data-warehouse or lakehouse vendor in India or the GCC while the CloudSpan agreement runs."
    },
    {
        "id": "R-04", "contract_id": "C-001", "counterparty": "Orbit Travels", "file": S + "2022-07-01_orbit_travels_msa_scanned.md",
        "type": "non_compete", "clause": "6.1", "bound": "AtliQ Technologies Pvt Ltd",
        "restricted_activity": "Developing, licensing or providing travel-booking software",
        "scope": {"customers": "Online travel agencies", "geography": ["India"]},
        "start": "2022-07-01", "end": "2025-06-30", "end_basis": "Term (to 30 Jun 2024) plus 12 months",
        "quote": "it shall not develop, license or provide travel-booking software to any online travel agency operating in India.",
        "exception": "Clause 6.2: hotels, airlines and other businesses that are not online travel agencies are not restricted. Scanned copy with OCR errors; read with care.",
        "takeaway": "Expired. Shown for confidence: AtliQ could not build travel-booking software for Indian online travel agencies until 30 June 2025."
    },
    {
        "id": "R-05", "contract_id": "C-020", "counterparty": "Meridian Healthcare", "file": S + "2026-07-16_meridian_healthcare_nda.md",
        "type": "non_solicit", "clause": "7.3", "bound": "AtliQ (Recipient) only; not mutual",
        "restricted_activity": "Soliciting or hiring Meridian employees or consultants AtliQ dealt with",
        "scope": {"customers": "Meridian Healthcare staff", "geography": ["Worldwide"]},
        "start": "2026-07-16", "end": "2031-07-16", "end_basis": "Three-year term plus 24 months",
        "quote": "the Recipient shall not, directly or indirectly, solicit for employment or engagement, or employ or engage, any employee or consultant of Meridian with whom the Recipient had contact in connection with the Purpose, without Meridian's prior written consent.",
        "exception": "One-way: binds AtliQ only.",
        "takeaway": "One-way non-solicit and no-hire for 24 months after the NDA ends."
    },
    {
        "id": "R-06", "contract_id": "C-009", "counterparty": "Northwind Logistics", "file": S + "2025-06-20_northwind_logistics_msa.md",
        "type": "ip_assignment", "clause": "9.2", "bound": "AtliQ Technologies Pvt Ltd",
        "restricted_activity": "Reusing tools or frameworks (including the PipeKit accelerator) built into Northwind's deliverables",
        "scope": {"customers": "Any other client", "geography": ["Worldwide"]},
        "start": "2025-06-20", "end": None, "end_basis": "Perpetual assignment",
        "quote": "All Intellectual Property Rights in the Deliverables, including any software, tools, frameworks, libraries and pre-existing materials incorporated into the Deliverables, shall vest in the Client absolutely upon payment of the Charges for the relevant Milestone.",
        "exception": "SOW-1 builds the pipeline with AtliQ's proprietary PipeKit accelerator, which is incorporated into the deliverable, so rights in that PipeKit configuration pass to Northwind on payment.",
        "takeaway": "PipeKit as delivered to Northwind belongs to Northwind. Check before promising to reuse PipeKit 'like we did for Northwind'."
    },
    {
        "id": "R-07", "contract_id": "C-005", "counterparty": "PayTrack Technologies", "file": S + "2025-01-22_paytrack_technologies_msa.md",
        "type": "data_location", "clause": "7.2", "bound": "AtliQ Technologies Pvt Ltd",
        "restricted_activity": "Storing client payment data outside India",
        "scope": {"customers": "PayTrack data", "geography": ["India"]},
        "start": "2025-01-22", "end": None, "end_basis": "Indefinite for Client Data (clause 7.3)",
        "quote": "AtliQ acknowledges that Client Data may include payment system data subject to RBI data localisation requirements, and shall ensure that such data is stored only in India.",
        "exception": "",
        "takeaway": "PayTrack data must stay in India."
    },
    {
        "id": "R-08", "contract_id": "C-002", "counterparty": "Crestline Retail Inc", "file": S + "2024-08-01_crestline_retail_msa.md",
        "type": "data_location", "clause": "13.3", "bound": "AtliQ Inc",
        "restricted_activity": "Accessing Crestline production data from outside the United States",
        "scope": {"customers": "Crestline data", "geography": ["United States"]},
        "start": "2024-08-01", "end": "2027-07-31", "end_basis": "During the Term",
        "quote": "Supplier shall not access Crestline production data from outside the United States without Crestline's prior written approval.",
        "exception": "Prior written approval from Crestline.",
        "takeaway": "The Pune team needs Crestline's written approval before touching production data."
    },
    {
        "id": "R-09", "contract_id": "C-007", "counterparty": "Al Noor Hospitality Group", "file": S + "2025-03-15_al_noor_hospitality_msa.md",
        "type": "data_location", "clause": "16.3", "bound": "AtliQ Technologies Pvt Ltd",
        "restricted_activity": "Transferring Al Noor guest data outside the UAE",
        "scope": {"customers": "Al Noor guest data", "geography": ["UAE"]},
        "start": "2025-03-15", "end": "2028-03-14", "end_basis": "During the Term",
        "quote": "The Supplier shall not transfer Guest Data outside the UAE without the Client's prior written consent. Any Guest Data accessed from India shall be accessed remotely from UAE-hosted environments only.",
        "exception": "",
        "takeaway": "Guest data stays in UAE-hosted environments."
    },
    {
        "id": "R-10", "contract_id": "C-043", "counterparty": "CareBridge Clinics", "file": S + "2025-10-06_carebridge_clinics_baa.md",
        "type": "data_location", "clause": "3.2", "bound": "AtliQ Inc and any subcontractor",
        "restricted_activity": "Accessing PHI outside the United States",
        "scope": {"customers": "CareBridge patient data", "geography": ["United States"]},
        "start": "2025-10-06", "end": "2026-10-05", "end_basis": "BAA runs until the MSA expires (5 Oct 2026); PHI protections may survive",
        "quote": "No PHI shall be accessed, stored or processed outside the United States.",
        "exception": "Personnel outside the United States may access de-identified data only, inside an approved environment. Subcontractors need a matching BAA (clause 6.1).",
        "takeaway": "Only de-identified data offshore; subcontractors need a matching BAA."
    },
    {
        "id": "R-11", "contract_id": "C-006", "counterparty": "Acme Retail Group", "file": S + "2025-03-10_acme_retail_group_msa.md",
        "type": "non_solicit", "clause": "14.1", "bound": "Both parties (mutual)",
        "restricted_activity": "Soliciting the other party's employees involved in the Services",
        "scope": {"customers": "Acme staff", "geography": ["Worldwide"]},
        "start": "2025-03-10", "end": "2027-09-09", "end_basis": "Two-year term plus 6 months",
        "quote": "During the term and for six (6) months thereafter, neither Party shall solicit any employee of the other Party who was involved in the Services.",
        "exception": "Mutual.", "takeaway": "Mutual non-solicit, low impact."
    },
    {
        "id": "R-12", "contract_id": "C-005", "counterparty": "PayTrack Technologies", "file": S + "2025-01-22_paytrack_technologies_msa.md",
        "type": "non_solicit", "clause": "13.1", "bound": "Both parties (mutual)",
        "restricted_activity": "Soliciting the other party's employees engaged in the Services",
        "scope": {"customers": "PayTrack staff", "geography": ["Worldwide"]},
        "start": "2025-01-22", "end": "2028-01-21", "end_basis": "Two-year term plus 12 months",
        "quote": "Neither Party shall solicit for employment the other Party's employees engaged in the Services during the term and for twelve (12) months thereafter.",
        "exception": "Mutual.", "takeaway": "Mutual non-solicit, low impact."
    },
    {
        "id": "R-13", "contract_id": "C-009", "counterparty": "Northwind Logistics", "file": S + "2025-06-20_northwind_logistics_msa.md",
        "type": "non_solicit", "clause": "8.2", "bound": "Both parties (mutual)",
        "restricted_activity": "Soliciting the other party's employees engaged in the Services",
        "scope": {"customers": "Northwind staff", "geography": ["Worldwide"]},
        "start": "2025-06-20", "end": "2028-12-19", "end_basis": "Three-year term plus 6 months",
        "quote": "Neither party shall, during the term and for six (6) months afterwards, solicit any employee of the other party engaged in the Services.",
        "exception": "Mutual.", "takeaway": "Mutual non-solicit, low impact."
    },
    {
        "id": "R-14", "contract_id": "C-008", "counterparty": "Sunrise Foods", "file": S + "2025-04-18_sunrise_foods_msa.md",
        "type": "non_solicit", "clause": "15.1", "bound": "Both parties (mutual)",
        "restricted_activity": "Soliciting the other party's employees engaged in the Services",
        "scope": {"customers": "Sunrise staff", "geography": ["Worldwide"]},
        "start": "2025-04-18", "end": "2028-10-17", "end_basis": "Three-year term plus 6 months (approximate)",
        "quote": "Neither Party shall solicit the employees of the other Party engaged in the Services during the term of the relevant SOW and six (6) months thereafter.",
        "exception": "Mutual.", "takeaway": "Mutual non-solicit, low impact."
    },
]

# ---------------------------------------------------------------- benchmark (from the 17 files on hand)
benchmark = {
    "source": "17 signed contracts on file (13 more of the 30 known contracts are not on file)",
    "contracts_on_file": 17, "contracts_known": 30,
    "liability_cap_multiple_of_fees": {
        "values": [
            {"contract": "PayTrack MSA", "multiple": 1.0, "basis": "fees under the SOW"},
            {"contract": "Acme MSA", "multiple": 1.0, "basis": "fees under the SOW"},
            {"contract": "Sunrise Foods MSA", "multiple": 1.0, "basis": "fees under the SOW"},
            {"contract": "Northwind MSA", "multiple": 1.0, "basis": "charges under the SOW"},
            {"contract": "Trustline MSA", "multiple": 1.0, "basis": "total fees"},
            {"contract": "Crestline MSA", "multiple": 1.0, "basis": "fees in the preceding 12 months"},
            {"contract": "Al Noor MSA", "multiple": 1.0, "basis": "fees in the preceding 12 months"},
            {"contract": "Orbit Travels MSA", "multiple": 1.0, "basis": "fees in the preceding 12 months"},
            {"contract": "Brightwater MSA", "multiple": 1.5, "basis": "150% of contract value"},
            {"contract": "CareBridge BAA", "multiple": 2.0, "basis": "fees in the preceding 12 months"}
        ],
        "typical": 1.0, "max_seen": 2.0,
        "summary": "8 of 10 client contracts cap liability at about 1x fees; the highest seen is 2x."
    },
    "delay_penalties": {
        "summary": "Acme, Northwind and Trustline: 0.5% of the milestone fee per week, capped at 5% of that milestone, client-caused delay excluded. Al Noor: 1% of milestone fees per week capped at 10% of total fees, client delay excluded. Brightwater (the outlier that cost AtliQ): 1% of contract value per day, no cap, no client-delay exclusion."
    },
    "payment_days": {"values": {"30": 6, "45": 2}, "summary": "30 days in most contracts; 45 days in Brightwater and Trustline."},
    "governing_law": {"summary": "India for most Pvt Ltd contracts (Mumbai, Pune or Delhi seats). Exceptions: Al Noor (DIFC), Northwind (English law, accepted), Brightwater (English law on a US-entity contract, signed under time pressure). US entity contracts: Ohio (Crestline), Texas (Harrington NDA), Arizona (CareBridge BAA)."},
    "ip": {"summary": "Client owns deliverables on payment; AtliQ keeps pre-existing tools and licenses them. Northwind is the exception: pre-existing materials incorporated in deliverables also pass to the client."},
    "non_solicit": {"summary": "Mutual, 6 to 12 months after the term in most contracts. Meridian NDA is one-way for 24 months."}
}

principles = [
    {"id": "P1", "text": "Delay penalties must be capped and must exclude delays caused by the client, scope changes or outside events."},
    {"id": "P2", "text": "Liability should be about 1x the fees and never unlimited; it should be proportionate to the contract value. (A preference, not a rule.)"},
    {"id": "P3", "text": "Indemnity should be mutual. AtliQ does not cover the other side's own negligence."},
    {"id": "P4", "text": "Payment within 30 days, 45 at most."},
    {"id": "P5", "text": "Governing law: India for AtliQ Technologies Pvt Ltd, the US for AtliQ Inc. Exceptions are possible but should be deliberate."},
    {"id": "P6", "text": "The client owns what AtliQ builds for them; AtliQ keeps its own pre-existing tools."},
    {"id": "P7", "text": "On termination, AtliQ is paid for work done."},
    {"id": "P8", "text": "Confidentiality should be mutual. A contract titled mutual must be checked for what each side is actually bound to."},
    {"id": "P9", "text": "No clash with promises AtliQ has already made: non-competes, exclusivity, most-favoured pricing, IP handed over, data location."}
]

with open(os.path.join(DATA, 'register.json'), 'w', encoding='utf-8') as f:
    json.dump(register, f, indent=1, ensure_ascii=False)
with open(os.path.join(DATA, 'benchmark.json'), 'w', encoding='utf-8') as f:
    json.dump(benchmark, f, indent=1, ensure_ascii=False)
with open(os.path.join(DATA, 'principles.json'), 'w', encoding='utf-8') as f:
    json.dump(principles, f, indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- contracts table (from the tracker)
files = {
    'C-001': 'signed/2022-07-01_orbit_travels_msa_scanned.md', 'C-002': 'signed/2024-08-01_crestline_retail_msa.md',
    'C-005': 'signed/2025-01-22_paytrack_technologies_msa.md', 'C-006': 'signed/2025-03-10_acme_retail_group_msa.md',
    'C-007': 'signed/2025-03-15_al_noor_hospitality_msa.md', 'C-008': 'signed/2025-04-18_sunrise_foods_msa.md',
    'C-009': 'signed/2025-06-20_northwind_logistics_msa.md', 'C-013': 'signed/2025-01-22_al_noor_mutual_nda.md',
    'C-014': 'signed/2025-11-28_brightwater_insurance_msa.md', 'C-016': 'signed/2026-02-10_al_noor_waiver_letter.md',
    'C-020': 'signed/2026-07-16_meridian_healthcare_nda.md', 'C-021': 'signed/2026-08-15_trustline_nbfc_msa.md',
    'C-032': 'signed/2025-09-01_cloudspan_strategic_partnership_agreement.md', 'C-039': 'signed/2025-04-28_rohan_iyer_contractor_agreement.md',
    'C-043': 'signed/2025-10-06_carebridge_clinics_baa.md', 'C-044': 'signed/2025-10-06_atliq_intercompany_subcontractor_baa.md',
    'C-045': 'signed/2026-08-20_harrington_health_mutual_nda.md',
    'C-023': 'incoming/2026-09-10_harrington_health_msa_draft.md', 'C-046': 'incoming/2026-09-16_harrington_health_baa_draft.md',
    'C-024': 'incoming/2026-09-15_travelhub_services_agreement_draft.md', 'C-025': 'incoming/2026-09-18_gulf_crown_hotels_msa_draft.md',
    'C-026': 'incoming/2026-09-19_lakeshore_grocers_msa_draft.md', 'C-027': 'incoming/2026-09-21_blueorchid_hotels_pilot_agreement_draft.md',
    'C-028': 'incoming/2026-09-23_rheinwerk_analytics_services_agreement_draft.md', 'C-029': 'incoming/2026-09-24_sunrise_foods_sow2_draft.md',
    'C-035': 'incoming/2026-09-24_datavane_strategic_partnership_agreement_draft.md', 'C-036': 'incoming/2026-09-25_finserve_capital_mutual_nda_draft.md',
    'C-037': 'incoming/2026-09-26_kriti_data_labs_subcontractor_agreement_draft.md', 'C-038': 'incoming/2026-09-27_loopmart_mutual_nda_draft.md',
    'C-040': 'incoming/2026-09-27_marcus_reed_contractor_agreement_draft.md', 'C-047': 'incoming/2026-09-27_daniel_ortiz_contractor_agreement_draft.md',
    'C-048': 'incoming/2026-09-27_daniel_ortiz_nda_draft.md',
}
rcount = {}
for r in register:
    rcount[r['contract_id']] = rcount.get(r['contract_id'], 0) + 1

def base_type(t):
    t = (t or '').strip()
    return t.split(' ')[0].split('(')[0] if t else ''

contracts = []
with open(os.path.join(DATA, 'contract_tracker.csv'), encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        cid = row['contract_id']
        contracts.append({
            "id": cid, "counterparty": row['counterparty'], "type": row['doc_type'], "entity": row['atliq_entity'],
            "country": (row['client_country'] or '').replace('?', '').strip(), "requested_by": row['requested_by'],
            "received": row['received_date'], "signed": row['signed_date'], "expiry": row['expiry_date'],
            "value": int(row['value_usd']) if (row['value_usd'] or '').lstrip('-').isdigit() else None,
            "status": row['status'] or 'Unknown', "notes": row['notes'],
            "file": ('samples/' + files[cid]) if cid in files else None,
            "restrictions": rcount.get(cid, 0),
        })
with open(os.path.join(DATA, 'contracts.json'), 'w', encoding='utf-8') as f:
    json.dump(contracts, f, indent=1, ensure_ascii=False)

import shutil
for name in ('register.json', 'benchmark.json', 'principles.json', 'contracts.json'):
    shutil.copyfile(os.path.join(DATA, name), os.path.join(PUB, name))
print('register', len(register), 'contracts', len(contracts), 'with files', sum(1 for c in contracts if c['file']))

# ---------------------------------------------------------------- verify every register quote is in its source file
def norm(s):
    s = re.sub(r'[*`_]', '', s)
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return re.sub(r'\s+', ' ', s).strip().lower()

bad = 0
for r in register:
    src = open(os.path.join(ROOT, 'public', r['file']), encoding='utf-8').read()
    if norm(r['quote']) not in norm(src):
        bad += 1
        print('QUOTE NOT FOUND', r['id'], r['file'])
    if r.get('waiver_file'):
        w = open(os.path.join(ROOT, 'public', r['waiver_file']), encoding='utf-8').read()
        if norm(r['waiver_quote']) not in norm(w):
            bad += 1
            print('WAIVER QUOTE NOT FOUND', r['id'])
print('quote check: all verified' if not bad else '%d problems' % bad)

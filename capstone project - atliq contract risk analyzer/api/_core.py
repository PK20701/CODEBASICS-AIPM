"""AtliQ Contract Risk Analyzer: review engine.

Design: rules and code decide everything that can be checked with a rule; the language model
only reads unstructured contract text. Every finding must carry a quote that is verified
against the source text in code. Nothing here signs, sends or approves anything.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIRS = [os.path.join(HERE, '..', 'data'), os.path.join(HERE, '..', 'public', 'data'), os.path.join(HERE, 'data')]

SEV_ORDER = {'Serious': 0, 'Negotiable': 1, 'Minor': 2}


# ----------------------------------------------------------------------------- data
def load_json(name):
    for d in DATA_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f)
    raise FileNotFoundError(name)


def register():
    return load_json('register.json')


def benchmark():
    return load_json('benchmark.json')


def principles():
    return load_json('principles.json')


# ----------------------------------------------------------------------------- text helpers
def norm(s):
    s = re.sub(r'[*`_#>|]', '', s or '')
    s = (s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
         .replace('–', '-').replace('—', '-').replace(' ', ' '))
    s = s.replace('"', '')  # models often drop the quote marks around defined terms
    return re.sub(r'\s+', ' ', s).strip().lower()


def verify_quote(quote, source):
    """True if the quote really appears in the source (whitespace, case and markdown ignored).
    A quote written with ellipses is checked piece by piece, in order."""
    q = norm(quote).strip(' "\'')
    if len(q) < 8:
        return False
    src = norm(source)
    if q in src:
        return True
    parts = [p.strip(' "\'.,;') for p in re.split(r'…|\.\.\.', q)]
    parts = [p for p in parts if len(p) >= 12]
    if len(parts) >= 2 or (len(parts) == 1 and parts[0] != q):
        pos = 0
        for p in parts:
            i = src.find(p, pos)
            if i < 0:
                return False
            pos = i + len(p)
        return True
    return False


def strip_md(s):
    return re.sub(r'\*\*|__|`', '', s)


# ----------------------------------------------------------------------------- clause segmentation
CLAUSE_RE = re.compile(r'^\s*(\d{1,2}(?:\.\d{1,2})+)\.?\s+(.*\S)\s*$')
HEAD_RE = re.compile(r'^\s*(?:#{1,4}\s*)?(\d{1,2})\.\s+([A-Z][A-Za-z0-9 ,&;:\'\-/()]{2,80})\s*$')
SCHED_RE = re.compile(r'^\s*(?:#{1,4}\s*)?(ANNEXURE|EXHIBIT|SCHEDULE|APPENDIX)\b(.*)$', re.I)


def segment(text):
    """Split a contract into clauses. Returns list of {id, section, heading, text}."""
    lines = (text or '').replace('\r', '').split('\n')
    clauses, cur, heading, section = [], None, '', ''
    sched = None

    def flush():
        nonlocal cur
        if cur and len(cur['text'].strip()) > 0:
            clauses.append(cur)
        cur = None

    for ln in lines:
        s = ln.strip()
        if not s or s.startswith('*(') or s == '---':
            continue
        ms = SCHED_RE.match(s)
        if ms and not CLAUSE_RE.match(s):
            flush()
            sched = {'id': 'S%d' % (len([c for c in clauses if c['id'].startswith('S')]) + 1), 'section': s.strip('# ').strip(),
                     'heading': s.strip('# ').strip(), 'text': ''}
            cur = sched
            continue
        if sched is not None and cur is sched:
            cur['text'] += ('\n' if cur['text'] else '') + strip_md(s)
            continue
        mh = HEAD_RE.match(s)
        if mh and not CLAUSE_RE.match(s):
            flush()
            heading = mh.group(2).strip().title()
            section = mh.group(1)
            continue
        mc = CLAUSE_RE.match(s)
        if mc:
            flush()
            cur = {'id': mc.group(1), 'section': section or mc.group(1).split('.')[0], 'heading': heading, 'text': strip_md(mc.group(2))}
            continue
        if cur is not None:
            cur['text'] += '\n' + strip_md(s)
    flush()
    numbered = [c for c in clauses if not c['id'].startswith('S')]
    if len(numbered) < 4:
        # fall back to paragraphs for text without clause numbers
        paras = [strip_md(p.strip()) for p in re.split(r'\n\s*\n', text or '') if len(p.strip()) >= 40]
        clauses = [{'id': 'P%d' % (i + 1), 'section': '', 'heading': '', 'text': p} for i, p in enumerate(paras)]
    return clauses


def make_batches(clauses, max_chars=6500, max_items=16):
    batches, cur, size = [], [], 0
    for c in clauses:
        n = len(c['text']) + 40
        if cur and (size + n > max_chars or len(cur) >= max_items):
            batches.append(cur)
            cur, size = [], 0
        cur.append(c)
        size += n
    if cur:
        batches.append(cur)
    return batches


# ----------------------------------------------------------------------------- model client (Gemini first, Groq as fallback)
class LLMError(Exception):
    pass


class QuotaError(LLMError):
    pass


USAGE = {'calls': 0, 'in': 0, 'out': 0}


def _post(url, headers, body, timeout=55):
    headers = dict(headers, **{'User-Agent': 'atliq-contract-risk-analyzer/1.0', 'Accept': 'application/json'})
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            detail = e.read().decode('utf-8')[:400]
        except Exception:
            pass
        if e.code in (429, 503, 500, 502, 504) or 'RESOURCE_EXHAUSTED' in detail or 'quota' in detail.lower():
            raise QuotaError('HTTP %s %s' % (e.code, detail[:200]))
        raise LLMError('HTTP %s %s' % (e.code, detail[:300]))
    except (urllib.error.URLError, TimeoutError) as e:
        raise QuotaError('network/timeout: %s' % e)


def parse_json(text):
    """Parse the model's JSON. Repairs trailing commas; anything else unparseable raises LLMError so the caller can retry or fall back."""
    t = (text or '').strip()
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', t, flags=re.S).strip()
    candidates = [t]
    a, b = t.find('{'), t.rfind('}')
    if a >= 0 and b > a:
        candidates.append(t[a:b + 1])
    for c in list(candidates):
        candidates.append(re.sub(r',\s*([}\]])', r'\1', c))
    for c in candidates:
        try:
            return json.loads(c)
        except Exception:
            continue
    raise LLMError('model did not return valid JSON')


GEMINI_ROTATION = 'gemini-flash-lite-latest,gemini-3.1-flash-lite,gemini-3-flash-preview,gemini-3.6-flash'


def gemini_json(system, user, tier):
    """Free-tier limits are per model, so try several Gemini models before giving up to the backup provider."""
    key = os.environ.get('GEMINI_API_KEY')
    if not key or os.environ.get('FORCE_GEMINI_FAIL'):
        raise QuotaError('gemini unavailable')
    first = os.environ.get('GEMINI_MODEL_FAST' if tier == 'fast' else 'GEMINI_MODEL_SMART')
    models = ([first] if first else []) + [m for m in os.environ.get('GEMINI_ROTATION', GEMINI_ROTATION).split(',') if m and m != first]
    last = None
    for i, m in enumerate(models):
        try:
            return _gemini_once(system, user, m, key, 30 if i else 45)
        except QuotaError as e:
            last = e
    raise QuotaError('all gemini models busy: %s' % str(last)[:160])


def _gemini_once(system, user, model, key, timeout):
    url = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (model, key)
    body = {'systemInstruction': {'parts': [{'text': system}]},
            'contents': [{'role': 'user', 'parts': [{'text': user}]}],
            'generationConfig': {'temperature': 0.1, 'responseMimeType': 'application/json'}}
    t0 = time.time()
    d = _post(url, {'Content-Type': 'application/json'}, body, timeout)
    try:
        text = ''.join(p.get('text', '') for p in d['candidates'][0]['content']['parts'])
    except Exception:
        raise LLMError('empty gemini response: %s' % json.dumps(d)[:200])
    u = d.get('usageMetadata', {})
    return parse_json(text), {'provider': 'gemini', 'model': model, 'ms': int((time.time() - t0) * 1000),
                              'in': u.get('promptTokenCount', 0), 'out': u.get('candidatesTokenCount', 0)}


GROQ_ROTATION = 'openai/gpt-oss-120b,qwen/qwen3.8-27b,openai/gpt-oss-20b'


def groq_json(system, user, tier, max_chars=22000):
    """Backup provider. Each Groq model has its own tokens-per-minute budget, so rotate through several."""
    key = os.environ.get('GROQ_API_KEY')
    if not key:
        raise LLMError('no fallback model configured')
    first = os.environ.get('GROQ_MODEL')
    models = ([first] if first else []) + [m for m in os.environ.get('GROQ_ROTATION', GROQ_ROTATION).split(',') if m and m != first]
    if len(user) > max_chars:
        user = user[:max_chars] + ' [truncated for the backup model]'
    last = None
    for attempt in range(2):
        for model in models:
            try:
                return _groq_once(system, user, model, key)
            except QuotaError as e:
                last = e
        m = re.search(r'try again in ([0-9.]+)s', str(last))
        if attempt or not m or float(m.group(1)) > 15:
            break
        time.sleep(float(m.group(1)) + 0.5)
    raise last


def _groq_once(system, user, model, key):
    url = 'https://api.groq.com/openai/v1/chat/completions'
    body = {'model': model, 'temperature': 0.1, 'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}
    t0 = time.time()
    d = _post(url, {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key}, body)
    text = d['choices'][0]['message']['content']
    text = re.sub(r'<think>.*?</think>', '', text or '', flags=re.S)
    u = d.get('usage', {})
    return parse_json(text), {'provider': 'groq', 'model': model, 'ms': int((time.time() - t0) * 1000),
                              'in': u.get('prompt_tokens', 0), 'out': u.get('completion_tokens', 0)}


def llm_json(system, user, tier='smart'):
    """Gemini first; on rate limit or outage switch to Groq. Returns (object, meta)."""
    notes = []
    try:
        obj, meta = gemini_json(system, user, tier)
    except QuotaError as e:
        notes.append('gemini: %s' % str(e)[:120])
        obj, meta = groq_json(system, user, tier)
        meta['fallback'] = True
        meta['notes'] = notes
    except LLMError as e:
        # malformed output: one retry on the same provider, then fall back
        try:
            obj, meta = gemini_json(system, user + '\n\nReturn valid JSON only.', tier)
            meta['retried'] = True
        except LLMError:
            notes.append('gemini: %s' % str(e)[:120])
            obj, meta = groq_json(system, user, tier)
            meta['fallback'] = True
            meta['notes'] = notes
    if isinstance(obj, list):
        obj = {'findings': obj, 'items': obj, 'matches': obj}
    if not isinstance(obj, dict):
        obj = {}
    USAGE['calls'] += 1
    USAGE['in'] += meta.get('in', 0)
    USAGE['out'] += meta.get('out', 0)
    return obj, meta


# ----------------------------------------------------------------------------- prompts
SYS_BASE = ("You are a contract review assistant for AtliQ Technologies, an IT services company with no legal team. "
            "You help the founder decide faster. You never give legal advice, never say a contract is safe to sign, "
            "and never invent text. Quote only text that really appears in the material you are given. "
            "When you are unsure, say so. Answer with JSON only.")

EXTRACT_PROMPT = """Read this contract and extract its key details. Use null when something is not stated. Do not guess.
Return JSON with exactly these keys:
{{
 "doc_type": "MSA|SOW|NDA|BAA|DPA|Partnership|Amendment|Other",
 "title": "short title",
 "counterparty": "the other party (not AtliQ)",
 "client_country": "country of the other party, or null",
 "client_industry": "for example hospitality, healthcare, retail, banking, logistics, software, other",
 "atliq_entity": "Pvt Ltd" | "Inc" | "Unknown",
 "effective_date": "YYYY-MM-DD or null",
 "term_months": number or null,
 "end_date": "YYYY-MM-DD or null",
 "governing_law": "text or null",
 "courts_or_seat": "text or null",
 "governing_law_source": {{"clause_id": "e.g. 17.1", "quote": "exact text that states the governing law and the courts or arbitration seat"}},
 "parties_quote": "exact text of the paragraph that names the parties",
 "payment_source": {{"clause_id": "x", "quote": "exact text of the payment-days clause"}},
 "currency": "USD|INR|EUR|AED|SAR|GBP|other",
 "total_value": number or null,
 "annual_fee": number or null,
 "payment_days": number or null,
 "services_summary": "max 25 words",
 "regions_of_service": ["countries where the client's business or its end customers are located (NOT where AtliQ staff sit)"],
 "liability_cap": {{"kind": "multiple_of_fees|fixed_amount|unlimited|none_stated|other", "multiple": number or null, "amount": number or null, "basis": "text", "clause_id": "e.g. 12.2", "quote": "exact text"}},
 "delay_penalty": {{"present": true|false, "per": "day|week|none", "rate_percent": number or null, "capped": true|false|null, "excludes_client_delay": true|false|null, "clause_id": "e.g. 9.1", "quote": "exact text"}},
 "mutual_confidentiality": true|false|null,
 "one_sided_note": "if titled mutual but obligations bind one party only, say who and how, else null",
 "handles_phi": true|false,
 "handles_eu_personal_data": true|false,
 "mentions_baa_or_dpa": "text of any reference to a BAA or DPA, else null",
 "insurance_requirements": [{{"type": "cyber|liability|e&o|other", "amount_usd": number, "clause_id": "x", "quote": "exact text"}}],
 "rates": [{{"role": "text", "rate": number, "currency": "USD", "unit": "hour|day|month", "clause_id": "x"}}],
 "restrictive_covenants": [{{"type": "non_compete|exclusivity|mfn_pricing|non_solicit|ip_assignment|data_location|other", "who_is_bound": "AtliQ|client|both", "summary": "max 30 words", "restricted_activity": "text", "customers": "who or what kind of customer the restriction covers, e.g. any other hotel group", "geography": ["..."], "clause_id": "x", "quote": "exact text", "duration_basis": "term|term_plus_months|fixed_months|perpetual|unknown", "months_after_term": number or null}}]
}}
Contract text:
\"\"\"
{text}
\"\"\"
"""

ANALYZE_PROMPT = """Review ONLY these clauses of a contract that AtliQ ({entity}) is asked to sign with {counterparty} ({doctype}).
Context: annual fee {annual_fee}, total value {total_value}, term {term} months, payment {payment} days, governing law {law}.
You only see some of the clauses. Never say something is missing or not specified; flag only what is present in the clauses shown. Liability caps, delay penalties, payment days and governing law are checked separately in code, so skip them unless a clause is unusual in another way. Do not list clauses that are standard or already in line with the principles (for example mutual indemnity, a 1x cap, US governing law for AtliQ Inc); list only real risks or deviations, each with a title.

AtliQ's principles (a preference, not a rule; every contract is judged on its own context):
{principles}

What AtliQ's past contracts look like (benchmark):
{benchmark}

Look for: uncapped or disproportionate liability, delay penalties that ignore client-caused delay or outside events, indemnity covering the other side's own negligence, payment later than 45 days or pay-when-paid, termination that does not pay AtliQ for work done, unilateral changes, auto-renewal, IP assignment of AtliQ's pre-existing tools, one-sided confidentiality or covenants (even if titled mutual), exclusivity or non-compete or most-favoured pricing, data location limits, anything that looks unusual.
Over-flag rather than miss: a false alarm is cheap, a missed clause is expensive. When a clause is fine, do not flag it.

Return JSON: {{"reviewed_ids": [every clause id you read], "findings": [{{"clause_id": "x", "topic": "liability|delay_penalty|indemnity|payment|governing_law|ip|termination|confidentiality|mutuality|exclusivity|non_compete|mfn|data_protection|insurance|assignment|amendment|renewal|other", "severity": "Serious|Negotiable|Minor", "title": "max 10 words", "quote": "exact words copied from that clause, max 40 words", "why": "max 30 words, why it matters to AtliQ", "comparison": "max 25 words: how it compares with the principles or past contracts", "unsure": true|false}}]}}

Clauses:
{clauses}
"""

NOTES_PROMPT = """These are notes or a transcript of informal discussions (calls, chats) between AtliQ and a client. They are NOT part of the contract and are not binding, but they matter.
Extract every commitment, promise or change of terms mentioned (price, discount, scope, timeline, payment terms, exclusivity, staffing, anything else).
For each, say whether the contract below reflects it.

Contract key terms: {terms}

Register of AtliQ's past commitments (ids and summaries):
{register}

Return JSON: {{"items": [{{"quote": "exact words copied from the notes, max 40 words", "kind": "price|scope|timeline|payment|exclusivity|other", "summary": "max 25 words", "contract_reflects": "yes|no|unclear", "register_conflict": "register id like R-02 or null", "severity": "Serious|Negotiable|Minor", "unsure": true|false}}]}}

Notes:
\"\"\"
{notes}
\"\"\"
"""

CONFLICT_PROMPT = """Decide which of AtliQ's past commitments could collide with this new deal. Be generous: say "possible" when unsure.

New deal: client {counterparty} ({industry}, {country}); AtliQ entity {entity}; services: {services}; regions: {regions}; text hints: {hints}

Past commitments (register):
{register}

Return JSON: {{"matches": [{{"register_id": "R-01", "relevance": "likely|possible", "reason": "max 30 words: why it applies or might apply to this deal"}}]}}
Only include entries that likely or possibly apply (same industry, region, activity, rates, tools or data). Return an empty list if none.
"""


# ----------------------------------------------------------------------------- extraction and checks
def clamp_text(text, n=110000):
    return text if len(text) <= n else text[:n]


def clean_details(d):
    """Models sometimes return a list or null where a record is expected. Make the shapes safe."""
    d = dict(d or {})
    for k in ('liability_cap', 'delay_penalty', 'governing_law_source', 'payment_source'):
        v = d.get(k)
        if isinstance(v, list):
            v = next((x for x in v if isinstance(x, dict)), {})
        d[k] = v if isinstance(v, dict) else {}
    for k in ('regions_of_service', 'insurance_requirements', 'rates', 'restrictive_covenants'):
        v = d.get(k)
        d[k] = [x for x in v if (isinstance(x, dict) if k != 'regions_of_service' else isinstance(x, str))] if isinstance(v, list) else []
    for k in ('term_months', 'total_value', 'annual_fee', 'payment_days'):
        try:
            d[k] = float(d[k]) if d.get(k) not in (None, '') else None
        except (TypeError, ValueError):
            d[k] = None
    for k in ('term_months', 'payment_days'):
        if d.get(k) is not None:
            d[k] = int(d[k])
    return d


def action_extract(contract_text, **_):
    obj, meta = llm_json(SYS_BASE, EXTRACT_PROMPT.format(text=clamp_text(contract_text)), 'fast')
    obj = clean_details(obj)
    return {'details': obj, 'meta': meta, 'clauses': len(segment(contract_text))}


def fmt_money(v, cur='USD'):
    if v is None:
        return 'n/a'
    return '%s %s' % (cur, '{:,.0f}'.format(v))


def annual_fee_of(d):
    if d.get('annual_fee'):
        return d['annual_fee']
    if d.get('total_value') and d.get('term_months'):
        return d['total_value'] / max(d['term_months'] / 12.0, 1.0)
    return d.get('total_value')


def liability_ratio(d):
    """Returns (multiple_of_annual_fee or None, text, severity or None)."""
    lc = d.get('liability_cap') or {}
    kind = lc.get('kind')
    bm = benchmark()['liability_cap_multiple_of_fees']
    top = bm.get('max_seen', 2.0)
    if kind == 'unlimited':
        return None, 'unlimited', 'Serious'
    fee = annual_fee_of(d)
    mult = None
    if kind == 'multiple_of_fees' and lc.get('multiple') is not None:
        mult = float(lc['multiple'])
    elif kind == 'fixed_amount' and lc.get('amount') and fee:
        mult = float(lc['amount']) / float(fee)
    if mult is None:
        return None, 'not stated', ('Negotiable' if kind == 'none_stated' else None)
    if mult <= top:
        sev = 'Minor' if mult > bm.get('typical', 1.0) * 1.01 else None
    elif mult <= 2 * top:
        sev = 'Negotiable'
    else:
        sev = 'Serious'
    return mult, '%.1fx annual fee' % mult, sev


US_STATES = ['alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado', 'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
             'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
             'mississippi', 'missouri', 'montana', 'nebraska', 'nevada', 'new hampshire', 'new jersey', 'new mexico', 'new york', 'north carolina',
             'north dakota', 'ohio', 'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina', 'south dakota', 'tennessee', 'texas',
             'utah', 'vermont', 'virginia', 'washington', 'west virginia', 'wisconsin', 'wyoming', 'united states', 'u.s.', 'usa', 'federal', 'new jersey']


def is_us(s):
    s = (s or '').lower()
    if re.search(r'\b(england|english|london|singapore|india|uae|dubai|difc|germany|german|munich|saudi|ireland|scotland|hong kong)\b', s) and not any(st in s for st in ('united states', 'u.s.')):
        return False
    return any(h in s for h in US_STATES) or s.strip() in ('us', 'usa', 'u.s.')


FOREIGN = r'\b(england|english|london|singapore|india|indian|mumbai|pune|delhi|bengaluru|bangalore|uae|dubai|difc|abu dhabi|germany|german|munich|frankfurt|saudi|riyadh|ireland|dublin|scotland|hong kong|canada|ontario|toronto|australia|sydney|paris|france|netherlands|amsterdam|icc|lcia|siac|hkiac)\b'


def is_foreign(s):
    s = (s or '').lower()
    return bool(re.search(FOREIGN, s)) and not any(x in s for x in ('united states', 'u.s.', 'new york', 'delaware', 'new jersey'))


def locate(text, keywords, maxlen=320):
    """Find the first sentence in the contract that contains any keyword. Returns (clause_id, sentence) or (None, None).
    Used when the model's own quote cannot be verified, so a rule finding always points at real text."""
    for c in segment(text):
        for sent in re.split(r'(?<=[.;])\s+', c['text']):
            low = sent.lower()
            if any(k in low for k in keywords) and len(sent) >= 25:
                return c['id'], sent.strip()[:maxlen]
    return None, None


def rules_findings(details, text):
    """Deterministic checks. No model involved."""
    d = details or {}
    out = []

    def add(topic, sev, title, why, comparison, clause_id=None, quote=None, source='rule', absence=False):
        verified = bool(quote) and verify_quote(quote, text)
        out.append({'source': source, 'topic': topic, 'severity': sev, 'title': title, 'why': why, 'comparison': comparison,
                    'clause_id': clause_id, 'quote': quote if verified else None, 'verified': verified or absence,
                    'unsure': not (verified or absence), 'absence': absence})

    def src(obj, kws):
        obj = obj or {}
        q = obj.get('quote')
        if q and verify_quote(q, text):
            return obj.get('clause_id'), q
        return locate(text, kws)

    entity, law, country = d.get('atliq_entity'), d.get('governing_law') or '', d.get('client_country') or ''
    courts = (d.get('courts_or_seat') or '')
    gsrc = d.get('governing_law_source') or {}
    gq, gc = gsrc.get('quote'), gsrc.get('clause_id')
    if not (gq and verify_quote(gq, text)):
        gc2, gq2 = locate(text, ['arbitration', 'courts of', 'courts at', 'courts located', 'exclusive jurisdiction', 'governed by'] if courts else ['governed by', 'governing law', 'laws of'])
        if gq2:
            gc, gq = gc2, gq2
    pq = d.get('parties_quote')
    if not (pq and verify_quote(pq, text)):
        pq = None
        for ln in text.split('\n'):
            if re.search(r'(?i)atliq (inc|technologies)', ln) and len(ln) > 40:
                pq = strip_md(ln.strip())[:300]
                break
    if entity == 'Inc':
        if law and not is_us(law):
            add('governing_law', 'Serious', 'US entity under non-US law (%s)' % law, 'AtliQ Inc has no presence outside the US; disputes would be fought abroad.',
                'Principle: US law for AtliQ Inc. Brightwater signed this way and it cost $23k.', gc, gq)
        elif courts and is_foreign(courts):
            add('governing_law', 'Serious', 'US entity with courts or arbitration outside the US (%s)' % courts, 'AtliQ Inc has no presence abroad; a dispute would be run in a foreign forum.',
                'Principle: US law and US courts for AtliQ Inc.', gc, gq)
    if entity == 'Pvt Ltd' and law and 'india' not in law.lower():
        add('governing_law', 'Negotiable', 'Indian entity under non-Indian law (%s)' % law, 'Disputes would be fought under foreign law and courts.',
            'Principle: India for AtliQ Pvt Ltd. Past exceptions (Al Noor DIFC, Northwind English law) were deliberate.', gc, gq)
    if entity == 'Inc' and country and not is_us(country):
        add('governing_law', 'Serious', 'AtliQ Inc named for a non-US client (%s)' % country, 'AtliQ Inc serves US clients only; the entity decides tax, invoicing and bank account.',
            'Entity sheet: clients outside the US contract with AtliQ Technologies Pvt Ltd.', 'Parties', pq)
    if entity == 'Pvt Ltd' and country and is_us(country):
        add('governing_law', 'Serious', 'AtliQ Pvt Ltd named for a US client', 'US clients contract with AtliQ Inc.', 'Entity sheet: AtliQ Inc serves the United States only.', 'Parties', pq)

    mult, txt, sev = liability_ratio(d)
    lc = d.get('liability_cap') or {}
    if sev and not (txt == 'not stated' and (d.get('doc_type') or '').upper() in ('NDA', 'MUTUAL NDA', 'BAA', 'DPA')):
        add('liability', sev, 'Liability %s' % ('is unlimited' if txt == 'unlimited' else ('cap is %s' % txt if mult else 'cap not stated')),
            'The cap is out of line with the contract value.' if mult else 'No limit protects AtliQ.',
            'Past contracts: 8 of 10 cap liability at about 1x fees; highest seen 2x.', *src(lc, ['aggregate liability', 'total liability', 'liability shall not exceed', 'unlimited', 'without limitation']))

    dp = d.get('delay_penalty') or {}
    if dp.get('present'):
        if dp.get('capped') is False or dp.get('excludes_client_delay') is False:
            what = []
            if dp.get('capped') is False:
                what.append('no cap')
            if dp.get('excludes_client_delay') is False:
                what.append('no exclusion for client-caused delay')
            add('delay_penalty', 'Serious', 'Delay penalty with ' + ' and '.join(what),
                'AtliQ could pay for delays it did not cause (Brightwater).', 'Past contracts cap penalties at 5% of the milestone and exclude client delay (3 of 3).',
                *src(dp, ['liquidated damages', 'delay']))

    pdays = d.get('payment_days')
    if pdays and pdays > 45:
        ps = d.get('payment_source') or {}
        if not (ps.get('quote') and verify_quote(ps['quote'], text)):
            pc2, pq2 = locate(text, ['days of receipt', 'days of the invoice', 'days after receipt', 'days from receipt', 'payable within', 'pay each', 'net '])
            ps = {'clause_id': pc2, 'quote': pq2}
        add('payment', 'Serious' if pdays > 90 else 'Negotiable', 'Payment in %d days' % pdays, 'Long payment terms hurt cash flow.', 'Principle: 30 days, 45 at most.',
            ps.get('clause_id'), ps.get('quote'))

    # documents needed
    txt_all = text.lower()
    if d.get('handles_phi') and not d.get('mentions_baa_or_dpa') and 'business associate' not in txt_all:
        add('data_protection', 'Serious', 'Health data but no BAA referenced', 'A HIPAA Business Associate Agreement is required before patient data moves.',
            'Healthcare deals need an NDA, a BAA and the services contract (CareBridge, Harrington).', absence=True)
    if d.get('handles_eu_personal_data') and not d.get('mentions_baa_or_dpa') and 'data processing' not in txt_all:
        add('data_protection', 'Negotiable', 'EU personal data but no DPA referenced', 'A GDPR data processing agreement is usually needed.', 'European work with personal data needs a DPA.', absence=True)

    for ins in d.get('insurance_requirements') or []:
        amt = ins.get('amount_usd') or 0
        if (ins.get('type') or '').lower().startswith('cyber') and amt > 1_000_000:
            add('insurance', 'Serious', 'Cyber insurance of $%s required; AtliQ holds $1M' % '{:,.0f}'.format(amt),
                'AtliQ would be in breach on signing.', 'AtliQ facts: cyber cover is $1,000,000.', ins.get('clause_id'), ins.get('quote'))
    return out


# ----------------------------------------------------------------------------- register matching
RATE_CARD = [('senior', 'data engineer', 85.0), ('data engineer', None, 62.0), ('bi developer', None, 58.0)]


def reg_status(r, today=None):
    today = today or date.today().isoformat()
    if r.get('end') is None:
        return 'active'
    return 'expired' if r['end'] < today else 'active'


GEO_NAMES = {'uae': ['uae', 'united arab emirates', 'dubai', 'abu dhabi'], 'saudi arabia': ['saudi', 'riyadh', 'jeddah'], 'qatar': ['qatar', 'doha'],
             'kuwait': ['kuwait'], 'bahrain': ['bahrain'], 'oman': ['oman', 'muscat'], 'india': ['india'], 'united states': ['united states', 'usa', 'u.s.']}
GCC_WORDS = ['uae', 'united arab emirates', 'dubai', 'abu dhabi', 'saudi', 'riyadh', 'qatar', 'doha', 'kuwait', 'bahrain', 'oman', 'muscat', 'gcc', 'gulf']


def geo_match(r, d):
    """Does the deal's client country or service regions fall inside the restriction's geography?"""
    geos = [g.lower() for g in r['scope'].get('geography', [])]
    if 'worldwide' in geos:
        return True
    deal = ' '.join([(d.get('client_country') or ''), ' '.join(d.get('regions_of_service') or [])]).lower()
    for g in geos:
        for n in GEO_NAMES.get(g, [g]):
            if n in deal:
                return True
    return False


def keyword_conflicts(details, text, reg=None):
    """Deterministic matching on register fields and keywords. Also the fallback when no model is available."""
    d = details or {}
    hay = ' '.join([text.lower(), (d.get('services_summary') or '').lower()])  # not the model's industry label: it can be wrong
    out = []
    for r in (reg if reg is not None else register()):
        why, rel = None, None
        if r['type'] in ('non_compete', 'exclusivity'):
            sc = r['scope'].get('customers', '').lower()
            hotel = any(k in hay for k in ('hotel', 'hospitality', 'resort', 'revenue management', 'revenue-management'))
            if 'hospitality' in sc and hotel:
                if geo_match(r, d):
                    why, rel = 'Hospitality client in the restricted region, and the services are of the restricted kind.', 'likely'
                elif any(k in hay for k in GCC_WORDS):
                    why, rel = 'Hospitality client; the text mentions the Gulf, so a restricted-region property may be covered. Confirm the scope.', 'possible'
                else:
                    why, rel = 'Hospitality client; the region is outside the restriction as stated, but confirm that no property in the GCC is included.', 'possible'
            elif 'online travel' in sc and 'travel' in hay and 'booking' in hay and geo_match(r, d):
                why, rel = 'Travel-booking software for an online travel agency in India.', 'likely'
            elif 'competing' in r['restricted_activity'].lower() and any(k in hay for k in ('snowflake', 'databricks', 'bigquery', 'redshift', 'lakehouse')):
                if geo_match(r, d):
                    why, rel = 'Work on a competing data platform for a client in India or the GCC.', 'likely'
                else:
                    why, rel = 'The deal involves a data platform; the client is outside India and the GCC, so this is probably allowed (clause 7.3), but confirm no partner fee is involved.', 'possible'
        if why is None and str(r['id']).startswith('N-') and r['type'] in ('non_compete', 'exclusivity'):
            why, rel = new_entry_match(r, d, hay)
        if r['type'] == 'ip_assignment' and 'pipekit' in hay and why is None:
            why, rel = 'The deal reuses PipeKit, which passed to Northwind in the delivered configuration.', 'likely'
        elif r['type'] == 'mfn_pricing':
            for rate in (d.get('rates') or []):
                role = (rate.get('role') or '').lower()
                val, unit = rate.get('rate'), (rate.get('unit') or 'hour').lower()
                if val is None or unit != 'hour':
                    continue
                for a_, b_, card in RATE_CARD:
                    if a_ in role and (b_ is None or b_ in role) and val < card:
                        why, rel = 'Hourly rate %s for "%s" is below Crestline\'s $%.0f card, which may trigger a retroactive credit.' % (val, rate.get('role'), card), 'likely'
                        break
                if why:
                    break
        if why:
            out.append({'register_id': r['id'], 'relevance': rel, 'reason': why})
    return out


def action_conflicts(details, contract_text, extra_register=None, exclude_contract=None, **_):
    reg = register() + sanitize_extra(extra_register, exclude_contract)
    by_id = {r['id']: r for r in reg}
    kw = keyword_conflicts(details, contract_text, reg)
    d = details or {}
    compact = [{'id': r['id'], 'who': r['counterparty'], 'type': r['type'], 'activity': r['restricted_activity'], 'scope': r['scope'], 'ends': r.get('end')} for r in reg]
    meta, matches = None, []
    try:
        obj, meta = llm_json(SYS_BASE, CONFLICT_PROMPT.format(
            counterparty=d.get('counterparty'), industry=d.get('client_industry'), country=d.get('client_country'), entity=d.get('atliq_entity'),
            services=d.get('services_summary'), regions=', '.join(d.get('regions_of_service') or []),
            hints=', '.join(sorted(set(x.lower() for x in re.findall(r'(?i)\b(hotel|hospitality|resort|pipekit|snowflake|databricks|lakehouse|travel|revenue management)\b', contract_text)))[:12]),
            register=json.dumps(compact)), 'smart')
        matches = [m for m in obj.get('matches', []) if m.get('register_id') in by_id]
    except LLMError as e:
        meta = {'provider': 'none', 'error': str(e)[:160]}
    # Rules decide how strong a match is. The model can add possible matches but cannot turn a
    # region mismatch into a "likely" conflict.
    ruled = {k['register_id']: k for k in kw}
    final = {}
    for m in matches:
        r = by_id[m['register_id']]
        rel = m.get('relevance', 'possible')
        if r['type'] in ('non_compete', 'exclusivity') and not geo_match(r, d):
            rel = 'possible'
        if m['register_id'] in ruled and ruled[m['register_id']]['relevance'] == 'likely':
            rel = 'likely'
        final[m['register_id']] = {'register_id': m['register_id'], 'relevance': rel, 'reason': m.get('reason') or ruled.get(m['register_id'], {}).get('reason', '')}
    for k in kw:
        if k['register_id'] not in final:
            final[k['register_id']] = dict(k)
    has_rates = any(x.get('rate') for x in (d.get('rates') or []))
    low = (contract_text or '').lower()
    for rid in list(final):
        t_ = by_id[rid]['type']
        if rid in ruled:
            continue
        if t_ in ('non_compete', 'exclusivity') and not geo_match(by_id[rid], d):
            del final[rid]
        elif t_ == 'mfn_pricing':  # rate comparison is done by rules above; a model-only hunch adds noise
            del final[rid]
        elif t_ == 'ip_assignment' and 'pipekit' not in low and 'northwind' not in low:
            del final[rid]
    out = []
    for rid, m in final.items():
        r = by_id[rid]
        status = reg_status(r)
        rel = m['relevance']
        if status == 'expired':
            sev = 'Minor'
        elif r['type'] in ('non_compete', 'exclusivity', 'mfn_pricing', 'ip_assignment') and rel == 'likely':
            sev = 'Serious'
        else:
            sev = 'Negotiable' if rel == 'likely' else 'Minor'
        out.append({'source': 'register', 'topic': r['type'], 'severity': sev,
                    'title': ('%s: %s' % (r['counterparty'], r['restricted_activity'])) if status == 'active' else 'Expired restriction: %s (%s)' % (r['counterparty'], r['restricted_activity']),
                    'why': m.get('reason', ''), 'comparison': r['takeaway'], 'clause_id': r['clause'], 'quote': r['quote'], 'verified': True, 'unsure': rel != 'likely',
                    'register_id': r['id'], 'register_status': status, 'register_end': r.get('end'), 'register_file': r['file'],
                    'register_counterparty': r['counterparty'], 'exception': r.get('exception'), 'relevance': rel})
    return {'conflicts': out, 'meta': meta, 'checked': len(reg), 'checked_contracts': len({r['contract_id'] for r in reg})}


# ----------------------------------------------------------------------------- clause analysis
def principles_text():
    return '\n'.join('- %s' % p['text'] for p in principles())


def benchmark_text():
    b = benchmark()
    return '\n'.join('- %s' % v for v in (b['liability_cap_multiple_of_fees']['summary'], b['delay_penalties']['summary'], b['payment_days']['summary'],
                                          b['governing_law']['summary'], b['ip']['summary'], b['non_solicit']['summary']))


def action_analyze(clauses, details, full_text='', **_):
    d = details or {}
    cl_text = '\n\n'.join('[%s] (%s) %s' % (c['id'], c.get('heading', ''), c['text']) for c in clauses)
    prompt = ANALYZE_PROMPT.format(entity=d.get('atliq_entity') or 'Unknown', counterparty=d.get('counterparty') or 'the counterparty',
                                   doctype=d.get('doc_type') or 'contract', annual_fee=fmt_money(annual_fee_of(d), d.get('currency') or 'USD'),
                                   total_value=fmt_money(d.get('total_value'), d.get('currency') or 'USD'), term=d.get('term_months') or 'n/a',
                                   law=d.get('governing_law') or 'n/a', payment=d.get('payment_days') or 'n/a', principles=principles_text(), benchmark=benchmark_text(), clauses=cl_text)
    obj, meta = llm_json(SYS_BASE, prompt, 'smart')
    source = '\n'.join(c['text'] for c in clauses)
    ids = {c['id'] for c in clauses}
    findings = []
    for f in obj.get('findings', []):
        if not isinstance(f, dict) or not (f.get('title') or '').strip():
            continue
        sev = f.get('severity') if f.get('severity') in SEV_ORDER else 'Minor'
        cid = str(f.get('clause_id', ''))
        quote = f.get('quote') or ''
        ok = verify_quote(quote, source) or (full_text and verify_quote(quote, full_text))
        findings.append({'source': 'contract', 'topic': f.get('topic') or 'other', 'severity': sev, 'title': (f.get('title') or '').strip(),
                         'why': f.get('why', ''), 'comparison': f.get('comparison', ''), 'clause_id': cid if cid in ids else (cid or None),
                         'quote': quote if ok else None, 'claimed_quote': None if ok else quote, 'verified': bool(ok), 'unsure': bool(f.get('unsure')) or not ok})
    reviewed = [i for i in obj.get('reviewed_ids', []) if i in ids]
    return {'findings': findings, 'reviewed': sorted(set(reviewed) | (ids if not obj.get('reviewed_ids') else set())), 'meta': meta}


# ----------------------------------------------------------------------------- informal notes
def action_notes(notes_text, details, contract_text='', **_):
    if not (notes_text or '').strip():
        return {'items': [], 'meta': None}
    d = details or {}
    terms = {'fees': d.get('total_value'), 'annual_fee': d.get('annual_fee'), 'payment_days': d.get('payment_days'), 'term_months': d.get('term_months'),
             'rates': d.get('rates'), 'services': d.get('services_summary')}
    compact = [{'id': r['id'], 'who': r['counterparty'], 'type': r['type'], 'takeaway': r['takeaway']} for r in register()]
    obj, meta = llm_json(SYS_BASE, NOTES_PROMPT.format(terms=json.dumps(terms), register=json.dumps(compact), notes=clamp_text(notes_text, 40000)), 'smart')
    items = []
    for it in obj.get('items', []):
        q = it.get('quote') or ''
        ok = verify_quote(q, notes_text)
        sev = it.get('severity') if it.get('severity') in SEV_ORDER else 'Negotiable'
        if sev == 'Serious' and not it.get('register_conflict'):
            sev = 'Negotiable'  # unofficial and not binding: Serious only when it touches a past commitment
        reflects = it.get('contract_reflects', 'unclear')
        if reflects == 'yes' and sev != 'Serious':
            sev = 'Minor'
        items.append({'source': 'unofficial', 'topic': 'informal_term', 'severity': sev, 'title': (it.get('summary') or '')[:90],
                      'why': 'Unofficial and not binding, but it affects the deal. %s' % ({'yes': 'The contract reflects it.', 'no': 'The contract does not reflect it.'}.get(reflects, 'Not clear whether the contract reflects it.')),
                      'comparison': ('May touch past commitment %s.' % it['register_conflict']) if it.get('register_conflict') else '',
                      'clause_id': None, 'quote': q if ok else None, 'verified': ok, 'unsure': True, 'kind': it.get('kind'), 'contract_reflects': reflects,
                      'register_id': it.get('register_conflict')})
    return {'items': items, 'meta': meta}


# ----------------------------------------------------------------------------- merge, dedupe, order
def merge_findings(*groups):
    allf = []
    for g in groups:
        allf.extend(g or [])
    rule_topics = {f['topic'] for f in allf if f['source'] == 'rule'}
    allf = [f for f in allf if not (f['source'] == 'contract' and f['topic'] in rule_topics)]
    seen, out = set(), []
    # rule and register findings first so they win duplicates
    allf.sort(key=lambda f: {'rule': 0, 'register': 1, 'unofficial': 2, 'contract': 3}.get(f['source'], 4))
    for f in allf:
        key = (f.get('topic'), str(f.get('clause_id') or ''), f['source'] in ('register',) and f.get('register_id'))
        if f['source'] == 'contract' and (f.get('topic'), str(f.get('clause_id') or ''), False) in seen:
            continue
        seen.add(key)
        out.append(f)
    for i, f in enumerate(sorted(out, key=lambda f: (SEV_ORDER.get(f['severity'], 3), 0 if f.get('verified') else 1))):
        f['id'] = 'F%02d' % (i + 1)
    out.sort(key=lambda f: f['id'])
    return out


def compute_end(details, cov):
    """Date arithmetic for a restriction: term plus months after term."""
    try:
        start = date.fromisoformat(details.get('effective_date'))
    except Exception:
        return None
    months = (details.get('term_months') or 0)
    basis = cov.get('duration_basis')
    if basis == 'perpetual':
        return None
    if basis == 'fixed_months':
        total = cov.get('months_after_term') or 0
    elif basis == 'term_plus_months':
        total = months + (cov.get('months_after_term') or 0)
    elif basis == 'term':
        total = months
    else:
        return None
    y, m = start.year + (start.month - 1 + total) // 12, (start.month - 1 + total) % 12 + 1
    d = min(start.day, 28)
    return date(y, m, d).isoformat()


def make_takeaway(who, clause, activity, customers, geography, end):
    t = '%s, clause %s: %s' % (who or 'Counterparty', clause or '?', activity or 'restriction')
    if customers:
        t += ' for ' + customers
    if geography:
        t += ' in ' + ', '.join(geography)
    t += (', until %s' % end) if end else ', with no end date'
    return t + '. Check before taking similar work.'


ENTRY_TYPES = ('non_compete', 'exclusivity', 'mfn_pricing', 'non_solicit', 'ip_assignment', 'data_location', 'other')


def sanitize_extra(extra, exclude_contract=None):
    """Confirmed register entries sent by the browser. Keep only well-formed ones, with safe defaults."""
    out, seen = [], set()
    for e in (extra or [])[:80]:
        if not isinstance(e, dict) or e.get('status') != 'confirmed':
            continue
        eid = str(e.get('id') or '')[:60]
        if not eid or eid in seen or e.get('contract_id') == exclude_contract:
            continue
        seen.add(eid)
        sc = e.get('scope') if isinstance(e.get('scope'), dict) else {}
        geo = [str(g)[:40] for g in (sc.get('geography') or []) if isinstance(g, str)][:12] or ['Worldwide']
        end = e.get('end') if isinstance(e.get('end'), str) and re.match(r'^\d{4}-\d{2}-\d{2}$', e.get('end')) else None
        out.append({'id': eid, 'contract_id': str(e.get('contract_id') or '')[:40], 'counterparty': str(e.get('counterparty') or 'Counterparty')[:80],
                    'type': e.get('type') if e.get('type') in ENTRY_TYPES else 'other', 'clause': str(e.get('clause') or '')[:20], 'bound': str(e.get('bound') or '')[:80],
                    'restricted_activity': str(e.get('restricted_activity') or '')[:300], 'scope': {'customers': str(sc.get('customers') or '')[:200], 'geography': geo},
                    'start': e.get('start') if isinstance(e.get('start'), str) else None, 'end': end, 'quote': str(e.get('quote') or '')[:600] or None,
                    'file': None, 'exception': None, 'takeaway': str(e.get('takeaway') or '')[:400]})
    return out


STOP = set('provide providing services service software develop developing offering offer other third parties party customers customer clients client any all same similar work'.split())


def _words(text):
    return {w for w in re.findall(r'[a-z]{5,}', (text or '').lower().replace('-', ' ')) if w not in STOP}


def new_entry_match(r, d, hay):
    """Match a newly confirmed restriction (non-compete or exclusivity) against a deal: region, kind of customer, kind of work."""
    geo = geo_match(r, d)
    cust_words = _words((r.get('scope') or {}).get('customers'))
    act_words = _words(r.get('restricted_activity'))
    cust = any(w in hay or w.rstrip('s') in hay for w in cust_words)
    act = any(w in hay or w.rstrip('s') in hay for w in act_words)
    where = 'in the restricted region' if geo else 'outside the stated region'
    if geo and cust and act:
        return 'The deal matches a restriction recently confirmed from %s: the same kind of customer and work, %s.' % (r['counterparty'], where), 'likely'
    if (geo and (cust or act)) or (cust and act):
        return 'The deal may fall under a restriction confirmed from %s (customer or work matches, region %s). Confirm the scope.' % (r['counterparty'], 'matches' if geo else 'differs'), 'possible'
    return None, None


def action_register_entry(details, contract_text, contract_id='NEW', **_):
    d = details or {}
    entries = []
    for i, c in enumerate(d.get('restrictive_covenants') or []):
        ok = verify_quote(c.get('quote') or '', contract_text)
        end = compute_end(d, c)
        activity = c.get('restricted_activity') or c.get('summary') or ''
        geo = [g for g in (c.get('geography') or []) if isinstance(g, str)]
        cust = c.get('customers') if isinstance(c.get('customers'), str) else ''
        entries.append({'id': 'N-%s-%d' % (contract_id, i + 1), 'contract_id': contract_id, 'counterparty': d.get('counterparty'), 'type': c.get('type'),
                        'clause': c.get('clause_id'), 'bound': c.get('who_is_bound'), 'restricted_activity': activity,
                        'scope': {'customers': cust, 'geography': geo}, 'quote': c.get('quote') if ok else None, 'verified': ok,
                        'start': d.get('effective_date'), 'end': end, 'status': 'pending_confirmation', 'summary': c.get('summary'),
                        'file': None, 'exception': None, 'takeaway': make_takeaway(d.get('counterparty'), c.get('clause_id'), activity, cust, geo, end)})
    return {'entries': entries}


# ----------------------------------------------------------------------------- whole pipeline (tests and local use)
def run_review(contract_text, notes_text='', context=None, workers=2, extra_register=None, exclude_contract=None):
    t0 = time.time()
    ex = action_extract(contract_text)
    details = dict(ex['details'])
    for k, v in (context or {}).items():
        if v not in (None, ''):
            details[k] = v
    clauses = segment(contract_text)
    batches = make_batches(clauses)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(action_analyze, b, details, contract_text) for b in batches]
        conf = pool.submit(action_conflicts, details, contract_text, extra_register, exclude_contract)
        nt = pool.submit(action_notes, notes_text, details, contract_text)
        analyzed = [f.result() for f in futs]
        conflicts, notes = conf.result(), nt.result()
    rules = rules_findings(details, contract_text)
    findings = merge_findings(rules, conflicts['conflicts'], notes['items'], [f for a in analyzed for f in a['findings']])
    reviewed = sorted({i for a in analyzed for i in a['reviewed']})
    mult, ltxt, _ = liability_ratio(details)
    metas = [ex['meta']] + [a['meta'] for a in analyzed] + [conflicts['meta'], notes['meta']]
    return {'details': details, 'clauses_total': len(clauses), 'clauses_reviewed': len(reviewed), 'findings': findings,
            'liability_multiple': mult, 'liability_text': ltxt, 'checked_register': conflicts['checked'],
            'seconds': round(time.time() - t0, 1), 'calls': [m for m in metas if m],
            'tokens_in': sum((m or {}).get('in', 0) for m in metas), 'tokens_out': sum((m or {}).get('out', 0) for m in metas)}

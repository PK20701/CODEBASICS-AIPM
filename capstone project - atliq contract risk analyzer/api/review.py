"""Vercel serverless entry point (Python). One endpoint, several actions, so the browser can run
the review as parallel steps and show progress. POST /api/review {"action": "...", ...}

Protection (all best effort on a serverless platform, see README "Protecting the endpoint"):
  * size and type limits on every request
  * same-origin check: a browser on another site is refused
  * per-address rate limit and a daily model-call budget (kept in memory, so they reset when the instance restarts)
  * an optional access code (set ACCESS_CODE in the environment to require it for model calls)
"""
import base64
import io
import json
import hmac
import os
import sys
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _core as core  # noqa: E402

MAX_BODY = 450_000          # bytes of JSON for every action except a file conversion
MAX_UPLOAD = 4_000_000      # characters of base64 for a file conversion (the platform allows about 4.5 MB)
MAX_TEXT = 150_000          # characters of contract text
MAX_NOTES = 60_000
MAX_CLAUSES = 40
MAX_CLAUSE_CHARS = 20_000
MODEL_ACTIONS = {'extract', 'analyze', 'conflicts', 'notes'}
WINDOW_S = 300
WINDOW_MAX = int(os.environ.get('RATE_LIMIT_PER_5MIN', '90'))   # model calls per address per 5 minutes (a long contract uses about 12)
DAILY_MAX = int(os.environ.get('DAILY_MODEL_CALLS', '2500'))
_hits = defaultdict(deque)
_day = {'d': None, 'n': 0}


def to_text(name, b64):
    """Convert an uploaded PDF, Word or text file to plain text. Word tables are kept (rate cards and fee schedules live there)."""
    raw = base64.b64decode(b64)
    n = (name or '').lower()
    if n.endswith('.pdf'):
        from pypdf import PdfReader
        return '\n\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(raw)).pages)
    if n.endswith('.docx'):
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        d = docx.Document(io.BytesIO(raw))
        out = []
        for child in d.element.body.iterchildren():
            tag = child.tag.rsplit('}', 1)[-1]
            if tag == 'p':
                out.append(Paragraph(child, d).text)
            elif tag == 'tbl':
                for row in Table(child, d).rows:
                    cells = []
                    for c in row.cells:
                        t = c.text.strip().replace('\n', ' ')
                        if t and (not cells or cells[-1] != t):   # merged cells repeat their text
                            cells.append(t)
                    if cells:
                        out.append(' | '.join(cells))
        return '\n'.join(out)
    return raw.decode('utf-8', errors='replace')


def dispatch(body):
    a = body.get('action')
    if a == 'health':
        return {'gemini': bool(os.environ.get('GEMINI_API_KEY')), 'groq': bool(os.environ.get('GROQ_API_KEY')), 'access_code_required': bool(os.environ.get('ACCESS_CODE')),
                'principles': core.principles(), 'benchmark': core.benchmark()}
    if a == 'convert':
        text = to_text(body.get('name'), body.get('data'))
        return {'text': text, 'clauses': len(core.segment(text)), 'quality': core.text_quality(text)}
    if a == 'segment':
        cl = core.segment(body.get('text', ''))
        return {'clauses': cl, 'batches': [[c['id'] for c in b] for b in core.make_batches(cl)]}
    if a == 'extract':
        return core.action_extract(body.get('text', ''))
    if a == 'rules':
        d = body.get('details') or {}
        f = core.rules_findings(d, body.get('text', ''), body.get('contract_id'))
        mult, txt, sev = core.liability_ratio(d)
        return {'findings': f, 'liability_multiple': mult, 'liability_text': txt}
    if a == 'analyze':
        return core.action_analyze(body.get('clauses') or [], body.get('details') or {}, body.get('text', ''))
    if a == 'conflicts':
        return core.action_conflicts(body.get('details') or {}, body.get('text', ''), body.get('extra_register'), body.get('exclude_contract'))
    if a == 'notes':
        return core.action_notes(body.get('notes', ''), body.get('details') or {}, body.get('text', ''))
    if a == 'register_entry':
        return core.action_register_entry(body.get('details') or {}, body.get('text', ''), body.get('contract_id', 'NEW'))
    if a == 'merge':
        return {'findings': core.merge_findings(body.get('rules'), body.get('conflicts'), body.get('notes'), body.get('analysis'))}
    return {'error': 'unknown action'}


def refuse(status, error, message):
    return status, {'error': error, 'message': message}


def guard(body, ip='', headers=None, size=None):
    """Return (status, payload) to refuse the request, or None to let it through."""
    headers = headers or {}
    if not isinstance(body, dict) or not isinstance(body.get('action'), str):
        return refuse(400, 'bad_request', 'The request is not understood.')
    a = body['action']
    origin = headers.get('origin')
    host = headers.get('host')
    if origin and host and urlparse(origin).netloc != host:
        return refuse(403, 'origin', 'Requests from other sites are not accepted.')
    if size is not None and a != 'convert' and size > MAX_BODY:
        return refuse(413, 'too_large', 'The request is too large.')
    for k, cap in (('text', MAX_TEXT), ('notes', MAX_NOTES)):
        v = body.get(k)
        if k == 'notes' and a != 'notes':
            continue   # in the merge step "notes" is a list of findings, not text
        if v is not None and (not isinstance(v, str) or len(v) > cap):
            return refuse(413, 'too_large', 'The %s is too long (limit %d characters).' % (k, cap))
    if a == 'convert' and (not isinstance(body.get('data'), str) or len(body['data']) > MAX_UPLOAD):
        return refuse(413, 'too_large', 'The file is too large (limit about 3 MB).')
    if a == 'analyze':
        cl = body.get('clauses')
        if not isinstance(cl, list) or len(cl) > MAX_CLAUSES or any(not isinstance(c, dict) or len(str(c.get('text', ''))) > MAX_CLAUSE_CHARS for c in cl):
            return refuse(413, 'too_large', 'Too many or too long clauses in one call.')
    if a in MODEL_ACTIONS:
        code = os.environ.get('ACCESS_CODE')
        if code and not hmac.compare_digest(str(headers.get('x-access-code', '')), code):
            return refuse(401, 'access', 'An access code is needed for this demo.')
        now = time.time()
        q = _hits[ip or 'unknown']
        while q and now - q[0] > WINDOW_S:
            q.popleft()
        if len(q) >= WINDOW_MAX:
            return refuse(429, 'rate_limit', 'Too many reviews from this address in a short time. Please wait a few minutes.')
        today = time.strftime('%Y-%m-%d', time.gmtime())
        if _day['d'] != today:
            _day['d'], _day['n'] = today, 0
        if _day['n'] >= DAILY_MAX:
            return refuse(429, 'daily_budget', 'The demo has reached its daily model budget. Please try again tomorrow.')
        q.append(now)
        _day['n'] += 1
    return None


def handle(body, ip='', headers=None, size=None):
    refused = guard(body, ip, headers, size)
    if refused:
        return refused
    try:
        return 200, dispatch(body)
    except core.QuotaError as e:
        return 429, {'error': 'quota', 'message': 'The model is rate-limited right now. Try again in a minute. %s' % str(e)[:120]}
    except core.LLMError as e:
        return 502, {'error': 'model', 'message': str(e)[:300]}
    except Exception as e:  # never leak a stack trace to the browser
        return 500, {'error': 'server', 'message': '%s: %s' % (type(e).__name__, str(e)[:200])}


def client_ip(headers, fallback=''):
    xf = headers.get('x-forwarded-for') or headers.get('x-real-ip') or ''
    return xf.split(',')[0].strip() or fallback


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        headers = {k.lower(): v for k, v in self.headers.items()}
        if n > MAX_UPLOAD + 1000:
            code, out = refuse(413, 'too_large', 'The request is too large.')
        else:
            try:
                body = json.loads(self.rfile.read(n) or b'{}')
            except Exception:
                body = None
            code, out = handle(body, client_ip(headers, self.client_address[0]), headers, n)
        data = json.dumps(out).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

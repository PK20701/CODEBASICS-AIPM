"""Vercel serverless entry point (Python). One endpoint, several actions, so the browser can run
the review as parallel steps and show progress. POST /api/review {"action": "...", ...}"""
import base64
import io
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _core as core  # noqa: E402


def to_text(name, b64):
    """Convert an uploaded PDF, Word or text file to plain text."""
    raw = base64.b64decode(b64)
    n = (name or '').lower()
    if n.endswith('.pdf'):
        from pypdf import PdfReader
        return '\n\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(raw)).pages)
    if n.endswith('.docx'):
        import docx
        d = docx.Document(io.BytesIO(raw))
        return '\n'.join(p.text for p in d.paragraphs)
    return raw.decode('utf-8', errors='replace')


def dispatch(body):
    a = body.get('action')
    if a == 'health':
        return {'gemini': bool(os.environ.get('GEMINI_API_KEY')), 'groq': bool(os.environ.get('GROQ_API_KEY')),
                'principles': core.principles(), 'benchmark': core.benchmark()}
    if a == 'convert':
        text = to_text(body.get('name'), body.get('data'))
        return {'text': text, 'clauses': len(core.segment(text))}
    if a == 'segment':
        cl = core.segment(body.get('text', ''))
        return {'clauses': cl, 'batches': [[c['id'] for c in b] for b in core.make_batches(cl)]}
    if a == 'extract':
        return core.action_extract(body.get('text', ''))
    if a == 'rules':
        d = body.get('details') or {}
        f = core.rules_findings(d, body.get('text', ''))
        mult, txt, sev = core.liability_ratio(d)
        return {'findings': f, 'liability_multiple': mult, 'liability_text': txt}
    if a == 'analyze':
        return core.action_analyze(body.get('clauses') or [], body.get('details') or {}, body.get('text', ''))
    if a == 'conflicts':
        return core.action_conflicts(body.get('details') or {}, body.get('text', ''))
    if a == 'notes':
        return core.action_notes(body.get('notes', ''), body.get('details') or {}, body.get('text', ''))
    if a == 'register_entry':
        return core.action_register_entry(body.get('details') or {}, body.get('text', ''), body.get('contract_id', 'NEW'))
    if a == 'merge':
        return {'findings': core.merge_findings(body.get('rules'), body.get('conflicts'), body.get('notes'), body.get('analysis'))}
    return {'error': 'unknown action'}


def handle(body):
    try:
        return 200, dispatch(body)
    except core.QuotaError as e:
        return 429, {'error': 'quota', 'message': 'The model is rate-limited right now. Try again in a minute. %s' % str(e)[:120]}
    except core.LLMError as e:
        return 502, {'error': 'model', 'message': str(e)[:300]}
    except Exception as e:  # never leak a stack trace to the browser
        return 500, {'error': 'server', 'message': '%s: %s' % (type(e).__name__, str(e)[:200])}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        try:
            body = json.loads(self.rfile.read(n) or b'{}')
        except Exception:
            body = {}
        code, out = handle(body)
        data = json.dumps(out).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

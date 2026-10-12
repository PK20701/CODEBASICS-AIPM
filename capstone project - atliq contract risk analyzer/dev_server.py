"""Local development server: serves public/ and routes /api/review to the same code Vercel runs.
Usage: python dev_server.py   (then open http://localhost:8765)
Keys are read from the environment or from a local .env file (never commit it)."""
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'api'))


def load_env():
    p = os.path.join(ROOT, '.env')
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8'):
            ln = ln.strip()
            if ln and not ln.startswith('#') and '=' in ln:
                k, v = ln.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))


load_env()
import review  # noqa: E402


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/':
            path = '/index.html'
        fp = os.path.normpath(os.path.join(ROOT, 'public', path.lstrip('/')))
        if not fp.startswith(os.path.join(ROOT, 'public')) or not os.path.isfile(fp):
            self.send_response(404)
            self.end_headers()
            return
        data = open(fp, 'rb').read()
        self.send_response(200)
        self.send_header('Content-Type', (mimetypes.guess_type(fp)[0] or 'application/octet-stream') + ('; charset=utf-8' if fp.endswith(('.md', '.html', '.json', '.js', '.csv')) else ''))
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path.split('?')[0] != '/api/review':
            self.send_response(404)
            self.end_headers()
            return
        n = int(self.headers.get('Content-Length') or 0)
        try:
            body = json.loads(self.rfile.read(n) or b'{}')
        except Exception:
            body = None
        headers = {k.lower(): v for k, v in self.headers.items()}
        code, out = review.handle(body, review.client_ip(headers, self.client_address[0]), headers, n)
        data = json.dumps(out).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *a):
        sys.stderr.write('%s\n' % (fmt % a))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8765'))
    print('AtliQ Contract Risk Analyzer on http://localhost:%d' % port)
    ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()

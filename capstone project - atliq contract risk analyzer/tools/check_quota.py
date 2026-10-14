"""Shows where the free model tiers stand right now. Uses the keys in .env (never printed).
Usage: python tools/check_quota.py
Groq: prints the limits and what is left, from the response headers of a tiny call.
Gemini: the API does not report remaining quota, so each model gets one tiny call; a 429 says whether the per-minute or the per-day limit was hit and when to retry.
For the official numbers and the daily reset, use the Google AI Studio usage page (aistudio.google.com/usage) and the Groq console (console.groq.com/settings/limits)."""
import json
import os
import re
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for ln in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
    if '=' in ln and not ln.startswith('#'):
        k, v = ln.strip().split('=', 1)
        os.environ.setdefault(k, v)

GEMINI = os.environ.get('GEMINI_ROTATION', 'gemini-3.1-flash-lite,gemini-3-flash-preview,gemini-flash-lite-latest,gemini-3.6-flash').split(',')
GROQ = os.environ.get('GROQ_ROTATION', 'openai/gpt-oss-120b,qwen/qwen3.8-27b,openai/gpt-oss-20b').split(',')

print('GROQ (limits are per model)')
for m in GROQ:
    body = {'model': m, 'messages': [{'role': 'user', 'content': 'Reply with JSON {"ok":true}'}], 'max_tokens': 200, 'response_format': {'type': 'json_object'}}
    req = urllib.request.Request('https://api.groq.com/openai/v1/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ['GROQ_API_KEY'], 'User-Agent': 'atliq/1.0'})
    try:
        r = urllib.request.urlopen(req, timeout=40)
        h, status = r.headers, 'ok'
    except urllib.error.HTTPError as e:
        h, status = e.headers, 'HTTP %s' % e.code
    g = lambda k: h.get('x-ratelimit-' + k, '?')
    print('  %-22s %-8s requests left %s of %s a day (back to full in %s) | tokens left %s of %s a minute' % (
        m, status, g('remaining-requests'), g('limit-requests'), g('reset-requests'), g('remaining-tokens'), g('limit-tokens')))

print('\nGEMINI (the free tier has per-minute and per-day limits for each model)')
key = os.environ['GEMINI_API_KEY']
for m in GEMINI:
    url = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (m, key)
    body = {'contents': [{'role': 'user', 'parts': [{'text': 'Reply with JSON {"ok":true}'}]}], 'generationConfig': {'responseMimeType': 'application/json'}}
    t = time.time()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}), timeout=40)
        print('  %-26s ok, answered in %.1f s' % (m, time.time() - t))
    except urllib.error.HTTPError as e:
        txt = e.read().decode('utf-8', 'replace')
        kind = 'PER-DAY limit hit (resets at midnight Pacific time)' if re.search(r'PerDay', txt) else 'per-minute limit hit' if re.search(r'PerMinute', txt) else 'rate limited'
        retry = re.search(r'retry in ([0-9.]+)s', txt)
        print('  %-26s HTTP %s: %s%s' % (m, e.code, kind if e.code == 429 else 'error', (', retry in %.0f s' % float(retry.group(1))) if retry else ''))
    except Exception as e:
        print('  %-26s no answer in %.0f s (%s)' % (m, time.time() - t, str(e)[:50]))

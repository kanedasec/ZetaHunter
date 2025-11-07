#!/usr/bin/env python3
"""Safe Juice Shop test script (lab only).
Performs a few non-destructive HTTP requests and prints JSON to stdout.
Usage:
    python3 juice_shop_test.py http://localhost:3000
Output (JSON):
    {
      "evidence": [...],
      "stdout": "...",
      "exit_code": 0
    }
"""
import sys
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title = ""
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.in_title = True
    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False
    def handle_data(self, data):
        if self.in_title:
            self.title += data

def fetch(path):
    try:
        req = Request(path, headers={'User-Agent': 'BugHunterAI-juice-test/1.0'})
        with urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            return resp.status, content
    except HTTPError as e:
        return e.code, ''
    except URLError as e:
        return None, ''
    except Exception:
        return None, ''

def safe_probe(target):
    evidence = []
    stdout_parts = []
    # Normalize target
    if target.endswith('/'):
        target = target[:-1]
    # Probe root
    status, content = fetch(target + '/')
    stdout_parts.append(f'GET / -> status={status}')
    title = ''
    if content:
        p = TitleParser()
        p.feed(content)
        title = p.title.strip()
        if title:
            evidence.append({'path': '/', 'title': title})
    # Probe known Juice Shop endpoint (non-destructive)
    status_api, _ = fetch(target + '/rest/user/login')
    stdout_parts.append(f'GET /rest/user/login -> status={status_api}')
    # Simple heuristic: look for "OWASP Juice Shop" in title or homepage
    found = False
    if 'juice shop' in (title.lower() if title else '') or (content and 'OWASP Juice Shop' in content):
        found = True
        evidence.append({'note': 'juice-shop-like-homepage-detected'})
    result = {
        "evidence": evidence,
        "stdout": "\n".join(stdout_parts),
        "exit_code": 0 if status else 2
    }
    print(json.dumps(result))
    return result

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"evidence": [], "stdout": "usage: juice_shop_test.py <target_url>", "exit_code": 2}))
        sys.exit(2)
    target = sys.argv[1]
    safe_probe(target)

if __name__ == '__main__':
    main()

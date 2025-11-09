#!/usr/bin/env python3
"""Simple playbook executor for MVP.
Usage:
    python3 executor.py backend/playbooks/basic-recon.yml http://localhost:3000
This script loads the YAML playbook and executes steps sequentially.
Supported step types:
  - http_get: performs a GET request to the target+path and records status and title
  - run_script: executes a local script (path is relative to repo root) and captures JSON output
Security: only allows targets listed in ALLOWED_TARGETS env var (comma-separated).
"""
import sys
import os
import subprocess
import json
import time
import yaml
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

def allowed_target(target):
    allowed = os.getenv("ALLOWED_TARGETS", "localhost,127.0.0.1").split(",")
    return any(a.strip() in target for a in allowed)

def http_get_resolve(base, step):
    """
    Resolve 'path' ou 'url' a partir do step (tanto em step['params'] quanto no topo).
    Se 'url' for absoluto (http://...), usa direto. Caso contrário, junta com base.
    """
    params = step.get('params', {}) or {}
    url_field = params.get('url') or step.get('url')
    path_field = params.get('path') or step.get('path') or '/'

    if url_field:
        if '://' in url_field:
            full = url_field
        else:
            full = base.rstrip('/') + url_field
    else:
        full = base.rstrip('/') + path_field

    try:
        req = Request(full, headers={'User-Agent': 'BugHunterAI-executor/1.0'})
        with urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            status = resp.status
    except HTTPError as e:
        status = e.code
        content = ''
    except URLError:
        status = None
        content = ''
    except Exception:
        status = None
        content = ''

    title = ''
    if content:
        p = TitleParser()
        p.feed(content)
        title = p.title.strip()

    # Para manter compatibilidade com o formato antigo do retorno:
    # reporto 'path' com o que eu usei (se foi url absoluto, mantenho em 'path' para exibir)
    used_path = full if '://' in (url_field or '') else path_field
    return {'path': used_path, 'status': status, 'title': title, 'content_sample': content[:200]}


def run_script(script_path, target):
    # script_path pode ter vindo de params ou do topo do step
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    full = os.path.join(repo_root, script_path) if not os.path.isabs(script_path) else script_path
    if not os.path.exists(full):
        return {'error': 'script not found', 'path': script_path}
    try:
        proc = subprocess.run(
            ['python3', full, target],
            capture_output=True, text=True,
            timeout=int(os.getenv('RUNNER_TIMEOUT', '30'))
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        # tentar parsear JSON do stdout
        try:
            parsed = json.loads(stdout) if stdout else None
        except Exception:
            parsed = None
        result = parsed if isinstance(parsed, dict) else {'raw_stdout': stdout}
        # sempre devolva stderr e return_code pra facilitar debug
        return {
            'script': script_path,
            'exit_code': proc.returncode,
            'stderr': stderr,
            'result': result
        }
    except subprocess.TimeoutExpired:
        return {'script': script_path, 'error': 'timeout'}
    except Exception as e:
        return {'script': script_path, 'error': str(e)}


def run_playbook(playbook_path, target):
    if not allowed_target(target):
        raise SystemExit('target not allowed by ALLOWED_TARGETS')
    if not os.path.exists(playbook_path):
        raise SystemExit('playbook not found')
    with open(playbook_path, 'r', encoding='utf-8') as f:
        pb = yaml.safe_load(f)
    results = {'playbook': playbook_path, 'target': target, 'steps': []}
    for step in pb.get('steps', []):
        sid = step.get('id')
        stype = step.get('type')
        params = step.get('params', {})
        entry = {'id': sid, 'type': stype}
        if stype == 'http_get':
            entry['result'] = http_get_resolve(target, step)
        elif stype == 'run_script':
            # tolerante: tenta params.script, depois top-level script, depois top-level path
            script = step.get('params', {}).get('script') or step.get('script') or step.get('path')
            entry['result'] = run_script(script, target)
        else:
            entry['result'] = {'error': 'unsupported step type'}
        results['steps'].append(entry)
        time.sleep(0.5)
    return results

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(json.dumps({"error": "usage: executor.py <playbook.yml> <target>"}))
        sys.exit(2)
    playbook = sys.argv[1]
    target = sys.argv[2]
    out = run_playbook(playbook, target)
    print(json.dumps(out, indent=2))

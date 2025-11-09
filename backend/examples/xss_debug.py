import requests
from urllib.parse import urlparse
import sys
import json

def probe_reflected_xss(target_url):
    url = target_url.rstrip('/')
    for path in ['/about/', '/contact/']:
        response = requests.get(f'{url}{path}')
        if 'referrer' in response.headers:
            print(json.dumps({'evidence': [f'{url}{path}', response.headers['referrer']], 'stdout': f'Responded with referrer: {response.headers["referrer"]}', 'exit_code': 1}))
            return
    print(json.dumps({'evidence': [], 'stdout': 'No referrer header found', 'exit_code': 0}))

if __name__ == '__main__':
    target_url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:3000'
    probe_reflected_xss(target_url)

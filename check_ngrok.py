import urllib.request
import json
try:
    response = urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels', timeout=2)
    data = json.loads(response.read().decode('utf-8'))
    for t in data.get('tunnels', []):
        print(f"Tunnel: {t.get('public_url')} -> {t.get('config', {}).get('addr')}")
except Exception as e:
    print('Error:', e)

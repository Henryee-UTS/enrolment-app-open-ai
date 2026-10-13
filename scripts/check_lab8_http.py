"""Read-only functional checks except refreshing the derived RAG index."""
import json
from pathlib import Path
import requests

root = Path(__file__).resolve().parents[1]
results = []

def record(name, response, expected=200):
    assert response.status_code == expected, (name, response.status_code, response.text)
    try:
        payload = response.json()
    except ValueError:
        payload = {'html_served': True}
    results.append({'check': name, 'http_status': response.status_code, 'payload': payload})
    return payload

record('frontend RAG page', requests.get('http://localhost:8080/tabs/rag.html', timeout=10))
record('RAG health', requests.get('http://localhost:5003/health', timeout=10))
base = 'http://localhost:5001/rag'
r = record('refresh via Docker', requests.post(base+'/refresh', timeout=60))
assert r['vector_store_status'] == 'ready', r
r = record('retrieve via Docker', requests.post(base+'/retrieve', data={'query':'students enrolled in ASD101'}, timeout=30))
assert r['retrieval_mode'] == 'vector'
r = record('subject answer', requests.post(base+'/answer', data={'query':'Which students are enrolled in ASD101?'}, timeout=30))
assert 'John Smith' in r['answer'] and 'Sarah Jones' in r['answer'] and r['citations']
r = record('aggregate answer', requests.post(base+'/answer', data={'query':'student count','k':1}, timeout=30))
assert '10 students' in r['answer'], r
r = record('absent subject', requests.post(base+'/answer', data={'query':'Which students are enrolled in XYZ999?'}, timeout=30))
assert r['answer'] == 'Insufficient evidence.' and not r['citations']
record('disabled mode', requests.post(base+'/answer', headers={'X-RAG-Mode':'off'}, data={'query':'student count'}, timeout=10),403)
record('invalid k', requests.post(base+'/retrieve', data={'query':'student count','k':'bad'}, timeout=10),400)
record('blank query', requests.post(base+'/answer', data={'query':''}, timeout=10),400)
record('invalid JSON type', requests.post('http://localhost:5003/answer', json=[], timeout=10),400)
(root/'reports/rag-http-checks.json').write_text(json.dumps(results, indent=2))
print(f'{len(results)} HTTP checks passed; reports/rag-http-checks.json')

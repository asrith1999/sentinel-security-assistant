"""Run with the backend and MySQL running; creates a disposable test account/case."""
import argparse
import secrets
import uuid
from pathlib import Path
import httpx

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ai',action='store_true',help='Also run real local model inference (may be slow).')
args=parser.parse_args()
with httpx.Client(base_url='http://127.0.0.1:8000/api',timeout=240) as client:
    health=client.get('/health');health.raise_for_status()
    assert health.json()['database'], 'Database is not ready'
    account=client.post('/auth/register',json={'name':'Local acceptance test','email':f'test-{uuid.uuid4().hex[:12]}@example.com','password':secrets.token_urlsafe(20)})
    account.raise_for_status()
    client.headers['Authorization']='Bearer '+account.json()['token']
    logs=(Path(__file__).resolve().parents[2]/'examples/suspicious-login.log').read_text()
    case=client.post('/investigations',json={'title':'Local acceptance test','source':'synthetic example','logs':logs});case.raise_for_status()
    data=case.json();assert data['line_count']==8 and data['finding_count']==4, data
    report=client.get(f"/investigations/{data['id']}/report",params={'language':'ta'});report.raise_for_status()
    assert 'சம்பவ அறிக்கை' in report.text
    if args.ai:
        result=client.post(f"/investigations/{data['id']}/explain",json={'language':'ta'});result.raise_for_status()
        assert result.json()['ai_summary'].strip()
        print('Real model returned a nonempty response; review its content manually.')
    client.post('/auth/logout').raise_for_status()
    print('PASS: live backend database/auth, sample analysis, Tamil report and logout.')
    print('A synthetic test account and case remain in your local database.')

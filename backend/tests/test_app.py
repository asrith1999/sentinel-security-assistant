import uuid
from datetime import timedelta
import pytest
import httpx
from fastapi.testclient import TestClient
from app.main import app, _attempts
from app.db import Base, engine, SessionLocal, User, LoginSession, now
from app.security import token_hash
from app.analyzer import analyze
from app import ai

SAMPLE='\n'.join([f'2026-10-27T08:00:0{i}Z sshd Failed password for admin from 203.0.113.24' for i in range(5)]+['2026-10-27T08:01:03Z sshd Accepted password for admin from 203.0.113.24'])

@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    _attempts.clear()
    with TestClient(app) as c:
        yield c

def signup(c,email='a@example.com'):
    r=c.post('/api/auth/register',json={'name':'Asrith','email':email,'password':'test-password-123'})
    assert r.status_code==201,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def case(c,h,logs=SAMPLE):
    r=c.post('/api/investigations',headers=h,json={'title':'SSH review','logs':logs})
    assert r.status_code==201,r.text
    return r.json()

def test_auth_hash_login_logout(client):
    h=signup(client)
    with SessionLocal() as db:
        user=db.query(User).first()
        assert user.password_hash.startswith('scrypt$')
        assert 'test-password' not in user.password_hash
        assert db.query(LoginSession).first().token_hash!=h['Authorization'].split()[1]
    assert client.get('/api/auth/me',headers=h).json()['name']=='Asrith'
    assert client.post('/api/auth/login',json={'email':'a@example.com','password':'incorrect-password'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'a@example.com','password':'test-password-123'}).status_code==200
    assert client.post('/api/auth/logout',headers=h).status_code==204
    assert client.get('/api/auth/me',headers=h).status_code==401

def test_duplicate_and_invalid_register(client):
    signup(client)
    assert client.post('/api/auth/register',json={'name':'Other','email':'A@example.com','password':'test-password-123'}).status_code==409
    assert client.post('/api/auth/register',json={'name':' ','email':'bad','password':'x'}).status_code==422

def test_expired_token(client):
    h=signup(client)
    with SessionLocal() as db:
        token=db.get(LoginSession,token_hash(h['Authorization'].split()[1]));token.expires_at=now()-timedelta(seconds=1);db.commit()
    assert client.get('/api/investigations',headers=h).status_code==401

def test_owner_isolation_and_report(client):
    a=signup(client);item=case(client,a);b=signup(client,'b@example.com')
    for suffix in ['', '/report']:
        assert client.get('/api/investigations/'+item['id']+suffix,headers=b).status_code==404
    assert client.get('/api/investigations',headers=b).json()==[]
    assert client.patch('/api/investigations/'+item['id'],headers=b,json={'status':'resolved'}).status_code==404
    assert client.post('/api/investigations/'+item['id']+'/explain',headers=b,json={}).status_code==404
    r=client.get('/api/investigations/'+item['id']+'/report?language=ta',headers=a)
    assert r.status_code==200 and 'சம்பவ அறிக்கை' in r.text
    assert client.patch('/api/investigations/'+item['id'],headers=a,json={'status':'resolved'}).json()['status']=='resolved'
    assert client.get('/api/investigations/'+item['id'],headers=a).json()['logs']==SAMPLE

def test_validation_and_body_limit(client):
    h=signup(client)
    assert client.post('/api/investigations',headers=h,json={'title':'x','logs':' '}).status_code==422
    assert client.post('/api/investigations',headers=h,json={'title':'x','logs':'a'*200001}).status_code==422
    assert client.post('/api/investigations',headers=h,content=b'x'*(1024*1024+1)).status_code==413
    assert client.get('/api/investigations').status_code==401
    assert client.get('/api/health',headers={'Origin':'https://untrusted.example'}).status_code==403
    assert client.get('/api/health',headers={'Host':'untrusted.example'}).status_code==400

def test_auth_throttle(client):
    for _ in range(15):
        assert client.post('/api/auth/login',json={'email':'missing@example.com','password':'incorrect-password'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'missing@example.com','password':'incorrect-password'}).status_code==429

def test_correlation_and_false_positive_guards():
    result=analyze(SAMPLE)
    assert result['line_count']==6
    assert {f['code'] for f in result['findings']}=={'auth_failures','success_after_failures'}
    assert not any(f['code']=='success_after_failures' for f in analyze(SAMPLE.replace('Accepted password for admin','Accepted password for bob'))['findings'])
    assert not any(f['code']=='success_after_failures' for f in analyze(SAMPLE.replace('08:01:03','10:01:03'))['findings'])
    assert analyze('healthcheck OK')['risk']=='unclassified'

def test_json_and_tamil_findings():
    result=analyze('[{"src_ip":"198.51.100.20","user":"test","message":"login_failed"}]')
    assert result['line_count']==1
    assert 'test / 198.51.100.20' in result['findings'][0]['title']
    assert 'உள்நுழைவு' in result['findings'][0]['title_ta']

def test_mocked_ollama_and_saved_chat(client,monkeypatch):
    requests=[]
    def handler(request):
        import json
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={'message':{'content':'தமிழ் ஆய்வு: ஆதாரத்தைச் சரிபார்க்கவும்.'}})
    real=httpx.AsyncClient
    monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(handler),**kw))
    h=signup(client);item=case(client,h)
    r=client.post('/api/investigations/'+item['id']+'/explain',headers=h,json={'language':'ta'})
    assert r.status_code==200 and 'தமிழ்' in r.json()['ai_summary']
    assert requests[0]['stream'] is False and 'Tamil' in requests[0]['messages'][0]['content']
    thread=str(uuid.uuid4())
    payload={'question':'Explain this alert','conversation_id':thread,'language':'ta','investigation_id':item['id']}
    assert client.post('/api/chat',headers=h,json=payload).status_code==200
    assert len(client.get('/api/chat/'+thread,headers=h).json())==1
    other=signup(client,'other@example.com')
    assert client.get('/api/chat/'+thread,headers=other).json()==[]
    assert client.post('/api/chat',headers=other,json=payload).status_code==404

def test_ollama_offline_does_not_fake_answer(client,monkeypatch):
    def handler(request): raise httpx.ConnectError('offline',request=request)
    real=httpx.AsyncClient
    monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(handler),**kw))
    h=signup(client);item=case(client,h)
    r=client.post('/api/investigations/'+item['id']+'/explain',headers=h,json={})
    assert r.status_code==503
    assert client.get('/api/investigations/'+item['id'],headers=h).json()['ai_summary']==''
    status=client.get('/api/health').json()
    assert status['database'] and not status['ollama']['reachable']

def test_ollama_missing_model_and_timeout(client,monkeypatch):
    real=httpx.AsyncClient
    def missing(request): return httpx.Response(404,json={'error':'missing'})
    monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(missing),**kw))
    h=signup(client);item=case(client,h);path='/api/investigations/'+item['id']+'/explain'
    assert 'ollama pull' in client.post(path,headers=h,json={}).json()['detail']
    def timeout(request): raise httpx.ReadTimeout('slow',request=request)
    monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(timeout),**kw))
    assert client.post(path,headers=h,json={}).status_code==504

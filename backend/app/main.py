import json
import re
import uuid
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text, delete, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .config import settings
from .db import Base, engine, User, LoginSession, Investigation, Chat, now
from .security import get_db, current_user, password_hash, verify_password, issue_session, bearer, token_hash
from .analyzer import analyze
from . import ai

@asynccontextmanager
async def lifespan(app):
    try:
        Base.metadata.create_all(engine)
    except SQLAlchemyError:
        pass  # /api/health provides actionable readiness instead of crashing the UI.
    yield

app = FastAPI(title='Sentinel Security Assistant', version='2.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.frontend_origins.split(','), allow_methods=['GET','POST','PATCH','DELETE'], allow_headers=['Authorization','Content-Type'])

@app.middleware('http')
async def local_boundary(request: Request, call_next):
    # Limits DNS rebinding and browser cross-origin calls to this local lab server.
    host = request.headers.get('host','').split(':')[0]
    if host not in {'127.0.0.1','localhost','testserver'}:
        return Response('Localhost access only', status_code=400)
    origin = request.headers.get('origin')
    if origin and origin not in settings.frontend_origins.split(','):
        return Response('Origin not allowed', status_code=403)
    if request.method in {'POST','PATCH','PUT'}:
        size = 0
        parts = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 1024*1024:
                return Response('Request exceeds 1 MB', status_code=413)
            parts.append(chunk)
        request._body = b''.join(parts)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# Bounded, per-process login/register throttle for this single-process localhost app.
_attempts = defaultdict(deque)
def rate_limit(request):
    key = request.client.host if request.client else 'local'
    cutoff = time.monotonic()-60
    for old in list(_attempts):
        while _attempts[old] and _attempts[old][0] < cutoff:
            _attempts[old].popleft()
        if not _attempts[old]:
            del _attempts[old]
    q = _attempts[key]
    if len(q)>=15:
        raise HTTPException(429,'Too many authentication attempts. Wait one minute.')
    q.append(time.monotonic())

class Credentials(BaseModel):
    email: str = Field(min_length=3,max_length=254)
    password: str = Field(min_length=10,max_length=128)
    @field_validator('email')
    @classmethod
    def email_valid(cls,v):
        v=v.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v):
            raise ValueError('Enter a valid email address')
        return v
class Registration(Credentials):
    name: str = Field(min_length=1,max_length=100)
    @field_validator('name')
    @classmethod
    def name_valid(cls,v):
        if not v.strip(): raise ValueError('Name cannot be blank')
        return v.strip()
class Evidence(BaseModel):
    title: str = Field(min_length=1,max_length=150)
    source: str = Field(default='Pasted logs',max_length=150)
    logs: str = Field(min_length=1,max_length=200000)
    @field_validator('title','logs')
    @classmethod
    def not_blank(cls,v):
        if not v.strip(): raise ValueError('Cannot be blank')
        return v
class Language(BaseModel):
    language: Literal['en','ta']='en'
class ChatRequest(Language):
    question: str = Field(min_length=1,max_length=3000)
    conversation_id: uuid.UUID
    investigation_id: uuid.UUID | None = None
class StatusChange(BaseModel):
    status: Literal['open','investigating','resolved']

def profile(user):
    return {'id':user.id,'name':user.name,'email':user.email}
def public_case(c, full=False):
    data={'id':c.id,'title':c.title,'source':c.source,'status':c.status,'created_at':c.created_at.isoformat()+'Z',
        'line_count':c.result['line_count'],'finding_count':c.result['finding_count'],'risk':c.result['risk']}
    if full: data.update(result=c.result,logs=c.logs,ai_summary=c.ai_summary)
    return data

def owned_case(db,user,id):
    c=db.scalar(select(Investigation).where(Investigation.id==str(id),Investigation.user_id==user.id))
    if not c: raise HTTPException(404,'Investigation not found.')
    return c

@app.get('/api/health')
async def health():
    database=False
    try:
        with engine.connect() as c:
            c.execute(text('SELECT 1'))
            database=all(inspect(c).has_table(table) for table in ['users','login_sessions','investigations','chats'])
    except SQLAlchemyError:
        pass
    return {'backend':True,'database':database,'ollama':await ai.health()}

@app.post('/api/auth/register',status_code=201)
def register(body:Registration,request:Request,db:Session=Depends(get_db)):
    rate_limit(request)
    user=User(name=body.name,email=body.email,password_hash=password_hash(body.password))
    db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'This email is already registered.')
    return {'token':issue_session(db,user.id),'user':profile(user)}

@app.post('/api/auth/login')
def login(body:Credentials,request:Request,db:Session=Depends(get_db)):
    rate_limit(request)
    user=db.scalar(select(User).where(User.email==body.email))
    # Constant-cost password work for unknown accounts.
    hashed=user.password_hash if user else password_hash('unused-password')
    if not verify_password(body.password,hashed) or not user:
        raise HTTPException(401,'Email or password is incorrect.')
    db.execute(delete(LoginSession).where(LoginSession.expires_at<now()))
    return {'token':issue_session(db,user.id),'user':profile(user)}

@app.get('/api/auth/me')
def me(user:User=Depends(current_user)):
    return profile(user)

@app.post('/api/auth/logout',status_code=204)
def logout(auth=Depends(bearer),user:User=Depends(current_user),db:Session=Depends(get_db)):
    db.execute(delete(LoginSession).where(LoginSession.token_hash==token_hash(auth.credentials)))
    db.commit()
    return Response(status_code=204)

@app.post('/api/investigations',status_code=201)
def create_case(body:Evidence,user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=Investigation(id=str(uuid.uuid4()),user_id=user.id,title=body.title.strip(),source=body.source,logs=body.logs,result=analyze(body.logs))
    db.add(c);db.commit()
    return public_case(c,True)

@app.get('/api/investigations')
def cases(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return [public_case(c) for c in db.scalars(select(Investigation).where(Investigation.user_id==user.id).order_by(Investigation.created_at.desc()).limit(200))]

@app.get('/api/investigations/{id}')
def get_case(id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    return public_case(owned_case(db,user,id),True)

@app.patch('/api/investigations/{id}')
def set_status(id:uuid.UUID,body:StatusChange,user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=owned_case(db,user,id);c.status=body.status;db.commit()
    return public_case(c,True)

@app.post('/api/investigations/{id}/explain')
async def explain(id:uuid.UUID,body:Language,user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=owned_case(db,user,id)
    context=json.dumps(c.result,ensure_ascii=False)+'\nRAW LOG EXCERPT (first 12000 characters only):\n'+c.logs[:12000]
    result=await ai.answer('Explain these findings. Provide observations, hypotheses, missing evidence and a numbered investigation plan. Do not treat unclassified logs as safe.',body.language,context=context)
    c.ai_summary=result;db.commit()
    return public_case(c,True)

@app.get('/api/investigations/{id}/report')
def report(id:uuid.UUID,language:Literal['en','ta']='en',user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=owned_case(db,user,id);ta=language=='ta'
    rows=[('சம்பவ அறிக்கை வரைவு' if ta else 'INCIDENT REPORT DRAFT'),c.title,f'ID: {c.id}',f'UTC: {c.created_at.isoformat()}Z',
        ('நிலை: ' if ta else 'Status: ')+c.status,f"Lines: {c.result['line_count']} | Findings: {c.result['finding_count']}",
        'Method: deterministic rules; AI commentary is unverified.','']
    for f in c.result['findings']:
        rows.extend([f['title_ta'] if ta else f['title'],f['detail_ta'] if ta else f['detail'],*f['evidence'],''])
    if not c.result['findings']: rows.append('பொருந்தும் அறிகுறிகள் இல்லை; இது பாதுகாப்பை உறுதிப்படுத்தாது.' if ta else 'No supported patterns matched; safety is not established.')
    rows += ['\nAI commentary (unverified):',c.ai_summary or 'Not requested.',
        '\nAnalyst verification: affected assets [add]; impact [add]; confirmed timeline [add]; approvals and actions [add].',
        'No system changes or containment actions were performed by this application.']
    return Response('\n'.join(rows),media_type='text/plain; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="sentinel-{c.id}.txt"'})

@app.get('/api/chat/{conversation_id}')
def chat_history(conversation_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    return [{'question':c.question,'answer':c.answer} for c in db.scalars(select(Chat).where(Chat.user_id==user.id,Chat.conversation_id==str(conversation_id)).order_by(Chat.id).limit(100))]

@app.post('/api/chat')
async def chat(body:ChatRequest,user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=list(db.scalars(select(Chat).where(Chat.user_id==user.id,Chat.conversation_id==str(body.conversation_id)).order_by(Chat.id.desc()).limit(4)))[::-1]
    history=[]
    for row in rows: history.extend([{'role':'user','content':row.question[:3000]},{'role':'assistant','content':row.answer[:2000]}])
    context=''
    if body.investigation_id:
        c=owned_case(db,user,body.investigation_id)
        context=json.dumps(c.result,ensure_ascii=False)+'\nFirst 12000 log characters:\n'+c.logs[:12000]
    result=await ai.answer(body.question,body.language,history,context)
    db.add(Chat(user_id=user.id,conversation_id=str(body.conversation_id),question=body.question,answer=result));db.commit()
    return {'answer':result,'model':settings.ollama_model,'conversation_id':str(body.conversation_id)}

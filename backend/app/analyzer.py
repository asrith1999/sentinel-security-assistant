"""Deterministic evidence matching. Never executes log content."""
import re
import json
from collections import defaultdict
from datetime import datetime, timezone

IP = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
STAMP = re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?')

def parse_line(line):
    text = line
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            text = ' '.join(f'{k}={v}' for k, v in obj.items())
    except (ValueError, TypeError):
        obj = {}
    ip = (obj.get('src_ip') or obj.get('ip')) if isinstance(obj, dict) else None
    m = re.search(r'(?:for (?:invalid user )?|user(?:name)?[=:]\s*)([\w.@-]+)', text, re.I)
    user = obj.get('user') or obj.get('username') if isinstance(obj, dict) else None
    user = str(user or (m.group(1) if m else 'unknown'))
    match = IP.search(text)
    ip = str(ip or (match.group(0) if match else 'unknown'))
    time = STAMP.search(text)
    stamp = None
    if time:
        try:
            parsed = datetime.fromisoformat(time.group(0).replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            stamp = parsed.timestamp()
        except ValueError:
            pass
    return {'text': text, 'ip': ip, 'user': user, 'stamp': stamp}

def analyze(raw: str):
    raw = raw.strip()
    try:
        array = json.loads(raw)
        lines = [json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x for x in array] if isinstance(array, list) else raw.splitlines()
    except ValueError:
        lines = raw.splitlines()
    lines = [x for x in lines if x.strip()]
    events = [parse_line(x) for x in lines]
    failures = defaultdict(list)
    successes = []
    findings = []
    def add(code, severity, title, title_ta, detail, detail_ta, entries):
        findings.append({'code': code, 'severity': severity, 'title': title, 'title_ta': title_ta,
            'detail': detail, 'detail_ta': detail_ta, 'count': len(entries),
            'evidence': [x['text'][:700] for x in entries[:3]]})
    for e in events:
        if re.search(r'failed password|authentication fail|login[_ ]failed|invalid user', e['text'], re.I):
            failures[(e['ip'], e['user'])].append(e)
        if re.search(r'accepted password|login[_ ]success|authentication success', e['text'], re.I):
            successes.append(e)
    for (ip, user), entries in failures.items():
        add('auth_failures', 'high' if len(entries) >= 5 else 'medium',
            f'Authentication failures: {user} / {ip}', f'உள்நுழைவு தோல்விகள்: {user} / {ip}',
            f'{len(entries)} failures share this source/account. Check timing, owner activity and configuration. Counts alone do not establish an attack.',
            f'இந்த மூலம்/கணக்கில் {len(entries)} தோல்விகள் உள்ளன. நேரம், பயனர் செயல்பாடு, அமைப்புகளைச் சரிபார்க்கவும். எண்ணிக்கை மட்டும் தாக்குதலை உறுதிப்படுத்தாது.', entries)
        if ip != 'unknown' and user != 'unknown':
            for success in successes:
                same = success['ip'] == ip and success['user'] == user
                prior = [e for e in entries if e['stamp'] is not None and success['stamp'] is not None and 0 < success['stamp'] - e['stamp'] <= 900]
                if same and len(prior) >= 5:
                    add('success_after_failures', 'high', 'Successful login after repeated failures', 'பல தோல்விகளுக்குப் பின் வெற்றிகரமான உள்நுழைவு',
                        f'Same account ({user}) and source ({ip}) had at least 5 failures within 15 minutes before success. Verify with the owner; compromise is not confirmed.',
                        'ஒரே கணக்கு மற்றும் மூலத்திலிருந்து 15 நிமிடங்களுக்குள் குறைந்தது 5 தோல்விகளுக்குப் பின் வெற்றி உள்ளது. கணக்கு உரிமையாளரிடம் சரிபார்க்கவும்; ஊடுருவல் உறுதிப்படுத்தப்படவில்லை.', [success])
                    break
    sensitive = [e for e in events if re.search(r'/etc/shadow|mimikatz|encodedcommand|privilege escalation', e['text'], re.I)]
    if sensitive:
        add('sensitive_command', 'high', 'Sensitive command indicator', 'முக்கிய கட்டளை தொடர்பான அறிகுறி',
            'Review process ancestry and authorization. Legitimate administration can also match these indicators.',
            'செயல்முறை தொடர் மற்றும் அனுமதியைச் சரிபார்க்கவும். முறையான நிர்வாகச் செயல்களிலும் இந்த அறிகுறிகள் இருக்கலாம்.', sensitive)
    denied = [e for e in events if re.search(r'\bdeny\b|\bdenied\b|\bblocked\b|\bdrop\b', e['text'], re.I)]
    if denied:
        add('denied_traffic', 'medium', 'Denied or blocked activity', 'மறுக்கப்பட்ட அல்லது தடுக்கப்பட்ட செயல்பாடு',
            'Review firewall rule, destination and repetition. Blocked traffic alone does not establish compromise.',
            'ஃபயர்வால் விதி, இலக்கு, மீண்டும் நிகழ்வதைச் சரிபார்க்கவும். தடுக்கப்பட்ட போக்குவரத்து மட்டும் ஊடுருவலை உறுதிப்படுத்தாது.', denied)
    probes = [e for e in events if re.search(r'(?:GET|POST)\s+\S*(?:\.env|wp-admin|\.git/|\.\./)', e['text'], re.I)]
    if probes:
        add('web_probe', 'medium', 'Sensitive web path requested', 'முக்கிய இணையப் பாதைக்கான கோரிக்கை',
            'Inspect response status and body exposure. A path request is not evidence of successful exploitation.',
            'பதில் நிலை மற்றும் வெளியான தரவைச் சரிபார்க்கவும். கோரிக்கை மட்டும் வெற்றிகரமான தாக்குதலின் ஆதாரம் அல்ல.', probes)
    return {'line_count': len(lines), 'finding_count': len(findings), 'risk': 'high' if any(f['severity']=='high' for f in findings) else 'medium' if findings else 'unclassified',
            'findings': findings, 'method': 'Deterministic rules; optional local AI commentary is separate.'}

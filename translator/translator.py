# -*- coding: utf-8 -*-
"""
로스트 스토리즈 스토리 번역기 (Gemini API)
- 파이썬 3.9+ 기본 기능만 사용 (추가 설치 불필요)
- src/ 의 스토리 데이터를 읽어 ko/ 에 뷰어용 번역 파일을 만든다.
"""
import os, sys, json, csv, re, time, queue, threading, traceback, urllib.request, urllib.error, webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')
OUT = os.path.join(HERE, 'ko')
CFG_PATH = os.path.join(HERE, 'config.json')
BATCH_PATH = os.path.join(HERE, 'batches.json')
API = 'https://generativelanguage.googleapis.com'

PRICES = {  # USD per 1M tokens (input, output) — 2026-12-31까지 인하가 기준, 배치는 절반
    'gemini-3.8-flash': (0.75, 3.75),
    'gemini-3.7-flash': (0.75, 3.75),
    'gemini-3.5-flash': (0.30, 2.50),
    'gemini-3.5-flash-lite': (0.10, 0.40),
}
CAT_LABEL = [('prologue', '프롤로그'), ('main', '메인 스토리'), ('storyevent', '이벤트 스토리'), ('akito', '아키토 편'),
             ('another', '어나더'), ('entangle', '엔탱글'), ('bondslevel', '인연(본즈)'), ('gacha', '가챠 스토리'),
             ('gachanews', '가챠 뉴스'), ('birthday', '생일'), ('tutorial', '튜토리얼'), ('expedition', '원정')]

PH_GENDER = re.compile(r'%[^%\n]*%[^%\n]*%')

# ---------------------------------------------------------------- data
def load_index():
    with open(os.path.join(SRC, 'index.json'), encoding='utf-8') as f:
        return json.load(f)

def load_ep_lines(key):
    """returns ordered list of (k, kind, speaker, text)"""
    with open(os.path.join(SRC, 'ep', key + '.json'), encoding='utf-8') as f:
        d = json.load(f)
    lines = {}
    for g in d['groups'].values():
        for it in g:
            t = it[0]
            if t == 'S':
                lines[it[3]] = (it[3], 'S', it[1], it[2])
            elif t == 'N':
                lines[it[2]] = (it[2], 'N', '', it[1])
            elif t == 'T':
                lines[it[3]] = (it[3], 'T', '', it[2])
    return [lines[k] for k in sorted(lines)]

def load_glossary(path):
    rows = []
    if not path or not os.path.exists(path):
        return rows
    with open(path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            ja = (r.get('일본어') or '').strip(); ko = (r.get('한국어') or '').strip()
            if ja and ko and not ja.startswith('['):
                rows.append((ja, ko, (r.get('분류') or '').strip(), (r.get('메모') or '').strip()))
    rows.sort(key=lambda x: -len(x[0]))
    return rows

def read_json(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)

# ---------------------------------------------------------------- prompt
STYLE = """당신은 일본 게임 「코드 기아스 반역의 를르슈 로스트 스토리즈」의 스토리 대본을 한국어로 옮기는 전문 번역가입니다.

규칙:
1. 자연스러운 한국어 구어체로 번역합니다. 직역투를 피하고, 캐릭터의 성격과 말투(반말/존댓말, 위압적인 말투, 귀족적인 말투 등)를 원작 분위기대로 살립니다.
2. 고유명사는 [용어집]의 표기를 반드시 따릅니다. 용어집에 없는 이름은 일반적인 외래어 표기법으로 음역합니다.
3. [HERO_NAME] 은 주인공 이름 자리입니다. 그대로 [HERO_NAME] 으로 남깁니다.
4. %A%B% 형태는 주인공 성별에 따른 말투 분기입니다(A=남성, B=여성). 개수와 위치를 유지하고 양쪽 모두 한국어로 옮깁니다. 예: %ああ%ええ% → %그래%응%. 한국어에서 같아지면 %나%나% 처럼 같은 말을 양쪽에 씁니다.
5. 줄바꿈(\\n)은 원문과 비슷한 위치에 둡니다. 「……」「――」 같은 부호는 「……」「――」 그대로 씁니다. （ ）로 감싼 속마음은 ( )로 바꿉니다.
6. 번역문만 출력합니다. 설명, 주석, 원문을 붙이지 않습니다.

출력 형식: id를 키, 번역문을 값으로 하는 JSON 객체 하나만 출력합니다. id는 하나도 빠뜨리거나 추가하지 않습니다.
출력 예시: {"0": "첫 번째 대사 번역", "1": "두 번째 대사 번역", "2": "세 번째 대사 번역"}
입력처럼 {"id": ..., "speaker": ...} 형태로 한 줄씩 쓰지 마세요."""

def glossary_for(text_blob, gloss, names, limit=120):
    out = []
    for ja, ko, cat, memo in gloss:
        if ja in text_blob:
            out.append(f'{ja} = {ko}' + (f' ({memo})' if memo and cat != '인물' else ''))
            if len(out) >= limit:
                break
    used = set(x.split(' = ')[0] for x in out)
    for ja, ko in names.items():
        if ja not in used and ja in text_blob and len(out) < limit + 60:
            out.append(f'{ja} = {ko}')
    return '\n'.join(out)

def build_prompt(ep_label, chunk, ctx, gloss, names):
    blob = '\n'.join(c[2] + ' ' + c[3] for c in chunk)
    g = glossary_for(blob, gloss, names)
    body = []
    for k, kind, spk, text in chunk:
        who = ('주인공' if spk == '[HERO_NAME]' else names.get(spk, spk)) if spk else ('나레이션' if kind == 'N' else '장 제목')
        body.append(json.dumps({'id': str(k), 'speaker': who, 'ja': text}, ensure_ascii=False))
    ctx_txt = '\n'.join(f'{names.get(s, s) or "-"}: {t}' for _, _, s, t in ctx) or '(없음)'
    return (f'{STYLE}\n\n[용어집]\n{g or "(해당 없음)"}\n\n[회차] {ep_label}\n\n'
            f'[직전 대사 — 참고만, 번역하지 않음]\n{ctx_txt}\n\n[번역할 대사]\n' + '\n'.join(body))

def gen_config(model, json_out=True):
    gc = {'temperature': 0.4}
    if json_out:
        gc['responseMimeType'] = 'application/json'
    if model.startswith('gemini-3'):
        gc['thinkingConfig'] = {'thinkingLevel': 'low'}
    return gc

def gender_of(epkey):
    return 'f' if epkey.endswith('_female') else 'm'

def repair_gender(src, out, g):
    """원문보다 많은 %남%여% 분기는 회차 성별에 맞는 쪽으로 정리한다."""
    n_src = len(PH_GENDER.findall(src))
    groups = PH_GENDER.findall(out)
    if len(groups) <= n_src:
        return out
    keep = n_src
    def sub(m):
        nonlocal keep
        if keep > 0:
            keep -= 1; return m.group(0)
        a, b = m.group(0)[1:-1].split('%', 1)
        return b if g == 'f' else a
    return PH_GENDER.sub(sub, out)

def validate(chunk, res, epkey=''):
    """검증 + 자동 보정. 보정된 값은 res 에 다시 써 넣는다."""
    if not isinstance(res, dict):
        return 'JSON 객체가 아님'
    want = {str(c[0]) for c in chunk}
    got = set(res.keys())
    if want - got:
        return f'누락 id {sorted(want - got)[:5]}'
    g = gender_of(epkey)
    for k, kind, spk, text in chunk:
        v = res.get(str(k))
        if not isinstance(v, str) or (text.strip() and not v.strip()):
            return f'빈 번역 id {k}'
        v = repair_gender(text, v, g)
        if '[HERO_NAME]' in text and '[HERO_NAME]' not in v:
            return f'[HERO_NAME] 누락 id {k}'
        res[str(k)] = v
    return None

def _collect(obj, out_objs):
    if isinstance(obj, dict):
        out_objs.append(obj)
        if len(obj) == 1 and isinstance(next(iter(obj.values())), (dict, list)):
            _collect(next(iter(obj.values())), out_objs)
    elif isinstance(obj, list):
        for x in obj:
            _collect(x, out_objs)

def parse_json_text(t):
    """Gemini 응답에서 번역을 읽는다. 다음 형태를 모두 받아들인다:
       {"0":"..."} / 앞뒤 군더더기 / 같은 객체 반복 / [{"id":"0","ko":"..."}] / 한 줄씩 {"id":..} / {"translations":{...}}"""
    t = re.sub(r'```[a-zA-Z]*', '', t.strip()).replace('```', '')
    dec = json.JSONDecoder(); objs = []; i = 0
    while i < len(t):
        m = re.compile(r'[\[{]').search(t, i)
        if not m:
            break
        try:
            obj, end = dec.raw_decode(t, m.start())
        except ValueError:
            i = m.start() + 1; continue
        _collect(obj, objs); i = end
    if not objs:
        raise ValueError('JSON을 찾지 못함: ' + t[:120])
    out = {}
    for o in objs:
        if 'id' in o:  # 입력 형식을 흉내 낸 응답
            v = None
            for f in ('ko', 'translation', 'korean', 'text', 't', 'value', 'kr'):
                if isinstance(o.get(f), str):
                    v = o[f]; break
            if v is None:
                cand = [x for k, x in o.items() if k not in ('id', 'speaker', 'ja') and isinstance(x, str)]
                v = cand[0] if cand else None
            if v is not None:
                out.setdefault(str(o['id']), v)
            continue
        if len(o) == 1 and isinstance(next(iter(o.values())), (dict, list)):
            continue  # {"translations": {...}} — 안쪽 객체가 objs에 따로 들어 있음
        for k, v in o.items():
            if isinstance(v, str):
                out.setdefault(str(k), v)
    return out

# ---------------------------------------------------------------- HTTP
def http(method, url, key, body=None, headers=None, raw=False, timeout=300):
    h = {'x-goog-api-key': key}
    if headers:
        h.update(headers)
    data = None
    if body is not None:
        if isinstance(body, (bytes, bytearray)):
            data = body
        else:
            data = json.dumps(body).encode('utf-8'); h.setdefault('Content-Type', 'application/json')
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read()
            return (b, r.headers) if raw else json.loads(b.decode('utf-8') or '{}')
    except urllib.error.HTTPError as e:
        msg = e.read().decode('utf-8', 'replace')[:600]
        raise RuntimeError(f'HTTP {e.code}: {msg}')

def generate(key, model, prompt):
    body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': gen_config(model)}
    try:
        r = http('POST', f'{API}/v1beta/models/{model}:generateContent', key, body)
    except RuntimeError as e:
        if 'thinking' in str(e).lower():
            body['generationConfig'].pop('thinkingConfig', None)
            r = http('POST', f'{API}/v1beta/models/{model}:generateContent', key, body)
        else:
            raise
    cands = r.get('candidates') or []
    if not cands:
        raise RuntimeError('응답 없음: ' + json.dumps(r.get('promptFeedback', {}), ensure_ascii=False)[:200])
    text = ''.join(p.get('text', '') for p in cands[0].get('content', {}).get('parts', []) if not p.get('thought'))
    return text, r.get('usageMetadata', {})

# ---------------------------------------------------------------- engine
class Engine:
    def __init__(self, log, progress):
        self.log = log; self.progress = progress; self.stop = False
        self.usage = {'in': 0, 'out': 0}
        self.lock = threading.Lock()
        os.makedirs(OUT, exist_ok=True)

    def cost(self, model, batch=False):
        pi, po = PRICES.get(model, (0.75, 3.75))
        c = (self.usage['in'] * pi + self.usage['out'] * po) / 1e6
        return c / 2 if batch else c

    def add_usage(self, u):
        with self.lock:
            self.usage['in'] += u.get('promptTokenCount', 0)
            self.usage['out'] += u.get('candidatesTokenCount', 0) + u.get('thoughtsTokenCount', 0)

    # ---- episode plan
    def plan(self, cats, chunk_size):
        idx = load_index()
        jobs = []  # (key, label, chunks[list], existing dict)
        for c in idx:
            if c['id'] not in cats:
                continue
            for g in c['groups']:
                for e in g['eps']:
                    key = e[0]
                    lines = load_ep_lines(key)
                    if not lines:
                        continue
                    done = read_json(os.path.join(OUT, key + '.json'), {})
                    todo_idx = [i for i, l in enumerate(lines) if str(l[0]) not in done]
                    if not todo_idx:
                        continue
                    chunks = []
                    i = 0
                    while i < len(lines):
                        part = lines[i:i + chunk_size]
                        if any(str(l[0]) not in done for l in part):
                            ctx = lines[max(0, i - 6):i]
                            chunks.append((i // chunk_size, part, ctx))
                        i += chunk_size
                    jobs.append((key, f'{c["title"]} · {g["title"]} {e[1]}', chunks, len(lines)))
        return jobs

    def save_ep(self, key, add, total):
        with self.lock:
            p = os.path.join(OUT, key + '.json')
            d = read_json(p, {}); d.update(add); write_json(p, d)
            lst_p = os.path.join(OUT, '_list.json')
            lst = read_json(lst_p, [])
            if len(d) >= total and key not in lst:
                lst.append(key); write_json(lst_p, lst)
            return len(d)

    # ---- names
    def names_pass(self, key, model, gloss):
        idx = load_index()
        spk = {}
        for c in idx:
            for g in c['groups']:
                for e in g['eps']:
                    for k, kind, s, t in load_ep_lines(e[0]):
                        if s and s != '[HERO_NAME]':
                            spk[s] = spk.get(s, 0) + 1
        known = {ja: ko for ja, ko, cat, m in gloss}
        names = read_json(os.path.join(OUT, 'names.json'), {})
        for ja, ko in known.items():
            if ja in spk:
                names[ja] = ko
        todo = [s for s in sorted(spk, key=lambda x: -spk[x]) if s not in names]
        self.log(f'화자 이름 {len(spk)}개 중 용어집으로 {len(spk) - len(todo)}개 해결, {len(todo)}개 번역 필요')
        gl = '\n'.join(f'{ja} = {ko}' for ja, ko, cat, m in gloss if cat == '인물')
        for i in range(0, len(todo), 250):
            if self.stop:
                break
            part = todo[i:i + 250]
            prompt = ('다음은 일본 게임 「코드 기아스 로스트 스토리즈」의 화자 이름 목록입니다. 각 이름을 한국어 표기로 옮기세요.\n'
                      '규칙: 아래 [참고 용어집]의 인명 표기를 우선 따르고, 성과 이름이 붙은 경우 용어집 표기를 조합합니다. '
                      '「兵士Ａ」처럼 일반 명사+기호는 「병사 A」처럼 뜻을 옮깁니다. 「ルルーシュ＆スザク」처럼 여러 명이면 「를르슈&스자쿠」로 씁니다. '
                      '전각 영숫자는 반각으로 바꿉니다.\n출력: {"원래 이름": "한국어"} JSON 객체 하나.\n\n[참고 용어집]\n' + gl +
                      '\n\n[이름 목록]\n' + '\n'.join(part))
            for attempt in range(3):
                try:
                    t, u = generate(key, model, prompt); self.add_usage(u)
                    res = parse_json_text(t)
                    for s in part:
                        if isinstance(res.get(s), str) and res[s].strip():
                            names[s] = res[s].strip()
                    break
                except Exception as e:
                    self.log(f'  이름 번역 재시도 {attempt + 1}: {e}')
                    time.sleep(3)
            write_json(os.path.join(OUT, 'names.json'), names)
            self.log(f'  이름 {min(i + 250, len(todo))}/{len(todo)} 처리')
            self.progress(min(i + 250, len(todo)), len(todo))
        self.log(f'names.json 저장 완료 ({len(names)}개)')
        return names

    # ---- normal mode
    def run_normal(self, key, model, cats, chunk_size, workers, gloss):
        names = read_json(os.path.join(OUT, 'names.json'), {})
        if not names:
            self.log('※ names.json이 없습니다. 먼저 [1단계: 화자 이름 번역]을 실행하면 이름 표기가 통일됩니다.')
        jobs = self.plan(cats, chunk_size)
        tasks = [(j[0], j[1], ch, j[3]) for j in jobs for ch in j[2]]
        self.log(f'번역할 회차 {len(jobs)}개, 요청 {len(tasks)}건')
        if not tasks:
            return
        done_n = 0; fail = []

        def work(t):
            epkey, label, (ci, part, ctx), total = t
            prompt = build_prompt(label, part, ctx, gloss, names)
            last = None
            for attempt in range(3):
                if self.stop:
                    return epkey, ci, None, '중지됨'
                try:
                    txt, u = generate(key, model, prompt); self.add_usage(u)
                    res = parse_json_text(txt)
                    err = validate(part, res, epkey)
                    if not err:
                        return epkey, ci, {str(l[0]): res[str(l[0])] for l in part}, None
                    last = err
                except Exception as e:
                    last = str(e)
                    if 'HTTP 429' in last:
                        time.sleep(20 * (attempt + 1))
                time.sleep(2)
            return epkey, ci, None, last

        totals = {j[0]: j[3] for j in jobs}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(work, t) for t in tasks]
            for f in as_completed(futs):
                epkey, ci, res, err = f.result()
                done_n += 1
                if res:
                    n = self.save_ep(epkey, res, totals[epkey])
                    if n >= totals[epkey]:
                        self.log(f'✓ {epkey} 완료')
                else:
                    fail.append((epkey, ci, err)); self.log(f'✗ {epkey} #{ci}: {err}')
                self.progress(done_n, len(tasks))
                if done_n % 10 == 0:
                    self.log(f'  진행 {done_n}/{len(tasks)} · 사용 토큰 입력 {self.usage["in"]:,} / 출력 {self.usage["out"]:,} · 예상 ${self.cost(model):.2f}')
                if self.stop:
                    for x in futs:
                        x.cancel()
                    break
        self.log(f'끝. 실패 {len(fail)}건 (다시 실행하면 실패한 부분만 이어서 번역합니다) · 예상 비용 ${self.cost(model):.2f}')

    # ---- batch mode
    def batch_submit(self, key, model, cats, chunk_size, gloss):
        names = read_json(os.path.join(OUT, 'names.json'), {})
        jobs = self.plan(cats, chunk_size)
        state = read_json(BATCH_PATH, {'batches': []})
        pending = set()
        for b in state['batches']:
            if b.get('status') not in ('done', 'failed'):
                pending.update(b.get('keys', []))
        lines = []; keys = []
        for epkey, label, chunks, total in jobs:
            for ci, part, ctx in chunks:
                k = f'{epkey}|{ci}|{chunk_size}'
                if k in pending:
                    continue
                req = {'contents': [{'role': 'user', 'parts': [{'text': build_prompt(label, part, ctx, gloss, names)}]}],
                       'generationConfig': gen_config(model)}
                lines.append(json.dumps({'key': k, 'request': req}, ensure_ascii=False)); keys.append(k)
        if not lines:
            self.log('제출할 요청이 없습니다 (모두 번역됐거나 이미 제출됨).')
            return
        # split into files of <= 150MB / 20000 lines
        parts = [list(range(i, min(i + 15000, len(lines)))) for i in range(0, len(lines), 15000)]
        for pi, rng in enumerate(parts):
            data = ('\n'.join(lines[i] for i in rng) + '\n').encode('utf-8')
            self.log(f'배치 파일 업로드 {pi + 1}/{len(parts)} ({len(rng)}건, {len(data) / 1e6:.1f}MB)…')
            _, hd = http('POST', f'{API}/upload/v1beta/files', key, {'file': {'display_name': f'ls_{int(time.time())}_{pi}'}},
                         headers={'X-Goog-Upload-Protocol': 'resumable', 'X-Goog-Upload-Command': 'start',
                                  'X-Goog-Upload-Header-Content-Length': str(len(data)),
                                  'X-Goog-Upload-Header-Content-Type': 'application/jsonl'}, raw=True)
            up = hd.get('x-goog-upload-url') or hd.get('X-Goog-Upload-URL')
            r = http('POST', up, key, data, headers={'Content-Length': str(len(data)), 'X-Goog-Upload-Offset': '0',
                                                     'X-Goog-Upload-Command': 'upload, finalize'}, timeout=900)
            fname = r['file']['name']
            b = http('POST', f'{API}/v1beta/models/{model}:batchGenerateContent', key,
                     {'batch': {'display_name': f'ls-story-{pi}', 'input_config': {'file_name': fname}}})
            name = b.get('name') or b.get('metadata', {}).get('name')
            state['batches'].append({'name': name, 'model': model, 'status': 'submitted', 'keys': [keys[i] for i in rng],
                                     'submitted': time.strftime('%Y-%m-%d %H:%M')})
            write_json(BATCH_PATH, state)
            self.log(f'  제출됨: {name}')
        self.log('배치 제출 완료. 보통 몇 분~몇 시간 걸립니다(최대 24시간). [배치 결과 받기]로 확인하세요.')

    def batch_collect(self, key, chunk_size_default):
        state = read_json(BATCH_PATH, {'batches': []})
        if not state['batches']:
            self.log('제출된 배치가 없습니다.'); return
        cache = {}
        for b in state['batches']:
            if b.get('status') in ('done', 'failed'):
                continue
            info = http('GET', f'{API}/v1beta/{b["name"]}', key)
            meta = info.get('metadata', info)
            st = meta.get('state') or info.get('state') or '?'
            self.log(f'{b["name"]}: {st}')
            if st.endswith('SUCCEEDED'):
                resp = info.get('response', {}) or meta
                fname = (resp.get('responsesFile') or meta.get('output', {}).get('responsesFile')
                         or meta.get('dest', {}).get('fileName') or resp.get('dest', {}).get('fileName'))
                if not fname:
                    self.log('  결과 파일 이름을 찾지 못했습니다: ' + json.dumps(info)[:300]); continue
                raw, _ = http('GET', f'{API}/download/v1beta/{fname}:download?alt=media', key, raw=True, timeout=900)
                ok = bad = 0
                for line in raw.decode('utf-8').splitlines():
                    if not line.strip():
                        continue
                    o = json.loads(line)
                    k = o.get('key', ''); epkey, ci, cs = k.split('|'); ci = int(ci); cs = int(cs)
                    if epkey not in cache:
                        cache[epkey] = load_ep_lines(epkey)
                    lines = cache[epkey]; part = lines[ci * cs:(ci + 1) * cs]
                    try:
                        r = o['response']; self.add_usage(r.get('usageMetadata', {}))
                        txt = ''.join(p.get('text', '') for p in r['candidates'][0]['content']['parts'] if not p.get('thought'))
                        res = parse_json_text(txt); err = validate(part, res, epkey)
                        if err:
                            raise ValueError(err)
                        self.save_ep(epkey, {str(l[0]): res[str(l[0])] for l in part}, len(lines)); ok += 1
                    except Exception as e:
                        bad += 1
                b['status'] = 'done'; b['ok'] = ok; b['bad'] = bad
                self.log(f'  반영 {ok}건, 실패 {bad}건 (실패분은 다음 제출/일반 모드에서 다시 번역됩니다)')
                self.log(f'  누적 예상 비용(배치 할인 적용) ${self.cost(b.get("model", "gemini-3.8-flash"), True):.2f}')
            elif st.endswith(('FAILED', 'CANCELLED', 'EXPIRED')):
                b['status'] = 'failed'; self.log('  이 배치는 실패했습니다. 다시 제출하세요.')
            write_json(BATCH_PATH, state)

    def status(self, cats):
        idx = load_index(); tot = done = eps = eps_done = 0
        lst = set(read_json(os.path.join(OUT, '_list.json'), []))
        for c in idx:
            if c['id'] not in cats:
                continue
            for g in c['groups']:
                for e in g['eps']:
                    n = e[2]; tot += n; eps += 1
                    d = read_json(os.path.join(OUT, e[0] + '.json'), {}) if os.path.exists(os.path.join(OUT, e[0] + '.json')) else {}
                    done += min(len(d), n)
                    if e[0] in lst:
                        eps_done += 1
        return tot, done, eps, eps_done

# ---------------------------------------------------------------- GUI
def main():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    os.makedirs(OUT, exist_ok=True)
    cfg = read_json(CFG_PATH, {})
    root = tk.Tk(); root.title('로스트 스토리즈 스토리 번역기 (Gemini)'); root.geometry('760x720')
    q = queue.Queue()
    log = lambda s: q.put(('log', s))
    prog = lambda a, b: q.put(('prog', a, b))
    eng = Engine(log, prog)
    pad = {'padx': 10, 'pady': 5}

    f1 = ttk.LabelFrame(root, text='1. API 설정'); f1.pack(fill='x', **pad)
    ttk.Label(f1, text='Gemini API 키').grid(row=0, column=0, sticky='w', padx=6, pady=4)
    v_key = tk.StringVar(value=cfg.get('key', os.environ.get('GEMINI_API_KEY', '')))
    ttk.Entry(f1, textvariable=v_key, show='•', width=52).grid(row=0, column=1, sticky='we', padx=6)
    ttk.Button(f1, text='키 발급 페이지', command=lambda: webbrowser.open('https://aistudio.google.com/apikey')).grid(row=0, column=2, padx=6)
    ttk.Label(f1, text='모델').grid(row=1, column=0, sticky='w', padx=6, pady=4)
    v_model = tk.StringVar(value=cfg.get('model', 'gemini-3.8-flash'))
    ttk.Combobox(f1, textvariable=v_model, values=list(PRICES), width=28).grid(row=1, column=1, sticky='w', padx=6)
    ttk.Label(f1, text='용어집').grid(row=2, column=0, sticky='w', padx=6, pady=4)
    v_gl = tk.StringVar(value=cfg.get('glossary', os.path.join(HERE, 'ls_glossary.csv')))
    ttk.Entry(f1, textvariable=v_gl, width=52).grid(row=2, column=1, sticky='we', padx=6)
    ttk.Button(f1, text='찾기', command=lambda: v_gl.set(filedialog.askopenfilename(filetypes=[('CSV', '*.csv')]) or v_gl.get())).grid(row=2, column=2, padx=6)

    f2 = ttk.LabelFrame(root, text='2. 번역 범위'); f2.pack(fill='x', **pad)
    v_cats = {}
    for i, (cid, lab) in enumerate(CAT_LABEL):
        v = tk.BooleanVar(value=cid in cfg.get('cats', ['prologue', 'main']))
        ttk.Checkbutton(f2, text=lab, variable=v).grid(row=i // 4, column=i % 4, sticky='w', padx=8, pady=2)
        v_cats[cid] = v
    f2b = ttk.Frame(f2); f2b.grid(row=3, column=0, columnspan=4, sticky='w', padx=8, pady=4)
    ttk.Label(f2b, text='요청당 대사 수').pack(side='left')
    v_chunk = tk.IntVar(value=cfg.get('chunk', 60)); ttk.Spinbox(f2b, from_=20, to=150, textvariable=v_chunk, width=5).pack(side='left', padx=6)
    ttk.Label(f2b, text='동시 요청 수(일반 모드)').pack(side='left', padx=(16, 0))
    v_workers = tk.IntVar(value=cfg.get('workers', 4)); ttk.Spinbox(f2b, from_=1, to=16, textvariable=v_workers, width=4).pack(side='left', padx=6)

    f3 = ttk.LabelFrame(root, text='3. 실행'); f3.pack(fill='x', **pad)
    btns = []
    def cats(): return [c for c, v in v_cats.items() if v.get()]
    def save_cfg():
        write_json(CFG_PATH, {'key': v_key.get().strip(), 'model': v_model.get().strip(), 'glossary': v_gl.get(),
                              'cats': cats(), 'chunk': v_chunk.get(), 'workers': v_workers.get()})
    def run(fn):
        if not v_key.get().strip():
            messagebox.showwarning('API 키', 'Gemini API 키를 입력하세요.'); return
        save_cfg(); eng.stop = False
        for b in btns: b.state(['disabled'])
        def t():
            try:
                fn()
            except Exception as e:
                log('오류: ' + str(e)); log(traceback.format_exc()[-800:])
            q.put(('done',))
        threading.Thread(target=t, daemon=True).start()
    K = lambda: v_key.get().strip(); M = lambda: v_model.get().strip(); GL = lambda: load_glossary(v_gl.get())
    b1 = ttk.Button(f3, text='1단계: 화자 이름 번역', command=lambda: run(lambda: eng.names_pass(K(), M(), GL())))
    b2 = ttk.Button(f3, text='번역 시작 (일반)', command=lambda: run(lambda: eng.run_normal(K(), M(), cats(), v_chunk.get(), v_workers.get(), GL())))
    b3 = ttk.Button(f3, text='배치 제출 (반값)', command=lambda: run(lambda: eng.batch_submit(K(), M(), cats(), v_chunk.get(), GL())))
    b4 = ttk.Button(f3, text='배치 결과 받기', command=lambda: run(lambda: eng.batch_collect(K(), v_chunk.get())))
    for i, b in enumerate((b1, b2, b3, b4)):
        b.grid(row=0, column=i, padx=6, pady=6, sticky='we'); btns.append(b)
    b5 = ttk.Button(f3, text='중지', command=lambda: (setattr(eng, 'stop', True), log('중지 요청됨 — 진행 중인 요청이 끝나면 멈춥니다.')))
    b5.grid(row=1, column=0, padx=6, pady=4, sticky='we')
    def show_status():
        tot, done, eps, epd = eng.status(cats())
        log(f'[진행 현황] 선택 범위 대사 {done:,}/{tot:,}줄 ({(done / tot * 100) if tot else 0:.1f}%) · 완료 회차 {epd}/{eps}')
    ttk.Button(f3, text='진행 현황', command=show_status).grid(row=1, column=1, padx=6, pady=4, sticky='we')
    ttk.Button(f3, text='결과 폴더 열기', command=lambda: os.startfile(OUT) if hasattr(os, 'startfile') else None).grid(row=1, column=2, padx=6, pady=4, sticky='we')

    pb = ttk.Progressbar(root, mode='determinate'); pb.pack(fill='x', padx=10, pady=(4, 0))
    txt = scrolledtext.ScrolledText(root, height=18, font=('Malgun Gothic', 9)); txt.pack(fill='both', expand=True, padx=10, pady=8)

    def pump():
        try:
            while True:
                m = q.get_nowait()
                if m[0] == 'log':
                    txt.insert('end', m[1] + '\n'); txt.see('end')
                elif m[0] == 'prog':
                    pb['maximum'] = max(1, m[2]); pb['value'] = m[1]
                elif m[0] == 'done':
                    for b in btns: b.state(['!disabled'])
        except queue.Empty:
            pass
        root.after(150, pump)
    pump()
    log('준비 완료. 처음이면 ① API 키 입력 → ② [1단계: 화자 이름 번역] → ③ 범위 선택 후 [번역 시작] 순서로 진행하세요.')
    log('결과는 ko 폴더에 쌓이며, 중간에 꺼도 다시 실행하면 남은 부분만 이어서 번역합니다.')
    root.mainloop()

if __name__ == '__main__':
    main()
